import os
import sys

# Ensure the project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, send_from_directory
from flask_cors import CORS

from backend.database import engine, Base, run_migrations
from backend.models import (
    Lead, OutreachActivity, WebsiteAnalysisRecord, CollectionJob,
    CollectionLog, FollowUp, ApiUsageRecord
)
from backend.routes.leads import leads_bp
from backend.routes.analyzer import analyzer_bp
from backend.routes.google_places import google_places_bp

# ── Ensure all database tables, columns & indexes exist ─────────────────
run_migrations()
Base.metadata.create_all(bind=engine)

# ── Flask app ───────────────────────────────────────────────────────────
app = Flask(__name__, static_folder=None)
CORS(app)

app.register_blueprint(leads_bp)
app.register_blueprint(analyzer_bp)
app.register_blueprint(google_places_bp)

# ── Serve frontend static files ────────────────────────────────────────
FRONTEND_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend"
)

@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "leads.html")

@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(FRONTEND_DIR, path)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
