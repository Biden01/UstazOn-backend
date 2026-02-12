"""
Migration script: Copy image paths from old SQLite DB to new PostgreSQL DB.

1. Subjects: image_file -> image_url (as /media/{path})
2. Cards: img1-img5 -> img1_url-img5_url (as /media/{path} for local files, or as-is for URLs)
"""

import sqlite3
import psycopg2

OLD_DB = "/var/UstazOn/UstazOn/db.sqlite3"
NEW_DB = "postgresql://postgres:q7OfuPIW5xe9GpIsI9iy5B8xkVP6AmV@127.0.0.1:5432/ustazon"
MEDIA_PREFIX = "/media/"


def convert_path(value: str | None) -> str | None:
    """Convert old Django image field value to a URL."""
    if not value or value == "None":
        return None
    # Already a full URL
    if value.startswith("http://") or value.startswith("https://"):
        return value
    # Local file path - prepend /media/
    return MEDIA_PREFIX + value


def migrate():
    sqlite_conn = sqlite3.connect(OLD_DB)
    sqlite_conn.row_factory = sqlite3.Row
    pg_conn = psycopg2.connect(NEW_DB)

    sqlite_cur = sqlite_conn.cursor()
    pg_cur = pg_conn.cursor()

    # --- Migrate subjects: image_file -> image_url ---
    print("=== Migrating subjects ===")
    sqlite_cur.execute("SELECT id, image_file, hero_image_file FROM SubjectPage_subject")
    subject_count = 0
    for row in sqlite_cur.fetchall():
        sid = row["id"]
        image_url = convert_path(row["image_file"])
        hero_url = convert_path(row["hero_image_file"])

        if image_url:
            pg_cur.execute(
                "UPDATE subjects SET image_url = %s WHERE id = %s",
                (image_url, sid),
            )
            subject_count += pg_cur.rowcount

        if hero_url:
            pg_cur.execute(
                "UPDATE subjects SET hero_image_url = %s WHERE id = %s",
                (hero_url, sid),
            )

    print(f"  Updated {subject_count} subjects")

    # --- Migrate cards: img1-img5 -> img1_url-img5_url ---
    print("=== Migrating cards ===")
    sqlite_cur.execute(
        "SELECT id, img1, img2, img3, img4, img5 FROM MaterialsPage_card"
    )

    batch = []
    card_count = 0
    for row in sqlite_cur.fetchall():
        cid = row["id"]
        imgs = [convert_path(row[f"img{i}"]) for i in range(1, 6)]

        # Skip if all images are None
        if not any(imgs):
            continue

        batch.append((imgs[0], imgs[1], imgs[2], imgs[3], imgs[4], cid))
        card_count += 1

        if len(batch) >= 1000:
            pg_cur.executemany(
                """UPDATE cards
                   SET img1_url = %s, img2_url = %s, img3_url = %s,
                       img4_url = %s, img5_url = %s
                   WHERE id = %s""",
                batch,
            )
            batch = []

    if batch:
        pg_cur.executemany(
            """UPDATE cards
               SET img1_url = %s, img2_url = %s, img3_url = %s,
                   img4_url = %s, img5_url = %s
               WHERE id = %s""",
            batch,
        )

    print(f"  Updated {card_count} cards")

    pg_conn.commit()
    print("=== Migration complete ===")

    # Verification
    pg_cur.execute("SELECT count(*) FROM cards WHERE img1_url IS NOT NULL")
    print(f"  Cards with img1_url: {pg_cur.fetchone()[0]}")
    pg_cur.execute("SELECT id, substring(image_url from 1 for 60) FROM subjects LIMIT 5")
    print("  Sample subjects:")
    for r in pg_cur.fetchall():
        print(f"    {r[0]}: {r[1]}")

    pg_cur.close()
    pg_conn.close()
    sqlite_cur.close()
    sqlite_conn.close()


if __name__ == "__main__":
    migrate()
