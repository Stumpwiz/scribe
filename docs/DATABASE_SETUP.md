# Scribe Database Setup

## Overview

The `scribe` project shares a PostgreSQL database with the `clerk` project. Both projects access the same AWS RDS PostgreSQL instance, allowing scribe to read and work with the same data used by clerk.

## Database Details

- **Provider**: AWS RDS PostgreSQL 18.1
- **Host**: `database.example.com`
- **Port**: 5432
- **Database**: `clerk_community_admin`
- **User**: `clerk_user`
- **SSL Mode**: Required

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  the development host (192.0.2.10) - Development Server               │
│                                                               │
│  ┌──────────────────────┐    ┌──────────────────────┐       │
│  │  clerk Project       │    │  scribe Project      │       │
│  │  (/clerk)            │    │  (/scribe)           │       │
│  │                      │    │                      │       │
│  │  • FastAPI backend   │    │  • CrewAI agents     │       │
│  │  • Next.js frontend  │    │  • Email tools       │       │
│  │  • Defines models    │    │  • Imports models    │       │
│  └──────────┬───────────┘    └──────────┬───────────┘       │
│             │                           │                    │
│             └──────────┬────────────────┘                    │
└────────────────────────┼─────────────────────────────────────┘
                         │
                         │ SSL Connection
                         ▼
           ┌─────────────────────────────┐
           │   AWS RDS PostgreSQL        │
           │   (us-east-1)               │
           │                             │
           │   clerk_community_admin     │
           │   • bodies                  │
           │   • persons                 │
           │   • offices                 │
           │   • terms                   │
           │   • report_records          │
           │   • letter_templates        │
           │   • users                   │
           └─────────────────────────────┘
```

## Setup Steps Completed

### 1. Database Configuration

Added to `/path/to/projects/scribe/.env`:
```ini
DATABASE_URL=postgresql+psycopg2://clerk_user:password@database.example.com/clerk_community_admin?sslmode=require
```

### 2. Dependencies Updated

Added to `pyproject.toml`:
- `sqlalchemy>=2.0.0` - ORM for database access
- `alembic>=1.13.0` - Database migrations (managed by clerk)
- `pydantic-settings>=2.0.0` - Configuration management
- `psycopg2-binary>=2.9.11` - PostgreSQL driver (already present)

### 3. Database Module Created

Created `/path/to/projects/scribe/src/scribe/database.py`:
- Provides `get_db()` generator for session management
- Provides `get_db_session()` for direct session access
- Configured connection pooling for RDS

### 4. Model Sharing Setup

Created `/path/to/projects/scribe/src/scribe/clerk_models.py`:
- Imports clerk models while avoiding environment variable conflicts
- Exports all clerk SQLAlchemy models:
  - `Body` - Governance bodies (committees)
  - `Person` - Council members and residents
  - `Office` - Leadership positions within bodies
  - `Term` - Person assignments to offices with dates
  - `ReportRecord` - Meeting report metadata
  - `LetterTemplate` - Letter generation templates
  - `User` - Authentication users

### 5. Clerk Backend Configuration

Modified `/path/to/projects/clerk/backend/app/config.py`:
- Added `extra = 'ignore'` to allow sharing environment between projects
- Prevents validation errors when both .env files are loaded

## Usage in Scribe

### Basic Query Example

```python
from scribe.database import get_db_session
from scribe.clerk_models import Body, Office

# Get a database session
db = get_db_session()

try:
    # Query all governance bodies
    bodies = db.query(Body).all()

    for body in bodies:
        print(f"Body: {body.name}")

        # Get offices for this body
        offices = db.query(Office).filter(
            Office.office_body_id == body.body_id
        ).all()

        for office in offices:
            print(f"  - {office.title}")

finally:
    db.close()
```

### Using Context Manager

```python
from scribe.database import get_db
from scribe.clerk_models import Person

# Use with context manager
for db in get_db():
    persons = db.query(Person).filter(
        Person.person_status == 'Active'
    ).all()

    print(f"Found {len(persons)} active persons")
```

## Testing

Run the test script to verify database connectivity:

```bash
cd /path/to/projects/scribe
.venv/bin/python test_db_connection.py
```

Expected output:
```
============================================================
Scribe Database Connection Test
============================================================
Testing database connection...
✓ Connection successful!
  PostgreSQL version: PostgreSQL 18.1 on aarch64-unknown-linux-gnu...

