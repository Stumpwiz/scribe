# Simple test to check if the main module can be imported
try:
    import src.scribe.main
    print("Successfully imported src.scribe.main - circular dependency resolved!")
except ImportError as e:
    print(f"Import error: {e}")