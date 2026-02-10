#!/usr/bin/env python3
"""
Migration script for data missing from the initial Django→FastAPI migration.
Transfers: test_results, test_links, subscriptions, page_access, qmj_files,
card_favorites, game data, and user fields (email, avatar, name updates).

Uses psycopg2 + sqlite3 directly for speed.
PostgreSQL is accessible at localhost:5432 (Docker port mapping).
"""
import json
import sqlite3
from datetime import datetime
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values

# Paths and connection
SQLITE_DB = Path(__file__).parent.parent / "backend_old" / "UstazOn" / "db.sqlite3"
PG_DSN = "dbname=ustazon user=postgres password=hcAPWlSXOVMXYUcH36SkDAio9tmwWT3 host=127.0.0.1 port=5432"


def get_connections():
    sqlite_conn = sqlite3.connect(str(SQLITE_DB))
    sqlite_conn.row_factory = sqlite3.Row
    pg_conn = psycopg2.connect(PG_DSN)
    pg_conn.autocommit = False
    return sqlite_conn, pg_conn


def parse_dt(val):
    """Parse datetime string from SQLite."""
    if not val:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(val, fmt)
        except ValueError:
            continue
    return None


def parse_int(val):
    """Safely parse an integer, handling text values from SQLite."""
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


# ─── 1. Add missing columns to users table ───────────────────────────────────

def add_user_columns(pg):
    cur = pg.cursor()
    # Add email column if not exists
    cur.execute("""
        DO $$ BEGIN
            ALTER TABLE users ADD COLUMN email VARCHAR(254);
        EXCEPTION WHEN duplicate_column THEN NULL;
        END $$;
    """)
    # Add avatar column if not exists
    cur.execute("""
        DO $$ BEGIN
            ALTER TABLE users ADD COLUMN avatar VARCHAR(255);
        EXCEPTION WHEN duplicate_column THEN NULL;
        END $$;
    """)
    pg.commit()
    print("[OK] User columns (email, avatar) ensured")


# ─── 2. Update user fields ───────────────────────────────────────────────────

def migrate_user_fields(sq, pg):
    print("Migrating user fields (email, avatar, names)...")
    cur_sq = sq.execute("""
        SELECT id, email, avatar, first_name, last_name, name
        FROM AuthPage_user
    """)
    cur_pg = pg.cursor()
    updated = 0

    for row in cur_sq:
        uid = row["id"]
        email = row["email"] if row["email"] else None
        avatar = row["avatar"] if row["avatar"] else None
        # Build full name from first+last if current name is empty
        old_name = row["name"] or ""
        first = row["first_name"] or ""
        last = row["last_name"] or ""
        full_name = f"{first} {last}".strip() if (first or last) else None

        sets = []
        vals = []
        if email:
            sets.append("email = %s")
            vals.append(email)
        if avatar:
            sets.append("avatar = %s")
            vals.append(avatar)
        if full_name and not old_name:
            sets.append("name = %s")
            vals.append(full_name[:100])

        if sets:
            vals.append(uid)
            cur_pg.execute(
                f"UPDATE users SET {', '.join(sets)} WHERE id = %s", vals
            )
            updated += 1

    pg.commit()
    print(f"[OK] Updated {updated} users with email/avatar/name")


# ─── 3. Migrate test_results ─────────────────────────────────────────────────

def migrate_test_results(sq, pg):
    print("Migrating test_results...")
    cur_pg = pg.cursor()

    # Check existing count
    cur_pg.execute("SELECT count(*) FROM test_results")
    existing = cur_pg.fetchone()[0]
    if existing > 0:
        print(f"  Skipping: {existing} records already exist")
        return

    rows = sq.execute("""
        SELECT id, test_id, student_name, group_name,
               correct_answers, total_questions, percentage,
               warning_count, attempt_count, completed_at
        FROM TestPage_testresult
    """).fetchall()

    # Filter to only valid test_ids
    cur_pg.execute("SELECT id FROM tests")
    valid_tests = {r[0] for r in cur_pg.fetchall()}

    data = []
    skipped = 0
    for r in rows:
        if r["test_id"] not in valid_tests:
            skipped += 1
            continue
        data.append((
            r["id"], r["test_id"], r["student_name"],
            r["group_name"] or None,
            r["correct_answers"], r["total_questions"],
            r["percentage"], r["warning_count"], r["attempt_count"],
            parse_dt(r["completed_at"]) or datetime.utcnow()
        ))

    if data:
        execute_values(cur_pg, """
            INSERT INTO test_results (id, test_id, student_name, group_name,
                correct_answers, total_questions, percentage,
                warning_count, attempt_count, completed_at)
            VALUES %s ON CONFLICT (id) DO NOTHING
        """, data)

    # Fix sequence
    cur_pg.execute("SELECT setval('test_results_id_seq', (SELECT COALESCE(MAX(id),1) FROM test_results), true)")
    pg.commit()
    print(f"[OK] Migrated {len(data)} test_results (skipped {skipped} with invalid test_id)")


