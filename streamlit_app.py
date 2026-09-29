"""Streamlit Community Cloud entry point."""

from pathlib import Path
import runpy
import sys


PROJECT_DIR = Path(__file__).resolve().parent / "job-agent"
sys.path.insert(0, str(PROJECT_DIR))
runpy.run_path(str(PROJECT_DIR / "app" / "streamlit_app.py"), run_name="__main__")
