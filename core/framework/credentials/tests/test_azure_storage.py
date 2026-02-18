"""Tests for Azure Key Vault storage adapter."""

import json
from unittest.mock import MagicMock, patch

import pytest
from pydantic import SecretStr

# Use absolute imports assuming this runs from core root
from framework.credentials.models import CredentialKey, CredentialObject, CredentialType
from framework.credentials.vault.azure import AzureKeyVaultStorage


@pytest.fixture
def mock_credential():
    return CredentialObject(
        id="test-cred",
        credential_type=CredentialType.API_KEY,
        keys={"api_key": CredentialKey(name="api_key", value=SecretStr("secret-value"))},
    )


@pytest.fixture
def mock_azure_modules():
    # Mock the azure modules so we don't need them installed
    mock_identity = MagicMock()
    mock_secrets = MagicMock()

    with patch.dict(
        "sys.modules",
        {
            "azure": MagicMock(),
            "azure.identity": mock_identity,
            "azure.keyvault": MagicMock(),
            "azure.keyvault.secrets": mock_secrets,
            "azure.core": MagicMock(),
            "azure.core.exceptions": MagicMock(),
        },
    ):
        yield mock_identity, mock_secrets


@pytest.fixture
def mock_azure_client(mock_azure_modules):
    _, mock_secrets = mock_azure_modules
    # Configure the mocked SecretClient class
    mock_client_instance = MagicMock()
    mock_client_cls = MagicMock(return_value=mock_client_instance)
    mock_secrets.SecretClient = mock_client_cls

    return mock_client_instance


@pytest.fixture
def azure_storage(mock_azure_client):
    # The fixture ensures modules are mocked during instantiation via dependency chain
    return AzureKeyVaultStorage(vault_url="https://test.vault.azure.net/")


def test_save(azure_storage, mock_azure_client, mock_credential):
    azure_storage.save(mock_credential)

    mock_azure_client.set_secret.assert_called_once()
    args, _ = mock_azure_client.set_secret.call_args
    secret_name, secret_value = args

    assert secret_name == "test-cred"
    data = json.loads(secret_value)
    assert data["id"] == "test-cred"
    assert data["keys"]["api_key"]["value"] == "secret-value"


def test_load(azure_storage, mock_azure_client):
    mock_secret = MagicMock()
    # Mock the JSON structure corresponding to a saved credential
    mock_secret.value = json.dumps(
        {
            "id": "test-cred",
            "credential_type": "api_key",
            "keys": {"api_key": {"name": "api_key", "value": "secret-value"}},
        }
    )
    mock_azure_client.get_secret.return_value = mock_secret

    loaded = azure_storage.load("test-cred")

    assert loaded is not None
    assert loaded.id == "test-cred"
    assert loaded.get_key("api_key") == "secret-value"
    mock_azure_client.get_secret.assert_called_with("test-cred")


def test_load_not_found(azure_storage, mock_azure_client):
    # Simulate Azure SDK exception for Not Found
    mock_azure_client.get_secret.side_effect = Exception("(ResourceNotFound) Secret not found")

    loaded = azure_storage.load("non-existent")
    assert loaded is None


def test_delete(azure_storage, mock_azure_client):
    result = azure_storage.delete("test-cred")

    assert result is True
    mock_azure_client.begin_delete_secret.assert_called_with("test-cred")


def test_delete_not_found(azure_storage, mock_azure_client):
    mock_azure_client.begin_delete_secret.side_effect = Exception(
        "(ResourceNotFound) Secret not found"
    )

    result = azure_storage.delete("non-existent")
    assert result is False


def test_list_all(azure_storage, mock_azure_client):
    mock_secret1 = MagicMock()
    mock_secret1.name = "cred1"
    mock_secret2 = MagicMock()
    mock_secret2.name = "cred2"

    mock_azure_client.list_properties_of_secrets.return_value = [mock_secret1, mock_secret2]

    creds = azure_storage.list_all()
    assert "cred1" in creds
    assert "cred2" in creds
    assert len(creds) == 2


def test_exists(azure_storage, mock_azure_client):
    mock_azure_client.get_secret.return_value = MagicMock()
    assert azure_storage.exists("test-cred") is True

    mock_azure_client.get_secret.side_effect = Exception("Not found")
    assert azure_storage.exists("non-existent") is False
