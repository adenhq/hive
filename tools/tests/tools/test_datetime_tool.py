"""Tests for datetime_tool - Date and time operations for AI agents."""

import pytest
from fastmcp import FastMCP

from aden_tools.tools.datetime_tool.datetime_tool import register_tools


@pytest.fixture
def datetime_tools(mcp: FastMCP):
    """Register datetime tools and return them as a dict."""
    register_tools(mcp)
    return {
        "get_current_datetime": mcp._tool_manager._tools["get_current_datetime"].fn,
        "parse_date": mcp._tool_manager._tools["parse_date"].fn,
        "format_date": mcp._tool_manager._tools["format_date"].fn,
        "date_diff": mcp._tool_manager._tools["date_diff"].fn,
        "add_time": mcp._tool_manager._tools["add_time"].fn,
        "compare_dates": mcp._tool_manager._tools["compare_dates"].fn,
        "get_day_of_week": mcp._tool_manager._tools["get_day_of_week"].fn,
    }


class TestGetCurrentDatetime:
    """Tests for get_current_datetime."""

    def test_default_format(self, datetime_tools):
        """Default format returns YYYY-MM-DD HH:MM:SS."""
        result = datetime_tools["get_current_datetime"]()
        # Should match pattern 2026-01-30 14:30:00
        parts = result.split()
        assert len(parts) >= 2
        date_parts = parts[0].split("-")
        assert len(date_parts) == 3
        assert int(date_parts[0]) >= 2020
        assert 1 <= int(date_parts[1]) <= 12
        assert 1 <= int(date_parts[2]) <= 31

    def test_custom_date_only_format(self, datetime_tools):
        """Custom format %Y-%m-%d returns date only."""
        result = datetime_tools["get_current_datetime"](format="%Y-%m-%d")
        assert len(result.split("-")) == 3
        assert " " not in result

    def test_custom_month_name_format(self, datetime_tools):
        """Format %B %d, %Y returns e.g. January 30, 2026."""
        result = datetime_tools["get_current_datetime"](format="%B %d, %Y")
        assert "," in result
        assert result[0].isalpha()

    def test_timezone_offset_utc(self, datetime_tools):
        """timezone_offset=0 gives UTC-like result."""
        result = datetime_tools["get_current_datetime"](
            format="%Y-%m-%d %H:%M:%S", timezone_offset=0
        )
        assert "Error" not in result
        assert len(result) >= 19

    def test_timezone_offset_positive(self, datetime_tools):
        """Positive offset (e.g. IST +5:30) works."""
        result = datetime_tools["get_current_datetime"](
            format="%Y-%m-%d %H:%M:%S", timezone_offset=5
        )
        assert "Error" not in result

    def test_timezone_offset_negative(self, datetime_tools):
        """Negative offset (e.g. EST -5) works."""
        result = datetime_tools["get_current_datetime"](
            format="%Y-%m-%d %H:%M:%S", timezone_offset=-5
        )
        assert "Error" not in result


class TestParseDate:
    """Tests for parse_date."""

    def test_iso_input_default_output(self, datetime_tools):
        """Parse 2026-01-30 with no format returns same format by default."""
        result = datetime_tools["parse_date"](date_string="2026-01-30")
        assert result == "2026-01-30"

    def test_parse_with_explicit_input_format(self, datetime_tools):
        """Parse January 30, 2026 with %B %d, %Y."""
        result = datetime_tools["parse_date"](
            date_string="January 30, 2026",
            input_format="%B %d, %Y",
            output_format="%Y-%m-%d",
        )
        assert result == "2026-01-30"

    def test_parse_dmy_slash(self, datetime_tools):
        """Parse 30/01/2026 (d/m/y) auto-detected."""
        result = datetime_tools["parse_date"](
            date_string="30/01/2026",
            output_format="%Y-%m-%d",
        )
        assert result == "2026-01-30"

    def test_parse_short_month(self, datetime_tools):
        """Parse Jan 30, 2026."""
        result = datetime_tools["parse_date"](
            date_string="Jan 30, 2026",
            output_format="%Y-%m-%d",
        )
        assert result == "2026-01-30"

    def test_parse_iso_datetime(self, datetime_tools):
        """Parse ISO datetime 2026-01-30T14:30:00."""
        result = datetime_tools["parse_date"](
            date_string="2026-01-30T14:30:00",
            output_format="%Y-%m-%d",
        )
        assert result == "2026-01-30"

    def test_parse_invalid_date_returns_error(self, datetime_tools):
        """Invalid date string returns Error."""
        result = datetime_tools["parse_date"](date_string="not-a-date")
        assert "Error" in result
        assert "parse" in result.lower() or "Could not" in result

    def test_parse_empty_string_returns_error(self, datetime_tools):
        """Empty string returns error."""
        result = datetime_tools["parse_date"](date_string="")
        assert "Error" in result

    def test_parse_wrong_explicit_format_returns_error(self, datetime_tools):
        """Wrong input_format returns error."""
        result = datetime_tools["parse_date"](
            date_string="2026-01-30",
            input_format="%d/%m/%Y",  # expects 30/01/2026
        )
        assert "Error" in result


