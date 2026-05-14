import os
import sys

# Point at the real indexed data so these are true integration tests
DB_DIR = os.path.join(os.path.dirname(__file__), "..", "mcp-server", "data")
os.environ["DB_DIR"] = os.path.abspath(DB_DIR)

# Make mcp-server importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-server"))
