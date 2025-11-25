"""TONL encoder - converts JSON/Python objects to TONL format."""

from typing import Any

from .types import EncodeOptions, JSONValue
from .utils import infer_type, needs_quoting, quote_string


class TONLEncoder:
    """Encoder for converting Python objects to TONL format."""

    def __init__(self, options: EncodeOptions = None):
        """Initialize encoder with options."""
        self.options = options or EncodeOptions()
        self.indent_level = 0

    def encode(self, data: JSONValue) -> str:
        """Encode Python object to TONL string."""
        lines = []

        # Add version header
        lines.append(f"#version {self.options.version}")

        # Add delimiter header if not comma
        if self.options.delimiter != ",":
            delimiter_repr = "\\t" if self.options.delimiter == "\t" else self.options.delimiter
            lines.append(f"#delimiter {delimiter_repr}")

        # Encode root value
        root_lines = self._encode_value(data, "root")
        lines.extend(root_lines)

        return "\n".join(lines)

    def _encode_value(self, value: Any, key: str) -> list[str]:
        """Encode a value with the given key."""
        if value is None:
            return [f"{self._indent()}{key}: null"]

        if isinstance(value, (bool, int, float)):
            return self._encode_primitive(value, key)

        if isinstance(value, str):
            return self._encode_primitive(value, key)

        if isinstance(value, list):
            return self._encode_array(value, key)

        if isinstance(value, dict):
            return self._encode_object(value, key)

        # Fallback: treat as string
        return self._encode_primitive(str(value), key)

    def _encode_primitive(self, value: Any, key: str) -> list[str]:
        """Encode a primitive value."""
        indent = self._indent()

        if isinstance(value, bool):
            formatted = "true" if value else "false"
        elif isinstance(value, (int, float)):
            formatted = str(value)
        elif isinstance(value, str):
            if needs_quoting(value, self.options.delimiter):
                formatted = quote_string(value)
            else:
                formatted = value
        else:
            formatted = "null"

        return [f"{indent}{key}: {formatted}"]

    def _encode_array(self, arr: list[Any], key: str) -> list[str]:
        """Encode an array."""
        if not arr:
            return [f"{self._indent()}{key}[0]:"]

        # Check if uniform object array
        if self._is_uniform_object_array(arr):
            return self._encode_tabular_array(arr, key)

        # Check if primitive array
        if all(isinstance(item, (type(None), bool, int, float, str)) for item in arr):
            return self._encode_primitive_array(arr, key)

        # Mixed array
        return self._encode_mixed_array(arr, key)

    def _encode_primitive_array(self, arr: list[Any], key: str) -> list[str]:
        """Encode an array of primitives."""
        indent = self._indent()
        formatted_values = []

        for item in arr:
            if isinstance(item, bool):
                formatted_values.append("true" if item else "false")
            elif isinstance(item, (int, float)):
                formatted_values.append(str(item))
            elif isinstance(item, str):
                if needs_quoting(item, self.options.delimiter):
                    formatted_values.append(quote_string(item))
                else:
                    formatted_values.append(item)
            else:
                formatted_values.append("null")

        # Format delimiter - comma has no leading space, others have space on both sides
        if self.options.delimiter == ",":
            delimiter_sep = ", "
        else:
            delimiter_sep = f" {self.options.delimiter} "

        joined = delimiter_sep.join(formatted_values)

        if len(joined) < self.options.single_line_threshold:
            return [f"{indent}{key}[{len(arr)}]: {joined}"]
        else:
            return [f"{indent}{key}[{len(arr)}]:", f"{indent}  {joined}"]

    def _encode_tabular_array(self, arr: list[dict[str, Any]], key: str) -> list[str]:
        """Encode a uniform array of objects in tabular format."""
        indent = self._indent()

        # Get sorted columns from first object
        columns = sorted(arr[0].keys())

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
                if isinstance(val, bool):
                    row_values.append("true" if val else "false")
                elif isinstance(val, (int, float)):
                    row_values.append(str(val))
                elif isinstance(val, str):
                    if needs_quoting(val, self.options.delimiter):
                        row_values.append(quote_string(val))
                    else:
                        row_values.append(val)
                elif val is None:
                    row_values.append("null")
                else:
                    # Nested object/array - not supported in tabular format
                    row_values.append(str(val))

            # Format delimiter - comma has no leading space, others have space on both sides
            if self.options.delimiter == ",":
                delimiter_sep = ", "
            else:
                delimiter_sep = f" {self.options.delimiter} "

            row = delimiter_sep.join(row_values)
            lines.append(f"{indent}  {row}")

        return lines

    def _encode_mixed_array(self, arr: list[Any], key: str) -> list[str]:
        """Encode a mixed array with indexed elements."""
        indent = self._indent()
        lines = [f"{indent}{key}[{len(arr)}]:"]

        self.indent_level += 1
        for i, item in enumerate(arr):
            item_lines = self._encode_value(item, f"[{i}]")
            lines.extend(item_lines)
        self.indent_level -= 1

        return lines

    def _encode_object(self, obj: dict[str, Any], key: str) -> list[str]:
        """Encode an object."""
        indent = self._indent()

        # Filter undefined values and sort keys
        keys = sorted(k for k in obj.keys() if obj[k] is not None or k in obj)

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
                if isinstance(val, bool):
                    formatted = "true" if val else "false"
                elif isinstance(val, (int, float)):
                    formatted = str(val)
                elif isinstance(val, str):
                    if needs_quoting(val, self.options.delimiter):
                        formatted = quote_string(val)
                    else:
                        formatted = val
                else:
                    formatted = "null"
                pairs.append(f"{k}: {formatted}")

            return [f"{header} {' '.join(pairs)}"]

    def _should_use_multiline(self, obj: dict[str, Any]) -> bool:
        """Determine if an object should use multi-line format."""
        for value in obj.values():
            if isinstance(value, (dict, list)):
                return True
            if isinstance(value, str) and "\n" in value:
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


def encode(data: JSONValue, options: EncodeOptions = None) -> str:
    """Convenience function to encode data to TONL format."""
    encoder = TONLEncoder(options)
    return encoder.encode(data)
