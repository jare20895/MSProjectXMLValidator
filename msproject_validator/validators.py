"""Validation checks for MS Project XML files."""
from .utils import find_all, find_one, get_task_name, log_error
from .config import DATE_REGEX, DURATION_REGEX, logger
from datetime import datetime

def check_xml_well_formed(xml_file):
    """Check that the provided XML file is well-formed.

    Attempts to parse the file using ElementTree. Returns True when the file
    parses successfully; otherwise prints an error and returns False.

    Args:
        xml_file: Path to the XML file to validate.

    Returns:
        True if the XML is well-formed, False on parse error or missing file.
    """
    print("Step 1: Checking if XML is well-formed...")
    import xml.etree.ElementTree as ET
    try:
        with open(xml_file, 'r', encoding='utf-8') as f:
            ET.parse(f)
        print("  [OK] XML is well-formed.\n")
        return True
    except ET.ParseError as e:
        print(f"\n--- FATAL ERROR: XML is not well-formed! ---")
        print(f"  Error details: {e}\n")
        return False
    except FileNotFoundError:
        print(f"\n--- FATAL ERROR: File not found ---")
        print(f"  Could not find file: {xml_file}\n")
        return False

def check_unique_uids(root, errors):
    """Check for duplicate UIDs within Tasks, Resources, and Assignments.

    Scans the Task, Resource, and Assignment collections and records any
    duplicate UID values into the `errors` mapping.

    Args:
        root: XML root element for the Project.
        errors: dict to which error messages will be appended.

    Returns:
        A tuple (task_uids_set, resource_uids_set) useful for downstream checks.
    """
    print("Step 2: Checking for duplicate UIDs...")
    uid_sets = {
        'Task': (find_all(root, './/ns:Task'), set()),
        'Resource': (find_all(root, './/ns:Resource'), set()),
        'Assignment': (find_all(root, './/ns:Assignment'), set()),
    }
    has_errors = False
    for name, (elements, uid_set) in uid_sets.items():
        for elem in elements:
            uid_elem = find_one(elem, 'ns:UID')
            if uid_elem is not None:
                uid = uid_elem.text
                if uid in uid_set:
                    log_error(errors, "Duplicate UIDs", f"Duplicate {name} UID found: {uid}")
                    has_errors = True
                uid_set.add(uid)
    if not has_errors:
        print("  [OK] All UIDs are unique.\n")
    return uid_sets['Task'][1], uid_sets['Resource'][1]

def check_referential_integrity(root, task_uids, resource_uids, errors):
    """Check that Assignments and PredecessorLinks reference existing UIDs.

    Validates that each Assignment's TaskUID and ResourceUID exist in the
    previously-collected sets, and that every PredecessorUID refers to a
    known Task UID.

    Args:
        root: XML root element for the Project.
        task_uids: set of task UIDs found in the project.
        resource_uids: set of resource UIDs found in the project.
        errors: dict to which error messages will be appended.
    """
    print("Step 3: Checking referential integrity...")
    has_errors = False
    for assign in find_all(root, './/ns:Assignment'):
        assign_uid = find_one(assign, 'ns:UID')
        task_uid = find_one(assign, 'ns:TaskUID')
        res_uid = find_one(assign, 'ns:ResourceUID')
        if assign_uid is None or task_uid is None or res_uid is None:
            continue
        if task_uid.text not in task_uids:
            log_error(errors, "Broken References", f"Assignment <UID>{assign_uid.text}</UID> points to non-existent TaskUID: {task_uid.text}")
            has_errors = True
        if res_uid.text not in resource_uids:
            log_error(errors, "Broken References", f"Assignment <UID>{assign_uid.text}</UID> points to non-existent ResourceUID: {res_uid.text}")
            has_errors = True
    for link in find_all(root, './/ns:PredecessorLink'):
        pred_uid = find_one(link, 'ns:PredecessorUID')
        if pred_uid is None:
            continue
        if pred_uid.text not in task_uids:
            parent_task = link.find('../ns:Name')
            parent_name = parent_task.text if parent_task is not None else "Unknown"
            log_error(errors, "Broken References", f"Task '{parent_name}' has a PredecessorLink to non-existent TaskUID: {pred_uid.text}")
            has_errors = True
    if not has_errors:
        print("  [OK] All references (Assignments, Predecessors) are valid.\n")

