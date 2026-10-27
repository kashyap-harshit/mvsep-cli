import unittest
import tempfile
import os
from pathlib import Path
from mvsep.queue import scan_audio_files, load_queue_state, save_queue_state


class TestQueue(unittest.TestCase):
    def test_scan_audio_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            d = Path(tmpdir)
            f1 = d / "song1.mp3"
            f2 = d / "song2.wav"
            f3 = d / "notes.txt"
            f4 = d / ".hidden.mp3"

            f1.touch()
            f2.touch()
            f3.touch()
            f4.touch()

            found = scan_audio_files(d)
            names = [f.name for f in found]

            self.assertIn("song1.mp3", names)
            self.assertIn("song2.wav", names)
            self.assertNotIn("notes.txt", names)
            self.assertNotIn(".hidden.mp3", names)

    def test_queue_state_persistence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / ".mvsep_queue.json"
            initial = load_queue_state(state_file)
            self.assertIn("items", initial)

            initial["items"]["file1"] = {"status": "completed", "task_hash": "abc"}
            save_queue_state(state_file, initial)

            loaded = load_queue_state(state_file)
            self.assertEqual(loaded["items"]["file1"]["status"], "completed")
            self.assertEqual(loaded["items"]["file1"]["task_hash"], "abc")


if __name__ == "__main__":
    unittest.main()
