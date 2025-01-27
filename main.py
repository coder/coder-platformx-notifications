import logging
from flask import Flask, jsonify, request

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route("/", methods=['GET'])
def hello_world():
    return jsonify({"message": "Hello from Coder middleware"})

@app.route("/", methods=['POST'])
def webhook_handler():
    payload = request.get_json()
    logger.info("Received webhook payload: %s", payload)
    return jsonify({"status": "received"})

@app.route("/health")
def health_check():
    return jsonify({"status": "healthy"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True) 