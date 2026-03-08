from __future__ import annotations

import unittest
from pathlib import Path

from cua_mac.mac import MacComputerBackend
from cua_mac.loop import run_computer_loop
from cua_mac.models import DisplayGeometry, Screenshot


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

    def test_loop_accepts_uncapped_mode(self):
        backend = FakeBackend()
        client = FakeClient(
            [
                {
                    "id": "resp_1",
                    "output": [
                        {
                            "actions": [{"type": "screenshot"}],
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
                                    "text": "Done without an explicit cap.",
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
            max_turns=None,
        )

        self.assertEqual(result.final_message, "Done without an explicit cap.")
        self.assertEqual(result.turns, 2)


class MacComputerBackendTests(unittest.TestCase):
    def test_to_event_point_uses_screenshot_scale_and_clamps(self):
        backend = MacComputerBackend.__new__(MacComputerBackend)
        backend.geometry = DisplayGeometry(
            width_points=1512.0,
            height_points=982.0,
            width_px=3024,
            height_px=1964,
            scale_factor=2.0,
        )

        self.assertEqual(backend._to_event_point(1854, 2118), (927.0, 981.5))

    def test_keypress_accepts_sequence_of_plain_keys(self):
        backend = MacComputerBackend.__new__(MacComputerBackend)
        pressed = []
        backend._press_key_chord = lambda primary_key, modifiers: pressed.append(
            (primary_key, list(modifiers))
        )
        backend._sleep_after_action = lambda: None

        backend.keypress(["1", "7", "*", "2", "4", "="])

        self.assertEqual(
            pressed,
            [
                ("1", []),
                ("7", []),
                ("*", []),
                ("2", []),
                ("4", []),
                ("=", []),
            ],
        )

    def test_keypress_keeps_modifier_chords(self):
        backend = MacComputerBackend.__new__(MacComputerBackend)
        pressed = []
        backend._press_key_chord = lambda primary_key, modifiers: pressed.append(
            (primary_key, list(modifiers))
        )
        backend._sleep_after_action = lambda: None

        backend.keypress(["command", "a"])

        self.assertEqual(pressed, [("a", ["command"])])

    def test_type_text_uses_keycodes_for_supported_characters(self):
        backend = MacComputerBackend.__new__(MacComputerBackend)
        pressed = []
        backend._press_key_chord = lambda primary_key, modifiers: pressed.append(
            (primary_key, list(modifiers))
        )
        backend._type_unicode_character = lambda character: self.fail(
            f"Unexpected unicode fallback for {character!r}"
        )
        backend._sleep_after_action = lambda: None

        backend.type_text("Ab*\n\t")

        self.assertEqual(
            pressed,
            [
                ("A", []),
                ("b", []),
                ("*", []),
                ("enter", []),
                ("tab", []),
            ],
        )

    def test_type_text_falls_back_to_unicode_for_unsupported_characters(self):
        backend = MacComputerBackend.__new__(MacComputerBackend)
        pressed = []
        unicode_chars = []
        backend._press_key_chord = lambda primary_key, modifiers: pressed.append(
            (primary_key, list(modifiers))
        )
        backend._type_unicode_character = lambda character: unicode_chars.append(character)
        backend._sleep_after_action = lambda: None

        backend.type_text("a🙂")

        self.assertEqual(pressed, [("a", [])])
        self.assertEqual(unicode_chars, ["🙂"])


if __name__ == "__main__":
    unittest.main()
