#!/usr/bin/env python3
"""
Sync missing records from old Django SQLite DB to new FastAPI PostgreSQL DB.

Usage:
    python scripts/sync_from_sqlite.py

Connects to:
    - SQLite: /var/UstazOn/UstazOn/db.sqlite3 (read-only)
    - PostgreSQL: localhost:5432/ustazon (sync driver)
"""

import sqlite3
from datetime import datetime, timezone

import psycopg2
from psycopg2.extras import execute_values

SQLITE_PATH = "/var/UstazOn/UstazOn/db.sqlite3"
PG_DSN = "postgresql://postgres:hcAPWlSXOVMXYUcH36SkDAio9tmwWT3@localhost:5432/ustazon"

NOW = datetime.now(timezone.utc)


def get_sqlite_conn():
    conn = sqlite3.connect(f"file:{SQLITE_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def get_pg_conn():
    return psycopg2.connect(PG_DSN)


def get_existing_ids(pg_cur, table: str) -> set:
    pg_cur.execute(f"SELECT id FROM {table}")
    return {row[0] for row in pg_cur.fetchall()}


def safe_int(val, default=None):
    """Convert text to int, handling empty strings and non-numeric values."""
    if val is None or val == "":
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def sync_users(sq_conn, pg_conn):
    print("\n=== Syncing USERS ===")
    sq_cur = sq_conn.cursor()
    pg_cur = pg_conn.cursor()

    existing = get_existing_ids(pg_cur, "users")

    # Get existing phones and IINs to avoid unique constraint violations
    pg_cur.execute("SELECT phone FROM users WHERE phone IS NOT NULL")
    existing_phones = {row[0] for row in pg_cur.fetchall()}
    pg_cur.execute("SELECT iin FROM users WHERE iin IS NOT NULL")
    existing_iins = {row[0] for row in pg_cur.fetchall()}

    sq_cur.execute("SELECT * FROM AuthPage_user")
    rows = sq_cur.fetchall()

    to_insert = []
    skipped_iin = 0
    for r in rows:
        if r["id"] in existing:
            continue
        iin = r["username"]
        if iin in existing_iins:
            skipped_iin += 1
            continue

        phone = r["phone"] or "unknown"
        # Deduplicate phone: if already exists, use id as placeholder
        if phone in existing_phones:
            phone = f"dup_{r['id']}"
        existing_phones.add(phone)
        existing_iins.add(iin)

        to_insert.append((
            r["id"],
            iin,
            r["name"] or "",
            phone,
            r["password"],           # hashed_password (Django format)
            r["email"] or None,
            r["avatar"] or None,
            bool(r["is_active"]),
            False,                   # is_verified
            bool(r["is_staff"]),     # is_admin
            bool(r["is_superuser"]),
            r["date_joined"] or NOW.isoformat(),
            r["date_joined"] or NOW.isoformat(),
        ))

    if skipped_iin:
        print(f"  Skipped {skipped_iin} users (IIN already exists).")

    if not to_insert:
        print("  No missing users to insert.")
        return

    execute_values(
        pg_cur,
        """INSERT INTO users (id, iin, name, phone, hashed_password, email, avatar,
                              is_active, is_verified, is_admin, is_superuser,
                              created_at, updated_at)
           VALUES %s ON CONFLICT (id) DO NOTHING""",
        to_insert,
    )
    pg_conn.commit()
    print(f"  Inserted {len(to_insert)} users.")


def sync_windows(sq_conn, pg_conn):
    print("\n=== Syncing WINDOWS ===")
    sq_cur = sq_conn.cursor()
    pg_cur = pg_conn.cursor()

    existing = get_existing_ids(pg_cur, "windows")
    sq_cur.execute("SELECT * FROM TemplatesPage_window")
    rows = sq_cur.fetchall()

    to_insert = []
    for r in rows:
        if r["id"] in existing:
            continue
        to_insert.append((
            r["id"],
            r["name"],
            r["template_id"],
            r["link"] or None,
            bool(r["nsub"]),
            r["image_url"] or None,
            r["image"] or None,     # image -> image_file
            NOW,
        ))

    if not to_insert:
        print("  No missing windows.")
        return

    execute_values(
        pg_cur,
        """INSERT INTO windows (id, name, template_id, link, nsub, image_url, image_file, created_at)
           VALUES %s ON CONFLICT (id) DO NOTHING""",
        to_insert,
    )
    pg_conn.commit()
    print(f"  Inserted {len(to_insert)} windows.")


def sync_card_topics(sq_conn, pg_conn):
    print("\n=== Syncing CARD_TOPICS ===")
    sq_cur = sq_conn.cursor()
    pg_cur = pg_conn.cursor()

    existing = get_existing_ids(pg_cur, "card_topics")
    sq_cur.execute("SELECT * FROM MaterialsPage_cardtopic")
    rows = sq_cur.fetchall()

    to_insert = []
    for r in rows:
        if r["id"] in existing:
            continue
        to_insert.append((
            r["id"],
            r["topic"],
            None,    # parent_topic_id
            NOW,
        ))

    if not to_insert:
        print("  No missing card_topics.")
        return

    execute_values(
        pg_cur,
        """INSERT INTO card_topics (id, topic, parent_topic_id, created_at)
           VALUES %s ON CONFLICT (id) DO NOTHING""",
        to_insert,
    )
    pg_conn.commit()
    print(f"  Inserted {len(to_insert)} card_topics.")


def sync_cards(sq_conn, pg_conn):
    print("\n=== Syncing CARDS ===")
    sq_cur = sq_conn.cursor()
    pg_cur = pg_conn.cursor()

    existing = get_existing_ids(pg_cur, "cards")
    sq_cur.execute("SELECT * FROM MaterialsPage_card")
    rows = sq_cur.fetchall()

    to_insert = []
    for r in rows:
        if r["id"] in existing:
            continue
        to_insert.append((
            r["id"],
            r["author_id"],
            r["name"],
            r["description"] or None,
            r["grade"],
            r["quarter"],
            r["topic_id"],
            r["window_id"],
            r["subject_card"] or None,
            r["file"] or None,           # file -> file_path
            r["url"] or None,
            bool(r["iframe"]),
            r["img1_url"] or None,
            r["img2"] or None,           # img2 -> img2_url
            r["img3"] or None,           # img3 -> img3_url
            r["img4"] or None,           # img4 -> img4_url
            r["img5"] or None,           # img5 -> img5_url
            r["video1_url"] or None,
            r["video1_file"] or None,    # video1_file -> video1_file_path
            r["created_at"] or NOW.isoformat(),
            NOW,
        ))

    if not to_insert:
        print("  No missing cards.")
        return

    execute_values(
        pg_cur,
        """INSERT INTO cards (id, author_id, name, description, grade, quarter,
                              topic_id, window_id, subject_card, file_path, url, iframe,
                              img1_url, img2_url, img3_url, img4_url, img5_url,
                              video1_url, video1_file_path, created_at, updated_at)
           VALUES %s ON CONFLICT (id) DO NOTHING""",
        to_insert,
    )
    pg_conn.commit()
    print(f"  Inserted {len(to_insert)} cards.")


def sync_m2m(sq_conn, pg_conn, sq_table, pg_table, sq_cols, pg_cols):
    """Generic M2M sync. sq_cols and pg_cols are tuples of column names."""
    print(f"\n=== Syncing {pg_table} ===")
    sq_cur = sq_conn.cursor()
    pg_cur = pg_conn.cursor()

    col_select = ", ".join(sq_cols)
    sq_cur.execute(f"SELECT {col_select} FROM {sq_table}")
    sq_rows = {tuple(r) for r in sq_cur.fetchall()}

    pg_col_select = ", ".join(pg_cols)
    pg_cur.execute(f"SELECT {pg_col_select} FROM {pg_table}")
    pg_rows = {tuple(r) for r in pg_cur.fetchall()}

    # Map SQLite column order to PG column order (for renamed cols)
    to_insert = list(sq_rows - pg_rows)

    if not to_insert:
        print(f"  No missing {pg_table}.")
        return

    placeholders = ", ".join(["%s"] * len(pg_cols))
    col_list = ", ".join(pg_cols)
    query = f"INSERT INTO {pg_table} ({col_list}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"

    pg_cur.executemany(query, to_insert)
    pg_conn.commit()
    print(f"  Inserted {len(to_insert)} rows into {pg_table}.")


def sync_card_m2m(sq_conn, pg_conn):
    # card_subject: same column names
    sync_m2m(sq_conn, pg_conn,
             "MaterialsPage_card_subject", "card_subject",
             ("card_id", "subject_id"), ("card_id", "subject_id"))

    # card_institution_type: institutiontype_id -> institution_type_id
    print(f"\n=== Syncing card_institution_type ===")
    sq_cur = sq_conn.cursor()
    pg_cur = pg_conn.cursor()

    sq_cur.execute("SELECT card_id, institutiontype_id FROM MaterialsPage_card_institution_type")
    sq_rows = {(r[0], r[1]) for r in sq_cur.fetchall()}

    pg_cur.execute("SELECT card_id, institution_type_id FROM card_institution_type")
    pg_rows = {(r[0], r[1]) for r in pg_cur.fetchall()}

    to_insert = list(sq_rows - pg_rows)
    if not to_insert:
        print("  No missing card_institution_type.")
    else:
        pg_cur.executemany(
            "INSERT INTO card_institution_type (card_id, institution_type_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            to_insert,
        )
        pg_conn.commit()
        print(f"  Inserted {len(to_insert)} rows.")

    # card_favorites — filter out references to missing cards/users
    print(f"\n=== Syncing card_favorites ===")
    existing_cards = get_existing_ids(pg_cur, "cards")
    existing_users = get_existing_ids(pg_cur, "users")

    sq_cur.execute("SELECT card_id, user_id FROM MaterialsPage_card_favorites")
    sq_rows = {(r[0], r[1]) for r in sq_cur.fetchall()}

    pg_cur.execute("SELECT card_id, user_id FROM card_favorites")
    pg_rows = {(r[0], r[1]) for r in pg_cur.fetchall()}

    to_insert = [(c, u) for c, u in (sq_rows - pg_rows)
                 if c in existing_cards and u in existing_users]
    if not to_insert:
        print("  No missing card_favorites.")
    else:
        pg_cur.executemany(
            "INSERT INTO card_favorites (card_id, user_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            to_insert,
        )
        pg_conn.commit()
        print(f"  Inserted {len(to_insert)} rows.")


def sync_qmj(sq_conn, pg_conn):
    print("\n=== Syncing QMJ ===")
    sq_cur = sq_conn.cursor()
    pg_cur = pg_conn.cursor()

    existing = get_existing_ids(pg_cur, "qmj")
    sq_cur.execute("SELECT * FROM QmjPage_qmj")
    rows = sq_cur.fetchall()

    to_insert = []
    for r in rows:
        if r["id"] in existing:
            continue
        to_insert.append((
            r["id"],
            safe_int(r["grade"]),
            safe_int(r["quarter"]),
            r["code"] or None,
            r["title"],
            r["text"] or None,
            safe_int(r["hour"], default=1),
            r["order"] if r["order"] is not None else 0,
            r["file"] or None,
            r["author_id"],
            r["created_at"] or NOW.isoformat(),
            r["updated_at"] or NOW.isoformat(),
        ))

    if not to_insert:
        print("  No missing qmj.")
        return

    execute_values(
        pg_cur,
        """INSERT INTO qmj (id, grade, quarter, code, title, text, hour, "order",
                            file, author_id, created_at, updated_at)
           VALUES %s ON CONFLICT (id) DO NOTHING""",
        to_insert,
    )
    pg_conn.commit()
    print(f"  Inserted {len(to_insert)} qmj records.")


def sync_qmj_m2m(sq_conn, pg_conn):
    # qmj_subjects
    sync_m2m(sq_conn, pg_conn,
             "QmjPage_qmj_subject", "qmj_subjects",
             ("qmj_id", "subject_id"), ("qmj_id", "subject_id"))

    # qmj_institution_types: institutiontype_id -> institution_type_id
    print(f"\n=== Syncing qmj_institution_types ===")
    sq_cur = sq_conn.cursor()
    pg_cur = pg_conn.cursor()

    sq_cur.execute("SELECT qmj_id, institutiontype_id FROM QmjPage_qmj_institution_type")
    sq_rows = {(r[0], r[1]) for r in sq_cur.fetchall()}

    pg_cur.execute("SELECT qmj_id, institution_type_id FROM qmj_institution_types")
    pg_rows = {(r[0], r[1]) for r in pg_cur.fetchall()}

    to_insert = list(sq_rows - pg_rows)
    if not to_insert:
        print("  No missing qmj_institution_types.")
    else:
        pg_cur.executemany(
            "INSERT INTO qmj_institution_types (qmj_id, institution_type_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            to_insert,
        )
        pg_conn.commit()
        print(f"  Inserted {len(to_insert)} rows.")


def sync_qmj_files(sq_conn, pg_conn):
    print("\n=== Syncing QMJ_FILES ===")
    sq_cur = sq_conn.cursor()
    pg_cur = pg_conn.cursor()

    existing = get_existing_ids(pg_cur, "qmj_files")
    sq_cur.execute("SELECT * FROM QmjPage_qmjfile")
    rows = sq_cur.fetchall()

    to_insert = []
    for r in rows:
        if r["id"] in existing:
            continue
        to_insert.append((
            r["id"],
            r["file"],
            r["uploaded_at"],
            r["file_size"],
            r["file_type"] or "",
            r["qmj_id"],
            r["uploaded_by_id"],
        ))

    if not to_insert:
        print("  No missing qmj_files.")
        return

    execute_values(
        pg_cur,
        """INSERT INTO qmj_files (id, file, uploaded_at, file_size, file_type, qmj_id, uploaded_by_id)
           VALUES %s ON CONFLICT (id) DO NOTHING""",
        to_insert,
    )
    pg_conn.commit()
    print(f"  Inserted {len(to_insert)} qmj_files.")


def reset_sequences(pg_conn):
    print("\n=== Resetting sequences ===")
    pg_cur = pg_conn.cursor()

    tables = ["users", "windows", "card_topics", "cards", "qmj", "qmj_files"]
    for table in tables:
        seq_name = f"{table}_id_seq"
        pg_cur.execute(f"SELECT setval('{seq_name}', COALESCE((SELECT MAX(id) FROM {table}), 1))")
        val = pg_cur.fetchone()[0]
        print(f"  {seq_name} -> {val}")

    pg_conn.commit()


def print_comparison(sq_conn, pg_conn):
    print("\n=== VERIFICATION: Row counts ===")
    sq_cur = sq_conn.cursor()
    pg_cur = pg_conn.cursor()

    comparisons = [
        ("AuthPage_user", "users"),
        ("TemplatesPage_window", "windows"),
        ("MaterialsPage_cardtopic", "card_topics"),
        ("MaterialsPage_card", "cards"),
        ("MaterialsPage_card_subject", "card_subject"),
        ("MaterialsPage_card_institution_type", "card_institution_type"),
        ("MaterialsPage_card_favorites", "card_favorites"),
        ("QmjPage_qmj", "qmj"),
        ("QmjPage_qmj_subject", "qmj_subjects"),
        ("QmjPage_qmj_institution_type", "qmj_institution_types"),
        ("QmjPage_qmjfile", "qmj_files"),
    ]

    print(f"  {'SQLite Table':<45} {'Count':>6}  {'PG Table':<30} {'Count':>6}  {'Match':>5}")
    print("  " + "-" * 100)
    for sq_table, pg_table in comparisons:
        sq_cur.execute(f"SELECT COUNT(*) FROM {sq_table}")
        sq_count = sq_cur.fetchone()[0]
        pg_cur.execute(f"SELECT COUNT(*) FROM {pg_table}")
        pg_count = pg_cur.fetchone()[0]
        match = "OK" if pg_count >= sq_count else "DIFF"
        print(f"  {sq_table:<45} {sq_count:>6}  {pg_table:<30} {pg_count:>6}  {match:>5}")


def main():
    print("Connecting to databases...")
    sq_conn = get_sqlite_conn()
    pg_conn = get_pg_conn()

    try:
        sync_users(sq_conn, pg_conn)
        sync_windows(sq_conn, pg_conn)
        sync_card_topics(sq_conn, pg_conn)
        sync_cards(sq_conn, pg_conn)
        sync_card_m2m(sq_conn, pg_conn)
        sync_qmj(sq_conn, pg_conn)
        sync_qmj_m2m(sq_conn, pg_conn)
        sync_qmj_files(sq_conn, pg_conn)
        reset_sequences(pg_conn)
        print_comparison(sq_conn, pg_conn)
        print("\nDone!")
    except Exception as e:
        pg_conn.rollback()
        print(f"\nERROR: {e}")
        raise
    finally:
        sq_conn.close()
        pg_conn.close()


if __name__ == "__main__":
    main()
