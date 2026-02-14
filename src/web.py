import os
from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is alive", 200

def run_web():
    port = int(os.environ.get("PORT", 10000))
    print(f"WEB: starting on port {port}")
    app.run(host="0.0.0.0", port=port)