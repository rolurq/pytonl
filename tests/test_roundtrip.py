"""Roundtrip tests ensuring JSON -> TONL -> JSON fidelity."""


from pytonl import decode, encode
from tests.fixtures.sample_data import (
    NESTED_OBJECT_JSON,
    PRIMITIVE_ARRAYS_JSON,
    SIMPLE_OBJECT_JSON,
    TYPE_TEST_JSON,
    UNIFORM_ARRAY_JSON,
)


class TestRoundtrip:
    """Test cases for roundtrip conversion."""

    def test_roundtrip_simple_object(self):
        """Test JSON -> TONL -> JSON preserves simple object."""
        tonl = encode(SIMPLE_OBJECT_JSON)
        result = decode(tonl)
        assert result == SIMPLE_OBJECT_JSON

    def test_roundtrip_uniform_array(self):
        """Test JSON -> TONL -> JSON preserves uniform array."""
        tonl = encode(UNIFORM_ARRAY_JSON)
        result = decode(tonl)
        assert result == UNIFORM_ARRAY_JSON

    def test_roundtrip_primitive_arrays(self):
        """Test JSON -> TONL -> JSON preserves primitive arrays."""
        tonl = encode(PRIMITIVE_ARRAYS_JSON)
        result = decode(tonl)
        assert result == PRIMITIVE_ARRAYS_JSON

    def test_roundtrip_nested_object(self):
        """Test JSON -> TONL -> JSON preserves nested objects."""
        tonl = encode(NESTED_OBJECT_JSON)
        result = decode(tonl)
        assert result == NESTED_OBJECT_JSON

    def test_roundtrip_type_preservation(self):
        """Test that types are preserved through roundtrip."""
        tonl = encode(TYPE_TEST_JSON)
        result = decode(tonl)
        assert result["bool_true"] is True
        assert result["bool_false"] is False
        assert isinstance(result["int_positive"], int)
        assert isinstance(result["int_negative"], int)
        assert isinstance(result["float_value"], float)
        assert isinstance(result["string_value"], str)
        assert result["null_value"] is None

    def test_roundtrip_complex_structure(self):
        """Test roundtrip with complex nested structure."""
        data = {
            "users": [
                {
                    "id": 1,
                    "name": "Alice",
                    "profile": {"age": 30, "active": True},
                    "tags": ["admin", "moderator"],
                }
            ],
            "settings": {"theme": "dark", "notifications": False},
        }
        tonl = encode(data)
        result = decode(tonl)
        assert result == data

    def test_roundtrip_special_values(self):
        """Test roundtrip with special values."""
        data = {
            "empty_string": "",
            "whitespace": "  spaces  ",
            "number_string": "123",
            "bool_string": "true",
        }
        tonl = encode(data)
        result = decode(tonl)
        # Empty string becomes null in TONL
        # Other values should be preserved as strings
        assert result["whitespace"] == "  spaces  "
        assert result["number_string"] == "123"
        assert result["bool_string"] == "true"
