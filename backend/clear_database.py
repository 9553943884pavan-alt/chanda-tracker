"""
Script to delete specific users and all their associated data.
Run with: .venv\\Scripts\\activate; python clear_database.py
"""

import asyncio
import sys
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sqlalchemy import text
from database import engine


# Names of users to delete (case-insensitive partial match)
USERS_TO_DELETE = ["pavan", "srivardhan", "adwith"]


async def delete_users():
    """Find and delete specific users and all their related data."""

    async with engine.begin() as conn:
        # Find users by name (case-insensitive)
        user_ids = []
        for name in USERS_TO_DELETE:
            result = await conn.execute(
                text("SELECT id, full_name, email, role FROM users WHERE full_name ILIKE :name"),
                {"name": f"%{name}%"}
            )
            found = result.fetchall()
            if found:
                for user in found:
                    user_ids.append(user[0])
                    print(f"Found user: {user[1]} ({user[2]}) - Role: {user[3]}")
            else:
                print(f"⚠ No user found matching: '{name}'")

        if not user_ids:
            print("\n❌ No matching users found. Nothing to delete.")
            return

        # Delete related data in correct order (respecting foreign keys)

        # 1. Delete payments where user is giver or collector or verified_by
        result = await conn.execute(
            text("""
                DELETE FROM payments 
                WHERE giver_id = ANY(:user_ids) 
                   OR collector_id = ANY(:user_ids) 
                   OR verified_by = ANY(:user_ids)
                RETURNING id
            """),
            {"user_ids": user_ids}
        )
        payments_deleted = result.rowcount
        print(f"\n✓ Deleted {payments_deleted} payment(s)")

        # 2. Delete broadcasts sent by these users
        result = await conn.execute(
            text("DELETE FROM broadcasts WHERE sent_by = ANY(:user_ids) RETURNING id"),
            {"user_ids": user_ids}
        )
        broadcasts_deleted = result.rowcount
        print(f"✓ Deleted {broadcasts_deleted} broadcast(s)")

        # 3. Delete collector profiles for these users
        result = await conn.execute(
            text("DELETE FROM collector_profiles WHERE user_id = ANY(:user_ids) RETURNING user_id"),
            {"user_ids": user_ids}
        )
        profiles_deleted = result.rowcount
        print(f"✓ Deleted {profiles_deleted} collector profile(s)")

        # 4. Delete OTP codes for these users' emails
        # First get the emails
        result = await conn.execute(
            text("SELECT email FROM users WHERE id = ANY(:user_ids)"),
            {"user_ids": user_ids}
        )
        user_emails = [row[0] for row in result.fetchall()]

        if user_emails:
            result = await conn.execute(
                text("DELETE FROM otp_codes WHERE email = ANY(:emails) RETURNING id"),
                {"emails": user_emails}
            )
            otps_deleted = result.rowcount
            print(f"✓ Deleted {otps_deleted} OTP code(s)")

        # 5. Finally delete the users themselves
        result = await conn.execute(
            text("DELETE FROM users WHERE id = ANY(:user_ids) RETURNING id"),
            {"user_ids": user_ids}
        )
        users_deleted = result.rowcount
        print(f"✓ Deleted {users_deleted} user(s)")

        print("\n✅ Successfully deleted all data for the specified users!")


if __name__ == "__main__":
    asyncio.run(delete_users())
