# VoiceTriage
Call a Twilio number → leave voicemail → OpenAI transcribes → Anthropic classifies
(category, urgency). Simple JS frontend shows past messages.

## Quick start
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in keys + PUBLIC_BASE_URL
uvicorn app:app --reload --port ${PORT:-8000}
