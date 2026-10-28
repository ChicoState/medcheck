from medications.interactions import check_label_pair, interaction_terms


def label(name, generic, brands, ingredients, text):
    return {
        "displayName": name,
        "genericName": generic,
        "brandNames": brands,
        "activeIngredients": ingredients,
        "sections": [{"key": "drug_interactions", "title": "Drug interactions", "text": text}],
        "sourceUrl": "https://example.test/label",
        "labelEffectiveDate": "2026-10-01",
        "datasetUpdatedAt": "2026-10-15",
        "externalId": "one",
        "provider": "openfda",
    }


def test_interaction_terms_include_generic_brand_and_ingredient_without_strength():
    terms = interaction_terms(
        label(
            "Eliquis 5 mg",
            "APIXABAN",
            ["ELIQUIS"],
            ["apixaban 5 mg"],
            "label text",
        )
    )

    assert terms == {"apixaban", "eliquis"}


def test_check_label_pair_returns_directional_label_match():
    first = label(
        "Alprazolam",
        "ALPRAZOLAM",
        ["XANAX"],
        ["alprazolam"],
        "Use with XANAX and opioids may cause additive CNS depression.",
    )
    second = label(
        "Xanax",
        "ALPRAZOLAM",
        ["XANAX"],
        ["alprazolam"],
        "Avoid use with opioids.",
    )

    result = check_label_pair(first, second)

    assert result["status"] == "label_match"
    assert len(result["findings"]) == 1
    assert result["findings"][0]["sourceMedication"] == "Alprazolam"
    assert result["findings"][0]["matchedTerm"] == "xanax"


def test_check_label_pair_does_not_claim_safety_when_no_match_exists():
    first = label("Drug A", "DRUGA", ["BRANDA"], ["druga"], "Avoid alcohol.")
    second = label("Drug B", "DRUGB", ["BRANDB"], ["drugb"], "Take with food.")

    result = check_label_pair(first, second)

    assert result["status"] == "no_label_match"
    assert result["findings"] == []
