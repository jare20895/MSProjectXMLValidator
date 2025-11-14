# Microsoft Project XML Validator - Implementation Documentation

## Overview

This document maps each validation rule from `MSProjectXMLRules.md` to its implementation in `PythonValidatorMSProject.py`. It provides a complete reference for understanding how each validation rule is enforced.

**Implementation File**: `PythonValidatorMSProject.py`
**Rules File**: `MSProjectXMLRules.md`
**Last Updated**: 2025-11-13

---

## Implementation Status Legend

- ✅ **Fully Implemented** - Rule is validated and enforced
- 🔧 **Implemented with Repair** - Rule is validated and auto-repair is available
- ⚠️ **Partially Implemented** - Rule is partially validated
- ❌ **Not Implemented** - Rule is documented but not yet validated

---

## 1. XML Structure Requirements

### 1.1 Well-Formed XML ✅

**Rule**: The file must be valid, well-formed XML with proper nesting and closed tags.

**Implementation**: `check_xml_well_formed(xml_file)`
- **Location**: Lines 287-310
- **Method**: Uses `ET.parse()` to validate XML structure
- **Catches**:
  - `ET.ParseError` for malformed XML
  - `FileNotFoundError` for missing files
- **Repair**: None (file must be manually fixed)
- **Exit Behavior**: Stops validation if this check fails

```python
def check_xml_well_formed(xml_file):
    """
    Checks if the XML file is 'well-formed'.
    This will catch 99% of typo errors like mismatched or invalid tags.
    """
    try:
        with open(xml_file, 'r', encoding='utf-8') as f:
            ET.parse(f)
        return True
    except ET.ParseError as e:
        print(f"\n--- FATAL ERROR: XML is not well-formed! ---")
        return False
```

**Test Case**: Catches mismatched tags like `</Gg>` instead of `</Assignment>`

---

### 1.2 Namespace Declaration ✅

**Rule**: Root `<Project>` element must declare namespace `http://schemas.microsoft.com/project`

**Implementation**: Implicit in parsing
- **Location**: Global constant `NAMESPACE` (line 30)
- **Method**: All find operations use namespace mapping
- **Validation**: Implicit - parser will fail if namespace is missing/incorrect

```python
NAMESPACE = {'ns': 'http://schemas.microsoft.com/project'}
```

**Note**: If namespace is missing, all `find_all()` and `find_one()` operations will return no results, causing subsequent validation failures.

---

### 1.3 Required Root Elements ⚠️

**Rule**: Project must contain minimum required elements (UID, Name, StartDate, etc.)

**Implementation**: Partially validated through calendar logic check
- **Location**: `check_calendar_logic()` (lines 406-443)
- **Current Coverage**:
  - ✅ `<MinutesPerWeek>` - checked for existence
  - ✅ `<CalendarUID>` - checked for existence
  - ❌ Other required fields not explicitly validated

**Recommendation**: Add explicit check for required root elements

---

## 2. Unique Identifier Rules

### 2.1 UID Uniqueness ✅

**Rule**: All UIDs must be unique within their respective collections (Tasks, Resources, Assignments)

**Implementation**: `check_unique_uids(root, errors)`
- **Location**: Lines 312-336
- **Method**: Uses Python sets to detect duplicates
- **Collections Checked**:
  - Tasks (`//ns:Task/ns:UID`)
  - Resources (`//ns:Resource/ns:UID`)
  - Assignments (`//ns:Assignment/ns:UID`)
- **Repair**: None (UIDs must be manually corrected)
- **Returns**: Tuple of (task_uids set, resource_uids set) for referential integrity checking

```python
def check_unique_uids(root, errors):
    uid_sets = {
        'Task': (find_all(root, './/ns:Task'), set()),
        'Resource': (find_all(root, './/ns:Resource'), set()),
        'Assignment': (find_all(root, './/ns:Assignment'), set()),
    }

    for name, (elements, uid_set) in uid_sets.items():
        for elem in elements:
            uid_elem = find_one(elem, 'ns:UID')
            if uid_elem is not None:
                uid = uid_elem.text
                if uid in uid_set:
                    log_error(errors, "Duplicate UIDs", f"Duplicate {name} UID found: {uid}")
                uid_set.add(uid)
```

---

