"""Core orchestration: validate and optionally repair MS Project XML files."""
import xml.etree.ElementTree as ET
from .config import logger
from .validators import (
    check_xml_well_formed,
    check_unique_uids,
    check_referential_integrity,
    check_data_formats,
    check_calendar_logic,
)
from .repairs import (
    fix_summary_task_predecessors,
    detect_circular_dependencies,
    fix_date_formats,
    remove_conflicting_dates,
    add_essential_project_metadata,
    add_essential_ms_project_fields,
    fix_incorrect_milestones,
    fix_zero_work_tasks,
    calculate_finish_dates,
    add_missing_predecessors,
)
from .reporting import generate_repair_comment, write_repair_log

def validate_and_repair_project_xml(xml_file, output_file=None, repair_mode=True):
    """Validate (and optionally repair) an MS Project XML file.

    This is the high-level orchestration function that runs all validation
    checks in sequence and, when `repair_mode` is True, attempts a set of
    automated repairs. When an `output_file` is provided and repairs are
    performed the modified XML is written and a repair log is generated.

    Args:
        xml_file: Path to input MS Project XML file.
        output_file: Optional path to write repaired XML. If omitted no file
            is written (repairs happen in-memory).
        repair_mode: If True, attempt repairs for detected issues.

    Returns:
        A tuple (success: bool, repairs: dict, errors: dict).
    """
    logger.info('=' * 80)
    logger.info(f"Starting validation{' and repair' if repair_mode else ''} of: {xml_file}")
    logger.info('=' * 80)
    print(f"\n{'='*80}")
    print(f"--- {'Validating and Repairing' if repair_mode else 'Validating'} Project File: {xml_file} ---")
    print(f"{'='*80}\n")
    if not check_xml_well_formed(xml_file):
        return False, {}, {}
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        errors = {}
        repairs = {}
        task_uids, resource_uids = check_unique_uids(root, errors)
        check_referential_integrity(root, task_uids, resource_uids, errors)
        check_data_formats(root, errors)
        check_calendar_logic(root, errors)
        if repair_mode:
            print(f"\n{'='*80}")
            print("--- REPAIR MODE: Attempting to fix detected issues ---")
            print(f"{'='*80}\n")
            fix_summary_task_predecessors(root, repairs)
            detect_circular_dependencies(root, errors, repairs)
            fix_date_formats(root, errors, repairs)
            if "Data Formats" in repairs and "Data Formats" in errors:
                del errors["Data Formats"]
            remove_conflicting_dates(root, repairs)
            add_essential_project_metadata(root, repairs)
            add_essential_ms_project_fields(root, repairs)
            fix_incorrect_milestones(root, repairs)
            fix_zero_work_tasks(root, repairs)
            calculate_finish_dates(root, repairs)
            add_missing_predecessors(root, repairs)
            if output_file:
                ET.register_namespace('', 'http://schemas.microsoft.com/project')
                tree.write(output_file, encoding='UTF-8', xml_declaration=True)
                with open(output_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                content = content.replace(
                    "<?xml version='1.0' encoding='UTF-8'?>",
                    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                )
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                report = generate_repair_comment(repairs, errors)
                log_file = output_file.replace('.xml', '_repair.log')
                write_repair_log(log_file, report)
                print(f"\n{'='*80}")
                print(f"Repaired XML saved to: {output_file}")
                print(f"Repair log saved to:  {log_file}")
                print(f"{'='*80}\n")
            else:
                logger.warning("Repair mode enabled but no output file specified. Changes not saved.")
        print(f"\n{'='*80}")
        if errors:
            print("--- VALIDATION COMPLETED WITH ERRORS ---")
            print(f"{'='*80}")
            print("\nRemaining issues found:")
            for category, msgs in errors.items():
                print(f"\n{category} ({len(msgs)} errors):")
                for msg in msgs:
                    print(f"  - {msg}")
            if repairs:
                print(f"\nRepairs made: {sum(len(v) for v in repairs.values())} total")
                if not repair_mode:
                    print("  (Run in repair mode to save fixes)")
            return False, repairs, errors
        else:
            print("--- VALIDATION SUCCESSFUL ---")
            print(f"{'='*80}")
            if repairs:
                print(f"\nAll issues successfully repaired! ({sum(len(v) for v in repairs.values())} repairs made)")
                print("File should now import into Microsoft Project without errors.\n")
            else:
                print("\nFile is well-formed, all references are valid, and formats are correct.\n")
            return True, repairs, errors
    except Exception as e:
        logger.exception("Unexpected error during validation")
        print(f"\n{'='*80}")
        print(f"An unexpected error occurred during validation: {e}")
        print(f"{'='*80}\n")
        import traceback
        traceback.print_exc()
        return False, {}, {}

def validate_project_xml(xml_file):
    """Run validation-only (no repairs) and return True if it passes.

    This thin wrapper calls `validate_and_repair_project_xml` with
    `repair_mode=False` and returns the boolean success flag.
    """
    success, _, _ = validate_and_repair_project_xml(xml_file, repair_mode=False)
    return success
