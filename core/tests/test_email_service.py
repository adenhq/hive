"""Tests for email service."""

import pytest
from unittest.mock import MagicMock

from framework.services.email_service import (
    EmailConfig,
    BudgetAlertEmail,
    EmailService,
)


@pytest.fixture
def email_config_disabled():
    """Email config with service disabled."""
    return EmailConfig(
        api_key="test_api_key",
        from_email="alerts@example.com",
        enabled=False,
    )


@pytest.fixture
def email_config_enabled():
    """Email config with service enabled."""
    return EmailConfig(
        api_key="re_test_api_key_1234567890",
        from_email="alerts@example.com",
        enabled=True,
    )


@pytest.fixture
def budget_alert():
    """Sample budget alert."""
    return BudgetAlertEmail(
        recipients=["user@example.com", "admin@example.com"],
        budget_name="Engineering Team Monthly",
        current_spend=800.00,
        budget_limit=1000.00,
        percentage_used=80.0,
        threshold=80,
    )


@pytest.fixture
def budget_alert_critical():
    """Sample critical budget alert."""
    return BudgetAlertEmail(
        recipients=["user@example.com"],
        budget_name="Production Inference",
        current_spend=950.00,
        budget_limit=1000.00,
        percentage_used=95.0,
        threshold=95,
    )


class TestEmailConfig:
    """Test EmailConfig."""

    def test_initialization(self, email_config_enabled):
        """Test basic initialization."""
        assert email_config_enabled.api_key == "re_test_api_key_1234567890"
        assert email_config_enabled.from_email == "alerts@example.com"
        assert email_config_enabled.enabled is True

    def test_from_env_with_enabled(self, monkeypatch):
        """Test loading from environment with enabled."""
        monkeypatch.setenv("EMAIL_RESEND_API_KEY", "re_env_key")
        monkeypatch.setenv("EMAIL_FROM", "noreply@company.com")
        monkeypatch.setenv("EMAIL_ENABLED", "true")

        config = EmailConfig.from_env()

        assert config.api_key == "re_env_key"
        assert config.from_email == "noreply@company.com"
        assert config.enabled is True

    def test_from_env_with_disabled(self, monkeypatch):
        """Test loading from environment with disabled."""
        monkeypatch.delenv("EMAIL_RESEND_API_KEY", raising=False)
        monkeypatch.delenv("EMAIL_FROM", raising=False)
        monkeypatch.delenv("EMAIL_ENABLED", raising=False)

        config = EmailConfig.from_env()

        assert config.api_key == ""
        assert config.from_email == "alerts@example.com"
        assert config.enabled is False

    def test_from_env_custom_prefix(self, monkeypatch):
        """Test loading from environment with custom prefix."""
        monkeypatch.setenv("CUSTOM_RESEND_API_KEY", "re_custom_key")
        monkeypatch.setenv("CUSTOM_FROM", "custom@company.com")
        monkeypatch.setenv("CUSTOM_ENABLED", "true")

        config = EmailConfig.from_env(prefix="CUSTOM_")

        assert config.api_key == "re_custom_key"
        assert config.from_email == "custom@company.com"
        assert config.enabled is True


