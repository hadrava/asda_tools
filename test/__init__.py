import unittest
import os.path
from asda_tools import ASDAParser


class TestASDAParser(unittest.TestCase):
    DATA_DIR = "test_files/"
    DATA_FILES = [
            "test_01_params",
            "test_01_pr",
            "test_02_params",
            "test_02_pr",
            ]

    def test_load(self):
        for filename in self.DATA_FILES:
            test_filename = os.path.join(os.path.dirname(__file__), self.DATA_DIR, filename)
            with self.subTest(test_filename=test_filename):
                parser = ASDAParser()
                parser.load_param_file(test_filename + ".par")
                parser.parse()
                output_json = parser.to_json() + "\n"
                with open(test_filename + ".json") as f:
                    ideal_json = f.read()
                self.assertEqual(output_json, ideal_json)

    def test_reconstruct(self):
        for filename in self.DATA_FILES:
            test_filename = os.path.join(os.path.dirname(__file__), self.DATA_DIR, filename)
            with self.subTest(test_filename=test_filename):
                writer = ASDAParser()
                writer.from_json_file(test_filename + ".json")
                writer.reconstruct()
                with open(test_filename + ".par", "rb") as f:
                    ideal_binary = f.read()
                self.assertEqual(writer.binary_reconstruct, ideal_binary)


if __name__ == '__main__':
    unittest.main()
