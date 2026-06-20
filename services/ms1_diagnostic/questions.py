"""Graph/DAG-based branching question tree for MS1.

The diagnostic questionnaire is modelled as a directed acyclic graph: each
:class:`Question` is a node, and :class:`QuestionEdge` instances connect a question
to its follow-ups, optionally gated by a :class:`Condition` on the source answer.
This lets the questionnaire branch — e.g. only ask about ESRS data points if the
respondent says they're in scope for CSRD — while guaranteeing (via cycle
detection at build time) that traversal always terminates.

Answers collected here form the "perception" half of MS1's analysis: what the
organisation *believes* about its own posture.
"""

from __future__ import annotations

from collections import deque
from enum import Enum
from typing import Any, Callable

from pydantic import BaseModel, ConfigDict, Field

from services.file_parser.normalizer import SignalDomain


class QuestionType(str, Enum):
    BOOLEAN = "boolean"
    SINGLE_CHOICE = "single_choice"
    MULTI_CHOICE = "multi_choice"
    SCALE = "scale"  # ordinal 0..max_scale
    NUMERIC = "numeric"


class ConditionOperator(str, Enum):
    EQ = "eq"
    NE = "ne"
    IN = "in"
    GTE = "gte"
    LTE = "lte"
    CONTAINS = "contains"  # for multi-choice answers
    TRUTHY = "truthy"


class Condition(BaseModel):
    """A declarative predicate evaluated against a source question's answer."""

    model_config = ConfigDict(frozen=True)

    operator: ConditionOperator
    value: Any = None

    def matches(self, answer: Any) -> bool:
        op = self.operator
        if op is ConditionOperator.TRUTHY:
            return bool(answer)
        if answer is None:
            return False
        if op is ConditionOperator.EQ:
            return answer == self.value
        if op is ConditionOperator.NE:
            return answer != self.value
        if op is ConditionOperator.IN:
            return answer in (self.value or [])
        if op is ConditionOperator.CONTAINS:
            return isinstance(answer, (list, tuple, set)) and self.value in answer
        if op is ConditionOperator.GTE:
            return _as_number(answer) >= _as_number(self.value)
        if op is ConditionOperator.LTE:
            return _as_number(answer) <= _as_number(self.value)
        return False


def _as_number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


class AnswerOption(BaseModel):
    """A selectable choice carrying a maturity score in ``[0, 1]``."""

    model_config = ConfigDict(frozen=True)

    value: str
    label: str
    score: float = Field(default=0.0, ge=0.0, le=1.0)


class Question(BaseModel):
    """A single diagnostic question (a node in the DAG)."""

    model_config = ConfigDict(frozen=True)

    id: str
    domain: SignalDomain
    text: str
    type: QuestionType
    options: tuple[AnswerOption, ...] = ()
    max_scale: int = 5
    weight: float = Field(default=1.0, gt=0.0, description="Relative importance in scoring.")
    required: bool = True

    def normalized_score(self, answer: Any) -> float | None:
        """Map a raw answer to a ``[0, 1]`` maturity contribution, or ``None``.

        ``None`` means the question was not (validly) answered and should be
        excluded from perceived-score aggregation.
        """
        if answer is None:
            return None
        if self.type is QuestionType.BOOLEAN:
            return 1.0 if bool(answer) else 0.0
        if self.type is QuestionType.SCALE:
            number = _as_number(answer)
            if number != number or self.max_scale <= 0:  # NaN guard
                return None
            return max(0.0, min(number / self.max_scale, 1.0))
        if self.type is QuestionType.NUMERIC:
            number = _as_number(answer)
            return None if number != number else max(0.0, min(number, 1.0))
        if self.type is QuestionType.SINGLE_CHOICE:
            for option in self.options:
                if option.value == answer:
                    return option.score
            return None
        if self.type is QuestionType.MULTI_CHOICE:
            if not isinstance(answer, (list, tuple, set)) or not self.options:
                return None
            chosen = [opt.score for opt in self.options if opt.value in answer]
            if not chosen:
                return 0.0
            # Average of the selected options' scores.
            return sum(chosen) / len(chosen)
        return None


class QuestionEdge(BaseModel):
    """A directed edge from one question to a follow-up, optionally gated."""

    model_config = ConfigDict(frozen=True)

    source: str
    target: str
    condition: Condition | None = None

    def is_open(self, source_answer: Any) -> bool:
        return self.condition is None or self.condition.matches(source_answer)


class CyclicGraphError(ValueError):
    """Raised when the configured questions form a cycle (not a DAG)."""


class DiagnosticResponse(BaseModel):
    """A respondent's answers, keyed by question id."""

    project_id: str
    answers: dict[str, Any] = Field(default_factory=dict)

    def answer_for(self, question_id: str) -> Any:
        return self.answers.get(question_id)


