# ==========================================================
# DERMAGLOW AI - DATABASE
# Developer: Salwa Choudhari
# ==========================================================

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "dermaglow.db"


# ==========================================================
# DATABASE CONNECTION
# ==========================================================

def get_db_connection():

    conn = sqlite3.connect(
        DATABASE,
        timeout=15
    )

    conn.row_factory = sqlite3.Row

    conn.execute("PRAGMA foreign_keys = ON")

    return conn


# ==========================================================
# CREATE / UPGRADE DATABASE
# ==========================================================

def create_database():

    conn = get_db_connection()

    try:

        # ------------------------------------------
        # PRODUCTS TABLE
        # ------------------------------------------

        conn.execute("""
            CREATE TABLE IF NOT EXISTS products (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                barcode TEXT NOT NULL UNIQUE,

                product_name TEXT NOT NULL,

                brand TEXT,

                category TEXT,

                ingredients TEXT,

                quantity TEXT,

                source_url TEXT NOT NULL,

                source_name TEXT NOT NULL
                    DEFAULT 'Open Beauty Facts',

                india_tagged INTEGER NOT NULL DEFAULT 0,

                verification_status TEXT NOT NULL
                    DEFAULT 'pending'
                    CHECK (
                        verification_status IN (
                            'pending',
                            'approved',
                            'rejected'
                        )
                    ),

                image_url TEXT,

                price_inr REAL,

                price_source_url TEXT,

                price_checked_at TEXT,

                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                updated_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ------------------------------------------
        # SAFELY UPGRADE EXISTING PRODUCTS TABLE
        # ------------------------------------------

        columns = conn.execute(
            "PRAGMA table_info(products)"
        ).fetchall()

        column_names = {
            column["name"]
            for column in columns
        }

        new_columns = {
            "image_url": "TEXT",
            "price_inr": "REAL",
            "price_source_url": "TEXT",
            "price_checked_at": "TEXT"
        }

        for name, column_type in new_columns.items():

            if name not in column_names:

                conn.execute(
                    f"ALTER TABLE products "
                    f"ADD COLUMN {name} {column_type}"
                )

                print(
                    f"Added product column: {name}"
                )

        # ------------------------------------------
        # NEW: CUSTOMER REVIEWS TABLE
        # ------------------------------------------

        conn.execute("""
            CREATE TABLE IF NOT EXISTS reviews (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                product_id INTEGER NOT NULL,

                reviewer_name TEXT NOT NULL,

                rating INTEGER NOT NULL
                    CHECK (rating BETWEEN 1 AND 5),

                review_title TEXT NOT NULL,

                review_text TEXT NOT NULL,

                moderation_status TEXT NOT NULL
                    DEFAULT 'pending'
                    CHECK (
                        moderation_status IN (
                            'pending',
                            'approved',
                            'rejected'
                        )
                    ),

                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                moderated_at TEXT,

                FOREIGN KEY (product_id)
                    REFERENCES products(id)
                    ON DELETE CASCADE
            )
        """)

        # ------------------------------------------
        # INDEXES
        # ------------------------------------------

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_products_status
            ON products(verification_status)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_products_brand
            ON products(brand)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_products_category
            ON products(category)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_reviews_product
            ON reviews(product_id)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_reviews_status
            ON reviews(moderation_status)
        """)

        conn.commit()

    except Exception:

        conn.rollback()
        raise

    finally:

        conn.close()


# ==========================================================
# PRODUCT STATISTICS
# ==========================================================

def get_database_stats():

    conn = get_db_connection()

    try:

        row = conn.execute("""
            SELECT

                COUNT(*) AS total,

                SUM(
                    CASE
                        WHEN verification_status = 'pending'
                        THEN 1 ELSE 0
                    END
                ) AS pending,

                SUM(
                    CASE
                        WHEN verification_status = 'approved'
                        THEN 1 ELSE 0
                    END
                ) AS approved,

                SUM(
                    CASE
                        WHEN verification_status = 'rejected'
                        THEN 1 ELSE 0
                    END
                ) AS rejected,

                SUM(
                    CASE
                        WHEN image_url IS NOT NULL
                         AND TRIM(image_url) != ''
                        THEN 1 ELSE 0
                    END
                ) AS with_images,

                SUM(
                    CASE
                        WHEN price_inr IS NOT NULL
                        THEN 1 ELSE 0
                    END
                ) AS with_prices

            FROM products
        """).fetchone()

        return {
            key: row[key] or 0
            for key in row.keys()
        }

    finally:

        conn.close()


# ==========================================================
# REVIEW STATISTICS
# ==========================================================

def get_review_stats():

    conn = get_db_connection()

    try:

        row = conn.execute("""
            SELECT

                COUNT(*) AS total,

                SUM(
                    CASE
                        WHEN moderation_status = 'pending'
                        THEN 1 ELSE 0
                    END
                ) AS pending,

                SUM(
                    CASE
                        WHEN moderation_status = 'approved'
                        THEN 1 ELSE 0
                    END
                ) AS approved,

                SUM(
                    CASE
                        WHEN moderation_status = 'rejected'
                        THEN 1 ELSE 0
                    END
                ) AS rejected

            FROM reviews
        """).fetchone()

        return {
            key: row[key] or 0
            for key in row.keys()
        }

    finally:

        conn.close()


# ==========================================================
# RUN DATABASE SETUP
# ==========================================================

if __name__ == "__main__":

    create_database()

    print()
    print("====================================")
    print("DERMAGLOW AI DATABASE")
    print("====================================")

    print("Total products:", get_database_stats()["total"])
    print("Total reviews:", get_review_stats()["total"])

    print()
    print("Database is ready.")
    print("Existing products have been preserved.")