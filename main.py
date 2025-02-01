import logging
import os
import time
import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request

# Load environment variables and configure logging
load_dotenv()

# Configure logging levels
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,     # Most verbose - shows payloads, redacted API keys
    "INFO": logging.INFO,       # Normal - shows event names and forwarding status
    "WARNING": logging.WARNING  # Least verbose - shows only warnings and errors
}

logging.basicConfig(
    level=LOG_LEVELS.get(LOG_LEVEL, logging.INFO),
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Load configuration
GETDX_API_KEY = os.getenv("GETDX_API_KEY")
EVENTS_TRACKED = [event.strip() for event in os.getenv("EVENTS_TRACKED", "").split(",") if event.strip()]

# Initialize Flask app
app = Flask(__name__)

def normalize_event_name(event_name):
    """Normalize event name for case-insensitive comparison."""
    return " ".join(event_name.lower().split())

def get_target_email(payload):
    """Extract the appropriate email based on event type."""
    coder_payload = payload.get("payload", {})
    event_name = coder_payload.get("notification_name", "").lower()
    
    if "workspace" in event_name:
        return coder_payload.get("data", {}).get("owner", {}).get("email")
    elif "user account" in event_name:
        return coder_payload.get("data", {}).get("user", {}).get("email")
    return None

def prepare_getdx_payload(coder_webhook):
    """Prepare the payload for getDX API."""
    coder_payload = coder_webhook.get("payload", {})
    
    # Create clean version without notification recipient details
    clean_payload = coder_webhook.copy()
    clean_inner = clean_payload.get("payload", {}).copy()
    
    # Remove admin notification fields
    for field in ["user_id", "user_email", "user_name", "user_username"]:
        clean_inner.pop(field, None)
    clean_payload["payload"] = clean_inner
    
    return {
        "name": coder_payload.get("notification_name"),
        "email": get_target_email(coder_webhook),
        "timestamp": str(int(time.time())),
        "metadata": {
            "full_webhook": clean_payload,
            "labels": coder_payload.get("labels"),
            "event_data": coder_payload.get("data")
        }
    }

def forward_to_getdx(payload):
    """Forward event to getDX API."""
    if not GETDX_API_KEY:
        logger.error("GETDX_API_KEY is not set")
        return
    
    getdx_payload = prepare_getdx_payload(payload)
    if not getdx_payload["email"]:
        logger.error("No target email found in payload")
        return
    
    # Remove None values from metadata
    getdx_payload["metadata"] = {k: v for k, v in getdx_payload["metadata"].items() if v is not None}
    
    logger.debug("Using API key: %s...%s", GETDX_API_KEY[:4], GETDX_API_KEY[-4:])
    logger.debug("Forwarding to getDX with payload: %s", getdx_payload)
    
    try:
        response = requests.post(
            "https://api.getdx.com/events.track",
            json=getdx_payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {GETDX_API_KEY.strip()}"
            }
        )
        response.raise_for_status()
        logger.info("Successfully forwarded event to getDX")
        logger.debug("getDX response: %s", response.text)
    except requests.exceptions.RequestException as e:
        logger.error("Failed to forward event to getDX: %s", e)
        if hasattr(e, 'response') and e.response:
            logger.error("getDX error response: %s", e.response.text)

@app.route("/", methods=['GET'])
def hello_world():
    return jsonify({"message": "Hello from Coder middleware"})

@app.route("/", methods=['POST'])
def webhook_handler():
    try:
        payload = request.get_json()
        event_name = payload.get("payload", {}).get("notification_name", "").strip()
        
        logger.debug("Received webhook payload: %s", payload)
        logger.info("Received webhook for event: %s", event_name)
        
        if normalize_event_name(event_name) in [normalize_event_name(e) for e in EVENTS_TRACKED]:
            logger.info("Forwarding event: %s", event_name)
            forward_to_getdx(payload)
        else:
            logger.info("Event not tracked, ignoring: %s", event_name)
        
        return jsonify({"status": "received"})
    except Exception as e:
        logger.error("Error processing webhook: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 500

# Log startup information
if __name__ == "__main__":
    logger.info("Server starting with log level: %s", LOG_LEVEL)
    logger.info("To change verbosity, set LOG_LEVEL to: %s", ", ".join(LOG_LEVELS.keys()))
    logger.info("Tracking events: %s", EVENTS_TRACKED)
    app.run(host="0.0.0.0", port=8080)
