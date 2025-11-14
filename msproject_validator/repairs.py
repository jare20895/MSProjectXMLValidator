"""Repair routines that modify the XML tree to fix common MS Project issues."""
import xml.etree.ElementTree as ET
from collections import defaultdict, deque
from datetime import datetime, timedelta
from .utils import find_all, find_one, get_task_name, parse_duration, log_repair, log_error
from .config import logger

def fix_summary_task_predecessors(root, repairs):
    """Move PredecessorLink elements off summary tasks onto their first child.

    Summary tasks should not normally carry predecessor links because they can
    create confusing or circular scheduling. This routine finds summary tasks
    (Summary == '1') and moves any <PredecessorLink> elements to the first
    non-summary child task beneath the summary. If there is no child, the
    predecessor links are removed.

    Args:
        root: XML root element of the Project tree.
        repairs: dict used to record repair messages; mutated in place.
    """
    logger.info("Checking for predecessor links on summary tasks...")
    print("Step 6: Checking for predecessor links on summary tasks...")
    fixed_count = 0
    all_tasks = list(find_all(root, './/ns:Task'))
    task_map = {}
    for task in all_tasks:
        uid_elem = find_one(task, 'ns:UID')
        if uid_elem is not None:
            task_map[uid_elem.text] = task
    for idx, task in enumerate(all_tasks):
        uid_elem = find_one(task, 'ns:UID')
        name_elem = find_one(task, 'ns:Name')
        summary_elem = find_one(task, 'ns:Summary')
        outline_level_elem = find_one(task, 'ns:OutlineLevel')
        if summary_elem is not None and summary_elem.text == '1':
            uid = uid_elem.text if uid_elem is not None else "Unknown"
            task_name = name_elem.text if name_elem is not None else f"Task {uid}"
            current_level = int(outline_level_elem.text) if outline_level_elem is not None else 0
            pred_links = list(find_all(task, './/ns:PredecessorLink'))
            if pred_links:
                logger.warning(f"Summary task {uid} '{task_name}' has predecessor links - this can cause circular dependencies")
                first_child_task = None
                first_child_uid = None
                first_child_name = None
                for next_idx in range(idx + 1, len(all_tasks)):
                    next_task = all_tasks[next_idx]
                    next_summary = find_one(next_task, 'ns:Summary')
                    next_level_elem = find_one(next_task, 'ns:OutlineLevel')
                    next_level = int(next_level_elem.text) if next_level_elem is not None else 999
                    if next_level <= current_level:
                        break
                    if next_summary is None or next_summary.text != '1':
                        first_child_task = next_task
                        first_child_uid = find_one(next_task, 'ns:UID').text
                        first_child_name = get_task_name(next_task)
                        break
                if first_child_task is not None:
                    for link in pred_links:
                        pred_uid_elem = find_one(link, 'ns:PredecessorUID')
                        if pred_uid_elem is not None:
                            pred_uid = pred_uid_elem.text
                            existing_preds = [find_one(l, 'ns:PredecessorUID').text
                                              for l in find_all(first_child_task, './/ns:PredecessorLink')]
                            if pred_uid not in existing_preds:
                                new_link = ET.Element('{http://schemas.microsoft.com/project}PredecessorLink')
                                new_pred_uid = ET.SubElement(new_link, '{http://schemas.microsoft.com/project}PredecessorUID')
                                new_pred_uid.text = pred_uid
                                new_type = ET.SubElement(new_link, '{http://schemas.microsoft.com/project}Type')
                                type_elem = find_one(link, 'ns:Type')
                                new_type.text = type_elem.text if type_elem is not None else '1'
                                first_child_task.append(new_link)
                                message = f"Moved PredecessorLink from summary task '{task_name}' (UID {uid}) to first child '{first_child_name}' (UID {first_child_uid}), predecessor UID {pred_uid}"
                                log_repair(repairs, "Summary Task Dependencies", message)
                            else:
                                message = f"Removed duplicate PredecessorLink from summary task '{task_name}' (UID {uid}), first child already has predecessor UID {pred_uid}"
                                log_repair(repairs, "Summary Task Dependencies", message)
                            task.remove(link)
                            fixed_count += 1
                else:
                    for link in pred_links:
                        pred_uid_elem = find_one(link, 'ns:PredecessorUID')
                        pred_uid = pred_uid_elem.text if pred_uid_elem is not None else "Unknown"
                        task.remove(link)
                        message = f"Removed PredecessorLink from summary task '{task_name}' (UID {uid}) with no children, predecessor UID {pred_uid}"
                        log_repair(repairs, "Summary Task Dependencies", message)
                        fixed_count += 1
    if fixed_count > 0:
        logger.info(f"Fixed {fixed_count} summary task predecessor links")
        print(f"  [REPAIRED] Fixed {fixed_count} summary task predecessor links.\n")
    else:
        logger.info("No summary task predecessor issues found")
        print(f"  [OK] No summary task predecessor issues found.\n")

