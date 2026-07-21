import requests
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# ── Active sanctions database ─────────────────────────────
# In production this would pull from OFAC SDN list API
# Here we maintain a curated static dataset of energy-relevant sanctions

ACTIVE_SANCTIONS = [
    {
        "entity":       "National Iranian Oil Company (NIOC)",
        "country":      "Iran",
        "sanctioned_by": ["USA", "EU", "UK"],
        "reason":       "Iranian nuclear program",
        "since":        "2012",
        "oil_impact":   "Blocks ~1.5 mb/d from global market",
        "severity":     "CRITICAL",
    },
    {
        "entity":       "Russian oil exports via Baltic ports",
        "country":      "Russia",
        "sanctioned_by": ["USA", "EU", "G7"],
        "reason":       "Ukraine invasion",
        "since":        "2022",
        "oil_impact":   "Price cap of $60/barrel on Russian crude",
        "severity":     "HIGH",
    },
    {
        "entity":       "Venezuelan state oil company PDVSA",
        "country":      "Venezuela",
        "sanctioned_by": ["USA"],
        "reason":       "Political sanctions",
        "since":        "2019",
        "oil_impact":   "Restricts ~400 kb/d",
        "severity":     "MEDIUM",
    },
    {
        "entity":       "Syrian Petroleum Company",
        "country":      "Syria",
        "sanctioned_by": ["USA", "EU"],
        "reason":       "Civil war sanctions",
        "since":        "2011",
        "oil_impact":   "Minor — Syria is small producer",
        "severity":     "LOW",
    },
]

# ── India's top crude oil suppliers ──────────────────────
INDIA_SUPPLIERS = [
    {
        "country":        "Russia",
        "share_percent":  38.0,
        "grade":          ["Urals", "ESPO"],
        "route":          "Direct tanker via Indian Ocean",
        "sanction_risk":  "MEDIUM",
        "notes":          "Price cap applies — India buying at discount",
    },
    {
        "country":        "Iraq",
        "share_percent":  22.0,
        "grade":          ["Basra Heavy", "Basra Medium"],
        "route":          "Persian Gulf → Arabian Sea",
        "sanction_risk":  "LOW",
        "notes":          "Stable supplier, passes through Hormuz",
    },
    {
        "country":        "Saudi Arabia",
        "share_percent":  16.0,
        "grade":          ["Arab Light", "Arab Heavy"],
        "route":          "Persian Gulf → Arabian Sea",
        "sanction_risk":  "LOW",
        "notes":          "OPEC+ production cuts risk supply reduction",
    },
    {
        "country":        "UAE",
        "share_percent":  8.0,
        "grade":          ["Murban"],
        "route":          "Persian Gulf → Arabian Sea",
        "sanction_risk":  "LOW",
        "notes":          "Reliable, premium grade",
    },
    {
        "country":        "USA",
        "share_percent":  6.0,
        "grade":          ["WTI", "Eagle Ford"],
        "route":          "Atlantic → Cape of Good Hope → India",
        "sanction_risk":  "NONE",
        "notes":          "Long route but zero sanction risk",
    },
    {
        "country":        "Nigeria",
        "share_percent":  4.0,
        "grade":          ["Bonny Light"],
        "route":          "Atlantic → Cape of Good Hope → India",
        "sanction_risk":  "NONE",
        "notes":          "Good alternative if Hormuz disrupted",
    },
    {
        "country":        "Others",
        "share_percent":  6.0,
        "grade":          ["Various"],
        "route":          "Various",
        "sanction_risk":  "LOW",
        "notes":          "Angola, Kuwait, Mexico etc.",
    },
]

