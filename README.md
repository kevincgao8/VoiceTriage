# VoiceTriage 🎙️

AI-powered voice message classification system that automatically transcribes voicemails and categorizes them by urgency and type.

## Features

- **Voice Recording**: Twilio integration for incoming calls and voicemail recording
- **AI Transcription**: OpenAI Whisper for accurate speech-to-text conversion
- **Smart Classification**: Anthropic Claude for intelligent message categorization
- **Real-time Dashboard**: Live web interface showing all messages with auto-refresh
- **No Database Required**: In-memory storage for simplicity (easily replaceable)

## Architecture

```
User calls Twilio → Records voicemail → Webhook to backend → 
Download audio → OpenAI transcription → Anthropic classification → 
Store results → Frontend displays in real-time
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables

Copy `env.example` to `.env` and configure:

```bash
cp env.example .env
```

**Required variables:**
- `PUBLIC_BASE_URL`: Your public-facing URL (e.g., ngrok tunnel)
- `OPENAI_API_KEY`: OpenAI API key for transcription
- `ANTHROPIC_API_KEY`: Anthropic API key for classification

**Optional variables:**
- `TWILIO_ACCOUNT_SID`: Twilio account SID for signature validation
- `TWILIO_AUTH_TOKEN`: Twilio auth token for signature validation
- `USE_STUBS`: Set to `true` for testing without real API calls

### 3. Run the Application

```bash
python app.py
```

Or with uvicorn directly:

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

The app will be available at `http://localhost:8000`

## Twilio Setup

### 1. Get a Twilio Phone Number

1. Sign up at [twilio.com](https://twilio.com)
2. Get a phone number in the Twilio Console
3. Note your Account SID and Auth Token

### 2. Configure Webhook URLs

In your Twilio phone number settings:

- **Voice Configuration**: Set webhook URL to `{PUBLIC_BASE_URL}/twilio/voice`
- **HTTP Method**: POST

### 3. Make Your App Publicly Accessible

For local development, use ngrok:

```bash
# Install ngrok
brew install ngrok  # macOS
# or download from https://ngrok.com

# Create tunnel
ngrok http 8000

# Copy the HTTPS URL to your .env file
PUBLIC_BASE_URL=https://xxxxx.ngrok.io
```

## API Endpoints

### Health Check
- `GET /api/health` - Returns `{"ok": true}`

### Twilio Webhooks
- `POST /twilio/voice` - Handles incoming calls, returns TwiML
- `POST /twilio/recording` - Processes recording status callbacks

### Messages
- `GET /api/messages` - Returns all processed messages (newest first)

### Static Files
- `/` - Serves the main dashboard
- `/static/*` - Static assets (CSS, JS)

## Frontend Features

- **Real-time Updates**: Auto-refreshes every 10 seconds
- **Responsive Design**: Works on desktop and mobile
- **Message Table**: Shows timestamp, caller, transcript, category, urgency, and audio links
- **Smart Badges**: Color-coded categories and urgency levels
- **Audio Playback**: Direct links to original recordings

## Message Classification

The system automatically categorizes messages into:

**Categories:**
- `billing` - Payment, subscription, or billing issues
- `bug` - Technical problems or errors
- `feature` - Feature requests or enhancements
- `other` - General inquiries or uncategorized

**Urgency Levels:**
- `low` - Non-critical, can wait
- `medium` - Important but not urgent
- `high` - Critical, needs immediate attention

## Development & Testing

### Test Mode

Set `USE_STUBS=true` in your `.env` file to:
- Skip real API calls
- Use mock transcript and classification data
- Test the full flow without API costs

### Local Testing

1. Start the app with `USE_STUBS=true`
2. Use a tool like Postman to POST to `/twilio/voice`
3. Check the dashboard for test messages

### Production Considerations

**TODO items for production deployment:**
- Replace in-memory storage with database (PostgreSQL, MongoDB)
- Add authentication and authorization
- Implement proper error handling and retries
- Add request rate limiting
- Set up monitoring and logging
- Add Twilio signature validation
- Implement message queuing for high volume
- Add audio file storage (S3, etc.)

## Troubleshooting

### Common Issues

1. **"PUBLIC_BASE_URL environment variable is required"**
   - Make sure you have a `.env` file with the correct URL
   - Ensure ngrok is running and the URL is accessible

2. **"OpenAI API key not configured"**
   - Check your `.env` file has the correct `OPENAI_API_KEY`
   - Verify the API key is valid and has credits

3. **"Anthropic API key not configured"**
   - Check your `.env` file has the correct `ANTHROPIC_API_KEY`
   - Verify the API key is valid and has credits

4. **Twilio webhook not working**
   - Ensure your ngrok tunnel is active
   - Check the webhook URL in Twilio console
   - Verify the endpoint returns valid TwiML

### Logs

Check the console output for detailed error messages and request logs.

## License

MIT License - feel free to use this for your own projects!
