import os

from dotenv import load_dotenv

# Never send telemetry to a live Sentry DSN during tests. Set before app.main is
# imported (it calls init_telemetry at import time) and before load_dotenv below;
# load_dotenv(override=False) won't overwrite it, so init_telemetry sees an empty
# DSN and skips sentry_sdk.init entirely even if .env defines a real one.
os.environ["SENTRY_DSN"] = ""

# Load .env so ANTHROPIC_API_KEY (and friends) are present without manual shell
# setup — e.g. the eval-seed tests attempt to run instead of auto-skipping.
load_dotenv()
