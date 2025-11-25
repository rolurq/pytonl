"""Utility functions for TONL encoding and decoding."""

import re
from typing import Any

from .types import TONLType


def infer_type(value: Any) -> TONLType:
    """Infer TONL type from a Python value."""
    if value is None:
        return TONLType.NULL

    if isinstance(value, bool):
        return TONLType.BOOL

    if isinstance(value, int):
        if 0 <= value <= 0xFFFFFFFF:
            return TONLType.U32
        elif -0x80000000 <= value <= 0x7FFFFFFF:
            return TONLType.I32
        else:
            return TONLType.F64

    if isinstance(value, float):
        return TONLType.F64

    if isinstance(value, str):
        return TONLType.STR

    if isinstance(value, list):
        return TONLType.LIST

    if isinstance(value, dict):
        return TONLType.OBJ

    return TONLType.STR  # Fallback


def needs_quoting(value: str, delimiter: str) -> bool:
    """Check if a string value needs quoting based on delimiter and special characters."""
    if not value:
        return True

    # Always quote if contains delimiter
    if delimiter in value:
        return True

    # Quote if contains special characters
    special_chars = ["\n", "\r", "\t", '"', ":"]
    if any(char in value for char in special_chars):
        return True

    # Quote if starts/ends with whitespace
    if value != value.strip():
        return True

    # Quote if it looks like a number, boolean, or null
    if value.lower() in ("null", "true", "false"):
        return True

    if is_number(value):
        return True

    return False


def quote_string(value: str) -> str:
    """Quote a string value for TONL output."""
    # Check if we need triple quotes (contains newlines or quotes)
    if "\n" in value or '"""' in value:
        # Use triple quotes
        escaped = value.replace("\\", "\\\\").replace('"""', '\\"""')
        return f'"""{escaped}"""'

    # Use regular quotes, escape internal quotes by doubling
    escaped = value.replace('"', '""')
    return f'"{escaped}"'


def unquote_string(value: str) -> str:
    """Unquote a TONL string value."""
    value = value.strip()

    # Triple-quoted string
    if value.startswith('"""') and value.endswith('"""') and len(value) >= 6:
        content = value[3:-3]
        return content.replace('\\"""', '"""').replace("\\\\", "\\")

    # Regular quoted string
    if value.startswith('"') and value.endswith('"') and len(value) >= 2:
        content = value[1:-1]
        return content.replace('""', '"')

    return value


def is_number(s: str) -> bool:
    """Check if a string represents a number."""
    pattern = r"^-?\d+\.?\d*([eE][+-]?\d+)?$"
    return bool(re.match(pattern, s))


def parse_primitive_value(value_str: str) -> Any:
    """Parse a primitive value from TONL string."""
    trimmed = value_str.strip()

    # Quoted string
    if (trimmed.startswith('"') and trimmed.endswith('"')) or (
        trimmed.startswith('"""') and trimmed.endswith('"""')
    ):
        return unquote_string(trimmed)

    # Null
    if trimmed == "null" or trimmed == "":
        return None

    # Boolean
    if trimmed == "true":
        return True
    if trimmed == "false":
        return False

    # Number
    if is_number(trimmed):
        if "." in trimmed or "e" in trimmed.lower():
            return float(trimmed)
        else:
            return int(trimmed)

    # Unquoted string
    return trimmed


def split_line_by_delimiter(line: str, delimiter: str) -> list[str]:
    """Split a TONL line by delimiter, respecting quoted strings."""
    fields = []
    current_field = ""
    mode = "plain"  # Modes: plain, inQuote, inTripleQuote
    i = 0

    while i < len(line):
        char = line[i]
        next_char = line[i + 1] if i + 1 < len(line) else None
        next_next_char = line[i + 2] if i + 2 < len(line) else None

        if mode == "plain":
            if char == '"':
                # Check for triple quote
                if next_char == '"' and next_next_char == '"':
                    mode = "inTripleQuote"
                    current_field += '"""'
                    i += 2  # Skip next two quotes
                else:
                    mode = "inQuote"
                    current_field += char

            elif char == "\\" and next_char == delimiter:
                # Escaped delimiter
                current_field += delimiter
                i += 1  # Skip backslash

            elif char == delimiter:
                # Field separator
                fields.append(current_field.strip())
                current_field = ""

            else:
                current_field += char

        elif mode == "inQuote":
            current_field += char
            if char == '"':
                if next_char == '"':
                    # Doubled quote = literal quote (keep both in field)
                    current_field += '"'
                    i += 1
                else:
                    # End of quoted field
                    mode = "plain"

        elif mode == "inTripleQuote":
            current_field += char
            if char == '"' and next_char == '"' and next_next_char == '"':
                current_field += '""'
                mode = "plain"
                i += 2

        i += 1

    # Add last field
    fields.append(current_field.strip())
    return fields


def is_valid_identifier(name: str) -> bool:
    """Check if a string is a valid TONL identifier."""
    pattern = r"^[a-zA-Z_][a-zA-Z0-9_]*$"
    return bool(re.match(pattern, name))
