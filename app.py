"""
AgriGuide AI - Flask Backend
IBM watsonx.ai powered Agriculture Assistant
"""

import os
import re
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session
from dotenv import load_dotenv

# ─────────────────────────────────────────────────────────────────
# Load .env from the project root (same directory as this file).
# dotenv_path makes the location explicit regardless of cwd.
# ─────────────────────────────────────────────────────────────────
_HERE = Path(__file__).parent.resolve()
_DOTENV_PATH = _HERE / ".env"
load_dotenv(dotenv_path=_DOTENV_PATH, override=True)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "agriguide-dev-secret-2024")

# ─────────────────────────────────────────────────────────────────
# AGENT INSTRUCTIONS — Modify this section to customise the AI agent
# ─────────────────────────────────────────────────────────────────
AGENT_INSTRUCTIONS = {
    # Personality & tone
    "personality": "friendly, knowledgeable, and empathetic agricultural expert",
    "tone": "professional yet approachable, using simple language farmers can understand",

    # Safety & ethics rules
    "safety_rules": [
        "Never recommend unsafe pesticide combinations",
        "Always advise consulting local agricultural officers for critical decisions",
        "Do not provide medical advice for human health",
        "Recommend government-approved practices only",
        "Warn about environmental impact of chemical overuse",
    ],

    # Core farming expertise areas
    "agriculture_expertise": [
        "Crop selection and rotation",
        "Soil health and fertility management",
        "Integrated Pest Management (IPM)",
        "Organic and sustainable farming",
        "Irrigation and water management",
        "Fertilizer and nutrient management",
        "Seed selection and variety recommendations",
        "Harvest and post-harvest management",
        "Climate-smart agriculture",
        "Government agricultural schemes and subsidies",
        "Disease identification and prevention",
        "Weather-based advisory",
    ],

    # Supported languages (inform users, model responds in user language)
    "supported_languages": ["English", "Hindi", "Tamil", "Telugu", "Kannada",
                            "Marathi", "Bengali", "Gujarati", "Punjabi"],

    # Recommendation style
    "recommendation_style": (
        "Structured with clear headings, bullet points for action items, "
        "estimated timelines, input cost hints, and a 'Quick Tip' at the end."
    ),

    # Farming specializations
    "specializations": [
        "Smallholder and marginal farming",
        "Kharif and Rabi crop cycles",
        "Dryland and rainfed agriculture",
        "Horticulture and floriculture",
        "Aquaculture and integrated farming",
        "Precision agriculture",
    ],

    # Response language instruction
    "language_instruction": (
        "Detect the language of the user message and respond in the same language. "
        "Default to English if uncertain."
    ),
}

# ─────────────────────────────────────────────────────────────────
# IBM watsonx.ai Configuration — loaded from .env, never hardcoded
# ─────────────────────────────────────────────────────────────────
IBM_API_KEY    = os.getenv("IBM_API_KEY",    "").strip()
IBM_PROJECT_ID = os.getenv("IBM_PROJECT_ID", "").strip()
IBM_URL        = os.getenv("IBM_URL",        "").strip()
MODEL_NAME     = os.getenv("MODEL_NAME",     "").strip()

# Minimum SDK version required for Sydney (au-syd) and other newer regions.
# SDK < 1.1.23 has a hardcoded URL allowlist that excludes au-syd and raises
# "The specified url is not valid … add instance_id openshift" at init time.
_SDK_MIN_VERSION = "1.1.23"