class TestFormatDate:
    """Tests for format_date."""

    def test_iso_to_human(self, datetime_tools):
        """Convert 2026-01-30 to January 30, 2026."""
        result = datetime_tools["format_date"](
            date_string="2026-01-30",
            input_format="%Y-%m-%d",
            output_format="%B %d, %Y",
        )
        assert result == "January 30, 2026"

    def test_same_format_passthrough(self, datetime_tools):
        """Same input and output format returns unchanged."""
        result = datetime_tools["format_date"](
            date_string="2026-01-30",
            input_format="%Y-%m-%d",
            output_format="%Y-%m-%d",
        )
        assert result == "2026-01-30"

    def test_iso_to_dmy_slash(self, datetime_tools):
        """Convert to DD/MM/YYYY."""
        result = datetime_tools["format_date"](
            date_string="2026-01-30",
            input_format="%Y-%m-%d",
            output_format="%d/%m/%Y",
        )
        assert result == "30/01/2026"

    def test_invalid_input_returns_error(self, datetime_tools):
        """Invalid date string returns Error."""
        result = datetime_tools["format_date"](
            date_string="invalid",
            input_format="%Y-%m-%d",
        )
        assert "Error" in result

    def test_wrong_input_format_returns_error(self, datetime_tools):
        """Wrong input_format returns error."""
        result = datetime_tools["format_date"](
            date_string="30/01/2026",
            input_format="%Y-%m-%d",
        )
        assert "Error" in result


class TestDateDiff:
    """Tests for date_diff."""

    def test_diff_days_positive(self, datetime_tools):
        """date2 after date1 returns positive days."""
        result = datetime_tools["date_diff"](
            date1="2026-01-01",
            date2="2026-01-11",
            unit="days",
        )
        assert "10.00 days" == result

    def test_diff_days_negative(self, datetime_tools):
        """date2 before date1 returns negative days."""
        result = datetime_tools["date_diff"](
            date1="2026-01-11",
            date2="2026-01-01",
            unit="days",
        )
        assert "-10.00 days" == result

    def test_diff_same_date_zero(self, datetime_tools):
        """Same date returns 0 days."""
        result = datetime_tools["date_diff"](
            date1="2026-01-30",
            date2="2026-01-30",
            unit="days",
        )
        assert "0.00 days" == result

    def test_diff_hours(self, datetime_tools):
        """Unit hours returns hours."""
        result = datetime_tools["date_diff"](
            date1="2026-01-30 00:00:00",
            date2="2026-01-30 02:30:00",
            unit="hours",
            date_format="%Y-%m-%d %H:%M:%S",
        )
        assert "hours" in result
        assert "2.50" in result or "2.5" in result

    def test_diff_human_readable(self, datetime_tools):
        """Unit human returns 'X days, Y hours after/before'."""
        result = datetime_tools["date_diff"](
            date1="2026-01-01",
            date2="2026-01-03",
            unit="human",
        )
        assert "day" in result
        assert "after" in result or "before" in result

    def test_diff_unknown_unit_returns_error(self, datetime_tools):
        """Unknown unit returns Error."""
        result = datetime_tools["date_diff"](
            date1="2026-01-01",
            date2="2026-01-02",
            unit="weeks",
        )
        assert "Error" in result
        assert "Unknown unit" in result or "unit" in result.lower()

    def test_diff_invalid_date_returns_error(self, datetime_tools):
        """Invalid date returns Error."""
        result = datetime_tools["date_diff"](
            date1="not-a-date",
            date2="2026-01-02",
        )
        assert "Error" in result


class TestAddTime:
    """Tests for add_time."""

    def test_add_days_forward(self, datetime_tools):
        """Add 7 days gives next week."""
        result = datetime_tools["add_time"](
            date_string="2026-01-30",
            days=7,
        )
        assert result == "2026-02-06"

    def test_subtract_days(self, datetime_tools):
        """Subtract 1 day."""
        result = datetime_tools["add_time"](
            date_string="2026-01-30",
            days=-1,
        )
        assert result == "2026-01-29"

    def test_add_zero_unchanged(self, datetime_tools):
        """Add 0 returns same date."""
        result = datetime_tools["add_time"](
            date_string="2026-01-30",
            days=0,
        )
        assert result == "2026-01-30"

    def test_add_hours(self, datetime_tools):
        """Add 2 hours to datetime."""
        result = datetime_tools["add_time"](
            date_string="2026-01-30 14:00:00",
            hours=2,
            date_format="%Y-%m-%d %H:%M:%S",
        )
        assert "16:00:00" in result

    def test_add_days_cross_month(self, datetime_tools):
        """Add days crossing month boundary."""
        result = datetime_tools["add_time"](
            date_string="2026-01-31",
            days=1,
        )
        assert result == "2026-02-01"

    def test_leap_year_feb(self, datetime_tools):
        """Add 1 day to Feb 28 in leap year gives Feb 29."""
        result = datetime_tools["add_time"](
            date_string="2026-02-28",  # 2026 is not leap year
            days=1,
        )
        assert result == "2026-03-01"

    def test_add_time_invalid_date_returns_error(self, datetime_tools):
        """Invalid date returns Error."""
        result = datetime_tools["add_time"](
            date_string="invalid",
            days=1,
        )
        assert "Error" in result


