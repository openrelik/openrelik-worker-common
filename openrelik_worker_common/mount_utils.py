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

import os

def _get_partitions(diskimage_path:str) -> list:
    """List partitions from disk image file.

    This function will list all partitions from a provided disk image file. 

    Args:
        diskimage_path: The path to the disk image file to mount.

    Returns:
        A list of partitions detected with specs.
    """
    # losetup --find --partscan --show disk.img
    # Use https://github.com/genalt/blkinfo
    # Or lsblk -J /dev/loop0
    return [{"name":"vda1","size":"123000"},{"name":"vda2","size":"100"}]

def mount_partitions(diskimage_path:str, all_partitions:bool) -> list:
    """Mount partitions from disk image file.

    This function will mount the biggest or all partitions from a provided disk image file. It will
    return the path where the partitions have been mounted.

    Args:
        diskimage_path: The path to the disk image file to mount.
        all_partitions: If all partitions should be mounted or only the biggest.

    Returns:
        A list of mounted partitions.
    """
    return ["/mnt/tmpdiskpath"]