"""TONL encoder - converts JSON/Python objects to TONL format."""

import math
from typing import Any

from .types import EncodeOptions, JSONValue
from .utils import infer_type, needs_quoting, quote_string, select_best_delimiter


class TONLEncoder:
    """Encoder for converting Python objects to TONL format."""

    def __init__(self, options: EncodeOptions):
        """Initialize encoder with options."""
        self.options = options
        self.indent_level = 0
        self.delimiter: str = ","  # Selected during encoding

    def encode(self, data: JSONValue) -> str:
        """Encode Python object to TONL string."""
        self.delimiter = self.options.delimiter or select_best_delimiter(data)

        lines = []

        # Add version header
        lines.append(f"#version {self.options.version}")

        # Add delimiter header if not comma (comma is default)
        if self.delimiter != ",":
            # Emit the actual delimiter character in the header. For tab, this means
            # an actual TAB character after "#delimiter ", matching the examples
            # in TRANSFORMATION_EXAMPLES and tests.
            lines.append(f"#delimiter {self.delimiter}")

        # Encode root value
        # Root Unwrapping: If root is a dict with exactly one key and value is complex,
        # unwrap it to avoid redundant root{key}: nesting.
        if isinstance(data, dict) and len(data) == 1:
            key = next(iter(data))
            val = data[key]
            if isinstance(val, (dict, list)):
                root_lines = self._encode_value(val, key)
            else:
                root_lines = self._encode_value(data, "root")
        else:
            root_lines = self._encode_value(data, "root")

        lines.extend(root_lines)

        return "\n".join(lines)

    def _encode_value(self, value: Any, key: str) -> list[str]:
        """Encode a value with a given key."""
        if isinstance(value, dict):
            return self._encode_object(value, key)
        elif isinstance(value, list):
            return self._encode_array(value, key)
        else:
            return self._encode_primitive(value, key)

    def _format_primitive_value(
        self, value: Any, in_single_line_object: bool = False, in_tabular_context: bool = False
    ) -> str:
        """Format a primitive value for TONL output."""
        if isinstance(value, bool):
            return "true" if value else "false"
        elif isinstance(value, (int, float)):
            if isinstance(value, float):
                if math.isnan(value):
                    return "NaN"
                if math.isinf(value):
                    return "Infinity" if value > 0 else "-Infinity"
                # Format float values to match examples:
                # - Preserve natural representation for non-integers (e.g., 95.5 -> "95.5")
                # - For integer-valued floats, prefer two decimal places when there is a
                #   single decimal digit (e.g., 1500.0 -> "1500.00" as in money examples).
                s = str(value)
                if "." not in s:
                    return s
                whole, frac = s.split(".", 1)
                # Only pad when the float is mathematically integral and has a single
                # decimal digit in its string form (e.g., "1500.0").
                if value.is_integer() and len(frac) == 1:
                    return f"{whole}.{frac}0"
                return s
            return str(value)
        elif isinstance(value, str):
            needs = needs_quoting(value, self.delimiter, in_single_line_object, in_tabular_context)
            if needs:
                return quote_string(value)
            return value
        elif value is None:
            return "null"
        return str(value)

    def _encode_primitive(self, value: Any, key: str) -> list[str]:
        """Encode a primitive value."""
        indent = self._indent()
        formatted = self._format_primitive_value(value)
        return [f"{indent}{key}: {formatted}"]

    def _encode_array(self, arr: list[Any], key: str) -> list[str]:
        """Encode an array."""
        if not arr:
            indent = self._indent()
            return [f"{indent}{key}[0]:"]

        # Check if it's a uniform array of objects (tabular candidate)
        if self._is_uniform_object_array(arr):
            return self._encode_tabular_array(arr, key)

        # Check if it's a simple primitive array
        if all(not isinstance(x, (dict, list)) for x in arr):
            return self._encode_primitive_array(arr, key)

        # Mixed array
        return self._encode_mixed_array(arr, key)

    def _encode_primitive_array(self, arr: list[Any], key: str) -> list[str]:
        """Encode an array of primitive values."""
        indent = self._indent()

        # Format all values
        formatted_values = [self._format_primitive_value(x) for x in arr]

        # Format delimiter - comma has no leading space, others have space on both sides
        if self.delimiter == ",":
            delimiter_sep = ", "
        elif self.delimiter == "\t":
            delimiter_sep = "\t"
        else:
            delimiter_sep = f" {self.delimiter} "

        joined = delimiter_sep.join(formatted_values)

        if len(joined) < self.options.single_line_threshold:
            return [f"{indent}{key}[{len(arr)}]: {joined}"]
        else:
            return [f"{indent}{key}[{len(arr)}]:", f"{indent}  {joined}"]

    def _encode_tabular_array(self, arr: list[dict[str, Any]], key: str) -> list[str]:
        """Encode a uniform array of objects in tabular format."""
        indent = self._indent()

        # Get columns from first object (preserve order)
        columns = list(arr[0].keys())

        # Build header
        col_defs = []
        for col in columns:
            if self.options.include_types:
                type_hint = infer_type(arr[0][col])
                if type_hint.value not in ["obj", "list"]:
                    col_defs.append(f"{col}:{type_hint.value}")
                else:
                    col_defs.append(col)
            else:
                col_defs.append(col)

        header = f"{indent}{key}[{len(arr)}]{{{','.join(col_defs)}}}:"
        lines = [header]

        # Encode each row
        for item in arr:
            row_values = []
            for col in columns:
                val = item.get(col)
                if isinstance(val, (dict, list)):
                    # Nested object/array - not supported in tabular format
                    row_values.append(str(val))
                else:
                    row_values.append(self._format_primitive_value(val, in_tabular_context=True))

            # Format delimiter - comma has no leading space, others have space on both sides
            if self.delimiter == ",":
                delimiter_sep = ", "
            elif self.delimiter == "\t":
                delimiter_sep = "\t"
            else:
                delimiter_sep = f" {self.delimiter} "

            row = delimiter_sep.join(row_values)
            lines.append(f"{indent}  {row}")

        return lines

    def _encode_mixed_array(self, arr: list[Any], key: str) -> list[str]:
        """Encode a mixed array with indexed elements."""
        indent = self._indent()
        lines = [f"{indent}{key}[{len(arr)}]:"]

        self.indent_level += 1
        for i, item in enumerate(arr):
            item_key = f"[{i}]"
            item_lines = self._encode_value(item, item_key)
            lines.extend(item_lines)
        self.indent_level -= 1

        return lines

    def _encode_object(self, obj: dict[str, Any], key: str) -> list[str]:
        """Encode an object."""
        indent = self._indent()

        # Filter undefined values (preserve order)
        keys = [k for k in obj.keys() if obj[k] is not None or k in obj]

        if not keys:
            return [f"{indent}{key}{{}}:"]

        # Build column definitions
        col_defs = []
        for k in keys:
            if self.options.include_types:
                type_hint = infer_type(obj[k])
                if type_hint.value not in ["obj", "list"]:
                    col_defs.append(f"{k}:{type_hint.value}")
                else:
                    col_defs.append(k)
            else:
                col_defs.append(k)

        header = f"{indent}{key}{{{','.join(col_defs)}}}:"

        # Decide single-line vs multi-line
        if self._should_use_multiline(obj):
            lines = [header]
            self.indent_level += 1
            for k in keys:
                value_lines = self._encode_value(obj[k], k)
                lines.extend(value_lines)
            self.indent_level -= 1
            return lines
        else:
            # Single line format
            pairs = []
            for k in keys:
                val = obj[k]
                formatted = self._format_primitive_value(val, in_single_line_object=True)
                # print(f"DEBUG: k={k}, val={val}, formatted={formatted}")
                pairs.append(f"{k}: {formatted}")

            result = [f"{header} {' '.join(pairs)}"]
            # print(f"DEBUG: _encode_object returning: {result}")
            return result

    def _should_use_multiline(self, obj: dict[str, Any]) -> bool:
        """Determine if an object should use multi-line format."""
        # Check for nested structures or newlines
        for value in obj.values():
            if isinstance(value, (dict, list)):
                return True
            if isinstance(value, str) and "\n" in value:
                return True

        # NOTE: We intentionally do NOT force multi-line just because a value would
        # need quoting in single-line mode. The reference examples (e.g., 7.3, 7.4)
        # keep many quoted-or-quotable values on a single line as long as there is
        # no further nesting and the line length stays reasonable.

        # Check predicted line length using formatted primitive representations,
        # i.e. how the values would appear in a single-line object. This makes the
        # heuristic match the reference examples more closely (e.g., 5.2, 5.3).
        length = 0
        for k, v in obj.items():
            length += len(k) + 2  # key + ": "
            if isinstance(v, (dict, list)):
                # Nested structures are already handled above; treat their
                # contribution as minimal here.
                length += 4
            else:
                formatted = self._format_primitive_value(v, in_single_line_object=True)
                length += len(formatted)
            length += 1  # space separator

        if length > self.options.single_line_threshold:
            return True

        return False

    def _is_uniform_object_array(self, arr: list[Any]) -> bool:
        """Check if array contains uniform objects with same keys and all primitive values."""
        if not arr:
            return False

        if not all(isinstance(item, dict) for item in arr):
            return False

        first_keys = set(arr[0].keys())
        # Check all objects have same keys
        if not all(set(item.keys()) == first_keys for item in arr):
            return False

        # Check all values are primitives (no nested objects or arrays)
        # Tabular format only works with primitive values
        for item in arr:
            for value in item.values():
                if isinstance(value, (dict, list)):
                    return False

        return True

    def _indent(self) -> str:
        """Get current indentation string."""
        return " " * (self.indent_level * self.options.indent)


def encode(data: JSONValue, options: EncodeOptions | None = None) -> str:
    """Convenience function to encode data to TONL format."""
    options = options or EncodeOptions()
    encoder = TONLEncoder(options)
    return encoder.encode(data)
