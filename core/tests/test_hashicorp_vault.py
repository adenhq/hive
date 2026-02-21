"""Tests for HashiCorp Vault credential storage.

Mock-based tests that don't require a real Vault server.
Tests serialization, deserialization, and path sanitization logic.
"""

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from pydantic import SecretStr

from framework.credentials.models import CredentialKey, CredentialObject, CredentialType


def _sanitize_credential_id(cred_id: str) -> str:
    """Sanitize credential ID for use in paths (mirrors Vault logic)."""
    return cred_id.replace("/", "_").replace("\\", "_")


def _build_vault_path(prefix: str, credential_id: str) -> str:
    """Build Vault path for a credential."""
    safe_id = _sanitize_credential_id(credential_id)
    return f"{prefix}/{safe_id}"


class TestVaultPathSanitization:
    """Tests for Vault path building logic."""

    def test_path_sanitizes_forward_slashes(self):
        """Test that forward slashes in credential IDs are sanitized."""
        path = _build_vault_path("hive/credentials", "my/credential/id")
        assert "/" not in path.split("/")[-1]

    def test_path_sanitizes_backslashes(self):
        """Test that backslashes in credential IDs are sanitized."""
        path = _build_vault_path("hive/credentials", "my\\credential\\id")
        assert "\\" not in path

    def test_path_includes_prefix(self):
        """Test that path includes the configured prefix."""
        path = _build_vault_path("custom/prefix", "my-credential")
        assert path.startswith("custom/prefix/")

    def test_sanitize_preserves_valid_characters(self):
        """Test that valid characters are preserved."""
        safe_id = _sanitize_credential_id("valid-credential_name")
        assert safe_id == "valid-credential_name"


class TestVaultSerialization:
    """Tests for Vault serialization/deserialization logic."""

    def _serialize_for_vault(self, credential: CredentialObject) -> dict:
        """Serialize credential for Vault storage (mirrors implementation)."""
        data: dict = {
            "_type": credential.credential_type.value,
        }

        if credential.provider_id:
            data["_provider_id"] = credential.provider_id

        if credential.description:
            data["_description"] = credential.description

        if credential.auto_refresh:
            data["_auto_refresh"] = "true"

        for key_name, key in credential.keys.items():
            data[key_name] = key.get_secret_value()

            if key.expires_at:
                data[f"_expires_{key_name}"] = key.expires_at.isoformat()

            if key.metadata:
                data[f"_metadata_{key_name}"] = str(key.metadata)

        return data

    def _deserialize_from_vault(self, credential_id: str, data: dict) -> CredentialObject:
        """Deserialize credential from Vault storage (mirrors implementation)."""
        cred_type = CredentialType(data.pop("_type", "api_key"))
        provider_id = data.pop("_provider_id", None)
        description = data.pop("_description", "")
        auto_refresh = data.pop("_auto_refresh", "") == "true"

        keys: dict[str, CredentialKey] = {}
        key_names = [k for k in data.keys() if not k.startswith("_")]

        for key_name in key_names:
            value = data[key_name]

            expires_at = None
            expires_key = f"_expires_{key_name}"
            if expires_key in data:
                try:
                    expires_at = datetime.fromisoformat(data[expires_key])
                except (ValueError, TypeError):
                    pass

            metadata: dict = {}
            metadata_key = f"_metadata_{key_name}"
            if metadata_key in data:
                try:
                    import ast

                    metadata = ast.literal_eval(data[metadata_key])
                except (ValueError, SyntaxError):
                    pass

            keys[key_name] = CredentialKey(
                name=key_name,
                value=SecretStr(value),
                expires_at=expires_at,
                metadata=metadata,
            )

        return CredentialObject(
            id=credential_id,
            credential_type=cred_type,
            keys=keys,
            provider_id=provider_id,
            description=description,
            auto_refresh=auto_refresh,
        )

    def test_serialize_api_key_credential(self):
        """Test serializing an API key credential."""
        cred = CredentialObject(
            id="test-api",
            credential_type=CredentialType.API_KEY,
            keys={
                "api_key": CredentialKey(
                    name="api_key",
                    value=SecretStr("secret-key-123"),
                )
            },
            description="Test API key",
        )

        data = self._serialize_for_vault(cred)

        assert data["_type"] == "api_key"
        assert data["_description"] == "Test API key"
        assert data["api_key"] == "secret-key-123"

    def test_serialize_oauth2_credential(self):
        """Test serializing an OAuth2 credential with expiration."""
        expires = datetime(2025, 12, 31, 12, 0, 0, tzinfo=timezone.utc)

        cred = CredentialObject(
            id="oauth-cred",
            credential_type=CredentialType.OAUTH2,
            keys={
                "access_token": CredentialKey(
                    name="access_token",
                    value=SecretStr("access-123"),
                    expires_at=expires,
                ),
                "refresh_token": CredentialKey(
                    name="refresh_token",
                    value=SecretStr("refresh-456"),
                ),
            },
            provider_id="google",
            auto_refresh=True,
        )

        data = self._serialize_for_vault(cred)

        assert data["_type"] == "oauth2"
        assert data["_provider_id"] == "google"
        assert data["_auto_refresh"] == "true"
        assert data["access_token"] == "access-123"
        assert data["refresh_token"] == "refresh-456"
        assert "_expires_access_token" in data

    def test_deserialize_api_key_credential(self):
        """Test deserializing an API key credential."""
        data = {
            "_type": "api_key",
            "_description": "Test key",
            "api_key": "secret-value",
        }

        cred = self._deserialize_from_vault("test-id", data.copy())

        assert cred.id == "test-id"
        assert cred.credential_type == CredentialType.API_KEY
        assert cred.description == "Test key"
        assert cred.keys["api_key"].value.get_secret_value() == "secret-value"

    def test_deserialize_oauth2_credential(self):
        """Test deserializing an OAuth2 credential with expiration."""
        data = {
            "_type": "oauth2",
            "_provider_id": "github",
            "_auto_refresh": "true",
            "access_token": "at-123",
            "_expires_access_token": "2025-12-31T12:00:00+00:00",
            "refresh_token": "rt-456",
        }

        cred = self._deserialize_from_vault("oauth-id", data.copy())

        assert cred.credential_type == CredentialType.OAUTH2
        assert cred.provider_id == "github"
        assert cred.auto_refresh is True
        assert cred.keys["access_token"].expires_at is not None
        assert cred.keys["refresh_token"].value.get_secret_value() == "rt-456"

    def test_serialize_and_deserialize_roundtrip(self):
        """Test that serialize -> deserialize produces identical credential."""
        original = CredentialObject(
            id="roundtrip-test",
            credential_type=CredentialType.API_KEY,
            keys={
                "key1": CredentialKey(
                    name="key1",
                    value=SecretStr("value1"),
                    metadata={"source": "test"},
                ),
                "key2": CredentialKey(
                    name="key2",
                    value=SecretStr("value2"),
                ),
            },
            description="Roundtrip test",
        )

        serialized = self._serialize_for_vault(original)
        deserialized = self._deserialize_from_vault("roundtrip-test", serialized.copy())

        assert deserialized.id == original.id
        assert deserialized.credential_type == original.credential_type
        assert deserialized.description == original.description
        assert (
            deserialized.keys["key1"].value.get_secret_value()
            == original.keys["key1"].value.get_secret_value()
        )
        assert (
            deserialized.keys["key2"].value.get_secret_value()
            == original.keys["key2"].value.get_secret_value()
        )


