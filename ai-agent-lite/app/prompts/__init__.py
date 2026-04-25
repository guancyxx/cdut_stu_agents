"""Prompt template loader — reads .md files from the prompts directory.

Each prompt is a single Markdown file using $variable placeholders
(compatible with string.Template). No YAML, nobrace escaping issues.
"""
import logging
from pathlib import Path
from string import Template
from typing import Dict

logger = logging.getLogger("ai-agent-lite.prompts")

_PROMPTS_DIR = Path(__file__).parent
_CACHE: Dict[str, str] = {}


def _load_prompt(name: str) -> str:
    """Load a single .md prompt file by name (without extension)."""
    md_path = _PROMPTS_DIR / f"{name}.md"
    try:
        text = md_path.read_text(encoding="utf-8")
        logger.debug("Loaded prompt %s (%d bytes)", name, len(text))
        return text
    except FileNotFoundError:
        logger.warning("Prompt file not found: %s", md_path)
        return ""


def get_prompt(name: str) -> str:
    """Get a prompt template string by file name (without .md extension).

    Returns the raw template text with $variable placeholders.
    Callers should use string.Template to substitute variables,
    or fall back to their own inline template.
    """
    global _CACHE
    if name not in _CACHE:
        _CACHE[name] = _load_prompt(name)
    return _CACHE[name]



def render_prompt(name: str, **kwargs) -> str:
    """Load a prompt template and substitute variables in one call.

    Uses string.Template.safe_substitute() so missing variables
    are left as-is instead of raising KeyError.
    """
    template_text = get_prompt(name)
    if not template_text:
        return ""
    return Template(template_text).safe_substitute(**kwargs)