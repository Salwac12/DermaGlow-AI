# ==========================================================
# DERMAGLOW AI - CUSTOMER REVIEWS
# Developer: Salwa Choudhari
# ==========================================================

import hmac

from flask import (
    Blueprint,
    request,
    render_template,
    redirect,
    url_for,
    session,
    flash,
    abort
)

from database import (
    get_db_connection,
    get_review_stats
)


reviews_bp = Blueprint(
    "reviews",
    __name__
)


# ==========================================================
# CSRF VALIDATION
# ==========================================================

def verify_csrf():

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


# ==========================================================
# REVIEW PAGE
# ==========================================================

@reviews_bp.route("/reviews")
def review_page():

    try:
        product_id = int(
            request.args.get("product_id", 0)
        )
    except (ValueError, TypeError):
        product_id = 0

    conn = get_db_connection()

    try:

        # Products eligible for public reviews

        products = conn.execute("""
            SELECT id, product_name, brand
            FROM products
            WHERE verification_status = 'approved'
            ORDER BY product_name COLLATE NOCASE
            LIMIT 200
        """).fetchall()

        # Products can also be opened by their
        # exact ID, even when they are not among
        # the first 200 dropdown entries.

        selected_product = conn.execute("""
            SELECT id, product_name, brand,
                   category, image_url
            FROM products
            WHERE id = ?
              AND verification_status = 'approved'
        """, (product_id,)).fetchone()

        approved_reviews = []

        average_rating = None

        review_count = 0

        if selected_product:

            approved_reviews = conn.execute("""
                SELECT
                    reviewer_name,
                    rating,
                    review_title,
                    review_text,
                    created_at

                FROM reviews

                WHERE product_id = ?
                  AND moderation_status = 'approved'

                ORDER BY created_at DESC, id DESC

                LIMIT 50
            """, (product_id,)).fetchall()

            rating_row = conn.execute("""
                SELECT
                    COUNT(*) AS review_count,
                    AVG(rating) AS average_rating

                FROM reviews

                WHERE product_id = ?
                  AND moderation_status = 'approved'
            """, (product_id,)).fetchone()

            review_count = rating_row["review_count"]

            average_rating = rating_row["average_rating"]

        # Only authenticated admins may see
        # reviews awaiting moderation.

        pending_reviews = []

        if session.get("admin_logged_in"):

            pending_reviews = conn.execute("""
                SELECT
                    reviews.id,
                    reviews.product_id,
                    reviews.reviewer_name,
                    reviews.rating,
                    reviews.review_title,
                    reviews.review_text,
                    reviews.created_at,
                    products.product_name

                FROM reviews

                JOIN products
                  ON reviews.product_id = products.id

                WHERE reviews.moderation_status = 'pending'

                ORDER BY reviews.created_at ASC,
                         reviews.id ASC

                LIMIT 50
            """).fetchall()

    finally:
        conn.close()

    return render_template(
        "reviews.html",
        products=products,
        selected_product=selected_product,
        approved_reviews=approved_reviews,
        average_rating=average_rating,
        review_count=review_count,
        pending_reviews=pending_reviews,
        review_stats=get_review_stats(),
        is_admin=bool(
            session.get("admin_logged_in")
        )
    )


# ==========================================================
# SUBMIT CUSTOMER REVIEW
# ==========================================================

@reviews_bp.route(
    "/reviews/submit",
    methods=["POST"]
)
def submit_review():

    verify_csrf()

    # Simple honeypot field.
    # Normal users won't fill this field.

    if request.form.get("website", "").strip():

        return redirect(
            url_for("reviews.review_page")
        )

    try:

        product_id = int(
            request.form.get("product_id", "")
        )

        rating = int(
            request.form.get("rating", "")
        )

    except (ValueError, TypeError):

        flash(
            "Please select a product and rating.",
            "error"
        )

        return redirect(
            url_for("reviews.review_page")
        )

    reviewer_name = request.form.get(
        "reviewer_name",
        ""
    ).strip()

    review_title = request.form.get(
        "review_title",
        ""
    ).strip()

    review_text = request.form.get(
        "review_text",
        ""
    ).strip()

    if not 1 <= rating <= 5:

        flash(
            "Rating must be between 1 and 5 stars.",
            "error"
        )

        return redirect(
            url_for(
                "reviews.review_page",
                product_id=product_id
            )
        )

    if not 2 <= len(reviewer_name) <= 50:

        flash(
            "Your display name must contain "
            "2–50 characters.",
            "error"
        )

        return redirect(
            url_for(
                "reviews.review_page",
                product_id=product_id
            )
        )

    if not 3 <= len(review_title) <= 100:

        flash(
            "Review title must contain "
            "3–100 characters.",
            "error"
        )

        return redirect(
            url_for(
                "reviews.review_page",
                product_id=product_id
            )
        )

    if not 15 <= len(review_text) <= 2000:

        flash(
            "Review must contain "
            "15–2000 characters.",
            "error"
        )

        return redirect(
            url_for(
                "reviews.review_page",
                product_id=product_id
            )
        )

    conn = get_db_connection()

    try:

        product = conn.execute("""
            SELECT id
            FROM products
            WHERE id = ?
              AND verification_status = 'approved'
        """, (product_id,)).fetchone()

        if not product:

            flash(
                "This product is not available "
                "for reviews.",
                "error"
            )

            return redirect(
                url_for("reviews.review_page")
            )

        conn.execute("""
            INSERT INTO reviews (
                product_id,
                reviewer_name,
                rating,
                review_title,
                review_text,
                moderation_status
            )

            VALUES (?, ?, ?, ?, ?, 'pending')
        """, (
            product_id,
            reviewer_name,
            rating,
            review_title,
            review_text
        ))

        conn.commit()

    finally:
        conn.close()

    flash(
        "Thank you! Your review has been submitted "
        "and is awaiting moderation.",
        "success"
    )

    return redirect(
        url_for(
            "reviews.review_page",
            product_id=product_id
        )
    )


# ==========================================================
# ADMIN REVIEW MODERATION
# ==========================================================

@reviews_bp.route(
    "/reviews/<int:review_id>/moderate",
    methods=["POST"]
)
def moderate_review(review_id):

    if not session.get("admin_logged_in"):

        return redirect(
            url_for("admin_login")
        )

    verify_csrf()

    new_status = request.form.get(
        "new_status",
        ""
    )

    if new_status not in {
        "approved",
        "rejected"
    }:
        abort(400)

    conn = get_db_connection()

    try:

        result = conn.execute("""
            UPDATE reviews

            SET
                moderation_status = ?,
                moderated_at = CURRENT_TIMESTAMP

            WHERE id = ?
              AND moderation_status = 'pending'
        """, (
            new_status,
            review_id
        ))

        if result.rowcount == 0:
            abort(404)

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

    flash(
        f"Review {new_status} successfully.",
        "success"
    )

    return redirect(
        url_for("reviews.review_page")
    )