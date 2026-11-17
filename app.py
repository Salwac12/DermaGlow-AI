# ==========================================================
# DERMAGLOW AI
# MAIN FLASK APPLICATION
#
# Developer: Salwa Choudhari
#
# Features:
# - Homepage
# - Skin Analysis
# - Product Catalog
# - Product Images
# - Indian Reference Prices
# - Search and Pagination
# - Product Ratings and Review Counts
# - Admin Login
# - Approve All Products
# - Individual Product Approval
# - Product Price Management
# - Customer Reviews
# - Personalized Recommendations
# - Morning and Night Skincare Routine
# ==========================================================

import os
import hmac
import math
import secrets

from decimal import Decimal, InvalidOperation
from functools import wraps
from urllib.parse import urlparse

from dotenv import load_dotenv

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    abort
)

from database import (
    create_database,
    get_db_connection,
    get_database_stats
)

from recommendations import recommendations_bp

from reviews import reviews_bp


# ==========================================================
# LOAD ENVIRONMENT SETTINGS
# ==========================================================

load_dotenv()


# ==========================================================
# CREATE FLASK APPLICATION
# ==========================================================

app = Flask(__name__)

app.register_blueprint(recommendations_bp)

app.register_blueprint(reviews_bp)

app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

app.secret_key = (
    os.environ.get("FLASK_SECRET_KEY")
    or secrets.token_hex(32)
)

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=(
        os.environ.get("VERCEL") == "1"
    )
)


# ==========================================================
# ADMIN CONFIGURATION
# ==========================================================

ADMIN_USERNAME = os.environ.get(
    "DERMAGLOW_ADMIN_USERNAME",
    ""
).strip()

ADMIN_PASSWORD = os.environ.get(
    "DERMAGLOW_ADMIN_PASSWORD",
    ""
)

ADMIN_CONFIGURED = bool(
    ADMIN_USERNAME
    and ADMIN_PASSWORD
    and ADMIN_PASSWORD != "REPLACE_WITH_YOUR_PRIVATE_PASSWORD"
)


# ==========================================================
# INITIALIZE DATABASE
# ==========================================================

create_database()


# ==========================================================
# ADMIN LOGIN PROTECTION
# ==========================================================

def admin_login_required(view):

    @wraps(view)
    def protected_view(*args, **kwargs):

        if not session.get("admin_logged_in"):

            flash(
                "Please log in to continue.",
                "warning"
            )

            return redirect(
                url_for("admin_login")
            )

        return view(*args, **kwargs)

    return protected_view


# ==========================================================
# CSRF PROTECTION
# ==========================================================

def get_csrf_token():

    if "csrf_token" not in session:

        session["csrf_token"] = (
            secrets.token_urlsafe(32)
        )

    return session["csrf_token"]


def validate_csrf_token():

    submitted = request.form.get(
        "csrf_token",
        ""
    )

    expected = session.get(
        "csrf_token",
        ""
    )

    if not submitted or not expected:

        abort(400)

    if not hmac.compare_digest(
        submitted,
        expected
    ):

        abort(400)


app.jinja_env.globals["csrf_token"] = get_csrf_token


# ==========================================================
# HOMEPAGE
# ==========================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# ==========================================================
# SKIN ANALYSIS
# ==========================================================

@app.route("/skin-analysis")
def skin_analysis():

    return render_template(
        "skin_analysis.html"
    )


# ==========================================================
# SEARCH HELPERS
# ==========================================================

def get_page_number():

    try:

        page = int(
            request.args.get("page", 1)
        )

    except (ValueError, TypeError):

        page = 1

    return max(
        1,
        min(page, 100000)
    )


def escaped_search_term(search):

    escaped = (
        search.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )

    return f"%{escaped}%"


# ==========================================================
# PRODUCT CATALOG
# NOW INCLUDES CUSTOMER RATINGS
# ==========================================================

