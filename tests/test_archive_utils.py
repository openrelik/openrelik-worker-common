import unittest
from unittest.mock import patch, MagicMock
from openrelik_worker_common.archive_utils import extract_archive
import os
import shutil
import subprocess
from uuid import uuid4


class Utils(unittest.TestCase):
    output_folder = "/tmp"
    log_file = "/tmp/log.txt"

    @patch("subprocess.call")
    @patch("subprocess.check_output")
    @patch("shutil.which")
    def test_extract_archive_tgz(
        self, mock_which, mock_check_output, mock_subprocess_call
    ):
        input_file = {"path": "/path/to/archive.tgz", "display_name": "archive.tgz"}
        mock_check_output.return_value = b""
        mock_which.return_value = True
        mock_subprocess_call.return_value = 0

        result = extract_archive(input_file, self.output_folder, self.log_file)
        self.assertIn("tar -vxzf", result[0])
        self.assertIn(self.output_folder, result[1])

    @patch("subprocess.call")
    @patch("subprocess.check_output")
    @patch("shutil.which")
    def test_extract_archive_zip(
        self, mock_which, mock_check_output, mock_subprocess_call
    ):
        input_file = {"path": "/path/to/archive.zip", "display_name": "archive.zip"}
        mock_check_output.return_value = b""
        mock_which.return_value = True
        mock_subprocess_call.return_value = 0

        result = extract_archive(input_file, self.output_folder, self.log_file)
        self.assertIn("7z x", result[0])
        self.assertIn(self.output_folder, result[1])

    @patch("subprocess.call")
    @patch("subprocess.check_output")
    def test_extract_archive_error(self, mock_check_output, mock_subprocess_call):
        input_file = {"path": "/path/to/archive.tgz", "display_name": "archive.tgz"}
        mock_subprocess_call.return_value = 1

        with self.assertRaises(RuntimeError):
            extract_archive(input_file, self.output_folder, self.log_file)

    @patch("subprocess.check_output")
    def test_extract_archive_7z_not_found(self, mock_check_output):
        input_file = {"path": "/path/to/archive.tgz", "display_name": "archive.tgz"}
        mock_check_output.return_value = b""

        with patch("shutil.which", return_value=None):
            with self.assertRaises(RuntimeError):
                extract_archive(input_file, self.output_folder, self.log_file)

    @patch("os.makedirs")
    @patch("shutil.which")
    def test_extract_archive_mkdir_error(self, mock_which, mock_makedirs):
        input_file = {"path": "/path/to/archive.tgz", "display_name": "archive.tgz"}
        mock_makedirs.side_effect = OSError("Mocked error")
        mock_which.return_value = True

        with self.assertRaises(OSError):
            extract_archive(input_file, self.output_folder, self.log_file)


if __name__ == "__main__":
    unittest.main()
