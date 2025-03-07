# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest
import unittest.mock
import os
import tempfile
from pathlib import Path

from openrelik_worker_common import file_utils


class Utils(unittest.TestCase):
    """Test the utils helper functions."""

    def assertFileExists(self, path):
        """Helper function to check if file exists."""
        if not Path(path).resolve().is_file():
            raise AssertionError(f"File does not exist: {path}")

    def assertFileDoesNotExists(self, path):
        """Helper function to check if file does not exists."""
        if Path(path).resolve().is_file():
            raise AssertionError(f"File exists: {path}")

    def test_count_file_lines(self):
        """Test count_file_lines function."""
        mock_file_content = """Line1
        Line2
        Line3
        """

        file = Path("file.txt")
        file.write_text(mock_file_content, encoding="utf-8")
        lines = file_utils.count_file_lines(file.absolute())
        self.assertEqual(lines, 3)
        file.unlink()

    @unittest.mock.patch("openrelik_worker_common.file_utils.uuid4")
    def test_create_output_file(self, mock_uuid):
        """Test create_output_file function."""

        # Generate a mocked uuid.hex()
        h = unittest.mock.MagicMock()
        h.hex = "123456789"
        mock_uuid.return_value = h

        # Test with only an output_path.
        result = file_utils.create_output_file(output_base_path="output_path/")
        self.assertEqual(result.display_name, "123456789")
        self.assertEqual(result.path, "output_path/123456789")

        # Test with an extra file_name.
        result = file_utils.create_output_file(
            output_base_path="output_path/", display_name="test.txt"
        )
        self.assertEqual(result.display_name, "test.txt")

        # Test with an extra file_extension.
        result = file_utils.create_output_file(
            output_base_path="output_path/", display_name="test.txt"
        )
        self.assertEqual(result.display_name, "test.txt")
        self.assertEqual(result.path, "output_path/123456789.txt")

        # Test with an extra explicit file_extension.
        result = file_utils.create_output_file(
            output_base_path="output_path/", display_name="test.txt", extension="test"
        )
        self.assertEqual(result.display_name, "test.txt.test")
        self.assertEqual(result.path, "output_path/123456789.test")

        # Test with an extra source_file_id OutputFile instance.
        source_file_id = file_utils.create_output_file(output_base_path="output_path/")
        result = file_utils.create_output_file(
            output_base_path="output_path/", source_file_id=source_file_id
        )
        self.assertEqual(result.source_file_id.uuid, source_file_id.uuid)

    @unittest.mock.patch("openrelik_worker_common.file_utils.uuid4")
    def test_outputfile_to_dict(self, mock_uuid):
        """Test the outputfile_to_dict function."""
        uuid = unittest.mock.MagicMock()
        uuid.hex = "123456789"
        mock_uuid.return_value = uuid

        parent_outputfile = file_utils.create_output_file(
            output_base_path="output_path/"
        )
        outputfile = file_utils.create_output_file(
            output_base_path="output_path/", source_file_id=parent_outputfile
        )
        result = outputfile.to_dict()
        expected = {
            "uuid": "123456789",
            "display_name": "123456789",
            "extension": "",
            "data_type": None,
            "path": "output_path/123456789",
            "original_path": None,
            "source_file_id": parent_outputfile,
        }
        self.assertDictEqual(result, expected)

    def test_build_file_tree(self):
        """Test the build_file_tree function."""
        test_paths = [
            ["/etc/xxx/sshd_config", "/etc/xxx/sshd_config"],
            ["/etc/xxx_version", "/etc/xxx_version"],
            ["/etc/xxx/ssh_config", "/etc/xxx/ssh_config"],
            ["/etc/../xxx/config", "/xxx/config"],
            ["/etc/../../../../ssh/sshd_config", "/ssh/sshd_config"],
        ]
        files: file_utils.OutputFile = []
        output_path = tempfile.TemporaryDirectory()
        for path in test_paths:
            file = file_utils.create_output_file(
                output_base_path=output_path.name, original_path=path[0]
            )
            open(file.path, "a", encoding="utf-8").close()
            files.append(file)

        file_tree_root = file_utils.build_file_tree(output_path.name, files)

        for path in test_paths:
            self.assertFileExists(
                os.path.join(file_tree_root.name, file_utils.get_relative_path(path[1]))
            )

        file_utils.delete_file_tree(file_tree_root)

        # Test with a non OutputFile instance as files array element
        files = [file_utils.OutputFile, "not-an-OutputFile"]
        self.assertIsNone(file_utils.build_file_tree(output_path, files))

        # Test with an empty files array
        files = []
        self.assertIsNone(file_utils.build_file_tree(output_path, files))

    def test_delete_file_tree(self):
        """Test delete_file_tree function."""
        with self.assertRaises(TypeError):
            file_utils.delete_file_tree("not-a-temp-directory-object")

        tmpdir = tempfile.TemporaryDirectory()
        filepath = os.path.join(tmpdir.name, "testfile")
        open(filepath, "a", encoding="utf-8").close()

        file_utils.delete_file_tree(tmpdir)

        self.assertFileDoesNotExists(filepath)

    def test_get_relative_path(self):
        """Test get_relative_path function."""
        relative_path = file_utils.get_relative_path("/xxx/yyy/test.txt")
        self.assertEqual(relative_path, "xxx/yyy/test.txt")


if __name__ == "__main__":
    unittest.main()
