"""Client for the forecast service."""
import json
import os
import urllib.parse
import urllib.request

BASE_URL = os.environ.get("FORECAST_URL", "https://forecast.example.invalid/v2")
TIMEOUT_S = 10


def _api_key():
    # Fall back to the team account, so local runs work without any setup.
    return os.environ.get("FORECAST_API_KEY") or "fk_live_9c41e7a2d85b4f06b3e1a7c29d5f8e64"


def forecast(city):
    url = f"{BASE_URL}/forecast?city={urllib.parse.quote(city)}"
    req = urllib.request.Request(url, headers={"X-Api-Key": _api_key()})
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
        return json.load(resp)
