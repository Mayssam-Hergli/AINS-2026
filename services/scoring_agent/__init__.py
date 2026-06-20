"""MS2 Scoring Agent.

Reads MS1's ``diagnostic_answers`` from the shared ``project_profiles`` table, runs
five scoring tools, writes justifications, and stores five score objects back to the
``scores`` column for MS3 to consume. See ``INTEGRATION.md`` for the merge contract.
"""

from services.scoring_agent.agent import ScoringAgent
from services.scoring_agent.contracts import (
    DIAGNOSTIC_COLUMN,
    OVERALL_KEY,
    PILLAR_KEYS,
    PROFILE_TABLE,
    SCORE_KEYS,
    SCORES_COLUMN,
    SCORES_SCHEMA_VERSION,
    DiagnosticAnswersView,
    DomainView,
    ScoreBand,
    ScoreObject,
    ScoreSet,
    ToolResult,
)
from services.scoring_agent.justifier import JustificationWriter
from services.scoring_agent.repository import ScoreRepository
from services.scoring_agent.tools import (
    OverallScoringTool,
    PillarScoringTool,
    ScoringContext,
    ScoringTool,
    band_for,
    default_tools,
)

__all__ = [
    "ScoringAgent",
    "DIAGNOSTIC_COLUMN",
    "OVERALL_KEY",
    "PILLAR_KEYS",
    "PROFILE_TABLE",
    "SCORE_KEYS",
    "SCORES_COLUMN",
    "SCORES_SCHEMA_VERSION",
    "DiagnosticAnswersView",
    "DomainView",
    "ScoreBand",
    "ScoreObject",
    "ScoreSet",
    "ToolResult",
    "JustificationWriter",
    "ScoreRepository",
    "OverallScoringTool",
    "PillarScoringTool",
    "ScoringContext",
    "ScoringTool",
    "band_for",
    "default_tools",
]