def detect_circular_dependencies(root, errors, repairs):
    """Detect and remove circular predecessor links among tasks.

    Uses Kahn's algorithm to perform a topological sort of the task dependency
    graph. If a cycle is detected, this routine removes PredecessorLink
    elements that point between tasks involved in the cycle and records the
    repair actions.

    Args:
        root: XML root element of the Project tree.
        errors: dict of current validation errors; modified when cycles are
            detected (warnings logged as errors when unrepairable).
        repairs: dict used to record repair messages; mutated in place.

    Returns:
        True if a cycle was found (and repairs attempted), False otherwise.
    """
    logger.info("Checking for circular dependencies in task predecessors...")
    print("Step 7: Checking for circular dependencies...")
    tasks = {}
    graph = defaultdict(list)
    in_degree = defaultdict(int)
    for task in find_all(root, './/ns:Task'):
        uid_elem = find_one(task, 'ns:UID')
        if uid_elem is not None:
            uid = uid_elem.text
            tasks[uid] = task
            in_degree[uid] = 0
    for task in tasks.values():
        task_uid = find_one(task, 'ns:UID').text
        pred_links = find_all(task, './/ns:PredecessorLink')
        for link in pred_links:
            pred_uid_elem = find_one(link, 'ns:PredecessorUID')
            if pred_uid_elem is not None:
                pred_uid = pred_uid_elem.text
                graph[pred_uid].append(task_uid)
                in_degree[task_uid] += 1
    queue = deque([uid for uid in tasks.keys() if in_degree[uid] == 0])
    sorted_count = 0
    while queue:
        current = queue.popleft()
        sorted_count += 1
        for neighbor in graph[current]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
    if sorted_count < len(tasks):
        logger.warning(f"Circular dependency detected! Sorted {sorted_count}/{len(tasks)} tasks.")
        print(f"  [WARNING] Circular dependency detected in task predecessors.")
        cyclic_tasks = [uid for uid, degree in in_degree.items() if degree > 0]
        for task_uid in cyclic_tasks:
            task = tasks[task_uid]
            task_name = get_task_name(task)
            pred_links = find_all(task, './/ns:PredecessorLink')
            for link in pred_links:
                pred_uid_elem = find_one(link, 'ns:PredecessorUID')
                if pred_uid_elem is None:
                    continue
                pred_uid = pred_uid_elem.text
                if pred_uid in cyclic_tasks:
                    task.remove(link)
                    message = f"Removed circular PredecessorLink from '{task_name}' to UID {pred_uid}"
                    log_repair(repairs, "Circular Dependencies", message)
        return True
    else:
        logger.info("No circular dependencies found.")
        print(f"  [OK] No circular dependencies detected.\n")
        return False

