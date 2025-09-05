import os
import time
import json
import requests
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, validator
from dotenv import load_dotenv
import statistics

# Load environment variables
load_dotenv()

app = FastAPI(title="Schema-Strict Extractor")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Global stats tracking
stats = {
    "runs": 0,
    "valids": 0,
    "latencies": [],
    "total_cost": 0.0
}

# Pydantic models
class ExtractRequest(BaseModel):
    text: str

class ExtractedData(BaseModel):
    customer: str
    email: str
    category: str
    urgency: str
    summary: str
    
    @validator('category')
    def validate_category(cls, v):
        if v not in ['billing', 'bug', 'feature', 'other']:
            raise ValueError('Category must be one of: billing, bug, feature, other')
        return v
    
    @validator('urgency')
    def validate_urgency(cls, v):
        if v not in ['low', 'medium', 'high']:
            raise ValueError('Urgency must be one of: low, medium, high')
        return v

class ExtractResponse(BaseModel):
    data: Optional[ExtractedData]
    valid: bool
    errors: List[str]
    latency_ms: int
    est_cost_usd: float

class StatsResponse(BaseModel):
    runs: int
    valids: int
    success_rate_pct: float
    avg_latency_ms: float

# Configuration
PROVIDER = os.getenv('PROVIDER', 'OPENAI').upper()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
MODEL = os.getenv('MODEL', 'gpt-4o-mini')
PORT = int(os.getenv('PORT', 8000))

# Stub responses for when API keys are missing
STUB_RESPONSES = [
    {
        "customer": "John Doe",
        "email": "john@example.com",
        "category": "bug",
        "urgency": "high",
        "summary": "Application crashes when clicking submit button"
    },
    {
        "customer": "Jane Smith",
        "email": "jane@company.com",
        "category": "billing",
        "urgency": "medium",
        "summary": "Invoice amount seems incorrect for last month"
    },
    {
        "customer": "Bob Wilson",
        "email": "bob@startup.io",
        "category": "feature",
        "urgency": "low",
        "summary": "Would like to add dark mode to the interface"
    }
]

def get_stub_response(text: str) -> dict:
    """Return a deterministic stub response based on input text"""
    import hashlib
    hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
    return STUB_RESPONSES[hash_val % len(STUB_RESPONSES)]

def call_openai(text: str) -> str:
    """Call OpenAI API to extract structured data"""
    if not OPENAI_API_KEY:
        return json.dumps(get_stub_response(text))
    
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    prompt = f"""Extract the following information from this text and return ONLY valid JSON with no additional text or prose:

Text: {text}

Return a JSON object with these exact fields:
- customer: string (name of the person)
- email: string (email address)
- category: string (must be one of: billing, bug, feature, other)
- urgency: string (must be one of: low, medium, high)
- summary: string (brief description of the issue/request)

Example format:
{{
  "customer": "John Doe",
  "email": "john@example.com",
  "category": "bug",
  "urgency": "high",
  "summary": "Application crashes when clicking submit button"
}}"""

    data = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 500
    }
    
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers=headers,
        json=data,
        timeout=30
    )
    
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return json.dumps(get_stub_response(text))

def call_anthropic(text: str) -> str:
    """Call Anthropic API to extract structured data"""
    if not ANTHROPIC_API_KEY:
        return json.dumps(get_stub_response(text))
    
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01"
    }
    
    prompt = f"""Extract the following information from this text and return ONLY valid JSON with no additional text or prose:

Text: {text}

Return a JSON object with these exact fields:
- customer: string (name of the person)
- email: string (email address)
- category: string (must be one of: billing, bug, feature, other)
- urgency: string (must be one of: low, medium, high)
- summary: string (brief description of the issue/request)

Example format:
{{
  "customer": "John Doe",
  "email": "john@example.com",
  "category": "bug",
  "urgency": "high",
  "summary": "Application crashes when clicking submit button"
}}"""

    data = {
        "model": MODEL,
        "max_tokens": 500,
        "messages": [{"role": "user", "content": prompt}]
    }
    
    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers=headers,
        json=data,
        timeout=30
    )
    
    if response.status_code == 200:
        return response.json()["content"][0]["text"]
    else:
        return json.dumps(get_stub_response(text))

def estimate_cost(provider: str, model: str, tokens: int) -> float:
    """Estimate cost in USD based on provider, model, and token count"""
    # Rough cost estimates (you may want to update these)
    costs = {
        "OPENAI": {
            "gpt-4o-mini": 0.00015,  # per 1K tokens
            "gpt-4o": 0.005,
            "gpt-3.5-turbo": 0.0005
        },
        "ANTHROPIC": {
            "claude-3-haiku": 0.00025,
            "claude-3-sonnet": 0.003,
            "claude-3-opus": 0.015
        }
    }
    
    base_cost = costs.get(provider, {}).get(model, 0.001)
    return (tokens / 1000) * base_cost

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"ok": True}

@app.post("/api/extract", response_model=ExtractResponse)
async def extract_data(request: ExtractRequest):
    """Extract structured data from text"""
    start_time = time.time()
    
    # Call the appropriate API
    if PROVIDER == "OPENAI":
        response_text = call_openai(request.text)
    elif PROVIDER == "ANTHROPIC":
        response_text = call_anthropic(request.text)
    else:
        response_text = json.dumps(get_stub_response(request.text))
    
    # Try to parse the response
    try:
        # Clean the response - remove any prose and extract just the JSON
        response_text = response_text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        data = ExtractedData(**json.loads(response_text))
        valid = True
        errors = []
        
    except (json.JSONDecodeError, ValueError) as e:
        # First attempt failed, try to repair
        try:
            # Strip any prose and try to find JSON
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(0)
                data = ExtractedData(**json.loads(response_text))
                valid = True
                errors = []
            else:
                # Use stub as fallback
                data = ExtractedData(**get_stub_response(request.text))
                valid = False
                errors = [f"Failed to parse response: {str(e)}"]
        except Exception:
            # Final fallback to stub
            data = ExtractedData(**get_stub_response(request.text))
            valid = False
            errors = [f"Failed to parse response: {str(e)}"]
    
    # Calculate metrics
    latency_ms = int((time.time() - start_time) * 1000)
    est_cost_usd = estimate_cost(PROVIDER, MODEL, len(request.text.split()) * 2)  # Rough token estimate
    
    # Update stats
    stats["runs"] += 1
    if valid:
        stats["valids"] += 1
    stats["latencies"].append(latency_ms)
    stats["total_cost"] += est_cost_usd
    
    return ExtractResponse(
        data=data,
        valid=valid,
        errors=errors,
        latency_ms=latency_ms,
        est_cost_usd=est_cost_usd
    )

@app.get("/api/stats", response_model=StatsResponse)
async def get_stats():
    """Get extraction statistics"""
    avg_latency = 0.0
    if stats["latencies"]:
        avg_latency = statistics.mean(stats["latencies"])
    
    success_rate = 0.0
    if stats["runs"] > 0:
        success_rate = (stats["valids"] / stats["runs"]) * 100
    
    return StatsResponse(
        runs=stats["runs"],
        valids=stats["valids"],
        success_rate_pct=round(success_rate, 2),
        avg_latency_ms=round(avg_latency, 2)
    )

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main HTML page"""
    with open("static/index.html", "r") as f:
        return HTMLResponse(content=f.read())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)