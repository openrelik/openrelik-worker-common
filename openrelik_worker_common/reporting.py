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
"""Helper methods for reporting."""

from enum import IntEnum


class Priority(IntEnum):
    """Reporting priority enum to store common values.

    Priorities can be anything in the range of 0-100, where 0 is the highest
    priority.
    """

    LOW = 80
    MEDIUM = 50
    HIGH = 20
    CRITICAL = 10


def bold(text):
    """Formats text as bold in Markdown format.

    Args:
      text(string): Text to format

    Return:
      string: Formatted text.
    """
    return f"**{text.strip():s}**"


def heading1(text):
    """Formats text as heading 1 in Markdown format.

    Args:
      text(string): Text to format

    Return:
      string: Formatted text.
    """
    return f"# {text.strip():s}"


def heading2(text):
    """Formats text as heading 2 in Markdown format.

    Args:
      text(string): Text to format

    Return:
      string: Formatted text.
    """
    return f"## {text.strip():s}"


def heading3(text):
    """Formats text as heading 3 in Markdown format.

    Args:
      text(string): Text to format

    Return:
      string: Formatted text.
    """
    return f"### {text.strip():s}"


def heading4(text):
    """Formats text as heading 4 in Markdown format.

    Args:
      text(string): Text to format

    Return:
      string: Formatted text.
    """
    return f"#### {text.strip():s}"


def heading5(text):
    """Formats text as heading 5 in Markdown format.

    Args:
      text(string): Text to format

    Return:
      string: Formatted text.
    """
    return f"##### {text.strip():s}"


def bullet(text, level=1):
    """Formats text as a bullet in Markdown format.

    Args:
      text(string): Text to format
      level(int): Indentation level

    Return:
      string: Formatted text.
    """
    return f"{'    ' * (level - 1):s}* {text.strip():s}"


def code(text):
    """Formats text as code in Markdown format.

    Args:
      text(string): Text to format

    Return:
      string: Formatted text.
    """
    return f"`{text.strip():s}`"
