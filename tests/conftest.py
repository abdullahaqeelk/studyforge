"""
Pytest configuration shared by every test module.

The project's modules live in src/ and import each other by plain module name
(`from config import ...`), which works when a script is run directly from that
directory. Pytest runs from the repository root instead, so src/ is added to
the import path here rather than in each test file.
"""

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
