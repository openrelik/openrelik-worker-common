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

import unittest
import subprocess
from fakeredis import FakeStrictRedis
from pathlib import Path
from redlock import Redlock
from unittest.mock import patch

from openrelik_worker_common import mount_utils


class Utils(unittest.TestCase):
    """Test the mount utils functions."""

    mountroot = "./mnt"

    redis_client = None

    @classmethod
    def setUpClass(self):
        # Setup fake redis client
        self.redis_client = FakeStrictRedis(server_type="redis")

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
        bd.setup()
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
            mount_utils.BlockDevice("./test_data/image_vfat.img").setup()
        mock_subprocess.return_value = subprocess.CompletedProcess(
            args=[], stderr="device not found /dev/loop0", returncode=1
        )
        with self.assertRaises(RuntimeError) as e:
            mount_utils.BlockDevice("./test_data/image_vfat.img").setup()
        self.assertEqual(
            str(e.exception),
            "Error lsblk: device not found /dev/loop0 None",
        )

    def test_GetFsTypeVfat(self):
        bd = mount_utils.BlockDevice("./test_data/image_vfat.img")
        bd.setup()
        self.assertEqual(bd._get_fstype(bd.blkdevice), "vfat")

    def test_GetFsTypeExt4MultiplePartitions(self):
        bd = mount_utils.BlockDevice("./test_data/image_with_partitions.img")
        bd.setup()
        for partition in bd.partitions:
            t = bd._get_fstype(partition.strip())
            self.assertEqual(t, "ext4")

    @patch("openrelik_worker_common.mount_utils.BlockDevice._get_hostname")
    @patch("openrelik_worker_common.mount_utils.Redlock")
    @patch.object(mount_utils.BlockDevice, "_is_important_partition")
    def test_GetFreeNbDevice(self, mock_partition, mock_redlock, mock_get_hostname):
        mock_partition.return_value = True
        mock_redlock.return_value = Redlock(
            [
                self.redis_client,
            ]
        )
        mock_get_hostname.return_value = "random_host_name"

        bd = mount_utils.BlockDevice("./test_data/image_with_partitions.qcow2")
        bd.setup()
        self.assertEqual(bd.blkdevice, "/dev/nbd0")
        self.assertIsNotNone(bd.redlock)
        self.assertEqual(
            self.redis_client.get("random_host_name-/dev/nbd0"), bd.redlock.key
        )

    @patch("openrelik_worker_common.mount_utils.socket.gethostname")
    def test_GetHostNameSocket(self, mock_socket):
        mock_socket.return_value = "myhostname"
        hostname = mount_utils.BlockDevice._get_hostname(None)
        self.assertEqual(hostname, "myhostname")

    @patch("openrelik_worker_common.mount_utils.os.environ.get")
    def test_GetHostNameENV(self, mock_env):
        mock_env.return_value = "mynodename"
        hostname = mount_utils.BlockDevice._get_hostname(None)
        self.assertEqual(hostname, "mynodename")

    def test_NbdSetup(self):
        bd = mount_utils.BlockDevice("./test_data/image_vfat.img")
        bd.setup()
        self.assertEqual(bd.blkdevice, "/dev/loop0")

    def test_LoSetup(self):
        bd = mount_utils.BlockDevice("./test_data/image_vfat.img")
        bd.setup()
        self.assertEqual(bd.blkdevice, "/dev/loop0")

    def test_LoSetupFail(self):
        with self.assertRaises(RuntimeError) as e:
            mount_utils.BlockDevice("imagedoesnotexist").setup()
        self.assertEqual(
            str(e.exception),
            "image_path does not exist: imagedoesnotexist",
        )

    def test_MountNoPartitions(self):
        bd = mount_utils.BlockDevice("./test_data/image_without_partitions.img")
        bd.setup()
        bd.mountroot = self.mountroot
        bd.mount()

        for folder in bd.mountpoints:
            self.assertFileExists(f"{folder}/testfile.txt")
        bd.umount()

    @patch.object(mount_utils.BlockDevice, "_is_important_partition")
    def test_MountWithPartitions(self, mock_important):
        mock_important.return_value = True

        bd = mount_utils.BlockDevice("./test_data/image_with_partitions.img")
        bd.setup()
        bd.mountroot = self.mountroot
        bd.mount()

        for folder in bd.mountpoints:
            self.assertFileExists(f"{folder}/testfile.txt")

        bd.umount()

    @patch.object(mount_utils.BlockDevice, "_is_important_partition")
    @patch.object(mount_utils.BlockDevice, "_get_free_nbd_device")
    def test_MountWithQCOW2Partitions(self, mock_nbd, mock_important):
        mock_important.return_value = True
        mock_nbd.return_value = "/dev/nbd0"

        bd = mount_utils.BlockDevice("./test_data/image_with_partitions.qcow2")
        bd.setup()
        bd.mountroot = self.mountroot
        bd.mount()

        for folder in bd.mountpoints:
            self.assertFileExists(f"{folder}/testfile.txt")

        bd.umount()

    @patch("openrelik_worker_common.mount_utils.subprocess.run")
    @patch("openrelik_worker_common.mount_utils.pathlib.Path.exists")
    @patch.object(mount_utils.BlockDevice, "_get_free_nbd_device")
    def test_MountWithQCOW2Error(self, mock_nbd, mock_pathlib, mock_subprocess):
        mock_subprocess.return_value = subprocess.CompletedProcess(
            args=[], stdout="not a qcow file", returncode=1
        )
        mock_pathlib.returnvalue = True
        mock_nbd.return_value = "/dev/nbd0"

        with self.assertRaises(RuntimeError) as e:
            mount_utils.BlockDevice("./test_data/nonexistent_qcow2_image.qcow2").setup()
        self.assertEqual(
            str(e.exception),
            "Error running qemu-nbd: None not a qcow file",
        )

    @patch.object(mount_utils.BlockDevice, "_is_important_partition")
    def test_MountWithNonExistingPartition(self, mock_important):
        mock_important.return_value = True

        bd = mount_utils.BlockDevice("./test_data/image_with_partitions.img")
        bd.setup()
        bd.mountroot = self.mountroot

        with self.assertRaises(RuntimeError) as e:
            bd.mount(partition_name="/dev/loop0p999")
        self.assertEqual(
            str(e.exception),
            "Error running mount: partition name /dev/loop0p999 not found",
        )

        bd.umount()

    @patch.object(mount_utils.BlockDevice, "_is_important_partition")
    def test_MountWithNamedPartition(self, mock_important):
        mock_important.return_value = True

        bd = mount_utils.BlockDevice("./test_data/image_with_partitions.img")
        bd.setup()
        bd.mountroot = self.mountroot
        bd.mount(partition_name="/dev/loop0p1")

        for folder in bd.mountpoints:
            self.assertFileExists(f"{folder}/testfile.txt")

        bd.umount()

    def test_MountNothingTodo(self):
        bd = mount_utils.BlockDevice("./test_data/image_with_partitions.img")
        bd.setup()

        bd.blkdevice = "/dev/doesnotexist"
        bd.partitions = ""

        with self.assertRaises(RuntimeError) as e:
            bd.mount()
        self.assertEqual(
            str(e.exception),
            "Error running blkid on /dev/doesnotexist:  ",
        )

    @patch.object(mount_utils.BlockDevice, "_is_important_partition")
    def test_ParsePartitionsEmpty(self, mock_important):
        mock_important.return_value = True

        bd = mount_utils.BlockDevice("./test_data/image_vfat.img")
        bd.setup()
        self.assertEqual(bd.partitions, [])

    @patch.object(mount_utils.BlockDevice, "_is_important_partition")
    def test_ParsePartitions(self, mock_important):
        mock_important.return_value = True

        bd = mount_utils.BlockDevice("./test_data/image_with_partitions.img")
        bd.setup()
        self.assertEqual(bd.partitions, ["/dev/loop0p1", "/dev/loop0p2"])

    def test_Umount(self):
        bd = mount_utils.BlockDevice("./test_data/image_vfat.img")
        bd.setup()
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
        bd.setup()
        partition = {"name": "loop0p1", "size": 1000000000}

        mock_fstype.return_value = "ext4"
        self.assertTrue(bd._is_important_partition(partition))

        mock_fstype.return_value = "typenotsupported"
        self.assertFalse(bd._is_important_partition(partition))

    @patch("openrelik_worker_common.mount_utils.shutil.which")
    def test_RequiredToolsAvailable_all_tools_available(self, mock_which):
        mock_which.return_value = "/path/to/tool"
        result = mount_utils.BlockDevice._required_tools_available(None)
        self.assertTrue(result)

    @patch("openrelik_worker_common.mount_utils.shutil.which")
    def test_RequiredToolsAvailable_no_tools_available(self, mock_which):
        mock_which.return_value = None
        with self.assertRaises(
            RuntimeError,
        ) as e:
            mount_utils.BlockDevice._required_tools_available(None)
        self.assertEqual(
            str(e.exception),
            "Missing required tools: lsblk blkid mount qemu-nbd sudo",
        )

    @patch("openrelik_worker_common.mount_utils.shutil.which")
    def test_RequiredToolsAvailable__some_tools_available(self, mock_which):
        mock_which.side_effect = [
            "/path/to/lsblk",
            None,
            "/path/to/mount",
            None,
            None,
            "/path/to/partprobe",
        ]
        with self.assertRaises(
            RuntimeError,
        ) as e:
            mount_utils.BlockDevice._required_tools_available(None)
        self.assertEqual(
            str(e.exception), "Missing required tools: blkid qemu-nbd sudo"
        )

    def tearDown(self):
        # Cleanup any left over loop/nbd devices
        losetup_command = ["sudo", "losetup", "-D"]
        subprocess.run(losetup_command, capture_output=False, check=False)
        nbd_command = ["sudo", "qemu-nbd", "-d", "/dev/nbd0"]
        subprocess.run(nbd_command, capture_output=False, check=False)

    @classmethod
    def tearDownClass(self):
        pass


if __name__ == "__main__":
    unittest.main()
