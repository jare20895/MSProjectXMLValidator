"""CLI entrypoint for msproject_validator.

Replaces the legacy PythonValidatorMSProject.py script.
"""
import sys
import argparse
from msproject_validator.core import validate_and_repair_project_xml, validate_project_xml
from msproject_validator import __version__

def main(argv=None):
    """CLI entrypoint.

    Parses arguments and either runs validation-only or runs repair mode and
    writes a repaired XML file and a repair log.
    """
    parser = argparse.ArgumentParser(description='MS Project XML Validator and Repair Tool')
    parser.add_argument('input', help='Input MS Project XML file')
    parser.add_argument('output', nargs='?', help='Output repaired XML file (if omitted, runs validation only)')
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')
    args = parser.parse_args(argv)

    if args.output:
        success, repairs, errors = validate_and_repair_project_xml(args.input, args.output, repair_mode=True)
        if success:
            print(f"\n✓ SUCCESS: Repaired file saved to: {args.output}")
            return 0
        else:
            print(f"\n✗ FAILED: Could not repair all issues. Check the report in: {args.output}")
            return 1
    else:
        success = validate_project_xml(args.input)
        if success:
            print('\n✓ VALIDATION PASSED')
            return 0
        else:
            print('\n✗ VALIDATION FAILED')
            print('  Tip: Run with an output file to attempt automatic repairs:')
            print(f"    python validate.py {args.input} {args.input.replace('.xml', '_repaired.xml')}")
            return 1

if __name__ == '__main__':
    sys.exit(main())
