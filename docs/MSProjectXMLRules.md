# Microsoft Project XML Validation Rules

## Overview

This document describes the validation rules and schema requirements for Microsoft Project 2021 XML files. These rules ensure that XML files will successfully import into Microsoft Project without errors.

## Document Version

- **Target Application**: Microsoft Project 2021
- **XML Schema Namespace**: `http://schemas.microsoft.com/project`
- **Last Updated**: 2025-11-13
- **Based on Analysis**: RiseUpSprint1Corrected.xml (MS Project 2021 export)

---

## Table of Contents

1. [XML Structure Requirements](#xml-structure-requirements)
2. [Essential MS Project Fields](#essential-ms-project-fields)
3. [Unique Identifier Rules](#unique-identifier-rules)
4. [Referential Integrity](#referential-integrity)
5. [Data Format Requirements](#data-format-requirements)
6. [Calendar and Schedule Logic](#calendar-and-schedule-logic)
7. [Dependency Management](#dependency-management)
8. [Common Validation Errors](#common-validation-errors)
9. [Best Practices](#best-practices)
10. [Using the Validator Tool](#using-the-validator-tool)
11. [Reference](#reference)

---

## 1. XML Structure Requirements

### 1.1 Well-Formed XML

The file MUST be valid, well-formed XML:
- Proper XML declaration: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>`
  - **CRITICAL**: The `standalone="yes"` attribute is REQUIRED by Microsoft Project
- All tags must be properly closed
- Tags must be properly nested
- Special characters must be escaped (`&amp;`, `&lt;`, `&gt;`, `&quot;`, `&apos;`)

### 1.2 Namespace Declaration

The root `<Project>` element must declare the Microsoft Project namespace:

```xml
<Project xmlns="http://schemas.microsoft.com/project">
  ...
</Project>
```

### 1.3 Required Root Elements

Minimum required elements in the `<Project>` root:

- `<UID>` - Unique identifier for the project
- `<Name>` - Project name
- `<StartDate>` - Project start date
- `<FinishDate>` - Project finish date
- `<ScheduleFromStart>` - 1 for forward scheduling, 0 for backward
- `<CurrentDate>` - Current date for the project
- `<CalendarUID>` - UID of the base calendar

---

## 2. Essential MS Project Fields

### 2.1 Overview

Based on analysis of MS Project 2021 XML exports, certain fields are essential for proper task scheduling and display. While MS Project can import files with minimal fields, **including these essential fields ensures correct behavior** and prevents issues like "0 days?" duration display or incorrect scheduling.

### 2.2 Critical Task Fields

Every task should include these essential fields for proper scheduling:

| Field | Required Value | Purpose | Impact if Missing |
|-------|----------------|---------|-------------------|
| `DurationFormat` | `7` | Display format for durations (7=hours, 39=days, 53=hours?) | Tasks show "0 days?" instead of actual duration |
| `Estimated` | `0` | Whether duration is confirmed (0) or estimated (1) | MS Project treats duration as uncertain |
| `PercentComplete` | `0` | Task completion percentage (0-100) | Status tracking won't work properly |
| `Active` | `1` | Whether task is active (1) or inactive (0) | Task may not appear in schedules |
| `Manual` | `0` | Auto-scheduled (0) or manually scheduled (1) | Scheduling calculations fail |
| `IsNull` | `0` | Task exists (0) or is null (1) | Task may not display |
| `WBS` | (varies) | Work Breakdown Structure code (typically matches OutlineNumber) | Hierarchy tracking fails |

### 2.3 Recommended Task Fields

These fields are recommended for better project management:

| Field | Default Value | Purpose |
|-------|---------------|---------|
| `PercentWorkComplete` | `0` | Work completion percentage |
| `Priority` | `500` | Task priority (500 = medium) |
| `Critical` | `0` | Whether task is on critical path (0 or 1) |

### 2.4 DurationFormat Values

The `DurationFormat` field controls how MS Project displays durations:

**Standard Values:**
- `7` = **hours** (displays as "8 hrs") - **RECOMMENDED for confirmed durations**
- `39` = **days** (displays as "1 day", "2 days")
- `53` = **hours?** (displays as "8 hrs?") - Indicates estimated/uncertain duration

**CRITICAL**: Using `DurationFormat=53` or omitting this field causes MS Project to display durations as uncertain (with "?" suffix), which can make all tasks show "0 days?" even when durations are correctly specified.

**Best Practice**: Always use `DurationFormat=7` for tasks with confirmed durations in hours.

### 2.5 Complete Task Example

**Minimal Task (may cause display issues):**
```xml
<Task>
  <UID>3</UID>
  <Name>Story: Extend 'sys_user'</Name>
  <Type>0</Type>
  <Start>2025-11-10T08:00:00</Start>
  <Duration>PT8H0M0S</Duration>
  <Work>PT8H0M0S</Work>
  <OutlineNumber>1.1.1</OutlineNumber>
  <OutlineLevel>2</OutlineLevel>
</Task>
```
**Result in MS Project**: Shows "0 days?" instead of "8 hrs"

**Complete Task (with essential fields):**
```xml
<Task>
  <UID>3</UID>
  <Name>Story: Extend 'sys_user'</Name>
  <Type>0</Type>
  <Start>2025-11-10T08:00:00</Start>
  <Finish>2025-11-10T17:00:00</Finish>
  <Duration>PT8H0M0S</Duration>
  <DurationFormat>7</DurationFormat>
  <Work>PT8H0M0S</Work>
  <OutlineNumber>1.1.1</OutlineNumber>
  <OutlineLevel>2</OutlineLevel>
  <PercentComplete>0</PercentComplete>
  <PercentWorkComplete>0</PercentWorkComplete>
  <Active>1</Active>
  <Manual>0</Manual>
  <Estimated>0</Estimated>
  <IsNull>0</IsNull>
  <Priority>500</Priority>
  <Critical>0</Critical>
  <WBS>1.1.1</WBS>
</Task>
```
**Result in MS Project**: Shows "8 hrs" correctly ✅

### 2.6 Validator Auto-Addition

The validator (`PythonValidatorMSProject.py`) automatically adds all essential fields if they are missing, using the `add_essential_ms_project_fields()` function. This ensures that manually created XML files will import and schedule correctly in MS Project.

---

## 3. Unique Identifier Rules

### 3.1 UID Uniqueness

All `<UID>` elements must be unique within their respective collections:

- **Tasks**: Each task must have a unique UID within `<Tasks>`
- **Resources**: Each resource must have a unique UID within `<Resources>`
- **Assignments**: Each assignment must have a unique UID within `<Assignments>`
- **Calendars**: Each calendar must have a unique UID within `<Calendars>`

### 3.2 UID Format

UIDs must be:
- Positive integers
- Typically sequential starting from 1
- Represented as text content within `<UID>` tags

**Example:**
```xml
<Task>
  <UID>1</UID>
  <ID>1</ID>
  <Name>Task Name</Name>
  ...
</Task>
```

---

## 4. Referential Integrity

### 4.1 Assignment References

Every `<Assignment>` must reference valid UIDs:

- `<TaskUID>` must match a UID in `<Tasks>`
- `<ResourceUID>` must match a UID in `<Resources>`

**Example:**
```xml
<Assignment>
  <UID>1</UID>
  <TaskUID>3</TaskUID>       <!-- Must exist in Tasks -->
  <ResourceUID>2</ResourceUID> <!-- Must exist in Resources -->
  <Units>1.0</Units>          <!-- 1.0 = 100% allocation -->
</Assignment>
```

**Resource Units:**
- `1.0` = 100% allocation (full-time)
- `0.5` = 50% allocation (half-time)
- `0.25` = 25% allocation (quarter-time)
- `0` = No allocation (typically for summary tasks or milestones)

### 4.2 Predecessor Links

Every `<PredecessorLink>` must reference a valid Task UID:

```xml
<Task>
  <UID>5</UID>
  <Name>Dependent Task</Name>
  <PredecessorLink>
    <PredecessorUID>4</PredecessorUID> <!-- Must be a valid Task UID -->
    <Type>1</Type> <!-- 1=FS, 2=SS, 3=FF, 4=SF -->
  </PredecessorLink>
</Task>
```

### 4.3 Calendar References

The project `<CalendarUID>` must reference a valid calendar defined in `<Calendars>`:

```xml
<Project>
  <CalendarUID>1</CalendarUID>
  <Calendars>
    <Calendar>
      <UID>1</UID> <!-- Must match CalendarUID above -->
      <Name>Standard</Name>
      ...
    </Calendar>
  </Calendars>
</Project>
```

---

## 5. Data Format Requirements

### 5.1 Date Format

All dates must be in ISO 8601 format: `YYYY-MM-DDTHH:MM:SS`

**Valid:**
- `2025-11-10T08:00:00`
- `2025-12-18T17:30:00`

**Invalid:**
- `11/10/2025` (US format)
- `2025-11-10` (missing time)
- `2025-11-10 08:00:00` (space instead of T)

**Date Fields:**
- `<StartDate>`, `<FinishDate>` (Project level)
- `<Start>`, `<Finish>` (Task level)
- `<CurrentDate>`, `<CreationDate>`

### 5.2 Duration Format

All durations must be in ISO 8601 duration format: `PT#H#M#S`

**Valid:**
- `PT8H0M0S` (8 hours)
- `PT16H0M0S` (16 hours)
- `PT4H30M0S` (4.5 hours)

**Invalid:**
- `8h` (not ISO 8601)
- `PT4TwoH0M0S` (text in number field)
- `PT8H` (missing minutes and seconds)

**Duration Fields:**
- `<Duration>` - Task duration
- `<Work>` - Work effort

**See Also:** Section 2.4 for `DurationFormat` field values that control how durations are displayed in MS Project.

### 5.3 Numeric Values

Units and percentages must be decimal numbers:

- `<Units>` - Resource units (e.g., `1.0`, `0.5`, `0.25`)
- `<PercentComplete>` - Percentage (0-100)
- `<MaxUnits>` - Maximum units for a resource

---

## 6. Calendar and Schedule Logic

### 6.1 Working Week Definition

Calendars must define working days and times:

```xml
<Calendar>
  <UID>1</UID>
  <Name>Standard</Name>
  <IsBaseCalendar>1</IsBaseCalendar>
  <WeekDays>
    <WeekDay>
      <DayType>2</DayType> <!-- 1=Sun, 2=Mon, ..., 7=Sat -->
      <DayWorking>1</DayWorking> <!-- 1=working, 0=non-working -->
      <WorkingTimes>
        <WorkingTime>
          <FromTime>08:00:00</FromTime>
          <ToTime>12:00:00</ToTime>
        </WorkingTime>
        <WorkingTime>
          <FromTime>13:00:00</FromTime>
          <ToTime>17:00:00</ToTime>
        </WorkingTime>
      </WorkingTimes>
    </WeekDay>
  </WeekDays>
</Calendar>
```

### 6.2 Minutes Per Week Validation

The `<MinutesPerWeek>` value should match the total working minutes defined in the base calendar.

**Calculation:**
- Count working days (where `<DayWorking>1</DayWorking>`)
- Sum all working time intervals per day
- Multiply by 60 to convert to minutes
- Total should equal `<MinutesPerWeek>`

**Example:**
- 6 working days × 8 hours/day × 60 minutes/hour = 2880 minutes/week

### 6.3 Schedule Constraints

**Allow Microsoft Project to Calculate Dates:**
- Only set explicit `<Start>` and `<Finish>` dates for constrained tasks
- For most tasks, provide `<Duration>` and `<PredecessorLink>` and let MS Project calculate dates
- Summary tasks should NOT have explicit start/finish dates

**Milestone Tasks:**
- Must have `<Milestone>1</Milestone>`
- Should have `<Duration>PT0H0M0S</Duration>`
- Can have constrained dates if representing a fixed deadline

---

## 7. Dependency Management

### 7.1 Dependency Types

```xml
<PredecessorLink>
  <PredecessorUID>3</PredecessorUID>
  <Type>1</Type> <!-- Type values -->
</PredecessorLink>
```

**Dependency Types:**
- `1` = Finish-to-Start (FS) - Most common
- `2` = Start-to-Start (SS)
- `3` = Finish-to-Finish (FF)
- `4` = Start-to-Finish (SF) - Rarely used

### 7.2 Circular Dependencies

**CRITICAL**: Tasks must NOT have circular dependencies

**Invalid Example:**
```
Task A depends on Task B
Task B depends on Task C
Task C depends on Task A  � CIRCULAR!
```

The validator uses topological sorting (Kahn's algorithm) to detect circular dependencies.

### 7.3 Summary Task Dependencies

**CRITICAL RULE**: Summary tasks (where `<Summary>1</Summary>`) must **NEVER** have predecessor links.

**Why This Matters:**
- Summary task dates are automatically calculated from their child tasks
- Adding predecessor links to summary tasks creates implicit circular dependencies
- MS Project will report "circular relationship" errors during import
- This is the most common cause of circular dependency errors

**Correct Approach:**
- Always place predecessor links on the **first child task** of a summary, not on the summary itself
- Let MS Project calculate summary dates from child task dates
- Dependencies should only be between leaf (non-summary) tasks

**Invalid Example:**
```xml
<!-- WRONG: Summary task with predecessor -->
<Task>
  <UID>8</UID>
  <Name>Sprint 2</Name>
  <Summary>1</Summary>
  <PredecessorLink>
    <PredecessorUID>7</PredecessorUID>  <!-- ERROR: Summary should not have predecessors -->
    <Type>1</Type>
  </PredecessorLink>
</Task>
```

**Valid Example:**
```xml
<!-- CORRECT: Summary task without predecessor -->
<Task>
  <UID>8</UID>
  <Name>Sprint 2</Name>
  <Summary>1</Summary>
  <!-- No PredecessorLink -->
</Task>

<!-- CORRECT: First child task has the predecessor -->
<Task>
  <UID>9</UID>
  <Name>First Task in Sprint 2</Name>
  <Summary>0</Summary>
  <PredecessorLink>
    <PredecessorUID>7</PredecessorUID>  <!-- Correct: Predecessor on child task -->
    <Type>1</Type>
  </PredecessorLink>
</Task>
```

**Validator Behavior:**
The validator automatically detects summary task predecessors and moves them to the first child task using the `fix_summary_task_predecessors()` function.

---

## 8. Common Validation Errors

### 8.1 "Duplicate UID" Error

**Cause:** Two or more elements have the same `<UID>` value

**Fix:** Ensure all UIDs are unique within their collection (Tasks, Resources, or Assignments)

### 8.2 "Broken Reference" Error

**Cause:** An Assignment or PredecessorLink references a UID that doesn't exist

**Fix:**
- Verify the referenced UID exists
- Check for typos in UID values
- Ensure Tasks/Resources are defined before being referenced

### 8.3 "Invalid Date Format" Error

**Cause:** Date not in `YYYY-MM-DDTHH:MM:SS` format

**Common Mistakes:**
- `2025-11-10` → Should be `2025-11-10T08:00:00`
- `11/10/2025` → Should be `2025-11-10T08:00:00`
- `2025-11-10 08:00:00` → Should be `2025-11-10T08:00:00` (T not space)

### 8.4 "Invalid Duration Format" Error

**Cause:** Duration not in `PT#H#M#S` format

**Common Mistakes:**
- `8h` → Should be `PT8H0M0S`
- `PT4TwoH0M0S` → Should be `PT4H0M0S` (typo)
- `PT8H` → Should be `PT8H0M0S` (missing M and S)

### 8.5 "Circular Dependency" Error

**Cause:** Task dependencies form a loop

**Fix:**
- Map out all dependencies
- Remove the dependency creating the loop
- Restructure task relationships to eliminate cycles
- **Most Common**: Check for summary tasks with predecessors (see Section 7.3)

### 8.6 "Calendar Logic Mismatch" Error

**Cause:** `<MinutesPerWeek>` doesn't match calendar definition

**Fix:**
- Recalculate working hours from calendar
- Update `<MinutesPerWeek>` to match
- Or adjust calendar working times

### 8.7 "0 days?" Display Error (NEW)

**Symptom:** Tasks display as "0 days?" in MS Project instead of showing actual duration (e.g., "8 hrs")

**Cause:** Missing or incorrect essential MS Project fields, specifically:
- Missing `DurationFormat` field
- `DurationFormat=53` (estimated hours with "?") instead of `7` (confirmed hours)
- Missing or incorrect `Estimated` field (should be `0` for confirmed durations)
- Missing other essential fields (see Section 2)

**Example of Problem:**
```
Auto Scheduled    Story: Extend 'sys_user'    0 days?    Mon 11/10/25    Mon 11/10/25
```

**Fix:**
1. Add `<DurationFormat>7</DurationFormat>` to all tasks (for hours)
2. Add `<Estimated>0</Estimated>` to all tasks (for confirmed durations)
3. Add all essential MS Project fields (see Section 2.2)
4. Run the validator in repair mode to automatically add missing fields

**After Fix:**
```
Auto Scheduled    Story: Extend 'sys_user'    8 hrs    Mon 11/10/25    Mon 11/10/25
```

**Note:** The validator automatically adds all essential fields including `DurationFormat=7` and `Estimated=0` to prevent this issue.

---

## 9. Best Practices

### 9.1 Task Structure

1. **Use Summary Tasks** for organizing work into phases
   ```xml
   <Task>
     <UID>1</UID>
     <Name>Phase 1</Name>
     <Summary>1</Summary>
     <OutlineLevel>0</OutlineLevel>
   </Task>
   ```

2. **Use Outline Levels** to show hierarchy
   - Level 0 = Top-level summary
   - Level 1 = Sub-summary
   - Level 2+ = Detailed tasks

3. **Set Type Appropriately**
   - `0` = Fixed Units (default)
   - `1` = Fixed Duration
   - `2` = Fixed Work

4. **Include Essential Fields** - Always add the fields from Section 2.2 to prevent display issues

### 9.2 Dependency Best Practices

1. **Keep dependencies simple** - Use Finish-to-Start (Type 1) whenever possible
2. **Avoid long chains** - Break long dependency chains into summary groups
3. **Use lag/lead sparingly** - Prefer explicit tasks over lag time
4. **NEVER add predecessors to summary tasks** - See Section 7.3 for details

### 9.3 Date Management

1. **Minimize constraints** - Let MS Project calculate most dates
2. **Use milestones** for fixed deadlines
3. **Set project start date** - Let task dates flow from there
4. **Avoid explicit dates** on regular tasks - use duration + dependencies instead

### 9.4 Resource Allocation

1. **Define resources before assignments**
2. **Set realistic MaxUnits** - typically 1.0 for full-time
3. **Use Units appropriately** - 0.25 for 25% allocation, 1.0 for 100%
4. **Default to 100% allocation** - Use `Units=1.0` unless task requires partial time

### 9.5 Essential Fields Best Practices

1. **Always include DurationFormat** - Use `7` for hours, `39` for days
2. **Set Estimated=0** for confirmed durations (not `1` for estimated)
3. **Include WBS field** - Copy from OutlineNumber for proper hierarchy
4. **Use validator auto-add** - Run repair mode to add all essential fields automatically

### 9.6 Validation Workflow

1. **Always validate** before importing to MS Project
2. **Fix errors in order**:
   - XML well-formedness first
   - UIDs second
   - References third
   - Data formats fourth
   - Calendar logic last
3. **Test import** in MS Project after validation passes
4. **Keep backups** of working XML files

---

## 10. Using the Validator Tool

### 10.1 Validation Only Mode

```bash
python PythonValidatorMSProject.py ProjectSchedule.xml
```

This will check for errors without modifying the file.

### 10.2 Validation and Repair Mode

```bash
python PythonValidatorMSProject.py ProjectSchedule.xml ProjectSchedule_repaired.xml
```

This will:
1. Detect issues
2. Attempt automatic repairs (including adding essential MS Project fields)
3. Save the repaired file
4. Generate a separate repair log file (`.log`)
5. Report any issues that couldn't be automatically fixed

### 10.3 Understanding Repair Reports

The validator generates a separate repair log file (e.g., `ProjectSchedule_repaired_repair.log`):

```xml
<!--
================================================================================
MICROSOFT PROJECT XML - VALIDATION AND REPAIR REPORT
================================================================================
Generated: 2025-11-13 13:29:42

REPAIRS MADE:
--------------------------------------------------------------------------------
Data Formats: (1 repairs)
  * Fixed duration typo in <Work>: 'PT4TwoH0M0S' -> 'PT4H0M0S'

STATUS: All issues successfully repaired!
================================================================================
-->
```

---

## 11. Reference

### 11.1 Supported Microsoft Project Versions

- Microsoft Project 2021
- Microsoft Project 2019
- Microsoft Project 2016

### 11.2 Schema Documentation

Official Microsoft Project XML Schema:
- Namespace: `http://schemas.microsoft.com/project`
- Schema files available from Microsoft MSDN

### 11.3 Related Documentation

- **MS_PROJECT_EXPORT_ANALYSIS.md** - Detailed analysis of MS Project 2021 XML export structure
- **VALIDATOR_UPDATES_SUMMARY.md** - Summary of validator enhancements and fixes
- **implementation.md** - Technical implementation details of validator functions

### 11.4 Related Tools

- **PythonValidatorMSProject.py** - Validation and repair tool (this repository)
- **Microsoft Project** - Primary application for importing .xml files

### 11.5 Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0 | 2025-11-13 | Added essential MS Project fields section, DurationFormat details, enhanced summary task guidance |
| 1.5 | 2025-11-13 | Added "0 days?" error documentation, resource units clarification |
| 1.0 | 2025-11-13 | Initial documentation for Project 2021 schema |

---

## Appendix A: Complete Minimal Example

This example includes all essential MS Project fields for proper import and display.

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Project xmlns="http://schemas.microsoft.com/project">
  <UID>1</UID>
  <Name>Sample Project</Name>
  <StartDate>2025-01-01T08:00:00</StartDate>
  <FinishDate>2025-01-31T17:00:00</FinishDate>
  <ScheduleFromStart>1</ScheduleFromStart>
  <CurrentDate>2025-01-01T08:00:00</CurrentDate>
  <CalendarUID>1</CalendarUID>
  <DefaultStartTime>08:00:00</DefaultStartTime>
  <DefaultFinishTime>17:00:00</DefaultFinishTime>
  <MinutesPerDay>480</MinutesPerDay>
  <MinutesPerWeek>2400</MinutesPerWeek>

  <Calendars>
    <Calendar>
      <UID>1</UID>
      <Name>Standard</Name>
      <IsBaseCalendar>1</IsBaseCalendar>
      <WeekDays>
        <WeekDay>
          <DayType>2</DayType>
          <DayWorking>1</DayWorking>
          <WorkingTimes>
            <WorkingTime>
              <FromTime>08:00:00</FromTime>
              <ToTime>17:00:00</ToTime>
            </WorkingTime>
          </WorkingTimes>
        </WeekDay>
        <!-- Repeat for other working days -->
      </WeekDays>
    </Calendar>
  </Calendars>

  <Resources>
    <Resource>
      <UID>1</UID>
      <ID>1</ID>
      <Name>Developer</Name>
      <Type>1</Type>
      <MaxUnits>1.0</MaxUnits>
    </Resource>
  </Resources>

  <Tasks>
    <Task>
      <UID>1</UID>
      <ID>1</ID>
      <Name>Task 1</Name>
      <Type>0</Type>
      <Start>2025-01-01T08:00:00</Start>
      <Finish>2025-01-01T17:00:00</Finish>
      <Duration>PT8H0M0S</Duration>
      <DurationFormat>7</DurationFormat>
      <Work>PT8H0M0S</Work>
      <OutlineNumber>1</OutlineNumber>
      <OutlineLevel>0</OutlineLevel>
      <PercentComplete>0</PercentComplete>
      <PercentWorkComplete>0</PercentWorkComplete>
      <Active>1</Active>
      <Manual>0</Manual>
      <Estimated>0</Estimated>
      <IsNull>0</IsNull>
      <Priority>500</Priority>
      <Critical>0</Critical>
      <WBS>1</WBS>
    </Task>

    <Task>
      <UID>2</UID>
      <ID>2</ID>
      <Name>Task 2</Name>
      <Type>0</Type>
      <Duration>PT16H0M0S</Duration>
      <DurationFormat>7</DurationFormat>
      <Work>PT16H0M0S</Work>
      <OutlineNumber>2</OutlineNumber>
      <OutlineLevel>0</OutlineLevel>
      <PercentComplete>0</PercentComplete>
      <PercentWorkComplete>0</PercentWorkComplete>
      <Active>1</Active>
      <Manual>0</Manual>
      <Estimated>0</Estimated>
      <IsNull>0</IsNull>
      <Priority>500</Priority>
      <Critical>0</Critical>
      <WBS>2</WBS>
      <PredecessorLink>
        <PredecessorUID>1</PredecessorUID>
        <Type>1</Type>
      </PredecessorLink>
    </Task>
  </Tasks>

  <Assignments>
    <Assignment>
      <UID>1</UID>
      <TaskUID>1</TaskUID>
      <ResourceUID>1</ResourceUID>
      <Units>1.0</Units>
    </Assignment>

    <Assignment>
      <UID>2</UID>
      <TaskUID>2</TaskUID>
      <ResourceUID>1</ResourceUID>
      <Units>1.0</Units>
    </Assignment>
  </Assignments>
</Project>
```

---

**End of Documentation**