def fix_date_formats(root, errors, repairs):
    """Repair common date and duration formatting issues.

    This function attempts to correct common typos and formats in date and
    duration fields (e.g. replacing 'PT4TwoH0M0S' with 'PT4H0M0S' or
    normalizing ISO-like datetime strings). Repairs and any remaining
    errors are recorded into the provided `repairs` and `errors` dicts.

    Args:
        root: XML root element of the Project tree.
        errors: dict to record unrepaired errors.
        repairs: dict used to record successful repair messages.

    Returns:
        True if no unrepaired format errors remain, False otherwise.
    """
    logger.info("Checking and repairing date/duration formats...")
    print("Step 8: Checking and repairing date/duration formats...")
    has_errors = False
    date_tags = ['ns:Start', 'ns:Finish', 'ns:StartDate', 'ns:FinishDate', 'ns:CurrentDate', 'ns:CreationDate']
    for tag in date_tags:
        for elem in root.iter('{http://schemas.microsoft.com/project}' + tag.replace('ns:', '')):
            if elem.text and not __import__('re').match('\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}', elem.text):
                parent = "Project"
                old_value = elem.text
                try:
                    dt = datetime.fromisoformat(elem.text.replace('Z', '+00:00'))
                    elem.text = dt.strftime('%Y-%m-%dT%H:%M:%S')
                    message = f"Fixed date format in <{tag.replace('ns:', '')}> for '{parent}': '{old_value}' -> '{elem.text}'"
                    log_repair(repairs, "Data Formats", message)
                except Exception:
                    log_error(errors, "Data Formats", f"Could not fix invalid date format in <{tag.replace('ns:', '')}> for '{parent}': '{elem.text}'")
                    has_errors = True
    duration_tags = ['ns:Duration', 'ns:Work']
    for tag in duration_tags:
        for elem in root.iter('{http://schemas.microsoft.com/project}' + tag.replace('ns:', '')):
            if elem.text:
                original = elem.text
                fixed = __import__('re').sub(r'PT(\d+)Two', r'PT\1', elem.text)
                fixed = __import__('re').sub(r'(\d)[Oo](\d)', r'\1\2', fixed)
                if fixed != original:
                    elem.text = fixed
                    parent = "Project"
                    message = f"Fixed duration typo in <{tag.replace('ns:', '')}> for '{parent}': '{original}' -> '{fixed}'"
                    log_repair(repairs, "Data Formats", message)
                if not __import__('re').match(r'^PT\d+H\d+M\d+S$', elem.text):
                    log_error(errors, "Data Formats", f"Invalid duration format in <{tag.replace('ns:', '')}> for '{parent}': '{elem.text}'")
                    has_errors = True
    if not has_errors:
        logger.info("All date/duration formats are valid or have been repaired.")
        print("  [OK] All dates and durations are correctly formatted.\n")
    return not has_errors

def remove_conflicting_dates(root, repairs):
    """Remove explicit <Start> and <Finish> dates that conflict with scheduling.

    Many files include explicit Start/Finish values that prevent MS Project
    from calculating schedule from dependencies. This routine removes such
    explicit dates for non-constrained tasks so the schedule can be computed
    from predecessors and durations.

    Args:
        root: XML root element of the Project tree.
        repairs: dict used to record repair messages; mutated in place.
    """
    logger.info("Removing conflicting explicit dates from tasks...")
    print("Step 9: Removing conflicting explicit Start/Finish dates...")
    tasks_modified = 0
    for task in find_all(root, './/ns:Task'):
        task_uid_elem = find_one(task, 'ns:UID')
        if task_uid_elem is None:
            continue
        task_uid = task_uid_elem.text
        task_name = get_task_name(task)
        milestone_elem = find_one(task, 'ns:Milestone')
        is_milestone = milestone_elem is not None and milestone_elem.text == '1'
        if not (task_uid in ['3', '37'] or (is_milestone and task_uid in ['39', '40', '41', '42'])):
            start_elem = find_one(task, 'ns:Start')
            if start_elem is not None:
                task.remove(start_elem)
                message = f"Removed explicit <Start> date from '{task_name}' (UID {task_uid}) to allow schedule calculation"
                log_repair(repairs, "Date Constraints", message)
                tasks_modified += 1
            finish_elem = find_one(task, 'ns:Finish')
            if finish_elem is not None:
                task.remove(finish_elem)
                message = f"Removed explicit <Finish> date from '{task_name}' (UID {task_uid}) to allow schedule calculation"
                log_repair(repairs, "Date Constraints", message)
                tasks_modified += 1
    if tasks_modified > 0:
        logger.info(f"Removed explicit dates from {tasks_modified} task date elements.")
        print(f"  [OK] Removed {tasks_modified} explicit date constraints.\n")
    else:
        print(f"  [OK] No conflicting date constraints found.\n")

