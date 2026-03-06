from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


LogFn = Callable[[str], None]
DEFAULT_INSTRUCTIONS = (
    "You are operating a local macOS desktop. "
    "Use the computer tool for UI interactions and stop when the task is complete."
)


@dataclass(frozen=True)
class LoopResult:
    final_message: str
    response_id: str
    turns: int


def run_computer_loop(
    *,
    backend: Any,
    client: Any,
    instructions: str = DEFAULT_INSTRUCTIONS,
    model: str,
    prompt: str,
    max_turns: int,
    log: LogFn | None = None,
) -> LoopResult:
    logger = log or (lambda message: None)
    previous_response_id: str | None = None
    initial_screenshot = backend.capture_screenshot("turn-000-initial")
    next_input: Any = [
        {
            "content": [
                {"text": prompt, "type": "input_text"},
                {
                    "detail": "original",
                    "image_url": initial_screenshot.image_url,
                    "type": "input_image",
                },
            ],
            "role": "user",
        }
    ]

    for turn in range(1, max_turns + 1):
        request = {
            "input": next_input,
            "instructions": instructions,
            "model": model,
            "parallel_tool_calls": False,
            "reasoning": {"effort": "low"},
            "tools": [{"type": "computer"}],
        }
        if previous_response_id is not None:
            request["previous_response_id"] = previous_response_id

        response = client.responses.create(**request)
        payload = dump_response(response)
        ensure_response_succeeded(payload)
        response_id = payload["id"]
        previous_response_id = response_id
        logger(f"Responses turn {turn}: {response_id}")

        computer_calls = [
            item for item in payload.get("output", []) if item.get("type") == "computer_call"
        ]
        if not computer_calls:
            final_message = extract_final_message(payload)
            if not final_message:
                raise RuntimeError(
                    f"Turn {turn} returned no computer call and no assistant message."
                )
            return LoopResult(
                final_message=final_message,
                response_id=response_id,
                turns=turn,
            )

        tool_outputs = []
        for index, computer_call in enumerate(computer_calls, start=1):
            if computer_call.get("pending_safety_checks"):
                raise RuntimeError("Pending safety checks are not implemented in this MVP.")

            actions = computer_call.get("actions", [])
            logger(
                f"Turn {turn}.{index} actions: "
                f"{' -> '.join(action.get('type', '?') for action in actions) or 'none'}"
            )
            call_id = computer_call.get("call_id")
            if not call_id:
                raise RuntimeError("Computer call did not include a call_id.")
            for action in actions:
                backend.execute_action(action)

            screenshot = backend.capture_screenshot(f"turn-{turn:03d}-call-{index:02d}")
            tool_outputs.append(
                {
                    "call_id": call_id,
                    "output": {
                        "detail": "original",
                        "image_url": screenshot.image_url,
                        "type": "computer_screenshot",
                    },
                    "type": "computer_call_output",
                }
            )

        next_input = tool_outputs

    raise RuntimeError(
        f"Loop exhausted the configured {max_turns} turns without a final assistant message."
    )


def dump_response(response: Any) -> dict[str, Any]:
    if isinstance(response, dict):
        return response
    if hasattr(response, "model_dump"):
        return response.model_dump(mode="json")
    raise TypeError(f"Unsupported response type: {type(response)!r}")


def ensure_response_succeeded(payload: dict[str, Any]) -> None:
    error = payload.get("error")
    if isinstance(error, dict) and error.get("message"):
        raise RuntimeError(str(error["message"]))
    if payload.get("status") == "failed":
        raise RuntimeError("Responses API request failed.")


def extract_final_message(payload: dict[str, Any]) -> str:
    parts: list[str] = []
    for item in payload.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") != "output_text":
                continue
            text = str(content.get("text", "")).strip()
            if text:
                parts.append(text)
    return "\n\n".join(parts)
