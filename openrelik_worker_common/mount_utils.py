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
import logging
import os
import pathlib
import shutil
import subprocess
import time

from uuid import uuid4


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BlockDevice:
    # TODO(hacktobeer) - add to class comment tool dependencies and explanations
    """BlockDevice provides functionality to map image files to block devices
    and mount them.

    Usage:
        bd = BlockDevice('/folder/path_to_disk_image.dd')
        mountpoints = bd.mount()
        # Do the things you need to do :)
        bd.umount()
    """

    MIN_PARTITION_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB

    def __init__(
        self, image_path: str, min_partition_size: int = MIN_PARTITION_SIZE_BYTES
    ):
        """Initialize BlockDevice class instance.

        Args:
            image_path (str): path to the image file to map and mount.
            min_partition_size (int): minimum partition size, default MIN_PARTITION_SIZE_BYTES
        """
        self.image_path = image_path
        self.min_partition_size = min_partition_size
        self.blkdevice = None
        self.blkdeviceinfo = None
        self.partitions = []
        self.mountpoints = []
        self.mountroot = "/mnt"
        self.supported_fstypes = ["dos", "xfs", "ext2", "ext3", "ext4", "ntfs", "vfat"]
        self.supported_qcowtypes = ["qcow3", "qcow2", "qcow"]

        # Check if image_path exists
        if not pathlib.Path.exists(pathlib.Path(image_path)):
            raise RuntimeError(f"image_path does not exist: {image_path}")

        # Check if required tools are available
        self._required_tools_available()

        # Setup the block device
        ext = pathlib.Path(self.image_path).suffix.strip(".")
        if ext.lower() in self.supported_qcowtypes:
            self.blkdevice = self._nbdsetup()
            print(f"blockdevice: {self.blkdevice}")
        else:
            self.blkdevice = self._losetup()

        # Parse block device info
        self.blkdeviceinfo = self._blkinfo()

        # Parse partition information
        self.partitions = self._parse_partitions()

    def _losetup(self) -> str:
        """Map image file to loopback device using losetup.

        Returns:
            str: block device created by losetup

        Raises:
            RuntimeError: if there was an error running losetup.
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
            blkdevice = process.stdout.strip()
            logger.info(
                f"losetup: success creating {self.blkdevice} for {self.image_path}"
            )
        else:
            logger.error(
                f"losetup: failed creating {self.blkdevice} for {self.image_path}: {process.stderr} {process.stdout}"
            )
            raise RuntimeError(f"Error: {process.stderr} {process.stdout}")

        return blkdevice

    def _get_free_nbd_device(self):
        # TODO(hacktobeer) - implement (redis) locking for block devices!
        return "/dev/nbd0"

    def _nbdsetup(self):
        """Map QCOW image file to NBD device using qemu-nbd and probe partitions.

        Returns:
            str: block device created by qemu-nbd

        Raises:
            RuntimeError: if there was an error running qemu-nbd.
        """
        # Get and lock a free nbd device
        blockdevice = self._get_free_nbd_device()
        nbdsetup_command = [
            "sudo",
            "qemu-nbd",
            "--connect",
            blockdevice,
            self.image_path,
        ]

        process = subprocess.run(
            nbdsetup_command, capture_output=True, check=False, text=True
        )
        if process.returncode == 0:
            logger.info(
                f"qemu-nbd: success creating {self.blkdevice} for {self.image_path}"
            )
        else:
            logger.error(
                f"qemu-nbd: failed creating {self.blkdevice} for {self.image_path}: {process.stderr} {process.stdout}"
            )
            raise RuntimeError(
                f"Error running qemu-nbd: {process.stderr} {process.stdout}"
            )

        # This sleep is needed for qemu-nbd to activate the nbd device
        time.sleep(0.5)

        # Probe partitions
        partprobe_command = [
            "sudo",
            "fdisk",
            "-l",
            blockdevice.strip(),
        ]

        process = subprocess.run(
            partprobe_command, capture_output=True, check=False, text=True
        )
        if process.returncode == 0:
            logger.info(
                f"partprobe: success probing {self.blkdevice} for {self.image_path}"
            )
        else:
            logger.error(
                f"partprobe: failed probing {self.blkdevice} for {self.image_path}: {process.stderr} {process.stdout}"
            )
            raise RuntimeError(
                f"Error partprobe: failed probing: {process.stderr} {process.stdout}"
            )

        return blockdevice

    def _required_tools_available(self) -> bool:
        """Check if required cli tools are available.

        Returns:
            tuple: tuple of return bool and error message
        """
        tools = ["lsblk", "blkid", "mount", "qemu-nbd", "sudo", "partprobe"]
        missing_tools = [tool for tool in tools if not shutil.which(tool)]

        if missing_tools:
            raise RuntimeError(f"Missing required tools: {' '.join(missing_tools)}")

        return True

    def _blkinfo(self) -> dict:
        """Extract device and partition information using blkinfo.

        Returns:
            dict: lsblk json serialized dict

        Raises:
            RuntimeError: if there was an error running lsblk or parsing the json output.
        """
        lsblk_command = ["sudo", "lsblk", "-ba", "-J", self.blkdevice]

        process = subprocess.run(
            lsblk_command, capture_output=True, check=False, text=True
        )
        if process.returncode == 0:
            try:
                lsblk_json_output = process.stdout.strip()
                blkdeviceinfo = json.loads(lsblk_json_output)
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing lsblk json output: {lsblk_json_output}")
                raise RuntimeError(
                    f"Error parsing lsblk json output: {lsblk_json_output}: {e}"
                )
        else:
            logger.error(
                f"Error running lsblk on {self.blkdevice}: {process.stderr} {process.stdout}"
            )
            raise RuntimeError(f"Error lsblk: {process.stderr} {process.stdout}")

        return blkdeviceinfo

    def _parse_partitions(self) -> list:
        """Parse partition information from block device details.

        Returns:
            list[str]: a list of partitions
        """
        partitions = []
        bd = self.blkdeviceinfo.get("blockdevices")[0]
        if "children" not in bd:
            # No partitions on this disk.
            return partitions
        for children in bd.get("children"):
            partition = f"/dev/{children['name']}"
            if self._is_important_partition(children):
                partitions.append(partition)

        return partitions

    def _is_important_partition(self, partition: dict):
        """Decides if we will process a partition. We process the partition if:
        * > 100Mbyte in size
        * contains a filesystem type ext*, dos, vfat, xfs, ntfs

        Args:
            partition (dict): Partition details from lsblk.

        Returns:
            bool: True or False for importance of partition.
        """
        if partition["size"] < self.min_partition_size:
            return False
        fs_type = self._get_fstype(f"/dev/{partition['name']}")
        if fs_type not in self.supported_fstypes:
            return False

        return True

    def _get_fstype(self, devname: str):
        """Analyses the file system type of a block device or partition.

        Args:
            devname (str): block device or partitions device name.

        Returns:
            str: The filesystem type.

        Raises:
          RuntimeError: If there was an error running blkid.
        """
        blkid_command = ["sudo", "blkid", "-s", "TYPE", "-o", "value", f"{devname}"]

        process = subprocess.run(
            blkid_command, capture_output=True, check=False, text=True
        )
        if process.returncode == 0:
            return process.stdout.strip()
        else:
            logger.error(
                f"Error running blkid on {devname}: {process.stderr} {process.stdout}"
            )
            raise RuntimeError(
                f"Error running blkid on {devname}: {process.stderr} {process.stdout}"
            )

    def mount(self, partition_name: str = ""):
        """Mounts a disk or one or more partititions on a mountpoint.

        Args:
            partitions_name (str): Name of specific partition to mount.

        Returns:
            list: A list of paths the disk/partitions have been mounted on.

        Raises:
          RuntimeError: If there as an error running mount.
        """
        to_mount = []

        if partition_name and partition_name not in self.partitions:
            logger.error(
                f"Error running mount: partition name {partition_name} not found"
            )
            raise RuntimeError(
                f"Error running mount: partition name {partition_name} not found"
            )

        if partition_name:
            # Mount the specific partition requested
            to_mount.append(partition_name)
        elif not self.partitions:
            # No partitions found, mount the whole block device
            to_mount.append(self.blkdevice)
        elif self.partitions:
            # Mount all detected partitions
            to_mount = self.partitions

        if not to_mount:
            logger.error(f"Error: nothing to mount")
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
                logger.error(
                    f"Error running mount on {mounttarget}: {process.stderr} {process.stdout}"
                )
                raise RuntimeError(
                    f"Error running mount on {mounttarget}: {process.stderr} {process.stdout}"
                )
        return self.mountpoints

    def _umount_all(self):
        """Umounts all registered mount_points.

        Returns: None

        Raises:
            RuntimeError: If there was an error running umount.
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
                logger.error(
                    f"Error running umount on {mountpoint}: {process.stderr} {process.stdout}"
                )
                raise RuntimeError(
                    f"Error running umount on {mountpoint}: {process.stderr} {process.stdout}"
                )

        for mountpoint in removed:
            self.mountpoints.remove(mountpoint)

    def _detach_device(self):
        """Cleanup block devices for BlockDevice instance.

        Returns: None

        Raises:
            RuntimeError: If there was an error running losetup or qemu-nbd.
        """
        if "nbd" in self.blkdevice:
            command = ["sudo", "qemu-nbd", "--disconnect", self.blkdevice]
        else:
            command = ["sudo", "losetup", "--detach", self.blkdevice]

        process = subprocess.run(command, capture_output=True, check=False, text=True)
        if process.returncode == 0:
            logger.info(f"Detached {self.blkdevice} succes!")
            self.blkdevice = None
        else:
            logger.error(f"Detached {self.blkdevice} failed!")
            raise RuntimeError(
                f"Error detaching block device: {process.stderr} {process.stdout}"
            )

    def umount(self):
        self._umount_all()
        self._detach_device()
