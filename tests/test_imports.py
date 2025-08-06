# Test if imports work without circular dependency errors
try:
    from src.scribe.main import create_app
    print("Successfully imported create_app from main")
    
    from src.scribe.crew import crew
    print("Successfully imported crew")
    
    from src.scribe.ui.routes.reminder_routes import reminder_bp
    print("Successfully imported reminder_bp")
    
    print("All imports successful - circular dependency resolved!")
except ImportError as e:
    print(f"Import error: {e}")