def _check_sdk_version() -> str | None:
    """
    Return None if the installed ibm-watsonx-ai SDK meets the minimum version,
    or a sanitised error string if it is missing or too old.
    Never raises — only prints and returns.
    """
    try:
        import ibm_watsonx_ai as _wx
        installed = _wx.__version__
        print(f"[SDK] ibm-watsonx-ai installed version: {installed}", flush=True)
        from packaging.version import Version
        if Version(installed) < Version(_SDK_MIN_VERSION):
            msg = (
                f"ibm-watsonx-ai {installed} is too old — "
                f"version >= {_SDK_MIN_VERSION} is required for the Sydney (au-syd) endpoint. "
                f"Run: pip install 'ibm-watsonx-ai>={_SDK_MIN_VERSION}'"
            )
            print(f"[SDK ERROR] {msg}", flush=True)
            return msg
        return None
    except ImportError:
        msg = "ibm-watsonx-ai is not installed. Run: pip install ibm-watsonx-ai>=" + _SDK_MIN_VERSION
        print(f"[SDK ERROR] {msg}", flush=True)
        return msg

# ── Startup diagnostics (printed once when the process starts) ───
print("=" * 60, flush=True)
print("[CONFIG] .env path      :", _DOTENV_PATH, flush=True)
print("[CONFIG] .env exists    :", _DOTENV_PATH.exists(), flush=True)
print("[CONFIG] IBM_API_KEY    :", "SET" if IBM_API_KEY else "MISSING", flush=True)
print("[CONFIG] IBM_PROJECT_ID :", IBM_PROJECT_ID or "MISSING", flush=True)
print("[CONFIG] IBM_URL        :", IBM_URL or "MISSING", flush=True)
print("[CONFIG] MODEL_NAME     :", MODEL_NAME or "(empty — will auto-discover)", flush=True)
print("=" * 60, flush=True)

_SDK_ERROR = _check_sdk_version()


def _redact(text: str) -> str:
    """Scrub the IBM API key and IAM tokens from any string."""
    if IBM_API_KEY:
        text = text.replace(IBM_API_KEY, "<REDACTED>")
    # also catch bare ApiKey-… / apikey=… patterns in SDK error messages
    text = re.sub(r'(?i)(api[_\-]?key\s*[:=]\s*)\S+', r'\1<REDACTED>', text)
    text = re.sub(r'(?i)(bearer\s+)\S{20,}', r'\1<REDACTED>', text)
    return text


def _config_errors() -> list[str]:
    """Return a list of configuration problems, empty if all OK."""
    errors: list[str] = []
    if not IBM_API_KEY:
        errors.append("IBM_API_KEY is not set")
    if not IBM_PROJECT_ID:
        errors.append("IBM_PROJECT_ID is not set")
    else:
        # must look like a UUID
        if not re.fullmatch(
            r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            IBM_PROJECT_ID, re.IGNORECASE
        ):
            errors.append(f"IBM_PROJECT_ID does not look like a UUID: {IBM_PROJECT_ID!r}")
    if not IBM_URL:
        errors.append("IBM_URL is not set")
    else:
        if not IBM_URL.startswith("https://"):
            errors.append(f"IBM_URL must start with https://: {IBM_URL!r}")
    return errors


