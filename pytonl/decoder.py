"""TONL decoder - converts TONL format to JSON/Python objects."""

import re
from typing import Any

from .types import ColumnDef, DecodeOptions, JSONValue, TONLType
from .utils import parse_primitive_value, split_line_by_delimiter


class TONLDecoder:
    """Decoder for converting TONL format to Python objects."""

    def __init__(self, options: DecodeOptions = None):
        """Initialize decoder with options."""
        self.options = options or DecodeOptions()
        self.version = "1.0"
        self.delimiter = ","

    def decode(self, tonl_str: str) -> JSONValue:
        """Decode TONL string to Python object."""
        lines = tonl_str.split("\n")

        # Parse headers
        data_start = self._parse_headers(lines)

        # Parse data section
        data_lines = lines[data_start:]
        if not data_lines or not any(line.strip() for line in data_lines):
            return None

        result, _ = self._parse_lines(data_lines, 0)

        # Unwrap top-level single-key results based on value type
        # - "root{...}:" -> unwrap to get {...}
        # - "users[2]{...}:" -> unwrap array to get [...]
        # - "config{...}:" -> keep as {'config': {...}} (object with meaningful key)
        # - "value: null" -> unwrap primitive to get null
        if isinstance(result, dict) and len(result) == 1:
            key = list(result.keys())[0]
            value = result[key]

            # Unwrap if:
            # 1. Key is 'root' (standard unwrapping)
            # 2. Value is an array (arrays are unwrapped)
            # 3. Value is a primitive (single values are unwrapped)
            # Don't unwrap if value is an object/dict (meaningful structure)
            if key == "root" or isinstance(value, list) or not isinstance(value, (dict, list)):
                return value

        return result

    def _parse_headers(self, lines: list[str]) -> int:
        """Parse header lines and return index of first data line."""
        data_start = 0

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Skip empty lines
            if not stripped:
                data_start = i + 1
                continue

            # Skip schema directives
            if stripped.startswith("@"):
                data_start = i + 1
                continue

            # Parse header directives
            if stripped.startswith("#"):
                match = re.match(r"^#(\w+)\s+(.+)$", stripped)
                if match:
                    key = match.group(1)
                    value = match.group(2)

                    if key == "version":
                        self.version = value
                    elif key == "delimiter":
                        if value == "\\t":
                            self.delimiter = "\t"
                        elif value in [",", "|", ";"]:
                            self.delimiter = value

                data_start = i + 1
            else:
                # First non-header line
                break

        return data_start

    def _parse_lines(self, lines: list[str], start_indent: int) -> tuple[Any, int]:
        """Parse lines at a given indentation level."""
        if not lines:
            return None, 0

        first_line = lines[0]

        # Parse the first line to determine structure
        stripped = first_line.strip()

        # Try to parse as object/array header
        header_info = self._parse_header(stripped)

        if header_info:
            result, consumed = self._parse_block(lines, header_info)
            key = header_info["key"]

            # If the key is an array index like "[0]", return result unwrapped
            # Otherwise wrap in {key: result} dict
            if key.startswith("[") and key.endswith("]"):
                return result, consumed
            else:
                return {key: result}, consumed
        else:
            # Simple key-value pair
            return self._parse_key_value(stripped), 1

    def _parse_header(self, line: str) -> dict[str, Any] | None:
        """Parse a block header line."""
        # Match: key[N]{cols}: or key{cols}: or key[N]:
        # Must have either array brackets or column braces (or both)
        # Simple "key: value" should NOT match
        pattern = r"^([a-zA-Z_]\w*|\[\d+\])(\[\d+\])?(\{([^}]*)\})?:(.*)$"
        match = re.match(pattern, line)

        if not match:
            return None

        key = match.group(1)
        array_bracket = match.group(2)  # Optional [N]
        braces = match.group(3)  # Optional {cols}
        columns_str = match.group(4)  # Optional cols content
        rest = match.group(5).strip()  # Content after :

        # Must have either array brackets or column braces to be considered a header
        # Otherwise it's just a simple key: value pair
        if not array_bracket and not braces:
            return None

        is_array = array_bracket is not None
        array_length = int(array_bracket[1:-1]) if is_array else None

        # Parse column definitions
        columns = []
        if columns_str:
            for col_part in columns_str.split(","):
                col_part = col_part.strip()
                if ":" in col_part:
                    name, type_hint = col_part.split(":", 1)
                    try:
                        type_enum = TONLType(type_hint.strip())
                    except ValueError:
                        type_enum = None
                    columns.append(ColumnDef(name.strip(), type_enum))
                else:
                    columns.append(ColumnDef(col_part, None))

        return {
            "key": key,
            "is_array": is_array,
            "array_length": array_length,
            "columns": columns,
            "rest": rest,
        }

    def _parse_block(self, lines: list[str], header_info: dict[str, Any]) -> tuple[Any, int]:
        """Parse a block (object or array)."""
        is_array = header_info["is_array"]
        columns = header_info["columns"]
        rest = header_info["rest"]

        # If there's content on the same line as header
        if rest:
            # Single-line object or primitive array
            if is_array and not columns:
                # Primitive array on same line
                values = self._parse_array_values(rest)
                return values, 1
            elif columns:
                # Single-line object
                obj = self._parse_single_line_object(rest, columns)
                return obj, 1

        # Multi-line block
        first_line_indent = len(lines[0]) - len(lines[0].lstrip())
        lines_consumed = 1

        if is_array and columns:
            # Tabular array
            result = []
            for i in range(1, len(lines)):
                line = lines[i]
                line_indent = len(line) - len(line.lstrip())

                # Check if still part of this block
                if line.strip() and line_indent <= first_line_indent:
                    break

                if line.strip():
                    row_values = split_line_by_delimiter(line.strip(), self.delimiter)
                    obj = {}
                    for j, col in enumerate(columns):
                        if j < len(row_values):
                            obj[col.name] = parse_primitive_value(row_values[j])
                    result.append(obj)

                lines_consumed += 1

            return result, lines_consumed

        elif is_array:
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
            obj = {}
            i = 1
            while i < len(lines):
                line = lines[i]
                line_indent = len(line) - len(line.lstrip())

                if line.strip() and line_indent <= first_line_indent:
                    break

                if line.strip():
                    # Parse this line
                    sub_header = self._parse_header(line.strip())
                    if sub_header:
                        sub_result, sub_consumed = self._parse_block(lines[i:], sub_header)
                        obj[sub_header["key"]] = sub_result
                        i += sub_consumed
                        lines_consumed += sub_consumed
                    else:
                        # Key-value pair
                        kv_result = self._parse_key_value(line.strip())
                        if kv_result:
                            obj.update(kv_result)
                        i += 1
                        lines_consumed += 1
                else:
                    i += 1
                    lines_consumed += 1

            return obj, lines_consumed

    def _parse_key_value(self, line: str) -> dict[str, Any] | None:
        """Parse a simple key: value line."""
        match = re.match(r"^([a-zA-Z_]\w*|\[\d+\]):\s*(.*)$", line)
        if match:
            key = match.group(1)
            value_str = match.group(2)
            value = parse_primitive_value(value_str)
            return {key: value}
        return None

    def _parse_array_values(self, line: str) -> list[Any]:
        """Parse array values from a line."""
        values = split_line_by_delimiter(line, self.delimiter)
        return [parse_primitive_value(v) for v in values]

    def _parse_single_line_object(self, line: str, columns: list[ColumnDef]) -> dict[str, Any]:
        """Parse a single-line object with key: value pairs."""
        obj = {}
        # Split by key: value pattern
        pairs = re.findall(r"([a-zA-Z_]\w*):\s*([^:]+?)(?=\s+[a-zA-Z_]\w*:|$)", line)
        for key, value in pairs:
            obj[key.strip()] = parse_primitive_value(value.strip())
        return obj


def decode(tonl_str: str, options: DecodeOptions = None) -> JSONValue:
    """Convenience function to decode TONL string to Python object."""
    decoder = TONLDecoder(options)
    return decoder.decode(tonl_str)
