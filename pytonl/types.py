"""Type definitions and enums for TONL encoding/decoding."""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class TONLType(Enum):
    """TONL primitive type hints."""

    NULL = "null"
    BOOL = "bool"
    U32 = "u32"
    I32 = "i32"
    F64 = "f64"
    STR = "str"
    OBJ = "obj"
    LIST = "list"


class Delimiter(Enum):
    """Supported delimiters for TONL format."""

    COMMA = ","
    PIPE = "|"
    SEMICOLON = ";"
    TAB = "\t"


@dataclass
class EncodeOptions:
    """Options for encoding JSON to TONL."""

    delimiter: str = ","
    include_types: bool = False
    indent: int = 2
    version: str = "1.0"
    single_line_threshold: int = 80


@dataclass
class DecodeOptions:
    """Options for decoding TONL to JSON."""

    strict: bool = False
    auto_detect_delimiter: bool = True


@dataclass
class ColumnDef:
    """Column definition for TONL objects/arrays."""

    name: str
    type_hint: TONLType | None = None


JSONValue = None | bool | int | float | str | list[Any] | dict[str, Any]
