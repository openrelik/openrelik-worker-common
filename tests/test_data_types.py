import unittest

from openrelik_worker_common import data_types
from openrelik_worker_common import task_utils


class TestDataTypes(unittest.TestCase):
    """Test the OpenRelik data types."""

    def test_datatype_str_comparision(self):
        """Test string comparison of data types."""
        self.assertEqual(data_types.DataType.DISK_IMAGE_QCOW, "file:diskimage:qcow")

    def test_datatype_filtering(self):
        """Test glob comparision of data types."""
        input_files = [
            {"name": "testfile.qcow", "data_type": "container_explorer:file:disk:qcow"},
            {"name": "testfile.bin", "data_type": "hayabusa:file:binary"},
        ]

        filter_dict = {"data_types": ["*"]}
        compatible = task_utils.filter_compatible_files(input_files, filter_dict)
        self.assertEqual(len(compatible), 2)

        filter_dict = {"data_types": ["container_explorer:*"]}
        compatible = task_utils.filter_compatible_files(input_files, filter_dict)
        self.assertEqual(len(compatible), 1)

        filter_dict = {"data_types": ["*:disk:*"]}
        compatible = task_utils.filter_compatible_files(input_files, filter_dict)
        self.assertEqual(len(compatible), 1)

        filter_dict = {"data_types": ["*:binary"]}
        compatible = task_utils.filter_compatible_files(input_files, filter_dict)
        self.assertEqual(len(compatible), 1)


if __name__ == "__main__":
    unittest.main()