# ─── 4. Migrate test_links ───────────────────────────────────────────────────

def migrate_test_links(sq, pg):
    print("Migrating test_links...")
    cur_pg = pg.cursor()

    cur_pg.execute("SELECT count(*) FROM test_links")
    if cur_pg.fetchone()[0] > 0:
        print("  Skipping: records already exist")
        return

    rows = sq.execute("""
        SELECT id, test_id, unique_hash, group_name, created_at
        FROM TestPage_testlink
    """).fetchall()

    cur_pg.execute("SELECT id FROM tests")
    valid_tests = {r[0] for r in cur_pg.fetchall()}

    data = []
    for r in rows:
        if r["test_id"] not in valid_tests:
            continue
        data.append((
            r["id"], r["test_id"], r["unique_hash"],
            r["group_name"] or None,
            True,  # is_active
            0,     # attempts_count
            parse_dt(r["created_at"])
        ))

    if data:
        execute_values(cur_pg, """
            INSERT INTO test_links (id, test_id, unique_hash, group_name,
                is_active, attempts_count, created_at)
            VALUES %s ON CONFLICT (id) DO NOTHING
        """, data)

    cur_pg.execute("SELECT setval('test_links_id_seq', (SELECT COALESCE(MAX(id),1) FROM test_links), true)")
    pg.commit()
    print(f"[OK] Migrated {len(data)} test_links")


# ─── 5. Migrate subscriptions ────────────────────────────────────────────────

def migrate_subscriptions(sq, pg):
    print("Migrating subscriptions...")
    cur_pg = pg.cursor()

    cur_pg.execute("SELECT count(*) FROM subscriptions")
    if cur_pg.fetchone()[0] > 0:
        print("  Skipping: records already exist")
        return

    rows = sq.execute("""
        SELECT id, user_id, subject_id, institution_type_id, end_date
        FROM AuthPage_subscribe
    """).fetchall()

    # Get valid foreign keys
    cur_pg.execute("SELECT id FROM users")
    valid_users = {r[0] for r in cur_pg.fetchall()}
    cur_pg.execute("SELECT id FROM subjects")
    valid_subjects = {r[0] for r in cur_pg.fetchall()}
    cur_pg.execute("SELECT id FROM institution_types")
    valid_inst = {r[0] for r in cur_pg.fetchall()}

    data = []
    skipped = 0
    for r in rows:
        if (r["user_id"] not in valid_users or
                r["subject_id"] not in valid_subjects or
                r["institution_type_id"] not in valid_inst):
            skipped += 1
            continue
        data.append((
            r["id"], r["user_id"], r["subject_id"],
            r["institution_type_id"], r["end_date"]
        ))

    if data:
        execute_values(cur_pg, """
            INSERT INTO subscriptions (id, user_id, subject_id,
                institution_type_id, end_date)
            VALUES %s ON CONFLICT (id) DO NOTHING
        """, data)

    cur_pg.execute("SELECT setval('subscriptions_id_seq', (SELECT COALESCE(MAX(id),1) FROM subscriptions), true)")
    pg.commit()
    print(f"[OK] Migrated {len(data)} subscriptions (skipped {skipped})")


# ─── 6. Migrate page_access ──────────────────────────────────────────────────