Testing model queries...
  ✓ Bodies: 13 records
  ✓ Persons: 137 records
  ✓ Offices: 104 records
  ✓ Terms: 171 records
  ✓ Report Records: 171 records
  ✓ Letter Templates: 1 records
  ✓ Users: 0 records

✓ All models accessible!

Testing complex query (Bodies with their Offices)...
  Found 5 bodies:
    - Building Maintenance
      Offices: 7
    ...

✓ Complex query successful!
============================================================
✅ All tests passed! Scribe can access the clerk database.
============================================================
```

## Database Schema

The database contains the following main tables:

### Core Tables

- **body** - Governance bodies/committees
  - `body_id` (PK)
  - `name`
  - `body_type`
  - `body_precedence`

- **person** - Council members and residents
  - `person_id` (PK)
  - `last_name`, `first_name`, `middle_name`
  - `address_1`, `apt_number`
  - `email`, `telephone`
  - `person_status` (Active, Inactive, Deceased)

- **office** - Leadership positions
  - `office_id` (PK)
  - `title`
  - `office_body_id` (FK → body)
  - `office_precedence`

- **term** - Person assignments to offices
  - `term_id` (PK)
  - `term_body_id` (FK → body)
  - `term_office_id` (FK → office)
  - `term_person_id` (FK → person)
  - `start_date`, `end_date`
  - `appointment_date`

- **report_record** - Meeting report metadata
  - `report_id` (PK)
  - `report_body_id` (FK → body)
  - `report_period_start`, `report_period_end`
  - `report_meeting_date`

- **letter_template** - Letter generation templates
  - `template_id` (PK)
  - `name`, `template_text`

- **user** - Authentication users
  - `id` (PK)
  - `clerk_user_id`
  - `email`
  - `created_at`

## CI/CD Considerations

### Development (the development host)
- Both projects connect directly to AWS RDS
- No local PostgreSQL needed
- Use the same DATABASE_URL in both projects

### Production (AWS)
- Both applications will connect to the same RDS instance
- Ensure AWS security groups allow:
  - App Runner services → RDS (port 5432)
  - Lambda functions → RDS (if using serverless)
- Use AWS Secrets Manager for database credentials in production

### Migrations
- **IMPORTANT**: Database migrations are managed by the `clerk` project only
- Run migrations from clerk backend: `cd backend && alembic upgrade head`
- Scribe should NOT modify schema, only read/write data using existing models
- When clerk schema changes, scribe automatically gets the updates via shared models

## Security Notes

1. **Read/Write Access**: Scribe uses the same `clerk_user` credentials with full access
2. **SSL Required**: All connections must use SSL (enforced by `sslmode=require`)
3. **No Local PostgreSQL**: Database runs on AWS RDS, not locally on the development host
4. **Credentials**: Stored in `.env` files (not committed to git)

## Troubleshooting

### Connection Timeout
- Check the development host's internet connection
- Verify AWS RDS security group allows inbound from the development host's IP: `192.0.2.10`
- Test with: `psql "postgresql://clerk_user:password@database.example.com/clerk_community_admin?sslmode=require"`

### Import Errors
- Ensure scribe virtual environment is activated: `source .venv/bin/activate`
- Verify clerk-backend package is installed: `pip list | grep clerk-backend`
- Reinstall if needed: `pip install -e /path/to/projects/clerk/backend`

### Pydantic Validation Errors
- The clerk config now ignores extra environment variables with `extra = 'ignore'`
- If errors persist, check both .env files don't have conflicting variable names

## Next Steps

1. **Create Scribe Database Tools**: Build CrewAI tools that query the database
2. **Add Report Parsing**: Link email reports to `report_record` table
3. **Person Lookup**: Match email senders to `person` records
4. **Term Queries**: Find current committee members and chairs
5. **Consider Read-Only User**: Create a separate database user with SELECT-only permissions for scribe if write access isn't needed

## Related Documentation

- Clerk database migration docs: `/path/to/projects/clerk/docs/database-migration-complete.md`
- Clerk backup/restore guide: `/path/to/projects/clerk/docs/backup-and-restore-guide.md`
- Scribe project README: `/path/to/projects/scribe/README.md`