def check_data_formats(root, errors):
    """Check that project dates and durations use ISO 8601 formats.

    Verifies date/time fields and duration strings for both project-level and
    task-level elements. Any violations are recorded in `errors`.

    Args:
        root: XML root element for the Project.
        errors: dict to which error messages will be appended.
    """
    logger.info("Checking data formats (Dates & Durations)...")
    print("Step 4: Checking data formats (Dates & Durations)...")
    has_errors = False
    date_tags = ['ns:StartDate', 'ns:FinishDate', 'ns:CurrentDate', 'ns:CreationDate']
    for tag in date_tags:
        elem = find_one(root, f'.//{tag}')
        if elem is not None and elem.text and not DATE_REGEX.match(elem.text):
            log_error(errors, "Data Formats", f"Invalid date format in <{tag.replace('ns:', '')}> for 'Project'. Got: '{elem.text}'")
            has_errors = True
    for task in find_all(root, './/ns:Task'):
        task_name = get_task_name(task)
        for tag in ['ns:Start', 'ns:Finish']:
            elem = find_one(task, tag)
            if elem is not None and elem.text and not DATE_REGEX.match(elem.text):
                log_error(errors, "Data Formats", f"Invalid date format in <{tag.replace('ns:', '')}> for '{task_name}'. Got: '{elem.text}'")
                has_errors = True
        for tag in ['ns:Duration', 'ns:Work']:
            elem = find_one(task, tag)
            if elem is not None and elem.text and not DURATION_REGEX.match(elem.text):
                log_error(errors, "Data Formats", f"Invalid duration format in <{tag.replace('ns:', '')}> for '{task_name}'. Got: '{elem.text}'")
                has_errors = True
    if not has_errors:
        logger.info("All dates and durations are correctly formatted.")
        print("  [OK] All dates and durations are correctly formatted.\n")

def check_calendar_logic(root, errors):
    """Check that <MinutesPerWeek> matches the calculated base calendar minutes.

    Calculates total working minutes from the project's base calendar and
    compares against the declared <MinutesPerWeek> value. Discrepancies are
    recorded in `errors`.

    Args:
        root: XML root element for the Project.
        errors: dict to which error messages will be appended.
    """
    print("Step 5: Checking calendar logic...")
    has_errors = False
    try:
        mpw_elem = find_one(root, './/ns:MinutesPerWeek')
        if mpw_elem is None:
            print("  [SKIPPED] No <MinutesPerWeek> tag found in project.\n")
            return
        project_minutes = int(mpw_elem.text)
        base_cal_uid_elem = find_one(root, './/ns:CalendarUID')
        if base_cal_uid_elem is None:
            print("  [SKIPPED] No <CalendarUID> found.\n")
            return
        base_cal_uid = base_cal_uid_elem.text
        base_cal = find_one(root, f'.//ns:Calendar[ns:UID="{base_cal_uid}"]')
        if base_cal is None:
            log_error(errors, "Calendar Logic", f"Project CalendarUID {base_cal_uid} not found in <Calendars>.")
            return
        calculated_minutes = 0
        for day in find_all(base_cal, './/ns:WeekDay'):
            if find_one(day, 'ns:DayWorking') is not None and find_one(day, 'ns:DayWorking').text == '1':
                for wt in find_all(day, './/ns:WorkingTime'):
                    from_time = datetime.strptime(find_one(wt, 'ns:FromTime').text, '%H:%M:%S').time()
                    to_time = datetime.strptime(find_one(wt, 'ns:ToTime').text, '%H:%M:%S').time()
                    delta = datetime.combine(datetime.min, to_time) - datetime.combine(datetime.min, from_time)
                    calculated_minutes += delta.total_seconds() / 60
        if int(calculated_minutes) != project_minutes:
            log_error(errors, "Calendar Logic", f"<MinutesPerWeek> is {project_minutes}, but base calendar calculates to {int(calculated_minutes)}.")
            has_errors = True
        if not has_errors:
            print(f"  [OK] Project <MinutesPerWeek> ({project_minutes}) matches Base Calendar ({int(calculated_minutes)}).\n")
    except Exception as e:
        log_error(errors, "Calendar Logic", f"Could not parse calendar logic: {e}")
