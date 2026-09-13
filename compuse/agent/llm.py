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

from .contracts import BatchSpec, LobeDecision, RuntimeObservation, ScreenAssessment


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
Return JSON only, matching the BatchSpec schema. Plan at most 8 typed actions.
You see the current desktop observation and must keep a short, executable
batch; stop before a modal, navigation, submit, login, payment, or other state
transition whose result cannot be predicted. The predicted_end must describe
where the desktop will be after every action and include at least one checkable
anchor: an exact foreground_window, exact browser_url, or required_markers.
source_lobe must be \"A\". Do not invent that an action succeeded; the runtime
will observe the real desktop after dispatch."""

_B_SYSTEM = """You are Lobe B, Compuse's live shadow lobe and handoff gate.
Return JSON only. You receive Lobe A's exact current action batch and its
predicted end state. Independently prepare the next bounded typed-action batch
starting from that predicted end. The next batch's preconditions.source_batch_id
must equal the active batch_id, and its preconditions must preserve the
predicted end's checkable anchors. Reject the handoff if the predicted state is
not concrete, the next action is not grounded, or the sequence crosses an
uncertain transition. Use approved=false and batch=null when rejecting.
source_lobe must be \"B\". B is allowed to challenge A; never approve a guess."""

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
candidate batch unchanged. Reject uncertainty or any mismatch."""


def _batch_prompt(task: str, observation: RuntimeObservation, active: BatchSpec | None = None) -> str:
    payload: dict[str, Any] = {
        "task": task,
        "observation": observation.model_dump(mode="json", exclude={"screenshot_data_url"}),
    }
    if active is not None:
        payload["active_batch"] = active.model_dump(mode="json")
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _screen_prompt(
    task: str,
    observation: RuntimeObservation,
    active: BatchSpec,
    *,
    candidate: BatchSpec | None = None,
    assessment: ScreenAssessment | None = None,
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
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


class ModelLobeA:
    def __init__(self, client: OpenAICompatibleClient) -> None:
        self.client = client

    def plan_initial(self, task: str, observation: RuntimeObservation) -> BatchSpec | None:
        raw = self.client.complete_json(system=_A_SYSTEM, user_text=_batch_prompt(task, observation), observation=observation)
        if raw.get("done") is True:
            return None
        raw.pop("done", None)
        # JSON has arrays where the strict internal contract uses tuples.  The
        # action fields and bounds are still validated by Pydantic; this only
        # adapts the wire representation.
        return BatchSpec.model_validate(raw, strict=False)

    def predict_next(self, task: str, active_batch: BatchSpec, observation: RuntimeObservation) -> BatchSpec | None:
        raw = self.client.complete_json(system=_A_SYSTEM, user_text=_batch_prompt(task, observation, active_batch), observation=observation)
        if raw.get("done") is True:
            return None
        raw.pop("done", None)
        return BatchSpec.model_validate(raw, strict=False)


class ModelLobeB:
    def __init__(self, client: OpenAICompatibleClient) -> None:
        self.client = client

    def prepare_next(self, task: str, active_batch: BatchSpec, observation: RuntimeObservation) -> LobeDecision:
        raw = self.client.complete_json(system=_B_SYSTEM, user_text=_batch_prompt(task, observation, active_batch), observation=observation)
        return LobeDecision.model_validate(raw, strict=False)


class ModelScreenLobeB:
    """Vision-backed B for the continuous screen-awareness runtime."""

    def __init__(self, client: OpenAICompatibleClient) -> None:
        self.client = client

    def inspect_screen(
        self,
        task: str,
        active_batch: BatchSpec,
        observation: RuntimeObservation,
    ) -> ScreenAssessment:
        raw = self.client.complete_json(
            system=_SCREEN_SYSTEM,
            user_text=_screen_prompt(task, observation, active_batch),
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
        raw = self.client.complete_json(
            system=_SCREEN_GATE_SYSTEM,
            user_text=_screen_prompt(
                task,
                observation,
                active_batch,
                candidate=candidate,
                assessment=assessment,
            ),
            observation=observation,
        )
        return LobeDecision.model_validate(raw, strict=False)


__all__ = [
    "ModelError",
    "ModelLobeA",
    "ModelLobeB",
    "ModelScreenLobeB",
    "OpenAICompatibleClient",
]
