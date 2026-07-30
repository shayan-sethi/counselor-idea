import argparse
import json
import os
import secrets

import firebase_admin
from firebase_admin import credentials, firestore
from firebase_admin import auth as firebase_auth

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SYNTHETIC_EMAIL_DOMAIN = "unlocked.local"

# username(lowercased) -> known demo password, from login.html's own hint text
KNOWN_DEMO_PASSWORDS = {
    "admin": "admin123",
    "counselor": "counselor123",
}


def load_env():
    env_path = os.path.join(BASE_DIR, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip().strip('"').strip("'")


def password_for(username, password_hash):
    import hashlib
    lower = username.lower()
    if lower in KNOWN_DEMO_PASSWORDS:
        return KNOWN_DEMO_PASSWORDS[lower], True
    if lower.startswith("stu_") and hashlib.sha256(b"student123").hexdigest() == password_hash:
        return "student123", True
    return secrets.token_urlsafe(12), False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing to Firestore/Auth")
    args = parser.parse_args()

    load_env()

    key_path = os.environ.get("FIREBASE_SERVICE_ACCOUNT_PATH", "secrets/firebase-service-account.json")
    if not os.path.isabs(key_path):
        key_path = os.path.join(BASE_DIR, key_path)

    with open(os.path.join(BASE_DIR, "data", "students_db.json")) as f:
        students = json.load(f)
    with open(os.path.join(BASE_DIR, "data", "users_db.json")) as f:
        users = json.load(f)

    print(f"Loaded {len(students)} students and {len(users)} users from JSON.")

    plan = []
    for u in users:
        pw, known = password_for(u["username"], u["password_hash"])
        plan.append((u, pw, known))

    if args.dry_run:
        print("--dry-run: no writes performed.")
        print(f"Would write students collection: {[s['id'] for s in students]}")
        for u, pw, known in plan:
            print(f"Would create Auth user uid={u['username']!r} role={u['role']} known_password={known}")
        return

    firebase_admin.initialize_app(credentials.Certificate(key_path))
    db = firestore.client()

    # Students: straight bulk write (Phase 1 already covers this; safe to re-run/idempotent)
    batch = db.batch()
    for s in students:
        batch.set(db.collection("students").document(s["id"]), s)
    batch.commit()
    print(f"Wrote {len(students)} student docs to Firestore.")

    needs_reset = []
    for u, pw, known in plan:
        username = u["username"]
        try:
            firebase_auth.create_user(
                uid=username,
                email=f"{username}@{SYNTHETIC_EMAIL_DOMAIN}",
                password=pw,
            )
        except firebase_auth.UidAlreadyExistsError:
            print(f"  [skip] Auth user already exists: {username}")
            continue

        firebase_auth.set_custom_user_claims(username, {
            "role": u["role"],
            "student_id": u.get("student_id"),
        })
        db.collection("users").document(username).set({
            "username": username,
            "role": u["role"],
            "student_id": u.get("student_id"),
        })
        print(f"  [ok] Created Auth user + Firestore doc: {username} (role={u['role']})")
        if not known:
            needs_reset.append(username)

    print(f"\nDone. {len(plan)} accounts processed.")
    if needs_reset:
        print("\nThese accounts got a RANDOM password (original was unrecoverable from its hash).")
        print("Reset them via the admin panel before anyone tries to log in as these users:")
        for username in needs_reset:
            print(f"  - {username}")


if __name__ == "__main__":
    main()
