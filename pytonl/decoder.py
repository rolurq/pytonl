"""TONL decoder - converts TONL format to JSON/Python objects."""

import re
from typing import Any

from .types import DecodeOptions, JSONValue
from .utils import (
    coerce_typed_value,
    parse_key_value_pairs,
    parse_primitive_value,
    split_line_by_delimiter,
)


class TONLDecoder:
    """Decoder for converting TONL format to Python objects."""

    def __init__(self, options: DecodeOptions | None = None):
        """Initialize decoder with options."""
        self.options = options or DecodeOptions()
        self.delimiter = ","  # Default delimiter

    def decode(self, tonl_str: str) -> JSONValue:
        """Decode TONL string to Python object."""
        lines = tonl_str.splitlines()

        # Parse headers first to get version and delimiter
        start_idx = self._parse_headers(lines)

        # Parse data
        data_lines = lines[start_idx:]
        if not data_lines:
            return {}

        # Parse all top-level items
        result = {}
        i = 0
        while i < len(data_lines):
            line = data_lines[i]
            if not line.strip():
                i += 1
                continue

            sub_result, sub_consumed = self._parse_lines(data_lines[i:], 0)

            if sub_result is not None:
                if isinstance(sub_result, dict):
                    result.update(sub_result)
                elif not result:
                    # If result is empty and we got a non-dict, this is the single result
                    # (e.g. top-level array or primitive)
                    # But if we have multiple non-dict items, that's invalid JSON/TONL structure
                    # unless we treat them as a list? No, TONL top-level is usually object.
                    result = sub_result

            i += sub_consumed

        # Unwrap top-level single-key results based on value type
        # - "root{...}:" -> unwrap to get {...}
        # - "users[2]{...}:" -> unwrap array to get [...]
        # - "config{...}:" -> keep as {'config': {...}} (object with meaningful key)
        # - "value: null" -> unwrap primitive to get null
        if isinstance(result, dict) and len(result) == 1:
            key = list(result.keys())[0]
            value = result[key]

            if key == "root":
                return value

        return result

    def _parse_headers(self, lines: list[str]) -> int:
        """Parse headers and return index of first data line."""
        i = 0
        for original_line in lines:
            line = original_line.strip()
            if not line:
                i += 1
                continue

            if line.startswith("#version"):
                # Expect exactly "#version 1.0" for now.
                # Allow arbitrary internal whitespace but require the
                # numeric version to be 1.0.
                parts = line.split()
                if len(parts) != 2 or parts[0] != "#version" or parts[1] != "1.0":
                    raise ValueError(f"Unsupported TONL version header: {line!r}")
            elif line.startswith("#delimiter"):
                # Use original line to preserve whitespace delimiter
                # But we need to handle indentation? Headers shouldn't be indented.
                # Check if original_line starts with #delimiter (ignoring leading whitespace?)
                # No, headers must be at start of line?
                # Let's assume headers are not indented or we strip leading only.

                stripped_start = original_line.lstrip()
                if stripped_start.startswith("#delimiter"):
                    raw_val = stripped_start[10:]
                    # Strip newline only
                    val_part = raw_val.rstrip("\n").rstrip("\r")

                    if not val_part.strip():
                        # If empty after strip, check if it contained tab
                        if "\t" in val_part:
                            self.delimiter = "\t"
                    else:
                        delim = val_part.strip()
                        if delim == "\\t":
                            self.delimiter = "\t"
                        else:
                            self.delimiter = delim
            elif line.startswith("@"):
                # Directive - ignore for now
                pass
            else:
                # Not a header
                break
            i += 1
        return i

    def _parse_lines(self, lines: list[str], indent_level: int) -> tuple[Any, int]:
        """Parse lines at a given indentation level."""
        if not lines:
            return None, 0

        first_line = lines[0]

        # Parse the first line to determine structure
        stripped = first_line.strip()

        # Check for block header (Object or Array)
        # Matches: key{cols}: or key[N]: or key[N]{cols}:
        header_match = self._parse_header(stripped)

        if header_match:
            # It's a block (object or array)
            result, consumed = self._parse_block(lines, header_match)
            key = header_match["key"]

            # If the key is an array index like "[0]", return result unwrapped
            # Otherwise wrap in {key: result} dict
            if key.startswith("[") and key.endswith("]"):
                return result, consumed
            else:
                return {key: result}, consumed

        # Check for key-value pair
        kv_match = self._parse_key_value(stripped)
        if kv_match:
            key, value_str = kv_match

            # Handle multiline triple-quoted string values
            stripped_value = value_str.strip()
            if stripped_value.startswith('"""') and not stripped_value.endswith('"""'):
                # Accumulate subsequent lines until we find an unescaped closing """
                combined = stripped_value
                lines_consumed = 1

                def has_unescaped_triple_quote(s: str) -> bool:
                    idx = 0
                    while True:
                        idx = s.find('"""', idx)
                        if idx == -1:
                            return False
                        # Closing triple quote is not escaped with a backslash
                        if idx == 0 or s[idx - 1] != "\\":
                            return True
                        idx += 3

                i = 1
                while i < len(lines):
                    next_line = lines[i]
                    combined += "\n" + next_line
                    lines_consumed += 1
                    if has_unescaped_triple_quote(next_line):
                        break
                    i += 1

                value = parse_primitive_value(combined)
                return {key: value}, lines_consumed

            # Regular single-line primitive value
            value = parse_primitive_value(value_str)
            return {key: value}, 1

        # Check for primitive array (implicit key from context?)
        # No, top level primitive array usually has key[N]: ...
        # If we are here, it might be a continuation or invalid line
        return None, 1

    def _parse_header(self, line: str) -> dict[str, Any] | None:
        """Parse a block header line."""
        # Regex for headers:
        # Group 1: Key
        # Group 2: Array size (optional)
        # Group 3: Columns (optional)
        # Group 4: Rest of line (optional)

        # Pattern matches: key[size]{cols}: or key{cols}: or key[size]:
        # Updated regex to require either [] or {} to avoid matching simple key: value
        pattern = r"^(\w+|\[\d+\])(?:\[(\d+)\])?(?:\{([^}]*)\})?:\s*(.*)$"
        match = re.match(pattern, line)

        if match:
            key = match.group(1)
            array_size = match.group(2)
            columns_str = match.group(3)
            rest = match.group(4)

            # Must have either array brackets or column braces to be a header
            # (Regex guarantees : at end, but we need to ensure it's not just key:)
            if array_size is None and columns_str is None:
                return None

            is_array = array_size is not None
            columns: list[str] = []
            type_hints: dict[str, str] = {}
            if columns_str:
                # Parse columns, capturing optional type hints (e.g. col:u32)
                col_parts = columns_str.split(",")
                for part in col_parts:
                    part = part.strip()
                    if not part:
                        continue
                    if ":" in part:
                        name, hint = part.split(":", 1)
                        name = name.strip()
                        hint = hint.strip()
                        if name:
                            columns.append(name)
                            if hint:
                                type_hints[name] = hint
                    else:
                        columns.append(part)

            return {
                "key": key,
                "is_array": is_array,
                "array_size": int(array_size) if array_size else None,
                "columns": columns,
                "type_hints": type_hints,
                "rest": rest,
            }
        return None

    def _parse_key_value(self, line: str) -> tuple[str, str] | None:
        """Parse a key-value pair line."""
        # Match regular keys (word characters) or array indices like [0]
        pattern = r"^(\w+|\[\d+\]):\s*(.*)$"
        match = re.match(pattern, line)
        if match:
            return match.group(1), match.group(2)
        return None

    def _parse_block(self, lines: list[str], header_info: dict[str, Any]) -> tuple[Any, int]:
        """Parse a block (object or array)."""
        is_array = header_info["is_array"]
        columns = header_info["columns"]
        type_hints: dict[str, str] = header_info.get("type_hints", {})
        rest = header_info["rest"]

        # Calculate indentation of children
        first_line_indent = len(lines[0]) - len(lines[0].lstrip())

        # If we have content on the same line, it's a single-line block
        if rest:
            if is_array:
                # Primitive array on same line
                if not rest.strip():
                    return [], 1
                values = split_line_by_delimiter(rest, self.delimiter)
                parsed_values = [parse_primitive_value(v) for v in values]
                return parsed_values, 1
            else:
                # Single line object
                # Parse key: value pairs from the rest of the line, applying
                # type hints in strict mode when present.
                obj = parse_key_value_pairs(rest, type_hints=type_hints, strict=self.options.strict)
                return obj, 1

        # Multi-line block
        lines_consumed = 1
        result = [] if is_array else {}

        if is_array:
            # Check if tabular (uniform object array)
            # If we have columns defined in header, it's tabular
            if columns:
                # Tabular array
                # Each following line is a row of values
                while lines_consumed < len(lines):
                    line = lines[lines_consumed]
                    line_indent = len(line) - len(line.lstrip())

                    if line.strip() and line_indent <= first_line_indent:
                        break

                    if line.strip():
                        row_values = split_line_by_delimiter(line.strip(), self.delimiter)
                        obj: dict[str, Any] = {}
                        for j, col in enumerate(columns):
                            if j < len(row_values):
                                raw = row_values[j]
                                hint = type_hints.get(col)
                                if hint and self.options.strict:
                                    obj[col] = coerce_typed_value(raw, hint, strict=True)
                                else:
                                    obj[col] = parse_primitive_value(raw)
                        result.append(obj)

                    lines_consumed += 1

                return result, lines_consumed

            # Mixed array with indexed elements
            result = []
            i = 1
            while i < len(lines):
                line = lines[i]
                line_indent = len(line) - len(line.lstrip())

                if line.strip() and line_indent <= first_line_indent:
                    break

                if line.strip():
                    sub_result, sub_consumed = self._parse_lines(lines[i:], line_indent)

                    # Unwrap array item key if present (e.g. {'[0]': 'value'} -> 'value')
                    if isinstance(sub_result, dict) and len(sub_result) == 1:
                        key = list(sub_result.keys())[0]
                        if key.startswith("[") and key.endswith("]"):
                            sub_result = sub_result[key]

                    result.append(sub_result)
                    i += sub_consumed
                    lines_consumed += (
                        sub_consumed  # Correctly accumulate lines consumed by sub-blocks
                    )
                else:
                    i += 1
                    lines_consumed += 1

            return result, lines_consumed

        else:
            # Object
            # Parse children
            i = 1
            while i < len(lines):
                line = lines[i]
                line_indent = len(line) - len(line.lstrip())

                if line.strip() and line_indent <= first_line_indent:
                    break

                if line.strip():
                    sub_result, sub_consumed = self._parse_lines(lines[i:], line_indent)
                    if isinstance(sub_result, dict):
                        result.update(sub_result)
                    i += sub_consumed
                    lines_consumed += sub_consumed
                else:
                    i += 1
                    lines_consumed += 1

            return result, lines_consumed