@app.route("/products")
def products():

    search = request.args.get(
        "search",
        ""
    ).strip()[:100]

    category = request.args.get(
        "category",
        ""
    ).strip()

    status = request.args.get(
        "status",
        ""
    ).strip()

    page = get_page_number()

    per_page = 12

    if status not in {
        "pending",
        "approved",
        "rejected"
    }:

        status = ""

    conn = get_db_connection()

    try:

        # ------------------------------------------
        # AVAILABLE PRODUCT CATEGORIES
        # ------------------------------------------

        category_rows = conn.execute(
            """
            SELECT DISTINCT category

            FROM products

            WHERE category IS NOT NULL
              AND TRIM(category) != ''

            ORDER BY category
            """
        ).fetchall()

        categories = [
            row["category"]
            for row in category_rows
        ]

        if category not in categories:

            category = ""

        # ------------------------------------------
        # BUILD SEARCH CONDITIONS
        # ------------------------------------------

        conditions = []

        parameters = []

        if search:

            keyword = escaped_search_term(
                search
            )

            conditions.append(
                """
                (
                    product_name LIKE ?
                        ESCAPE '\\' COLLATE NOCASE

                    OR brand LIKE ?
                        ESCAPE '\\' COLLATE NOCASE

                    OR ingredients LIKE ?
                        ESCAPE '\\' COLLATE NOCASE
                )
                """
            )

            parameters.extend([
                keyword,
                keyword,
                keyword
            ])

        if category:

            conditions.append(
                "category = ?"
            )

            parameters.append(
                category
            )

        if status:

            conditions.append(
                "verification_status = ?"
            )

            parameters.append(
                status
            )

        where_clause = (
            " WHERE " + " AND ".join(conditions)
            if conditions else ""
        )

        # ------------------------------------------
        # COUNT MATCHING PRODUCTS
        # ------------------------------------------

        matching_count = conn.execute(
            """
            SELECT COUNT(*) AS total

            FROM products
            """
            + where_clause,
            parameters
        ).fetchone()["total"]

        total_pages = max(
            1,
            math.ceil(
                matching_count / per_page
            )
        )

        page = min(
            page,
            total_pages
        )

        offset = (
            page - 1
        ) * per_page

        # ------------------------------------------
        # FETCH PRODUCTS AND APPROVED REVIEW RATINGS
        # ------------------------------------------

        # Only approved customer reviews contribute
        # to the public rating.
        #
        # Pending and rejected reviews are excluded.

        product_rows = conn.execute(
            """
            SELECT

                p.id,
                p.barcode,
                p.product_name,
                p.brand,
                p.category,
                p.ingredients,
                p.quantity,
                p.source_url,
                p.image_url,
                p.price_inr,
                p.price_source_url,
                p.price_checked_at,
                p.verification_status,

                COALESCE(
                    ratings.review_count,
                    0
                ) AS review_count,

                ratings.average_rating

            FROM products AS p

            LEFT JOIN (

                SELECT

                    product_id,

                    COUNT(*) AS review_count,

                    AVG(rating) AS average_rating

                FROM reviews

                WHERE moderation_status = 'approved'

                GROUP BY product_id

            ) AS ratings

            ON ratings.product_id = p.id
            """
            + where_clause
            + """
            ORDER BY p.updated_at DESC, p.id DESC

            LIMIT ? OFFSET ?
            """,
            parameters + [
                per_page,
                offset
            ]
        ).fetchall()

    finally:

        conn.close()

    stats = get_database_stats()

    return render_template(
        "products.html",
        products=product_rows,
        stats=stats,
        search=search,
        category=category,
        status=status,
        categories=categories,
        page=page,
        total_pages=total_pages,
        matching_count=matching_count
    )


# ==========================================================
# ADMIN LOGIN
# ==========================================================

