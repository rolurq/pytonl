"""PyTONL - Token-Optimized Notation Language for Python.

TONL is a text-based serialization format designed for token efficiency in LLM contexts,
human readability, and bidirectional compatibility with JSON.
"""

from .__version__ import __version__
from .decoder import TONLDecoder, decode
from .encoder import TONLEncoder, encode
from .types import (
    ColumnDef,
    DecodeOptions,
    EncodeOptions,
    JSONValue,
    TONLType,
)

__all__ = [
    # Main API
    "encode",
    "decode",
    # Classes
    "TONLEncoder",
    "TONLDecoder",
    # Options
    "EncodeOptions",
    "DecodeOptions",
    # Types
    "TONLType",
    "Delimiter",
    "ColumnDef",
    "JSONValue",
    # Version
    "__version__",
]