def _discover_model() -> str:
    """
    Query the watsonx foundation-model specification endpoint (authenticated)
    and return the model_id of the best available text-generation instruct
    model for this agriculture assistant.

    Selection rules (applied in order, first match wins):
      1. granite-*-instruct  — preferred: IBM's own instruction-tuned models
      2. llama-*-instruct    — fallback general-purpose instruct model
      3. any *-instruct      — any remaining instruct-tuned model
      Excluded: any model whose ID contains "code" — code-generation models
                are not appropriate for an agriculture assistant.

    Returns an empty string on any error (caller must handle).
    """
    import urllib.request
    import urllib.parse
    import json as _json

    # ── Step 1: IBM Cloud IAM bearer token ────────────────────────
    iam_data = urllib.parse.urlencode({
        "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
        "apikey": IBM_API_KEY,
    }).encode()
    try:
        req = urllib.request.Request(
            "https://iam.cloud.ibm.com/identity/token",
            data=iam_data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            token = _json.loads(r.read())["access_token"]
        print("[DISCOVER] IAM token obtained", flush=True)
    except Exception as exc:
        print(f"[DISCOVER] IAM token failed — {type(exc).__name__}: {exc}", flush=True)
        return ""

    # ── Step 2: list foundation models for this region/project ────
    # Use the authenticated endpoint so we get the full list for our region.
    # version=2024-07-18 matches the SDK's own API_VERSION_PARAM file.
    specs_url = (
        f"{IBM_URL}/ml/v1/foundation_model_specs"
        f"?version=2024-07-18&limit=200"
    )
    try:
        req2 = urllib.request.Request(
            specs_url,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        )
        with urllib.request.urlopen(req2, timeout=15) as r:
            data = _json.loads(r.read())
        all_ids: list[str] = [m["model_id"] for m in data.get("resources", [])]
        print(f"[DISCOVER] {len(all_ids)} models available from {IBM_URL}", flush=True)
        print(f"[DISCOVER] full model list: {all_ids}", flush=True)
    except Exception as exc:
        print(f"[DISCOVER] model-spec query failed — {type(exc).__name__}: {exc}", flush=True)
        return ""

    if not all_ids:
        print("[DISCOVER] model list was empty", flush=True)
        return ""

    # ── Step 3: filter and rank for agriculture use ────────────────
    # Exclude code-generation models — irrelevant for an agriculture chatbot.
    text_ids = [mid for mid in all_ids if "code" not in mid.lower()]
    if not text_ids:
        print("[DISCOVER] all models were code models; using full list as fallback", flush=True)
        text_ids = all_ids

    def _rank(mid: str) -> int:
        m = mid.lower()
        if "granite" in m and "instruct" in m:
            return 0   # preferred: IBM granite instruct
        if "llama" in m and "instruct" in m:
            return 1   # fallback: llama instruct
        if "instruct" in m:
            return 2   # any other instruct model
        return 9       # non-instruct model (last resort)

    chosen = sorted(text_ids, key=_rank)[0]
    print(f"[DISCOVER] selected model: {chosen}", flush=True)
    return chosen


def _resolve_model() -> str:
    """
    Return the model ID to use:
      - If MODEL_NAME is set in .env, validate and use it as-is.
      - Otherwise run _discover_model() and update the global.
    """
    global MODEL_NAME

    if MODEL_NAME:
        print(f"[MODEL] Using configured MODEL_NAME: {MODEL_NAME}", flush=True)
        return MODEL_NAME

    print("[MODEL] MODEL_NAME not set — querying watsonx for available models …", flush=True)
    discovered = _discover_model()
    if discovered:
        MODEL_NAME = discovered
        print(f"[MODEL] Auto-selected MODEL_NAME: {MODEL_NAME}", flush=True)
    else:
        print("[MODEL] Could not discover a model; client will fail at runtime.", flush=True)
    return MODEL_NAME


# Run model resolution once at startup (after config is loaded).
# Skip if the SDK is too old — no point trying to connect.
_cfg_errors = _config_errors()
if _SDK_ERROR:
    pass  # already printed above by _check_sdk_version()
elif _cfg_errors:
    for _err in _cfg_errors:
        print(f"[CONFIG ERROR] {_err}", flush=True)
else:
    _resolve_model()


def get_watsonx_client():
    """
    Initialise and return an IBM watsonx.ai ModelInference client.

    Credentials: IBM Cloud IAM (api_key) — NOT Cloud Pak for Data.
    Do NOT pass instance_id="openshift"; that is only for on-premises CPD.

    validate=False: the SDK's built-in model-ID whitelist is a point-in-time
    snapshot. Newer models (e.g. granite-3-3-8b-instruct) may not appear in
    the list for older SDK releases. Skipping the local check lets the live
    API report the real error if the model truly does not exist.

    Prints the complete exception type + HTTP status on failure; never prints
    the API key.
    """
    if _SDK_ERROR:
        print(f"[watsonx] Cannot create client — SDK too old: {_SDK_ERROR}", flush=True)
        return None

    errors = _config_errors()
    if errors:
        for e in errors:
            print(f"[watsonx] Cannot create client — {e}", flush=True)
        return None

    if not MODEL_NAME:
        print("[watsonx] Cannot create client — MODEL_NAME is empty", flush=True)
        return None

    try:
        from ibm_watsonx_ai import Credentials
        from ibm_watsonx_ai.foundation_models import ModelInference
        from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as Params

        # IBM Cloud credentials: url + api_key only.
        # Never add instance_id="openshift" here — that is exclusively for
        # on-premises Cloud Pak for Data (CPD) installations and will cause
        # the SDK to attempt a CPD version handshake against your Cloud URL.
        credentials = Credentials(url=IBM_URL, api_key=IBM_API_KEY)

        model = ModelInference(
            model_id=MODEL_NAME,
            credentials=credentials,
            project_id=IBM_PROJECT_ID,
            validate=False,   # skip frozen SDK model-ID enum (see docstring)
            params={
                Params.MAX_NEW_TOKENS: 1024,
                Params.MIN_NEW_TOKENS: 10,
                Params.TEMPERATURE: 0.7,
                Params.TOP_P: 0.9,
                Params.REPETITION_PENALTY: 1.1,
            },
        )
        return model
    except Exception as exc:
        exc_type = type(exc).__name__
        exc_msg  = _redact(str(exc))
        status   = getattr(exc, "http_status_code", getattr(exc, "status_code", None))
        if status:
            print(f"[watsonx ERROR] {exc_type} (HTTP {status}): {exc_msg}", flush=True)
        else:
            print(f"[watsonx ERROR] {exc_type}: {exc_msg}", flush=True)
        app.logger.error("watsonx client init failed: %s: %s", exc_type, exc_msg)
        return None


def build_system_prompt() -> str:
    """Construct the full system prompt from AGENT_INSTRUCTIONS."""
    rules = "\n".join(f"  - {r}" for r in AGENT_INSTRUCTIONS["safety_rules"])
    expertise = "\n".join(f"  - {e}" for e in AGENT_INSTRUCTIONS["agriculture_expertise"])
    specs = "\n".join(f"  - {s}" for s in AGENT_INSTRUCTIONS["specializations"])
    langs = ", ".join(AGENT_INSTRUCTIONS["supported_languages"])

    return f"""You are AgriGuide AI, a {AGENT_INSTRUCTIONS['personality']}.
Your tone is {AGENT_INSTRUCTIONS['tone']}.

## Core Expertise
{expertise}

## Specializations
{specs}

## Safety Rules (strictly follow)
{rules}

## Recommendation Style
{AGENT_INSTRUCTIONS['recommendation_style']}

## Language
{AGENT_INSTRUCTIONS['language_instruction']}
Supported languages: {langs}

## Context Gathering
When a farmer asks for crop or fertilizer advice, ask for:
- Crop name (if not mentioned)
- Location / State / District
- Soil type (clay, loam, sandy, black cotton, red laterite, etc.)
- Farm size in acres/hectares
- Current season (Kharif / Rabi / Zaid / year-round)
- Irrigation availability (rainfed / irrigated / drip / sprinkler)
- Farming objective (subsistence / commercial / organic)

Keep context short if user has already provided details.
Always end responses with a practical "💡 Quick Tip" relevant to the query.
"""


def chat_with_watsonx(user_message: str, history: list) -> str:
    """Send a message to IBM watsonx.ai Granite and return the response."""
    errors = _config_errors()
    if errors:
        detail = "; ".join(errors)
        return f"⚠️ Configuration error — {detail}. Check your .env file."

    model = get_watsonx_client()
    if not model:
        return (
            f"⚠️ Could not connect to IBM watsonx (model: {MODEL_NAME}). "
            "Check the terminal for the exact error."
        )

    # Build prompt with conversation history (last 6 turns for context window)
    system_prompt = build_system_prompt()
    history_text = ""
    for turn in history[-6:]:
        role = turn.get("role", "user")
        content = turn.get("content", "")
        if role == "user":
            history_text += f"\nFarmer: {content}"
        else:
            history_text += f"\nAgriGuide AI: {content}"

    prompt = (
        f"<|system|>\n{system_prompt}\n<|end|>\n"
        f"{history_text}\n"
        f"Farmer: {user_message}\n"
        f"AgriGuide AI:"
    )

    try:
        response = model.generate_text(prompt=prompt)
        return response.strip() if response else "I could not generate a response. Please try again."
    except Exception as exc:
        exc_type = type(exc).__name__
        exc_msg  = _redact(str(exc))
        status   = getattr(exc, "http_status_code", getattr(exc, "status_code", None))
        if status:
            print(f"[watsonx ERROR] generate_text: {exc_type} (HTTP {status}): {exc_msg}", flush=True)
            return f"⚠️ Watsonx error (HTTP {status} {exc_type}): {exc_msg}"
        else:
            print(f"[watsonx ERROR] generate_text: {exc_type}: {exc_msg}", flush=True)
            return f"⚠️ Watsonx error ({exc_type}): {exc_msg}"


# ─────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/chat")
def chat():
    if "chat_history" not in session:
        session["chat_history"] = []
    return render_template("chat.html", history=session["chat_history"])


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/crop")
def crop():
    return render_template("crop.html")


@app.route("/fertilizer")
def fertilizer():
    return render_template("fertilizer.html")


@app.route("/pest")
def pest():
    return render_template("pest.html")


@app.route("/disease")
def disease():
    return render_template("disease.html")


@app.route("/weather")
def weather():
    return render_template("weather.html")


@app.route("/sustainable")
def sustainable():
    return render_template("sustainable.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


# ─────────────────────────────────────────────────────────────────
# API Endpoints
# ─────────────────────────────────────────────────────────────────

@app.route("/api/chat", methods=["POST"])
def api_chat():
    """Main chat endpoint — receives a message, returns AI response."""
    data = request.get_json(silent=True) or {}
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"error": "Message cannot be empty"}), 400

    # Retrieve / initialise session history
    if "chat_history" not in session:
        session["chat_history"] = []

    history = session["chat_history"]
    ai_response = chat_with_watsonx(user_message, history)

    # Persist to session (keep last 20 turns)
    history.append({"role": "user",      "content": user_message,  "time": datetime.now().strftime("%H:%M")})
    history.append({"role": "assistant", "content": ai_response,   "time": datetime.now().strftime("%H:%M")})
    session["chat_history"] = history[-20:]
    session.modified = True

    return jsonify({
        "response":  ai_response,
        "timestamp": datetime.now().strftime("%H:%M"),
    })


