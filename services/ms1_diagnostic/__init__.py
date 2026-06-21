"""MS1 — Diagnostic Engine.

Public surface for the perception-vs-reality diagnostic: a branching question DAG,
a gap detector, a multi-criteria blocker ranker, and a maturity classifier that
writes the ``diagnostic_answers`` contract to ``project_profiles`` for MS2.
"""

from services.ms1_diagnostic.answer_schema import (
    ALL_KEYS,
    ANSWERS_SCHEMA_VERSION,
    FIELD_SPECS,
    GROUPS,
    REQUIRED_KEYS,
    FieldSpec,
    build_diagnostic_answers,
    keys_for_group,
    validate_answers,
)
from services.ms1_diagnostic.blocker_ranker import (
    Blocker,
    BlockerCategory,
    BlockerRanker,
    CriteriaScores,
    CriteriaWeights,
)
from services.ms1_diagnostic.intake import AnswerRepository, IntakeService
from services.ms1_diagnostic.engine import (
    DiagnosticAnswers,
    DiagnosticEngine,
    DomainMaturity,
    LLMAssessment,
    LLMMaturityClassifier,
    MaturityLevel,
    OverallMaturity,
    ProjectProfileRepository,
    RuleEngine,
)
from services.ms1_diagnostic.gap_detector import (
    DomainGap,
    GapDetector,
    GapDirection,
    GapReport,
    GapSeverity,
)
from services.ms1_diagnostic.questions import (
    AnswerOption,
    Condition,
    ConditionOperator,
    DiagnosticResponse,
    Question,
    QuestionEdge,
    QuestionGraph,
    QuestionType,
    build_default_graph,
)

__all__ = [
    "ALL_KEYS",
    "ANSWERS_SCHEMA_VERSION",
    "FIELD_SPECS",
    "GROUPS",
    "REQUIRED_KEYS",
    "FieldSpec",
    "build_diagnostic_answers",
    "keys_for_group",
    "validate_answers",
    "AnswerRepository",
    "IntakeService",
    "Blocker",
    "BlockerCategory",
    "BlockerRanker",
    "CriteriaScores",
    "CriteriaWeights",
    "DiagnosticAnswers",
    "DiagnosticEngine",
    "DomainMaturity",
    "LLMAssessment",
    "LLMMaturityClassifier",
    "MaturityLevel",
    "OverallMaturity",
    "ProjectProfileRepository",
    "RuleEngine",
    "DomainGap",
    "GapDetector",
    "GapDirection",
    "GapReport",
    "GapSeverity",
    "AnswerOption",
    "Condition",
    "ConditionOperator",
    "DiagnosticResponse",
    "Question",
    "QuestionEdge",
    "QuestionGraph",
    "QuestionType",
    "build_default_graph",
]
