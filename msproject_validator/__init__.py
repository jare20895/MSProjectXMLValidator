"""msproject_validator package.

Expose high-level API for validating and repairing MS Project XML files.
"""
from .core import validate_and_repair_project_xml, validate_project_xml

__all__ = ["validate_and_repair_project_xml", "validate_project_xml"]

__version__ = "0.1.0"