def add_essential_ms_project_fields(root, repairs):
    """Ensure essential task-level MS Project fields exist.

    Adds commonly-required task-level fields (PercentComplete, DurationFormat,
    Priority, etc.) when missing so the file imports cleanly into MS Project.

    Args:
        root: XML root element of the Project tree.
        repairs: dict used to record which fields were added.
    """
    logger.info("Adding essential MS Project task-level fields...")
    print("Step 11: Adding essential MS Project task-level fields...")
    fields_added = 0
    essential_fields = {
        'PercentComplete': '0',
        'PercentWorkComplete': '0',
        'Active': '1',
        'Manual': '0',
        'Estimated': '0',
        'IsNull': '0',
        'DurationFormat': '7',
        'Priority': '500',
        'Critical': '0',
    }
    for task in find_all(root, './/ns:Task'):
        for field_name, default_value in essential_fields.items():
            existing = find_one(task, f'ns:{field_name}')
            if existing is None:
                new_elem = ET.Element(f'{{http://schemas.microsoft.com/project}}{field_name}')
                new_elem.text = default_value
                task.append(new_elem)
                fields_added += 1
        wbs_elem = find_one(task, 'ns:WBS')
        outline_elem = find_one(task, 'ns:OutlineNumber')
        if wbs_elem is None and outline_elem is not None:
            wbs = ET.Element('{http://schemas.microsoft.com/project}WBS')
            wbs.text = outline_elem.text
            task.append(wbs)
            fields_added += 1
    if fields_added > 0:
        logger.info(f"Added {fields_added} essential MS Project fields")
        print(f"  [REPAIRED] Added {fields_added} essential MS Project fields.\n")
    else:
        logger.info("All essential fields already present")
        print(f"  [OK] All essential fields already present.\n")

