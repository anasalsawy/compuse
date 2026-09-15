"""Provider-neutral OpenAI-compatible model adapter for Compuse.

It intentionally uses the standard library so Featherless, OpenAI, Azure
OpenAI-compatible gateways, or a local gateway can be selected by environment
variables without changing the runtime.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any

from pydantic import ValidationError

from .contracts import (
    BCoreReview,
    BatchSpec,
    DeceptionGrade,
    LobeBProfile,
    LobeDecision,
    ParallelSplitPlan,
    RuntimeObservation,
    ScreenAssessment,
)


class ModelError(RuntimeError):
    pass


class OpenAICompatibleClient:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        self.base_url = (base_url or os.getenv("COMPUSE_LLM_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.api_key = api_key if api_key is not None else os.getenv("COMPUSE_LLM_API_KEY", "")
        self.model = model or os.getenv("COMPUSE_LLM_MODEL", "gpt-4.1-mini")
        self.timeout = timeout

    @property
    def endpoint(self) -> str:
        return self.base_url if self.base_url.endswith("/chat/completions") else f"{self.base_url}/chat/completions"

    def complete_json(self, *, system: str, user_text: str, observation: RuntimeObservation | None = None) -> dict[str, Any]:
        content: list[dict[str, Any]] = [{"type": "text", "text": user_text}]
        if observation is not None and observation.screenshot_data_url:
            content.append({
                "type": "image_url",
                "image_url": {"url": observation.screenshot_data_url},
            })
        payload = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": content},
            ],
        }
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = urllib.request.Request(self.endpoint, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            raise ModelError(f"model request failed: {exc}") from exc
        try:
            envelope = json.loads(raw)
            content_value = envelope["choices"][0]["message"]["content"]
            if isinstance(content_value, list):
                content_value = "".join(
                    str(part.get("text", "")) if isinstance(part, dict) else str(part)
                    for part in content_value
                )
            return self._parse_json_object(str(content_value))
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ModelError(f"model returned an invalid JSON response: {exc}") from exc

    @staticmethod
    def _parse_json_object(text: str) -> dict[str, Any]:
        cleaned = text.strip()
        fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL | re.IGNORECASE)
        if fenced:
            cleaned = fenced.group(1).strip()
        value = json.loads(cleaned)
        if not isinstance(value, dict):
            raise ValueError("top-level response must be an object")
        return value


_A_SYSTEM = """You are Lobe A, the active computer-use planner in Compuse.
Return JSON only, matching the exact BatchSpec schema supplied in the user
message. Do not use a generic computer-use action format. The top-level object
must contain batch_id, actions, preconditions, predicted_end, confidence,
risk, barrier_after, terminal, and source_lobe. Every action must use the
exact discriminator field `kind`; never use `action_type`, `button`, `clicks`,
or `modifiers`. Plan at most 8 typed actions.
You see the current desktop observation and must keep a short, executable
batch; stop before a modal, navigation, submit, login, payment, or other state
transition whose result cannot be predicted. The predicted_end must describe
where the desktop will be after every action and include at least one checkable
anchor: an exact foreground_window, exact browser_url, or required_markers.
source_lobe must be \"A\". Do not invent that an action succeeded; the runtime
will observe the real desktop after dispatch. Do not omit required metadata or
add fields not present in the supplied schema."""

_B_SYSTEM = """You are Lobe B, Compuse's live shadow lobe and handoff gate.
Return JSON only matching the exact LobeDecision schema supplied in the user
message. If a batch is present, it must be a complete BatchSpec. Every action
inside it must use `kind` as the discriminator; never use `action_type`,
`button`, `clicks`, or `modifiers`.
You receive Lobe A's exact current action batch and its predicted end state.
Independently prepare the next bounded typed-action batch starting from that
predicted end. The next batch's preconditions.source_batch_id must equal the
active batch_id, and its preconditions must preserve the predicted end's
checkable anchors. Reject the handoff if the predicted state is not concrete,
the next action is not grounded, or the sequence crosses an uncertain
transition. Use approved=false and batch=null when rejecting. source_lobe must
be \"B\". B is allowed to challenge A; never approve a guess.

