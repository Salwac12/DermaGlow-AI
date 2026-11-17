# ==========================================================
# DERMAGLOW AI
# AUTOMATIC SKINCARE PRODUCT IMPORTER WITH IMAGES
#
# Developer: Salwa Choudhari
# ==========================================================

import json
import os
import time
import sqlite3
import urllib.error
import urllib.parse
import urllib.request

from database import (
    create_database,
    get_db_connection,
    get_database_stats
)


# ==========================================================
# CONFIGURATION
# ==========================================================

API_URL = (
    "https://world.openbeautyfacts.org/api/v2/search"
)

CONTACT = os.getenv(
    "DERMAGLOW_CONTACT",
    "educational-project"
)

USER_AGENT = (
    f"DermaGlowAI/0.3 "
    f"(skincare catalog; {CONTACT})"
)

PAGE_SIZE = 100

MAX_PAGES = 10

REQUEST_DELAY = 7

REQUEST_TIMEOUT = 30

MAX_RETRIES = 3


# ==========================================================
# API FIELDS
# ==========================================================

PRODUCT_FIELDS = [

    "code",
    "product_name",
    "product_name_en",
    "generic_name",
    "brands",
    "categories",
    "categories_tags",
    "countries_tags",
    "ingredients_text",
    "ingredients_text_en",
    "quantity",

    # Product images

    "image_front_url",
    "image_front_small_url",
    "image_url"

]


# ==========================================================
# SKINCARE KEYWORDS
# ==========================================================

SKINCARE_KEYWORDS = [

    "skincare",
    "skin care",

    "face wash",
    "facewash",

    "face cleanser",
    "facial cleanser",

    "cleansing gel",
    "cleansing foam",
    "cleansing milk",

    "micellar water",

    "moisturizer",
    "moisturiser",

    "moisturizing cream",
    "moisturising cream",

    "hydrating cream",
    "face cream",
    "facial cream",
    "face lotion",

    "face serum",
    "facial serum",
    "skin serum",

    "vitamin c serum",
    "niacinamide serum",
    "hyaluronic acid serum",

    "sunscreen",
    "sunblock",
    "sun cream",
    "sun protection",

    "spf 30",
    "spf 50",

    "face toner",
    "facial toner",

    "face mask",
    "facial mask",
    "sheet mask",

    "face exfoliant",
    "facial exfoliant",

    "serum"

]


EXCLUDED_KEYWORDS = [

    "shampoo",
    "conditioner",
    "hair dye",
    "hair color",
    "hair colour",
    "hair spray",
    "hair oil",

    "mascara",
    "eyeliner",
    "lipstick",
    "lip gloss",

    "nail polish",
    "nail varnish",

    "perfume",
    "deodorant",

    "toothpaste",
    "mouthwash"

]


# ==========================================================
# TEXT CLEANING
# ==========================================================

def clean_text(value):

    if value is None:
        return ""

    if isinstance(value, list):

        return ", ".join(
            str(item)
            for item in value
        ).strip()

    return str(value).strip()


# ==========================================================
# PRODUCT NAME
# ==========================================================

def get_product_name(product):

    for field in [

        "product_name",
        "product_name_en",
        "generic_name"

    ]:

        value = clean_text(
            product.get(field)
        )

        if value:
            return value

    return ""


# ==========================================================
# INDIA TAG
# ==========================================================

def is_indian_product(product):

    tags = product.get(
        "countries_tags",
        []
    )

    if not isinstance(tags, list):
        return False

    return "en:india" in [
        str(tag).lower().strip()
        for tag in tags
    ]


# ==========================================================
# SKINCARE FILTER
# ==========================================================

def is_skincare_product(product):

    name = get_product_name(product)

    categories = clean_text(
        product.get("categories")
    )

    category_tags = clean_text(
        product.get("categories_tags")
    )

    text = (
        name + " " +
        categories + " " +
        category_tags
    ).lower()

    if any(
        keyword in text
        for keyword in EXCLUDED_KEYWORDS
    ):
        return False

    return any(
        keyword in text
        for keyword in SKINCARE_KEYWORDS
    )


# ==========================================================
# DETECT PRODUCT CATEGORY
# ==========================================================

