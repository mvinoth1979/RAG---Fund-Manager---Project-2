import sys
import os
from pathlib import Path

# Add project root to path so internal imports work
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

# Import the FastAPI app from the delivery phase
from phase_6_response_delivery.api import app

# Vercel needs the 'app' variable to be the entry point
# No changes needed if 'app' is the FastAPI instance
