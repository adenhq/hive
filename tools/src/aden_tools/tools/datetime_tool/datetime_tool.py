"""
DateTime Tool - Date and time operations for AI agents.

Provides tools for parsing, formatting, and manipulating dates and times.
Useful for scheduling, deadline tracking, and time-based calculations.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastmcp import FastMCP


def register_tools(mcp: FastMCP) -> None:
    """Register datetime tools with the MCP server."""

    @mcp.tool()
    def get_current_datetime(
        format: str = "%Y-%m-%d %H:%M:%S",
        timezone_offset: Optional[int] = None,
    ) -> str:
        """
        Get the current date and time.
        Use this tool when you need to know the current date or time.

        Args:
            format: Output format string (default: "YYYY-MM-DD HH:MM:SS").
                   Common formats:
                   - "%Y-%m-%d" for "2026-01-30"
                   - "%Y-%m-%d %H:%M:%S" for "2026-01-30 14:30:00"
                   - "%B %d, %Y" for "January 30, 2026"
                   - "%d/%m/%Y" for "30/01/2026"
                   - "%I:%M %p" for "02:30 PM"
            timezone_offset: UTC offset in hours (e.g., -5 for EST, +5.5 for IST).
                            If not provided, uses system local time.

        Returns:
            Current date/time formatted as specified string
        """
        try:
            if timezone_offset is not None:
                # Create timezone with specified offset
                tz = timezone(timedelta(hours=timezone_offset))
                now = datetime.now(tz)
            else:
                now = datetime.now()

            return now.strftime(format)

        except Exception as e:
            return f"Error: {str(e)}"

    @mcp.tool()
    def parse_date(
        date_string: str,
        input_format: Optional[str] = None,
        output_format: str = "%Y-%m-%d",
    ) -> str:
        """
        Parse a date string and convert it to a standard format.
        Use this tool to convert human-readable dates to a standard format.

        Args:
            date_string: The date string to parse (e.g., "January 30, 2026",
                        "30/01/2026", "2026-01-30")
            input_format: Optional format of the input string. If not provided,
                         common formats will be tried automatically.
                         Examples: "%B %d, %Y", "%d/%m/%Y", "%Y-%m-%d"
            output_format: Desired output format (default: "YYYY-MM-DD")

        Returns:
            Parsed date in the specified output format, or error message
        """
        try:
            parsed_date = None

            if input_format:
                # Use specified format
                parsed_date = datetime.strptime(date_string, input_format)
            else:
                # Try common formats
                common_formats = [
                    "%Y-%m-%d",           # 2026-01-30
                    "%Y/%m/%d",           # 2026/01/30
                    "%d-%m-%Y",           # 30-01-2026
                    "%d/%m/%Y",           # 30/01/2026
                    "%m-%d-%Y",           # 01-30-2026
                    "%m/%d/%Y",           # 01/30/2026
                    "%B %d, %Y",          # January 30, 2026
                    "%b %d, %Y",          # Jan 30, 2026
                    "%d %B %Y",           # 30 January 2026
                    "%d %b %Y",           # 30 Jan 2026
                    "%Y-%m-%dT%H:%M:%S",  # ISO format
                    "%Y-%m-%d %H:%M:%S",  # Standard datetime
                ]

                for fmt in common_formats:
                    try:
                        parsed_date = datetime.strptime(date_string, fmt)
                        break
                    except ValueError:
                        continue

            if parsed_date is None:
                return f"Error: Could not parse date '{date_string}'. Please specify input_format."

            return parsed_date.strftime(output_format)

        except Exception as e:
            return f"Error: {str(e)}"

    @mcp.tool()
    def format_date(
        date_string: str,
        input_format: str = "%Y-%m-%d",
        output_format: str = "%B %d, %Y",
    ) -> str:
        """
        Convert a date from one format to another.
        Use this tool to reformat dates for display or processing.

        Args:
            date_string: The date string to format (e.g., "2026-01-30")
            input_format: Format of the input date string (default: "%Y-%m-%d")
            output_format: Desired output format (default: "%B %d, %Y" -> "January 30, 2026")

        Returns:
            Date in the new format, or error message
        """
        try:
            parsed_date = datetime.strptime(date_string, input_format)
            return parsed_date.strftime(output_format)

        except ValueError as e:
            return f"Error: Could not parse '{date_string}' with format '{input_format}'. {str(e)}"
        except Exception as e:
            return f"Error: {str(e)}"

    @mcp.tool()
    def date_diff(
        date1: str,
        date2: str,
        unit: str = "days",
        date_format: str = "%Y-%m-%d",
    ) -> str:
        """
        Calculate the difference between two dates.
        Use this tool to find how many days/hours/minutes between two dates.

        Args:
            date1: First date string
            date2: Second date string
            unit: Unit for the result - "days", "hours", "minutes", "seconds",
                  or "human" for human-readable format
            date_format: Format of the input date strings (default: "%Y-%m-%d")
                        Use "%Y-%m-%d %H:%M:%S" for datetime strings

        Returns:
            Difference between dates in specified unit (date2 - date1).
            Positive if date2 is after date1, negative if before.
        """
        try:
            dt1 = datetime.strptime(date1, date_format)
            dt2 = datetime.strptime(date2, date_format)

            diff = dt2 - dt1

            if unit == "days":
                result = diff.days + diff.seconds / 86400
                return f"{result:.2f} days"
            elif unit == "hours":
                result = diff.total_seconds() / 3600
                return f"{result:.2f} hours"
            elif unit == "minutes":
                result = diff.total_seconds() / 60
                return f"{result:.2f} minutes"
            elif unit == "seconds":
                result = diff.total_seconds()
                return f"{result:.0f} seconds"
            elif unit == "human":
                # Human-readable format
                total_seconds = abs(diff.total_seconds())
                days = int(total_seconds // 86400)
                hours = int((total_seconds % 86400) // 3600)
                minutes = int((total_seconds % 3600) // 60)

                parts = []
                if days > 0:
                    parts.append(f"{days} day{'s' if days != 1 else ''}")
                if hours > 0:
                    parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
                if minutes > 0:
                    parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")

                if not parts:
                    return "0 minutes"

                result_str = ", ".join(parts)
                if diff.total_seconds() < 0:
                    return f"{result_str} before"
                else:
                    return f"{result_str} after"
            else:
                return f"Error: Unknown unit '{unit}'. Use 'days', 'hours', 'minutes', 'seconds', or 'human'."

        except ValueError as e:
            return f"Error: Could not parse dates with format '{date_format}'. {str(e)}"
        except Exception as e:
            return f"Error: {str(e)}"

    @mcp.tool()
    def add_time(
        date_string: str,
        days: int = 0,
        hours: int = 0,
        minutes: int = 0,
        date_format: str = "%Y-%m-%d",
        output_format: Optional[str] = None,
    ) -> str:
        """
        Add or subtract time from a date.
        Use this tool to calculate future or past dates.

        Args:
            date_string: The starting date string
            days: Number of days to add (negative to subtract)
            hours: Number of hours to add (negative to subtract)
            minutes: Number of minutes to add (negative to subtract)
            date_format: Format of the input date string (default: "%Y-%m-%d")
            output_format: Format for the result (default: same as input format)

        Returns:
            New date/time after adding the specified duration

        Examples:
            - add_time("2026-01-30", days=7) -> "2026-02-06" (one week later)
            - add_time("2026-01-30", days=-1) -> "2026-01-29" (yesterday)
            - add_time("2026-01-30 14:00:00", hours=2, date_format="%Y-%m-%d %H:%M:%S")
        """
        try:
            dt = datetime.strptime(date_string, date_format)
            delta = timedelta(days=days, hours=hours, minutes=minutes)
            result_dt = dt + delta

            out_fmt = output_format if output_format else date_format
            return result_dt.strftime(out_fmt)

        except ValueError as e:
            return f"Error: Could not parse '{date_string}' with format '{date_format}'. {str(e)}"
        except Exception as e:
            return f"Error: {str(e)}"

    @mcp.tool()
    def compare_dates(
        date1: str,
        date2: str,
        date_format: str = "%Y-%m-%d",
    ) -> str:
        """
        Compare two dates to determine which comes first.
        Use this tool to check if a deadline has passed or compare events.

        Args:
            date1: First date string
            date2: Second date string
            date_format: Format of the input date strings (default: "%Y-%m-%d")

        Returns:
            Comparison result: "before", "after", or "same"
        """
        try:
            dt1 = datetime.strptime(date1, date_format)
            dt2 = datetime.strptime(date2, date_format)

            if dt1 < dt2:
                return f"'{date1}' is before '{date2}'"
            elif dt1 > dt2:
                return f"'{date1}' is after '{date2}'"
            else:
                return f"'{date1}' and '{date2}' are the same"

        except ValueError as e:
            return f"Error: Could not parse dates with format '{date_format}'. {str(e)}"
        except Exception as e:
            return f"Error: {str(e)}"

    @mcp.tool()
    def get_day_of_week(
        date_string: str,
        date_format: str = "%Y-%m-%d",
    ) -> str:
        """
        Get the day of the week for a given date.
        Use this tool to find what day (Monday, Tuesday, etc.) a date falls on.

        Args:
            date_string: The date string to check
            date_format: Format of the input date string (default: "%Y-%m-%d")

        Returns:
            Day of the week (e.g., "Monday", "Tuesday", etc.)
        """
        try:
            dt = datetime.strptime(date_string, date_format)
            return dt.strftime("%A")

        except ValueError as e:
            return f"Error: Could not parse '{date_string}' with format '{date_format}'. {str(e)}"
        except Exception as e:
            return f"Error: {str(e)}"