def detect_category(product):

    name = get_product_name(product)

    categories = clean_text(
        product.get("categories")
    )

    text = (
        name + " " + categories
    ).lower()

    if any(
        word in text
        for word in [
            "sunscreen",
            "sunblock",
            "sun cream",
            "sun protection",
            "spf 30",
            "spf 50"
        ]
    ):
        return "Sunscreen"

    if any(
        word in text
        for word in [
            "face wash",
            "facewash",
            "cleanser",
            "cleansing",
            "micellar"
        ]
    ):
        return "Face Wash"

    if any(
        word in text
        for word in [
            "moisturizer",
            "moisturiser",
            "moisturizing",
            "moisturising",
            "face cream",
            "hydrating cream"
        ]
    ):
        return "Moisturizer"

    if "serum" in text:
        return "Serum"

    if "toner" in text:
        return "Toner"

    if any(
        word in text
        for word in [
            "face mask",
            "facial mask",
            "sheet mask"
        ]
    ):
        return "Face Mask"

    if "exfoliant" in text:
        return "Exfoliant"

    return categories or "Other Skincare"


# ==========================================================
# VALIDATE PRODUCT IMAGE URL
# ==========================================================

def valid_image_url(value):

    url = clean_text(value)

    if not url:
        return ""

    try:

        parsed = urllib.parse.urlparse(url)

        if parsed.scheme != "https":
            return ""

        if parsed.hostname not in {
            "images.openbeautyfacts.org",
            "static.openbeautyfacts.org"
        }:
            return ""

        if not parsed.path.startswith("/"):
            return ""

        return url

    except ValueError:

        return ""


# ==========================================================
# GET PRODUCT IMAGE
# ==========================================================

def get_product_image(product):

    image_fields = [

        "image_front_url",
        "image_front_small_url",
        "image_url"

    ]

    for field in image_fields:

        image = valid_image_url(
            product.get(field)
        )

        if image:
            return image

    return ""


# ==========================================================
# FETCH API PAGE
# ==========================================================

def fetch_page(page_number):

    parameters = {

        "countries_tags_en": "india",

        "page": page_number,

        "page_size": PAGE_SIZE,

        "fields": ",".join(
            PRODUCT_FIELDS
        )

    }

    url = (
        API_URL + "?" +
        urllib.parse.urlencode(parameters)
    )

    request = urllib.request.Request(

        url,

        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json"
        }

    )

    for attempt in range(
        1,
        MAX_RETRIES + 1
    ):

        try:

            with urllib.request.urlopen(
                request,
                timeout=REQUEST_TIMEOUT
            ) as response:

                data = json.loads(
                    response.read().decode("utf-8")
                )

                if not isinstance(data, dict):
                    raise RuntimeError(
                        "Unexpected API response."
                    )

                products = data.get(
                    "products",
                    []
                )

                if not isinstance(products, list):
                    raise RuntimeError(
                        "Invalid product response."
                    )

                return data

        except urllib.error.HTTPError as error:

            if error.code not in {
                429, 500, 502, 503, 504
            }:
                raise

            if attempt == MAX_RETRIES:
                raise

            retry_after = error.headers.get(
                "Retry-After"
            )

            try:
                wait = int(retry_after)
            except (ValueError, TypeError):
                wait = REQUEST_DELAY * attempt

            wait = max(
                REQUEST_DELAY,
                min(wait, 120)
            )

            print(
                f"Temporary API error. "
                f"Retrying after {wait} seconds."
            )

            time.sleep(wait)

        except (
            urllib.error.URLError,
            TimeoutError
        ):

            if attempt == MAX_RETRIES:
                raise

            wait = REQUEST_DELAY * attempt

            print(
                f"Network problem. "
                f"Retrying after {wait} seconds."
            )

            time.sleep(wait)

    raise RuntimeError(
        "Unable to fetch product data."
    )


# ==========================================================
# SAVE PRODUCT
# ==========================================================

