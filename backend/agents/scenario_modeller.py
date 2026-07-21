import os
import json
import sys
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from backend.llm_client import ask_llm, ask_llm_json
from backend.knowledge.rag_store import query_similar_incidents, populate_knowledge_base

SNAPSHOT_PATH = "backend/data/latest_snapshot.json"
OUTPUT_PATH   = "backend/data/scenario_analysis.json"
ACTIVE_PATH   = "backend/data/active_scenario.json"

DEFAULT_SCENARIO = "hormuz_partial"

# ── Predefined scenarios ──────────────────────────────────
SCENARIOS = {
    "hormuz_closure": {
        "name":        "Strait of Hormuz Full Closure",
        "description": "Iran closes Strait of Hormuz completely",
        "supply_cut_percent":  45,
        "affected_corridor":   "hormuz",
        "duration_days":       30,
        "price_shock_percent": 35,
        "severity":            10,
    },
    "hormuz_partial": {
        "name":        "Strait of Hormuz Partial Disruption",
        "description": "Military tensions reduce Hormuz throughput by 40%",
        "supply_cut_percent":  18,
        "affected_corridor":   "hormuz",
        "duration_days":       14,
        "price_shock_percent": 12,
        "severity":            7,
    },
    "red_sea_closure": {
        "name":        "Red Sea Complete Shutdown",
        "description": "Houthi attacks force all tankers to Cape route",
        # Not a true supply cut — it's a routing delay. The 6% effective cut
        # represents cargo stranded in transit while the fleet re-routes.
        "supply_cut_percent":  6,
        "affected_corridor":   "red_sea",
        "duration_days":       60,
        "price_shock_percent": 8,
        "severity":            6,
        "delay_days":          14,
    },
    "opec_emergency_cut": {
        "name":        "OPEC+ Emergency Production Cut",
        "description": "OPEC+ announces emergency 2mb/d production cut",
        "supply_cut_percent":  12,
        "affected_corridor":   "none",
        "duration_days":       180,
        "price_shock_percent": 20,
        "severity":            8,
    },
    "russia_sanctions": {
        "name":        "Full Russia Oil Embargo",
        "description": "G7 imposes full embargo on Russian crude forcing India to replace 38% supply",
        "supply_cut_percent":  38,
        "affected_corridor":   "multiple",
        "duration_days":       365,
        "price_shock_percent": 25,
        "severity":            9,
    },
}

# ── India energy baseline constants ──────────────────────
INDIA_BASELINE = {
    "daily_consumption_kbd":  5200,   # thousand barrels per day
    "spr_days":               9.5,    # strategic reserve, days of TOTAL consumption
    "refinery_capacity_kbd":  5000,   # total refinery capacity
    "baseline_refinery_util": 85.0,   # % utilisation in normal operations
    "import_dependency":      0.88,   # 88% imported
    "hormuz_dependency":      0.45,   # 45% via Hormuz
    "russia_dependency":      0.38,   # 38% from Russia
    "current_brent":          74.85,  # USD/barrel
    "annual_import_bill_bn":  132,    # USD billion per year
    "gdp_bn_usd":             3900,   # India GDP, USD billion
}


# ── Active scenario state (fixes the overwrite bug) ───────
def get_active_scenario():
    """Return the scenario the user last selected, else the default."""
    try:
        with open(ACTIVE_PATH) as f:
            key = json.load(f).get("scenario_key")
        if key in SCENARIOS:
            return key
    except (FileNotFoundError, json.JSONDecodeError, AttributeError):
        pass
    return DEFAULT_SCENARIO


