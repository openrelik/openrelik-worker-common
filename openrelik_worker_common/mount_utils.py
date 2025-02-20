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

import json
import logging
import os
import subprocess
from uuid import uuid4

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BlockDevice:
    """BlockDevice provides functionality to map image files to block devices
    and mount them.

    Usage:
        bd = BlockDevice('/folder/path_to_disk_image.dd')
        mountpoints = bd.mount()
        # Do the things you need to do :)
        bd.destroy()
    """

    def __init__(self, image_path: str):
        """Initialize BlockDevice class instance.

        Args:
            image_path (str): path to the image file to map and mount.
        """
        self.image_path = image_path
        self.blkdevice = None
        self.blkdeviceinfo = None
        self.partitions = []
        self.mountpoints = []
        self.mountroot = "/mnt"

        # Setup the loop device
        self._losetup()

        # Parse block device info
        self._blkinfo()

        # Parse partition information
        self._parse_partitions()

    def _losetup(self):
        """Map image file to loopback device using losetup.

        Returns: None
        """
        losetup_command = [
            "sudo",
            "losetup",
            "--find",
            "--partscan",
            "--show",
            self.image_path,
        ]

        process = subprocess.run(
            losetup_command, capture_output=True, check=False, text=True
        )
        if process.returncode == 0:
            self.blkdevice = process.stdout.strip()
        else:
            raise RuntimeError(f"Error: {process.stderr} {process.stdout}")

        return None

    def _blkinfo(self):
        """Extract device and partition information using blkinfo.

        Returns: None
        """
        lsblk_command = ["sudo", "lsblk", "-ba", "-J", self.blkdevice]

        process = subprocess.run(
            lsblk_command, capture_output=True, check=False, text=True
        )
        if process.returncode == 0:
            self.blkdeviceinfo = json.loads(process.stdout.strip())
        else:
            raise RuntimeError(f"Error lsblk:  {process.stderr} {process.stdout}")

        return None

    def _parse_partitions(self):
        """Parse partition information from block device details.

        Returns: None
        """
        bd = self.blkdeviceinfo.get("blockdevices")[0]
        if "children" not in bd:
            # No partitions on this disk.
            return
        for children in bd.get("children"):
            partition = f"/dev/{children["name"]}"
            if self._is_important_partition(children):
                self.partitions.append(partition)

        return None

    def _is_important_partition(self, partition: str):
        """Decides if we will process a partition. We process the partition if:
        * > 100Mbyte in size
        * contains a filesystem type ext*, dos, vfat, xfs, ntfs

        Args:
            partitions (str): Name of the partition.

        Returns:
            bool: True or False for importance of partition.
        """
        if partition["size"] < 100000000:
            return False
        fs_type = self._get_fstype(f"/dev/{partition["name"]}")
        if fs_type not in [
            "dos",
            "xfs",
            "ext2",
            "ext3",
            "ext4",
            "ntfs",
            "vfat",
        ]:
            return False

        return True

    def _get_fstype(self, devname: str):
        """Analyses the file system type of a block device or partition.

        Args:
            dev_name (str): block device or patitions device name.

        Returns:
            str: The filesystem type.
        """
        blkid_command = ["sudo", "blkid", "-s", "TYPE", "-o", "value", f"{devname}"]

        process = subprocess.run(
            blkid_command, capture_output=True, check=False, text=True
        )
        if process.returncode == 0:
            return process.stdout.strip()
        else:
            raise RuntimeError(
                f"Error running blkid on {devname}: {process.stderr} {process.stdout}"
            )

        return None

    def mount(self, partition_name: str = ""):
        """Mounts a disk or one or more partititions on a mountpoint.

        Args:
            partitions_name (str): Nameof specific partition to mount.

        Returns:
            list: A list of paths the disk/partitions have been mounted on.
        """
        to_mount = []

        if partition_name and partition_name not in self.partitions:
            raise RuntimeError(
                f"Error running mount: partition name {partition_name} not found"
            )

        if partition_name:
            to_mount.append(partition_name)
        elif not self.partitions:
            to_mount.append(self.blkdevice)
        elif self.partitions:
            to_mount = self.partitions

        if not to_mount:
            raise RuntimeError(f"Error: nothing to mount")

        for mounttarget in to_mount:
            logger.info(f"Trying to mount {mounttarget}")
            mount_command = ["sudo", "mount"]
            fstype = self._get_fstype(mounttarget)
            if fstype == "xfs":
                mount_command.extend(["-o", "ro,norecovery"])
            elif fstype in ["ext2", "ext3", "ext4"]:
                mount_command.extend(["-o", "ro,noload"])
            else:
                mount_command.extend(["-o", "ro"])

            mount_command.append(mounttarget)

            mount_folder = f"{self.mountroot}/{uuid4().hex}"
            os.makedirs(mount_folder)

            mount_command.append(mount_folder)

            process = subprocess.run(
                mount_command, capture_output=True, check=False, text=True
            )
            if process.returncode == 0:
                logger.info(f"Mounted {mounttarget} to {mount_folder}")
                self.mountpoints.append(mount_folder)
            else:
                raise RuntimeError(
                    f"Error running mount on {mounttarget}: {process.stderr} {process.stdout}"
                )
        return self.mountpoints

    def umount(self):
        """Umounts all registered mount_points.

        Returns: None
        """
        removed = []
        for mountpoint in self.mountpoints:
            umount_command = ["sudo", "umount", f"{mountpoint}"]

            process = subprocess.run(
                umount_command, capture_output=True, check=False, text=True
            )
            if process.returncode == 0:
                logger.info(f"umount {mountpoint} success")
                os.rmdir(mountpoint)
                removed.append(mountpoint)
            else:
                raise RuntimeError(
                    f"Error running umount on {mountpoint}: {process.stderr} {process.stdout}"
                )

        for mountpoint in removed:
            self.mountpoints.remove(mountpoint)

        return None

    def destroy(self):
        """Cleanup mount points and loopmount devices for BlockDevice instance.

        Returns: None
        """
        self.umount()

        losetup_command = ["sudo", "losetup", "--detach", self.blkdevice]
        process = subprocess.run(
            losetup_command, capture_output=True, check=False, text=True
        )
        if process.returncode == 0:
            logger.info(f"Detached {self.blkdevice} succes!")
            self.blkdevice = process.stdout.strip()
        else:
            raise RuntimeError(
                f"Error losetup detach: {process.stderr} {process.stdout}"
            )

        return None
