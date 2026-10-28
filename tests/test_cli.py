import unittest
from mvsep.cli import main
from mvsep.config import load_config


class TestCli(unittest.TestCase):
    def test_cli_help(self):
        with self.assertRaises(SystemExit) as cm:
            main(["--help"])
        self.assertEqual(cm.exception.code, 0)

    def test_cli_version(self):
        with self.assertRaises(SystemExit) as cm:
            main(["--version"])
        self.assertEqual(cm.exception.code, 0)

    def test_cli_no_args(self):
        # With no inputs, prints help and returns 0
        ret = main([])
        self.assertEqual(ret, 0)


if __name__ == "__main__":
    unittest.main()
