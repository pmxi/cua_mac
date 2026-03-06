Minimal local macOS computer-use runner using the OpenAI Responses API `computer` tool.

Current MVP:

- captures the live desktop as the initial model input
- executes batched `computer_call.actions[]` locally on macOS
- captures a fresh screenshot after each action batch
- returns that image as `computer_call_output`

Constraints:

- use `uv` only
- supports exactly one connected display
- requires macOS Screen Recording and Accessibility access for the Python process used by `uv`

Setup:

```bash
uv sync
```

Capture a manual screenshot:

```bash
uv run python -m cua_mac screenshot
```

Run the loop:

```bash
uv run python -m cua_mac run "Open Notes and create a note titled test"
```

Optional flags:

```bash
uv run python -m cua_mac run \
  --model gpt-5.4 \
  --max-turns 200 \
  --action-delay-ms 120 \
  "Open Calculator and compute 17 * 24"
```

Artifacts are written under `artifacts/<timestamp>/`.
