"""
Test script for the EmailService's email validation functionality.
"""

from src.scribe.tools.email_service import EmailService

def test_email_validation():
    """Test the email validation functionality of the EmailService class."""
    email_service = EmailService()
    
    print("Testing email validation functionality of EmailService...")
    
    # Test 1: Validate a valid email address
    try:
        result = email_service._validate_email("test@example.com")
        print(f"Test 1: Validated 'test@example.com' as {result}")
        assert result == True, f"Expected True, got {result}"
    except Exception as e:
        print(f"Test 1 failed: {str(e)}")
    
    # Test 2: Validate another valid email address
    try:
        result = email_service._validate_email("user10@example.com")
        print(f"Test 2: Validated 'user10@example.com' as {result}")
        assert result == True, f"Expected True, got {result}"
    except Exception as e:
        print(f"Test 2 failed: {str(e)}")
    
    # Test 3: Validate an invalid email address (missing @)
    try:
        result = email_service._validate_email("invalid-email")
        print(f"Test 3: Validated 'invalid-email' as {result}")
        assert result == False, f"Expected False, got {result}"
    except Exception as e:
        print(f"Test 3 failed: {str(e)}")
    
    # Test 4: Validate an invalid email address (missing domain)
    try:
        result = email_service._validate_email("user@")
        print(f"Test 4: Validated 'user@' as {result}")
        assert result == False, f"Expected False, got {result}"
    except Exception as e:
        print(f"Test 4 failed: {str(e)}")

def test_run_method():
    """Test the _run method with email validation."""
    email_service = EmailService()
    
    print("\nTesting _run method with email validation...")
    
    # Test 1: Send to valid email addresses
    to = ["test@example.com", "user11@example.com"]
    result = email_service._run(action="send", to=to, subject="Test Subject", body="Test Body", dry_run=True)
    print(f"Test 1 result: {result}")
    
    # Test 2: Send to a mix of valid and invalid email addresses
    to = ["test@example.com", "invalid-email"]
    result = email_service._run(action="send", to=to, subject="Test Subject", body="Test Body", dry_run=True)
    print(f"Test 2 result: {result}")
    
    # Test 3: Send to an invalid email address
    to = ["user@"]
    result = email_service._run(action="send", to=to, subject="Test Subject", body="Test Body", dry_run=True)
    print(f"Test 3 result: {result}")

if __name__ == "__main__":
    test_email_validation()
    test_run_method()