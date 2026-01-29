"""Tests for HashiCorp Vault storage adapter.

Run with:
    cd core
    python -m pytest tests/test_hashicorp_vault.py -v
"""

import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from pydantic import SecretStr

from framework.credentials.models import CredentialKey, CredentialObject, CredentialType


# ===========================================================================
# Fixtures
# ===========================================================================

def _make_credential(
    cred_id: str = "test-cred",
    cred_type: CredentialType = CredentialType.API_KEY,
    keys: dict | None = None,
    provider_id: str | None = None,
    description: str = "",
    auto_refresh: bool = False,
) -> CredentialObject:
    """Create a sample CredentialObject for testing."""
    if keys is None:
        keys = {
            "api_key": CredentialKey(
                name="api_key",
                value=SecretStr("secret-value-123"),
            ),
        }
    return CredentialObject(
        id=cred_id,
        credential_type=cred_type,
        keys=keys,
        provider_id=provider_id,
        description=description,
        auto_refresh=auto_refresh,
    )


@pytest.fixture
def mock_hvac():
    """Fixture that patches hvac at the import level used by hashicorp.py."""
    mock_hvac_module = MagicMock()
    mock_client = MagicMock()
    mock_client.is_authenticated.return_value = True
    mock_hvac_module.Client.return_value = mock_client

    with patch.dict("sys.modules", {"hvac": mock_hvac_module}):
        yield mock_hvac_module, mock_client


def _make_vault_storage(mock_hvac_fixture):
    """Create a HashiCorpVaultStorage given the mock_hvac fixture tuple."""
    mock_hvac_module, mock_client = mock_hvac_fixture

    from framework.credentials.vault.hashicorp import HashiCorpVaultStorage

    storage = HashiCorpVaultStorage(
        url="https://vault.example.com:8200",
        token="test-token",
    )
    return storage, mock_client


# ===========================================================================
# TestHashiCorpVaultInit
# ===========================================================================

class TestHashiCorpVaultInit:
    """Tests for HashiCorpVaultStorage initialization."""

    def test_successful_init_with_valid_token(self, mock_hvac):
        """Initialize successfully with a valid, authenticated token."""
        storage, mock_client = _make_vault_storage(mock_hvac)

        assert storage._url == "https://vault.example.com:8200"
        assert storage._token == "test-token"
        assert storage._mount == "secret"
        assert storage._prefix == "hive/credentials"

    def test_raises_value_error_for_unauthenticated_token(self, mock_hvac):
        """Raise ValueError when token fails authentication."""
        mock_hvac_module, mock_client = mock_hvac
        mock_client.is_authenticated.return_value = False

        from framework.credentials.vault.hashicorp import HashiCorpVaultStorage

        with pytest.raises(ValueError, match="authentication failed"):
            HashiCorpVaultStorage(
                url="https://vault.example.com:8200",
                token="bad-token",
            )

    def test_raises_value_error_without_token(self, mock_hvac):
        """Raise ValueError when no token is available."""
        from framework.credentials.vault.hashicorp import HashiCorpVaultStorage

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="[Tt]oken required"):
                HashiCorpVaultStorage(
                    url="https://vault.example.com:8200",
                    token=None,
                )

    def test_custom_mount_point_and_prefix(self, mock_hvac):
        """Custom mount_point and path_prefix are stored."""
        from framework.credentials.vault.hashicorp import HashiCorpVaultStorage

        storage = HashiCorpVaultStorage(
            url="https://vault.example.com:8200",
            token="tok",
            mount_point="kv",
            path_prefix="myapp/secrets",
        )

        assert storage._mount == "kv"
        assert storage._prefix == "myapp/secrets"

    def test_namespace_support(self, mock_hvac):
        """Namespace is passed to hvac.Client for Enterprise support."""
        mock_hvac_module, mock_client = mock_hvac

        from framework.credentials.vault.hashicorp import HashiCorpVaultStorage

        HashiCorpVaultStorage(
            url="https://vault.example.com:8200",
            token="tok",
            namespace="my-namespace",
        )

        mock_hvac_module.Client.assert_called_with(
            url="https://vault.example.com:8200",
            token="tok",
            namespace="my-namespace",
            verify=True,
        )


# ===========================================================================
# TestHashiCorpVaultCRUD
# ===========================================================================