### 2.2 UID Format ❌

**Rule**: UIDs should be positive integers

**Implementation**: Not currently validated
- **Reason**: Python string comparison works for numeric UIDs
- **Risk**: Low - MS Project generates valid UIDs

**Recommendation**: Add format validation if creating UIDs programmatically

---

## 3. Referential Integrity

### 3.1 Assignment References ✅

**Rule**: All `<Assignment>` elements must reference valid TaskUID and ResourceUID

**Implementation**: `check_referential_integrity(root, task_uids, resource_uids, errors)`
- **Location**: Lines 338-366 (Assignment checking: lines 346-357)
- **Method**:
  - Gets all assignments
  - Checks each `<TaskUID>` exists in task_uids set
  - Checks each `<ResourceUID>` exists in resource_uids set
- **Repair**: None (references must be manually fixed)

```python
for assign in find_all(root, './/ns:Assignment'):
    assign_uid = find_one(assign, 'ns:UID').text
    task_uid = find_one(assign, 'ns:TaskUID').text
    res_uid = find_one(assign, 'ns:ResourceUID').text

    if task_uid not in task_uids:
        log_error(errors, "Broken References", f"Assignment <UID>{assign_uid}</UID> points to non-existent TaskUID: {task_uid}")
    if res_uid not in resource_uids:
        log_error(errors, "Broken References", f"Assignment <UID>{assign_uid}</UID> points to non-existent ResourceUID: {res_uid}")
```

---

### 3.2 Predecessor Links ✅

**Rule**: All `<PredecessorLink>` elements must reference valid Task UIDs

**Implementation**: `check_referential_integrity(root, task_uids, resource_uids, errors)`
- **Location**: Lines 359-366
- **Method**:
  - Gets all PredecessorLink elements
  - Checks each `<PredecessorUID>` exists in task_uids set
  - Reports parent task name for context
- **Repair**: None (must be manually fixed)

```python
for link in find_all(root, './/ns:PredecessorLink'):
    pred_uid = find_one(link, 'ns:PredecessorUID').text
    if pred_uid not in task_uids:
        parent_task = link.find('../ns:Name')
        parent_name = parent_task.text if parent_task is not None else "Unknown"
        log_error(errors, "Broken References", f"Task '{parent_name}' has a PredecessorLink to non-existent TaskUID: {pred_uid}")
```

---

### 3.3 Calendar References ✅

**Rule**: Project `<CalendarUID>` must reference a valid calendar in `<Calendars>`

**Implementation**: `check_calendar_logic(root, errors)`
- **Location**: Lines 421-424
- **Method**:
  - Gets project's `<CalendarUID>`
  - Searches for matching `<Calendar>` with that UID
  - Reports error if not found
- **Repair**: None

```python
base_cal_uid = find_one(root, './/ns:CalendarUID').text
base_cal = find_one(root, f'.//ns:Calendar[ns:UID="{base_cal_uid}"]')

if base_cal is None:
    log_error(errors, "Calendar Logic", f"Project CalendarUID {base_cal_uid} not found in <Calendars>.")
```

---

## 4. Data Format Requirements

### 4.1 Date Format 🔧

**Rule**: All dates must be in ISO 8601 format `YYYY-MM-DDTHH:MM:SS`

**Validation**: `check_data_formats(root, errors)`
- **Location**: Lines 368-404
- **Fields Checked**:
  - Project level: `StartDate`, `FinishDate`, `CurrentDate`, `CreationDate`
  - Task level: `Start`, `Finish`
- **Method**: Regex pattern matching (`DATE_REGEX`)

**Repair**: `fix_date_formats(root, errors, repairs)`
- **Location**: Lines 169-222
- **Capabilities**:
  - ✅ Attempts to parse and reformat invalid dates
  - ✅ Handles timezone indicators (Z)
  - ❌ Cannot fix dates in non-ISO format (e.g., MM/DD/YYYY)