def set_active_scenario(key):
    """Persist the user's scenario choice so later agent runs don't reset it."""
    payload = {
        "scenario_key": key,
        "scenario_name": SCENARIOS[key]["name"],
        "set_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    _atomic_write(ACTIVE_PATH, payload)


def _atomic_write(path, payload):
    """Write JSON atomically so the API never reads a half-written file."""
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(payload, f, indent=2)
    os.replace(tmp, path)


# ── Economics ─────────────────────────────────────────────
def compute_economic_impact(scenario):
    """
    Calculate hard numbers for what this scenario means for India.
    Pure math — no LLM. Every figure the LLM later quotes comes from here.
    """
    base = INDIA_BASELINE
    sc   = scenario

    # Supply gap
    daily_import_kbd   = base["daily_consumption_kbd"] * base["import_dependency"]
    supply_gap_kbd     = daily_import_kbd * (sc["supply_cut_percent"] / 100)
    supply_gap_percent = sc["supply_cut_percent"] * base["import_dependency"]

    # SPR is a STOCK (thousand barrels), not a rate.
    # 9.5 days of total consumption = 9.5 * 5200 = 49,400 kb held in reserve.
    spr_stock_kb = base["spr_days"] * base["daily_consumption_kbd"]

    # How many days that stock can plug THIS gap
    if supply_gap_kbd > 0:
        spr_covers_days = spr_stock_kb / supply_gap_kbd
    else:
        spr_covers_days = float(sc["duration_days"])

    spr_covers_days    = min(spr_covers_days, float(sc["duration_days"]))
    gap_after_spr_days = max(0.0, sc["duration_days"] - spr_covers_days)

    # Price impact
    new_brent_price    = base["current_brent"] * (1 + sc["price_shock_percent"] / 100)
    price_increase_usd = new_brent_price - base["current_brent"]

    # Cost of paying more for the barrels we STILL import
    remaining_import_kbd = daily_import_kbd - supply_gap_kbd
    price_cost_per_day_mn = remaining_import_kbd * 1000 * price_increase_usd / 1_000_000

    # Cost of replacing the missing barrels at the new (higher) price
    replacement_cost_per_day_mn = supply_gap_kbd * 1000 * new_brent_price / 1_000_000

    total_cost_per_day_mn   = price_cost_per_day_mn + replacement_cost_per_day_mn
    total_additional_cost_bn = (price_cost_per_day_mn * sc["duration_days"]) / 1000

    # Refinery utilisation
    refinery_util_drop = supply_gap_kbd / base["refinery_capacity_kbd"] * 100
    new_refinery_util  = max(0.0, base["baseline_refinery_util"] - refinery_util_drop)

    # GDP exposure — computed, never guessed by the LLM
    risk_to_gdp_percent = total_additional_cost_bn / base["gdp_bn_usd"] * 100

    # Downstream fuel price impact (rough)
    petrol_price_increase = price_increase_usd * 0.60
    diesel_price_increase = price_increase_usd * 0.55

    return {
        "daily_import_kbd":            round(daily_import_kbd, 0),
        "supply_gap_kbd":              round(supply_gap_kbd, 0),
        "supply_gap_percent":          round(supply_gap_percent, 1),
        "spr_stock_kb":                round(spr_stock_kb, 0),
        "spr_covers_days":             round(spr_covers_days, 1),
        "gap_after_spr_days":          round(gap_after_spr_days, 1),
        "new_brent_price":             round(new_brent_price, 2),
        "price_increase_usd":          round(price_increase_usd, 2),
        "price_cost_per_day_mn":       round(price_cost_per_day_mn, 1),
        "replacement_cost_per_day_mn": round(replacement_cost_per_day_mn, 1),
        "total_cost_per_day_mn":       round(total_cost_per_day_mn, 1),
        "additional_cost_bn_usd":      round(total_additional_cost_bn, 2),
        "baseline_refinery_util_pct":  base["baseline_refinery_util"],
        "refinery_utilisation_pct":    round(new_refinery_util, 1),
        "risk_to_gdp_percent":         round(risk_to_gdp_percent, 3),
        "petrol_increase_usd_bbl":     round(petrol_price_increase, 2),
        "diesel_increase_usd_bbl":     round(diesel_price_increase, 2),
    }


def get_alternative_routes(scenario_key):
    """Return viable alternative procurement options for each scenario."""
    alternatives = {
        "hormuz_closure": [
            {"supplier": "Nigeria",      "grade": "Bonny Light",  "route": "Cape of Good Hope", "extra_days": 7,  "available_kbd": 200},
            {"supplier": "USA",          "grade": "WTI",          "route": "Cape of Good Hope", "extra_days": 10, "available_kbd": 300},
            {"supplier": "Angola",       "grade": "Cabinda",      "route": "Cape of Good Hope", "extra_days": 8,  "available_kbd": 150},
            {"supplier": "Brazil",       "grade": "Lula",         "route": "Atlantic",          "extra_days": 12, "available_kbd": 100},
        ],
        "hormuz_partial": [
            {"supplier": "Nigeria",      "grade": "Bonny Light",  "route": "Cape of Good Hope", "extra_days": 7,  "available_kbd": 200},
            {"supplier": "USA",          "grade": "WTI",          "route": "Cape of Good Hope", "extra_days": 10, "available_kbd": 300},
        ],
        "red_sea_closure": [
            {"supplier": "Saudi Arabia", "grade": "Arab Light",   "route": "Cape of Good Hope", "extra_days": 10, "available_kbd": 800},
            {"supplier": "Iraq",         "grade": "Basra Medium", "route": "Cape of Good Hope", "extra_days": 11, "available_kbd": 600},
        ],
        "opec_emergency_cut": [
            {"supplier": "USA",          "grade": "WTI",          "route": "Cape of Good Hope", "extra_days": 10, "available_kbd": 400},
            {"supplier": "Canada",       "grade": "Heavy Blend",  "route": "Pacific",           "extra_days": 15, "available_kbd": 200},
            {"supplier": "Brazil",       "grade": "Lula",         "route": "Atlantic",          "extra_days": 12, "available_kbd": 200},
        ],
        "russia_sanctions": [
            {"supplier": "Saudi Arabia", "grade": "Arab Light",   "route": "Persian Gulf",      "extra_days": 0,  "available_kbd": 500},
            {"supplier": "Iraq",         "grade": "Basra Heavy",  "route": "Persian Gulf",      "extra_days": 0,  "available_kbd": 400},
            {"supplier": "Nigeria",      "grade": "Bonny Light",  "route": "Cape of Good Hope", "extra_days": 7,  "available_kbd": 300},
            {"supplier": "USA",          "grade": "WTI",          "route": "Cape of Good Hope", "extra_days": 10, "available_kbd": 400},
        ],
    }
    return alternatives.get(scenario_key, [])


def run_scenario(scenario_key):
    """Run a full scenario analysis: economic impact + RAG precedent + LLM narrative."""
    if scenario_key not in SCENARIOS:
        print(f"Unknown scenario: {scenario_key}")
        print(f"Available: {list(SCENARIOS.keys())}")
        return None

    scenario = SCENARIOS[scenario_key]
    print(f"\n{'='*60}")
    print(f"SCENARIO: {scenario['name'].upper()}")
    print(f"{'='*60}")
    print(f"  {scenario['description']}")
    print(f"  Supply cut   : {scenario['supply_cut_percent']}%")
    print(f"  Duration     : {scenario['duration_days']} days")
    print(f"  Price shock  : +{scenario['price_shock_percent']}%")

    # Step 1 — Hard numbers
    print(f"\n[1/4] Computing economic impact...")
    impact = compute_economic_impact(scenario)

    print(f"  Supply gap        : {impact['supply_gap_kbd']} kbd")
    print(f"  New Brent price   : ${impact['new_brent_price']}/barrel")
    print(f"  Extra price cost  : ${impact['price_cost_per_day_mn']}M/day")
    print(f"  Replacement cost  : ${impact['replacement_cost_per_day_mn']}M/day")
    print(f"  Total cost        : ${impact['total_cost_per_day_mn']}M/day")
    print(f"  Additional cost   : ${impact['additional_cost_bn_usd']}B over {scenario['duration_days']} days")
    print(f"  SPR stock         : {impact['spr_stock_kb']} kb")
    print(f"  SPR covers        : {impact['spr_covers_days']} days at this gap")
    print(f"  Gap after SPR     : {impact['gap_after_spr_days']} days uncovered")
    print(f"  Refinery util     : {impact['baseline_refinery_util_pct']}% → {impact['refinery_utilisation_pct']}%")
    print(f"  GDP exposure      : {impact['risk_to_gdp_percent']}%")

    # Step 2 — Alternatives
    print(f"\n[2/4] Identifying alternative procurement routes...")
    alternatives = get_alternative_routes(scenario_key)
    total_alternative_kbd = sum(a["available_kbd"] for a in alternatives)

    for alt in alternatives:
        print(f"  → {alt['supplier']:12} {alt['grade']:15} "
              f"+{alt['extra_days']} days  {alt['available_kbd']} kbd")
    print(f"  Total alternative capacity: {total_alternative_kbd} kbd "
          f"vs gap of {impact['supply_gap_kbd']} kbd")

    # Step 3 — Historical precedent via RAG
    print(f"\n[3/4] Searching historical precedents...")
    similar = query_similar_incidents(
        f"{scenario['description']} oil supply disruption India",
        n_results=2
    )
    historical_context = ""
    for s in similar:
        historical_context += f"\n- {s['metadata']['title']}: {s['metadata']['impact']}"
        print(f"  Similar: {s['metadata']['title']}")

    # Step 4 — LLM narrative. All NUMBERS are given to it; it must not invent any.
    print(f"\n[4/4] Generating AI response plan...")
    alt_summary = ", ".join(
        [f"{a['supplier']} ({a['available_kbd']} kbd)" for a in alternatives]
    ) or "none identified"

    prompt = f"""You are an energy crisis advisor to the Government of India.

SCENARIO: {scenario['name']}
Supply gap: {impact['supply_gap_kbd']} kbd
Brent price: ${impact['new_brent_price']}/barrel
Cost: ${impact['total_cost_per_day_mn']}M/day, ${impact['additional_cost_bn_usd']}B total
SPR covers: {impact['spr_covers_days']} days, leaving {impact['gap_after_spr_days']} days uncovered
Alternative suppliers: {alt_summary}
Historical precedent: {historical_context[:200]}

Use ONLY the numbers above. Do not invent figures.
Return ONLY valid JSON, no markdown, no explanation:
{{"situation_assessment":"two sentences on severity","day_1_actions":["action","action","action"],"week_1_actions":["action","action","action"],"month_1_actions":["action","action"],"spr_recommendation":"specific SPR release recommendation","top_alternative_supplier":"best supplier name and why","key_risk":"the single biggest risk","confidence":"HIGH"}}"""

    response_plan = ask_llm_json(prompt)

    if not response_plan:
        print("  [LLM] Failed — using deterministic fallback plan.")
        response_plan = {
            "situation_assessment":     f"{scenario['name']} opens a {impact['supply_gap_kbd']} kbd supply gap, "
                                        f"leaving {impact['gap_after_spr_days']} days uncovered after SPR drawdown.",
            "day_1_actions":            ["Activate SPR drawdown", "Convene emergency cabinet meeting", "Contact alternative suppliers"],
            "week_1_actions":           ["Negotiate spot contracts", "Activate Cape of Good Hope route", "Reduce non-essential consumption"],
            "month_1_actions":          ["Sign long-term supply agreements", "Accelerate renewable substitution"],
            "spr_recommendation":       f"Release SPR at a rate covering the {impact['supply_gap_kbd']} kbd gap "
                                        f"for up to {impact['spr_covers_days']} days.",
            "top_alternative_supplier": alternatives[0]["supplier"] if alternatives else "Nigeria",
            "key_risk":                 "Alternative capacity is insufficient to fully close the gap before SPR runs out.",
            "confidence":               "MEDIUM",
        }

    # Numbers are OWNED by Python, never by the LLM.
    response_plan["estimated_stabilisation_days"] = scenario["duration_days"]
    response_plan["risk_to_gdp_percent"]          = impact["risk_to_gdp_percent"]

    result = {
        "timestamp":     datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "scenario_key":  scenario_key,
        "scenario":      scenario,
        "impact":        impact,
        "alternatives":  alternatives,
        "total_alternative_kbd":  total_alternative_kbd,
        "alternative_shortfall_kbd": round(
            max(0.0, impact["supply_gap_kbd"] - total_alternative_kbd), 1
        ),
        "response_plan": response_plan,
        "historical_precedents": [s["metadata"]["title"] for s in similar],
    }

    print(f"\n{'='*60}")
    print(f"RESPONSE PLAN")
    print(f"{'='*60}")
    print(f"  Assessment: {response_plan.get('situation_assessment','')}")
    print(f"\n  DAY 1 ACTIONS:")
    for a in response_plan.get("day_1_actions", []):
        print(f"  → {a}")
    print(f"\n  WEEK 1 ACTIONS:")
    for a in response_plan.get("week_1_actions", []):
        print(f"  → {a}")
    print(f"\n  SPR: {response_plan.get('spr_recommendation','')}")
    print(f"  Best alternative: {response_plan.get('top_alternative_supplier','')}")
    print(f"  Key risk: {response_plan.get('key_risk','')}")
    print(f"  Confidence: {response_plan.get('confidence','')}")
    print(f"  Stabilisation: {response_plan.get('estimated_stabilisation_days','')} days")
    print(f"  GDP risk: {response_plan.get('risk_to_gdp_percent','')}%")

    return result


def run_active_scenario():
    """
    Entry point when called with NO argument (e.g. by /api/run-agents).
    Re-runs whatever scenario the user last selected — it does NOT reset
    the dashboard back to a hardcoded default.
    """
    print(f"\n{'='*60}")
    print(f"DISRUPTION SCENARIO MODELLER")
    print(f"Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    populate_knowledge_base()

    # Load snapshot for context (non-fatal if missing)
    try:
        with open(SNAPSHOT_PATH) as f:
            snapshot = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        snapshot = {}
        print("\n  ⚠ Snapshot unavailable — continuing without live context.")

    print(f"\nAvailable scenarios:")
    for key, sc in SCENARIOS.items():
        print(f"  [{key}] {sc['name']}")

    active = get_active_scenario()
    print(f"\nActive scenario (user-selected): {active}")

    result = run_scenario(active)
    if result:
        _atomic_write(OUTPUT_PATH, result)
        print(f"\n  Full scenario saved to: {OUTPUT_PATH}")
    return result


if __name__ == "__main__":
    # With an argument: user explicitly picked a scenario.
    #   e.g. python backend/agents/scenario_modeller.py hormuz_closure
    # Without: re-run whatever is currently active.
    if len(sys.argv) > 1 and sys.argv[1] in SCENARIOS:
        populate_knowledge_base()
        set_active_scenario(sys.argv[1])   # persist the choice
        result = run_scenario(sys.argv[1])
        if result:
            _atomic_write(OUTPUT_PATH, result)
            print(f"\n  Full scenario saved to: {OUTPUT_PATH}")
    else:
        run_active_scenario()