#!/usr/bin/env python3
"""Utility script to update a user's password directly in the database."""

import hashlib
import os
import sys
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+mysqlconnector://macmarket_user:MarketLLMftw2020Brentwood@localhost:3306/macmarket",
)

engine = create_engine(DATABASE_URL, future=True)


def update_password(user_id: int, new_password: str) -> None:
    """Hash the password and update the record."""
    hashed = hashlib.sha256(new_password.encode()).hexdigest()
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE users SET password_hash = :hash WHERE id = :id"),
            {"hash": hashed, "id": user_id},
        )


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python change_password.py <user_id> <new_password>")
        sys.exit(1)
    uid = int(sys.argv[1])
    pw = sys.argv[2]
    update_password(uid, pw)
    print(f"Password updated for user {uid}")
