# msproject_validator — usage & notes

This document was added on 2025-11-13 to describe the new `msproject_validator` package and how to run the validator and tests.

Quick commands (run from repository root):

```bash
# Validate only (prints validation results)
python3 validate.py path/to/input.xml

# Attempt automatic repairs and write repaired XML + repair log
python3 validate.py path/to/input.xml path/to/output_repaired.xml
```

Outputs
- Repaired file: the path you provided for the repaired XML
- Repair log: same directory, filename suffixed `_repair.log`

Tests
- Unit tests are under `tests/test_repairs.py` and use Python's built-in `unittest`.

Run tests:

```bash
python3 -m unittest discover -v
```

Notes
- The package is namespaced under `msproject_validator` and the CLI `validate.py` is present at the repo root for convenience.
- If you plan to run tests from another CWD, ensure the repo root is on `PYTHONPATH` so `msproject_validator` can be imported.
