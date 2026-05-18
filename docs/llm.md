# LLM Verifier (`/discuss`)

A calm, opt-in sparring partner powered by a **local** LLM via Ollama.

The verifier never overrides your ratings. It asks one question or
names one tension, then says "Your call."

## Setup

### 1. Install Ollama and the model

```bash
brew install ollama
ollama pull gemma4:e4b
ollama serve   # if not already running
```

### 2. Install the `[llm]` extra

```bash
pip install -e ".[llm]"
```

### 3. Enable it

```bash
export TASK_PRIORITIZER_LLM_ENABLED=1
```

That env var is the master switch. Without it, `/discuss` returns a
calm "LLM disabled" message and no network call is made.

## Usage

```text
> {p1:30} write quarterly report
[normal scoring output…]

> /discuss
Asking the model… (Ctrl-C to cancel)
── gemma4:e4b ──
Your Confidence is high but Risk is also high. Worth a 5-minute
plan-of-attack before you start? Your call.
──────────────────────────────────────────
```

## Configuration

| Env var | Default | Purpose |
|---------|---------|---------|
| `TASK_PRIORITIZER_LLM_ENABLED` | unset | Master switch. Must be `1`. |
| `TASK_PRIORITIZER_LLM_MODEL` | `gemma4:e4b` | Ollama model name. |
| `TASK_PRIORITIZER_LLM_TIMEOUT` | `30.0` | HTTP timeout (seconds). |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama endpoint. |

## Failure Modes (all calm)

- Ollama not running → `LLM unavailable. Check Ollama is running on localhost:11434.`
- Model not pulled → Ollama returns an error JSON; surfaced as `LLM unreachable: <message>`.
- Timeout → same path as above.
- No prior `/discuss` target → `Score a task first, then /discuss it.`

## Prompt Design

The system prompt is intentionally short and constraining:

- ≤120 words.
- No emojis, no exclamation marks.
- Name one tension OR affirm coherence.
- End with: `Your call.`

See `task_prioritizer/llm/verifier.py:SYSTEM_PROMPT`.

## Tests

- 9 mocked tests (transport-level via `httpx.MockTransport`).
- 1 live test, gated by `TASK_PRIORITIZER_LLM_LIVE=1`:

```bash
TASK_PRIORITIZER_LLM_LIVE=1 pytest tests/test_llm_verifier.py::test_live_ollama_generates_short_response -v
```
