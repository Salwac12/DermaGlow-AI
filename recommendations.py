# ==========================================================
# DERMAGLOW AI
# RECOMMENDATION API
#
# Developer: Salwa Choudhari
# ==========================================================

from flask import (
    Blueprint,
    request,
    jsonify
)

from recommender import (
    build_recommendation_result
)


recommendations_bp = Blueprint(
    "recommendations",
    __name__
)


# ==========================================================
# GET PERSONALIZED RECOMMENDATIONS
# ==========================================================

@recommendations_bp.route(
    "/api/recommendations",
    methods=["POST"]
)
def get_personalized_recommendations():

    if not request.is_json:

        return jsonify({
            "error": "Please submit valid JSON data."
        }), 415

    data = request.get_json(
        silent=True
    )

    try:

        result = build_recommendation_result(
            data
        )

    except ValueError as error:

        return jsonify({
            "error": str(error)
        }), 400

    return jsonify(result)