core_review is mandatory and is B's always-on foundation. It must broaden the
context with useful notes, missing prerequisites, failure modes, and unasked
questions. It must also review claims: GREEN means no deception detected, not
guaranteed truth. If a claim says an action created, changed, or completed an
artifact, proof_required must request the full artifact, not only a manifest or
summary. Keep core_review concise and evidence-based."""

_SCREEN_SYSTEM = """You are Lobe B in Compuse's continuous screen-awareness mode.
Return JSON only with observation_revision, status, and reason. Inspect the
current screenshot and metadata independently of Lobe A. Use status=stable
when the visible desktop is a safe continuation of the active batch, changed
when it is a normal expected transition, and unsafe when focus, application,
modal state, or visible content makes the next action unreliable. Never claim
stable from a guess; an unknown screen is unsafe."""

_SCREEN_GATE_SYSTEM = """You are Lobe B, the independent screen-awareness gate in
Compuse. Return JSON only matching LobeDecision. Review A's exact proposed next
batch against the freshly observed screen and B's assessment. Approve only if
the screen is stable, the candidate's source_batch_id is exact, and its
preconditions are grounded in the observation. If approved, return the exact
candidate batch unchanged. Reject uncertainty or any mismatch. Include the
mandatory core_review described by the B profile instructions. If a batch is
returned, use the complete BatchSpec schema supplied in the user message and
use `kind` for every action discriminator."""


_BATCH_SCHEMA_RULES = """
Wire-format rules for every BatchSpec:
- The top-level object is complete: batch_id, actions, preconditions,
  predicted_end, confidence, risk, barrier_after, terminal, source_lobe.
- `actions` is a non-empty array. Each item is discriminated by `kind`.
- Use only fields from the supplied schema. For example, a click is
  {"kind":"click","x":123,"y":456}; a launch is
  {"kind":"application.launch","target_id":"..."}; a browse action is
  {"kind":"browse","url":"https://..."}.
- Never emit `action_type`, `button`, `clicks`, `modifiers`, or another
  framework's computer-use action format.
- `preconditions` and `predicted_end` must use the exact coordinate space and
  a checkable anchor from the observation. Initial A batches use
  source_batch_id=null; later batches name the exact source batch.