class QuestionGraph:
    """A DAG of diagnostic questions with branching traversal.

    Roots (questions with no incoming edges) are always active. A non-root question
    becomes active once *at least one* incoming edge is "open" given current answers.
    """

    def __init__(self, questions: list[Question], edges: list[QuestionEdge]) -> None:
        self._questions: dict[str, Question] = {q.id: q for q in questions}
        if len(self._questions) != len(questions):
            raise ValueError("Duplicate question ids in graph")

        self._edges = list(edges)
        self._outgoing: dict[str, list[QuestionEdge]] = {q.id: [] for q in questions}
        self._incoming: dict[str, list[QuestionEdge]] = {q.id: [] for q in questions}
        for edge in self._edges:
            if edge.source not in self._questions or edge.target not in self._questions:
                raise ValueError(f"Edge references unknown question: {edge}")
            self._outgoing[edge.source].append(edge)
            self._incoming[edge.target].append(edge)

        self._roots = tuple(qid for qid, edges in self._incoming.items() if not edges)
        self._topological_order = self._topo_sort()

    @property
    def questions(self) -> dict[str, Question]:
        return dict(self._questions)

    @property
    def roots(self) -> tuple[str, ...]:
        return self._roots

    def get(self, question_id: str) -> Question:
        return self._questions[question_id]

    def _topo_sort(self) -> list[str]:
        indegree = {qid: len(edges) for qid, edges in self._incoming.items()}
        queue: deque[str] = deque(qid for qid, deg in indegree.items() if deg == 0)
        order: list[str] = []
        while queue:
            node = queue.popleft()
            order.append(node)
            for edge in self._outgoing[node]:
                indegree[edge.target] -= 1
                if indegree[edge.target] == 0:
                    queue.append(edge.target)
        if len(order) != len(self._questions):
            raise CyclicGraphError("Question graph contains a cycle; expected a DAG")
        return order

    def active_questions(self, answers: dict[str, Any]) -> list[Question]:
        """Return questions reachable given the current answers, in DAG order."""
        active: set[str] = set(self._roots)
        for qid in self._topological_order:
            if qid not in active:
                continue
            source_answer = answers.get(qid)
            for edge in self._outgoing[qid]:
                if edge.is_open(source_answer):
                    active.add(edge.target)
        return [self._questions[qid] for qid in self._topological_order if qid in active]

    def next_questions(self, answers: dict[str, Any]) -> list[Question]:
        """Active questions that are still unanswered — what to ask next."""
        return [q for q in self.active_questions(answers) if answers.get(q.id) is None]

    def is_complete(self, answers: dict[str, Any]) -> bool:
        """True when every *required* active question has an answer."""
        return all(
            answers.get(q.id) is not None
            for q in self.active_questions(answers)
            if q.required
        )

    def coverage(self, answers: dict[str, Any]) -> float:
        """Fraction of active questions that have been answered."""
        active = self.active_questions(answers)
        if not active:
            return 1.0
        answered = sum(1 for q in active if answers.get(q.id) is not None)
        return round(answered / len(active), 4)

    def filter_answers(self, answers: dict[str, Any]) -> dict[str, Any]:
        """Drop answers for questions that aren't active (e.g. abandoned branches)."""
        active_ids = {q.id for q in self.active_questions(answers)}
        return {qid: value for qid, value in answers.items() if qid in active_ids}

    def validate_answers(self, answers: dict[str, Any]) -> list[str]:
        """Return a list of schema violations in ``answers`` (empty list = valid).

        Catches unknown question ids and values that don't conform to a question's
        type (e.g. a choice value not in its options, a scale out of range) before
        they can silently skew scoring downstream.
        """
        issues: list[str] = []
        for qid, value in answers.items():
            question = self._questions.get(qid)
            if question is None:
                issues.append(f"unknown question id: {qid!r}")
                continue
            if value is None:
                continue
            issues.extend(self._validate_value(question, value))
        return issues

    @staticmethod
    def _validate_value(question: "Question", value: Any) -> list[str]:
        qid = question.id
        qtype = question.type
        if qtype is QuestionType.BOOLEAN:
            if not isinstance(value, bool) and value not in (0, 1):
                return [f"{qid}: expected a boolean, got {value!r}"]
        elif qtype is QuestionType.SCALE:
            number = _as_number(value)
            if number != number:
                return [f"{qid}: expected a number, got {value!r}"]
            if not 0 <= number <= question.max_scale:
                return [f"{qid}: scale value {value!r} out of range 0..{question.max_scale}"]
        elif qtype is QuestionType.NUMERIC:
            if _as_number(value) != _as_number(value):  # NaN check
                return [f"{qid}: expected a number, got {value!r}"]
        elif qtype is QuestionType.SINGLE_CHOICE:
            valid = {opt.value for opt in question.options}
            if value not in valid:
                return [f"{qid}: {value!r} not in options {sorted(valid)}"]
        elif qtype is QuestionType.MULTI_CHOICE:
            if not isinstance(value, (list, tuple, set)):
                return [f"{qid}: expected a list of options, got {value!r}"]
            valid = {opt.value for opt in question.options}
            unknown = [v for v in value if v not in valid]
            if unknown:
                return [f"{qid}: unknown options {unknown} (valid: {sorted(valid)})"]
        return []


