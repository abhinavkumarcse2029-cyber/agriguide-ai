"""
Temporary diagnostic script — probes IBM IAM + watsonx model list.
API key is NEVER printed. Delete after use.
"""
import sys
import json
import urllib.request
import urllib.parse
import os

# Read from env so the key never appears in terminal history
from dotenv import load_dotenv
load_dotenv(dotenv_path=".env", override=True)

API_KEY    = os.getenv("IBM_API_KEY", "")
PROJECT_ID = os.getenv("IBM_PROJECT_ID", "")
URL        = os.getenv("IBM_URL", "https://us-south.ml.cloud.ibm.com")

if not API_KEY:
    print("[PROBE] IBM_API_KEY not set — write .env first"); sys.exit(1)

# ── 1. IAM token ──────────────────────────────────────────────────
iam_data = urllib.parse.urlencode({
    "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
    "apikey": API_KEY,
}).encode()
req = urllib.request.Request(
    "https://iam.cloud.ibm.com/identity/token",
    data=iam_data,
    headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
)
try:
    with urllib.request.urlopen(req, timeout=20) as r:
        token_body = json.loads(r.read())
    token = token_body["access_token"]
    print("[IAM] token obtained  ✓")
except Exception as e:
    print(f"[IAM] FAILED — {type(e).__name__}: {e}")
    sys.exit(1)

# ── 2. List available foundation models ───────────────────────────
for api_ver in ["2024-03-13", "2023-05-29"]:
    models_url = f"{URL}/ml/v1/foundation_model_specs?version={api_ver}&limit=200"
    req2 = urllib.request.Request(
        models_url,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req2, timeout=20) as r:
            resp = json.loads(r.read())
        ids = [m["model_id"] for m in resp.get("resources", [])]
        print(f"[MODELS] api-version={api_ver}  total={len(ids)}")
        granite = sorted(m for m in ids if "granite" in m.lower())
        print(f"[GRANITE IDs found]  {json.dumps(granite, indent=2)}")
        break
    except Exception as e:
        print(f"[MODELS] api-version={api_ver} failed — {type(e).__name__}: {e}")

# ── 3. Quick smoke-test: init ModelInference ──────────────────────
print("\n[SMOKE] initialising ModelInference …")
try:
    from ibm_watsonx_ai import Credentials
    from ibm_watsonx_ai.foundation_models import ModelInference
    from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as Params

    MODEL_TO_TEST = os.getenv("MODEL_NAME", "ibm/granite-3-3-8b-instruct")
    print(f"[SMOKE] model_id = {MODEL_TO_TEST}")

    creds = Credentials(url=URL, api_key=API_KEY)
    model = ModelInference(
        model_id=MODEL_TO_TEST,
        credentials=creds,
        project_id=PROJECT_ID,
        validate=False,   # skip SDK's frozen whitelist — same as app.py
        params={
            Params.MAX_NEW_TOKENS: 20,
            Params.MIN_NEW_TOKENS: 1,
        },
    )
    # Minimal generate to confirm the model is reachable
    out = model.generate_text(prompt="Hi")
    print(f"[SMOKE] generate_text returned: {repr(out[:120])}")
    print("[SMOKE] SUCCESS ✓  — client initialises and generates correctly")
except Exception as e:
    msg = str(e)
    print(f"[SMOKE] FAILED — {type(e).__name__}: {msg}")
