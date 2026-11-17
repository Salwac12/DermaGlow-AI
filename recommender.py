# ==========================================================
# DERMAGLOW AI
# PERSONALIZED SKINCARE RECOMMENDATION & ROUTINE ENGINE
#
# Developer: Salwa Choudhari
#
# Features:
# - Questionnaire validation
# - Approved product recommendations
# - Ingredient exclusion checks
# - Morning skincare routine
# - Night skincare routine
# - Product matching
# - Clear safety limitations
# ==========================================================

from database import get_db_connection


# ==========================================================
# ALLOWED USER OPTIONS
# ==========================================================

ALLOWED_CATEGORIES = {
    "Face Wash",
    "Moisturizer",
    "Sunscreen",
    "Serum"
}

ALLOWED_SKIN_TYPES = {
    "Oily",
    "Dry",
    "Combination",
    "Normal",
    "Not Sure"
}

ALLOWED_SENSITIVITIES = {
    "Low",
    "Moderate",
    "High",
    "Not Sure"
}

ALLOWED_CONCERNS = {
    "Acne",
    "Dark Spots",
    "Dryness",
    "Excess Oil",
    "Uneven Skin Tone",
    "Fine Lines",
    "Dullness",
    "Redness"
}


# ==========================================================
# INGREDIENT SEARCH KEYWORDS
# ==========================================================

# These keywords help organize product records.
# Their presence does not prove suitability, safety,
# effectiveness, or medical benefit.

CONCERN_INGREDIENTS = {

    "Dryness": [
        "glycerin",
        "hyaluronic acid",
        "ceramide",
        "squalane"
    ],

    "Excess Oil": [
        "niacinamide"
    ],

    "Dark Spots": [
        "niacinamide",
        "ascorbic acid",
        "vitamin c"
    ],

    "Dullness": [
        "glycerin",
        "hyaluronic acid"
    ],

    "Uneven Skin Tone": [
        "niacinamide",
        "ascorbic acid"
    ]

}


# ==========================================================
# INPUT HELPERS
# ==========================================================

def clean_value(value, maximum=200):

    if not isinstance(value, str):
        return ""

    return value.strip()[:maximum]


def clean_list(values, allowed):

    if not isinstance(values, list):
        return []

    result = []

    for value in values:

        if (
            isinstance(value, str)
            and value in allowed
            and value not in result
        ):

            result.append(value)

    return result


# ==========================================================
# VALIDATE QUESTIONNAIRE
# ==========================================================

def validate_profile(data):

    if not isinstance(data, dict):

        raise ValueError(
            "Invalid skincare profile."
        )

    skin_type = clean_value(
        data.get("skin_type")
    )

    sensitivity = clean_value(
        data.get("sensitivity")
    )

    if skin_type not in ALLOWED_SKIN_TYPES:

        raise ValueError(
            "Please select a valid skin type."
        )

    if sensitivity not in ALLOWED_SENSITIVITIES:

        raise ValueError(
            "Please select a valid sensitivity level."
        )

    concerns = clean_list(
        data.get("concerns", []),
        ALLOWED_CONCERNS
    )

    products = clean_list(
        data.get("products", []),
        ALLOWED_CATEGORIES
    )

    if not products:

        raise ValueError(
            "Please select at least one product category."
        )

    try:

        budget = int(
            data.get("budget")
        )

    except (ValueError, TypeError):

        raise ValueError(
            "Please select a valid budget."
        )

    if budget < 300 or budget > 5000:

        raise ValueError(
            "Budget must be between ₹300 and ₹5,000."
        )

    avoid_text = clean_value(
        data.get("avoid_ingredients"),
        500
    )

    exclusions = []

    for item in avoid_text.split(","):

        item = item.strip().lower()

        if item and item not in exclusions:

            exclusions.append(item)

    exclusions = exclusions[:20]

    return {

        "skin_type": skin_type,

        "sensitivity": sensitivity,

        "concerns": concerns,

        "products": products,

        "budget": budget,

        "avoid_ingredients": avoid_text,

        "exclusions": exclusions

    }


# ==========================================================
# INGREDIENT KEYWORD MATCHING
# ==========================================================

def ingredient_relevance(
    ingredients,
    concerns
):

    ingredient_text = (
        ingredients or ""
    ).lower()

    matched = []

    for concern in concerns:

        keywords = CONCERN_INGREDIENTS.get(
            concern,
            []
        )

        for keyword in keywords:

            if (
                keyword in ingredient_text
                and keyword not in matched
            ):

                matched.append(keyword)

    return matched


