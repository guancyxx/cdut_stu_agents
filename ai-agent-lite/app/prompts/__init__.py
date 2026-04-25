"""Prompt template loader — reads prompts from prompts.yaml at startup."""
import logging
from pathlib import Path
from typing import Dict

import yaml

logger = logging.getLogger("ai-agent-lite.prompts")

_PROMPTS: Dict[str, dict] = {}


def _load_prompts() -> Dict[str, dict]:
    """Load all prompt templates from the YAML file."""
    yaml_path = Path(__file__).parent / "prompts.yaml"
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        logger.info("Loaded %d prompt sections from %s", len(data), yaml_path)
        return data or {}
    except Exception as exc:
        logger.warning("Failed to load prompts.yaml, will use inline fallbacks: %s", exc)
        return {}


def get_prompt(section: str, key: str = "template") -> str:
    """Get a prompt template string by section and key.

    Falls back to empty string if not found (callers should have their
    own inline fallback for resilience).
    """
    global _PROMPTS
    if not _PROMPTS:
        _PROMPTS = _load_prompts()
    section_data = _PROMPTS.get(section, {})
    if isinstance(section_data, str):
        return section_data
    return section_data.get(key, "")


def get_prompt_section(section: str) -> dict:
    """Get an entire prompt section (e.g., next_step_suggester with multiple templates)."""
    global _PROMPTS
    if not _PROMPTS:
        _PROMPTS = _load_prompts()
    return _PROMPTS.get(section, {})