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

from __future__ import annotations  # support forward looking type hints

import base64
import json
import os
import subprocess
import tempfile

from pathlib import Path, PurePath
from typing import Optional
from uuid import uuid4


def dict_to_b64_string(dict_to_encode: dict) -> str:
    """Encode a dictionary to a base64-encoded string.

    Args:
        dict_to_encode: The dictionary to encode.

    Returns:
        The base64-encoded string.
    """
    json_string = json.dumps(dict_to_encode)
    return base64.b64encode(json_string.encode("utf-8")).decode("utf-8")


def count_lines_in_file(file_path):
    """Count the number of lines in a file.

    Args:
        file_path: The path to the file.

    Returns:
        The number of lines in the file.
    """
    wc = subprocess.check_output(["wc", "-l", file_path])
    return int(wc.decode("utf-8").split()[0])


def get_input_files(pipe_result: str, input_files: list) -> list:
    """Set the input files for the task.

    Args:
        pipe_result: The result of the previous task (from Celery).
        input_files: The input files for the task.

    Returns:
        The input files for the task.
    """
    if pipe_result:
        result_string = base64.b64decode(pipe_result.encode("utf-8")).decode("utf-8")
        result_dict = json.loads(result_string)
        input_files = result_dict.get("output_files")
    return input_files


def task_result(
    output_files: list, workflow_id: str, command: str, meta: dict = None
) -> str:
    """Create a task result dictionary and encode it to a base64 string.

    Args:
        output_files: List of output file dictionaries.
        workflow_id: ID of the workflow.
        command: The command used to execute the task.
        meta: Additional metadata for the task (optional).

    Returns:
        Base64-encoded string representing the task result.
    """
    result = {
        "output_files": output_files,
        "workflow_id": workflow_id,
        "command": command,
        "meta": meta,
    }
    return dict_to_b64_string(result)


class OutputFile:
    """Represents an output file.

    Attributes:
        uuid: Unique identifier for the file.
        display_name: Display name for the file.
        data_type: Data type of the file.
        path: The full path to the file.
        original_path: The full original path to the file.
        source_file_id: The OutputFile this file belongs to.
    """

    def __init__(
        self,
        output_path: str,
        filename: Optional[str] = None,
        data_type: Optional[str] = None,
        original_path: Optional[str] = None,
        source_file_id: Optional[OutputFile] = None,
    ):
        """Initialize an OutputFile object.

        Args:
            output_path: The path to the output directory.
            filename: The name of the output file (optional, UUID if missing).
            data_type: The data type of the output file (optional).
            orignal_path: The orignal path of the file (optional).
            source_file_id: The OutputFile this file belongs to (optional).
        """
        self.uuid = uuid4().hex
        self.display_name = filename if filename else self.uuid
        self.data_type = data_type
        self.path = os.path.join(output_path, self.uuid)
        self.original_path = original_path
        self.source_file_id = source_file_id

    def to_dict(self):
        """
        Return a dictionary representation of the OutputFile object.
        This is what the mediator server gets and uses to create a File in the database.

        Returns:
            A dictionary containing the attributes of the OutputFile object.
        """
        return {
            "display_name": self.display_name,
            "data_type": self.data_type,
            "uuid": self.uuid,
            "path": self.path,
            "original_path": self.original_path,
            "source_file_id": self.source_file_id,
        }


def create_output_file(
    output_path: str,
    filename: Optional[str] = None,
    data_type: Optional[str] = "openrelik:worker:file:generic",
    original_path: Optional[str] = None,
    source_file_id: Optional[OutputFile] = None,
) -> OutputFile:
    """Creates and returns an OutputFile object.

    Args:
        output_path: The path to the output directory.
        filename: The name of the output file (optional).
        data_type: The data type of the output file (optional).
        original_path: The orignal path of the file (optional).
        source_file_id: The OutputFile this file belongs to (optional).

    Returns:
        An OutputFile object.
    """
    return OutputFile(output_path, filename, data_type, original_path, source_file_id)


def get_path_without_root(path: str) -> str:
    """Converts a full path to relative path without the root.

    Args:
        path: A full path.

    Returns:
        A relative path without the root.
    """
    path = PurePath(path)
    return str(path.relative_to(path.anchor))


def build_file_tree(
    output_path: str, files: list[OutputFile]
) -> tempfile.TemporaryDirectory | None:
    """Creates the original file tree structure from a list of OutputFiles.

    Args:
        output_path: Path to the OpenRelik output directory.
        files: A list of OutPutFile instances.

    Returns:
        The root path of the file tree as a TemporaryDirectory or None.
    """
    if not files or not all(isinstance(file, OutputFile) for file in files):
        return None

    tree_root = tempfile.TemporaryDirectory(dir=output_path, delete=False)

    for file in files:
        normalized_path = os.path.normpath(file.original_path)
        original_filename = Path(normalized_path).name
        original_folder = Path(normalized_path).parent
        relative_original_folder = get_path_without_root(original_folder)
        # Create complete folder structure.
        try:
            tmp_full_path = os.path.join(tree_root.name, relative_original_folder)

            # Ensure that the constructed path is within the system's temporary
            # directory, preventing attempts to write files outside of it.
            if tree_root.name not in tmp_full_path:
                raise PermissionError(
                    f"Folder {tmp_full_path} not in OpenRelik output_path: {output_path}"
                )

            os.makedirs(tmp_full_path)
        except FileExistsError:
            pass
        # Create hardlink to file
        os.link(
            file.path,
            os.path.join(tree_root.name, relative_original_folder, original_filename),
        )

    return tree_root


def delete_file_tree(root_path: tempfile.TemporaryDirectory):
    """Delete a temporary file tree folder structure.

    Args:
        root_path: TemporaryDirectory root object of file tree structure.

    Returns: None
    Raises: TypeError
    """
    if not isinstance(root_path, tempfile.TemporaryDirectory):
        raise TypeError("Root path is not a TemporaryDirectory object!")

    root_path.cleanup()