class TestHashiCorpVaultCRUD:
    """Tests for CRUD operations on HashiCorpVaultStorage."""

    def test_save_writes_to_vault(self, mock_hvac):
        """save() serializes credential and writes to Vault KV v2."""
        storage, mock_client = _make_vault_storage(mock_hvac)
        cred = _make_credential()

        storage.save(cred)

        mock_client.secrets.kv.v2.create_or_update_secret.assert_called_once()
        call_kwargs = mock_client.secrets.kv.v2.create_or_update_secret.call_args[1]
        assert call_kwargs["path"] == "hive/credentials/test-cred"
        assert call_kwargs["mount_point"] == "secret"
        assert "api_key" in call_kwargs["secret"]

    def test_load_reads_from_vault(self, mock_hvac):
        """load() reads and deserializes credential from Vault."""
        storage, mock_client = _make_vault_storage(mock_hvac)

        mock_client.secrets.kv.v2.read_secret_version.return_value = {
            "data": {
                "data": {
                    "_type": "api_key",
                    "api_key": "loaded-secret",
                },
            },
        }

        result = storage.load("test-cred")

        assert result is not None
        assert result.id == "test-cred"
        assert result.credential_type == CredentialType.API_KEY
        assert result.get_key("api_key") == "loaded-secret"

    def test_load_returns_none_for_not_found(self, mock_hvac):
        """load() returns None when secret is not found (404)."""
        storage, mock_client = _make_vault_storage(mock_hvac)

        mock_client.secrets.kv.v2.read_secret_version.side_effect = Exception(
            "404 not found"
        )

        result = storage.load("nonexistent")
        assert result is None

    def test_load_raises_on_non_404_error(self, mock_hvac):
        """load() re-raises non-404 errors."""
        storage, mock_client = _make_vault_storage(mock_hvac)

        mock_client.secrets.kv.v2.read_secret_version.side_effect = Exception(
            "Permission denied"
        )

        with pytest.raises(Exception, match="Permission denied"):
            storage.load("test-cred")

    def test_delete_removes_credential(self, mock_hvac):
        """delete() removes credential and all versions."""
        storage, mock_client = _make_vault_storage(mock_hvac)

        result = storage.delete("test-cred")

        assert result is True
        mock_client.secrets.kv.v2.delete_metadata_and_all_versions.assert_called_once()

    def test_delete_returns_false_for_not_found(self, mock_hvac):
        """delete() returns False when credential doesn't exist."""
        storage, mock_client = _make_vault_storage(mock_hvac)

        mock_client.secrets.kv.v2.delete_metadata_and_all_versions.side_effect = (
            Exception("not found")
        )

        result = storage.delete("nonexistent")
        assert result is False

    def test_exists_returns_true(self, mock_hvac):
        """exists() returns True when secret exists."""
        storage, mock_client = _make_vault_storage(mock_hvac)
        mock_client.secrets.kv.v2.read_secret_version.return_value = {"data": {}}

        assert storage.exists("test-cred") is True

    def test_exists_returns_false(self, mock_hvac):
        """exists() returns False when secret doesn't exist."""
        storage, mock_client = _make_vault_storage(mock_hvac)
        mock_client.secrets.kv.v2.read_secret_version.side_effect = Exception("not found")

        assert storage.exists("nonexistent") is False

    def test_list_all_returns_credential_ids(self, mock_hvac):
        """list_all() returns all credential IDs under prefix."""
        storage, mock_client = _make_vault_storage(mock_hvac)
        mock_client.secrets.kv.v2.list_secrets.return_value = {
            "data": {"keys": ["cred1", "cred2", "subfolder/"]}
        }

        result = storage.list_all()

        assert result == ["cred1", "cred2", "subfolder"]

    def test_list_all_returns_empty_for_not_found(self, mock_hvac):
        """list_all() returns empty list when prefix doesn't exist."""
        storage, mock_client = _make_vault_storage(mock_hvac)
        mock_client.secrets.kv.v2.list_secrets.side_effect = Exception("404 not found")

        assert storage.list_all() == []


# ===========================================================================
# TestHashiCorpVaultSerialization
# ===========================================================================