@app.route("/api/quick-ask", methods=["POST"])
def api_quick_ask():
    """One-shot quick question endpoint (no session history)."""
    data = request.get_json(silent=True) or {}
    topic   = data.get("topic", "general farming")
    context = data.get("context", "")

    prompt = f"Give a concise, practical recommendation about {topic}. {context}"
    model  = get_watsonx_client()

    if not model:
        return jsonify({"error": "AI service unavailable"}), 503

    try:
        system_prompt = build_system_prompt()
        full_prompt = (
            f"<|system|>\n{system_prompt}\n<|end|>\n"
            f"Farmer: {prompt}\nAgriGuide AI:"
        )
        response = model.generate_text(prompt=full_prompt)
        return jsonify({"response": response.strip()})
    except Exception as exc:
        safe = _redact(str(exc))
        return jsonify({"error": safe}), 500


@app.route("/api/clear-chat", methods=["POST"])
def api_clear_chat():
    """Clear chat history from session."""
    session.pop("chat_history", None)
    return jsonify({"status": "cleared"})


@app.route("/api/health")
def api_health():
    """
    Detailed health endpoint — reports config state, client creation and a
    live smoke-test against watsonx.  Never returns the API key.
    """
    cfg_errors = _config_errors()
    configuration_loaded = len(cfg_errors) == 0

    # Try to build a client
    watsonx_client_created = False
    connection_status      = "not_attempted"
    smoke_result           = None

    if configuration_loaded and MODEL_NAME:
        client = get_watsonx_client()
        if client:
            watsonx_client_created = True
            # Run a minimal smoke-test prompt
            try:
                from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as Params
                out = client.generate_text(
                    prompt="Reply with exactly one word: hello",
                    params={Params.MAX_NEW_TOKENS: 10, Params.MIN_NEW_TOKENS: 1},
                )
                smoke_result      = repr(out.strip()) if out else "(empty response)"
                connection_status = "ok"
                print(f"[HEALTH] smoke-test result: {smoke_result}", flush=True)
            except Exception as exc:
                exc_type = type(exc).__name__
                exc_msg  = _redact(str(exc))
                status   = getattr(exc, "http_status_code", getattr(exc, "status_code", None))
                if status:
                    detail = f"{exc_type} HTTP {status}: {exc_msg}"
                else:
                    detail = f"{exc_type}: {exc_msg}"
                connection_status = f"error: {detail}"
                print(f"[HEALTH] smoke-test failed: {detail}", flush=True)
        else:
            connection_status = "client_creation_failed"
    elif not MODEL_NAME:
        connection_status = "no_model_selected"
    else:
        connection_status = "config_invalid: " + "; ".join(cfg_errors)

    return jsonify({
        "app":                    "AgriGuide AI",
        "timestamp":              datetime.now().isoformat(),
        "configuration_loaded":   configuration_loaded,
        "config_errors":          cfg_errors,
        "dotenv_path":            str(_DOTENV_PATH),
        "dotenv_exists":          _DOTENV_PATH.exists(),
        "selected_model":         MODEL_NAME or None,
        "watsonx_client_created": watsonx_client_created,
        "connection_status":      connection_status,
        "smoke_test_result":      smoke_result,
        # presence indicators only — never the actual values
        "ibm_api_key_set":        bool(IBM_API_KEY),
        "ibm_project_id_set":     bool(IBM_PROJECT_ID),
        "ibm_url":                IBM_URL,
    })


