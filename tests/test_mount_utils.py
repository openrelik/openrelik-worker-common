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
import subprocess
from pathlib import Path
import time

from openrelik_worker_common import mount_utils


class Utils(unittest.TestCase):
    """Test the mount utils functions."""

    def assertFileExists(self, path):
        """Helper function to check if file exists."""
        if not Path(path).resolve().is_file():
            raise AssertionError(f"File does not exist: {path}")

    def test_BlkInfo(self):
        # TODO(hacktobeer): add more tests with blkinfo from GKE Node disks!!
        bd = mount_utils.BlockDevice("./test_data/image_vfat.img")
        self.assertEqual(
            str(bd.blkdeviceinfo),
            "{'blockdevices': [{'name': 'loop0', 'maj:min': '7:0', 'rm': False, 'size': '1M', 'ro': False, 'type': 'loop', 'mountpoints': [None]}]}",
        )
        self.cleanup(bd)

    def test_GetFsTypeVfat(self):
        bd = mount_utils.BlockDevice("./test_data/image_vfat.img")
        self.assertEqual(bd._get_fstype(bd.blkdevice), "vfat")
        self.cleanup(bd)

    def test_GetFsTypeExt4MultiplePartitions(self):
        bd = mount_utils.BlockDevice("./test_data/image_with_partitions.img")
        for partition in bd.partitions:
            t = bd._get_fstype(partition.strip())
            self.assertEqual(t, "ext4")
        self.cleanup(bd)

    def test_LoSetup(self):
        with self.assertRaises(RuntimeError) as e:
            mount_utils.BlockDevice("imagedoesnotexist")
            self.cleanup(bd)

        bd = mount_utils.BlockDevice("./test_data/image_vfat.img")
        self.assertEqual(bd.blkdevice, "/dev/loop0")
        self.cleanup(bd)

    def test_MountNoPartitions(self):
        bd = mount_utils.BlockDevice("./test_data/image_without_partitions.img")
        bd.mountroot = "./mnt"
        bd.mount()

        for folder in bd.mountpoints:
            self.assertFileExists(f"{folder}/testfile.txt")
        self.cleanup(bd)

    def test_ParsePartitions(self):
        bd = mount_utils.BlockDevice("./test_data/image_vfat.img")
        self.assertEqual(bd.partitions, [])
        self.cleanup(bd)

        bd = mount_utils.BlockDevice("./test_data/image_with_partitions.img")
        self.assertEqual(bd.partitions, ["/dev/loop0p1", "/dev/loop0p2"])
        self.cleanup(bd)

    def cleanup(self, bd):
        # Cleanup all mounts and loop devices that might have been setup during the tests.
        if bd:
            bd.umount()
        losetup_command = ["losetup", "-D"]
        process = subprocess.run(
            losetup_command, capture_output=True, check=False, text=True
        )

    @classmethod
    def tearDownClass(self):
        self.cleanup(self, None)


if __name__ == "__main__":
    unittest.main()