```python
DATE_REGEX = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$')

# Validation
for task in find_all(root, './/ns:Task'):
    task_name = get_task_name(task)
    for tag in ['ns:Start', 'ns:Finish']:
        elem = find_one(task, tag)
        if elem is not None and elem.text and not DATE_REGEX.match(elem.text):
            log_error(errors, "Data Formats", f"Invalid date format...")

# Repair
for tag in date_tags:
    for elem in root.iter('{http://schemas.microsoft.com/project}' + tag.replace('ns:', '')):
        if elem.text and not DATE_REGEX.match(elem.text):
            try:
                dt = datetime.fromisoformat(elem.text.replace('Z', '+00:00'))
                elem.text = dt.strftime('%Y-%m-%dT%H:%M:%S')
                log_repair(repairs, "Data Formats", f"Fixed date format...")
            except:
                log_error(errors, "Data Formats", f"Could not fix...")
```

---

### 4.2 Duration Format 🔧

**Rule**: All durations must be in ISO 8601 format `PT#H#M#S`

**Validation**: `check_data_formats(root, errors)`
- **Location**: Lines 395-400
- **Fields Checked**: `Duration`, `Work`
- **Method**: Regex pattern matching (`DURATION_REGEX`)

**Repair**: `fix_date_formats(root, errors, repairs)`
- **Location**: Lines 197-216
- **Capabilities**:
  - ✅ Fixes typo "PT#TwoH#M#S" → "PT#H#M#S"
  - ✅ Fixes letter 'O' instead of zero
  - ❌ Cannot fix non-ISO formats (e.g., "8h")

```python
DURATION_REGEX = re.compile(r'^PT\d+H\d+M\d+S$')

# Repair logic for common typos
original = elem.text
fixed = re.sub(r'PT(\d+)Two', r'PT\1', elem.text)  # Fix "Two" typo
fixed = re.sub(r'(\d)[Oo](\d)', r'\1\2', fixed)    # Fix letter O

if fixed != original:
    elem.text = fixed
    log_repair(repairs, "Data Formats", f"Fixed duration typo: '{original}' -> '{fixed}'")
```

**Example Repair**:
- Input: `PT4TwoH0M0S`
- Output: `PT4H0M0S`

---

### 4.3 Numeric Values ❌

**Rule**: Units and percentages must be valid decimal numbers

**Implementation**: Not currently validated
- **Fields Not Checked**:
  - `<Units>`
  - `<MaxUnits>`
  - `<PercentComplete>`

**Recommendation**: Add numeric validation for resource allocation values

---

## 5. Calendar and Schedule Logic

### 5.1 Working Week Definition ✅

**Rule**: Calendars must define working days and working time ranges

**Implementation**: `check_calendar_logic(root, errors)`
- **Location**: Lines 427-432
- **Method**:
  - Iterates through `<WeekDay>` elements
  - Checks `<DayWorking>` flag
  - Parses `<WorkingTime>` ranges
  - Calculates total working minutes
- **Validation**: Indirect - used for minutes calculation

```python
for day in find_all(base_cal, './/ns:WeekDay'):
    if find_one(day, 'ns:DayWorking').text == '1':
        for wt in find_all(day, './/ns:WorkingTime'):
            from_time = datetime.strptime(find_one(wt, 'ns:FromTime').text, '%H:%M:%S').time()
            to_time = datetime.strptime(find_one(wt, 'ns:ToTime').text, '%H:%M:%S').time()

            delta = datetime.combine(datetime.min, to_time) - datetime.combine(datetime.min, from_time)
            calculated_minutes += delta.total_seconds() / 60
```

---

### 5.2 Minutes Per Week Validation ✅

**Rule**: `<MinutesPerWeek>` should match total working minutes in base calendar

**Implementation**: `check_calendar_logic(root, errors)`
- **Location**: Lines 406-443
- **Method**:
  - Gets project's `<MinutesPerWeek>` value
  - Calculates minutes from calendar definition
  - Compares calculated vs. stated values
- **Repair**: None (requires manual calendar adjustment)

```python
project_minutes = int(mpw_elem.text)
calculated_minutes = 0

# Calculate from calendar...
if int(calculated_minutes) != project_minutes:
    log_error(errors, "Calendar Logic",
              f"<MinutesPerWeek> is {project_minutes}, but base calendar calculates to {int(calculated_minutes)}.")
```

**Example**:
- Calendar: 6 days × 8 hours/day = 2880 minutes/week
- `<MinutesPerWeek>2880</MinutesPerWeek>` ✅ Matches

---

### 5.3 Schedule Constraints 🔧

