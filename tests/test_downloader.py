import unittest
from pathlib import Path
from mvsep.downloader import extract_stem_name, format_output_path, StemDownloader


class TestDownloader(unittest.TestCase):
    def test_extract_stem_name(self):
        self.assertEqual(extract_stem_name("nowhere-man_bs6stem_mt_0_vocals.mp3"), "vocals")
        self.assertEqual(extract_stem_name("track_123_bass.wav"), "bass")
        self.assertEqual(extract_stem_name("song_instrum.mp3"), "instrum")
        self.assertEqual(extract_stem_name("song_guitar.flac"), "guitar")
        self.assertEqual(extract_stem_name("simple.mp3"), "simple")

    def test_format_output_path(self):
        output_dir = Path("/tmp/output")
        template = "%(title)s/%(stem)s.%(ext)s"
        dest = format_output_path(
            template=template,
            output_dir=output_dir,
            title="Nowhere Man",
            stem="vocals",
            ext="mp3",
            task_hash="hash123",
        )
        self.assertEqual(str(dest), "/tmp/output/Nowhere Man/vocals.mp3")

    def test_filter_files(self):
        downloader = StemDownloader()
        files = [
            {"download": "song_vocals.mp3", "url": "http://.../v"},
            {"download": "song_drums.mp3", "url": "http://.../d"},
            {"download": "song_bass.mp3", "url": "http://.../b"},
        ]

        filtered = downloader.filter_files(files, stem_filter=["vocals", "bass"])
        self.assertEqual(len(filtered), 2)
        names = [f["download"] for f in filtered]
        self.assertIn("song_vocals.mp3", names)
        self.assertIn("song_bass.mp3", names)
        self.assertNotIn("song_drums.mp3", names)


if __name__ == "__main__":
    unittest.main()
