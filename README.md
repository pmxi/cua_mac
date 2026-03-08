# `cua_mac`

Minimal computer use implementation for macOS (local!) using the latest GPT-5.4 native computer use support. To my knowledge, no other such implementation yet exists.

Here's an example command:

```bash
uv run python -m cua_mac run "Open Firefox and navigate to Hacker News"
```

Demo:



https://github.com/user-attachments/assets/3b12f7b5-6b43-4a9a-8fd0-2984e07f6d50



The following is an AI-generated README:


## Requirements

- macOS
- `uv`
- Python `3.14` available through `uv`
- An OpenAI API key
- Screen Recording permission for the app launching `uv`
- Accessibility permission for the app launching `uv`

## Setup

Install dependencies:

```bash
uv sync
```

Create a `.env` file in the repo root:

```bash
OPENAI_API_KEY=your_api_key_here
```

Grant permissions in macOS:

1. Grant `Screen Recording` to the terminal app you use to launch `uv`.
2. Grant `Accessibility` to that same app.

If you run through `Ghostty`, grant permissions to `Ghostty`.
If you run through `Terminal`, grant permissions to `Terminal`.

## Basic Usage

Capture a manual screenshot:

```bash
uv run python -m cua_mac screenshot
```

Run a task:

```bash
uv run python -m cua_mac run "Open Calculator and compute 17 * 24"
```

The runner prints progress lines like:

```text
Responses turn 1: resp_...
Turn 1.1 actions: click :: [{"button":"left","type":"click","x":1854,"y":2118}]
```

When the model finishes, it prints the final assistant message.

## Common Examples

Open Calculator and do a simple computation:

```bash
uv run python -m cua_mac run "Open Calculator and compute 17 * 24"
```

Open Notes and create a short note:

```bash
uv run python -m cua_mac run "Open Notes and create a note titled test with the body hello from cua_mac"
```

Open Firefox and go to a page:

```bash
uv run python -m cua_mac run "Open Firefox and navigate to https://news.ycombinator.com"
```

Draft an email:

```bash
uv run python -m cua_mac run "Open Mail and draft an email to example@example.com with subject test and body hello"
```

## Useful Flags

Choose a model:

```bash
uv run python -m cua_mac run \
  --model gpt-5.4 \
  "Open Calculator and compute 17 * 24"
```

Slow down local UI actions:

```bash
uv run python -m cua_mac run \
  --action-delay-ms 250 \
  "Open Notes and create a note titled slower run"
```

Set an explicit turn limit:

```bash
uv run python -m cua_mac run \
  --max-turns 50 \
  "Open Firefox and search for OpenAI"
```

By default there is no implicit turn cap. If you omit `--max-turns`, the loop runs until the model returns a final response or an error occurs.

Write artifacts to a specific directory:

```bash
uv run python -m cua_mac \
  --artifact-dir artifacts/manual-test \
  run "Open Calculator and compute 17 * 24"
```

## Artifacts

Each run writes screenshots under:

```text
artifacts/<timestamp>/
```

Typical files:

- `turn-000-initial.png`
- `turn-001-call-01.png`
- `turn-002-call-01.png`

These are the exact screenshots the model is acting on after each loop step.

## How The Loop Works

1. Capture the current desktop.
2. Send the prompt plus screenshot to the Responses API with `tools=[{"type": "computer"}]`.
3. Receive a `computer_call` with `actions[]`.
4. Execute those actions locally on macOS.
5. Capture a new screenshot.
6. Send it back as `computer_call_output`.
7. Repeat until the model returns a final message.

## Current Scope

This is still an MVP. Current behavior and limits:

- Supports exactly one connected display
- Uses screenshot-pixel coordinates for mouse actions
- Supports `click`, `double_click`, `move`, `drag`, `scroll`, `type`, `keypress`, `wait`, and `screenshot`
- Uses real key events for normal typing
- Falls back to Unicode event injection only for unsupported characters
- Prints action logs to stdout
- Stores screenshots locally for inspection

## Troubleshooting

### Screenshot capture fails

If you see a screenshot error, confirm `Screen Recording` is granted to the terminal app launching `uv`.

### Accessibility preflight fails

If the runner says Accessibility is not granted, enable `Accessibility` for the terminal app launching `uv`, then fully relaunch that app.

### macOS makes the "beep" sound while typing

That usually means the intended field is not actually focused.

Try:

- making the prompt tell the model to click the input field before typing
- increasing `--action-delay-ms`
- checking the latest artifact screenshots to confirm focus

### Clicks land in the wrong place

Inspect the logged action payloads and the saved screenshots together.
The runner now interprets click coordinates in screenshot-pixel space, which should match the model's view of the screen.

## Help

Top-level CLI help:

```bash
uv run python -m cua_mac --help
```

`run` command help:

```bash
uv run python -m cua_mac run --help
```
