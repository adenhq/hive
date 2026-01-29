# DateTime Tool

A comprehensive date and time manipulation tool for AI agents.

## Description

This tool provides date and time operations that AI agents commonly need, such as getting the current time, parsing dates, calculating differences, and formatting dates for display.

## Tools Provided

### 1. `get_current_datetime`

Get the current date and time with optional timezone support.

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `format` | str | No | `%Y-%m-%d %H:%M:%S` | Output format string |
| `timezone_offset` | int | No | None (local) | UTC offset in hours |

**Examples:**
```python
get_current_datetime()
# Returns: "2026-01-30 14:30:00"

get_current_datetime(format="%B %d, %Y")
# Returns: "January 30, 2026"

get_current_datetime(timezone_offset=-5)  # EST
# Returns: "2026-01-30 09:30:00"
```

---

### 2. `parse_date`

Parse a date string from various formats into a standard format.

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `date_string` | str | Yes | - | Date string to parse |
| `input_format` | str | No | Auto-detect | Format of input string |
| `output_format` | str | No | `%Y-%m-%d` | Desired output format |

**Supported Auto-Detect Formats (in priority order):**
1. `2026-01-30` (ISO)
2. `2026/01/30` (ISO with slashes)
3. `30-01-2026` (European with dashes)
4. `30/01/2026` (European with slashes)
5. `01-30-2026` (US with dashes)
6. `01/30/2026` (US with slashes)
7. `January 30, 2026` (Long month name)
8. `Jan 30, 2026` (Short month name)
9. `30 January 2026` (Day first, long month)
10. `30 Jan 2026` (Day first, short month)

> **Note on Ambiguous Dates:** For dates like `01/02/2026`, European format (DD/MM/YYYY)
> takes precedence over US format (MM/DD/YYYY). So `01/02/2026` is parsed as **February 1, 2026**.
> To avoid ambiguity, use `input_format` parameter or ISO format (`2026-01-02`).

**Examples:**
```python
parse_date("January 30, 2026")
# Returns: "2026-01-30"

parse_date("30/01/2026", output_format="%B %d, %Y")
# Returns: "January 30, 2026"
```

---

### 3. `format_date`

Convert a date from one format to another.

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `date_string` | str | Yes | - | Date string to format |
| `input_format` | str | No | `%Y-%m-%d` | Current format |
| `output_format` | str | No | `%B %d, %Y` | Desired format |

**Examples:**
```python
format_date("2026-01-30")
# Returns: "January 30, 2026"

format_date("2026-01-30", output_format="%d/%m/%Y")
# Returns: "30/01/2026"
```

---

### 4. `date_diff`

Calculate the difference between two dates.

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `date1` | str | Yes | - | First date |
| `date2` | str | Yes | - | Second date |
| `unit` | str | No | `days` | Unit: days/hours/minutes/seconds/human |
| `date_format` | str | No | `%Y-%m-%d` | Format of input dates |

**Examples:**
```python
date_diff("2026-01-30", "2026-02-06")
# Returns: "7.00 days"

date_diff("2026-01-30", "2026-01-25")
# Returns: "-5.00 days"

date_diff("2026-01-30", "2026-02-06", unit="human")
# Returns: "7 days after"
```

---

### 5. `add_time`

Add or subtract time from a date.

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `date_string` | str | Yes | - | Starting date |
| `days` | int | No | 0 | Days to add (negative to subtract) |
| `hours` | int | No | 0 | Hours to add |
| `minutes` | int | No | 0 | Minutes to add |
| `date_format` | str | No | `%Y-%m-%d` | Format of input date |
| `output_format` | str | No | Same as input | Format of output |

**Examples:**
```python
add_time("2026-01-30", days=7)
# Returns: "2026-02-06"

add_time("2026-01-30", days=-1)
# Returns: "2026-01-29"

add_time("2026-01-30 14:00:00", hours=2, date_format="%Y-%m-%d %H:%M:%S")
# Returns: "2026-01-30 16:00:00"
```

---

### 6. `compare_dates`

Compare two dates to determine which comes first.

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `date1` | str | Yes | - | First date |
| `date2` | str | Yes | - | Second date |
| `date_format` | str | No | `%Y-%m-%d` | Format of input dates |

**Examples:**
```python
compare_dates("2026-01-30", "2026-02-15")
# Returns: "'2026-01-30' is before '2026-02-15'"

compare_dates("2026-02-15", "2026-01-30")
# Returns: "'2026-02-15' is after '2026-01-30'"
```

---

### 7. `get_day_of_week`

Get the day of the week for a given date.

| Argument | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `date_string` | str | Yes | - | Date to check |
| `date_format` | str | No | `%Y-%m-%d` | Format of input date |

**Examples:**
```python
get_day_of_week("2026-01-30")
# Returns: "Friday"
```

---

## Common Format Codes

| Code | Meaning | Example |
|------|---------|---------|
| `%Y` | 4-digit year | 2026 |
| `%m` | Month (01-12) | 01 |
| `%d` | Day (01-31) | 30 |
| `%H` | Hour 24h (00-23) | 14 |
| `%I` | Hour 12h (01-12) | 02 |
| `%M` | Minute (00-59) | 30 |
| `%S` | Second (00-59) | 00 |
| `%p` | AM/PM | PM |
| `%B` | Full month name | January |
| `%b` | Short month name | Jan |
| `%A` | Full day name | Friday |
| `%a` | Short day name | Fri |

## Environment Variables

This tool does not require any environment variables.

## Error Handling

All functions return error strings starting with "Error:" when:
- Date string cannot be parsed with the specified format
- Invalid unit specified for date_diff
- Any unexpected error occurs

## Use Cases

1. **Scheduling Agent**: Calculate meeting times, check availability
2. **Deadline Tracker**: Compare dates, calculate days remaining
3. **Report Generator**: Format dates for different locales
4. **Calendar Agent**: Get day of week, add recurring events