def migrate_page_access(sq, pg):
    print("Migrating page_access...")
    cur_pg = pg.cursor()

    cur_pg.execute("SELECT count(*) FROM page_access")
    if cur_pg.fetchone()[0] > 0:
        print("  Skipping: records already exist")
        return

    rows = sq.execute("""
        SELECT id, url_pattern, name, description, protection_level,
               requires_specific_subject, is_active, created_at, updated_at,
               subject_id, institution_type_id
        FROM AuthPage_pageaccess
    """).fetchall()

    data = []
    for r in rows:
        data.append((
            r["id"], r["url_pattern"], r["name"],
            r["description"] or None, r["protection_level"],
            bool(r["requires_specific_subject"]),
            r["subject_id"], r["institution_type_id"],
            bool(r["is_active"]),
            parse_dt(r["created_at"]), parse_dt(r["updated_at"])
        ))

    if data:
        execute_values(cur_pg, """
            INSERT INTO page_access (id, url_pattern, name, description,
                protection_level, requires_specific_subject,
                subject_id, institution_type_id, is_active,
                created_at, updated_at)
            VALUES %s ON CONFLICT (id) DO NOTHING
        """, data)

    cur_pg.execute("SELECT setval('page_access_id_seq', (SELECT COALESCE(MAX(id),1) FROM page_access), true)")
    pg.commit()
    print(f"[OK] Migrated {len(data)} page_access rules")


# ─── 7. Migrate qmj_files ────────────────────────────────────────────────────

def migrate_qmj_files(sq, pg):
    print("Migrating qmj_files...")
    cur_pg = pg.cursor()

    cur_pg.execute("SELECT count(*) FROM qmj_files")
    if cur_pg.fetchone()[0] > 0:
        print("  Skipping: records already exist")
        return

    rows = sq.execute("""
        SELECT id, file, uploaded_at, file_size, file_type, qmj_id, uploaded_by_id
        FROM QmjPage_qmjfile
    """).fetchall()

    # Validate foreign keys
    cur_pg.execute("SELECT id FROM qmj")
    valid_qmj = {r[0] for r in cur_pg.fetchall()}
    cur_pg.execute("SELECT id FROM users")
    valid_users = {r[0] for r in cur_pg.fetchall()}

    data = []
    skipped = 0
    for r in rows:
        if r["qmj_id"] not in valid_qmj:
            skipped += 1
            continue
        uploaded_by = r["uploaded_by_id"] if r["uploaded_by_id"] and r["uploaded_by_id"] in valid_users else None
        data.append((
            r["id"], r["file"], r["file_size"], r["file_type"],
            r["qmj_id"], uploaded_by,
            parse_dt(r["uploaded_at"])
        ))

    if data:
        execute_values(cur_pg, """
            INSERT INTO qmj_files (id, file, file_size, file_type,
                qmj_id, uploaded_by_id, uploaded_at)
            VALUES %s ON CONFLICT (id) DO NOTHING
        """, data)

    cur_pg.execute("SELECT setval('qmj_files_id_seq', (SELECT COALESCE(MAX(id),1) FROM qmj_files), true)")
    pg.commit()
    print(f"[OK] Migrated {len(data)} qmj_files (skipped {skipped})")


# ─── 8. Migrate card_favorites ───────────────────────────────────────────────

def migrate_card_favorites(sq, pg):
    print("Migrating card_favorites...")
    cur_pg = pg.cursor()

    rows = sq.execute("""
        SELECT user_id, card_id FROM MaterialsPage_card_favorites
    """).fetchall()

    # Get existing
    cur_pg.execute("SELECT user_id, card_id FROM card_favorites")
    existing = {(r[0], r[1]) for r in cur_pg.fetchall()}

    # Validate foreign keys
    cur_pg.execute("SELECT id FROM users")
    valid_users = {r[0] for r in cur_pg.fetchall()}
    cur_pg.execute("SELECT id FROM cards")
    valid_cards = {r[0] for r in cur_pg.fetchall()}

    data = []
    skipped = 0
    for r in rows:
        pair = (r["user_id"], r["card_id"])
        if pair in existing:
            continue
        if r["user_id"] not in valid_users or r["card_id"] not in valid_cards:
            skipped += 1
            continue
        data.append(pair)

    if data:
        execute_values(cur_pg, """
            INSERT INTO card_favorites (user_id, card_id)
            VALUES %s ON CONFLICT DO NOTHING
        """, data)

    pg.commit()
    print(f"[OK] Migrated {len(data)} card_favorites (skipped {skipped})")


