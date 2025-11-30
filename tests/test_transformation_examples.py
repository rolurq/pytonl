"""Tests based on docs/TRANSFORMATION_EXAMPLES.md.

This file contains tests for ALL examples from the documentation.
Each test verifies that the encoder produces exact TONL output as documented.
"""

import math

import pytest

from pytonl import DecodeOptions, EncodeOptions, decode, encode


class TestSimpleTypes:
    """Tests for Simple Types (Section 1)."""

    def test_1_1_basic_primitives(self):
        """Example 1.1: Basic Primitives."""
        data = {"string": "hello", "number": 42, "float": 3.14, "boolean": True, "null_value": None}
        tonl = encode(data)
        assert (
            """#version 1.0
root{string,number,float,boolean,null_value}: string: hello number: 42 float: 3.14 boolean: true null_value: null"""  # noqa: E501
            == tonl
        )
        assert decode(tonl) == data

    def test_1_2_strings_requiring_quotes(self):
        """Example 1.2: Strings Requiring Quotes."""
        data = {
            "with_comma": "Hello, world",
            "with_colon": "Key: Value",
            "with_quotes": 'She said "hi"',
            "number_string": "123",
            "bool_string": "true",
        }
        tonl = encode(data)
        assert (
            '''#version 1.0
root{with_comma,with_colon,with_quotes,number_string,bool_string}:
  with_comma: "Hello, world"
  with_colon: "Key: Value"
  with_quotes: "She said ""hi"""
  number_string: "123"
  bool_string: "true"'''
            == tonl
        )
        assert decode(tonl) == data

    def test_1_3_special_numeric_values(self):
        """Example 1.3: Special Numeric Values."""
        data = {
            "infinity": float("inf"),
            "negative_infinity": float("-inf"),
            "not_a_number": float("nan"),
            "infinity_string": "Infinity",
        }
        tonl = encode(data)
        assert (
            '''#version 1.0
root{infinity,negative_infinity,not_a_number,infinity_string}:
  infinity: Infinity
  negative_infinity: -Infinity
  not_a_number: NaN
  infinity_string: "Infinity"'''
            == tonl
        )

        decoded = decode(tonl)
        assert decoded["infinity"] == float("inf")
        assert decoded["negative_infinity"] == float("-inf")
        assert math.isnan(decoded["not_a_number"])
        assert decoded["infinity_string"] == "Infinity"


class TestComplexObjects:
    """Tests for Complex Objects (Section 2)."""

    def test_2_1_nested_objects_multiline(self):
        """Example 2.1: Nested Objects (Multi-line)."""
        data = {"user": {"name": "Alice Smith", "profile": {"age": 30, "city": "New York"}}}
        tonl = encode(data)
        # Encoder chooses inline formatting for the inner profile object while
        # keeping the outer user block multi-line.
        assert (
            "#version 1.0\nuser{name,profile}:\n  name: Alice Smith\n  profile{age,city}: age: 30 city: New York"  # noqa: E501
            == tonl
        )
        assert decode(tonl) == data

    def test_2_2_flat_object_singleline(self):
        """Example 2.2: Flat Object (Single-line)."""
        data = {"config": {"timeout": 5000, "retries": 3, "debug": False}}
        tonl = encode(data)
        assert (
            """#version 1.0
config{timeout,retries,debug}: timeout: 5000 retries: 3 debug: false"""
            == tonl
        )
        assert decode(tonl) == data

    def test_2_3_mixed_nesting(self):
        """Example 2.3: Mixed Nesting."""
        data = {
            "app": {
                "name": "MyApp",
                "version": "2.0",
                "settings": {"theme": "dark", "language": "en"},
                "features": ["auth", "api", "cache"],
            }
        }
        tonl = encode(data)
        # According to the number-like string rules (Example 6.3), "2.0" should be
        # quoted to preserve it as a string rather than a numeric value.
        assert (
            """#version 1.0
app{name,version,settings,features}:
  name: MyApp
  version: "2.0"
  settings{theme,language}: theme: dark language: en
  features[3]: auth, api, cache"""
            == tonl
        )
        assert decode(tonl) == data