# ==========================================================
# FETCH APPROVED PRODUCTS
# ==========================================================

def fetch_approved_products():

    conn = get_db_connection()

    try:

        rows = conn.execute(
            """
            SELECT
                id,
                barcode,
                product_name,
                brand,
                category,
                ingredients,
                quantity,
                source_url

            FROM products

            WHERE verification_status = 'approved'

            ORDER BY product_name COLLATE NOCASE
            """
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:

        conn.close()


# ==========================================================
# PRODUCT ELIGIBILITY
# ==========================================================

def product_is_eligible(
    product,
    profile
):

    category = product.get("category")

    if category not in profile["products"]:

        return False

    ingredients = (
        product.get("ingredients")
        or ""
    )

    exclusions = profile["exclusions"]

    # When exclusions are present, records with
    # missing ingredient lists are not eligible.

    if exclusions and not ingredients:

        return False

    ingredient_text = ingredients.lower()

    for excluded in exclusions:

        if excluded in ingredient_text:

            return False

    return True


# ==========================================================
# RECOMMEND PRODUCTS
# ==========================================================

def get_recommendations(profile):

    approved_products = (
        fetch_approved_products()
    )

    recommendations = []

    for category in profile["products"]:

        candidates = []

        for product in approved_products:

            if product.get("category") != category:

                continue

            if not product_is_eligible(
                product,
                profile
            ):

                continue

            ingredients = (
                product.get("ingredients")
                or ""
            )

            matched = ingredient_relevance(
                ingredients,
                profile["concerns"]
            )

            reasons = [

                (
                    "Matches your requested "
                    + category.lower()
                    + " category."
                ),

                (
                    "Included in the administrator-"
                    "approved product catalog."
                )

            ]

            if matched:

                reasons.append(
                    "Contains relevant ingredient "
                    "keywords: "
                    + ", ".join(matched)
                    + "."
                )

            if profile["exclusions"]:

                reasons.append(
                    "No matching exclusion terms were "
                    "found in the available ingredient "
                    "text. This is not an allergy-safety "
                    "guarantee."
                )

            candidates.append({

                "id": product["id"],

                "name": (
                    product["product_name"]
                    or "Unnamed product"
                ),

                "brand": (
                    product["brand"]
                    or "Brand not listed"
                ),

                "category": category,

                "quantity": (
                    product["quantity"]
                    or ""
                ),

                "ingredients": ingredients,

                "source_url": (
                    product["source_url"]
                ),

                "matched_ingredients": matched,

                "reasons": reasons,

                "_score": len(matched)

            })

        candidates.sort(
            key=lambda item: (
                -item["_score"],
                item["name"].lower()
            )
        )

        # Keep up to three products per category.

        for candidate in candidates[:3]:

            candidate.pop(
                "_score",
                None
            )

            recommendations.append(
                candidate
            )

    return recommendations


# ==========================================================
# ROUTINE STEP HELPER
# ==========================================================

def create_routine_step(
    step_number,
    category,
    instruction,
    recommendations,
    optional=False
):

    # Find the first matching approved product.
    # The recommendation engine has already
    # applied the user's category and exclusions.

    matching_product = None

    for product in recommendations:

        if product["category"] == category:

            matching_product = {

                "name": product["name"],

                "brand": product["brand"],

                "source_url": product["source_url"]

            }

            break

    return {

        "step": step_number,

        "category": category,

        "instruction": instruction,

        "optional": optional,

        "product": matching_product

    }


# ==========================================================
# MORNING ROUTINE
# ==========================================================

def build_morning_routine(
    profile,
    recommendations
):

    routine = []

    selected = profile["products"]

    # ------------------------------------------
    # STEP 1: FACE WASH
    # ------------------------------------------

    if "Face Wash" in selected:

        routine.append(
            create_routine_step(

                len(routine) + 1,

                "Face Wash",

                (
                    "Cleanse gently if needed. "
                    "Avoid harsh scrubbing."
                ),

                recommendations

            )
        )

    # ------------------------------------------
    # STEP 2: MOISTURIZER
    # ------------------------------------------

    if "Moisturizer" in selected:

        routine.append(
            create_routine_step(

                len(routine) + 1,

                "Moisturizer",

                (
                    "Apply a moisturizer suitable "
                    "for your preferences."
                ),

                recommendations

            )
        )

    # ------------------------------------------
    # STEP 3: SUNSCREEN
    # ------------------------------------------

    if "Sunscreen" in selected:

        routine.append(
            create_routine_step(

                len(routine) + 1,

                "Sunscreen",

                (
                    "Apply broad-spectrum SPF 30 or "
                    "higher before daytime sun exposure. "
                    "Follow the product label for "
                    "application and reapplication."
                ),

                recommendations

            )
        )

    return routine


# ==========================================================
# NIGHT ROUTINE
# ==========================================================

def build_night_routine(
    profile,
    recommendations
):

    routine = []

    selected = profile["products"]

    # ------------------------------------------
    # STEP 1: FACE WASH
    # ------------------------------------------

    if "Face Wash" in selected:

        routine.append(
            create_routine_step(

                len(routine) + 1,

                "Face Wash",

                (
                    "Gently cleanse your skin to "
                    "remove sunscreen and daily residue."
                ),

                recommendations

            )
        )

    # ------------------------------------------
    # STEP 2: SERUM (OPTIONAL)
    # ------------------------------------------

    if "Serum" in selected:

        routine.append(
            create_routine_step(

                len(routine) + 1,

                "Serum",

                (
                    "Optional. Use only according to "
                    "the specific product's directions. "
                    "Some active serums are not suitable "
                    "for daily or nighttime use."
                ),

                recommendations,

                optional=True

            )
        )

    # ------------------------------------------
    # STEP 3: MOISTURIZER
    # ------------------------------------------

    if "Moisturizer" in selected:

        routine.append(
            create_routine_step(

                len(routine) + 1,

                "Moisturizer",

                (
                    "Finish with moisturizer according "
                    "to your skin's needs."
                ),

                recommendations

            )
        )

    return routine


# ==========================================================
# ROUTINE GUIDANCE
# ==========================================================

def build_routine_guidance(profile):

    guidance = [

        (
            "Introduce new skincare products gradually "
            "and follow each product's label."
        ),

        (
            "Patch testing can help identify some "
            "reactions, but it does not guarantee "
            "that a product will be tolerated."
        ),

        (
            "Daytime sun protection is important. "
            "Consider broad-spectrum SPF 30 or higher "
            "even if sunscreen was not selected."
        )

    ]

    if profile["sensitivity"] == "High":

        guidance.append(
            "You selected high sensitivity. "
            "Keep your routine simple and be especially "
            "careful with new active ingredients."
        )

    if "Redness" in profile["concerns"]:

        guidance.append(
            "Persistent redness or irritation may "
            "require advice from a dermatologist."
        )

    if "Acne" in profile["concerns"]:

        guidance.append(
            "Persistent or severe acne may require "
            "professional assessment. Cosmetic "
            "product matching is not acne treatment."
        )

    if "Serum" in profile["products"]:

        guidance.append(
            "Serum application order, frequency, and "
            "timing depend on the specific formula. "
            "The night routine is only a planning example."
        )

    return guidance


# ==========================================================
# BUILD COMPLETE RECOMMENDATION RESULT
# ==========================================================

def build_recommendation_result(data):

    profile = validate_profile(data)

    recommendations = get_recommendations(
        profile
    )

    returned_categories = {

        product["category"]

        for product in recommendations

    }

    missing_categories = [

        category

        for category in profile["products"]

        if category not in returned_categories

    ]

    morning_routine = build_morning_routine(
        profile,
        recommendations
    )

    night_routine = build_night_routine(
        profile,
        recommendations
    )

    guidance = build_routine_guidance(
        profile
    )

    return {

        "profile": {

            "skin_type": profile["skin_type"],

            "sensitivity": profile["sensitivity"],

            "concerns": profile["concerns"],

            "products": profile["products"],

            "budget": profile["budget"],

            "avoid_ingredients": (
                profile["avoid_ingredients"]
            )

        },

        "recommendations": recommendations,

        "missing_categories": missing_categories,

        "routine": {

            "morning": morning_routine,

            "night": night_routine,

            "guidance": guidance

        },

        "notices": [

            (
                "Recommendations are based on "
                "selected categories and available "
                "ingredient information."
            ),

            (
                "Product prices are not yet available. "
                "Your selected budget has not been "
                "checked against product prices."
            ),

            (
                "Skin-type suitability and allergy "
                "safety have not been independently "
                "verified."
            ),

            (
                "Product ingredients and availability "
                "may change. Check the current label."
            ),

            (
                "The routine is general cosmetic "
                "guidance, not a medical diagnosis "
                "or treatment plan."
            )

        ]

    }