# ─── 9. Migrate game_templates ───────────────────────────────────────────────

def migrate_game_templates(sq, pg):
    print("Migrating game_templates...")
    cur_pg = pg.cursor()

    cur_pg.execute("SELECT count(*) FROM game_templates")
    if cur_pg.fetchone()[0] > 0:
        print("  Skipping: records already exist")
        return

    rows = sq.execute("""
        SELECT id, name, game_type, description, instruction,
               preview_image, icon, min_items, max_items,
               default_settings, is_active, is_premium, "order", created_at
        FROM GameConstructor_gametemplate
    """).fetchall()

    data = []
    for r in rows:
        # Parse default_settings as JSON
        settings = r["default_settings"]
        if isinstance(settings, str):
            try:
                settings = json.loads(settings)
            except (json.JSONDecodeError, TypeError):
                settings = {}
        data.append((
            r["id"], r["name"], r["game_type"],
            r["description"] or None, r["instruction"] or None,
            r["preview_image"] or None, r["icon"] or None,
            r["min_items"], r["max_items"],
            json.dumps(settings),
            bool(r["is_active"]), bool(r["is_premium"]),
            r["order"],
            parse_dt(r["created_at"])
        ))

    if data:
        execute_values(cur_pg, """
            INSERT INTO game_templates (id, name, game_type, description,
                instruction, preview_image, icon, min_items, max_items,
                default_settings, is_active, is_premium, "order", created_at)
            VALUES %s ON CONFLICT (id) DO NOTHING
        """, data)

    cur_pg.execute("SELECT setval('game_templates_id_seq', (SELECT COALESCE(MAX(id),1) FROM game_templates), true)")
    pg.commit()
    print(f"[OK] Migrated {len(data)} game_templates")


# ─── 10. Migrate game_categories ─────────────────────────────────────────────

def migrate_game_categories(sq, pg):
    print("Migrating game_categories...")
    cur_pg = pg.cursor()

    cur_pg.execute("SELECT count(*) FROM game_categories")
    if cur_pg.fetchone()[0] > 0:
        print("  Skipping: records already exist")
        return

    rows = sq.execute("""
        SELECT id, name, description, icon, color, is_active, "order"
        FROM GameConstructor_gamecategory
    """).fetchall()

    data = []
    for r in rows:
        data.append((
            r["id"], r["name"], r["description"] or None,
            r["icon"] or None, r["color"] or None,
            bool(r["is_active"]), r["order"]
        ))

    if data:
        execute_values(cur_pg, """
            INSERT INTO game_categories (id, name, description, icon,
                color, is_active, "order")
            VALUES %s ON CONFLICT (id) DO NOTHING
        """, data)

    cur_pg.execute("SELECT setval('game_categories_id_seq', (SELECT COALESCE(MAX(id),1) FROM game_categories), true)")
    pg.commit()
    print(f"[OK] Migrated {len(data)} game_categories")


# ─── 11. Migrate games ───────────────────────────────────────────────────────

