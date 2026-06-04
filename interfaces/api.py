"""
DRS v3 API Gateway Shortcut — imports the modular FastAPI app from server/
"""
import sys
from pathlib import Path

# Ensure workspace root is in sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from server.main import app