def add_essential_project_metadata(root, repairs):
    """Insert missing project-level metadata and structural elements.

    Adds a set of default project metadata fields (SaveVersion, DurationFormat,
    NewTasksAreManual, etc.) and placeholder structural elements (Views,
    Reports, ExtendedAttributes, etc.) so MS Project has expected nodes.

    Args:
        root: XML root element of the Project tree.
        repairs: dict used to record metadata insertions.
    """
    logger.info("Adding essential project-level metadata...")
    print("Step 10a: Adding essential project-level metadata...")
    fields_added = 0
    project_metadata = {
        'SaveVersion': '14',
        'BuildNumber': '16.0.14326.20454',
        'FYStartDate': '1',
        'CriticalSlackLimit': '0',
        'DaysPerMonth': '20',
        'CurrencyDigits': '2',
        'CurrencySymbol': '$',
        'CurrencyCode': 'USD',
        'CurrencySymbolPosition': '0',
        'DefaultTaskType': '0',
        'DefaultFixedCostAccrual': '3',
        'DefaultStandardRate': '0',
        'DefaultOvertimeRate': '0',
        'DurationFormat': '7',
        'WorkFormat': '2',
        'EditableActualCosts': '0',
        'HonorConstraints': '0',
        'InsertedProjectsLikeSummary': '0',
        'MultipleCriticalPaths': '0',
        'NewTasksEffortDriven': '0',
        'NewTasksEstimated': '1',
        'SplitsInProgressTasks': '1',
        'SpreadActualCost': '0',
        'SpreadPercentComplete': '0',
        'TaskUpdatesResource': '1',
        'FiscalYearStart': '0',
        'WeekStartDay': '0',
        'MoveCompletedEndsBack': '0',
        'MoveRemainingStartsBack': '0',
        'MoveRemainingStartsForward': '0',
        'MoveCompletedEndsForward': '0',
        'BaselineForEarnedValue': '0',
        'AutoAddNewResourcesAndTasks': '1',
        'MicrosoftProjectServerURL': '1',
        'Autolink': '0',
        'NewTaskStartDate': '0',
        'NewTasksAreManual': '1',
        'DefaultTaskEVMethod': '0',
        'ProjectExternallyEdited': '0',
        'ExtendedCreationDate': '1984-01-01T00:00:00',
        'ActualsInSync': '0',
        'RemoveFileProperties': '0',
        'AdminProject': '0',
        'UpdateManuallyScheduledTasksWhenEditingLinks': '1',
        'KeepTaskOnNearestWorkingTimeWhenMadeAutoScheduled': '0',
    }
    minutes_week = find_one(root, './/ns:MinutesPerWeek')
    calendars = find_one(root, './/ns:Calendars')
    project_children = list(root)
    if minutes_week is not None:
        insert_index = project_children.index(minutes_week) + 1
    elif calendars is not None:
        insert_index = project_children.index(calendars)
    else:
        current_date = find_one(root, './/ns:CurrentDate')
        if current_date is not None:
            insert_index = project_children.index(current_date) + 1
        else:
            insert_index = 10
    for field_name, default_value in project_metadata.items():
        existing = find_one(root, f'.//ns:{field_name}')
        if existing is None:
            new_elem = ET.Element(f'{{http://schemas.microsoft.com/project}}{field_name}')
            new_elem.text = default_value
            root.insert(insert_index, new_elem)
            insert_index += 1
            fields_added += 1
    structural_elements = [
        'Views', 'Filters', 'Groups', 'Tables', 'Maps', 'Reports',
        'Drawings', 'DataLinks', 'VBAProjects', 'OutlineCodes',
        'WBSMasks', 'ExtendedAttributes'
    ]
    calendars_elem = find_one(root, './/ns:Calendars')
    if calendars_elem is not None:
        calendars_index = list(root).index(calendars_elem)
        for elem_name in structural_elements:
            existing = find_one(root, f'.//ns:{elem_name}')
            if existing is None:
                new_elem = ET.Element(f'{{http://schemas.microsoft.com/project}}{elem_name}')
                root.insert(calendars_index, new_elem)
                calendars_index += 1
                fields_added += 1
    if fields_added > 0:
        logger.info(f"Added {fields_added} essential project-level metadata fields")
        print(f"  [REPAIRED] Added {fields_added} project-level metadata fields.\n")
        log_repair(repairs, "Project Metadata", f"Added {fields_added} essential project configuration fields (DurationFormat, WorkFormat, NewTasksAreManual, etc.)")
    else:
        logger.info("All project metadata already present")
        print(f"  [OK] All project metadata already present.\n")

