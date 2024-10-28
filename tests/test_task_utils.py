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
from pathlib import Path

from openrelik_worker_common import task_utils
from openrelik_worker_common import file_utils


class Utils(unittest.TestCase):
    """Test the utils helper functions."""

    def test_dict_to_b64_string(self):
        """Test dict_to_b64_string function."""
        result = task_utils.encode_dict_to_base64({"a": "b"})
        self.assertEqual(result, "eyJhIjogImIifQ==")

    def test_get_input_files_input(self):
        """Test get_input_files function for input_files."""
        input_file = []
        input_file.append(file_utils.create_output_file("test/test"))

        result = task_utils.get_input_files(pipe_result=None, input_files=input_file)
        self.assertEqual(result, input_file)

    def test_get_input_files_pipe(self):
        """Test get_input_files function for pipe_result."""
        pipe_input = "eyJvdXRwdXRfZmlsZXMiOiAiL3Rlc3QvdGVzdCJ9"
        result = task_utils.get_input_files(pipe_result=pipe_input, input_files=None)
        expected = "/test/test"
        self.assertEqual(result, expected)

    def test_create_task_result(self):
        """Test create_task_result function."""
        output_files = ["a", "b"]
        workflow_id = "1234456789"
        command = "/bin/command"
        meta = {"key": "value"}

        expected = {
            "output_files": output_files,
            "workflow_id": workflow_id,
            "command": command,
            "meta": meta,
            "file_reports": [],
            "task_report": None,
        }

        result = task_utils.create_task_result(
            output_files=output_files,
            workflow_id=workflow_id,
            command=command,
            meta=meta,
            file_reports=[],
            task_report=None,
        )
        self.assertEqual(result, task_utils.encode_dict_to_base64(expected))


if __name__ == "__main__":
    unittest.main()