@app.route("/api/crop-data")
def api_crop_data():
    """Return sample crop data for dashboard charts."""
    return jsonify({
        "seasons": {
            "kharif": ["Rice", "Maize", "Cotton", "Soybean", "Groundnut", "Jowar", "Bajra"],
            "rabi":   ["Wheat", "Barley", "Mustard", "Chickpea", "Peas", "Linseed"],
            "zaid":   ["Watermelon", "Muskmelon", "Cucumber", "Bitter Gourd", "Moong"],
        },
        "soil_crops": {
            "Alluvial":     ["Wheat", "Rice", "Sugarcane", "Cotton"],
            "Black Cotton": ["Cotton", "Jowar", "Soybean", "Sunflower"],
            "Red Laterite": ["Groundnut", "Pulses", "Millets", "Cashew"],
            "Sandy":        ["Bajra", "Groundnut", "Watermelon", "Cucumber"],
            "Clay":         ["Rice", "Wheat", "Sugarcane", "Jute"],
        },
        "monthly_tips": [
            "Test soil pH before sowing",
            "Apply FYM / compost 3 weeks before transplanting",
            "Monitor for pest hotspots weekly",
            "Practice crop rotation every season",
            "Use drip irrigation to save 40–60% water",
        ],
    })


# ─────────────────────────────────────────────────────────────────
# Error handlers
# ─────────────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(e):
    return render_template("500.html"), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "True").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
