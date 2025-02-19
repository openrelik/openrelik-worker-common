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
import os
import subprocess
from uuid import uuid4


class BlockDevice:
    def __init__(self, image_path: str):
        pass
        self.image_path = image_path
        self.blkdevice = None
        self.blkdeviceinfo = None
        self.partitions = []
        self.mountpoints = []

        # Setup the loop device
        self._losetup()

        # Parse block device info
        self._blkinfo()

        # Parse partition information
        self._parse_partitions()

    def _losetup(self):
        losetup_command = ["losetup", "--find", "--partscan", "--show", self.image_path]

        process = subprocess.run(
            losetup_command, capture_output=True, check=False, text=True
        )
        if process.returncode == 0:
            self.blkdevice = process.stdout.strip()
        else:
            raise ValueError(
                f"Error: no partitions found or other losetup error: {process.stderr}"
            )

        return None

    def destroy(self):
        losetup_command = ["losetup", "--detach", self.blkdevice]

        process = subprocess.run(
            losetup_command, capture_output=True, check=False, text=True
        )
        if process.returncode == 0:
            print(f"Detached {self.blkdevice} succes!")
            self.blkdevice = process.stdout.strip()
        else:
            raise ValueError(
                f"Error: no partitions found or other losetup error: {process.stderr}"
            )

        return None

    def _blkinfo(self):
        lsblk_command = ["lsblk", "-J", self.blkdevice]

        process = subprocess.run(
            lsblk_command, capture_output=True, check=False, text=True
        )
        if process.returncode == 0:
            self.blkdeviceinfo = json.loads(process.stdout.strip())
        else:
            raise ValueError(
                f"Error: no partitions found or other lsblk error: {process.stderr}"
            )

        return None

    def _parse_partitions(self):
        bd = self.blkdeviceinfo.get("blockdevices")[0]
        if "children" not in bd:
            # TODO(hacktobeer): make this a log instead of print.
            print("No partitions found")
            return
        for children in bd.get("children"):
            self.partitions.append(f"/dev/{children["name"]}")

    def _get_fstype(self, devname: str):
        blkid_command = ["blkid", "-s", "TYPE", "-o", "value", f"{devname}"]

        process = subprocess.run(
            blkid_command, capture_output=True, check=False, text=True
        )
        if process.returncode == 0:
            return process.stdout.strip()
        else:
            raise ValueError(
                f"Error running blkid on {devname}: {process.stderr} {process.stdout}"
            )

    def mount(self, partition_name: str = ""):
        to_mount = []

        if partition_name and partition_name not in self.partitions:
            raise ValueError(
                f"Error running mount: partition name {partition_name} not found"
            )

        if partition_name:
            to_mount.append(partition_name)
        elif not self.partitions:
            to_mount.append(self.blkdevice)
        elif self.partitions:
            to_mount = self.partitions

        if not to_mount:
            raise ValueError(f"Error: nothing to mount")

        for mounttarget in to_mount:
            print(f"Trying to mount {mounttarget}")
            mount_command = ["mount"]
            fstype = self._get_fstype(mounttarget)
            if fstype == "ext4":
                mount_command.extend(["-o", "ro,noload"])
            if fstype == "xfs":
                mount_command.extend(["-o", "ro,norecover"])

            mount_command.append(mounttarget)

            mount_folder = f"/mnt/{uuid4().hex}"
            os.mkdir(mount_folder)

            mount_command.append(mount_folder)

            process = subprocess.run(
                mount_command, capture_output=True, check=False, text=True
            )
            if process.returncode == 0:
                print(f"Mounted {mounttarget} to {mount_folder}")
                self.mountpoints.append(mount_folder)
            else:
                raise ValueError(
                    f"Error running mount: {process.stderr} {process.stdout}"
                )

        return self.mountpoints

    def umount(self):
        for mountpoint in self.mountpoints:
            umount_command = ["umount", f"{mountpoint}"]

            process = subprocess.run(
                umount_command, capture_output=True, check=False, text=True
            )
            if process.returncode == 0:
                print(f"umount {mountpoint} success")
            else:
                raise ValueError(
                    f"Error running umount on {mountpoint}: {process.stderr} {process.stdout}"
                )

    def _calculate_size(self):
        pass
