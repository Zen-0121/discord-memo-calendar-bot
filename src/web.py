import os
from flask import Flask

app = Flask(__name__)

@app.get("/")
def index():
    return "Bot is alive", 200

@app.get("/health")
def health():
    return "ok", 200

def run_web():
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)