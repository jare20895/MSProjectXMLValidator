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
        repair_log = args.output.replace('.xml', '_repair.log')
        if success:
            print(f"\n✓ SUCCESS: Repaired file saved to: {args.output}")
            total_repairs = sum(len(v) for v in repairs.values()) if repairs else 0
            print(f"  Repairs performed: {total_repairs}")
            if total_repairs:
                # show up to 5 sample repair messages
                shown = 0
                print('  Sample repairs:')
                for category, msgs in repairs.items():
                    for m in msgs:
                        print(f"    - [{category}] {m}")
                        shown += 1
                        if shown >= 5:
                            break
                    if shown >= 5:
                        break
            print(f"  Repair log: {repair_log}")
            return 0
        else:
            print(f"\n✗ FAILED: Could not repair all issues.")
            if repairs:
                total_repairs = sum(len(v) for v in repairs.values())
                print(f"  Partial repairs performed: {total_repairs}")
            if errors:
                total_errors = sum(len(v) for v in errors.values())
                print(f"  Remaining errors: {total_errors}")
            print(f"  Check the repair log for details: {repair_log}")
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
