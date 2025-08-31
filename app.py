import os
import asyncio
import logging
from datetime import datetime
from typing import List, Optional
import json
import re

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response, FileResponse
from pydantic import BaseModel
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="VoiceTriage", version="1.0.0")

# In-memory storage (TODO: replace with database in production)
messages = []
message_id_counter = 1

# Store call information for recording processing
call_info = {}  # CallSid -> {from_number, timestamp}

# Environment variables
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
USE_STUBS = os.getenv("USE_STUBS", "false").lower() == "true"

# Validation
if not PUBLIC_BASE_URL:
    raise ValueError("PUBLIC_BASE_URL environment variable is required")

# Pydantic models
class Message(BaseModel):
    id: int
    from_number: str
    created_at: datetime
    recording_url: str
    transcript: str
    category: str
    urgency: str
    rationale: str

class TwilioVoiceRequest(BaseModel):
    From: str
    CallSid: str

class TwilioRecordingRequest(BaseModel):
    RecordingUrl: str
    From: str
    CallSid: str
    RecordingDuration: Optional[str] = None

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"ok": True}

@app.post("/twilio/voice")
async def twilio_voice(request: Request):
    """Handle incoming voice calls and return TwiML"""
    try:
        # Parse form data from Twilio
        form_data = await request.form()
        from_number = form_data.get("From", "Unknown")
        call_sid = form_data.get("CallSid", "Unknown")
        
        logger.info(f"Incoming call from {from_number}, CallSid: {call_sid}")
        
        # Store call information for later use in recording processing
        call_info[call_sid] = {
            "from_number": from_number,
            "timestamp": datetime.utcnow()
        }
        logger.info(f"Stored call info for {call_sid}: {from_number}")
        
        # Generate TwiML response
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">Hello! Please leave your message after the beep.</Say>
    <Record maxLength="120" playBeep="true" 
           recordingStatusCallback="{PUBLIC_BASE_URL}/twilio/recording" />
