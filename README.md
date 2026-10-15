# Doubao Chat API

A local FastAPI service that drives [Doubao](https://www.doubao.com/chat/) (豆包) through a real
browser, so you can call it like a normal chat-completions endpoint — including from tools that
already speak the OpenAI protocol.

No reverse-engineered private API keys: it automates the actual web UI with Playwright, which is
why it keeps working when Doubao's internal endpoints change.

## Why

Most "use Doubao from code" approaches depend on undocumented internal HTTP endpoints. They break
silently. This one drives the same page you use, so the contract is the UI, not a private API.

## Features

- `POST /chat` — send a message, get the reply
- `POST /v1/chat/completions` — **OpenAI-compatible** shape, so existing OpenAI SDK clients work
  by just pointing `base_url` here
- `GET /history` / `POST /clear` — conversation history control
- `GET /health` and `GET /health/simple` — readiness probes (the full one reports browser state)
- Structured logging via `loguru` with per-request ID tracing
- Middleware for request timing, error shaping and CORS
- Graceful shutdown + an optional background health-check loop

## Requirements

- Python 3.10+
- A machine that can run Playwright's Chromium (headless by default)

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

cp .env.example .env      # adjust if you like
python main.py
```

Then:

```bash
curl -s http://127.0.0.1:8000/health/simple

curl -s -X POST http://127.0.0.1:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"message": "用一句话解释什么是所有权"}'
```

Point an OpenAI client at it:

```python
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8000/v1", api_key="not-needed")
print(client.chat.completions.create(
    model="doubao",
    messages=[{"role": "user", "content": "你好"}],
).choices[0].message.content)
```

## Configuration

All settings come from environment variables (see `.env.example`); `config.py` groups them and
validates at startup. Highlights:

| Variable | Default | Notes |
|---|---|---|
| `HOST` / `PORT` | `127.0.0.1` / `8000` | Bind address |
| `HEADLESS` | `true` | Set `false` to watch the browser work — the fastest way to debug |
| `BROWSER_TYPE` | `chromium` | `chromium` / `firefox` / `webkit` |
| `DOUBAO_URL` | `https://www.doubao.com/chat/` | Entry point |
| `TIMEOUT` | — | Playwright navigation/response timeout |
| `LOG_LEVEL` | — | `loguru` level |

## Tests

The `test_*.py` files are independent, runnable scripts (they print their own pass/fail summary):

```bash
python test_configuration.py      # config loading and validation
python test_selectors.py          # DOM selectors still resolve
python test_api_functionality.py  # endpoint behaviour (server must be running)
python test_error_handling.py     # malformed input, upstream failures
python test_performance.py        # latency and resource use
python test_installation.py       # environment / dependency sanity
python test_playwright_automation.py
```

`screenshots/` holds a captured Doubao homepage used while identifying selectors.

## Notes and limitations

- One shared browser session, guarded by an `asyncio.Lock` — requests serialize rather than
  running truly concurrently. That is deliberate: a single logged-in page cannot safely serve
  parallel prompts.
- Because it drives a UI, a Doubao redesign can break selectors. `test_selectors.py` exists
  precisely to catch that early; start there when something stops working.
- `.env` is git-ignored and should stay that way.

## License

MIT — see [LICENSE](LICENSE).
