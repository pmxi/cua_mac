from __future__ import annotations

import unittest
from pathlib import Path

from cua_mac.loop import run_computer_loop
from cua_mac.models import Screenshot


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def model_dump(self, mode: str = "json"):
        return self.payload


class FakeResponsesAPI:
    def __init__(self, payloads):
        self.payloads = payloads
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        return FakeResponse(self.payloads[len(self.requests) - 1])


class FakeClient:
    def __init__(self, payloads):
        self.responses = FakeResponsesAPI(payloads)


class FakeBackend:
    def __init__(self):
        self.actions = []
        self.labels = []

    def capture_screenshot(self, label: str):
        self.labels.append(label)
        return Screenshot(
            path=Path(f"/tmp/{label}.png"),
            image_url=f"data:image/png;base64,{label}",
            width_px=1440,
            height_px=900,
            scale_factor=1.0,
        )

    def execute_action(self, action):
        self.actions.append(action)


class RunComputerLoopTests(unittest.TestCase):
    def test_loop_returns_computer_call_output_and_final_message(self):
        backend = FakeBackend()
        client = FakeClient(
            [
                {
                    "id": "resp_1",
                    "output": [
                        {
                            "actions": [{"type": "click", "x": 10, "y": 12}],
                            "call_id": "call_1",
                            "type": "computer_call",
                        }
                    ],
                },
                {
                    "id": "resp_2",
                    "output": [
                        {
                            "content": [
                                {
                                    "text": "Task completed locally.",
                                    "type": "output_text",
                                }
                            ],
                            "role": "assistant",
                            "type": "message",
                        }
                    ],
                },
            ]
        )

        result = run_computer_loop(
            backend=backend,
            client=client,
            model="gpt-5.4",
            prompt="Do the thing",
            max_turns=4,
        )

        self.assertEqual(result.final_message, "Task completed locally.")
        self.assertEqual(result.response_id, "resp_2")
        self.assertEqual(result.turns, 2)
        self.assertEqual(backend.actions, [{"type": "click", "x": 10, "y": 12}])
        self.assertEqual(backend.labels, ["turn-000-initial", "turn-001-call-01"])
        self.assertEqual(client.responses.requests[1]["previous_response_id"], "resp_1")
        self.assertEqual(
            client.responses.requests[1]["input"],
            [
                {
                    "call_id": "call_1",
                    "output": {
                        "detail": "original",
                        "image_url": "data:image/png;base64,turn-001-call-01",
                        "type": "computer_screenshot",
                    },
                    "type": "computer_call_output",
                }
            ],
        )

    def test_loop_rejects_pending_safety_checks(self):
        backend = FakeBackend()
        client = FakeClient(
            [
                {
                    "id": "resp_1",
                    "output": [
                        {
                            "actions": [{"type": "screenshot"}],
                            "call_id": "call_1",
                            "pending_safety_checks": [{"code": "requires_ack"}],
                            "type": "computer_call",
                        }
                    ],
                }
            ]
        )

        with self.assertRaisesRegex(
            RuntimeError, "Pending safety checks are not implemented"
        ):
            run_computer_loop(
                backend=backend,
                client=client,
                model="gpt-5.4",
                prompt="Do the thing",
                max_turns=1,
            )


if __name__ == "__main__":
    unittest.main()