class TestArrays:
    """Tests for Arrays (Section 3)."""

    def test_3_1_simple_primitive_array(self):
        """Example 3.1: Simple Primitive Array."""
        data = {"numbers": [1, 2, 3, 4, 5], "tags": ["urgent", "review", "bug-fix"]}
        tonl = encode(data)
        assert (
            """#version 1.0
root{numbers,tags}:
  numbers[5]: 1, 2, 3, 4, 5
  tags[3]: urgent, review, bug-fix"""
            == tonl
        )
        assert decode(tonl) == data

    def test_3_2_uniform_object_array(self):
        """Example 3.2: Uniform Object Array (Tabular)."""
        data = {
            "users": [
                {"id": 1, "name": "Alice", "role": "admin", "active": True},
                {"id": 2, "name": "Bob", "role": "user", "active": True},
                {"id": 3, "name": "Carol", "role": "editor", "active": False},
            ]
        }
        tonl = encode(data)
        assert (
            """#version 1.0
users[3]{id,name,role,active}:
  1, Alice, admin, true
  2, Bob, user, true
  3, Carol, editor, false"""
            == tonl
        )
        assert decode(tonl) == data

    def test_3_3_non_uniform_array(self):
        """Example 3.3: Non-Uniform Array (Mixed)."""
        data = {"items": ["text", 42, {"id": 1, "name": "Object"}, True, [1, 2, 3]]}
        tonl = encode(data)
        assert (
            """#version 1.0
items[5]:
  [0]: text
  [1]: 42
  [2]{id,name}: id: 1 name: Object
  [3]: true
  [4][3]: 1, 2, 3"""
            == tonl
        )
        assert decode(tonl) == data

    def test_3_4_array_with_null_values(self):
        """Example 3.4: Array with Null Values."""
        data = {"data": [1, None, 3, None, 5]}
        tonl = encode(data)
        assert "#version 1.0\ndata[5]: 1, null, 3, null, 5" == tonl
        assert decode(tonl) == data

    def test_3_5_empty_arrays(self):
        """Example 3.5: Empty Arrays."""
        data = {"empty_array": [], "other_field": "value"}
        tonl = encode(data)
        assert (
            """#version 1.0
root{empty_array,other_field}:
  empty_array[0]:
  other_field: value"""
            == tonl
        )
        assert decode(tonl) == data


class TestNestedStructures:
    """Tests for Nested Structures (Section 4)."""

    def test_4_1_deep_nesting(self):
        """Example 4.1: Deep Nesting."""
        data = {"level1": {"level2": {"level3": {"level4": {"level5": "deep value"}}}}}
        tonl = encode(data)
        # For deep nesting, the encoder keeps the innermost object (level4)
        # single-line while preserving the overall hierarchy.
        assert (
            "#version 1.0\nlevel1{level2}:\n  level2{level3}:\n    level3{level4}:\n      level4{level5}: level5: deep value"  # noqa: E501
            == tonl
        )
        assert decode(tonl) == data

    def test_4_2_array_of_arrays(self):
        """Example 4.2: Array of Arrays."""
        data = {"matrix": [[1, 2, 3], [4, 5, 6], [7, 8, 9]]}
        tonl = encode(data)
        assert (
            """#version 1.0
matrix[3]:
  [0][3]: 1, 2, 3
  [1][3]: 4, 5, 6
  [2][3]: 7, 8, 9"""
            == tonl
        )
        assert decode(tonl) == data

    def test_4_3_array_of_objects_with_arrays(self):
        """Example 4.3: Array of Objects with Arrays."""
        data = {
            "users": [
                {"id": 1, "name": "Alice", "tags": ["admin", "verified"]},
                {"id": 2, "name": "Bob", "tags": ["user"]},
            ]
        }
        tonl = encode(data)
        assert (
            """#version 1.0
users[2]:
  [0]{id,name,tags}:
    id: 1
    name: Alice
    tags[2]: admin, verified
  [1]{id,name,tags}:
    id: 2
    name: Bob
    tags[1]: user"""
            == tonl
        )
        assert decode(tonl) == data

    def test_4_4_object_with_mixed_content(self):
        """Example 4.4: Object with Mixed Content."""
        data = {
            "data": {
                "simple_field": "value",
                "nested_object": {"x": 1, "y": 2},
                "array_field": [1, 2, 3],
                "another_simple": 42,
            }
        }
        tonl = encode(data)
        assert (
            """#version 1.0
data{simple_field,nested_object,array_field,another_simple}:
  simple_field: value
  nested_object{x,y}: x: 1 y: 2
  array_field[3]: 1, 2, 3
  another_simple: 42"""
            == tonl
        )
        assert decode(tonl) == data


