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
"""OpenRelik data types

This file defines the OpenRelik data types that can be used for input and
output files. The data types are defined as StrEnums which takes care of
the interoparability between code and database through string comparision 
instead of forcing Enum object comparision. This also makes sure we can
use both Enum based comparision and string based glob filtering.
"""

from enum import StrEnum


class DataType(StrEnum):
    FILE_DISKIMAGE_QCOW = "file:diskimage:qcow"
    FILE_DISKIMAGE_RAW = "file:diskimage:raw"
    FILE_BINARY = "file:binary"