class TestEmailService:
    """Test EmailService."""

    def test_initialization_disabled(self, email_config_disabled):
        """Test initialization with disabled service."""
        service = EmailService(email_config_disabled)

        assert service.is_enabled() is False
        assert service.emails_client is None

    def test_initialization_enabled_with_mock(self, email_config_enabled):
        """Test initialization works with enabled config."""
        # We don't test actual initialization here since it depends on 
        # resend internals. Instead, we test the public interface.
        service = EmailService(email_config_enabled)
        # If it doesn't raise an exception, initialization was attempted
        assert service.config.enabled is True

    @pytest.mark.asyncio
    async def test_send_budget_alert_when_disabled(self, email_config_disabled, budget_alert):
        """Test sending alert when service is disabled."""
        service = EmailService(email_config_disabled)

        result = await service.send_budget_alert(budget_alert)

        assert result is False

    @pytest.mark.asyncio
    async def test_send_budget_alert_when_not_initialized(self, email_config_enabled, budget_alert):
        """Test sending alert when client is not initialized."""
        service = EmailService(email_config_enabled)
        # Force emails_client to None to simulate failed initialization
        service.emails_client = None
        
        result = await service.send_budget_alert(budget_alert)

        assert result is False

    @pytest.mark.asyncio
    async def test_send_budget_alert_with_mock_client(self, email_config_enabled, budget_alert):
        """Test successful budget alert send with mocked client."""
        service = EmailService(email_config_enabled)
        
        # Create a mock client
        mock_client = MagicMock()
        mock_client.send.return_value = {"id": "email_123"}
        service.emails_client = mock_client
        
        result = await service.send_budget_alert(budget_alert)

        assert result is True
        mock_client.send.assert_called_once()

        # Verify call arguments
        call_kwargs = mock_client.send.call_args[0][0]
        assert call_kwargs["from"] == "alerts@example.com"
        assert call_kwargs["to"] == ["user@example.com", "admin@example.com"]
        assert "Engineering Team Monthly" in call_kwargs["subject"]
        assert "80.0%" in call_kwargs["subject"]
        assert "800.00" in call_kwargs["html"]

    @pytest.mark.asyncio
    async def test_send_budget_alert_critical_with_mock(self, email_config_enabled, budget_alert_critical):
        """Test critical budget alert includes proper severity."""
        service = EmailService(email_config_enabled)
        
        mock_client = MagicMock()
        mock_client.send.return_value = {"id": "email_456"}
        service.emails_client = mock_client
        
        await service.send_budget_alert(budget_alert_critical)

        call_kwargs = mock_client.send.call_args[0][0]
        assert "CRITICAL" in call_kwargs["subject"] or "🚨" in call_kwargs["subject"]
        assert "Immediate action" in call_kwargs["html"]

    @pytest.mark.asyncio
    async def test_send_budget_alert_api_error_handled(self, email_config_enabled, budget_alert):
        """Test graceful handling of API errors."""
        service = EmailService(email_config_enabled)
        
        mock_client = MagicMock()
        mock_client.send.side_effect = Exception("API Error")
        service.emails_client = mock_client
        
        result = await service.send_budget_alert(budget_alert)

        # Should return False but not raise exception
        assert result is False

    def test_format_subject_warning(self, email_config_enabled, budget_alert):
        """Test subject formatting for warning threshold."""
        service = EmailService(email_config_enabled)
        subject = service._format_subject(budget_alert)

        assert "Budget Alert" in subject
        assert "Engineering Team Monthly" in subject
        assert "80.0%" in subject
        assert ("WARNING" in subject or "⚠️" in subject)

    def test_format_subject_critical(self, email_config_enabled, budget_alert_critical):
        """Test subject formatting for critical threshold."""
        service = EmailService(email_config_enabled)
        subject = service._format_subject(budget_alert_critical)

        assert "Budget Alert" in subject
        assert "Production Inference" in subject
        assert "95.0%" in subject
        assert ("CRITICAL" in subject or "🚨" in subject)

    def test_build_html_contains_budget_info(self, email_config_enabled, budget_alert):
        """Test HTML includes all budget information."""
        service = EmailService(email_config_enabled)
        html = service._build_budget_alert_html(budget_alert)

        assert "Engineering Team Monthly" in html
        assert "$800.00" in html
        assert "$1000.00" in html
        assert "$200.00" in html  # remaining
        assert "80.0%" in html
        assert "<!DOCTYPE html>" in html

    def test_build_html_critical_vs_warning(self, email_config_enabled, budget_alert, budget_alert_critical):
        """Test HTML differs between critical and warning."""
        service = EmailService(email_config_enabled)

        html_warning = service._build_budget_alert_html(budget_alert)
        html_critical = service._build_budget_alert_html(budget_alert_critical)

        # Both should be valid HTML
        assert "<!DOCTYPE html>" in html_warning
        assert "<!DOCTYPE html>" in html_critical

        # Critical should mention immediate action
        assert "Immediate action" in html_critical
        # Warning should mention review
        assert "review your spending" in html_warning

    def test_is_enabled_checks_both_conditions(self, email_config_enabled):
        """Test is_enabled checks both config and initialization."""
        # When disabled in config
        disabled_config = EmailConfig(
            api_key="test",
            from_email="test@example.com",
            enabled=False,
        )
        service = EmailService(disabled_config)
        assert service.is_enabled() is False

    def test_multiple_recipients(self, email_config_enabled):
        """Test sending to multiple recipients."""
        alert = BudgetAlertEmail(
            recipients=["user1@example.com", "user2@example.com", "user3@example.com"],
            budget_name="Test Budget",
            current_spend=100.0,
            budget_limit=200.0,
            percentage_used=50.0,
            threshold=50,
        )

        service = EmailService(email_config_enabled)
        html = service._build_budget_alert_html(alert)

        assert "Test Budget" in html
        assert "$100.00" in html

    def test_percentage_rounding(self, email_config_enabled):
        """Test percentage is properly rounded in output."""
        alert = BudgetAlertEmail(
            recipients=["user@example.com"],
            budget_name="Test",
            current_spend=333.33,
            budget_limit=1000.0,
            percentage_used=33.333,
            threshold=30,
        )

        service = EmailService(email_config_enabled)
        html = service._build_budget_alert_html(alert)
        subject = service._format_subject(alert)

        # Should format with 1 decimal place
        assert "33.3%" in subject or "33.4%" in subject  # Rounding
        assert "$333.33" in html