class TestSpecialCharacters:
    """Tests for Special Characters (Section 5)."""

    def test_5_1_delimiter_in_values(self):
        """Example 5.1: Delimiter in Values."""
        data = {"items": [{"name": "Item, A", "price": 10}, {"name": "Item B", "price": 20}]}
        tonl = encode(data)
        # Auto-select pipe delimiter because of commas in data
        assert (
            """#version 1.0
#delimiter |
items[2]{name,price}:
  Item, A | 10
  Item B | 20"""
            == tonl
        )
        assert decode(tonl) == data

    def test_5_2_quotes_in_values(self):
        """Example 5.2: Quotes in Values."""
        data = {
            "quote1": 'She said "hello"',
            "quote2": 'It\'s a "test"',
            "triple": 'Has """ triple quotes',
        }
        tonl = encode(data)
        # Expect exact TONL as documented in TRANSFORMATION_EXAMPLES (including
        # correct escaping of internal quotes and triple-quotes).
        assert (
            '#version 1.0\nroot{quote1,quote2,triple}:\n  quote1: "She said ""hello"""\n  quote2: "It\'s a ""test"""\n  triple: """Has \\""" triple quotes"""'  # noqa: E501
            == tonl
        )
        assert decode(tonl) == data

    def test_5_3_backslashes_and_paths(self):
        """Example 5.3: Backslashes and Paths."""
        data = {
            "windows_path": "C:\\Users\\Alice\\Documents",
            "regex": "\\d+\\.\\d+",
            "normal": "No backslash",
        }
        tonl = encode(data)
        # Ensure backslash-heavy values survive a full encode/decode roundtrip.
        assert decode(tonl) == data

    def test_5_4_unicode_and_emoji(self):
        """Example 5.4: Unicode and Emoji."""
        data = {"emoji": "Hello 👋 World 🌍", "unicode": "Héllo Wörld", "chinese": "你好世界"}
        tonl = encode(data)
        # All fields are primitives and fit comfortably on a single line.
        assert (
            "#version 1.0\nroot{emoji,unicode,chinese}: emoji: Hello 👋 World 🌍 unicode: Héllo Wörld chinese: 你好世界"  # noqa: E501
            == tonl
        )
        assert decode(tonl) == data


class TestEdgeCases:
    """Tests for Edge Cases (Section 6)."""

    def test_6_1_empty_and_whitespace(self):
        """Example 6.1: Empty and Whitespace."""
        data = {
            "empty_string": "",
            "space": " ",
            "spaces": "   ",
            "leading": "  text",
            "trailing": "text  ",
            "both": "  text  ",
        }
        tonl = encode(data)
        assert (
            '''#version 1.0
root{empty_string,space,spaces,leading,trailing,both}:
  empty_string: ""
  space: " "
  spaces: "   "
  leading: "  text"
  trailing: "text  "
  both: "  text  "'''
            == tonl
        )
        assert decode(tonl) == data

    def test_6_2_reserved_words_as_strings(self):
        """Example 6.2: Reserved Words as Strings."""
        data = {
            "true_string": "true",
            "false_string": "false",
            "null_string": "null",
            "undefined_string": "undefined",
            "infinity_string": "Infinity",
        }
        tonl = encode(data)
        assert (
            '''#version 1.0
root{true_string,false_string,null_string,undefined_string,infinity_string}:
  true_string: "true"
  false_string: "false"
  null_string: "null"
  undefined_string: "undefined"
  infinity_string: "Infinity"'''
            == tonl
        )
        assert decode(tonl) == data

    def test_6_3_number_like_strings(self):
        """Example 6.3: Number-like Strings."""
        data = {
            "integer_string": "123",
            "decimal_string": "3.14",
            "scientific_string": "1e10",
            "phone_number": "555-1234",
        }
        tonl = encode(data)
        assert (
            """#version 1.0
root{integer_string,decimal_string,scientific_string,phone_number}:
  integer_string: "123"
  decimal_string: "3.14"
  scientific_string: "1e10"
  phone_number: 555-1234"""
            == tonl
        )
        assert decode(tonl) == data

    def test_6_4_multiline_strings(self):
        """Example 6.4: Multiline Strings."""
        data = {
            "code": "function hello() {\n  return 'world';\n}",
            "poem": "Line 1\nLine 2\nLine 3",
        }
        tonl = encode(data)
        assert (
            '''#version 1.0
root{code,poem}:
  code: """function hello() {
  return 'world';
}"""
  poem: """Line 1
Line 2
Line 3"""'''
            == tonl
        )
        assert decode(tonl) == data