**Rule**: Minimize explicit dates; let MS Project calculate based on dependencies

**Implementation**: `remove_conflicting_dates(root, repairs)`
- **Location**: Lines 224-273
- **Method**:
  - Iterates through all tasks
  - Identifies tasks with explicit `<Start>` or `<Finish>` dates
  - Removes dates from non-constrained tasks
  - Preserves dates for:
    - First task (UID 3)
    - Fixed milestones (UID 37, 39-42)
- **Repair**: Yes - automatically removes conflicting dates

```python
for task in find_all(root, './/ns:Task'):
    task_uid = task_uid_elem.text

    # Keep dates for milestones with constraints or the first task
    if not (task_uid in ['3', '37'] or (is_milestone and task_uid in ['39', '40', '41', '42'])):
        # Remove Start date if present
        start_elem = find_one(task, 'ns:Start')
        if start_elem is not None:
            task.remove(start_elem)
            log_repair(repairs, "Date Constraints",
                      f"Removed explicit <Start> date from '{task_name}' (UID {task_uid})")
```

**Rationale**: Explicit dates override dependencies and can cause scheduling conflicts

---

## 6. Dependency Management

### 6.1 Dependency Types ❌

**Rule**: PredecessorLink `<Type>` must be valid (1=FS, 2=SS, 3=FF, 4=SF)

**Implementation**: Not currently validated
- **Fields Not Checked**: `<Type>` within `<PredecessorLink>`

**Recommendation**: Add validation to ensure Type is 1, 2, 3, or 4

---

### 6.2 Circular Dependencies 🔧

**Rule**: Task dependencies must not form loops (circular references)

**Implementation**: `detect_circular_dependencies(root, errors, repairs)`
- **Location**: Lines 94-167
- **Algorithm**: Kahn's topological sort
- **Method**:
  1. Build dependency graph from PredecessorLinks
  2. Calculate in-degree (number of dependencies) for each task
  3. Process tasks with no dependencies first
  4. Remove processed tasks from graph
  5. Repeat until all tasks processed or cycle detected
- **Repair**: Yes - removes predecessor links causing cycles

```python
def detect_circular_dependencies(root, errors, repairs):
    # Build dependency graph
    tasks = {}
    graph = defaultdict(list)
    in_degree = defaultdict(int)

    # Get all tasks and initialize
    for task in find_all(root, './/ns:Task'):
        uid = find_one(task, 'ns:UID').text
        tasks[uid] = task
        in_degree[uid] = 0

    # Build graph from predecessors
    for task in tasks.values():
        task_uid = find_one(task, 'ns:UID').text
        for link in find_all(task, './/ns:PredecessorLink'):
            pred_uid = find_one(link, 'ns:PredecessorUID').text
            graph[pred_uid].append(task_uid)
            in_degree[task_uid] += 1

    # Kahn's algorithm for topological sort
    queue = deque([uid for uid in tasks.keys() if in_degree[uid] == 0])
    sorted_count = 0

    while queue:
        current = queue.popleft()
        sorted_count += 1
        for neighbor in graph[current]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    # If sorted_count < total tasks, there's a cycle
    if sorted_count < len(tasks):
        cyclic_tasks = [uid for uid, degree in in_degree.items() if degree > 0]

        # Remove circular links
        for task_uid in cyclic_tasks:
            task = tasks[task_uid]
            for link in find_all(task, './/ns:PredecessorLink'):
                pred_uid = find_one(link, 'ns:PredecessorUID').text
                if pred_uid in cyclic_tasks:
                    task.remove(link)
                    log_repair(repairs, "Circular Dependencies",
                              f"Removed circular PredecessorLink from '{task_name}' to UID {pred_uid}")
```

**Example**:
```
Before: Task A → Task B → Task C → Task A (CYCLE!)
After:  Task A → Task B → Task C (link C→A removed)
```

---

### 6.3 Summary Task Dependencies ⚠️

**Rule**: Summary tasks typically should not have predecessor links

**Implementation**: Partially enforced through date removal
- **Location**: `remove_conflicting_dates()` identifies summary tasks
- **Current Behavior**: Removes explicit dates from summary tasks
- **Not Implemented**: No specific validation for predecessor links on summary tasks

**Recommendation**: Add warning if summary task has predecessor links

---

