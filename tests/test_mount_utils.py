# Copyright 2025 Google LLC
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

import json
import unittest
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

from openrelik_worker_common import mount_utils


class Utils(unittest.TestCase):
    """Test the mount utils functions."""

    mountroot = "./mnt"

    def SetUp(self):
        pass

    def assertFileExists(self, path):
        """Helper function to check if file exists."""
        if not Path(path).resolve().is_file():
            raise AssertionError(f"File does not exist: {path}")

    def assertFileDoesNotExists(self, path):
        """Helper function to check if file does not exists."""
        if Path(path).resolve().is_file():
            raise AssertionError(f"File exists: {path}")

    def test_BlkInfo(self):
        bd = mount_utils.BlockDevice("./test_data/image_vfat.img")
        self.assertEqual(
            str(bd.blkdeviceinfo),
            "{'blockdevices': [{'name': 'loop0', 'maj:min': '7:0', 'rm': False, 'size': 1048576, 'ro': False, 'type': 'loop', 'mountpoints': [None]}]}",
        )

    @patch("openrelik_worker_common.mount_utils.BlockDevice._losetup")
    @patch("openrelik_worker_common.mount_utils.subprocess.run")
    def test_BlkInfoError(self, mock_subprocess, mock_losetup):
        mock_losetup.return_value = "/dev/loop0"
        mock_subprocess.return_value = subprocess.CompletedProcess(
            args=[], stdout="this is not valid JSON", returncode=0
        )

        with self.assertRaises(RuntimeError):
            mount_utils.BlockDevice("./test_data/image_vfat.img")

        mock_subprocess.return_value = subprocess.CompletedProcess(
            args=[], stderr="device not found", returncode=1
        )
        with self.assertRaisesRegex(RuntimeError, "Error lsblk: device not found"):
            mount_utils.BlockDevice("./test_data/image_vfat.img")

    def test_GetFsTypeVfat(self):
        bd = mount_utils.BlockDevice("./test_data/image_vfat.img")
        self.assertEqual(bd._get_fstype(bd.blkdevice), "vfat")

    def test_GetFsTypeExt4MultiplePartitions(self):
        bd = mount_utils.BlockDevice("./test_data/image_with_partitions.img")
        for partition in bd.partitions:
            t = bd._get_fstype(partition.strip())
            self.assertEqual(t, "ext4")

    def test_LoSetup(self):
        bd = mount_utils.BlockDevice("./test_data/image_vfat.img")
        self.assertEqual(bd.blkdevice, "/dev/loop0")

    def test_LoSetupFail(self):
        with self.assertRaisesRegex(
            RuntimeError,
            "Error: losetup: imagedoesnotexist: failed to set up loop device: No such file or directory",
        ) as e:
            mount_utils.BlockDevice("imagedoesnotexist")

    def test_MountNoPartitions(self):
        bd = mount_utils.BlockDevice("./test_data/image_without_partitions.img")
        bd.mountroot = self.mountroot
        bd.mount()

        for folder in bd.mountpoints:
            self.assertFileExists(f"{folder}/testfile.txt")
        bd.umount()

    @patch.object(mount_utils.BlockDevice, "_is_important_partition")
    def test_MountWithPartitions(self, mock_important):
        mock_important.return_value = True

        bd = mount_utils.BlockDevice("./test_data/image_with_partitions.img")
        bd.mountroot = self.mountroot
        bd.mount()

        for folder in bd.mountpoints:
            self.assertFileExists(f"{folder}/testfile.txt")

        bd.umount()

    @patch.object(mount_utils.BlockDevice, "_is_important_partition")
    def test_MountWithNonExistingPartition(self, mock_important):
        mock_important.return_value = True

        bd = mount_utils.BlockDevice("./test_data/image_with_partitions.img")
        bd.mountroot = self.mountroot

        with self.assertRaisesRegex(
            RuntimeError, "Error running mount: partition name /dev/loop0p999 not found"
        ) as e:
            bd.mount(partition_name="/dev/loop0p999")

        bd.umount()

    @patch.object(mount_utils.BlockDevice, "_is_important_partition")
    def test_MountWithNamedPartition(self, mock_important):
        mock_important.return_value = True

        bd = mount_utils.BlockDevice("./test_data/image_with_partitions.img")
        bd.mountroot = self.mountroot
        bd.mount(partition_name="/dev/loop0p1")

        for folder in bd.mountpoints:
            self.assertFileExists(f"{folder}/testfile.txt")

        bd.umount()

    def test_MountNothingTodo(self):
        bd = mount_utils.BlockDevice("./test_data/image_with_partitions.img")

        bd.blkdevice = "/dev/doesnotexist"
        bd.partitions = ""

        with self.assertRaisesRegex(
            RuntimeError, "Error running blkid on /dev/doesnotexist"
        ) as e:
            bd.mount()

    @patch.object(mount_utils.BlockDevice, "_is_important_partition")
    def test_ParsePartitionsEmpty(self, mock_important):
        mock_important.return_value = True

        bd = mount_utils.BlockDevice("./test_data/image_vfat.img")
        self.assertEqual(bd.partitions, [])

    @patch.object(mount_utils.BlockDevice, "_is_important_partition")
    def test_ParsePartitions(self, mock_important):
        mock_important.return_value = True

        bd = mount_utils.BlockDevice("./test_data/image_with_partitions.img")
        self.assertEqual(bd.partitions, ["/dev/loop0p1", "/dev/loop0p2"])

    def test_Umount(self):
        bd = mount_utils.BlockDevice("./test_data/image_vfat.img")
        bd.mountroot = self.mountroot
        bd.mount()
        mountpoints = bd.mountpoints.copy()
        bd.umount()

        self.assertEqual(bd.mountpoints, [])
        for folder in mountpoints:
            self.assertFileDoesNotExists(folder)

    @patch.object(mount_utils.BlockDevice, "_get_fstype")
    def test_IsImportantPartition(self, mock_fstype):
        bd = mount_utils.BlockDevice("./test_data/image_vfat.img")
        partition = {"name": "loop0p1", "size": 1000000000}

        mock_fstype.return_value = "ext4"
        self.assertTrue(bd._is_important_partition(partition))

        mock_fstype.return_value = "typenotsupported"
        self.assertFalse(bd._is_important_partition(partition))

    @patch("openrelik_worker_common.mount_utils.which")
    def test_RequiredToolsAvailable_all_tools_available(self, mock_which):
        mock_which.return_value = "/path/to/tool"
        result = mount_utils.BlockDevice._required_tools_available(None)
        self.assertTrue(result[0])
        self.assertEqual(result[1], "")

    @patch("openrelik_worker_common.mount_utils.which")
    def test_RequiredToolsAvailable_no_tools_available(self, mock_which):
        mock_which.return_value = None
        result = mount_utils.BlockDevice._required_tools_available(None)
        self.assertFalse(result[0])
        self.assertIn("lsblk", result[1])
        self.assertIn("blkid", result[1])
        self.assertIn("mount", result[1])
        self.assertRaises(RuntimeError)

    @patch("openrelik_worker_common.mount_utils.which")
    def test_RequiredToolsAvailable__some_tools_available(self, mock_which):
        mock_which.side_effect = ["/path/to/lsblk", None, "/path/to/mount"]
        result = mount_utils.BlockDevice._required_tools_available(None)
        self.assertFalse(result[0])
        self.assertIn("blkid", result[1])

    def tearDown(self):
        losetup_command = ["sudo", "losetup", "-D"]
        process = subprocess.run(losetup_command, capture_output=False, check=False)


if __name__ == "__main__":
    unittest.main()
