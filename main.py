import logging
import os
import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request
import time

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Environment variables for configuration
GETDX_API_KEY = os.getenv("GETDX_API_KEY")
EVENTS_TRACKED = os.getenv("EVENTS_TRACKED", "").split(",")

# Clean up event list and convert to lowercase for case-insensitive comparison
EVENTS_TRACKED = [event.strip().lower() for event in EVENTS_TRACKED]

app = Flask(__name__)

@app.route("/", methods=['GET'])
def hello_world():
    return jsonify({"message": "Hello from Coder middleware"})

@app.route("/", methods=['POST'])
def webhook_handler():
    payload = request.get_json()
    logger.info("Received webhook payload: %s", payload)
    
    # Extract notification name from the nested payload structure
    event_name = payload.get("payload", {}).get("notification_name", "").strip()
    
    if event_name.lower() in EVENTS_TRACKED:
        logger.info("Forwarding event: %s", event_name)
        forward_to_getdx(payload)
    else:
        logger.info("Event not tracked, ignoring: %s", event_name)
        logger.debug("Tracked events are: %s", EVENTS_TRACKED)
    
    return jsonify({"status": "received"})

def forward_to_getdx(payload):
    if not GETDX_API_KEY:
        logger.error("GETDX_API_KEY is not set")
        return
    
    coder_payload = payload.get("payload", {})
    
    getdx_payload = {
        "name": coder_payload.get("notification_name"),
        "email": coder_payload.get("user_email"),
        "timestamp": str(int(time.time())),  # Current timestamp since Coder doesn't provide one
        "metadata": {
            "full_webhook": payload,  # The complete webhook payload
            "workspace_name": coder_payload.get("data", {}).get("workspace", {}).get("name"),
            "template_name": coder_payload.get("data", {}).get("template", {}).get("name"),
            "user_name": coder_payload.get("user_name"),
            "user_username": coder_payload.get("user_username"),
            "template_version": coder_payload.get("data", {}).get("template_version", {}).get("name"),
            "labels": coder_payload.get("labels")
        }
    }
    
    # Remove None values from metadata
    getdx_payload["metadata"] = {k: v for k, v in getdx_payload["metadata"].items() if v is not None}
    
    # Debug log the API key (masked)
    masked_key = f"{GETDX_API_KEY[:4]}...{GETDX_API_KEY[-4:]}" if GETDX_API_KEY else "None"
    logger.debug("Using API key: %s", masked_key)
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GETDX_API_KEY.strip()}"  # Added strip() to remove any whitespace
    }
    
    logger.info("Forwarding event to getDX with payload: %s", getdx_payload)
    
    try:
        response = requests.post("https://api.getdx.com/events.track", json=getdx_payload, headers=headers)
        response.raise_for_status()
        logger.info("Successfully forwarded event to getDX. Response: %s", response.text)
    except requests.exceptions.RequestException as e:
        logger.error("Failed to forward event to getDX: %s", e)
        # Log the actual response if available
        if hasattr(e, 'response') and e.response is not None:
            logger.error("getDX error response: %s", e.response.text)

@app.route("/health")
def health_check():
    return jsonify({"status": "healthy"})

if __name__ == "__main__":
    if not GETDX_API_KEY:
        logger.warning("GETDX_API_KEY is not set or empty")
    else:
        logger.info("GETDX_API_KEY is configured (length: %d)", len(GETDX_API_KEY))
    app.run(host="0.0.0.0", port=8080, debug=True)