class TestCompareDates:
    """Tests for compare_dates."""

    def test_date1_before_date2(self, datetime_tools):
        """First date before second."""
        result = datetime_tools["compare_dates"](
            date1="2026-01-01",
            date2="2026-01-15",
        )
        assert "before" in result

    def test_date1_after_date2(self, datetime_tools):
        """First date after second."""
        result = datetime_tools["compare_dates"](
            date1="2026-01-15",
            date2="2026-01-01",
        )
        assert "after" in result

    def test_same_date(self, datetime_tools):
        """Same date returns 'same'."""
        result = datetime_tools["compare_dates"](
            date1="2026-01-30",
            date2="2026-01-30",
        )
        assert "same" in result

    def test_compare_invalid_returns_error(self, datetime_tools):
        """Invalid date returns Error."""
        result = datetime_tools["compare_dates"](
            date1="not-a-date",
            date2="2026-01-30",
        )
        assert "Error" in result


class TestGetDayOfWeek:
    """Tests for get_day_of_week."""

    def test_known_date_friday(self, datetime_tools):
        """2026-01-30 is a Friday."""
        result = datetime_tools["get_day_of_week"](date_string="2026-01-30")
        assert result == "Friday"

    def test_known_date_monday(self, datetime_tools):
        """2026-01-26 is a Monday."""
        result = datetime_tools["get_day_of_week"](date_string="2026-01-26")
        assert result == "Monday"

    def test_leap_day_2024(self, datetime_tools):
        """2024-02-29 is Thursday."""
        result = datetime_tools["get_day_of_week"](date_string="2024-02-29")
        assert result == "Thursday"

    def test_custom_format(self, datetime_tools):
        """Works with custom date format."""
        result = datetime_tools["get_day_of_week"](
            date_string="30/01/2026",
            date_format="%d/%m/%Y",
        )
        assert result == "Friday"

    def test_invalid_date_returns_error(self, datetime_tools):
        """Invalid date returns Error."""
        result = datetime_tools["get_day_of_week"](date_string="invalid")
        assert "Error" in result


class TestEdgeCases:
    """Edge case tests for datetime tools."""

    def test_ambiguous_date_european_wins(self, datetime_tools):
        """Ambiguous date 01/02/2026 is parsed as Feb 1 (European DD/MM/YYYY)."""
        result = datetime_tools["parse_date"](date_string="01/02/2026")
        # European format (DD/MM/YYYY) takes precedence
        assert result == "2026-02-01"  # February 1, not January 2

    def test_invalid_format_directive_returns_error(self, datetime_tools):
        """Invalid strftime directive %Q returns Error."""
        result = datetime_tools["get_current_datetime"](format="%Q")
        assert "Error" in result

    def test_add_365_days_year_rollover(self, datetime_tools):
        """Adding 365 days rolls over to next year."""
        result = datetime_tools["add_time"](date_string="2026-01-01", days=365)
        assert result == "2027-01-01"

    def test_subtract_365_days_year_rollback(self, datetime_tools):
        """Subtracting 365 days rolls back to previous year."""
        result = datetime_tools["add_time"](date_string="2027-01-01", days=-365)
        assert result == "2026-01-01"

    def test_year_end_rollover(self, datetime_tools):
        """Dec 31 + 1 day = Jan 1 next year."""
        result = datetime_tools["add_time"](date_string="2026-12-31", days=1)
        assert result == "2027-01-01"

    def test_date_diff_minutes(self, datetime_tools):
        """date_diff with unit=minutes works correctly."""
        result = datetime_tools["date_diff"](
            date1="2026-01-30 10:00:00",
            date2="2026-01-30 10:45:30",
            unit="minutes",
            date_format="%Y-%m-%d %H:%M:%S",
        )
        assert "45.50 minutes" in result

    def test_date_diff_seconds(self, datetime_tools):
        """date_diff with unit=seconds works correctly."""
        result = datetime_tools["date_diff"](
            date1="2026-01-30 10:00:00",
            date2="2026-01-30 10:00:45",
            unit="seconds",
            date_format="%Y-%m-%d %H:%M:%S",
        )
        assert "45 seconds" in result

    def test_leap_year_feb_29_plus_one_day(self, datetime_tools):
        """Feb 29 in leap year + 1 day = Mar 1."""
        result = datetime_tools["add_time"](date_string="2024-02-29", days=1)
        assert result == "2024-03-01"

    def test_leap_year_feb_28_plus_one_day(self, datetime_tools):
        """Feb 28 in leap year + 1 day = Feb 29."""
        result = datetime_tools["add_time"](date_string="2024-02-28", days=1)
        assert result == "2024-02-29"

    def test_non_leap_year_feb_28_plus_one_day(self, datetime_tools):
        """Feb 28 in non-leap year + 1 day = Mar 1."""
        result = datetime_tools["add_time"](date_string="2026-02-28", days=1)
        assert result == "2026-03-01"
