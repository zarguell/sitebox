import os

# Shared API_KEY for all tests — set before any sitebox module is imported
os.environ.setdefault("API_KEY", "test-sitebox-key")