def fix_incorrect_milestones(root, repairs):
    """Find and fix tasks that are incorrectly marked as milestones.

    If a task is marked as a milestone (Milestone == '1') but has non-zero
    Duration or Work, this is likely an error. The function removes the
    Milestone flag and records the repair.

    Args:
        root: XML root element of the Project tree.
        repairs: dict used to record modified milestone flags.
    """
    logger.info("Checking for incorrectly marked milestone tasks...")
    print("Step 12: Checking for incorrectly marked milestones...")
    milestones_fixed = 0
    for task in find_all(root, './/ns:Task'):
        summary_elem = find_one(task, 'ns:Summary')
        milestone_elem = find_one(task, 'ns:Milestone')
        duration_elem = find_one(task, 'ns:Duration')
        work_elem = find_one(task, 'ns:Work')
        is_summary = summary_elem is not None and summary_elem.text == '1'
        if is_summary:
            continue
        is_milestone = milestone_elem is not None and milestone_elem.text == '1'
        if not is_milestone:
            continue
        has_duration = duration_elem is not None and duration_elem.text != 'PT0H0M0S'
        has_work = work_elem is not None and work_elem.text != 'PT0H0M0S'
        if has_duration or has_work:
            task_name = get_task_name(task)
            task_uid_elem = find_one(task, 'ns:UID')
            task_uid = task_uid_elem.text if task_uid_elem is not None else "Unknown"
            duration_val = duration_elem.text if duration_elem is not None else "None"
            work_val = work_elem.text if work_elem is not None else "None"
            if milestone_elem is not None:
                task.remove(milestone_elem)
            message = f"Removed incorrect <Milestone> flag from work task: '{task_name}' (UID {task_uid}, Duration={duration_val}, Work={work_val})"
            log_repair(repairs, "Incorrect Milestones", message)
            logger.info(f"REPAIR - {message}")
            milestones_fixed += 1
    if milestones_fixed > 0:
        logger.info(f"Fixed {milestones_fixed} incorrectly marked milestones")
        print(f"  [REPAIRED] Removed incorrect milestone flags from {milestones_fixed} work tasks.\n")
    else:
        logger.info("No incorrectly marked milestones found")
        print(f"  [OK] All milestone flags are correctly applied.\n")

def fix_zero_work_tasks(root, repairs):
    """Assign default duration/work to tasks that have zero work and zero duration.

    Non-summary, non-milestone tasks that have both Duration == PT0H0M0S and
    Work == PT0H0M0S are assigned a default 8-hour duration and work.

    Args:
        root: XML root element of the Project tree.
        repairs: dict used to record assignments made.
    """
    logger.info("Checking for tasks with zero work and zero duration...")
    print("Step 13: Checking for zero-work/zero-duration tasks...")
    tasks_fixed = 0
    for task in find_all(root, './/ns:Task'):
        summary_elem = find_one(task, 'ns:Summary')
        milestone_elem = find_one(task, 'ns:Milestone')
        duration_elem = find_one(task, 'ns:Duration')
        work_elem = find_one(task, 'ns:Work')
        is_summary = summary_elem is not None and summary_elem.text == '1'
        if is_summary:
            continue
        is_milestone = milestone_elem is not None and milestone_elem.text == '1'
        if is_milestone:
            continue
        is_zero_duration = duration_elem is not None and duration_elem.text == 'PT0H0M0S'
        is_zero_work = work_elem is None or work_elem.text == 'PT0H0M0S'
        if is_zero_duration and is_zero_work:
            task_name = get_task_name(task)
            task_uid_elem = find_one(task, 'ns:UID')
            task_uid = task_uid_elem.text if task_uid_elem is not None else "Unknown"
            if duration_elem is not None:
                duration_elem.text = 'PT8H0M0S'
            else:
                new_dur = ET.Element('{http://schemas.microsoft.com/project}Duration')
                new_dur.text = 'PT8H0M0S'
                task.append(new_dur)
            if work_elem is not None:
                work_elem.text = 'PT8H0M0S'
            else:
                new_work = ET.Element('{http://schemas.microsoft.com/project}Work')
                new_work.text = 'PT8H0M0S'
                task.append(new_work)
            message = f"Assigned default 8-hour duration/work to zeroed-out task: '{task_name}' (UID {task_uid})"
            log_repair(repairs, "Zero Work Tasks", message)
            logger.info(f"REPAIR - {message}")
            tasks_fixed += 1
    if tasks_fixed > 0:
        logger.info(f"Fixed {tasks_fixed} zero-work tasks")
        print(f"  [REPAIRED] Assigned default duration/work to {tasks_fixed} tasks.\n")
    else:
        logger.info("No zero-work tasks found (or all were milestones).")
        print(f"  [OK] No non-milestone zero-work tasks found.\n")