@app.route(
    "/admin/login",
    methods=["GET", "POST"]
)
def admin_login():

    if not ADMIN_CONFIGURED:

        return (
            "Admin credentials are not configured.",
            503
        )

    if session.get("admin_logged_in"):

        return redirect(
            url_for("admin_dashboard")
        )

    if request.method == "POST":

        validate_csrf_token()

        username = request.form.get(
            "username",
            ""
        )

        password = request.form.get(
            "password",
            ""
        )

        username_valid = hmac.compare_digest(
            username,
            ADMIN_USERNAME
        )

        password_valid = hmac.compare_digest(
            password,
            ADMIN_PASSWORD
        )

        if username_valid and password_valid:

            session.clear()

            session["admin_logged_in"] = True

            session["admin_username"] = (
                ADMIN_USERNAME
            )

            session["csrf_token"] = (
                secrets.token_urlsafe(32)
            )

            return redirect(
                url_for("admin_dashboard")
            )

        flash(
            "Invalid username or password.",
            "error"
        )

    return render_template(
        "admin.html",
        login_page=True,
        admin_configured=ADMIN_CONFIGURED
    )


# ==========================================================
# ADMIN DASHBOARD
# ==========================================================

@app.route("/admin")
@admin_login_required
def admin_dashboard():

    search = request.args.get(
        "search",
        ""
    ).strip()[:100]

    status = request.args.get(
        "status",
        "pending"
    ).strip()

    if status not in {
        "",
        "pending",
        "approved",
        "rejected"
    }:

        status = "pending"

    page = get_page_number()

    per_page = 10

    conditions = []

    parameters = []

    if search:

        keyword = escaped_search_term(
            search
        )

        conditions.append(
            """
            (
                product_name LIKE ?
                    ESCAPE '\\' COLLATE NOCASE

                OR brand LIKE ?
                    ESCAPE '\\' COLLATE NOCASE

                OR barcode LIKE ?
                    ESCAPE '\\' COLLATE NOCASE
            )
            """
        )

        parameters.extend([
            keyword,
            keyword,
            keyword
        ])

    if status:

        conditions.append(
            "verification_status = ?"
        )

        parameters.append(
            status
        )

    where_clause = (
        " WHERE " + " AND ".join(conditions)
        if conditions else ""
    )

    conn = get_db_connection()

    try:

        total_matching = conn.execute(
            """
            SELECT COUNT(*) AS total

            FROM products
            """
            + where_clause,
            parameters
        ).fetchone()["total"]

        total_pages = max(
            1,
            math.ceil(
                total_matching / per_page
            )
        )

        page = min(
            page,
            total_pages
        )

        offset = (
            page - 1
        ) * per_page

        product_rows = conn.execute(
            """
            SELECT

                id,
                barcode,
                product_name,
                brand,
                category,
                ingredients,
                quantity,
                source_url,
                image_url,
                price_inr,
                price_source_url,
                price_checked_at,
                verification_status

            FROM products
            """
            + where_clause
            + """
            ORDER BY updated_at DESC, id DESC

            LIMIT ? OFFSET ?
            """,
            parameters + [
                per_page,
                offset
            ]
        ).fetchall()

    finally:

        conn.close()

    return render_template(
        "admin.html",
        login_page=False,
        products=product_rows,
        stats=get_database_stats(),
        search=search,
        status=status,
        page=page,
        total_pages=total_pages,
        total_matching=total_matching
    )


# ==========================================================
# APPROVE ALL PRODUCTS
# ==========================================================

@app.route(
    "/admin/approve-all",
    methods=["POST"]
)
@admin_login_required
def approve_all_products():

    validate_csrf_token()

    confirmation = request.form.get(
        "confirmation",
        ""
    )

    if confirmation != "APPROVE_ALL":

        flash(
            "Bulk approval confirmation failed.",
            "error"
        )

        return redirect(
            url_for("admin_dashboard")
        )

    conn = get_db_connection()

    try:

        result = conn.execute(
            """
            UPDATE products

            SET
                verification_status = 'approved',
                updated_at = CURRENT_TIMESTAMP

            WHERE verification_status = 'pending'
            """
        )

        approved_count = result.rowcount

        conn.commit()

    except Exception:

        conn.rollback()
        raise

    finally:

        conn.close()

    flash(
        f"{approved_count} products approved "
        "for catalog use. Product information "
        "has not been independently verified.",
        "success"
    )

    return redirect(
        url_for(
            "admin_dashboard",
            status="approved"
        )
    )


# ==========================================================
# UPDATE PRODUCT APPROVAL STATUS
# ==========================================================

