"""Runtime configuration."""
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


def _load_preferred_model() -> str:
    """Load preferred model from ~/.hive/configuration.json."""
    default_model = "anthropic/claude-sonnet-4-20250514"
    config_path = Path.home() / ".hive" / "configuration.json"
    
    if not config_path.exists():
        return default_model
    
    try:
        with open(config_path) as f:
            config = json.load(f)
        
        llm = config.get("llm", {})
        
        if llm.get("provider") and llm.get("model"):
            return f"{llm['provider']}/{llm['model']}"
        else:
            logger.warning(
                "Configuration file %s is missing 'llm.provider' or 'llm.model'. "
                "Falling back to default model: %s",
                config_path, default_model
            )
    except json.JSONDecodeError as e:
        logger.error(
            "Invalid JSON in configuration file %s at line %d, column %d: %s. "
            "Falling back to default model: %s",
            config_path, e.lineno, e.colno, e.msg, default_model
        )
    except (IOError, OSError) as e:
        logger.error(
            "Error reading configuration file %s: %s. "
            "Falling back to default model: %s",
            config_path, e, default_model
        )
    except Exception as e:
        logger.exception(
            "Unexpected error loading configuration from %s: %s. "
            "Falling back to default model: %s",
            config_path, e, default_model
        )
    
    return default_model


@dataclass
class RuntimeConfig:
    model: str = field(default_factory=_load_preferred_model)
    temperature: float = 0.7
    max_tokens: int = 8192
    api_key: str | None = None
    api_base: str | None = None


default_config = RuntimeConfig()


# Agent metadata
@dataclass
class AgentMetadata:
    name: str = "Online Research Agent"
    version: str = "1.0.0"
    description: str = "Research any topic by searching multiple sources, synthesizing information, and producing a well-structured narrative report with citations."


metadata = AgentMetadata()
