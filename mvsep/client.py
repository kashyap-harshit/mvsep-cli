"""Network and API client for mvsep.com."""

import os
import re
import time
import requests
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse

DEFAULT_BASE_URL = "https://mvsep.com"
DEFAULT_USER_AGENT = "mvsep-cli/0.1"


class MVSepClient:
    def __init__(
        self,
        api_token: Optional[str] = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: int = 30,
        user_agent: str = DEFAULT_USER_AGENT,
    ):
        self.api_token = api_token
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.headers = {"User-Agent": user_agent}

    @staticmethod
    def extract_hash(url_or_hash: str) -> str:
        """Extract the separation task hash from a URL or raw hash string."""
        raw = url_or_hash.strip()
        # If it's a get_status URL: /result/get_status/<hash>
        if "/get_status/" in raw:
            match = re.search(r"/get_status/([^/?#]+)", raw)
            if match:
                return match.group(1)
        # If it's a URL like https://mvsep.com/result/<hash>[/download_zip]
        elif "mvsep.com/result/" in raw:
            match = re.search(r"mvsep\.com/result/([^/?#]+)", raw)
            if match:
                return match.group(1)

        # Remove any trailing query strings or path fragments
        if "/" in raw:
            raw = raw.rstrip("/").split("/")[-1]
        return raw.split("?")[0].split("#")[0]

    def login(self, email: str, password: str) -> Dict[str, Any]:
        """Authenticate with email and password to retrieve user data and API token."""
        url = f"{self.base_url}/api/app/login"
        data = {"email": email.strip(), "password": password}
        resp = requests.post(url, data=data, headers=self.headers, timeout=self.timeout)

        if resp.status_code != 200:
            try:
                err_json = resp.json()
                msg = err_json.get("message") or err_json.get("error") or resp.text
            except Exception:
                msg = resp.text
            raise RuntimeError(f"Login failed (HTTP {resp.status_code}): {msg}")

        res = resp.json()
        if not res.get("success"):
            raise RuntimeError(f"Login failed: {res.get('message', 'Invalid credentials')}")

        user_data = res.get("data", {})
        token = user_data.get("api_token")
        if token:
            self.api_token = token
        return user_data

    def get_user_info(self) -> Dict[str, Any]:
        """Fetch user profile and remaining credits."""
        if not self.api_token:
            raise ValueError("API token is required to fetch user info.")
        url = f"{self.base_url}/api/user"
        params = {"api_token": self.api_token}
        resp = requests.get(url, params=params, headers=self.headers, timeout=self.timeout)
        if resp.status_code != 200:
            raise RuntimeError(f"Failed to fetch user info (HTTP {resp.status_code}): {resp.text}")
        return resp.json().get("data", {})

    def create_separation(
        self,
        filepath: Optional[str] = None,
        remote_url: Optional[str] = None,
        sep_type: int = 63,
        output_format: int = 0,
        add_opt1: Optional[str] = None,
        add_opt2: Optional[str] = None,
        add_opt3: Optional[str] = None,
        is_demo: int = 0,
        progress_callback: Optional[Any] = None,
    ) -> str:
        """Create a new separation task using a local audio file or remote URL."""
        if not self.api_token:
            raise ValueError(
                "An API token is required to create separations.\n"
                "You can get your free API key at https://mvsep.com/api and set it with:\n"
                "  mvsep login\n"
                "or pass --token <your_token> / set MVSEP_API_TOKEN environment variable."
            )

        url = f"{self.base_url}/api/separation/create"
        data: Dict[str, Any] = {
            "api_token": self.api_token,
            "sep_type": str(sep_type),
            "output_format": str(output_format),
            "is_demo": str(is_demo),
        }
        if add_opt1:
            data["add_opt1"] = add_opt1
        if add_opt2:
            data["add_opt2"] = add_opt2
        if add_opt3:
            data["add_opt3"] = add_opt3

        files = None
        file_obj = None

        if filepath:
            if not os.path.isfile(filepath):
                raise FileNotFoundError(f"Audio file not found: {filepath}")
            file_obj = open(filepath, "rb")
            files = {"audiofile": file_obj}
        elif remote_url:
            data["url"] = remote_url
        else:
            raise ValueError("Either filepath or remote_url must be provided.")

        try:
            # We use a larger timeout for uploading large audio files
            upload_timeout = (30, 600)
            resp = requests.post(
                url,
                data=data,
                files=files,
                headers=self.headers,
                timeout=upload_timeout,
            )
        finally:
            if file_obj:
                file_obj.close()

        if resp.status_code != 200:
            try:
                err_data = resp.json()
                msg = err_data.get("message") or err_data.get("error") or resp.text
            except Exception:
                msg = resp.text
            raise RuntimeError(f"Separation creation failed (HTTP {resp.status_code}): {msg}")

        res = resp.json()
        if not res.get("success"):
            msg = res.get("message", "Unknown error from MVSep API")
            raise RuntimeError(f"Separation creation error: {msg}")

        task_hash = res.get("data", {}).get("hash")
        if not task_hash:
            raise RuntimeError("MVSep did not return a valid task hash.")

        return task_hash

    def get_status(self, task_hash: str) -> Dict[str, Any]:
        """Fetch current status and results for a separation task.

        Combines official /api/separation/get data with rich web /result/get_status
        queue and ETA estimates.
        """
        task_hash = self.extract_hash(task_hash)
        result: Dict[str, Any] = {
            "hash": task_hash,
            "status": "waiting",
            "stage": "queue",
            "queue_label": "",
            "eta": None,
            "files": [],
            "algorithm": "",
            "output_format": "",
            "input_file": {},
        }

        # 1. Query official API endpoint
        api_url = f"{self.base_url}/api/separation/get"
        try:
            resp = requests.get(
                api_url,
                params={"hash": task_hash},
                headers=self.headers,
                timeout=self.timeout,
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success"):
                    api_status = data.get("status", "")
                    if api_status:
                        result["status"] = api_status

                    details = data.get("data", {})
                    if "files" in details:
                        result["files"] = details["files"]
                        result["status"] = "done"
                        result["stage"] = "done"

                    if "algorithm" in details:
                        result["algorithm"] = details["algorithm"]
                    if "output_format" in details:
                        result["output_format"] = details["output_format"]
                    if "input_file" in details:
                        result["input_file"] = details["input_file"]
        except Exception:
            pass

        # If already done with files, no need to query web status view
        if result["status"] == "done" and result["files"]:
            return result

        # 2. Query web status view to get queue rank, ETA, and stage details
        web_status_url = f"{self.base_url}/result/get_status/{task_hash}"
        try:
            wresp = requests.get(web_status_url, headers=self.headers, timeout=self.timeout)
            if wresp.status_code == 200:
                wdata = wresp.json()
                w_status = wdata.get("status", "")
                if w_status:
                    result["status"] = w_status

                view = wdata.get("view", "")
                if view:
                    # Parse data-stage
                    stage_m = re.search(r'data-stage=["\']([^"\']+)["\']', view)
                    if stage_m:
                        result["stage"] = stage_m.group(1)

                    # Parse data-state-label (e.g. "Number 22 of 112 in the queue")
                    label_m = re.search(r'data-state-label=["\']([^"\']+)["\']', view)
                    if label_m:
                        result["queue_label"] = label_m.group(1)

                    # Parse data-eta
                    eta_m = re.search(r'data-eta=["\'](\d+)["\']', view)
                    if eta_m:
                        try:
                            result["eta"] = int(eta_m.group(1))
                        except ValueError:
                            pass

                    # If status is done but files weren't in /api/separation/get,
                    # parse stem links directly from the HTML view!
                    if w_status == "done" and not result["files"]:
                        stem_matches = re.findall(
                            r'href=["\'](https?://[^"\']+/storage/processed/[^"\']+\.(?:mp3|wav|flac))(?:\?dl=([^"\']+))?["\']',
                            view,
                        )
                        parsed_files = []
                        seen_urls = set()
                        for s_url, s_dl in stem_matches:
                            if s_url not in seen_urls:
                                seen_urls.add(s_url)
                                filename = s_dl or os.path.basename(s_url)
                                parsed_files.append({"url": s_url, "download": filename})
                        if parsed_files:
                            result["files"] = parsed_files
        except Exception:
            pass

        return result