"""


_PROFILE_INSTRUCTIONS = {
    LobeBProfile.BASE: "Apply only the always-on context and anti-deception core in addition to the runtime handoff contract.",
    LobeBProfile.PREDICTIVE: "Emphasize preparing the next bounded batch from A's predicted endpoint while preserving the always-on core.",
    LobeBProfile.SCREEN_AWARE: "Emphasize screen-grounded reasoning and visible transitions while preserving the always-on core.",
    LobeBProfile.GATEKEEPER: "Treat proof as a hard gate: reject any approval when core_review has proof_required entries or a non-GREEN deception grade.",
    LobeBProfile.RECOVERY: "Emphasize failure diagnosis, safe recovery prerequisites, and what must be re-observed before continuing.",
}


_SPLIT_SYSTEM = """You are the task-split planner at the front door of Compuse.
Return JSON only matching ParallelSplitPlan, or {"done": true} when the task
cannot be safely split. Find one real breaking point where two pieces can run
independently and later meet at one merge action. Loop A owns branch_a and
Loop B owns branch_b. The two branches must use different coordinate spaces
and non-overlapping exclusive_resources. Do not split work that touches the
same window, file, browser profile, account, clipboard, or other shared state.
Each branch must contain bounded typed BatchSpec objects whose first batch has
source_batch_id=null and whose later batches chain from the prior batch. The
merge_batch must have preconditions.source_batch_id equal to split_id and may
run only after both branch final observations match their predicted_end
anchors. Include the mandatory core_review: broaden context, identify missing
prerequisites and failure modes, review claims for deception, and request the
full artifact as proof for any artifact claim. GREEN means no deception
detected, not guaranteed truth. If there is no safe independent split, refuse
instead of forcing parallelism."""


def _batch_prompt(
    task: str,
    observation: RuntimeObservation,
    active: BatchSpec | None = None,
    *,
    profile: LobeBProfile | None = None,
    output_schema: dict[str, Any] | None = None,
) -> str:
    payload: dict[str, Any] = {
        "task": task,
        "observation": observation.model_dump(mode="json", exclude={"screenshot_data_url"}),
    }
    if active is not None:
        payload["active_batch"] = active.model_dump(mode="json")
    if output_schema is not None:
        payload["output_schema"] = output_schema
    if profile is not None:
        payload["manual_b_profile"] = profile.value
        payload["profile_instruction"] = _PROFILE_INSTRUCTIONS[profile]
        payload["always_on_core"] = {
            "context_broadening": True,
            "anti_deception_review": True,
            "green_definition": "no deception detected; not guaranteed truth",
            "artifact_claim_policy": "request the full artifact every time, never only a manifest or summary",
        }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _screen_prompt(
    task: str,
    observation: RuntimeObservation,
    active: BatchSpec,
    *,
    candidate: BatchSpec | None = None,
    assessment: ScreenAssessment | None = None,
    profile: LobeBProfile | None = None,
    output_schema: dict[str, Any] | None = None,
) -> str:
    payload: dict[str, Any] = {
        "task": task,
        "observation": observation.model_dump(mode="json", exclude={"screenshot_data_url"}),
        "active_batch": active.model_dump(mode="json"),
    }
    if candidate is not None:
        payload["candidate_next_batch"] = candidate.model_dump(mode="json")
    if assessment is not None:
        payload["screen_assessment"] = assessment.model_dump(mode="json")
    if output_schema is not None:
        payload["output_schema"] = output_schema
    if profile is not None:
        payload["manual_b_profile"] = profile.value
        payload["profile_instruction"] = _PROFILE_INSTRUCTIONS[profile]
        payload["always_on_core"] = {
            "context_broadening": True,
            "anti_deception_review": True,
            "green_definition": "no deception detected; not guaranteed truth",
            "artifact_claim_policy": "request the full artifact every time, never only a manifest or summary",
        }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _split_prompt(
    task: str,
    observation_a: RuntimeObservation,
    observation_b: RuntimeObservation,
    *,
    output_schema: dict[str, Any] | None = None,
) -> str:
    payload: dict[str, Any] = {
        "task": task,
        "observation_a": observation_a.model_dump(mode="json", exclude={"screenshot_data_url"}),
        "observation_b": observation_b.model_dump(mode="json", exclude={"screenshot_data_url"}),
        "required_safety": {
            "distinct_coordinate_spaces": True,
            "non_overlapping_exclusive_resources": True,
            "verified_branch_endings_before_merge": True,
            "merge_is_serial_after_both_lanes": True,
        },
    }
    if output_schema is not None:
        payload["output_schema"] = output_schema
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _validate_batch_or_repair(
    client: OpenAICompatibleClient,
    raw: dict[str, Any],
    *,
    task: str,
    observation: RuntimeObservation,
    active: BatchSpec | None,
    source_lobe: str,
) -> BatchSpec | None:
    """Validate a batch and make one bounded schema-repair request if needed.

    Vision models sometimes return a valid JSON object using a different
    computer-use vocabulary (for example ``action_type`` instead of the
    protocol's discriminated ``kind`` field).  We do not silently coerce that
    object or invent missing safety metadata.  Instead, the model gets one
    repair attempt with the actual Pydantic schema and validation error.  If
    repair fails, the original strict validation error is allowed to surface.
    """
    candidate = dict(raw)
    candidate.pop("done", None)
    try:
        return BatchSpec.model_validate(candidate, strict=False)
    except ValidationError as first_error:
        repair_payload: dict[str, Any] = {
            "task": task,
            "observation": observation.model_dump(mode="json", exclude={"screenshot_data_url"}),
            "invalid_response": raw,
            "validation_error": str(first_error),
            "required_source_lobe": source_lobe,
            "output_schema": BatchSpec.model_json_schema(),
        }
        if active is not None:
            repair_payload["active_batch"] = active.model_dump(mode="json")
        repaired = client.complete_json(
            system=(
                "Repair the invalid response into one complete BatchSpec JSON "
                "object. Return JSON only. Preserve the task and observation; "
                "do not invent action success. Use `kind` for every action, "
                "never `action_type`. Do not omit preconditions, predicted_end, "
                "confidence, or any required field.\n"
                f"{_BATCH_SCHEMA_RULES}"
            ),
            user_text=json.dumps(repair_payload, ensure_ascii=False, separators=(",", ":")),
            observation=observation,
        )
        repaired.pop("done", None)
        return BatchSpec.model_validate(repaired, strict=False)


class ModelLobeA:
    def __init__(self, client: OpenAICompatibleClient) -> None:
        self.client = client

    def plan_initial(self, task: str, observation: RuntimeObservation) -> BatchSpec | None:
        raw = self.client.complete_json(
            system=f"{_A_SYSTEM}\n{_BATCH_SCHEMA_RULES}",
            user_text=_batch_prompt(
                task,
                observation,
                output_schema=BatchSpec.model_json_schema(),
            ),
            observation=observation,
        )
        if raw.get("done") is True:
            return None
        return _validate_batch_or_repair(
            self.client,
            raw,
            task=task,
            observation=observation,
            active=None,
            source_lobe="A",
        )

    def predict_next(self, task: str, active_batch: BatchSpec, observation: RuntimeObservation) -> BatchSpec | None:
        raw = self.client.complete_json(
            system=f"{_A_SYSTEM}\n{_BATCH_SCHEMA_RULES}",
            user_text=_batch_prompt(
                task,
                observation,
                active_batch,
                output_schema=BatchSpec.model_json_schema(),
            ),
            observation=observation,
        )
        if raw.get("done") is True:
            return None
        return _validate_batch_or_repair(
            self.client,
            raw,
            task=task,
            observation=observation,
            active=active_batch,
            source_lobe="A",
        )


class ModelSplitPlanner:
    """Model-backed front-door planner for the isolated-lane prototype."""

    def __init__(self, client: OpenAICompatibleClient) -> None:
        self.client = client

    def plan_split(
        self,
        task: str,
        observation_a: RuntimeObservation,
        observation_b: RuntimeObservation,
    ) -> ParallelSplitPlan | None:
        raw = self.client.complete_json(
            system=_SPLIT_SYSTEM,
            user_text=_split_prompt(
                task,
                observation_a,
                observation_b,
                output_schema=ParallelSplitPlan.model_json_schema(),
            ),
            observation=observation_a,
        )
        if raw.get("done") is True or raw.get("parallelizable") is False:
            return None
        raw.pop("done", None)
        raw.pop("parallelizable", None)
        return ParallelSplitPlan.model_validate(raw, strict=False)

class ModelLobeB:
    def __init__(
        self,
        client: OpenAICompatibleClient,
        *,
        profile: LobeBProfile | str = LobeBProfile.BASE,
    ) -> None:
        self.client = client
        self.profile = LobeBProfile(profile)
        self.last_core_review: BCoreReview | None = None

    def _decision_with_core(
        self,
        *,
        system: str,
        user_text: str,
        observation: RuntimeObservation,
    ) -> LobeDecision:
        raw = self.client.complete_json(system=system, user_text=user_text, observation=observation)
        try:
            decision = self._validate_decision(raw)
        except ValidationError as first_error:
            repair_payload = {
                "invalid_response": raw,
                "validation_error": str(first_error),
                "output_schema": LobeDecision.model_json_schema(),
                "instruction": "Return a complete LobeDecision. If approved is true, include a complete BatchSpec; otherwise use batch=null.",
            }
            repaired = self.client.complete_json(
                system=(
                    f"{system}\nRepair the invalid JSON response. Return only a complete "
                    "LobeDecision matching the supplied schema. Every nested action "
                    "must use `kind`, never `action_type`. Do not invent proof or "
                    "action success."
                ),
                user_text=json.dumps(repair_payload, ensure_ascii=False, separators=(",", ":")),
                observation=observation,
            )
            decision = self._validate_decision(repaired)
        return decision

    def _validate_decision(self, raw: dict[str, Any]) -> LobeDecision:
        raw = dict(raw)
        core_raw = raw.pop("core_review", None)
        decision = LobeDecision.model_validate(raw, strict=False)
        if core_raw is None:
            review = BCoreReview(
                profile=self.profile,
                deception_grade=DeceptionGrade.YELLOW,
                proof_required=("full evidence for any completion or artifact claim",),
                summary="B did not receive a structured core review; treat claims as unverified.",
            )
        else:
            review = BCoreReview.model_validate(core_raw, strict=False).model_copy(update={"profile": self.profile})
        self.last_core_review = review
        return decision.model_copy(update={"core_review": review})

    def prepare_next(self, task: str, active_batch: BatchSpec, observation: RuntimeObservation) -> LobeDecision:
        system = f"{_B_SYSTEM}\nManual profile: {self.profile.value}. {_PROFILE_INSTRUCTIONS[self.profile]}"
        return self._decision_with_core(
            system=system,
            user_text=_batch_prompt(
                task,
                observation,
                active_batch,
                profile=self.profile,
                output_schema=LobeDecision.model_json_schema(),
            ),
            observation=observation,
        )


class ModelScreenLobeB(ModelLobeB):
    """Vision-backed B for the continuous screen-awareness runtime."""

    def inspect_screen(
        self,
        task: str,
        active_batch: BatchSpec,
        observation: RuntimeObservation,
    ) -> ScreenAssessment:
        raw = self.client.complete_json(
            system=_SCREEN_SYSTEM,
            user_text=_screen_prompt(
                task,
                observation,
                active_batch,
                output_schema=ScreenAssessment.model_json_schema(),
            ),
            observation=observation,
        )
        return ScreenAssessment.model_validate(raw, strict=False)

    def approve_next(
        self,
        task: str,
        active_batch: BatchSpec,
        candidate: BatchSpec,
        observation: RuntimeObservation,
        assessment: ScreenAssessment,
    ) -> LobeDecision:
        return self._decision_with_core(
            system=(
                f"{_SCREEN_GATE_SYSTEM}\nManual profile: {self.profile.value}. "
                f"{_PROFILE_INSTRUCTIONS[self.profile]}"
            ),
            user_text=_screen_prompt(
                task,
                observation,
                active_batch,
                candidate=candidate,
                assessment=assessment,
                profile=self.profile,
                output_schema=LobeDecision.model_json_schema(),
            ),
            observation=observation,
        )


class DynamicModelLobeB(ModelScreenLobeB):
    """One manually profiled B implementation for both runtime architectures.

    The profile is selected by the operator before a run and remains fixed for
    that run. Context broadening and anti-deception review stay mandatory in
    every profile; the profile only selects B's additional emphasis.
    """

    pass


__all__ = [
    "ModelError",
    "ModelLobeA",
    "ModelSplitPlanner",
    "ModelLobeB",
    "ModelScreenLobeB",
    "DynamicModelLobeB",
    "OpenAICompatibleClient",
]
