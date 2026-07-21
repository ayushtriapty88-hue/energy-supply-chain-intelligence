import os
import json
import sys
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from backend.llm_client import ask_llm, ask_llm_json
from backend.knowledge.rag_store import populate_knowledge_base
from backend.ingestion.sanctions_fetcher import (
    REFINERY_COMPATIBILITY,
    check_grade_compatibility,
)

OUTPUT_PATH = "backend/data/procurement_recommendations.json"

# ── Global supplier database ──────────────────────────────
ALL_SUPPLIERS = [
    {
        "country":       "Nigeria",
        "grade":         "Bonny Light",
        "price_premium": 2.5,
        "delivery_days": 18,
        "available_kbd": 200,
        "sanction_risk": "NONE",
        "route":         "Cape of Good Hope",
        "reliability":   0.92,
    },
    {
        "country":       "USA",
        "grade":         "WTI",
        "price_premium": 3.0,
        "delivery_days": 22,
        "available_kbd": 300,
        "sanction_risk": "NONE",
        "route":         "Cape of Good Hope",
        "reliability":   0.97,
    },
    {
        "country":       "Angola",
        "grade":         "Cabinda",
        "price_premium": 2.0,
        "delivery_days": 16,
        "available_kbd": 150,
        "sanction_risk": "NONE",
        "route":         "Cape of Good Hope",
        "reliability":   0.88,
    },
    {
        "country":       "Brazil",
        "grade":         "Lula",
        "price_premium": 3.5,
        "delivery_days": 25,
        "available_kbd": 100,
        "sanction_risk": "NONE",
        "route":         "Atlantic",
        "reliability":   0.90,
    },
    {
        "country":       "Saudi Arabia",
        "grade":         "Arab Light",
        "price_premium": 0.5,
        "delivery_days": 8,
        "available_kbd": 500,
        "sanction_risk": "LOW",
        "route":         "Persian Gulf",
        "reliability":   0.98,
    },
    {
        "country":       "Iraq",
        "grade":         "Basra Medium",
        "price_premium": 0.0,
        "delivery_days": 7,
        "available_kbd": 400,
        "sanction_risk": "LOW",
        "route":         "Persian Gulf",
        "reliability":   0.94,
    },
    {
        "country":       "UAE",
        "grade":         "Murban",
        "price_premium": 1.0,
        "delivery_days": 6,
        "available_kbd": 200,
        "sanction_risk": "LOW",
        "route":         "Persian Gulf",
        "reliability":   0.96,
    },
    {
        "country":       "Canada",
        "grade":         "Heavy Blend",
        "price_premium": 1.5,
        "delivery_days": 28,
        "available_kbd": 200,
        "sanction_risk": "NONE",
        "route":         "Pacific",
        "reliability":   0.91,
    },
    {
        "country":       "Russia",
        "grade":         "Urals",
        "price_premium": -8.0,
        "delivery_days": 12,
        "available_kbd": 800,
        "sanction_risk": "MEDIUM",
        "route":         "Direct",
        "reliability":   0.85,
    },
]

def score_supplier(supplier, base_brent, supply_gap_kbd,
                   blocked_corridors=None, excluded_countries=None):
    blocked_corridors  = blocked_corridors or []
    excluded_countries = excluded_countries or []

    if supplier["country"] in excluded_countries:
        return None

    route_lower = supplier["route"].lower()
    for corridor in blocked_corridors:
        if corridor in route_lower:
            return None

    actual_price  = base_brent + supplier["price_premium"]
    max_premium   = 10.0
    price_score   = max(0, (max_premium - supplier["price_premium"]) / max_premium * 25)

    max_days      = 30
    speed_score   = max(0, (max_days - supplier["delivery_days"]) / max_days * 25)

    volume_ratio  = min(supplier["available_kbd"] / max(supply_gap_kbd, 1), 1.0)
    volume_score  = volume_ratio * 20

    sanction_scores = {"NONE": 20, "LOW": 15, "MEDIUM": 3, "HIGH": 0, "CRITICAL": 0}
    sanction_score  = sanction_scores.get(supplier["sanction_risk"], 0)

    reliability_score = supplier["reliability"] * 10

    total_score = (price_score + speed_score +
                   volume_score + sanction_score + reliability_score)

    return {
        "country":         supplier["country"],
        "grade":           supplier["grade"],
        "route":           supplier["route"],
        "actual_price":    round(actual_price, 2),
        "delivery_days":   supplier["delivery_days"],
        "available_kbd":   supplier["available_kbd"],
        "sanction_risk":   supplier["sanction_risk"],
        "reliability":     supplier["reliability"],
        "total_score":     round(total_score, 1),
        "score_breakdown": {
            "price":        round(price_score, 1),
            "speed":        round(speed_score, 1),
            "volume":       round(volume_score, 1),
            "sanctions":    sanction_score,
            "reliability":  round(reliability_score, 1),
        }
    }

