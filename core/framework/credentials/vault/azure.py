"""
Azure Key Vault storage adapter.

Provides integration with Azure Key Vault for secure secret management.
Requires 'azure-identity' and 'azure-keyvault-secrets' packages.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import SecretStr

from ..models import CredentialObject
from ..storage import CredentialStorage

logger = logging.getLogger(__name__)


class AzureKeyVaultStorage(CredentialStorage):
    """
    Azure Key Vault storage adapter.

    Stores credentials as secrets in Azure Key Vault.
    Each credential is stored as a JSON string in a secret.

    The secret name corresponds to the credential ID (sanitized).
    The secret value contains the full CredentialObject serialization.

    Authentication:
    - Uses DefaultAzureCredential, which supports:
      - Environment variables (AZURE_CLIENT_ID, etc.)
      - Managed Identity
      - Azure CLI (az login)
      - Visual Studio Code
    """

    def __init__(
        self,
        vault_url: str,
        credential: Any | None = None,
    ):
        """
        Initialize Azure Key Vault storage.

        Args:
            vault_url: The URL of the key vault (e.g., https://myvault.vault.azure.net/)
            credential: The token credential to use for authentication.
                        If None, DefaultAzureCredential is used.
        """
        try:
            from azure.identity import DefaultAzureCredential
            from azure.keyvault.secrets import SecretClient
        except ImportError as e:
            raise ImportError(
                "Azure Key Vault support requires 'azure-identity' and 'azure-keyvault-secrets'. "
                "Install with: uv pip install azure-identity azure-keyvault-secrets"
            ) from e

        self.vault_url = vault_url
        self._credential = credential or DefaultAzureCredential()
        self._client = SecretClient(vault_url=self.vault_url, credential=self._credential)

        logger.info(f"Connected to Azure Key Vault at {vault_url}")

    def _secret_name(self, credential_id: str) -> str:
        """
        Convert credential ID to a valid AKV secret name.
        AKV secret names must be 1-127 characters, containing only 0-9, a-z, A-Z, and -.
        """
        # Replace invalid characters with dashes
        safe_id = "".join(c if c.isalnum() or c == "-" else "-" for c in credential_id)
        # Ensure it starts with a letter (encouraged but numbers allowed)
        # AKV allows starting with alphanumeric.
        return safe_id

    def save(self, credential: CredentialObject) -> None:
        """Save credential to Azure Key Vault."""
        secret_name = self._secret_name(credential.id)

        # Serialize to JSON
        data = self._serialize_credential(credential)
        json_str = json.dumps(data)

        try:
            self._client.set_secret(secret_name, json_str)
            logger.debug(f"Saved credential '{credential.id}' to Azure Key Vault")
        except Exception as e:
            logger.error(f"Failed to save credential '{credential.id}' to Azure Key Vault: {e}")
            raise

    def load(self, credential_id: str) -> CredentialObject | None:
        """Load credential from Azure Key Vault."""
        secret_name = self._secret_name(credential_id)

        try:
            secret = self._client.get_secret(secret_name)
            if not secret.value:
                return None

            data = json.loads(secret.value)
            return self._deserialize_credential(data)
        except Exception as e:
            error_str = str(e).lower()
            if "not found" in error_str or "404" in error_str:
                logger.debug(f"Credential '{credential_id}' not found in Azure Key Vault")
                return None
            logger.error(f"Failed to load credential '{credential_id}' from Azure Key Vault: {e}")
            raise

    def delete(self, credential_id: str) -> bool:
        """Delete credential from Azure Key Vault."""
        secret_name = self._secret_name(credential_id)

        try:
            # begin_delete_secret returns a Poller
            poller = self._client.begin_delete_secret(secret_name)
            poller.wait()
            logger.debug(f"Deleted credential '{credential_id}' from Azure Key Vault")
            return True
        except Exception as e:
            error_str = str(e).lower()
            if "not found" in error_str or "404" in error_str:
                return False
            logger.error(f"Failed to delete credential '{credential_id}' from Azure Key Vault: {e}")
            raise

    def list_all(self) -> list[str]:
        """List all credential IDs (secret names)."""
        try:
            secrets = self._client.list_properties_of_secrets()
            # We assume secret name maps to credential ID roughly (ignoring sanitization lossiness)
            return [s.name for s in secrets]
        except Exception as e:
            logger.error(f"Failed to list credentials from Azure Key Vault: {e}")
            raise

    def exists(self, credential_id: str) -> bool:
        """Check if credential exists."""
        secret_name = self._secret_name(credential_id)
        try:
            self._client.get_secret(secret_name)
            return True
        except Exception:
            return False

    def _serialize_credential(self, credential: CredentialObject) -> dict[str, Any]:
        """Convert credential to JSON-serializable dict."""
        # Ideally storage.py would expose _serialize_credential as protected
        # It is exposed in CredentialStorage but it's instance method.
        # Check parent implementation.
        # No, EncryptedFileStorage has it.
        # Just implement our own.

        data = credential.model_dump(mode="json")

        # Extract secret values
        for key_name, key_data in data.get("keys", {}).items():
            if "value" in key_data:
                actual_key = credential.keys.get(key_name)
                if actual_key:
                    key_data["value"] = actual_key.get_secret_value()

        return data

    def _deserialize_credential(self, data: dict[str, Any]) -> CredentialObject:
        """Reconstruct credential from dict."""
        for key_data in data.get("keys", {}).values():
            if "value" in key_data and isinstance(key_data["value"], str):
                key_data["value"] = SecretStr(key_data["value"])

        return CredentialObject.model_validate(data)
