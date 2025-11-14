# msproject_validator

A small package to validate and repair Microsoft Project XML (.xml) files.

Features
- Validate XML well-formedness, UID uniqueness and referential integrity.
- Detect and repair common issues: summary-task predecessor links, circular dependencies, malformed durations/dates, missing finish dates, and missing MS Project metadata fields.

Quick usage

Run validation only:

```bash
python3 validate.py path/to/input.xml
```

Attempt automatic repairs and write a repaired file + repair log:

```bash
python3 validate.py path/to/input.xml path/to/output_repaired.xml
```

Outputs
- Repaired XML will be written to the path you provide.
- A repair log will be created alongside the repaired XML with the suffix `_repair.log`.

License
MIT-style (no license file included in this scaffold). Use as you like.
