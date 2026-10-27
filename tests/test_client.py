import unittest
from unittest.mock import patch, MagicMock
from mvsep.client import MVSepClient


class TestClient(unittest.TestCase):
    def test_extract_hash(self):
        raw = "20261027133636-909ae99d45-nowhere-man.wav"
        self.assertEqual(MVSepClient.extract_hash(raw), raw)

        url1 = "https://mvsep.com/result/20261027133636-909ae99d45-nowhere-man.wav"
        self.assertEqual(MVSepClient.extract_hash(url1), raw)

        url2 = "https://mvsep.com/result/20261027133636-909ae99d45-nowhere-man.wav/download_zip"
        self.assertEqual(MVSepClient.extract_hash(url2), raw)

        url3 = "https://mvsep.com/result/get_status/20261027133636-909ae99d45-nowhere-man.wav"
        self.assertEqual(MVSepClient.extract_hash(url3), raw)

    @patch("mvsep.client.requests.get")
    def test_get_status_done_from_api(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "success": True,
            "status": "done",
            "data": {
                "hash": "test-hash.wav",
                "algorithm": "BS Roformer SW",
                "files": [
                    {"url": "https://de.mvsep.com/test_vocals.mp3", "download": "test_vocals.mp3"}
                ]
            }
        }
        mock_get.return_value = mock_resp

        client = MVSepClient()
        status = client.get_status("test-hash.wav")

        self.assertEqual(status["status"], "done")
        self.assertEqual(len(status["files"]), 1)
        self.assertEqual(status["files"][0]["download"], "test_vocals.mp3")

    @patch("mvsep.client.requests.get")
    def test_get_status_waiting_with_queue(self, mock_get):
        # First call to /api/separation/get returns status waiting, no files
        resp_api = MagicMock()
        resp_api.status_code = 200
        resp_api.json.return_value = {
            "success": True,
            "status": "waiting",
            "data": {}
        }

        # Second call to /result/get_status returns HTML view
        resp_web = MagicMock()
        resp_web.status_code = 200
        resp_web.json.return_value = {
            "success": True,
            "status": "waiting",
            "view": '<div data-stage="queue" data-eta="94" data-state-label="Number 22 of 112 in the queue"></div>'
        }

        mock_get.side_effect = [resp_api, resp_web]

        client = MVSepClient()
        status = client.get_status("test-hash.wav")

        self.assertEqual(status["status"], "waiting")
        self.assertEqual(status["stage"], "queue")
        self.assertEqual(status["queue_label"], "Number 22 of 112 in the queue")
        self.assertEqual(status["eta"], 94)


if __name__ == "__main__":
    unittest.main()
