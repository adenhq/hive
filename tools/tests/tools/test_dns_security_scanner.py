"""Tests for dns_security_scanner — DNSSEC validation via AD flag."""

from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch

import pytest

from aden_tools.tools.dns_security_scanner.dns_security_scanner import _check_dnssec


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_resolver(timeout: int = 10, lifetime: int = 10) -> Mock:
    """Create a mock resolver to pass as the `_resolver` argument."""
    resolver = Mock()
    resolver.timeout = timeout
    resolver.lifetime = lifetime
    return resolver


def _mock_response(ad_flag: bool) -> Mock:
    """Create a mock dns.resolver.Answer with controllable AD flag."""
    import dns.flags

    flags = dns.flags.QR | dns.flags.RD | dns.flags.RA
    if ad_flag:
        flags |= dns.flags.AD

    inner = Mock()
    inner.flags = flags

    answer = Mock()
    answer.response = inner
    return answer


# ---------------------------------------------------------------------------
# _check_dnssec
# ---------------------------------------------------------------------------

class TestCheckDnssec:
    """Tests for _check_dnssec using a validating resolver and AD flag."""

    @patch("aden_tools.tools.dns_security_scanner.dns_security_scanner.dns.resolver.Resolver")
    def test_dnssec_enabled_ad_flag_set(self, MockResolver: Mock) -> None:
        """AD flag present → enabled: True."""
        mock_instance = MockResolver.return_value
        mock_instance.resolve.return_value = _mock_response(ad_flag=True)

        result = _check_dnssec(_make_resolver(), "ietf.org")

        assert result["enabled"] is True
        assert result["issues"] == []

    @patch("aden_tools.tools.dns_security_scanner.dns_security_scanner.dns.resolver.Resolver")
    def test_dnssec_disabled_no_ad_flag(self, MockResolver: Mock) -> None:
        """AD flag absent → enabled: False with descriptive issue."""
        mock_instance = MockResolver.return_value
        mock_instance.resolve.return_value = _mock_response(ad_flag=False)

        result = _check_dnssec(_make_resolver(), "example.com")

        assert result["enabled"] is False
        assert len(result["issues"]) == 1
        assert "not validated" in result["issues"][0]

    @patch("aden_tools.tools.dns_security_scanner.dns_security_scanner.dns.resolver.Resolver")
    def test_dnssec_nxdomain(self, MockResolver: Mock) -> None:
        """Non-existent domain → enabled: False."""
        import dns.resolver

        mock_instance = MockResolver.return_value
        mock_instance.resolve.side_effect = dns.resolver.NXDOMAIN()

        result = _check_dnssec(_make_resolver(), "nonexistent.invalid")

        assert result["enabled"] is False
        assert len(result["issues"]) == 1

    @patch("aden_tools.tools.dns_security_scanner.dns_security_scanner.dns.resolver.Resolver")
    def test_dnssec_timeout(self, MockResolver: Mock) -> None:
        """DNS timeout → enabled: False."""
        import dns.exception

        mock_instance = MockResolver.return_value
        mock_instance.resolve.side_effect = dns.exception.Timeout()

        result = _check_dnssec(_make_resolver(), "slow.example.com")

        assert result["enabled"] is False
        assert len(result["issues"]) == 1

    @patch("aden_tools.tools.dns_security_scanner.dns_security_scanner.dns.resolver.Resolver")
    def test_dnssec_uses_validating_resolver(self, MockResolver: Mock) -> None:
        """Verify the function creates a resolver with known validating nameservers."""
        mock_instance = MockResolver.return_value
        mock_instance.resolve.return_value = _mock_response(ad_flag=True)

        _check_dnssec(_make_resolver(timeout=7, lifetime=12), "ietf.org")

        # Should be created with configure=False to bypass system config
        MockResolver.assert_called_once_with(configure=False)

        # Should use Google and Cloudflare DNS
        assert mock_instance.nameservers == ["8.8.8.8", "1.1.1.1"]

        # Should inherit timeout/lifetime from the caller's resolver
        assert mock_instance.timeout == 7
        assert mock_instance.lifetime == 12

    @patch("aden_tools.tools.dns_security_scanner.dns_security_scanner.dns.resolver.Resolver")
    def test_dnssec_uses_edns_do_bit(self, MockResolver: Mock) -> None:
        """Verify EDNS is enabled with DO flag and 4096 payload."""
        import dns.flags

        mock_instance = MockResolver.return_value
        mock_instance.resolve.return_value = _mock_response(ad_flag=True)

        _check_dnssec(_make_resolver(), "ietf.org")

        mock_instance.use_edns.assert_called_once_with(0, dns.flags.DO, 4096)

    @patch("aden_tools.tools.dns_security_scanner.dns_security_scanner.dns.resolver.Resolver")
    def test_dnssec_queries_soa_records(self, MockResolver: Mock) -> None:
        """Verify SOA records are queried instead of DNSKEY."""
        mock_instance = MockResolver.return_value
        mock_instance.resolve.return_value = _mock_response(ad_flag=True)

        _check_dnssec(_make_resolver(), "ietf.org")

        mock_instance.resolve.assert_called_once_with("ietf.org", "SOA")