def check_refinery_compatibility_for_suppliers(ranked_suppliers):
    for supplier in ranked_suppliers:
        grade        = supplier["grade"]
        compatible   = []
        incompatible = []
        for refinery_name, refinery_data in REFINERY_COMPATIBILITY.items():
            if grade in refinery_data["compatible_grades"]:
                compatible.append(refinery_name)
            else:
                incompatible.append(refinery_name)
        supplier["compatible_refineries"]   = compatible
        supplier["incompatible_refineries"] = incompatible
        supplier["refinery_count"]          = len(compatible)
    return ranked_suppliers

def compute_daily_cost_mn(supply_gap_kbd, avg_price_usd):
    """
    Cost of buying the replacement barrels, per day, in USD millions.
    supply_gap_kbd is THOUSAND barrels/day → × 1000 = barrels/day.
    NO factor of 42 — that would convert barrels to gallons.
    """
    barrels_per_day = supply_gap_kbd * 1000
    return round(barrels_per_day * avg_price_usd / 1_000_000, 1)


def run_procurement_orchestrator(
    supply_gap_kbd,
    base_brent_price,
    blocked_corridors=None,
    excluded_countries=None,
    scenario_name="General Disruption"
):
    print(f"\n{'='*60}")
    print(f"ADAPTIVE PROCUREMENT ORCHESTRATOR")
    print(f"Scenario: {scenario_name}")
    print(f"Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    print(f"\n  Supply gap to fill : {supply_gap_kbd} kbd")
    print(f"  Current Brent      : ${base_brent_price}/barrel")
    print(f"  Blocked corridors  : {blocked_corridors or 'None'}")
    print(f"  Excluded countries : {excluded_countries or 'None'}")

    if supply_gap_kbd <= 0:
        print("\n  No supply gap under this scenario — no emergency procurement needed.")
        output = {
            "timestamp":        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "scenario":         scenario_name,
            "supply_gap_kbd":   0,
            "base_brent":       base_brent_price,
            "ranked_suppliers": [],
            "procurement_plan": [],
            "gap_coverage_pct": 100.0,
            "executive_summary": {
                "executive_summary": "No supply gap under this scenario. Normal procurement continues.",
                "first_call_to_make": "None required",
                "estimated_cost_per_day_mn_usd": 0.0,
                "key_risk": "None identified",
                "confidence": "HIGH",
            },
        }
        _atomic_write(OUTPUT_PATH, output)
        return output

    # Step 1 — Score all suppliers
    print(f"\n[1/4] Scoring all suppliers...")
    scored = []
    for supplier in ALL_SUPPLIERS:
        score = score_supplier(
            supplier,
            base_brent_price,
            supply_gap_kbd,
            blocked_corridors,
            excluded_countries,
        )
        if score:
            scored.append(score)

    ranked = sorted(scored, key=lambda x: x["total_score"], reverse=True)

    # Step 2 — Refinery compatibility
    print(f"[2/4] Checking refinery grade compatibility...")
    ranked = check_refinery_compatibility_for_suppliers(ranked)

    # Step 3 — Build procurement plan
    print(f"[3/4] Building optimal procurement plan...")
    procurement_plan = []
    remaining_gap    = supply_gap_kbd

    for supplier in ranked:
        if remaining_gap <= 0:
            break
        volume_to_procure = min(supplier["available_kbd"], remaining_gap)
        remaining_gap    -= volume_to_procure
        procurement_plan.append({
            **supplier,
            "procure_kbd":    round(volume_to_procure, 1),
            "covers_percent": round(volume_to_procure / supply_gap_kbd * 100, 1),
        })

    gap_covered  = supply_gap_kbd - max(0, remaining_gap)
    coverage_pct = round(gap_covered / supply_gap_kbd * 100, 1)
    shortfall_kbd = round(max(0, remaining_gap), 1)

    # Volume-weighted average price of the actual plan — more honest than base Brent
    if procurement_plan:
        total_vol = sum(p["procure_kbd"] for p in procurement_plan)
        weighted_price = sum(
            p["procure_kbd"] * p["actual_price"] for p in procurement_plan
        ) / max(total_vol, 1)
    else:
        weighted_price = base_brent_price

    daily_cost_mn = compute_daily_cost_mn(gap_covered, weighted_price)
    baseline_cost_mn = compute_daily_cost_mn(gap_covered, base_brent_price)
    premium_cost_mn  = round(daily_cost_mn - baseline_cost_mn, 1)

    # Print ranked table
    print(f"\n  RANKED SUPPLIERS (highest score first):")
    print(f"  {'Rank':<5} {'Country':<14} {'Grade':<16} "
          f"{'Price':<10} {'Days':<6} {'Score':<8} {'Refineries'}")
    print(f"  {'-'*75}")
    for i, s in enumerate(ranked[:6]):
        print(f"  #{i+1:<4} {s['country']:<14} {s['grade']:<16} "
              f"${s['actual_price']:<9} {s['delivery_days']:<6} "
              f"{s['total_score']:<8} {s['refinery_count']} compatible")

    print(f"\n  PROCUREMENT PLAN TO COVER {supply_gap_kbd} kbd GAP:")
    print(f"  {'-'*55}")
    for p in procurement_plan:
        print(f"  → {p['country']:<14} {p['procure_kbd']} kbd "
              f"({p['covers_percent']}% of gap) "
              f"— {p['delivery_days']} days delivery")
    print(f"\n  Gap coverage: {coverage_pct}% "
          f"({'✅ FULLY COVERED' if coverage_pct >= 100 else f'⚠ SHORTFALL {shortfall_kbd} kbd'})")

    print(f"\n  COST OF THIS PLAN:")
    print(f"  Volumes procured : {round(gap_covered,1)} kbd")
    print(f"  Avg price paid   : ${round(weighted_price,2)}/barrel")
    print(f"  Total spend      : ${daily_cost_mn}M/day")
    print(f"  Premium vs Brent : ${premium_cost_mn}M/day extra")

    # Step 4 — LLM executive summary. Numbers are computed, not invented.
    print(f"\n[4/4] Generating executive procurement summary...")
    top3 = ranked[:3]
    top3_str = ", ".join(
        [f"{s['country']} (score {s['total_score']})" for s in top3]
    ) or "none available"

    prompt = f"""You are an energy procurement advisor to India's Petroleum Ministry.

Scenario: {scenario_name}
Supply gap: {supply_gap_kbd} kbd
Brent: ${base_brent_price}/barrel
Top-ranked suppliers: {top3_str}
Plan covers {coverage_pct}% of the gap; shortfall {shortfall_kbd} kbd
Cost of plan: ${daily_cost_mn}M/day (${premium_cost_mn}M/day above Brent)

Use ONLY the figures above. Do not invent numbers.
Return ONLY valid JSON, no markdown:
{{"executive_summary":"two sentences for the minister","first_call_to_make":"which country and what action","key_risk":"the single biggest risk, one sentence","confidence":"HIGH"}}"""

    summary = ask_llm_json(prompt)

    if not summary:
        print("  [LLM] Failed — using deterministic fallback summary.")
        summary = {
            "executive_summary": (
                f"Procurement plan covers {coverage_pct}% of the {supply_gap_kbd} kbd gap "
                f"using {len(procurement_plan)} suppliers at ${daily_cost_mn}M/day."
            ),
            "first_call_to_make": (
                f"Contact {ranked[0]['country']} petroleum ministry immediately"
                if ranked else "No viable supplier — escalate to cabinet"
            ),
            "key_risk": "Delivery delays on longer alternative routes leave the gap open in the interim.",
            "confidence": "MEDIUM",
        }

    # Cost figures are OWNED by Python. The LLM never sets them.
    summary["estimated_cost_per_day_mn_usd"] = daily_cost_mn
    summary["premium_over_brent_mn_usd"]     = premium_cost_mn
    summary["avg_price_paid_usd"]            = round(weighted_price, 2)

    # Guarantee every field the frontend expects exists
    summary.setdefault("executive_summary", "")
    summary.setdefault("first_call_to_make", "")
    summary.setdefault("key_risk", "Not specified")
    summary.setdefault("confidence", "MEDIUM")

    output = {
        "timestamp":         datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "scenario":          scenario_name,
        "supply_gap_kbd":    supply_gap_kbd,
        "base_brent":        base_brent_price,
        "ranked_suppliers":  ranked,
        "procurement_plan":  procurement_plan,
        "gap_coverage_pct":  coverage_pct,
        "shortfall_kbd":     shortfall_kbd,
        "avg_price_paid":    round(weighted_price, 2),
        "daily_cost_mn_usd": daily_cost_mn,
        "premium_mn_usd":    premium_cost_mn,
        "executive_summary": summary,
    }

    _atomic_write(OUTPUT_PATH, output)

    print(f"\n{'='*60}")
    print(f"PROCUREMENT RECOMMENDATION")
    print(f"{'='*60}")
    print(f"  {summary.get('executive_summary','')}")
    print(f"  First action : {summary.get('first_call_to_make','')}")
    print(f"  Daily cost   : ${summary.get('estimated_cost_per_day_mn_usd','')}M/day")
    print(f"  Premium      : ${summary.get('premium_over_brent_mn_usd','')}M/day above Brent")
    print(f"  Key risk     : {summary.get('key_risk','')}")
    print(f"  Confidence   : {summary.get('confidence','')}")
    print(f"\n  Full recommendations saved to: {OUTPUT_PATH}")
    print(f"{'='*60}")

    return output


def _atomic_write(path, payload):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(payload, f, indent=2)
    os.replace(tmp, path)


if __name__ == "__main__":
    populate_knowledge_base()

    try:
        with open("backend/data/scenario_analysis.json") as f:
            scenario = json.load(f)
        gap        = scenario["impact"]["supply_gap_kbd"]
        brent      = scenario["impact"]["new_brent_price"]
        sc_name    = scenario["scenario"]["name"]
        sc_key     = scenario["scenario_key"]
        corridor   = scenario["scenario"].get("affected_corridor", "none")
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        gap      = 824.0
        brent    = 83.83
        sc_name  = "Hormuz Partial Disruption"
        sc_key   = "hormuz_partial"
        corridor = "hormuz"

    # Corridor-driven blocking — no more string-matching on names
    blocked  = []
    excluded = []

    if corridor == "hormuz":
        blocked  = ["persian gulf"]     # Saudi/Iraq/UAE cut off
        excluded = ["Russia"]           # sanctioned, politically unavailable
    elif corridor == "red_sea":
        blocked  = []                   # re-routing, not blocking
        excluded = ["Russia"]
    elif sc_key == "russia_sanctions":
        blocked  = []
        excluded = ["Russia"]           # the whole point of the scenario
    elif sc_key == "opec_emergency_cut":
        blocked  = []
        excluded = ["Saudi Arabia", "Iraq", "UAE"]   # OPEC+ members cutting

    run_procurement_orchestrator(
        supply_gap_kbd     = gap,
        base_brent_price   = brent,
        blocked_corridors  = blocked,
        excluded_countries = excluded,
        scenario_name      = sc_name,
    )