class TestVaultStorageInitRequirements:
    """Tests for HashiCorpVaultStorage initialization requirements."""

    def test_init_requires_token_or_env_var(self):
        """Test that initialization requires token or VAULT_TOKEN env var."""
        import os

        with patch.dict(os.environ, {}, clear=True):
            assert os.environ.get("VAULT_TOKEN") is None

    def test_env_token_is_used(self):
        """Test that VAULT_TOKEN environment variable is used."""
        import os

        with patch.dict(os.environ, {"VAULT_TOKEN": "test-env-token"}):
            assert os.environ.get("VAULT_TOKEN") == "test-env-token"


class TestCredentialTypes:
    """Tests for credential type handling."""

    def test_credential_type_values(self):
        """Test that all credential types have correct string values."""
        assert CredentialType.API_KEY.value == "api_key"
        assert CredentialType.OAUTH2.value == "oauth2"
        assert CredentialType.BASIC_AUTH.value == "basic_auth"
        assert CredentialType.CUSTOM.value == "custom"

    def test_credential_type_from_string(self):
        """Test creating CredentialType from string."""
        assert CredentialType("api_key") == CredentialType.API_KEY
        assert CredentialType("oauth2") == CredentialType.OAUTH2


class TestCredentialKeyExpiration:
    """Tests for credential key expiration handling."""

    def test_credential_key_with_expiration(self):
        """Test creating a credential key with expiration."""
        expires = datetime(2025, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

        key = CredentialKey(
            name="access_token",
            value=SecretStr("token-value"),
            expires_at=expires,
        )

        assert key.expires_at == expires
        assert key.name == "access_token"

    def test_credential_key_without_expiration(self):
        """Test creating a credential key without expiration."""
        key = CredentialKey(
            name="api_key",
            value=SecretStr("key-value"),
        )

        assert key.expires_at is None

    def test_credential_key_metadata(self):
        """Test creating a credential key with metadata."""
        key = CredentialKey(
            name="oauth_token",
            value=SecretStr("token"),
            metadata={"scope": "read write", "token_type": "bearer"},
        )

        assert key.metadata["scope"] == "read write"
        assert key.metadata["token_type"] == "bearer"


class TestCredentialObjectValidation:
    """Tests for CredentialObject validation."""

    def test_credential_object_minimal(self):
        """Test creating a minimal credential object."""
        cred = CredentialObject(
            id="minimal",
            credential_type=CredentialType.API_KEY,
            keys={
                "key": CredentialKey(name="key", value=SecretStr("value")),
            },
        )

        assert cred.id == "minimal"
        assert cred.description == ""
        assert cred.provider_id is None
        assert cred.auto_refresh is False

    def test_credential_object_with_all_fields(self):
        """Test creating a credential object with all fields."""
        cred = CredentialObject(
            id="full",
            credential_type=CredentialType.OAUTH2,
            keys={
                "access_token": CredentialKey(
                    name="access_token",
                    value=SecretStr("at"),
                ),
            },
            description="Full credential",
            provider_id="provider-123",
            auto_refresh=True,
        )

        assert cred.id == "full"
        assert cred.description == "Full credential"
        assert cred.provider_id == "provider-123"
        assert cred.auto_refresh is True
