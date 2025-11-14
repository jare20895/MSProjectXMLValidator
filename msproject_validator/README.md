# MSProjectXMLValidator

**Validate XML project files for easier import to Microsoft Project from other project management software.**

## Overview

Migrating projects from tools like Smartsheet, Jira, Trello, Asana, Primavera, and others into Microsoft Project (`.mpp`) often means dealing with `.xml` files. Invalid formatting, missing fields, or structure errors can cause import failures or data loss. **MSProjectXMLValidator** is a Python tool to validate your XML project files and ensure smoother migration and import into Microsoft Project.

## Features

- Checks for correct structure and required fields
- Highlights format issues that can cause Microsoft Project imports to fail
- Easy command-line usage
- Extendable for custom validations

## Getting Started

### Prerequisites
- Python 3.x

### Installation
Clone the repository:
```bash
git clone https://github.com/jare20895/MSProjectXMLValidator.git
cd MSProjectXMLValidator
```
Install dependencies (if applicable):
```bash
pip install -r requirements.txt
```

### Usage

Run the CLI directly from the repository root:

```bash
# validation-only
python validate.py path/to/project.xml

# attempt automatic repairs and write repaired output + repair log
python validate.py path/to/project.xml path/to/project_repaired.xml
```

- The first form runs validation only and exits with status 0 on success.
- The second form attempts automatic repairs and writes a repaired XML plus a `_repair.log` file with details.

### Example output

```
Validating project.xml...
[ERROR] Task missing required UID field at line 78
[WARNING] Resource has blank Name at line 104
Validation completed. 2 errors, 1 warning.
```

## Typical Use Cases

- Migrating from Smartsheet, Jira, Asana, Trello, etc. to Microsoft Project
- Checking exported XML before importing
- Quickly detect format/submission errors for .xml files

## Contributing

Contributions and bug reports are welcome! Please open an issue or PR. See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

[MIT License](LICENSE)

## Related Topics

`microsoft-project` `xml` `project-management` `data-migration` `file-validator` `interoperability` `python`