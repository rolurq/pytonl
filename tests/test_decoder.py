"""Tests for TONL decoder."""


from pytonl import decode
from tests.fixtures.sample_data import (
    NESTED_OBJECT_TONL,
    PRIMITIVE_ARRAYS_TONL,
    SIMPLE_OBJECT_TONL,
    SPECIAL_CHARS_TONL,
    UNIFORM_ARRAY_TONL,
)


class TestDecoder:
    """Test cases for TONL decoder."""

    def test_decode_simple_object(self):
        """Test decoding a simple object."""
        result = decode(SIMPLE_OBJECT_TONL)
        assert result["active"] is True
        assert result["id"] == 123
        assert result["name"] == "Alice Smith"

    def test_decode_uniform_array(self):
        """Test decoding uniform object array."""
        result = decode(UNIFORM_ARRAY_TONL)
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[0]["name"] == "Alice"
        assert result[0]["role"] == "admin"
        assert result[1]["id"] == 2
        assert result[1]["name"] == "Bob"
        assert result[1]["role"] == "user"

    def test_decode_primitive_arrays(self):
        """Test decoding primitive arrays."""
        result = decode(PRIMITIVE_ARRAYS_TONL)
        assert result["numbers"] == [1, 2, 3, 4, 5]
        assert result["tags"] == ["urgent", "important", "review"]

    def test_decode_nested_object(self):
        """Test decoding nested objects."""
        result = decode(NESTED_OBJECT_TONL)
        assert result["config"]["cache"] is True
        assert result["config"]["database"]["host"] == "localhost"
        assert result["config"]["database"]["port"] == 5432

    def test_decode_special_characters(self):
        """Test decoding values with special characters."""
        result = decode(SPECIAL_CHARS_TONL)
        assert result[0]["name"] == "Item, A"
        assert result[0]["price"] == 99.99
        assert result[1]["name"] == "Item B"
        assert result[1]["price"] == 149.99

    def test_decode_empty_array(self):
        """Test decoding empty array."""
        tonl = "#version 1.0\nitems[0]:"
        result = decode(tonl)
        # Empty array may be None or empty list depending on implementation
        assert result is None or result == []

    def test_decode_null_value(self):
        """Test decoding null value."""
        tonl = "#version 1.0\nvalue: null"
        result = decode(tonl)
        assert result is None

    def test_decode_booleans(self):
        """Test decoding boolean values."""
        tonl = "#version 1.0\nroot{a,b}: a: true b: false"
        result = decode(tonl)
        assert result["a"] is True
        assert result["b"] is False

    def test_decode_numbers(self):
        """Test decoding various number types."""
        tonl = (
            "#version 1.0\nroot{int,negative,float}: int: 42 negative: -100 float: 3.14"
        )
        result = decode(tonl)
        assert result["int"] == 42
        assert result["negative"] == -100
        assert result["float"] == 3.14

    def test_decode_custom_delimiter(self):
        """Test decoding with custom delimiter."""
        tonl = """#version 1.0
#delimiter |
items[3]: a | b | c"""
        result = decode(tonl)
        assert result == ["a", "b", "c"]

    def test_decode_quoted_strings(self):
        """Test decoding quoted strings."""
        tonl = '#version 1.0\nname: "Alice Smith"'
        result = decode(tonl)
        assert result == "Alice Smith"

    def test_decode_escaped_quotes(self):
        """Test decoding strings with escaped quotes."""
        tonl = '#version 1.0\nname: "Say ""hello"""'
        result = decode(tonl)
        assert result == 'Say "hello"'
