"""
Pluggable credential management system.

Supports multiple credential sources (Env vars, config files, Vault, etc.)
managed via a priority chain.
"""

import os
import logging
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from pathlib import Path
import yaml

from framework.errors import ConfigurationError

logger = logging.getLogger(__name__)

class CredentialSource(ABC):
    """Abstract base class for credential sources."""

    @abstractmethod
    def get(self, key: str) -> Optional[str]:
        """Retrieve a credential value by key."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the source for logging/audit."""
        pass


class EnvVarSource(CredentialSource):
    """Credential source that reads from environment variables."""

    def __init__(self, prefix: str = ""):
        self.prefix = prefix

    @property
    def name(self) -> str:
        return "Environment Variables"

    def get(self, key: str) -> Optional[str]:
        # Try exact match first, then with prefix
        val = os.environ.get(key)
        if val is None and self.prefix:
            val = os.environ.get(f"{self.prefix}{key}")
        return val


class ConfigFileSource(CredentialSource):
    """
    Credential source that reads from a YAML or JSON config file.
    
    Supports nested keys via dot notation for internal lookup, 
    but the main interface 'get' expects top-level keys usually.
    This simple implementation assumes a flat key-value map or uses the key directly.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path).expanduser().resolve()
        self._cache: Dict[str, Any] = {}
        self._ensure_loaded()

    @property
    def name(self) -> str:
        return f"Config File ({self.path})"

    def _ensure_loaded(self):
        if not self.path.exists():
            return

        try:
            with open(self.path, "r") as f:
                content = yaml.safe_load(f) or {}
                if isinstance(content, dict):
                    self._cache = content
                else:
                    logger.warning(f"Config file {self.path} must contain a dictionary")
        except Exception as e:
            logger.error(f"Failed to load credential config file {self.path}: {e}")

    def get(self, key: str) -> Optional[str]:
        # Reloading logic could be added here for hot-reloading
        val = self._cache.get(key)
        return str(val) if val is not None else None


class VaultSource(CredentialSource):
    """
    Credential source that reads from HashiCorp Vault.
    
    Requires 'hvac' package.
    """

    def __init__(self, url: str, token: str | None = None, mount_point: str = "secret", path: str = "data"):
        try:
            import hvac
        except ImportError:
            raise ImportError("VaultSource requires 'hvac'. Install with: pip install hvac")

        self.url = url
        self.mount_point = mount_point
        self.path = path
        self.client = hvac.Client(url=url, token=token)
        self._cache: Dict[str, str] = {}
        self._loaded = False
    
    @property
    def name(self) -> str:
        return f"Vault ({self.url})"

    def _ensure_loaded(self):
        if self._loaded:
            return
            
        if not self.client.is_authenticated():
            logger.warning(f"Vault client for {self.url} is not authenticated")
            return

        try:
            # Assume KV V2 engine
            response = self.client.secrets.kv.v2.read_secret_version(
                mount_point=self.mount_point,
                path=self.path
            )
            data = response.get("data", {}).get("data", {})
            self._cache.update(data)
            self._loaded = True
        except Exception as e:
            logger.error(f"Failed to read from Vault path {self.mount_point}/{self.path}: {e}")

    def get(self, key: str) -> Optional[str]:
        self._ensure_loaded()
        return self._cache.get(key)


class AWSSecretsSource(CredentialSource):
    """
    Credential source that reads from AWS Secrets Manager.
    
    Requires 'boto3' package.
    Secrets in AWS are often JSON blobs; we try to parse them and look up the key.
    If the secret is a plain string, we return it if the key matches the secret ID logic.
    """

    def __init__(self, secret_id: str, region_name: str | None = None):
        try:
            import boto3
            from botocore.exceptions import ClientError
            self.ClientError = ClientError
        except ImportError:
            raise ImportError("AWSSecretsSource requires 'boto3'. Install with: pip install boto3")

        self.secret_id = secret_id
        self.client = boto3.client("secretsmanager", region_name=region_name)
        self._cache: Dict[str, str] = {}
        self._loaded = False

    @property
    def name(self) -> str:
        return f"AWS Secrets Manager ({self.secret_id})"

    def _ensure_loaded(self):
        if self._loaded:
            return

        try:
            response = self.client.get_secret_value(SecretId=self.secret_id)
            secret_string = response.get("SecretString")
            
            if secret_string:
                try:
                    # Try to parse as JSON map
                    import json
                    data = json.loads(secret_string)
                    if isinstance(data, dict):
                        self._cache.update(data)
                    else:
                        # Secret is a JSON something else, treat entire thing as value?
                        # For now, simplistic approach:
                        pass 
                except json.JSONDecodeError:
                    # Not JSON, treat as a single value secret?
                    # The user can just use this source to fetch that one key?
                    # But get(key) expects a key mismatch. 
                    # Let's map it to "value" or something?
                    self._cache["value"] = secret_string
            
            self._loaded = True
        except self.ClientError as e:
            logger.error(f"Failed to get AWS secret {self.secret_id}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error getting AWS secret {self.secret_id}: {e}")

    def get(self, key: str) -> Optional[str]:
        self._ensure_loaded()
        return self._cache.get(key)



class CredentialManager:
    """
    Manager that chains multiple CredentialSources.
    
    Attributes:
        sources: List of CredentialSource instances in priority order.
    """

    def __init__(self, sources: List[CredentialSource] | None = None):
        if sources is None:
            # Default chain: Env Vars only
            self.sources = [EnvVarSource()]
        else:
            self.sources = sources

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Retrieve a credential by checking sources in order.
        
        Args:
            key: The credential key (e.g. "OPENAI_API_KEY")
            default: Value to return if not found in any source
            
        Returns:
            The credential value provided by the highest priority source, or default.
        """
        for source in self.sources:
            try:
                val = source.get(key)
                if val is not None:
                    # Optional: Add audit logging here (Phase 3)
                    # logger.debug(f"Found credential {key} in {source.name}")
                    return val
            except Exception as e:
                logger.warning(f"Error reading from credential source {source.name}: {e}")
                continue
        
        return default

    def get_or_error(self, key: str) -> str:
        """
        Retrieve a credential or raise an error if missing.
        
        Raises:
            ConfigurationError: If credential is not found.
        """
        val = self.get(key)
        if val is None:
            raise ConfigurationError(
                f"Missing required credential: {key}. "
                f"Checked sources: {', '.join(s.name for s in self.sources)}"
            )
        return val
