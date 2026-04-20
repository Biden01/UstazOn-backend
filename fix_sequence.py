#!/usr/bin/env python3
"""
Fix PostgreSQL sequence for users table ID column.

This script resets the sequence to the correct value based on the maximum ID
currently in the users table. Run this after migrations that insert users
with explicit IDs.

Usage:
    python fix_sequence.py
"""
import asyncio
import sys
from sqlalchemy import text
from src.db.session import async_session_maker


async def fix_users_sequence():
    """Reset the users_id_seq sequence to match the maximum ID in the table."""
    async with async_session_maker() as session:
        try:
            # Get the current maximum ID from the users table
            result = await session.execute(
                text("SELECT MAX(id) FROM users")
            )
            max_id = result.scalar()

            if max_id is None:
                print("No users found in the table. Sequence is likely correct.")
                return

            print(f"Maximum user ID found: {max_id}")

            # Reset the sequence to start from max_id + 1
            await session.execute(
                text(f"SELECT setval('users_id_seq', {max_id}, true)")
            )
            await session.commit()

            # Verify the fix
            result = await session.execute(
                text("SELECT last_value FROM users_id_seq")
            )
            last_value = result.scalar()

            print(f"✓ Sequence successfully reset!")
            print(f"  Current sequence value: {last_value}")
            print(f"  Next ID will be: {last_value + 1}")

        except Exception as e:
            print(f"✗ Error fixing sequence: {e}")
            await session.rollback()
            sys.exit(1)


async def main():
    """Main entry point."""
    print("=" * 60)
    print("PostgreSQL Sequence Fix for users table")
    print("=" * 60)
    print()

    await fix_users_sequence()

    print()
    print("=" * 60)
    print("Done! You can now create new users without conflicts.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
