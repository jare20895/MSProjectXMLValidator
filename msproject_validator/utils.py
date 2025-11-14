"""Utility helpers used across the package."""
from .config import NAMESPACE, logger
import xml.etree.ElementTree as ET
import re
from datetime import datetime

def log_error(errors, category, message):
    """Log a new validation error.

    Record the provided message under the named category in the ``errors``
    mapping and emit an error-level log entry.

    Args:
        errors: dict mapping category -> list of messages; modified in-place.
        category: Short category name for the error (e.g. "Data Formats").
        message: Human-readable message describing the error.
    """
    if category not in errors:
        errors[category] = []
    errors[category].append(message)
    logger.error(f"{category}: {message}")
    print(f"  [ERROR] {message}")

def log_repair(repairs, category, message):
    """Log a repair action.

    Append the repair message to the `repairs` mapping under `category` and
    emit an informational log entry.

    Args:
        repairs: dict mapping category -> list of repair messages; modified in-place.
        category: Short category name for the repair (e.g. "Data Formats").
        message: Human-readable repair description.
    """
    if category not in repairs:
        repairs[category] = []
    repairs[category].append(message)
    logger.info(f"REPAIR - {category}: {message}")
    print(f"  [REPAIRED] {message}")

def find_all(element, path):
    """Find all elements using the package namespace mapping."""
    return element.findall(path, NAMESPACE)

def find_one(element, path):
    """Find a single element using the package namespace mapping."""
    return element.find(path, NAMESPACE)

def get_task_name(task_elem):
    """Get task name or fallback to UID."""
    name_elem = find_one(task_elem, 'ns:Name')
    uid_elem = find_one(task_elem, 'ns:UID')
    if name_elem is not None and name_elem.text:
        return name_elem.text
    elif uid_elem is not None:
        return f"Task UID {uid_elem.text}"
    return "Unknown Task"

def parse_duration(duration_str):
    """Parse ISO 8601 duration string (PT#H#M#S) to total minutes."""
    if not duration_str:
        return 0
    match = re.match(r'PT(\d+)H(\d+)M(\d+)S', duration_str)
    if match:
        hours, minutes, seconds = map(int, match.groups())
        return hours * 60 + minutes + seconds / 60
    return 0

def duration_to_string(total_minutes):
    """Convert total minutes to an ISO 8601 duration string.

    Example: 90 -> "PT1H30M0S".

    Args:
        total_minutes: Total duration in minutes (int or float).

    Returns:
        A string in the PT#H#M#S format.
    """
    hours = int(total_minutes // 60)
    minutes = int(total_minutes % 60)
    return f"PT{hours}H{minutes}M0S"
