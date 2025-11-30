"""PyTONL - Token-Optimized Notation Language for Python.

TONL is a text-based serialization format designed for token efficiency in LLM contexts,
human readability, and bidirectional compatibility with JSON.
"""

from typing import TextIO, overload

from .__version__ import __version__
from .decoder import TONLDecoder
from .encoder import TONLEncoder
from .types import (
    ColumnDef,
    DecodeOptions,
    EncodeOptions,
    JSONValue,
    TONLType,
)


@overload
def decode(src: str, options: DecodeOptions | None = None) -> JSONValue: ...


@overload
def decode(src: TextIO, options: DecodeOptions | None = None) -> JSONValue: ...


def decode(src: str | TextIO, options: DecodeOptions | None = None) -> JSONValue:
    """Convenience function to decode TONL string to Python object."""
    decoder = TONLDecoder(options)
    return decoder.decode(src if isinstance(src, str) else src.read())


def encode(data: JSONValue, options: EncodeOptions | None = None) -> str:
    """Convenience function to encode data to TONL format."""
    options = options or EncodeOptions()
    encoder = TONLEncoder(options)
    return encoder.encode(data)


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
    "ColumnDef",
    "JSONValue",
    # Version
    "__version__",
]