# ── Refinery grade compatibility ──────────────────────────
# This is your unique addition from the architecture discussion
REFINERY_COMPATIBILITY = {
    "Reliance Jamnagar": {
        "location":          "Gujarat",
        "capacity_kbd":      1240,
        "compatible_grades": [
            "Arab Light", "Arab Heavy", "Basra Heavy",
            "Basra Medium", "Murban", "Urals", "WTI",
            "Bonny Light", "ESPO", "Eagle Ford",
            "Cabinda", "Lula", "Heavy Blend"
        ],
        "notes": "World's largest refinery — processes almost all grades",
    },
    "Indian Oil Panipat": {
        "location":          "Haryana",
        "capacity_kbd":      300,
        "compatible_grades": [
            "Arab Light", "Basra Medium", "Murban",
            "WTI", "Bonny Light", "Cabinda"
        ],
        "notes": "Configured for medium-light grades",
    },
    "HPCL Mumbai": {
        "location":          "Maharashtra",
        "capacity_kbd":      156,
        "compatible_grades": [
            "Arab Light", "Basra Medium",
            "Bonny Light", "Cabinda"
        ],
        "notes": "Older refinery — limited heavy crude capacity",
    },
    "BPCL Kochi": {
        "location":          "Kerala",
        "capacity_kbd":      310,
        "compatible_grades": [
            "Arab Light", "Arab Heavy", "Basra Heavy",
            "Murban", "Urals", "Lula", "Cabinda"
        ],
        "notes": "Deep water port — can handle VLCCs",
    },
    "MRPL Mangalore": {
        "location":          "Karnataka",
        "capacity_kbd":      300,
        "compatible_grades": [
            "Arab Light", "Arab Heavy", "Basra Heavy",
            "Murban", "ESPO", "Bonny Light", "Lula"
        ],
        "notes": "ONGC subsidiary — handles Middle East grades well",
    },
}
def check_supplier_sanctions(supplier_country):
    """Check if a supplier country has active sanctions."""
    flagged = []
    for sanction in ACTIVE_SANCTIONS:
        if sanction["country"].lower() == supplier_country.lower():
            flagged.append(sanction)
    return flagged

def get_safe_alternative_suppliers(blocked_countries=None):
    """Return suppliers with no or low sanction risk, excluding blocked ones."""
    blocked_countries = blocked_countries or []
    alternatives = []
    for supplier in INDIA_SUPPLIERS:
        if supplier["country"] in blocked_countries:
            continue
        if supplier["sanction_risk"] in ["NONE", "LOW"]:
            alternatives.append(supplier)
    return sorted(alternatives, key=lambda x: x["share_percent"], reverse=True)

def check_grade_compatibility(refinery_name, crude_grade):
    """Check if a specific refinery can process a given crude grade."""
    refinery = REFINERY_COMPATIBILITY.get(refinery_name)
    if not refinery:
        return {"compatible": False, "reason": "Refinery not found"}
    compatible = crude_grade in refinery["compatible_grades"]
    return {
        "refinery":   refinery_name,
        "grade":      crude_grade,
        "compatible": compatible,
        "capacity":   refinery["capacity_kbd"],
        "notes":      refinery["notes"],
    }

def fetch_sanctions_summary():
    print(f"\n{'='*50}")
    print(f"Sanctions & Trade Intelligence")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}")

    print("\n[ACTIVE SANCTIONS AFFECTING OIL SUPPLY]")
    for s in ACTIVE_SANCTIONS:
        print(f"\n  Entity   : {s['entity']}")
        print(f"  Country  : {s['country']}")
        print(f"  Severity : {s['severity']}")
        print(f"  Impact   : {s['oil_impact']}")

    print(f"\n[INDIA SUPPLIER BREAKDOWN]")
    for supplier in INDIA_SUPPLIERS:
        risk_flag = "⚠" if supplier["sanction_risk"] in ["MEDIUM","HIGH","CRITICAL"] else "✓"
        print(f"  {risk_flag} {supplier['country']:15} {supplier['share_percent']}% — {supplier['sanction_risk']} sanction risk")

    print(f"\n[GRADE COMPATIBILITY CHECK — SAMPLE]")
    test_cases = [
        ("Reliance Jamnagar",  "Bonny Light"),
        ("HPCL Mumbai",        "Arab Heavy"),
        ("BPCL Kochi",         "Urals"),
        ("Indian Oil Panipat", "Basra Heavy"),
    ]
    for refinery, grade in test_cases:
        result = check_grade_compatibility(refinery, grade)
        status = "✓ Compatible" if result["compatible"] else "✗ Incompatible"
        print(f"  {status} — {refinery} + {grade}")

    print(f"\n[SAFE ALTERNATIVE SUPPLIERS IF HORMUZ BLOCKED]")
    alternatives = get_safe_alternative_suppliers(
        blocked_countries=["Iraq", "Saudi Arabia", "UAE", "Iran"]
    )
    for alt in alternatives:
        print(f"  {alt['country']:15} {alt['share_percent']}% share — Route: {alt['route']}")

    return {
        "sanctions":    ACTIVE_SANCTIONS,
        "suppliers":    INDIA_SUPPLIERS,
        "refineries":   REFINERY_COMPATIBILITY,
    }

if __name__ == "__main__":
    fetch_sanctions_summary()