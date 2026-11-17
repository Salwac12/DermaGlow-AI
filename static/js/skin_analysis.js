// ==========================================================
// DERMAGLOW AI
// SKIN ANALYSIS + PRODUCT RECOMMENDATIONS + ROUTINE BUILDER
//
// Developer: Salwa Choudhari
// ==========================================================

document.addEventListener("DOMContentLoaded", function () {

    // ======================================================
    // PAGE ELEMENTS
    // ======================================================

    const form = document.getElementById("skinForm");

    const budget = document.getElementById("budget");

    const budgetAmount = document.getElementById("budgetAmount");

    const skinImage = document.getElementById("skinImage");

    const imagePreview = document.getElementById("imagePreview");

    const previewImg = document.getElementById("previewImg");

    const removeImage = document.getElementById("removeImage");

    const profileResult = document.getElementById("profileResult");

    const profileDetails = document.getElementById("profileDetails");

    const editProfile = document.getElementById("editProfile");

    let currentImageURL = null;


    // ======================================================
    // CREATE HTML ELEMENTS SAFELY
    // ======================================================

    function createElement(tag, className, text) {

        const element = document.createElement(tag);

        if (className) {
            element.className = className;
        }

        if (text !== undefined) {
            element.textContent = text;
        }

        return element;

    }


    // ======================================================
    // SAFE PRODUCT SOURCE LINKS
    // ======================================================

    function createSourceLink(url, label) {

        try {

            const parsed = new URL(url);

            if (
                parsed.protocol !== "https:" ||
                parsed.hostname !== "world.openbeautyfacts.org"
            ) {
                return null;
            }

            const link = createElement(
                "a",
                "recommendation-link",
                label
            );

            link.href = parsed.href;

            link.target = "_blank";

            link.rel = "noopener noreferrer";

            return link;

        } catch (error) {

            return null;

        }

    }


    // ======================================================
    // BUDGET SLIDER
    // ======================================================

    budget.addEventListener("input", function () {

        budgetAmount.textContent = Number(
            budget.value
        ).toLocaleString("en-IN");

    });


    // ======================================================
    // SELFIE PREVIEW
    // ======================================================

    function clearImagePreview() {

        if (currentImageURL) {

            URL.revokeObjectURL(currentImageURL);

            currentImageURL = null;

        }

        previewImg.removeAttribute("src");

        imagePreview.hidden = true;

    }


    skinImage.addEventListener("change", function () {

        const file = skinImage.files[0];

        if (!file) {
            return;
        }

        const allowedTypes = [
            "image/jpeg",
            "image/png",
            "image/webp"
        ];

        if (
            !allowedTypes.includes(file.type) ||
            file.size > 5 * 1024 * 1024
        ) {

            alert(
                "Select a JPG, PNG, or WebP image under 5 MB."
            );

            skinImage.value = "";

            clearImagePreview();

            return;
        }

        clearImagePreview();

        currentImageURL = URL.createObjectURL(file);

        previewImg.src = currentImageURL;

        imagePreview.hidden = false;

    });


    removeImage.addEventListener("click", function () {

        skinImage.value = "";

        clearImagePreview();

    });


    // ======================================================
    // DISPLAY PROFILE ROWS
    // ======================================================

    function addProfileRow(label, value) {

        const row = createElement(
            "div",
            "profile-detail-row"
        );

        const title = createElement(
            "strong",
            "",
            label
        );

        const answer = createElement(
            "span",
            "",
            value
        );

        row.appendChild(title);

        row.appendChild(answer);

        profileDetails.appendChild(row);

    }


    // ======================================================
    // REMOVE PREVIOUS RESULTS
    // ======================================================

    function clearGeneratedSections() {

        const sections = [
            "recommendationsSection",
            "routineSection"
        ];

        sections.forEach(function (id) {

            const element = document.getElementById(id);

            if (element) {
                element.remove();
            }

        });

    }


    // ======================================================
    // DISPLAY RECOMMENDATIONS
    // ======================================================

    function showRecommendations(result) {

        const section = createElement(
            "section",
            "recommendations-section"
        );

        section.id = "recommendationsSection";

        section.appendChild(
            createElement(
                "h2",
                "recommendations-heading",
                "Your Skincare Product Shortlist 🌸"
            )
        );

        section.appendChild(
            createElement(
                "p",
                "recommendations-description",
                "Products selected from approved catalog records " +
                "based on your preferences and available ingredients."
            )
        );


        // ==================================================
        // NO MATCHING PRODUCTS
        // ==================================================

        if (!result.recommendations.length) {

            section.appendChild(
                createElement(
                    "div",
                    "recommendations-empty",
                    "No approved products currently match your " +
                    "selected categories and ingredient exclusions."
                )
            );

        } else {

            const grid = createElement(
                "div",
                "recommendations-grid"
            );

            result.recommendations.forEach(function (product) {

                const card = createElement(
                    "article",
                    "recommendation-card"
                );

                card.appendChild(
                    createElement(
                        "div",
                        "recommendation-category",
                        product.category
                    )
                );

                card.appendChild(
                    createElement(
                        "h3",
                        "",
                        product.name
                    )
                );

                card.appendChild(
                    createElement(
                        "p",
                        "recommendation-brand",
                        product.brand
                    )
                );

                if (product.quantity) {

                    card.appendChild(
                        createElement(
                            "p",
                            "recommendation-quantity",
                            "Quantity: " + product.quantity
                        )
                    );

                }

                const reasons = createElement(
                    "ul",
                    "recommendation-reasons"
                );

                product.reasons.forEach(function (reason) {

                    reasons.appendChild(
                        createElement(
                            "li",
                            "",
                            reason
                        )
                    );

                });

                card.appendChild(reasons);

                if (product.ingredients) {

                    const ingredientText =
                        product.ingredients.slice(0, 220);

                    card.appendChild(
                        createElement(
                            "p",
                            "recommendation-ingredients",
                            "Ingredients: " +
                            ingredientText +
                            (
                                product.ingredients.length > 220
                                ? "..."
                                : ""
                            )
                        )
                    );

                }

                const link = createSourceLink(
                    product.source_url,
                    "View Original Product →"
                );

                if (link) {
                    card.appendChild(link);
                }

                grid.appendChild(card);

            });

            section.appendChild(grid);

        }


        // ==================================================
        // MISSING CATEGORIES
        // ==================================================

        if (result.missing_categories.length) {

            section.appendChild(
                createElement(
                    "p",
                    "recommendation-warning",
                    "No eligible products found for: " +
                    result.missing_categories.join(", ")
                )
            );

        }


        // ==================================================
        // IMPORTANT LIMITATIONS
        // ==================================================

        const notice = createElement(
            "div",
            "recommendation-notice"
        );

        notice.appendChild(
            createElement(
                "strong",
                "",
                "Important Product Information"
            )
        );

        const noticeList = document.createElement("ul");

        result.notices.forEach(function (text) {

            noticeList.appendChild(
                createElement(
                    "li",
                    "",
                    text
                )
            );

        });

        notice.appendChild(noticeList);

        section.appendChild(notice);

        profileResult.appendChild(section);

    }


    // ======================================================
    // CREATE ONE ROUTINE STEP
    // ======================================================

    function createRoutineStep(step) {

        const card = createElement(
            "article",
            "recommendation-card"
        );

        const categoryLabel =
            "STEP " + step.step + " • " + step.category;

        card.appendChild(
            createElement(
                "div",
                "recommendation-category",
                categoryLabel
            )
        );

        const stepTitle = step.optional
            ? step.category + " (Optional)"
            : step.category;

        card.appendChild(
            createElement(
                "h3",
                "",
                stepTitle
            )
        );

        card.appendChild(
            createElement(
                "p",
                "recommendation-ingredients",
                step.instruction
            )
        );


        // ==================================================
        // MATCHING PRODUCT
        // ==================================================

        if (step.product) {

            card.appendChild(
                createElement(
                    "p",
                    "recommendation-brand",
                    "Suggested catalog product:"
                )
            );

            card.appendChild(
                createElement(
                    "p",
                    "",
                    step.product.name
                )
            );

            card.appendChild(
                createElement(
                    "p",
                    "recommendation-quantity",
                    step.product.brand
                )
            );

            const link = createSourceLink(
                step.product.source_url,
                "View Product →"
            );

            if (link) {
                card.appendChild(link);
            }

        } else {

            card.appendChild(
                createElement(
                    "p",
                    "recommendation-warning",
                    "No verified catalog product is currently " +
                    "available for this step."
                )
            );

        }

        return card;

    }


    // ======================================================
    // DISPLAY MORNING AND NIGHT ROUTINES
    // ======================================================

    function showRoutine(result) {

        const routine = result.routine;

        const section = createElement(
            "section",
            "recommendations-section"
        );

        section.id = "routineSection";

        section.appendChild(
            createElement(
                "h2",
                "recommendations-heading",
                "Your Personalized Skincare Routine ✨"
            )
        );

        section.appendChild(
            createElement(
                "p",
                "recommendations-description",
                "A simple routine outline based on your selected " +
                "product categories. Check individual product " +
                "directions before using anything."
            )
        );


        // ==================================================
        // MORNING ROUTINE
        // ==================================================

        const morningTitle = createElement(
            "h2",
            "recommendations-heading",
            "🌞 Morning Routine"
        );

        morningTitle.style.marginTop = "35px";

        section.appendChild(morningTitle);

        if (routine.morning.length) {

            const morningGrid = createElement(
                "div",
                "recommendations-grid"
            );

            routine.morning.forEach(function (step) {

                morningGrid.appendChild(
                    createRoutineStep(step)
                );

            });

            section.appendChild(morningGrid);

        } else {

            section.appendChild(
                createElement(
                    "div",
                    "recommendations-empty",
                    "You haven't selected products for the " +
                    "standard morning routine. Consider " +
                    "daytime sun protection."
                )
            );

        }


        // ==================================================
        // NIGHT ROUTINE
        // ==================================================

        const nightTitle = createElement(
            "h2",
            "recommendations-heading",
            "🌙 Night Routine"
        );

        nightTitle.style.marginTop = "40px";

        section.appendChild(nightTitle);

        if (routine.night.length) {

            const nightGrid = createElement(
                "div",
                "recommendations-grid"
            );

            routine.night.forEach(function (step) {

                nightGrid.appendChild(
                    createRoutineStep(step)
                );

            });

            section.appendChild(nightGrid);

        } else {

            section.appendChild(
                createElement(
                    "div",
                    "recommendations-empty",
                    "No nighttime routine steps were selected."
                )
            );

        }


        // ==================================================
        // ROUTINE GUIDANCE
        // ==================================================

        const guidance = createElement(
            "div",
            "recommendation-notice"
        );

        guidance.appendChild(
            createElement(
                "strong",
                "",
                "🌸 Routine Guidance"
            )
        );

        const list = document.createElement("ul");

        routine.guidance.forEach(function (message) {

            list.appendChild(
                createElement(
                    "li",
                    "",
                    message
                )
            );

        });

        guidance.appendChild(list);

        section.appendChild(guidance);

        profileResult.appendChild(section);

    }


    // ======================================================
    // SUBMIT QUESTIONNAIRE
    // ======================================================

    form.addEventListener("submit", async function (event) {

        event.preventDefault();

        if (!form.reportValidity()) {
            return;
        }

        const data = new FormData(form);

        const payload = {

            skin_type: data.get("skin_type"),

            sensitivity: data.get("sensitivity"),

            concerns: data.getAll("concerns"),

            products: data.getAll("products"),

            budget: Number(data.get("budget")),

            avoid_ingredients: (
                data.get("avoid_ingredients") || ""
            ).trim()

        };

        // No photograph is uploaded to the server.

        const submitButton = form.querySelector(
            'button[type="submit"]'
        );

        const originalText = submitButton.textContent;

        submitButton.disabled = true;

        submitButton.textContent = "Creating Your Routine...";

        try {

            const response = await fetch(
                "/api/recommendations",
                {

                    method: "POST",

                    headers: {
                        "Content-Type": "application/json"
                    },

                    body: JSON.stringify(payload)

                }
            );

            const result = await response.json();

            if (!response.ok) {

                throw new Error(
                    result.error ||
                    "Unable to create recommendations."
                );

            }


            // ==================================================
            // DISPLAY USER PROFILE
            // ==================================================

            profileDetails.replaceChildren();

            clearGeneratedSections();

            addProfileRow(
                "Skin Type",
                result.profile.skin_type
            );

            addProfileRow(
                "Sensitivity",
                result.profile.sensitivity
            );

            addProfileRow(
                "Skin Concerns",
                result.profile.concerns.join(", ") ||
                "Not specified"
            );

            addProfileRow(
                "Requested Products",
                result.profile.products.join(", ")
            );

            addProfileRow(
                "Selected Budget",
                "₹" +
                result.profile.budget.toLocaleString("en-IN")
            );

            addProfileRow(
                "Ingredients to Avoid",
                result.profile.avoid_ingredients ||
                "None specified"
            );


            // ==================================================
            // DISPLAY PRODUCT RECOMMENDATIONS
            // ==================================================

            showRecommendations(result);


            // ==================================================
            // DISPLAY MORNING & NIGHT ROUTINES
            // ==================================================

            showRoutine(result);


            // ==================================================
            // SHOW RESULTS
            // ==================================================

            form.hidden = true;

            profileResult.hidden = false;

            profileResult.scrollIntoView({

                behavior: "smooth",

                block: "start"

            });

        } catch (error) {

            alert(
                "Error: " + error.message
            );

        } finally {

            submitButton.disabled = false;

            submitButton.textContent = originalText;

        }

    });


    // ======================================================
    // EDIT PROFILE
    // ======================================================

    editProfile.addEventListener("click", function () {

        profileResult.hidden = true;

        form.hidden = false;

        form.scrollIntoView({

            behavior: "smooth",

            block: "start"

        });

    });


    // ======================================================
    // IMAGE CLEANUP
    // ======================================================

    window.addEventListener("pagehide", function () {

        clearImagePreview();

    });

});