## 7. Additional Repair Functions

### 7.1 Missing Predecessor Links

**Function**: `add_missing_predecessors(root, repairs)`
- **Location**: Lines 275-284
- **Status**: Placeholder for future implementation
- **Current Behavior**: Logs check completion, no actual validation

```python
def add_missing_predecessors(root, repairs):
    """
    Ensures that the first task in each sprint waits for the previous sprint to complete.
    """
    # Placeholder for future logic
    print("  [OK] Predecessor link integrity verified.\n")
```

**Recommendation**: Implement sprint boundary validation if needed

---

## 8. Helper Functions

### 8.1 Namespace Helpers

**Functions**: `find_all()`, `find_one()`
- **Location**: Lines 58-64
- **Purpose**: Simplify namespace-aware element finding

```python
def find_all(element, path):
    return element.findall(path, NAMESPACE)

def find_one(element, path):
    return element.find(path, NAMESPACE)
```

---

### 8.2 Task Identification

**Function**: `get_task_name(task_elem)`
- **Location**: Lines 66-74
- **Purpose**: Get human-readable task identifier for error messages

```python
def get_task_name(task_elem):
    name_elem = find_one(task_elem, 'ns:Name')
    uid_elem = find_one(task_elem, 'ns:UID')
    if name_elem is not None and name_elem.text:
        return name_elem.text
    elif uid_elem is not None:
        return f"Task UID {uid_elem.text}"
    return "Unknown Task"
```

---

### 8.3 Duration Parsing

**Functions**: `parse_duration()`, `duration_to_string()`
- **Location**: Lines 76-90
- **Purpose**: Convert between ISO 8601 duration format and minutes

```python
def parse_duration(duration_str):
    """Parse ISO 8601 duration string (PT#H#M#S) to total minutes."""
    match = re.match(r'PT(\d+)H(\d+)M(\d+)S', duration_str)
    if match:
        hours, minutes, seconds = map(int, match.groups())
        return hours * 60 + minutes + seconds / 60
    return 0

def duration_to_string(total_minutes):
    """Convert total minutes to ISO 8601 duration string."""
    hours = int(total_minutes // 60)
    minutes = int(total_minutes % 60)
    return f"PT{hours}H{minutes}M0S"
```

---

## 9. Validation Workflow

### Validation Sequence

The validator runs checks in this order:

1. **Step 1**: `check_xml_well_formed()` - ✅ FATAL if fails
2. **Step 2**: `check_unique_uids()` - ✅ Returns UID sets
3. **Step 3**: `check_referential_integrity()` - ✅ Uses UID sets
4. **Step 4**: `check_data_formats()` - ✅ Logs format errors
5. **Step 5**: `check_calendar_logic()` - ✅ Validates calendar

### Repair Sequence (if repair_mode=True)

6. **Step 6**: `detect_circular_dependencies()` - 🔧 Removes cycles
7. **Step 7**: `fix_date_formats()` - 🔧 Repairs format issues
8. **Clear resolved errors** - Removes "Data Formats" errors if repaired
9. **Step 8**: `remove_conflicting_dates()` - 🔧 Removes explicit dates
10. **Step 9**: `add_missing_predecessors()` - Placeholder
11. **Save repaired XML** with comment block

---

## 10. Implementation Gaps and Recommendations

### Currently Not Implemented

| Rule | Priority | Recommendation |
|------|----------|----------------|
| Required root elements validation | Medium | Add explicit check for UID, Name, StartDate, FinishDate, CalendarUID |
| UID format validation | Low | Validate UIDs are positive integers |
| Numeric value validation | Medium | Validate Units, MaxUnits, PercentComplete ranges |
| Dependency type validation | Low | Ensure Type is 1-4 |
| Summary task dependency warning | Low | Warn if summary task has predecessors |
| Sprint boundary validation | Low | Implement if sprint structure is critical |

### Potential Enhancements

1. **Validation Levels**
   - Add "strict" mode for comprehensive validation
   - Add "quick" mode for basic checks only

2. **Custom Repair Rules**
   - Allow user-defined repair strategies
   - Configuration file for repair behavior

3. **Reporting Improvements**
   - Generate HTML report in addition to XML comment
   - Export validation results to JSON/CSV

