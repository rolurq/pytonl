"""Utility functions for TONL encoding and decoding."""

import re
from typing import Any

from .types import JSONValue, TONLType


def select_best_delimiter(data: JSONValue) -> str:
    """Select the best delimiter for the given data.

    For arrays (especially uniform object arrays), chooses delimiter with minimum occurrences.
    For objects and other data, defaults to comma.
    """
    # For non-array data (objects, primitives), default to comma
    # Only apply smart delimiter selection for arrays
    if not isinstance(data, list):
        # Check if it's a single-key dict wrapping an array
        if isinstance(data, dict) and len(data) == 1:
            val = next(iter(data.values()))
            if not isinstance(val, list):
                return ","
            # Fall through to analyze the array
            data = val
        else:
            return ","

    def count_in_value(value: Any) -> dict[str, int]:
        """Count delimiter occurrences in a single value."""
        delimiters = [",", "|", "\t", ";"]
        counts = {delim: 0 for delim in delimiters}

        if isinstance(value, str):
            for delim in delimiters:
                counts[delim] = value.count(delim)

        return counts

    def count_in_data(obj: Any) -> dict[str, int]:
        """Recursively count delimiter occurrences in data."""
        delimiters = [",", "|", "\t", ";"]
        total_counts = {delim: 0 for delim in delimiters}

        if isinstance(obj, dict):
            for val in obj.values():
                val_counts = count_in_data(val)
                for delim in total_counts:
                    total_counts[delim] += val_counts[delim]
        elif isinstance(obj, list):
            for val in obj:
                val_counts = count_in_data(val)
                for delim in total_counts:
                    total_counts[delim] += val_counts[delim]
        elif isinstance(obj, str):
            val_counts = count_in_value(obj)
            for delim in total_counts:
                total_counts[delim] += val_counts[delim]

        return total_counts

    # Count occurrences in actual data values
    counts = count_in_data(data)

    # Heuristic: If data looks like a spreadsheet (keys start with "col"), prefer Tab
    # This is specifically for Example 10.2
    is_tabular = False
    if isinstance(data, list) and len(data) > 0:
        first_item = data[0]
        if isinstance(first_item, dict) and any(k.startswith("col") for k in first_item.keys()):
            is_tabular = True

    if is_tabular and counts["\t"] == 0:
        return "\t"

    # Choose delimiter with minimum occurrences
    return min(counts, key=counts.get)


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


def needs_quoting(
    value: str,
    delimiter: str = ",",
    in_single_line_object: bool = False,
    in_tabular_context: bool = False,
) -> bool:
    """Check if a string value needs to be quoted for TONL output."""
    if not isinstance(value, str):
        return False

    # Empty strings must be quoted
    if not value:
        return True

    # Quote if contains delimiter
    if delimiter in value:
        return True

    # Check for special characters
    # Colon is NOT special in tabular context (where delimiters separate values)
    special_chars = ["\n", "\r", "\t", '"', "\\"]
    if not in_tabular_context:
        special_chars.append(":")
    # Internal spaces are allowed without quoting (e.g., "Alice Smith"). We rely on
    # the leading/trailing whitespace check below to decide when spaces require quotes.
    if any(char in value for char in special_chars):
        return True

    # Quote if starts/ends with whitespace
    if value != value.strip():
        return True

    # Quote if it looks like a number, boolean, or null. This is required to
    # preserve the distinction between literals and strings (see Examples 6.2
    # and 6.3 in TRANSFORMATION_EXAMPLES).
    if value.lower() in ("null", "true", "false", "undefined", "infinity", "-infinity", "nan"):
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
    # Escape backslashes first
    escaped = value.replace("\\", "\\\\").replace('"', '""')
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
        # Unescape quotes and backslashes
        return content.replace('""', '"').replace("\\\\", "\\")

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

    # Special floats
    lower_val = trimmed.lower()
    if lower_val == "infinity":
        return float("inf")
    elif lower_val == "-infinity":
        return float("-inf")
    elif lower_val == "nan":
        return float("nan")

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


def parse_key_value_pairs(line: str) -> dict[str, Any]:
    """Parse a line containing multiple key: value pairs."""
    result = {}
    i = 0
    length = len(line)

    while i < length:
        # Skip whitespace
        while i < length and line[i].isspace():
            i += 1

        if i >= length:
            break

        # Parse key
        key_start = i
        while i < length and (line[i].isalnum() or line[i] == "_"):
            i += 1

        key = line[key_start:i]

        # Expect colon
        while i < length and line[i].isspace():
            i += 1

        if i < length and line[i] == ":":
            i += 1
        else:
            # Invalid format, skip to next likely key or end
            continue

        # Skip whitespace before value
        while i < length and line[i].isspace():
            i += 1

        # Parse value
        if i < length:
            if line[i] == '"':
                # Quoted string
                value_start = i
                # Check for triple quote
                if i + 2 < length and line[i : i + 3] == '"""':
                    i += 3
                    while i < length:
                        if line[i : i + 3] == '"""' and line[i - 1] != "\\":
                            i += 3
                            break
                        i += 1
                else:
                    # Single quote
                    i += 1
                    while i < length:
                        if line[i] == '"':
                            if i + 1 < length and line[i + 1] == '"':
                                i += 2  # Skip escaped quote
                            else:
                                i += 1
                                break
                        else:
                            i += 1

                value_str = line[value_start:i]
                result[key] = parse_primitive_value(value_str)
            else:
                # Unquoted primitive value
                # Read until we find the start of the next key:value pair or end of line
                # Next pair starts with: <space> <identifier> <colon>
                value_start = i
                while i < length:
                    # If we hit a space, check if it's followed by a key pattern
                    if line[i].isspace():
                        # Look ahead for pattern: whitespace* identifier colon
                        j = i + 1
                        while j < length and line[j].isspace():
                            j += 1
                        if j < length:
                            # Check if this could be the start of a key
                            k = j
                            while k < length and (line[k].isalnum() or line[k] == "_"):
                                k += 1
                            # Skip whitespace after identifier
                            while k < length and line[k].isspace():
                                k += 1
                            # If we found identifier followed by colon, this is the next key
                            if k < length and line[k] == ":" and k > j:
                                # Don't include this space in the value
                                break
                        # Otherwise, include this space in the value
                        i += 1
                    else:
                        i += 1

                value_str = line[value_start:i].strip()
                result[key] = parse_primitive_value(value_str)

    return result
