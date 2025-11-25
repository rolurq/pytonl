"""Test fixtures and sample data for TONL tests."""

# Example from IMPLEMENTATION_REFERENCE.md - Simple Object
SIMPLE_OBJECT_JSON = {"id": 123, "name": "Alice Smith", "active": True}

SIMPLE_OBJECT_TONL = """#version 1.0
root{active,id,name}: active: true id: 123 name: Alice Smith"""

# Uniform Object Array
UNIFORM_ARRAY_JSON = {
    "users": [
        {"id": 1, "name": "Alice", "role": "admin"},
        {"id": 2, "name": "Bob", "role": "user"},
    ]
}

UNIFORM_ARRAY_TONL = """#version 1.0
users[2]{id,name,role}:
  1, Alice, admin
  2, Bob, user"""

# Primitive Arrays
PRIMITIVE_ARRAYS_JSON = {
    "numbers": [1, 2, 3, 4, 5],
    "tags": ["urgent", "important", "review"],
}

PRIMITIVE_ARRAYS_TONL = """#version 1.0
root{numbers,tags}:
  numbers[5]: 1, 2, 3, 4, 5
  tags[3]: urgent, important, review"""

# Nested Object
NESTED_OBJECT_JSON = {
    "config": {"database": {"host": "localhost", "port": 5432}, "cache": True}
}

NESTED_OBJECT_TONL = """#version 1.0
config{cache,database}:
  cache: true
  database{host,port}:
    host: localhost
    port: 5432"""

# Array with special characters (quoting test)
SPECIAL_CHARS_JSON = {
    "items": [{"name": "Item, A", "price": 99.99}, {"name": "Item B", "price": 149.99}]
}

SPECIAL_CHARS_TONL = """#version 1.0
items[2]{name,price}:
  "Item, A", 99.99
  Item B, 149.99"""

# Mixed array
MIXED_ARRAY_JSON = {"items": ["text", 42, {"id": 1, "name": "Object"}, [1, 2, 3]]}

MIXED_ARRAY_TONL = """#version 1.0
items[4]:
  [0]: text
  [1]: 42
  [2]{id,name}: id: 1 name: Object
  [3][3]: 1, 2, 3"""

# Empty values
EMPTY_VALUES_JSON = {"empty_array": [], "empty_object": {}, "null_value": None}

# Type testing
TYPE_TEST_JSON = {
    "bool_true": True,
    "bool_false": False,
    "int_positive": 42,
    "int_negative": -100,
    "float_value": 3.14,
    "string_value": "hello world",
    "null_value": None,
}
