import unittest
import unittest.mock
from pathlib import Path

from openrelik_worker_common import utils


class Utils(unittest.TestCase):

    def test_dict_to_b64_string(self):
        result = utils.dict_to_b64_string({"a": "b"})
        self.assertEqual(result, "eyJhIjogImIifQ==")

    def test_count_lines_in_file(self):
        mock_file_content = """Line1
        Line2
        Line3
        """

        file = Path('file.txt')
        file.write_text(mock_file_content, encoding="utf-8")
        lines = utils.count_lines_in_file(file.absolute())
        self.assertEqual(lines, 3)
        file.unlink()

    def test_get_input_files_input(self):
        input_file = []
        input_file.append(utils.create_output_file("test/test"))

        result = utils.get_input_files(pipe_result=None,
                                       input_files=input_file)
        self.assertEqual(result, input_file)

    def test_get_input_files_pipe(self):
        pipe_input = "eyJvdXRwdXRfZmlsZXMiOiAiL3Rlc3QvdGVzdCJ9"
        result = utils.get_input_files(pipe_result=pipe_input,
                                       input_files=None)
        expected = "/test/test"
        self.assertEqual(result, expected)

    def test_task_result(self):
        output_files = ["a", "b"]
        workflow_id = "1234456789"
        command = "/bin/command"
        meta = {"key": "value"}

        expected = {
            "output_files": output_files,
            "workflow_id": workflow_id,
            "command": command,
            "meta": meta,
        }

        result = utils.task_result(output_files=output_files,
                                   workflow_id=workflow_id,
                                   command=command,
                                   meta=meta)
        self.assertEqual(result, utils.dict_to_b64_string(expected))

    @unittest.mock.patch("openrelik_worker_common.utils.uuid4")
    def test_create_output_file(self, mock_uuid):
        h = unittest.mock.MagicMock()
        h.hex = "123456789"
        mock_uuid.return_value = h

        result = utils.create_output_file(output_path="test/")
        self.assertEqual(result.display_name, "123456789")
        self.assertEqual(result.path, "test/123456789")

        result = utils.create_output_file(output_path="test/",
                                          filename="test.txt")
        self.assertEqual(result.display_name, "test.txt")
        self.assertEqual(result.path, "test/123456789")

        result = utils.create_output_file(output_path="test/",
                                          filename="test",
                                          file_extension="txt")
        self.assertEqual(result.display_name, "test.txt")
        self.assertEqual(result.path, "test/123456789")


if __name__ == '__main__':
    unittest.main()
