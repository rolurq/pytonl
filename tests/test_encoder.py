"""Tests for TONL encoder."""

from pytonl import EncodeOptions, decode, encode
from tests.fixtures.sample_data import (
    NESTED_OBJECT_JSON,
    PRIMITIVE_ARRAYS_JSON,
    SIMPLE_OBJECT_JSON,
    SPECIAL_CHARS_JSON,
    TYPE_TEST_JSON,
    UNIFORM_ARRAY_JSON,
)


class TestEncoder:
    """Test cases for TONL encoder."""

    def test_encode_simple_object(self):
        """Test encoding a simple object."""
        result = encode(SIMPLE_OBJECT_JSON)
        assert "#version 1.0" in result
        # Check that all keys are present in header (order may vary)
        assert "root{" in result and "active" in result and "id" in result and "name" in result
        assert "active: true" in result
        assert "id: 123" in result
        assert "name: Alice Smith" in result

    def test_encode_uniform_array(self):
        """Test encoding uniform object array."""
        result = encode(UNIFORM_ARRAY_JSON)
        assert "users[2]{id,name,role}:" in result
        assert "1, Alice, admin" in result
        assert "2, Bob, user" in result

    def test_encode_primitive_arrays(self):
        """Test encoding primitive arrays."""
        result = encode(PRIMITIVE_ARRAYS_JSON)
        assert "numbers[5]:" in result
        assert "1, 2, 3, 4, 5" in result
        assert "tags[3]:" in result
        assert "urgent, important, review" in result

    def test_encode_nested_object(self):
        """Test encoding nested objects."""
        result = encode(NESTED_OBJECT_JSON)
        # Check that keys are present (order may vary)
        assert "config{" in result and "cache" in result and "database" in result
        assert "cache: true" in result
        assert "database{" in result and "host" in result and "port" in result
        assert "host: localhost" in result
        assert "port: 5432" in result

    def test_encode_special_characters(self):
        """Test encoding values with special characters that need quoting."""
        result = encode(SPECIAL_CHARS_JSON)
        # Data contains comma, so auto-selection should choose pipe delimiter
        # With pipe, "Item, A" doesn't need quoting
        assert "#delimiter |" in result
        assert decode(result) == SPECIAL_CHARS_JSON
        assert "Item B" in result

    def test_encode_types(self):
        """Test encoding various types."""
        result = encode(TYPE_TEST_JSON)
        assert "bool_true: true" in result
        assert "bool_false: false" in result
        assert "int_positive: 42" in result
        assert "int_negative: -100" in result
        assert "float_value: 3.14" in result
        assert "string_value: hello world" in result
        assert "null_value: null" in result

    def test_encode_empty_array(self):
        """Test encoding empty array."""
        result = encode({"items": []})
        assert "items[0]:" in result

    def test_encode_empty_object(self):
        """Test encoding empty object."""
        result = encode({"config": {}})
        assert "config{}:" in result

    def test_encode_auto_delimiter_selection(self):
        """Test that encoder auto-selects best delimiter."""
        # This data has no commas, so should use comma (default)
        result = encode(PRIMITIVE_ARRAYS_JSON)
        # Comma is default, no delimiter header needed
        assert "#delimiter" not in result or result.count(",") > 0

    def test_encode_with_type_hints(self):
        """Test encoding with type hints."""
        options = EncodeOptions(include_types=True)
        result = encode({"age": 30, "active": True}, options)
        # Should include type hints in column definitions
        assert "age:u32" in result or "age:i32" in result
        assert "active:bool" in result
