#!/usr/bin/env python3
"""Create admin user for Brand2Context."""
import os, sys, sqlite3, uuid, bcrypt
from datetime import datetime, timezone

DB_PATH = os.getenv("DATABASE_URL", "sqlite:///data/brand2context.db").replace("sqlite:///", "")

def main():
    if not os.path.exists(DB_PATH):
        print(f"DB not found at {DB_PATH}, creating...")
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Create users table if not exists
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_admin BOOLEAN DEFAULT 0
    )""")
    
    # Add progress_step column to brands if not exists
    try:
        c.execute("ALTER TABLE brands ADD COLUMN progress_step TEXT DEFAULT 'pending'")
        print("Added progress_step column to brands table")
    except:
        pass  # column already exists
    
    email = "admin@brand2context.com"
    password = "B2C@admin2026!"
    name = "Admin"
    
    # Check if exists
    existing = c.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if existing:
        print(f"Admin user already exists: {email}")
        conn.close()
        return
    
    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    user_id = str(uuid.uuid4())
    
    c.execute(
        "INSERT INTO users (id, email, password_hash, name, created_at, is_admin) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, email, pw_hash, name, datetime.now(timezone.utc).isoformat(), 1)
    )
    conn.commit()
    conn.close()
    
    print(f"✅ Admin user created:")
    print(f"   Email: {email}")
    print(f"   Password: {password}")
    print(f"   ID: {user_id}")

if __name__ == "__main__":
    main()