def save_product(conn, product):

    if not isinstance(product, dict):
        return "skipped"

    barcode = clean_text(
        product.get("code")
    )

    if not barcode or not barcode.isdigit():
        return "skipped"

    if not is_indian_product(product):
        return "skipped"

    name = get_product_name(product)

    if not name:
        return "skipped"

    if not is_skincare_product(product):
        return "skipped"

    brand = clean_text(
        product.get("brands")
    )

    category = detect_category(product)

    ingredients = clean_text(
        product.get("ingredients_text_en")
        or product.get("ingredients_text")
    )

    quantity = clean_text(
        product.get("quantity")
    )

    image_url = get_product_image(product)

    source_url = (
        "https://world.openbeautyfacts.org/product/"
        + barcode
    )

    existing = conn.execute(
        """
        SELECT id, verification_status, image_url
        FROM products
        WHERE barcode = ?
        """,
        (barcode,)
    ).fetchone()

    # ======================================================
    # EXISTING PRODUCT
    # ======================================================

    if existing:

        # Preserve previously approved/rejected records.
        # Only enrich their image information.

        if existing["verification_status"] != "pending":

            if image_url:

                conn.execute(
                    """
                    UPDATE products
                    SET image_url = ?
                    WHERE barcode = ?
                      AND (
                          image_url IS NULL
                          OR image_url != ?
                      )
                    """,
                    (
                        image_url,
                        barcode,
                        image_url
                    )
                )

                return "image_updated"

            return "skipped"

        # Update pending product information.
        # Preserve its existing photo if the API
        # no longer returns an image.

        conn.execute(
            """
            UPDATE products

            SET
                product_name = ?,
                brand = ?,
                category = ?,
                ingredients = ?,
                quantity = ?,
                source_url = ?,
                image_url = CASE
                    WHEN ? != '' THEN ?
                    ELSE image_url
                END,
                india_tagged = 1,
                updated_at = CURRENT_TIMESTAMP

            WHERE barcode = ?
            """,
            (
                name,
                brand,
                category,
                ingredients,
                quantity,
                source_url,
                image_url,
                image_url,
                barcode
            )
        )

        return "updated"

    # ======================================================
    # NEW PRODUCT
    # ======================================================

    conn.execute(
        """
        INSERT INTO products (

            barcode,
            product_name,
            brand,
            category,
            ingredients,
            quantity,
            source_url,
            image_url,
            india_tagged,
            verification_status

        )

        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, 1, 'pending'
        )
        """,
        (
            barcode,
            name,
            brand,
            category,
            ingredients,
            quantity,
            source_url,
            image_url
        )
    )

    return "added"


# ==========================================================
# IMPORT PRODUCTS
# ==========================================================

def import_products():

    create_database()

    print()
    print("====================================")
    print("DERMAGLOW AI - PRODUCT IMAGE IMPORT")
    print("====================================")

    print("Maximum Pages:", MAX_PAGES)
    print("Page Size:", PAGE_SIZE)

    conn = get_db_connection()

    totals = {
        "added": 0,
        "updated": 0,
        "image_updated": 0,
        "skipped": 0
    }

    received_total = 0
    completed_pages = 0

    try:

        for page in range(
            1,
            MAX_PAGES + 1
        ):

            print()
            print(
                f"Fetching page {page}/{MAX_PAGES}..."
            )

            try:

                data = fetch_page(page)

            except Exception as error:

                print(
                    "Import stopped:",
                    error
                )

                break

            products = data.get(
                "products",
                []
            )

            if not products:

                print("No more products returned.")
                break

            page_stats = {
                key: 0
                for key in totals
            }

            try:

                for product in products:

                    result = save_product(
                        conn,
                        product
                    )

                    page_stats[result] += 1

                conn.commit()

            except sqlite3.DatabaseError:

                conn.rollback()
                raise

            received_total += len(products)
            completed_pages += 1

            for key, value in page_stats.items():
                totals[key] += value

            print(
                "Received:",
                len(products)
            )

            print(
                "New products:",
                page_stats["added"]
            )

            print(
                "Pending products updated:",
                page_stats["updated"]
            )

            print(
                "Approved/rejected image records processed:",
                page_stats["image_updated"]
            )

            print(
                "Skipped:",
                page_stats["skipped"]
            )

            available = data.get("count")

            if (
                isinstance(available, int)
                and page * PAGE_SIZE >= available
            ):
                break

            if len(products) < PAGE_SIZE:
                break

            if page < MAX_PAGES:

                print(
                    f"Waiting {REQUEST_DELAY} seconds..."
                )

                time.sleep(
                    REQUEST_DELAY
                )

    finally:

        conn.close()

    stats = get_database_stats()

    print()
    print("====================================")
    print("IMPORT COMPLETED")
    print("====================================")

    print(
        "Pages Completed:",
        completed_pages
    )

    print(
        "Records Received:",
        received_total
    )

    print(
        "Products Added:",
        totals["added"]
    )

    print(
        "Products Updated:",
        totals["updated"]
    )

    print(
        "Total Products:",
        stats["total"]
    )

    print(
        "Products With Images:",
        stats["with_images"]
    )

    print(
        "Approved Products:",
        stats["approved"]
    )

    print()
    print(
        "Existing product approvals have been preserved."
    )

    print(
        "New products remain pending verification."
    )


# ==========================================================
# RUN IMPORTER
# ==========================================================

if __name__ == "__main__":

    try:
        import_products()

    except Exception as error:

        print(
            "Import failed:",
            error
        )