@app.route(
    "/admin/product/<int:product_id>/status",
    methods=["POST"]
)
@admin_login_required
def update_product_status(product_id):

    validate_csrf_token()

    new_status = request.form.get(
        "new_status",
        ""
    )

    if new_status not in {
        "pending",
        "approved",
        "rejected"
    }:

        abort(400)

    conn = get_db_connection()

    try:

        result = conn.execute(
            """
            UPDATE products

            SET
                verification_status = ?,
                updated_at = CURRENT_TIMESTAMP

            WHERE id = ?
            """,
            (
                new_status,
                product_id
            )
        )

        if result.rowcount == 0:
            abort(404)

        conn.commit()

    except Exception:

        conn.rollback()
        raise

    finally:

        conn.close()

    flash(
        f"Product updated to {new_status}.",
        "success"
    )

    return redirect(
        url_for("admin_dashboard")
    )


# ==========================================================
# UPDATE PRODUCT PRICE
# ==========================================================

@app.route(
    "/admin/product/<int:product_id>/price",
    methods=["POST"]
)
@admin_login_required
def update_product_price(product_id):

    validate_csrf_token()

    action = request.form.get(
        "action",
        "save"
    )

    if action not in {
        "save",
        "clear"
    }:

        abort(400)

    conn = get_db_connection()

    try:

        existing = conn.execute(
            """
            SELECT id

            FROM products

            WHERE id = ?
            """,
            (product_id,)
        ).fetchone()

        if existing is None:
            abort(404)

        if action == "clear":

            conn.execute(
                """
                UPDATE products

                SET
                    price_inr = NULL,
                    price_source_url = NULL,
                    price_checked_at = NULL,
                    updated_at = CURRENT_TIMESTAMP

                WHERE id = ?
                """,
                (product_id,)
            )

            message = "Product price removed."

        else:

            price_text = request.form.get(
                "price_inr",
                ""
            ).strip()

            source_url = request.form.get(
                "price_source_url",
                ""
            ).strip()

            try:

                price = Decimal(
                    price_text
                )

            except (InvalidOperation, ValueError):

                flash(
                    "Enter a valid price.",
                    "error"
                )

                return redirect(
                    url_for(
                        "admin_dashboard",
                        status=""
                    )
                )

            if (
                not price.is_finite()
                or price <= 0
                or price > 1000000
                or price.as_tuple().exponent < -2
            ):

                flash(
                    "Enter a positive price "
                    "with up to two decimal places.",
                    "error"
                )

                return redirect(
                    url_for(
                        "admin_dashboard",
                        status=""
                    )
                )

            parsed = urlparse(
                source_url
            )

            if (
                len(source_url) > 1000
                or parsed.scheme != "https"
                or not parsed.hostname
                or parsed.username is not None
                or parsed.password is not None
            ):

                flash(
                    "Enter a valid HTTPS price source.",
                    "error"
                )

                return redirect(
                    url_for(
                        "admin_dashboard",
                        status=""
                    )
                )

            conn.execute(
                """
                UPDATE products

                SET
                    price_inr = ?,
                    price_source_url = ?,
                    price_checked_at = DATE('now'),
                    updated_at = CURRENT_TIMESTAMP

                WHERE id = ?
                """,
                (
                    float(price),
                    source_url,
                    product_id
                )
            )

            message = (
                "Product price saved successfully."
            )

        conn.commit()

    except Exception:

        conn.rollback()
        raise

    finally:

        conn.close()

    flash(
        message,
        "success"
    )

    return redirect(
        url_for(
            "admin_dashboard",
            status=""
        )
    )


# ==========================================================
# ADMIN LOGOUT
# ==========================================================

@app.route(
    "/admin/logout",
    methods=["POST"]
)
@admin_login_required
def admin_logout():

    validate_csrf_token()

    session.clear()

    flash(
        "Logged out successfully.",
        "success"
    )

    return redirect(
        url_for("admin_login")
    )


# ==========================================================
# RUN APPLICATION
# ==========================================================

if __name__ == "__main__":

    app.run(debug=True)