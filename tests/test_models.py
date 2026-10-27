import unittest
from mvsep.models import parse_format, resolve_model, FALLBACK_ALGORITHMS


class TestModels(unittest.TestCase):
    def test_parse_format(self):
        self.assertEqual(parse_format("mp3"), 0)
        self.assertEqual(parse_format(".wav"), 1)
        self.assertEqual(parse_format("FLAC"), 2)
        self.assertEqual(parse_format(0), 0)
        self.assertEqual(parse_format(1), 1)
        self.assertEqual(parse_format(2), 2)
        with self.assertRaises(ValueError):
            parse_format("ogg")
        with self.assertRaises(ValueError):
            parse_format(99)

    def test_resolve_model_by_id(self):
        m = resolve_model(63, algorithms=FALLBACK_ALGORITHMS)
        self.assertEqual(m["render_id"], 63)
        self.assertIn("BS Roformer SW", m["name"])

        m2 = resolve_model("20", algorithms=FALLBACK_ALGORITHMS)
        self.assertEqual(m2["render_id"], 20)
        self.assertIn("Demucs4", m2["name"])

    def test_resolve_model_by_name(self):
        m = resolve_model("demucs", algorithms=FALLBACK_ALGORITHMS)
        self.assertEqual(m["render_id"], 20)

        m2 = resolve_model("roformer sw", algorithms=FALLBACK_ALGORITHMS)
        self.assertEqual(m2["render_id"], 63)

    def test_resolve_model_not_found(self):
        with self.assertRaises(ValueError):
            resolve_model("nonexistent_model_xyz", algorithms=FALLBACK_ALGORITHMS)


if __name__ == "__main__":
    unittest.main()
