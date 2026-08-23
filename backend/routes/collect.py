"""
Backward-compatibility bridge for collect routes.
All functionality is now powered by backend.routes.google_places with Google Places API (New).
"""
from backend.routes.google_places import google_places_bp as collect_bp

__all__ = ["collect_bp"]
