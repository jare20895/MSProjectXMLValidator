# MSProject XML Validator

This repository contains a small package, `msproject_validator`, which validates
and optionally repairs Microsoft Project XML files so they import cleanly into
MS Project.

Quick start

From the repository root:

Validate only (no changes written):

```bash
python3 validate.py path/to/input.xml
```

Validate and attempt repairs (writes repaired XML + repair log):

```bash
python3 validate.py path/to/input.xml path/to/output_repaired.xml
```

Unit tests

Run the unit tests (ensure the project root is on PYTHONPATH):

```bash
PYTHONPATH=AIProjects/Coding/MSProjectXMLValidator python3 -m unittest discover -v AIProjects/Coding/MSProjectXMLValidator/tests
```

Docstring style

We use `pydocstyle` to enforce docstring conventions; run it with the
configured virtualenv Python:

```bash
/media/jare16/4TBSSD/.venv/bin/python -m pydocstyle msproject_validator
```

Docs

See `docs/msproject_validator.md` for a short usage note and `docs/implementation.md`
for the implementation mapping.