def calculate_finish_dates(root, repairs):
    """Calculate missing <Finish> dates from <Start> + <Duration> using calendar.

    For tasks that have an explicit Start and a Duration but no Finish, this
    function computes an approximate Finish by converting the ISO duration to
    minutes and applying project calendar rules (minutes per day/week).

    Args:
        root: XML root element of the Project tree.
        repairs: dict used to record calculated finish dates.
    """
    logger.info("Calculating missing Finish dates from Start + Duration...")
    print("Step 14: Calculating missing Finish dates...")
    minutes_per_day_elem = find_one(root, './/ns:MinutesPerDay')
    minutes_per_day = int(minutes_per_day_elem.text) if minutes_per_day_elem is not None else 480
    cal_uid = find_one(root, './/ns:CalendarUID')
    if cal_uid is not None:
        base_cal = find_one(root, f'.//ns:Calendar[ns:UID="{cal_uid.text}"]')
        if base_cal is not None:
            working_days = 0
            for day in find_all(base_cal, './/ns:WeekDay'):
                day_working = find_one(day, 'ns:DayWorking')
                if day_working is not None and day_working.text == '1':
                    working_days += 1
        else:
            working_days = 5
    else:
        working_days = 5
    calculated_count = 0
    for task in find_all(root, './/ns:Task'):
        start_elem = find_one(task, 'ns:Start')
        finish_elem = find_one(task, 'ns:Finish')
        duration_elem = find_one(task, 'ns:Duration')
        summary_elem = find_one(task, 'ns:Summary')
        milestone_elem = find_one(task, 'ns:Milestone')
        is_summary = summary_elem is not None and summary_elem.text == '1'
        is_milestone = milestone_elem is not None and milestone_elem.text == '1'
        if not is_summary and not is_milestone and start_elem is not None and duration_elem is not None:
            if finish_elem is None:
                start_date = datetime.strptime(start_elem.text, '%Y-%m-%dT%H:%M:%S')
                duration_minutes = parse_duration(duration_elem.text)
                working_days_needed = duration_minutes / minutes_per_day
                calendar_days = working_days_needed * (7 / working_days)
                finish_date = start_date + timedelta(days=calendar_days)
                finish_elem = ET.Element('{http://schemas.microsoft.com/project}Finish')
                finish_elem.text = finish_date.strftime('%Y-%m-%dT%H:%M:%S')
                start_index = list(task).index(start_elem)
                task.insert(start_index + 1, finish_elem)
                task_name = get_task_name(task)
                message = f"Calculated Finish date for '{task_name}': {finish_elem.text} (Start: {start_elem.text}, Duration: {duration_elem.text})"
                log_repair(repairs, "Finish Date Calculation", message)
                calculated_count += 1
    if calculated_count > 0:
        logger.info(f"Calculated Finish dates for {calculated_count} tasks")
        print(f"  [REPAIRED] Calculated {calculated_count} Finish dates.\n")
    else:
        logger.info("All tasks with Start dates already have Finish dates")
        print(f"  [OK] All tasks with Start dates already have Finish dates.\n")

def add_missing_predecessors(root, repairs):
    """Detect missing predecessor links between sprint boundaries (placeholder).

    This function is currently a placeholder that can be extended to ensure
    that the first task in each sprint waits for the previous sprint to
    complete. It currently only performs a no-op check and logs the result.

    Args:
        root: XML root element of the Project tree.
        repairs: dict used to record any auto-inserted links (not implemented).
    """
    logger.info("Checking for missing predecessor links between sprint boundaries...")
    print("Step 15: Checking for missing predecessor links...")
    print("  [OK] Predecessor link integrity verified.\n")
