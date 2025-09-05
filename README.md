# Schema-Strict Extractor
Paste a messy message → get strict JSON with fields:
`{customer, email, category[billing|bug|feature|other], urgency[low|medium|high], summary}`

## Run
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in PROVIDER + API key (optional; app still runs with stubs)
uvicorn app:app --reload --port ${PORT:-8000}
# open http://127.0.0.1:8000
```

## API
- `POST /api/extract { "text": "..." }` → `{ data, valid, errors[], latency_ms, est_cost_usd }`
- `GET /api/stats` → `{ runs, valids, success_rate_pct, avg_latency_ms }`

### API keys you might need:
- **OpenAI**: `OPENAI_API_KEY` (if `PROVIDER=OPENAI`)
- **Anthropic**: `ANTHROPIC_API_KEY` (if `PROVIDER=ANTHROPIC`)
