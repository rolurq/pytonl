"""Type definitions and enums for TONL encoding/decoding."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Literal


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


@dataclass
class EncodeOptions:
    """Options for encoding JSON to TONL."""

    include_types: bool = False
    indent: int = 2
    delimiter: Literal[",", "|", ";", "\t"] | None = None
    version: str = "1.0"
    single_line_threshold: int = 80


@dataclass
class DecodeOptions:
    """Options for decoding TONL to JSON."""

    strict: bool = False


@dataclass
class ColumnDef:
    """Column definition for TONL objects/arrays."""

    name: str
    type_hint: TONLType | None = None


JSONValue = None | bool | int | float | str | list[Any] | dict[str, Any]
