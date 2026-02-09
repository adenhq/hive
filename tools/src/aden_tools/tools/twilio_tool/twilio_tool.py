"""
Twilio Integration Tool - SMS and WhatsApp messaging.

Allows agents to send SMS and WhatsApp messages, fetch history,
and validate phone numbers using the Twilio API.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from dotenv import load_dotenv
from fastmcp import FastMCP

if TYPE_CHECKING:
    from aden_tools.credentials import CredentialStoreAdapter


# -----------------------------------------------------------------------------
# Helper: Client Initialization
# -----------------------------------------------------------------------------

def _get_client(credentials: CredentialStoreAdapter | None = None):
    """Returns an authenticated Twilio client or raises ImportError/ValueError."""
    try:
        from twilio.rest import Client
    except ImportError as err:
        raise ImportError(
            "The 'twilio' library is not installed. Please run `pip install twilio`."
        ) from err

    # Resolve SID and token from credential adapter (preferred) or env vars (fallback)
    load_dotenv()
    sid = None
    token = None
    if credentials is not None:

        sid = credentials.get("twilio_account_sid")
        token = credentials.get("twilio_auth_token")

    else:
        sid = os.getenv("TWILIO_ACCOUNT_SID")
        token = os.getenv("TWILIO_AUTH_TOKEN")

    if not sid or not token:
        raise ValueError(
            "Missing TWILIO_ACCOUNT_SID or TWILIO_AUTH_TOKEN environment variables."
        )
    return Client(sid, token)


def _get_from_number(credentials: CredentialStoreAdapter | None = None) -> str:
    """Returns the default from_number or raises an error."""
    load_dotenv()
    from_num = None

    if credentials is not None:
        from_num = credentials.get("twilio_from_number")
    else:
        from_num = os.getenv("TWILIO_FROM_NUMBER")

    if not from_num:
        raise ValueError("Missing TWILIO_FROM_NUMBER environment variable.")

    return from_num


# -----------------------------------------------------------------------------
# Tool Registration
# -----------------------------------------------------------------------------

def register_tools(mcp: FastMCP, credentials: CredentialStoreAdapter | None = None) -> None:
    """Register Twilio tools with the MCP server."""

    @mcp.tool()
    def send_sms(
        to: str,
        body: str,
        media_url: str | None = None,
    ) -> dict:
        """Send an SMS message. Returns dict on success or error."""
        try:
            client = _get_client(credentials)
            from_number = _get_from_number(credentials)

            # Safety: if caller included whatsapp: prefix, strip it for SMS
            if to.startswith("whatsapp:"):
                to = to.replace("whatsapp:", "")

            args = {"to": to, "from_": from_number, "body": body}
            if media_url:
                args["media_url"] = [media_url]

            msg = client.messages.create(**args)
            return {
                "sid": getattr(msg, "sid", None),
                "status": getattr(msg, "status", None),
                "to": to,
            }

        except (ImportError, ValueError) as e:
            return {
                "error": str(e),
                "help": (
                    "Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN env vars "
                    "or configure credential store"
                ),
            }
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def send_whatsapp(
        to: str,
        body: str,
        media_url: str | None = None,
    ) -> dict:
        """Send a WhatsApp message. Returns dict on success or error."""
        try:
            client = _get_client(credentials)
            from_number = _get_from_number(credentials)

            if not to.startswith("whatsapp:"):
                to = f"whatsapp:{to}"
            if not from_number.startswith("whatsapp:"):
                from_number = f"whatsapp:{from_number}"

            args = {"to": to, "from_": from_number, "body": body}
            if media_url:
                args["media_url"] = [media_url]

            msg = client.messages.create(**args)
            return {"sid": getattr(msg, "sid", None), "to": to}

        except (ImportError, ValueError) as e:
            return {
                "error": str(e),
                "help": (
                    "Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN env vars "
                    "or configure credential store"
                ),
            }
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def fetch_history(limit: int = 5, to: str | None = None) -> dict:
        """Retrieve recent message logs. Returns {"messages": [...]} or error."""
        try:
            client = _get_client(credentials)
            messages = client.messages.list(limit=limit, to=to)

            result = []
            for m in messages:
                direction = "OUT" if getattr(m, "direction", "").startswith("outbound") else "IN"
                date = getattr(m, "date_sent", None)
                if hasattr(date, "isoformat"):
                    date = date.isoformat()
                result.append({
                    "date": date,
                    "direction": direction,
                    "from": getattr(m, "from_", None),
                    "to": getattr(m, "to", None),
                    "body": getattr(m, "body", None),
                })

            return {"messages": result}

        except (ImportError, ValueError) as e:
            return {
                "error": str(e),
                "help": (
                    "Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN env vars "
                    "or configure credential store"
                ),
            }
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def validate_number(phone_number: str) -> dict:
        """Check if a phone number is valid and get its formatting."""
        try:
            client = _get_client(credentials)
            info = client.lookups.v2.phone_numbers(phone_number).fetch()

            return {
                "valid": getattr(info, "valid", None),
                "formatted": getattr(info, "phone_number", None),
                "country": getattr(info, "country_code", None),
            }

        except (ImportError, ValueError) as e:
            return {
                "error": str(e),
                "help": (
                    "Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN env vars "
                    "or configure credential store"
                ),
            }
        except Exception as e:
            return {"error": str(e)}
