#!/usr/bin/env python3
"""
Test script for DatabaseQueryTool

Tests the database query tool methods with real data from the AWS RDS database.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from scribe.tools.database_query_tool import DatabaseQueryTool


def test_council_officers():
    """Test getting council officer email addresses."""
    print("=" * 60)
    print("TEST: get_council_officers()")
    print("=" * 60)

    tool = DatabaseQueryTool()
    emails = tool.get_council_officers()

    print(f"\nFound {len(emails)} council officer email addresses:")
    for email in emails:
        print(f"  - {email}")

    return emails


def test_committee_chairs():
    """Test getting committee chair email addresses."""
    print("\n" + "=" * 60)
    print("TEST: get_committee_chairs()")
    print("=" * 60)

    tool = DatabaseQueryTool()
    emails = tool.get_committee_chairs()

    print(f"\nFound {len(emails)} committee chair email addresses:")
    for email in emails:
        print(f"  - {email}")

    return emails


def test_all_committees():
    """Test getting list of all committees."""
    print("\n" + "=" * 60)
    print("TEST: get_all_committees()")
    print("=" * 60)

    tool = DatabaseQueryTool()
    committees = tool.get_all_committees()

    print(f"\nFound {len(committees)} committees:")
    for committee in committees:
        print(f"  - {committee['name']}")
        if committee.get('mission'):
            print(f"    {committee['mission']}")

    return committees


def test_committee_members(committee_name):
    """Test getting members of a specific committee."""
    print("\n" + "=" * 60)
    print(f"TEST: get_committee_members('{committee_name}')")
    print("=" * 60)

    tool = DatabaseQueryTool()
    members = tool.get_committee_members(committee_name)

    print(f"\nFound {len(members)} members:")
    for member in members:
        print(f"  - {member['name']} ({member['office_title']})")
        print(f"    Email: {member['email'] or 'N/A'}")

    return members


def test_person_by_email(email):
    """Test looking up a person by email address."""
    print("\n" + "=" * 60)
    print(f"TEST: get_person_by_email('{email}')")
    print("=" * 60)

    tool = DatabaseQueryTool()
    person = tool.get_person_by_email(email)

    if person:
        print("\nPerson found:")
        print(f"  Name: {person['full_name']}")
        print(f"  Email: {person['email']}")
        print(f"  Phone: {person['phone'] or 'N/A'}")
        print(f"  Unit: {person['unit_number'] or 'N/A'}")
    else:
        print(f"\nNo person found with email '{email}'")

    return person


def compare_with_static_json():
    """Compare database results with static JSON files."""
    print("\n" + "=" * 60)
    print("COMPARISON: Database vs Static JSON Files")
    print("=" * 60)

    import json
    from pathlib import Path

    # Load static JSON files
    recipients_dir = Path(__file__).parent / "src" / "scribe" / "assets" / "recipients"

    with open(recipients_dir / "council_members.json") as f:
        static_officers = set(json.load(f))

    with open(recipients_dir / "committee_chairs.json") as f:
        static_chairs = set(json.load(f))

    # Get database results
    tool = DatabaseQueryTool()
    db_officers = set(tool.get_council_officers())
    db_chairs = set(tool.get_committee_chairs())

    print("\n📋 Council Officers:")
    print(f"  Static JSON: {len(static_officers)} emails")
    print(f"  Database:    {len(db_officers)} emails")

    if static_officers == db_officers:
        print("  ✅ MATCH - Same email addresses")
    else:
        print("  ⚠️  DIFFERENCE detected:")
        only_in_static = static_officers - db_officers
        only_in_db = db_officers - static_officers

        if only_in_static:
            print(f"    Only in static JSON: {only_in_static}")
        if only_in_db:
            print(f"    Only in database: {only_in_db}")

    print("\n📋 Committee Chairs:")
    print(f"  Static JSON: {len(static_chairs)} emails")
    print(f"  Database:    {len(db_chairs)} emails")

    if static_chairs == db_chairs:
        print("  ✅ MATCH - Same email addresses")
    else:
        print("  ⚠️  DIFFERENCE detected:")
        only_in_static = static_chairs - db_chairs
        only_in_db = db_chairs - static_chairs

        if only_in_static:
            print(f"    Only in static JSON: {only_in_static}")
        if only_in_db:
            print(f"    Only in database: {only_in_db}")


def main():
    """Run all tests."""
    print("🔍 Testing DatabaseQueryTool with real data\n")

    try:
        # Test 1: Council officers
        officers = test_council_officers()

        # Test 2: Committee chairs
        chairs = test_committee_chairs()

        # Test 3: All committees
        committees = test_all_committees()

        # Test 4: Committee members (if we found any committees)
        if committees:
            test_committee_members(committees[0]['name'])

        # Test 5: Person lookup (if we found any officers)
        if officers:
            test_person_by_email(officers[0])

        # Test 6: Compare with static JSON
        compare_with_static_json()

        print("\n" + "=" * 60)
        print("✅ ALL TESTS COMPLETED")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