# ---------------------------------------------------------------------------
# Default questionnaire
# ---------------------------------------------------------------------------

def _yes_no(score_yes: float = 1.0) -> tuple[AnswerOption, ...]:
    return (
        AnswerOption(value="yes", label="Yes", score=score_yes),
        AnswerOption(value="no", label="No", score=0.0),
    )


def build_default_graph() -> QuestionGraph:
    """A representative sustainability / compliance diagnostic DAG.

    Branches: CSRD scope unlocks ESRS data-point depth; an emissions-tracking "yes"
    unlocks a Scope-3 follow-up; a governance ethics policy unlocks a whistleblower
    follow-up.
    """
    questions = [
        # --- Compliance backbone ---
        Question(
            id="c_csrd_scope",
            domain=SignalDomain.COMPLIANCE,
            text="Is your organisation in scope for CSRD / ESRS reporting?",
            type=QuestionType.BOOLEAN,
            options=_yes_no(),
            weight=1.5,
        ),
        Question(
            id="c_esrs_datapoints",
            domain=SignalDomain.COMPLIANCE,
            text="How complete is your ESRS data-point inventory?",
            type=QuestionType.SCALE,
            max_scale=5,
            weight=1.3,
        ),
        Question(
            id="c_external_assurance",
            domain=SignalDomain.COMPLIANCE,
            text="Is your sustainability disclosure externally assured?",
            type=QuestionType.SINGLE_CHOICE,
            options=(
                AnswerOption(value="reasonable", label="Reasonable assurance", score=1.0),
                AnswerOption(value="limited", label="Limited assurance", score=0.6),
                AnswerOption(value="none", label="No external assurance", score=0.0),
            ),
            weight=1.2,
        ),
        # --- Environmental ---
        Question(
            id="e_emissions_tracking",
            domain=SignalDomain.ENVIRONMENTAL,
            text="Do you systematically track greenhouse-gas emissions?",
            type=QuestionType.BOOLEAN,
            options=_yes_no(),
            weight=1.4,
        ),
        Question(
            id="e_scope3",
            domain=SignalDomain.ENVIRONMENTAL,
            text="How mature is your Scope 3 (value-chain) emissions accounting?",
            type=QuestionType.SCALE,
            max_scale=5,
            weight=1.2,
        ),
        Question(
            id="e_reduction_target",
            domain=SignalDomain.ENVIRONMENTAL,
            text="Have you set a science-based emissions reduction target?",
            type=QuestionType.SINGLE_CHOICE,
            options=(
                AnswerOption(value="validated", label="SBTi-validated", score=1.0),
                AnswerOption(value="committed", label="Committed, not validated", score=0.6),
                AnswerOption(value="internal", label="Internal target only", score=0.4),
                AnswerOption(value="none", label="No target", score=0.0),
            ),
            weight=1.1,
        ),
        # --- Social ---
        Question(
            id="s_dei_metrics",
            domain=SignalDomain.SOCIAL,
            text="Which workforce metrics do you track?",
            type=QuestionType.MULTI_CHOICE,
            options=(
                AnswerOption(value="gender_pay", label="Gender pay gap", score=1.0),
                AnswerOption(value="diversity", label="Workforce diversity", score=1.0),
                AnswerOption(value="safety", label="Health & safety incidents", score=1.0),
                AnswerOption(value="training", label="Training hours", score=1.0),
            ),
            required=False,
        ),
        # --- Governance ---
        Question(
            id="g_ethics_policy",
            domain=SignalDomain.GOVERNANCE,
            text="Do you have a board-approved code of conduct / ethics policy?",
            type=QuestionType.BOOLEAN,
            options=_yes_no(),
            weight=1.2,
        ),
        Question(
            id="g_whistleblower",
            domain=SignalDomain.GOVERNANCE,
            text="Is there an independent whistleblower mechanism?",
            type=QuestionType.BOOLEAN,
            options=_yes_no(),
            weight=1.0,
        ),
    ]

    edges = [
        QuestionEdge(
            source="c_csrd_scope",
            target="c_esrs_datapoints",
            condition=Condition(operator=ConditionOperator.TRUTHY),
        ),
        QuestionEdge(source="c_csrd_scope", target="c_external_assurance"),
        QuestionEdge(source="c_esrs_datapoints", target="e_emissions_tracking"),
        QuestionEdge(
            source="e_emissions_tracking",
            target="e_scope3",
            condition=Condition(operator=ConditionOperator.TRUTHY),
        ),
        QuestionEdge(source="e_emissions_tracking", target="e_reduction_target"),
        QuestionEdge(source="e_reduction_target", target="s_dei_metrics"),
        QuestionEdge(source="s_dei_metrics", target="g_ethics_policy"),
        QuestionEdge(
            source="g_ethics_policy",
            target="g_whistleblower",
            condition=Condition(operator=ConditionOperator.TRUTHY),
        ),
    ]

    return QuestionGraph(questions, edges)


# Re-exported for callers who want to plug in custom predicate logic if needed.
ConditionPredicate = Callable[[Any], bool]
