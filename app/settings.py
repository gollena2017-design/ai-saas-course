from dotenv import load_dotenv
import os

load_dotenv()

# Threshold for switching to aggregated prompt mode.
# Can be overridden by environment variable AGGREGATE_TX_THRESHOLD.
try:
    AGGREGATE_TX_THRESHOLD = int(os.getenv("AGGREGATE_TX_THRESHOLD", "5"))
except ValueError:
    AGGREGATE_TX_THRESHOLD = 5
