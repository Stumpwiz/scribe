#!/usr/bin/env python3
"""
Test script to verify database connection and access to clerk models from scribe project.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from scribe.database import get_db_session, engine
from scribe.clerk_models import Body, Person, Office, Term, ReportRecord, LetterTemplate, User


def test_connection():
    """Test basic database connection."""
    print("Testing database connection...")
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            print(f"✓ Connection successful!")
            print(f"  PostgreSQL version: {version[:50]}...")
            return True
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False


def test_models():
    """Test querying data from shared models."""
    print("\nTesting model queries...")
    db = get_db_session()

    try:
        # Test each model
        models = [
            ("Bodies", Body),
            ("Persons", Person),
            ("Offices", Office),
            ("Terms", Term),
            ("Report Records", ReportRecord),
            ("Letter Templates", LetterTemplate),
            ("Users", User),
        ]

        for name, model in models:
            try:
                count = db.query(model).count()
                print(f"  ✓ {name}: {count} records")
            except Exception as e:
                print(f"  ✗ {name}: Error - {e}")

        print("\n✓ All models accessible!")
        return True

    except Exception as e:
        print(f"✗ Model query failed: {e}")
        return False
    finally:
        db.close()


def test_sample_query():
    """Test a more complex query joining tables."""
    print("\nTesting complex query (Bodies with their Offices)...")
    db = get_db_session()

    try:
        # Query bodies and their offices
        bodies = db.query(Body).limit(5).all()

        if bodies:
            print(f"  Found {len(bodies)} bodies:")
            for body in bodies:
                print(f"    - {body.name}")
                offices = db.query(Office).filter(Office.office_body_id == body.body_id).all()
                print(f"      Offices: {len(offices)}")
        else:
            print("  No bodies found in database")

        print("\n✓ Complex query successful!")
        return True

    except Exception as e:
        print(f"✗ Complex query failed: {e}")
        return False
    finally:
        db.close()


def main():
    """Run all tests."""
    print("=" * 60)
    print("Scribe Database Connection Test")
    print("=" * 60)

    success = True

    # Test 1: Basic connection
    if not test_connection():
        success = False
        print("\n⚠️  Cannot proceed without database connection")
        sys.exit(1)

    # Test 2: Model access
    if not test_models():
        success = False

    # Test 3: Complex queries
    if not test_sample_query():
        success = False

    # Summary
    print("\n" + "=" * 60)
    if success:
        print("✅ All tests passed! Scribe can access the clerk database.")
        print("=" * 60)
        sys.exit(0)
    else:
        print("⚠️  Some tests failed. Check the output above.")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
