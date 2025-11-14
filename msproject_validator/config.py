"""Configuration and shared constants for msproject_validator."""
import re
import logging

# Regex for ISO 8601 Date (YYYY-MM-DDTHH:MM:SS)
DATE_REGEX = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$')

# Regex for ISO 8601 Duration (PT#H#M#S)
DURATION_REGEX = re.compile(r'^PT\d+H\d+M\d+S$')

# The default namespace for MS Project XML
NAMESPACE = {'ns': 'http://schemas.microsoft.com/project'}

# Setup module-level logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)
