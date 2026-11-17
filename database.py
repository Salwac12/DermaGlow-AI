# ==========================================================
# DERMAGLOW AI - DATABASE
# Developer: Salwa Choudhari
#
# Local: SQLite
# Vercel: Neon PostgreSQL
# ==========================================================

import os
import re
import sqlite3

from pathlib import Path

from dotenv import load_dotenv


# ==========================================================
# ENVIRONMENT CONFIGURATION
# ==========================================================

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")

DATABASE = BASE_DIR / "dermaglow.db"

IS_VERCEL = os.environ.get("VERCEL") == "1"


# ==========================================================
# POSTGRESQL SQL COMPATIBILITY
# ==========================================================

def convert_sql_for_postgres(query):

    # SQLite uses DATE('now').
    # Our migrated date columns are stored as text.

    query = re.sub(
        r"DATE\s*\(\s*'now'\s*\)",
        "CURRENT_DATE::text",
        query,
        flags=re.IGNORECASE
    )

    # SQLite's NOCASE collation is not generally
    # available in PostgreSQL.
    #
    # Preserve case-insensitive product ordering.

    query = re.sub(
        r"\bproduct_name\s+COLLATE\s+NOCASE\b",
        "LOWER(product_name)",
        query,
        flags=re.IGNORECASE
    )

    # Remove any remaining SQLite NOCASE clauses.

    query = re.sub(
        r"\s+COLLATE\s+NOCASE\b",
        "",
        query,
        flags=re.IGNORECASE
    )

    # SQLite LIKE is case-insensitive for ASCII
    # by default. PostgreSQL uses ILIKE.

    query = re.sub(
        r"\bLIKE\b",
        "ILIKE",
        query,
        flags=re.IGNORECASE
    )

    # SQLite uses ? placeholders.
    # psycopg2 uses %s placeholders.

    query = query.replace("?", "%s")

    return query


# ==========================================================
# POSTGRESQL CONNECTION WRAPPER
# ==========================================================

class PostgresConnection:

    def __init__(self, connection):

        self.connection = connection

    def execute(self, query, parameters=None):

        from psycopg2.extras import RealDictCursor

        converted_query = convert_sql_for_postgres(
            query
        )

        cursor = self.connection.cursor(
            cursor_factory=RealDictCursor
        )

        try:

            cursor.execute(
                converted_query,
                tuple(parameters or ())
            )

            return cursor

        except Exception:

            cursor.close()
            raise

    def commit(self):

        self.connection.commit()

    def rollback(self):

        self.connection.rollback()

    def close(self):

        self.connection.close()


# ==========================================================
# DATABASE CONNECTION
# ==========================================================

def get_db_connection():

    # ------------------------------------------
    # VERCEL: NEON POSTGRESQL
    # ------------------------------------------

    if IS_VERCEL:

        import psycopg2

        database_url = os.environ.get(
            "DATABASE_URL",
            ""
        ).strip()

        if not database_url:

            raise RuntimeError(
                "DATABASE_URL is not configured "
                "in Vercel environment variables."
            )

        connection = psycopg2.connect(
            database_url,
            connect_timeout=10
        )

        return PostgresConnection(
            connection
        )

    # ------------------------------------------
    # LOCAL: SQLITE
    # ------------------------------------------

    connection = sqlite3.connect(
        DATABASE,
        timeout=15
    )

    connection.row_factory = sqlite3.Row

    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    return connection


# ==========================================================
# CREATE / VERIFY DATABASE
# ==========================================================

def create_database():

    # ------------------------------------------
    # POSTGRESQL
    # ------------------------------------------

    if IS_VERCEL:

        # The SQLite-to-Neon migration has already
        # created and populated these tables.
        #
        # Verify that they exist.
        # Do not recreate or overwrite their data.

        connection = get_db_connection()

        try:

            connection.execute(
                "SELECT id FROM products LIMIT 0"
            ).close()

            connection.execute(
                "SELECT id FROM reviews LIMIT 0"
            ).close()

            connection.commit()

        except Exception:

            connection.rollback()
            raise

        finally:

            connection.close()

        return

    # ------------------------------------------
    # SQLITE
    # ------------------------------------------

    connection = get_db_connection()

    try:

        connection.execute("""
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
        # UPGRADE EXISTING PRODUCTS TABLE
        # ------------------------------------------

        columns = connection.execute(
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

                connection.execute(
                    f"ALTER TABLE products "
                    f"ADD COLUMN {name} {column_type}"
                )

                print(
                    f"Added product column: {name}"
                )

        # ------------------------------------------
        # CUSTOMER REVIEWS TABLE
        # ------------------------------------------

        connection.execute("""
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

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_products_status
            ON products(verification_status)
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_products_brand
            ON products(brand)
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_products_category
            ON products(category)
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_reviews_product
            ON reviews(product_id)
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_reviews_status
            ON reviews(moderation_status)
        """)

        connection.commit()

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()


# ==========================================================
# PRODUCT STATISTICS
# ==========================================================

def get_database_stats():

    connection = get_db_connection()

    try:

        row = connection.execute("""
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

        connection.close()


# ==========================================================
# REVIEW STATISTICS
# ==========================================================

def get_review_stats():

    connection = get_db_connection()

    try:

        row = connection.execute("""
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

        connection.close()


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