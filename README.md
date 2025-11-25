# PyTONL

**Token-Optimized Notation Language** - A compact serialization format designed for LLM contexts, human readability, and perfect JSON compatibility.

## Features

- **🎯 Token Efficient**: 32-45% smaller than JSON for LLM contexts
- **👁️ Human Readable**: Clean, tabular format for structured data
- **🔄 Bidirectional**: Perfect JSON roundtrip compatibility
- **📊 Tabular Arrays**: Reduces redundancy in uniform object arrays
- **🎨 Smart Quoting**: Minimal quoting with automatic delimiter selection
- **📝 Type Hints**: Optional type annotations for validation

## Installation

```bash
pip install pytonl
```

For development:
```bash
pip install pytonl[dev]
```

## Quick Start

### Encoding JSON to TONL

```python
import pytonl

data = {
    "users": [
        {"id": 1, "name": "Alice", "role": "admin"},
        {"id": 2, "name": "Bob", "role": "user"}
    ]
}

tonl_str = pytonl.encode(data)
print(tonl_str)
```

Output:
```
#version 1.0
users[2]{id,name,role}:
  1, Alice, admin
  2, Bob, user
```

### Decoding TONL to JSON

```python
import pytonl

tonl_str = """#version 1.0
users[2]{id,name,role}:
  1, Alice, admin
  2, Bob, user"""

data = pytonl.decode(tonl_str)
print(data)
```

Output:
```python
{
    "users": [
        {"id": 1, "name": "Alice", "role": "admin"},
        {"id": 2, "name": "Bob", "role": "user"}
    ]
}
```

### Custom Options

```python
from pytonl import encode, EncodeOptions

# Use custom delimiter
options = EncodeOptions(delimiter="|", include_types=True)
tonl_str = encode(data, options)

# Decode with options
from pytonl import decode, DecodeOptions
data = decode(tonl_str, DecodeOptions(strict=True))
```

## Format Overview

TONL uses several strategies to minimize tokens:

### Tabular Format for Uniform Arrays
Instead of repeating keys for each object:
```json
[{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
```

TONL uses a table format:
```
items[2]{id,name}:
  1, Alice
  2, Bob
```

### Smart Quoting
Values are only quoted when necessary (contains delimiters, special chars, or looks like a keyword).

### Nested Blocks
Hierarchical data uses indentation for clarity:
```
config{database,cache}:
  cache: true
  database{host,port}:
    host: localhost
    port: 5432
```

## API Reference

### Main Functions

- **`encode(data, options=None)`**: Convert Python object to TONL string
- **`decode(tonl_str, options=None)`**: Convert TONL string to Python object

### Classes

- **`TONLEncoder`**: Encoder class for advanced usage
- **`TONLDecoder`**: Decoder class for advanced usage
- **`EncodeOptions`**: Configuration for encoding
- **`DecodeOptions`**: Configuration for decoding

### Types and Enums

- **`TONLType`**: Enum for type hints (null, bool, u32, i32, f64, str, obj, list)
- **`Delimiter`**: Supported delimiters (comma, pipe, semicolon, tab)

## Documentation

For the complete specification and implementation details, see the [IMPLEMENTATION_REFERENCE.md](docs/IMPLEMENTATION_REFERENCE.md).

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/pytonl.git
cd pytonl

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=pytonl --cov-report=html

# Run specific test file
pytest tests/test_encoder.py -v
```

### Code Quality

```bash
# Format code
black pytonl/ tests/

# Lint
ruff check pytonl/ tests/

# Type check
mypy pytonl/
```

## Examples

See the [tests](tests/) directory for comprehensive examples covering:
- Simple objects and arrays
- Nested structures
- Special characters and quoting
- Type preservation
- Roundtrip conversion

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
