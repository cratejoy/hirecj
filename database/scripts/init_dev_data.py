#!/usr/bin/env python3
"""Initialize development data for testing."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.database.utils import create_account, create_user, init_database, create_tables


async def init_dev_data():
    """Initialize development data."""
    print("Initializing database...")
    init_database()
    
    print("Creating tables...")
    create_tables()
    
    print("Creating test account...")
    account = await create_account(
        name="Acme Corp",
        slug="acme-corp"
    )
    print(f"  Created account: {account.name} ({account.id})")
    
    print("Creating test user...")
    user = await create_user(
        account_id=account.id,
        email="admin@acme.com",
        name="Admin User",
        role="admin"
    )
    print(f"  Created user: {user.name} ({user.email})")
    
    print("\n✅ Development data initialized!")
    print(f"   Account ID: {account.id}")
    print(f"   User Email: {user.email}")


if __name__ == "__main__":
    asyncio.run(init_dev_data())