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

import base64
import fnmatch
import json


def encode_dict_to_base64(dict_to_encode: dict) -> str:
    """Encode a dictionary to a base64-encoded string.

    Args:
        dict_to_encode: The dictionary to encode.

    Returns:
        The base64-encoded string.
    """
    json_string = json.dumps(dict_to_encode)
    return base64.b64encode(json_string.encode("utf-8")).decode("utf-8")


def get_input_files(pipe_result: str, input_files: list[dict], filter: dict = None) -> list[dict]:
    """Prepares the input files for the task.

    Determines the appropriate input files by checking for results from a
    previous task and then applies any specified file filtering.

    Args:
        previous_task_result: The result of the previous task (from Celery).
        input_files: The initial input files for the task.
        file_filter: A dictionary specifying filter criteria for the input files.

    Returns:
        A list of compatible input files for the task.
    """
    if pipe_result:
        result_string = base64.b64decode(pipe_result.encode("utf-8")).decode("utf-8")
        result_dict = json.loads(result_string)
        input_files = result_dict.get("output_files", [])

    if filter:
        input_files = filter_compatible_files(input_files, filter)

    return input_files


def create_task_result(
    output_files: list[dict],
    workflow_id: str,
    command: str = None,
    meta: dict = None,
    task_logs: list[dict] = [],
    file_reports: list[dict] = [],
    task_report: dict = None,
) -> str:
    """Create a task result dictionary and encode it to a base64 string.

    Args:
        output_files: List of output file dictionaries.
        workflow_id: ID of the workflow.
        command: The command used to execute the task.
        meta: Additional metadata for the task (optional).
        task_logs: List of task log file dictionaries.
        file_reports: List of file report dictionaries.
        task_report: A dictionary representing a task report.

    Returns:
        Base64-encoded string representing the task result.
    """
    result = {
        "output_files": output_files,
        "workflow_id": workflow_id,
        "command": command,
        "meta": meta,
        "task_logs": task_logs,
        "file_reports": file_reports,
        "task_report": task_report,
    }
    return encode_dict_to_base64(result)


def filter_compatible_files(input_files: list[dict], filter_dict: dict) -> list[dict]:
    """
    Filters a list of files based on compatibility with a given filter,
    including partial matching.

    Args:
      input_files: A list of file dictionaries, each containing keys
                   "data_type", "mime-type", "filename", and "extension".
      filter_dict: A dictionary specifying the filter criteria with keys
                   "data_types", "mime-types", and "extensions".

    Returns:
      A list of compatible file dictionaries.
    """
    compatible_files = []
    for file_data in input_files:
        if file_data.get("data_type") is not None and any(
            fnmatch.fnmatch(file_data.get("data_type"), pattern)
            for pattern in (filter_dict.get("data_types") or [])
        ):
            compatible_files.append(file_data)
        elif file_data.get("mime_type") is not None and any(
            fnmatch.fnmatch(file_data.get("mime_type"), pattern)
            for pattern in (filter_dict.get("mime_types") or [])
        ):
            compatible_files.append(file_data)
        elif file_data.get("display_name") is not None and any(
            fnmatch.fnmatch(file_data.get("display_name"), pattern)
            for pattern in (filter_dict.get("filenames") or [])
        ):
            compatible_files.append(file_data)
    return compatible_files