</Response>"""
        
        return Response(content=twiml, media_type="text/xml")
    
    except Exception as e:
        logger.error(f"Error in voice endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/twilio/recording")
async def twilio_recording(request: Request, background_tasks: BackgroundTasks):
    """Handle recording status callback from Twilio"""
    try:
        # Parse form data from Twilio
        form_data = await request.form()
        
        # Log all received data for debugging
        logger.info(f"Received recording webhook data: {dict(form_data)}")
        
        # Get required fields with better error handling
        recording_url = form_data.get("RecordingUrl")
        call_sid = form_data.get("CallSid")
        
        # Log what we found
        logger.info(f"Extracted - URL: {recording_url}, CallSid: {call_sid}")
        
        if not recording_url:
            logger.error(f"Missing RecordingUrl in form data: {dict(form_data)}")
            return Response(status_code=400, content="Missing RecordingUrl")
        
        if not call_sid:
            logger.error(f"Missing CallSid in form data: {dict(form_data)}")
            return Response(status_code=400, content="Missing CallSid")
        
        # Get caller information from stored call data
        if call_sid not in call_info:
            logger.error(f"No call info found for CallSid: {call_sid}")
            return Response(status_code=400, content="Call info not found")
        
        from_number = call_info[call_sid]["from_number"]
        logger.info(f"Retrieved caller info: {from_number} for CallSid: {call_sid}")
        
        logger.info(f"Recording received from {from_number}, CallSid: {call_sid}, URL: {recording_url}")
        
        # Add background task to process the recording
        background_tasks.add_task(
            process_recording, recording_url, from_number, call_sid
        )
        
        # Clean up call info after a delay (to allow processing to complete)
        background_tasks.add_task(
            cleanup_call_info, call_sid, delay_seconds=300  # 5 minutes
        )
        
        # Return quickly to Twilio
        return Response(status_code=200, content="OK")
    
    except Exception as e:
        logger.error(f"Error in recording endpoint: {e}")
        return Response(status_code=500, content="Internal server error")

async def cleanup_call_info(call_sid: str, delay_seconds: int = 300):
    """Clean up call information after processing is complete"""
    await asyncio.sleep(delay_seconds)
    if call_sid in call_info:
        del call_info[call_sid]
        logger.info(f"Cleaned up call info for {call_sid}")

async def process_recording(recording_url: str, from_number: str, call_sid: str):
    """Process the recording in the background"""
    global message_id_counter
    
    try:
        if USE_STUBS:
            # Use stub data for testing
            transcript = "This is a test voicemail message for demonstration purposes."
            category = "other"
            urgency = "medium"
            rationale = "Test message for development purposes."
        else:
            # Download audio and process with real APIs
            transcript, category, urgency, rationale = await process_with_apis(recording_url)
        
        # Create message record
        message = Message(
            id=message_id_counter,
            from_number=from_number,
            created_at=datetime.utcnow(),
            recording_url=recording_url,
            transcript=transcript,
            category=category,
            urgency=urgency,
            rationale=rationale
        )
        
        # Store in memory (TODO: replace with database)
        messages.append(message)
        message_id_counter += 1
        
        logger.info(f"Processed recording: {message.id} from {from_number}")
        
    except Exception as e:
        logger.error(f"Error processing recording: {e}")

async def process_with_apis(recording_url: str):
    """Process recording with OpenAI and Anthropic APIs"""
    try:
        # Download audio from Twilio with authentication
        audio_url = f"{recording_url}.mp3"
        logger.info(f"Downloading audio from: {audio_url}")
        
        # Use Twilio credentials for authentication
        if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
            auth = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            logger.info("Using Twilio authentication for audio download")
        else:
            auth = None
            logger.warning("No Twilio credentials found, attempting download without auth")
        
        response = requests.get(audio_url, auth=auth, timeout=30)
        response.raise_for_status()
        
        logger.info(f"Successfully downloaded audio, size: {len(response.content)} bytes")
        
        # Transcribe with OpenAI
        logger.info("Starting OpenAI transcription...")
        transcript = await transcribe_with_openai(response.content)
        logger.info(f"OpenAI transcription completed: {transcript[:100]}...")
        
        # Classify with Anthropic
        logger.info("Starting Anthropic classification...")
        category, urgency, rationale = await classify_with_anthropic(transcript)
        logger.info(f"Anthropic classification completed: {category}, {urgency}")
        
        return transcript, category, urgency, rationale
        
    except Exception as e:
        logger.error(f"API processing error: {e}")
        # Fallback to stub data
        return "Error processing message", "other", "medium", "Processing failed"

async def transcribe_with_openai(audio_content: bytes):
    """Transcribe audio using OpenAI Whisper"""
    if not OPENAI_API_KEY:
        raise ValueError("OpenAI API key not configured")
    
    logger.info("Setting up OpenAI transcription request...")
    
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    
    files = {
        "file": ("recording.mp3", audio_content, "audio/mpeg"),
        "model": (None, "whisper-1")
    }
    
    logger.info("Sending request to OpenAI...")
    response = requests.post(
        "https://api.openai.com/v1/audio/transcriptions",
        headers=headers,
        files=files,
        timeout=30
    )
    
    if not response.ok:
        logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
        response.raise_for_status()
    
    result = response.json()
    transcript = result.get("text", "")
    logger.info(f"OpenAI returned transcript: {transcript[:100]}...")
    
    return transcript

async def classify_with_anthropic(transcript: str):
    """Classify transcript using Anthropic Claude"""
    if not ANTHROPIC_API_KEY:
        raise ValueError("Anthropic API key not configured")
    
    logger.info("Setting up Anthropic classification request...")
    
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "content-type": "application/json",
        "anthropic-version": "2023-06-01"
    }
    
    system_prompt = """You are a support ticket triage tool. Output **only JSON** with keys `category`, `urgency`, `rationale`. `category` in {billing, bug, feature, other}. `urgency` in {low, medium, high}. Keep `rationale` one sentence."""
    
    data = {
        "model": "claude-3-haiku-20240307",
        "max_tokens": 150,
        "system": system_prompt,
        "messages": [
            {
                "role": "user",
                "content": f"Classify this support message: {transcript}"
            }
        ]
    }
    
    logger.info("Sending request to Anthropic...")
    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers=headers,
        json=data,
        timeout=30
    )
    
    if not response.ok:
        logger.error(f"Anthropic API error: {response.status_code} - {response.text}")
        response.raise_for_status()
    
    result = response.json()
    content = result["content"][0]["text"]
    logger.info(f"Anthropic returned: {content[:200]}...")
    
    # Extract JSON from response (handle cases where model adds text around JSON)
    json_match = re.search(r'\{.*\}', content, re.DOTALL)
    if json_match:
        try:
            classification = json.loads(json_match.group())
            logger.info(f"Successfully parsed classification: {classification}")
            return (
                classification.get("category", "other"),
                classification.get("urgency", "medium"),
                classification.get("rationale", "No rationale provided")
            )
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON from Anthropic response: {content}")
    
    # Fallback
    logger.warning("Using fallback classification")
    return "other", "medium", "Classification failed"

@app.get("/api/messages")
async def get_messages():
    """Get all messages (newest first)"""
    try:
        # Return messages sorted by creation time (newest first)
        sorted_messages = sorted(messages, key=lambda x: x.created_at, reverse=True)
        return sorted_messages
    except Exception as e:
        logger.error(f"Error getting messages: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Serve static files at root
@app.get("/")
async def root():
    """Serve the main page"""
    return FileResponse("static/index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