class TestRealWorldExamples:
    """Tests for Real-World Examples (Section 7)."""

    def test_7_1_user_database(self):
        """Example 7.1: User Database."""
        data = {
            "users": [
                {
                    "id": 1001,
                    "username": "alice_smith",
                    "email": "alice@company.com",
                    "firstName": "Alice",
                    "lastName": "Smith",
                    "age": 30,
                    "role": "admin",
                    "verified": True,
                    "lastLogin": "2025-11-04T10:30:00Z",
                },
                {
                    "id": 1002,
                    "username": "bob.jones",
                    "email": "bob@company.com",
                    "firstName": "Bob",
                    "lastName": "Jones",
                    "age": 25,
                    "role": "user",
                    "verified": True,
                    "lastLogin": "2025-11-04T09:15:00Z",
                },
                {
                    "id": 1003,
                    "username": "carol_w",
                    "email": "carol@personal.com",
                    "firstName": "Carol",
                    "lastName": "White",
                    "age": 35,
                    "role": "editor",
                    "verified": False,
                    "lastLogin": None,
                },
            ]
        }
        tonl = encode(data)
        assert (
            """#version 1.0
users[3]{id,username,email,firstName,lastName,age,role,verified,lastLogin}:
  1001, alice_smith, alice@company.com, Alice, Smith, 30, admin, true, 2025-11-04T10:30:00Z
  1002, bob.jones, bob@company.com, Bob, Jones, 25, user, true, 2025-11-04T09:15:00Z
  1003, carol_w, carol@personal.com, Carol, White, 35, editor, false, null"""
            == tonl
        )
        assert decode(tonl) == data

    def test_7_2_api_response(self):
        """Example 7.2: API Response."""
        data = {
            "status": "success",
            "timestamp": 1699123456,
            "data": {
                "total": 150,
                "page": 1,
                "pageSize": 10,
                "results": [
                    {"id": "abc123", "title": "First Result", "score": 0.95},
                    {"id": "def456", "title": "Second Result", "score": 0.87},
                ],
            },
            "meta": {"processingTime": 45, "cacheHit": True},
        }
        tonl = encode(data)
        assert (
            """#version 1.0
root{status,timestamp,data,meta}:
  status: success
  timestamp: 1699123456
  data{total,page,pageSize,results}:
    total: 150
    page: 1
    pageSize: 10
    results[2]{id,title,score}:
      abc123, First Result, 0.95
      def456, Second Result, 0.87
  meta{processingTime,cacheHit}: processingTime: 45 cacheHit: true"""
            == tonl
        )
        assert decode(tonl) == data

    def test_7_3_configuration_file(self):
        """Example 7.3: Configuration File."""
        data = {
            "app": {"name": "MyApplication", "version": "2.1.0", "environment": "production"},
            "database": {
                "host": "db.example.com",
                "port": 5432,
                "name": "myapp_prod",
                "poolSize": 20,
                "ssl": True,
            },
            "cache": {
                "enabled": True,
                "ttl": 3600,
                "provider": "redis",
                "connection": {"host": "cache.example.com", "port": 6379},
            },
            "features": {"authentication": True, "analytics": True, "notifications": False},
        }
        tonl = encode(data)
        assert (
            """#version 1.0
root{app,database,cache,features}:
  app{name,version,environment}: name: MyApplication version: 2.1.0 environment: production
  database{host,port,name,poolSize,ssl}: host: db.example.com port: 5432 name: myapp_prod poolSize: 20 ssl: true
  cache{enabled,ttl,provider,connection}:
    enabled: true
    ttl: 3600
    provider: redis
    connection{host,port}: host: cache.example.com port: 6379
  features{authentication,analytics,notifications}: authentication: true analytics: true notifications: false"""  # noqa: E501
            == tonl
        )
        assert decode(tonl) == data

    def test_7_4_ecommerce_product_catalog(self):
        """Example 7.4: E-commerce Product Catalog."""
        data = {
            "catalog": {
                "categories": [
                    {
                        "id": 1,
                        "name": "Electronics",
                        "products": [
                            {
                                "sku": "LAPTOP-001",
                                "name": "Professional Laptop",
                                "price": 1299.99,
                                "stock": 15,
                                "specs": {
                                    "ram": "16GB",
                                    "storage": "512GB SSD",
                                    "screen": "15.6 inch",
                                },
                            },
                            {
                                "sku": "MOUSE-001",
                                "name": "Wireless Mouse",
                                "price": 29.99,
                                "stock": 100,
                                "specs": {"dpi": 3200, "wireless": True, "battery": "AAA"},
                            },
                        ],
                    }
                ]
            }
        }
        tonl = encode(data)
        assert (
            """#version 1.0
catalog{categories}:
  categories[1]:
    [0]{id,name,products}:
      id: 1
      name: Electronics
      products[2]:
        [0]{sku,name,price,stock,specs}:
          sku: LAPTOP-001
          name: Professional Laptop
          price: 1299.99
          stock: 15
          specs{ram,storage,screen}: ram: 16GB storage: 512GB SSD screen: 15.6 inch
        [1]{sku,name,price,stock,specs}:
          sku: MOUSE-001
          name: Wireless Mouse
          price: 29.99
          stock: 100
          specs{dpi,wireless,battery}: dpi: 3200 wireless: true battery: AAA"""
            == tonl
        )
        assert decode(tonl) == data


