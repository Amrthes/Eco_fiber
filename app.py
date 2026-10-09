"""Root application entrypoint for EcoFiber AI (compatible with Vercel and Streamlit)."""

import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "src"))

# Execute the main Streamlit dashboard
from dashboard.app import *