def migrate_games(sq, pg):
    print("Migrating games...")
    cur_pg = pg.cursor()

    cur_pg.execute("SELECT count(*) FROM games")
    if cur_pg.fetchone()[0] > 0:
        print("  Skipping: records already exist")
        return

    rows = sq.execute("""
        SELECT id, title, description, grade, quarter, difficulty,
               settings, time_limit, attempts_limit, show_correct_answers,
               shuffle_items, is_public, is_featured, allow_embedding,
               password, views_count, plays_count, likes_count,
               created_at, updated_at, author_id, topic_id, template_id
        FROM GameConstructor_game
    """).fetchall()

    cur_pg.execute("SELECT id FROM users")
    valid_users = {r[0] for r in cur_pg.fetchall()}
    cur_pg.execute("SELECT id FROM game_templates")
    valid_templates = {r[0] for r in cur_pg.fetchall()}
    cur_pg.execute("SELECT id FROM card_topics")
    valid_topics = {r[0] for r in cur_pg.fetchall()}

    data = []
    skipped = 0
    for r in rows:
        if r["template_id"] not in valid_templates:
            skipped += 1
            continue
        author_id = r["author_id"] if r["author_id"] and r["author_id"] in valid_users else None
        topic_id = r["topic_id"] if r["topic_id"] and r["topic_id"] in valid_topics else None

        settings = r["settings"]
        if isinstance(settings, str):
            try:
                settings = json.loads(settings)
            except (json.JSONDecodeError, TypeError):
                settings = {}

        data.append((
            r["id"], r["title"], r["description"] or None,
            r["difficulty"] or "medium",
            r["grade"], r["quarter"],
            r["time_limit"], r["attempts_limit"],
            bool(r["show_correct_answers"]),
            bool(r["shuffle_items"]),
            bool(r["is_public"]), bool(r["is_featured"]),
            bool(r["allow_embedding"]),
            r["password"] or None,
            json.dumps(settings),
            r["views_count"] or 0, r["plays_count"] or 0, r["likes_count"] or 0,
            r["template_id"], author_id, topic_id,
            parse_dt(r["created_at"]), parse_dt(r["updated_at"])
        ))

    if data:
        execute_values(cur_pg, """
            INSERT INTO games (id, title, description, difficulty,
                grade, quarter, time_limit, attempts_limit,
                show_correct_answers, shuffle_items,
                is_public, is_featured, allow_embedding,
                password, settings, views_count, plays_count, likes_count,
                template_id, author_id, topic_id,
                created_at, updated_at)
            VALUES %s ON CONFLICT (id) DO NOTHING
        """, data)

    cur_pg.execute("SELECT setval('games_id_seq', (SELECT COALESCE(MAX(id),1) FROM games), true)")
    pg.commit()
    print(f"[OK] Migrated {len(data)} games (skipped {skipped})")


# ─── 12. Migrate game_items ──────────────────────────────────────────────────

def migrate_game_items(sq, pg):
    print("Migrating game_items...")
    cur_pg = pg.cursor()

    cur_pg.execute("SELECT count(*) FROM game_items")
    if cur_pg.fetchone()[0] > 0:
        print("  Skipping: records already exist")
        return

    rows = sq.execute("""
        SELECT id, item_type, question, answer, answer_options,
               hint, explanation, image, audio, video, video_url,
               points, time_limit, "order", is_active, extra_data,
               created_at, game_id
        FROM GameConstructor_gameitem
    """).fetchall()

    cur_pg.execute("SELECT id FROM games")
    valid_games = {r[0] for r in cur_pg.fetchall()}

    data = []
    skipped = 0
    for r in rows:
        if r["game_id"] not in valid_games:
            skipped += 1
            continue

        answer_options = r["answer_options"]
        if isinstance(answer_options, str):
            try:
                answer_options = json.loads(answer_options)
            except (json.JSONDecodeError, TypeError):
                answer_options = []

        extra_data = r["extra_data"]
        if isinstance(extra_data, str):
            try:
                extra_data = json.loads(extra_data)
            except (json.JSONDecodeError, TypeError):
                extra_data = {}

        data.append((
            r["id"], r["item_type"],
            r["question"] or None, r["answer"] or None,
            json.dumps(answer_options),
            r["hint"] or None, r["explanation"] or None,
            r["image"] or None, r["audio"] or None,
            r["video"] or None, r["video_url"] or None,
            r["points"] or 1, r["time_limit"],
            r["order"] or 0, bool(r["is_active"]),
            json.dumps(extra_data),
            r["game_id"],
            parse_dt(r["created_at"])
        ))

    if data:
        execute_values(cur_pg, """
            INSERT INTO game_items (id, item_type, question, answer,
                answer_options, hint, explanation, image, audio,
                video, video_url, points, time_limit, "order",
                is_active, extra_data, game_id, created_at)
            VALUES %s ON CONFLICT (id) DO NOTHING
        """, data)

    cur_pg.execute("SELECT setval('game_items_id_seq', (SELECT COALESCE(MAX(id),1) FROM game_items), true)")
    pg.commit()
    print(f"[OK] Migrated {len(data)} game_items (skipped {skipped})")


# ─── 13. Migrate game association tables ──────────────────────────────────────

