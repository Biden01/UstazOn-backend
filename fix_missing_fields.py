#!/usr/bin/env python3
"""
Fix missing field values that weren't transferred during initial migration.
- Cards: img1-img5 → img1_url-img5_url
- Subjects: image_url, hero_image_url, image_file, hero_image_file
- Windows: image → image_file
"""
import sqlite3
from pathlib import Path

import psycopg2

SQLITE_DB = Path(__file__).parent.parent / "backend_old" / "UstazOn" / "db.sqlite3"
PG_DSN = "dbname=ustazon user=postgres password=hcAPWlSXOVMXYUcH36SkDAio9tmwWT3 host=127.0.0.1 port=5432"


def fix_card_images(sq, pg):
    """Copy img1-img5 from old DB into img1_url-img5_url in new DB."""
    print("Fixing card images (img1→img1_url, img2→img2_url, ...)...")
    cur_sq = sq.execute("""
        SELECT id, img1, img2, img3, img4, img5
        FROM MaterialsPage_card
        WHERE (img1 IS NOT NULL AND img1 != '')
           OR (img2 IS NOT NULL AND img2 != '')
           OR (img3 IS NOT NULL AND img3 != '')
           OR (img4 IS NOT NULL AND img4 != '')
           OR (img5 IS NOT NULL AND img5 != '')
    """)
    cur_pg = pg.cursor()
    updated = 0

    for row in cur_sq:
        sets = []
        vals = []
        for i, col in enumerate(["img1", "img2", "img3", "img4", "img5"], 1):
            val = row[col]
            if val:
                sets.append(f"img{i}_url = COALESCE(NULLIF(img{i}_url, ''), %s)")
                vals.append(val)

        if sets:
            vals.append(row["id"])
            cur_pg.execute(
                f"UPDATE cards SET {', '.join(sets)} WHERE id = %s",
                vals
            )
            updated += 1

        if updated % 5000 == 0 and updated > 0:
            pg.commit()
            print(f"  ...{updated} cards updated")

    pg.commit()
    print(f"[OK] Updated images for {updated} cards")


def fix_subject_images(sq, pg):
    """Copy image fields from old subjects."""
    print("Fixing subject images...")
    cur_sq = sq.execute("""
        SELECT id, image_url, hero_image_url, image_file, hero_image_file
        FROM SubjectPage_subject
    """)
    cur_pg = pg.cursor()
    updated = 0

    for row in cur_sq:
        sets = []
        vals = []
        for col in ["image_url", "hero_image_url", "image_file", "hero_image_file"]:
            val = row[col]
            if val and val != "None":
                sets.append(f"{col} = %s")
                vals.append(val)

        if sets:
            vals.append(row["id"])
            cur_pg.execute(
                f"UPDATE subjects SET {', '.join(sets)} WHERE id = %s",
                vals
            )
            updated += 1

    pg.commit()
    print(f"[OK] Updated images for {updated} subjects")


def fix_window_images(sq, pg):
    """Copy image (local file) from old windows into image_file."""
    print("Fixing window image_file...")
    cur_sq = sq.execute("""
        SELECT id, image
        FROM TemplatesPage_window
        WHERE image IS NOT NULL AND image != '' AND image != 'None'
    """)
    cur_pg = pg.cursor()
    updated = 0

    for row in cur_sq:
        cur_pg.execute(
            "UPDATE windows SET image_file = %s WHERE id = %s AND (image_file IS NULL OR image_file = '')",
            (row["image"], row["id"])
        )
        updated += 1

    pg.commit()
    print(f"[OK] Updated image_file for {updated} windows")


def main():
    print("=" * 60)
    print("FIX: Missing field values")
    print("=" * 60)

    sq = sqlite3.connect(str(SQLITE_DB))
    sq.row_factory = sqlite3.Row
    pg = psycopg2.connect(PG_DSN)
    pg.autocommit = False

    try:
        fix_card_images(sq, pg)
        fix_subject_images(sq, pg)
        fix_window_images(sq, pg)

        print()
        print("=" * 60)
        print("ALL FIELDS FIXED!")
        print("=" * 60)
    except Exception as e:
        pg.rollback()
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        sq.close()
        pg.close()


if __name__ == "__main__":
    main()