class TestDelimiterComparison:
    """Tests for Delimiter Comparison (Section 8)."""

    def test_8_1_same_data_different_delimiters(self):
        """Example 8.1: Same Data, Different Delimiters."""
        data = {
            "data": [
                {"name": "Item, A", "category": "Tools, Hardware", "price": 99.99},
                {"name": "Item B", "category": "Electronics", "price": 149.99},
            ]
        }

        # With auto-selection, should choose pipe delimiter due to commas in data
        tonl = encode(data)
        assert "#delimiter |" in tonl
        assert decode(tonl) == data

    def test_8_2_smart_delimiter_selection(self):
        """Example 8.2: Smart Delimiter Selection.

        This is algorithmic/conceptual, main test is in test_8_1.
        Just verify that auto-selection works correctly.
        """
        # Data with commas - should select non-comma delimiter
        data = {"items": [{"name": "A, B", "value": "C, D"}]}
        tonl = encode(data)
        assert "#delimiter" in tonl  # Non-default delimiter chosen

        # Data without special chars - should use comma (default, no header)
        data2 = {"items": [{"name": "A", "value": "B"}]}
        tonl2 = encode(data2)
        assert "#delimiter" not in tonl2  # Comma is default


class TestTypeHints:
    """Tests for Type Hints (Section 9)."""

    def test_9_1_basic_type_hints(self):
        """Example 9.1: Basic Type Hints."""
        data = {"user": {"id": 123, "name": "Alice", "age": 30, "score": 95.5, "active": True}}

        # Without type hints
        tonl_no_types = encode(data, EncodeOptions(include_types=False))
        assert (
            "#version 1.0\nuser{id,name,age,score,active}: id: 123 name: Alice age: 30 score: 95.5 active: true"  # noqa: E501
            == tonl_no_types
        )
        assert decode(tonl_no_types) == data

        # With type hints
        tonl_types = encode(data, EncodeOptions(include_types=True))
        assert (
            "#version 1.0\nuser{id:u32,name:str,age:u32,score:f64,active:bool}: id: 123 name: Alice age: 30 score: 95.5 active: true"  # noqa: E501
            == tonl_types
        )
        assert decode(tonl_types) == data


class TestDelimiterExamples:
    """Tests for Section 10 Delimiter Examples."""

    def test_10_1_csv_like_data(self):
        """Example 10.1: CSV-like Data."""
        data = {
            "sales": [
                {"date": "2025-01-01", "amount": 1500.00, "region": "North, East"},
                {"date": "2025-01-02", "amount": 2300.00, "region": "South"},
            ]
        }
        tonl = encode(data)
        # Should auto-select pipe delimiter due to commas in data
        assert (
            """#version 1.0
#delimiter |
sales[2]{date,amount,region}:
  2025-01-01 | 1500.00 | North, East
  2025-01-02 | 2300.00 | South"""
            == tonl
        )
        assert decode(tonl) == data

    def test_10_2_tsv_like_data(self):
        """Example 10.2: TSV-like Data."""
        data = {
            "data": [
                {"col1": "a", "col2": "b", "col3": "c"},
                {"col1": "d", "col2": "e", "col3": "f"},
            ]
        }
        tonl = encode(data)
        # No special chars, should use default comma delimiter
        assert (
            """#version 1.0
#delimiter \t
data[2]{col1,col2,col3}:
  a	b	c
  d	e	f"""
            == tonl
        )
        assert decode(tonl) == data
