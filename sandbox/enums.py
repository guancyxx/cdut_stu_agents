"""Enumerations for the cdut-sandbox container.

These mirror ai-agent-lite/app/models/enums.py for the Verdict enum
but live in the sandbox directory because this container runs standalone.
"""
from enum import Enum


class Verdict(str, Enum):
    """OJ submission verdicts."""
    AC = "AC"
    WA = "WA"
    TLE = "TLE"
    MLE = "MLE"
    RE = "RE"
    CE = "CE"
    SE = "SE"
