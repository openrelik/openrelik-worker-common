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
import subprocess
import time
from uuid import uuid4


def extract_7zip(input_path: str, output_folder: str, log_file: str) -> str:
    """Unpacks an archive with 7zip.

    Args:
      input_path(string): Input archive path.
      output_folder(string): OpenRelik output_folder.
      log_file(string): Log file path.

    Return:
      command(string): The executed command string.
      export_folder: Root folder path to the unpacked archive.
    """
    export_folder = os.path.join(output_folder, uuid4().hex)
    os.mkdir(export_folder)

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
        raise RuntimeError("7zip execution error.")

    return (command_string, export_folder)