def migrate_game_associations(sq, pg):
    """Migrate game_subjects, game_institution_types, game_categories_link, game_favorites"""
    cur_pg = pg.cursor()

    # Validate foreign keys
    cur_pg.execute("SELECT id FROM games")
    valid_games = {r[0] for r in cur_pg.fetchall()}
    cur_pg.execute("SELECT id FROM subjects")
    valid_subjects = {r[0] for r in cur_pg.fetchall()}
    cur_pg.execute("SELECT id FROM institution_types")
    valid_inst = {r[0] for r in cur_pg.fetchall()}
    cur_pg.execute("SELECT id FROM game_categories")
    valid_cats = {r[0] for r in cur_pg.fetchall()}
    cur_pg.execute("SELECT id FROM users")
    valid_users = {r[0] for r in cur_pg.fetchall()}

    # game_subjects
    rows = sq.execute("SELECT game_id, subject_id FROM GameConstructor_game_subject").fetchall()
    data = [(r["game_id"], r["subject_id"]) for r in rows
            if r["game_id"] in valid_games and r["subject_id"] in valid_subjects]
    if data:
        execute_values(cur_pg, "INSERT INTO game_subjects (game_id, subject_id) VALUES %s ON CONFLICT DO NOTHING", data)
    print(f"  game_subjects: {len(data)}")

    # game_institution_types
    rows = sq.execute("SELECT game_id, institutiontype_id FROM GameConstructor_game_institution_type").fetchall()
    data = [(r["game_id"], r["institutiontype_id"]) for r in rows
            if r["game_id"] in valid_games and r["institutiontype_id"] in valid_inst]
    if data:
        execute_values(cur_pg, "INSERT INTO game_institution_types (game_id, institution_type_id) VALUES %s ON CONFLICT DO NOTHING", data)
    print(f"  game_institution_types: {len(data)}")

    # game_categories_link
    rows = sq.execute("SELECT game_id, gamecategory_id FROM GameConstructor_game_categories").fetchall()
    data = [(r["game_id"], r["gamecategory_id"]) for r in rows
            if r["game_id"] in valid_games and r["gamecategory_id"] in valid_cats]
    if data:
        execute_values(cur_pg, "INSERT INTO game_categories_link (game_id, category_id) VALUES %s ON CONFLICT DO NOTHING", data)
    print(f"  game_categories_link: {len(data)}")

    # game_favorites
    rows = sq.execute("SELECT game_id, user_id FROM GameConstructor_game_favorites").fetchall()
    data = [(r["game_id"], r["user_id"]) for r in rows
            if r["game_id"] in valid_games and r["user_id"] in valid_users]
    if data:
        execute_values(cur_pg, "INSERT INTO game_favorites (game_id, user_id) VALUES %s ON CONFLICT DO NOTHING", data)
    print(f"  game_favorites: {len(data)}")

    pg.commit()
    print("[OK] Game associations migrated")


# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("MIGRATION: Missing data from Django SQLite → PostgreSQL")
    print("=" * 60)

    if not SQLITE_DB.exists():
        print(f"ERROR: SQLite database not found at {SQLITE_DB}")
        return

    sq, pg = get_connections()
    print(f"Connected to SQLite: {SQLITE_DB}")
    print(f"Connected to PostgreSQL")
    print()

    try:
        # 1. Schema changes
        add_user_columns(pg)

        # 2. User field updates
        migrate_user_fields(sq, pg)

        # 3. Test results & links
        migrate_test_results(sq, pg)
        migrate_test_links(sq, pg)

        # 4. Subscriptions & page access
        migrate_subscriptions(sq, pg)
        migrate_page_access(sq, pg)

        # 5. QMJ files
        migrate_qmj_files(sq, pg)

        # 6. Card favorites
        migrate_card_favorites(sq, pg)

        # 7. Game data (order matters: templates → categories → games → items → associations)
        migrate_game_templates(sq, pg)
        migrate_game_categories(sq, pg)
        migrate_games(sq, pg)
        migrate_game_items(sq, pg)
        migrate_game_associations(sq, pg)

        print()
        print("=" * 60)
        print("MIGRATION COMPLETED SUCCESSFULLY!")
        print("=" * 60)

    except Exception as e:
        pg.rollback()
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        sq.close()
        pg.close()


if __name__ == "__main__":
    main()
