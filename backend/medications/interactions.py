"""Conservative interaction screening against normalized product-label text."""

import re

DISCLAIMER = (
    "This checks only the interaction text in the two retrieved product labels. "
    "An empty result does not prove that the products are safe to combine. "
    "Ask a pharmacist or healthcare professional before using them together."
)


def _clean_term(value):
    value = re.sub(r"\s+", " ", value.casefold()).strip(" .,;:-")
    value = re.sub(r"\s+(?:usp|hcl|hydrochloride|sodium|calcium)\b.*$", "", value)
    value = re.sub(r"\s+\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|%)\b.*$", "", value)
    return value.strip(" .,;:-")


def interaction_terms(label):
    values = [label.get("genericName"), *label.get("brandNames", [])]
    values.extend(label.get("activeIngredients", []))
    return {
        term
        for value in values
        if isinstance(value, str)
        for term in [_clean_term(value)]
        if len(term) >= 3
    }


def _interaction_text(label):
    return "\n\n".join(
        section["text"]
        for section in label.get("sections", [])
        if section.get("key") == "drug_interactions" and isinstance(section.get("text"), str)
    )


def _findings(source, target):
    text = _interaction_text(source)
    folded = text.casefold()
    findings = []
    for term in sorted(interaction_terms(target), key=lambda value: (-len(value), value)):
        if re.search(rf"(?<!\w){re.escape(term)}(?!\w)", folded):
            findings.append(
                {
                    "sourceMedication": source["displayName"],
                    "targetMedication": target["displayName"],
                    "matchedTerm": term,
                    "text": text,
                    "sourceUrl": source["sourceUrl"],
                    "labelEffectiveDate": source.get("labelEffectiveDate"),
                    "datasetUpdatedAt": source.get("datasetUpdatedAt"),
                }
            )
            break
    return findings


def check_label_pair(first, second):
    findings = _findings(first, second) + _findings(second, first)
    return {
        "status": "label_match" if findings else "no_label_match",
        "medications": [
            {
                "displayName": label["displayName"],
                "genericName": label.get("genericName"),
                "brandNames": label.get("brandNames", []),
                "activeIngredients": label.get("activeIngredients", []),
                "sourceUrl": label["sourceUrl"],
                "labelEffectiveDate": label.get("labelEffectiveDate"),
                "datasetUpdatedAt": label.get("datasetUpdatedAt"),
            }
            for label in (first, second)
        ],
        "findings": findings,
        "disclaimer": DISCLAIMER,
    }
