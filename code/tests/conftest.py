"""
Pytest configuration ensuring code directory is in sys.path.
"""

import os
import sys

CODE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if CODE_DIR not in sys.path:
    sys.path.insert(0, CODE_DIR)
