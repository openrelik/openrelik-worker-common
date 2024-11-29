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
"""Helper methods for archives."""

import os
import shutil
import subprocess
from uuid import uuid4


def extract_archive(input_file: dict, output_folder: str, log_file: str) -> str:
    """Unpacks an archive.

    Args:
      input_file(dict): Input file dict.
      output_folder(string): OpenRelik output_folder.
      log_file(string): Log file path.

    Return:
      command(string): The executed command string.
      export_folder: Root folder path to the unpacked archive.
    """
    input_path = input_file.get("path")
    input_filename = input_file.get("display_name")

    if not shutil.which("7z"):
        raise RuntimeError("7z executable not found!")

    export_folder = os.path.join(output_folder, uuid4().hex)
    os.mkdir(export_folder)

    if input_filename.endswith((".tgz", ".tar.gz")):
        command = [
            "tar",
            "-vxzf",
            input_path,
            "-C",
            f"{export_folder}",
        ]
    else:
        command = [
            "7z",
            "x",
            input_path,
            f"-o{export_folder}",
        ]

    command_string = " ".join(command)
    with open(log_file, "wb") as out:
        ret = subprocess.call(command, stdout=out, stderr=out)
    if ret != 0:
        raise RuntimeError("7zip or tar execution error.")

    return (command_string, export_folder)

import shutil
import os

def create_archive(input_folder_path: str, archive_path: str, delete_input: bool = False):
    """
    Zips the contents of a folder into a .zip archive and (optionally) deletes the original folder.

    Args:
        input_folder_path (str): Path to the folder to be zipped.
        archive_path (str): Path (including filename) where the zip file will be saved.
        delete_input (boolean): True if content in folder_path needs to be deleted after archive creation.
    
    Returns:
        str: Path to the created zip file.
    """
    if not os.path.isdir(input_folder_path):
        raise ValueError(f"The folder {input_folder_path} does not exist.")
    
    zip_file = shutil.make_archive(archive_path, 'zip', input_folder_path)
    
    if delete_input:
        shutil.rmtree(input_folder_path)
    
    return zip_file