class TestHashiCorpVaultSerialization:
    """Tests for credential serialization/deserialization."""

    def test_serialize_basic_credential(self, mock_hvac):
        """_serialize_for_vault() converts CredentialObject to dict."""
        storage, _ = _make_vault_storage(mock_hvac)
        cred = _make_credential(
            provider_id="my-provider",
            description="A test credential",
            auto_refresh=True,
        )

        data = storage._serialize_for_vault(cred)

        assert data["_type"] == "api_key"
        assert data["_provider_id"] == "my-provider"
        assert data["_description"] == "A test credential"
        assert data["_auto_refresh"] == "true"
        assert data["api_key"] == "secret-value-123"

    def test_serialize_with_expiration(self, mock_hvac):
        """_serialize_for_vault() includes expiration metadata."""
        storage, _ = _make_vault_storage(mock_hvac)
        expires = datetime(2025, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        cred = _make_credential(
            keys={
                "token": CredentialKey(
                    name="token",
                    value=SecretStr("tok-123"),
                    expires_at=expires,
                ),
            }
        )

        data = storage._serialize_for_vault(cred)

        assert "_expires_token" in data
        assert "2025-12-31" in data["_expires_token"]

    def test_serialize_with_metadata(self, mock_hvac):
        """_serialize_for_vault() includes key metadata."""
        storage, _ = _make_vault_storage(mock_hvac)
        cred = _make_credential(
            keys={
                "token": CredentialKey(
                    name="token",
                    value=SecretStr("tok-123"),
                    metadata={"scope": "read", "client_id": "abc"},
                ),
            }
        )

        data = storage._serialize_for_vault(cred)

        assert "_metadata_token" in data

    def test_deserialize_basic(self, mock_hvac):
        """_deserialize_from_vault() reconstructs CredentialObject."""
        storage, _ = _make_vault_storage(mock_hvac)

        data = {
            "_type": "oauth2",
            "_provider_id": "github",
            "_description": "GitHub OAuth",
            "access_token": "ghp_xxx",
            "refresh_token": "ghr_yyy",
        }

        result = storage._deserialize_from_vault("github-cred", data)

        assert result.id == "github-cred"
        assert result.credential_type == CredentialType.OAUTH2
        assert result.provider_id == "github"
        assert result.get_key("access_token") == "ghp_xxx"
        assert result.get_key("refresh_token") == "ghr_yyy"

    def test_deserialize_with_expiration(self, mock_hvac):
        """_deserialize_from_vault() parses expiration from ISO format."""
        storage, _ = _make_vault_storage(mock_hvac)

        data = {
            "_type": "bearer_token",
            "token": "bearer-xxx",
            "_expires_token": "2025-12-31T23:59:59+00:00",
        }

        result = storage._deserialize_from_vault("test", data)

        token_key = result.keys["token"]
        assert token_key.expires_at is not None
        assert token_key.expires_at.year == 2025

    def test_deserialize_handles_invalid_datetime(self, mock_hvac):
        """_deserialize_from_vault() handles invalid datetime strings gracefully."""
        storage, _ = _make_vault_storage(mock_hvac)

        data = {
            "_type": "api_key",
            "key": "val",
            "_expires_key": "not-a-date",
        }

        result = storage._deserialize_from_vault("test", data)
        assert result.keys["key"].expires_at is None

    def test_deserialize_handles_metadata(self, mock_hvac):
        """_deserialize_from_vault() recovers metadata via ast.literal_eval."""
        storage, _ = _make_vault_storage(mock_hvac)

        data = {
            "_type": "api_key",
            "token": "val",
            "_metadata_token": "{'scope': 'read', 'env': 'prod'}",
        }

        result = storage._deserialize_from_vault("test", data)
        assert result.keys["token"].metadata == {"scope": "read", "env": "prod"}

    def test_deserialize_handles_corrupt_metadata(self, mock_hvac):
        """_deserialize_from_vault() handles corrupt metadata strings."""
        storage, _ = _make_vault_storage(mock_hvac)

        data = {
            "_type": "api_key",
            "token": "val",
            "_metadata_token": "INVALID{{{NOT_PYTHON",
        }

        result = storage._deserialize_from_vault("test", data)
        assert result.keys["token"].metadata == {}


# ===========================================================================
# TestHashiCorpVaultVersioning
# ===========================================================================

class TestHashiCorpVaultVersioning:
    """Tests for Vault-specific versioning operations."""

    def test_get_secret_metadata(self, mock_hvac):
        """get_secret_metadata() returns version info."""
        storage, mock_client = _make_vault_storage(mock_hvac)
        mock_client.secrets.kv.v2.read_secret_metadata.return_value = {
            "data": {
                "current_version": 3,
                "oldest_version": 1,
                "versions": {"1": {}, "2": {}, "3": {}},
            }
        }

        result = storage.get_secret_metadata("test-cred")

        assert result is not None
        assert result["current_version"] == 3

    def test_get_secret_metadata_returns_none_on_error(self, mock_hvac):
        """get_secret_metadata() returns None on any error."""
        storage, mock_client = _make_vault_storage(mock_hvac)
        mock_client.secrets.kv.v2.read_secret_metadata.side_effect = Exception("error")

        assert storage.get_secret_metadata("test-cred") is None

    def test_soft_delete_specific_versions(self, mock_hvac):
        """soft_delete() marks specific versions as deleted."""
        storage, mock_client = _make_vault_storage(mock_hvac)

        result = storage.soft_delete("test-cred", versions=[1, 2])

        assert result is True
        mock_client.secrets.kv.v2.delete_secret_versions.assert_called_once()

    def test_soft_delete_latest_version(self, mock_hvac):
        """soft_delete() without versions deletes latest."""
        storage, mock_client = _make_vault_storage(mock_hvac)

        result = storage.soft_delete("test-cred")

        assert result is True
        mock_client.secrets.kv.v2.delete_latest_version_of_secret.assert_called_once()

    def test_soft_delete_returns_false_on_error(self, mock_hvac):
        """soft_delete() returns False on error."""
        storage, mock_client = _make_vault_storage(mock_hvac)
        mock_client.secrets.kv.v2.delete_latest_version_of_secret.side_effect = (
            Exception("error")
        )

        assert storage.soft_delete("test-cred") is False

    def test_undelete_recovers_versions(self, mock_hvac):
        """undelete() restores soft-deleted versions."""
        storage, mock_client = _make_vault_storage(mock_hvac)

        result = storage.undelete("test-cred", versions=[1, 2])

        assert result is True
        mock_client.secrets.kv.v2.undelete_secret_versions.assert_called_once()

    def test_undelete_returns_false_on_error(self, mock_hvac):
        """undelete() returns False on error."""
        storage, mock_client = _make_vault_storage(mock_hvac)
        mock_client.secrets.kv.v2.undelete_secret_versions.side_effect = Exception("error")

        assert storage.undelete("test-cred", versions=[1]) is False

    def test_load_version_loads_specific_version(self, mock_hvac):
        """load_version() loads a specific version by number."""
        storage, mock_client = _make_vault_storage(mock_hvac)
        mock_client.secrets.kv.v2.read_secret_version.return_value = {
            "data": {
                "data": {
                    "_type": "api_key",
                    "key": "old-value",
                },
            },
        }

        result = storage.load_version("test-cred", version=2)

        assert result is not None
        assert result.get_key("key") == "old-value"
        call_kwargs = mock_client.secrets.kv.v2.read_secret_version.call_args[1]
        assert call_kwargs["version"] == 2

    def test_load_version_returns_none_on_error(self, mock_hvac):
        """load_version() returns None when version doesn't exist."""
        storage, mock_client = _make_vault_storage(mock_hvac)
        mock_client.secrets.kv.v2.read_secret_version.side_effect = Exception("not found")

        assert storage.load_version("test-cred", version=999) is None


# ===========================================================================
# TestHashiCorpVaultErrorHandling
# ===========================================================================

class TestHashiCorpVaultErrorHandling:
    """Tests for error handling paths."""

    def test_save_raises_on_write_error(self, mock_hvac):
        """save() re-raises errors from Vault write operations."""
        storage, mock_client = _make_vault_storage(mock_hvac)
        mock_client.secrets.kv.v2.create_or_update_secret.side_effect = Exception(
            "Permission denied"
        )

        with pytest.raises(Exception, match="Permission denied"):
            storage.save(_make_credential())

    def test_list_all_raises_on_non_404_error(self, mock_hvac):
        """list_all() re-raises errors that aren't 'not found'."""
        storage, mock_client = _make_vault_storage(mock_hvac)
        mock_client.secrets.kv.v2.list_secrets.side_effect = Exception(
            "Internal server error"
        )

        with pytest.raises(Exception, match="Internal server error"):
            storage.list_all()

    def test_path_sanitization_prevents_traversal(self, mock_hvac):
        """_path() sanitizes credential IDs by replacing slashes."""
        storage, _ = _make_vault_storage(mock_hvac)

        path = storage._path("../../etc/passwd")
        cred_part = path.split("hive/credentials/")[1]
        assert "/" not in cred_part
        assert "\\" not in cred_part

    def test_path_replaces_slashes(self, mock_hvac):
        """_path() replaces / and \\ with underscores."""
        storage, _ = _make_vault_storage(mock_hvac)

        path = storage._path("cred/with/slashes")
        assert path == "hive/credentials/cred_with_slashes"

        path2 = storage._path("cred\\with\\backslashes")
        assert path2 == "hive/credentials/cred_with_backslashes"

    def test_delete_raises_on_non_404_error(self, mock_hvac):
        """delete() re-raises errors that aren't 'not found'."""
        storage, mock_client = _make_vault_storage(mock_hvac)
        mock_client.secrets.kv.v2.delete_metadata_and_all_versions.side_effect = (
            Exception("Internal server error")
        )

        with pytest.raises(Exception, match="Internal server error"):
            storage.delete("test-cred")