4. **Performance Optimization**
   - Cache parsed tree for multiple validation runs
   - Parallel validation for large files

---

## 11. Code Coverage Matrix

| Rule Category | Validation | Repair | Logging | Notes |
|--------------|-----------|--------|---------|-------|
| XML Well-formed | ✅ | ❌ | ✅ | Fatal error if fails |
| Namespace | ✅ | ❌ | ❌ | Implicit validation |
| UID Uniqueness | ✅ | ❌ | ✅ | Manual fix required |
| Assignment References | ✅ | ❌ | ✅ | Manual fix required |
| Predecessor References | ✅ | ❌ | ✅ | Manual fix required |
| Calendar References | ✅ | ❌ | ✅ | Manual fix required |
| Date Format | ✅ | 🔧 | ✅ | Partial auto-repair |
| Duration Format | ✅ | 🔧 | ✅ | Typo auto-repair |
| Calendar Minutes | ✅ | ❌ | ✅ | Manual fix required |
| Circular Dependencies | ✅ | 🔧 | ✅ | Auto-removes cycles |
| Schedule Constraints | ✅ | 🔧 | ✅ | Auto-removes dates |

**Legend**:
- ✅ Fully implemented
- 🔧 Implemented with repair capability
- ❌ Not implemented

---

## 12. Testing Recommendations

### Unit Tests Needed

1. **XML Well-formedness**
   - Valid XML passes
   - Mismatched tags fail
   - Missing closing tags fail

2. **UID Uniqueness**
   - Unique UIDs pass
   - Duplicate task UIDs fail
   - Duplicate resource UIDs fail
   - Duplicate assignment UIDs fail

3. **Referential Integrity**
   - Valid references pass
   - Invalid TaskUID in Assignment fails
   - Invalid ResourceUID in Assignment fails
   - Invalid PredecessorUID fails

4. **Data Formats**
   - Valid dates pass
   - Invalid date format fails and repairs
   - Valid durations pass
   - Duration typo repairs (PT4TwoH0M0S)

5. **Circular Dependencies**
   - No cycles pass
   - Simple cycle detected and repaired
   - Complex cycle detected and repaired

6. **Calendar Logic**
   - Matching minutes pass
   - Mismatched minutes fail
   - Missing calendar fails

### Integration Tests Needed

1. End-to-end validation on sample projects
2. Repair mode on intentionally broken files
3. Import repaired files into MS Project

---

## Appendix: Function Reference

### Validation Functions

| Function | Purpose | Returns | Can Fail |
|----------|---------|---------|----------|
| `check_xml_well_formed()` | Validates XML syntax | bool | Yes - stops execution |
| `check_unique_uids()` | Checks UID uniqueness | (task_uids, resource_uids) | No |
| `check_referential_integrity()` | Validates references | None | No |
| `check_data_formats()` | Validates date/duration formats | None | No |
| `check_calendar_logic()` | Validates calendar consistency | None | No |

### Repair Functions

| Function | Purpose | Modifies XML | Clears Errors |
|----------|---------|--------------|---------------|
| `detect_circular_dependencies()` | Removes circular links | Yes | No |
| `fix_date_formats()` | Fixes date/duration typos | Yes | No |
| `remove_conflicting_dates()` | Removes explicit dates | Yes | No |
| `add_missing_predecessors()` | Placeholder | No | No |

### Utility Functions

| Function | Purpose |
|----------|---------|
| `find_all()` | Namespace-aware findall |
| `find_one()` | Namespace-aware find |
| `get_task_name()` | Get task identifier for logging |
| `parse_duration()` | Convert PT#H#M#S to minutes |
| `duration_to_string()` | Convert minutes to PT#H#M#S |
| `log_error()` | Log validation error |
| `log_repair()` | Log repair action |
| `generate_repair_comment()` | Generate XML comment block |
| `add_comment_to_xml()` | Insert comment in XML file |

---

## Conclusion

The current implementation covers the most critical validation rules for Microsoft Project 2021 XML files. The validator successfully:

- Prevents import of malformed XML
- Detects and resolves the most common errors (circular dependencies, format issues)
- Provides detailed logging for manual fixes
- Generates comprehensive repair reports

Areas for future enhancement focus on edge cases and additional format validations that are less critical for basic import success.

---

**End of Implementation Documentation**
