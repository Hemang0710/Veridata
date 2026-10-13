import os

# Never send telemetry to a live Sentry DSN during tests. This runs before any
# test module imports app.main (which calls init_telemetry at import time), and
# load_dotenv(override=False) won't overwrite an already-set var, so init_telemetry
# sees an empty DSN and skips sentry_sdk.init entirely.
os.environ["SENTRY_DSN"] = ""
