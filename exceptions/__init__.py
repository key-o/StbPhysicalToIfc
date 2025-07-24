"""Custom exceptions for Stb2IFC"""

from .custom_errors import (
    ConversionError,
    FileNotFoundError,
    FileSizeError,
    XMLParseError,
    ElementValidationError,
    IFCGenerationError,
    Stb2IfcError,
)

__all__ = [
    "ConversionError",
    "FileNotFoundError",
    "FileSizeError", 
    "XMLParseError",
    "ElementValidationError",
    "IFCGenerationError",
    "Stb2IfcError",
]
