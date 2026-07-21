import os
import json
import sys
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

OUTPUT_PATH = "backend/data/digital_twin.json"

DATA_FILES = {
    "snapshot":       "backend/data/latest_snapshot.json",
    "geopolitical":   "backend/data/geopolitical_analysis.json",
    "scenario":       "backend/data/scenario_analysis.json",
    "procurement":    "backend/data/procurement_recommendations.json",
    "spr":            "backend/data/spr_recommendation.json",
}

def load_file(path):
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def build_digital_twin():
    print(f"\n{'='*60}")
    print(f"SUPPLY CHAIN DIGITAL TWIN")
    print(f"Building unified state...")
    print(f"{'='*60}")

    # Load all agent outputs
    snapshot     = load_file(DATA_FILES["snapshot"])
    geopolitical = load_file(DATA_FILES["geopolitical"])
    scenario     = load_file(DATA_FILES["scenario"])
    procurement  = load_file(DATA_FILES["procurement"])
    spr          = load_file(DATA_FILES["spr"])

    # ── Master risk score ─────────────────────────────────
    overall_risk = geopolitical.get("overall", {})
    risk_score   = overall_risk.get("overall_risk_score", 0)
    risk_level   = overall_risk.get("overall_risk_level", "UNKNOWN")

    # ── Corridor states ───────────────────────────────────
    corridors = {}
    raw_corridors = snapshot.get("corridors", {})
    geo_corridors = geopolitical.get("corridors", {})

    for name, data in raw_corridors.items():
        geo_data = geo_corridors.get(name, {})
        corridors[name] = {
            "risk_score":      data.get("risk_score", 0),
            "risk_level":      geo_data.get("risk_level", "UNKNOWN"),
            "vessels_moving":  data.get("vessels_moving", 0),
            "vessels_stopped": data.get("vessels_stopped", 0),
            "primary_threat":  geo_data.get("primary_threat", ""),
            "recommendation":  geo_data.get("recommendation", ""),
        }

    # ── Active scenario ───────────────────────────────────
    active_scenario = {}
    if scenario:
        active_scenario = {
            "name":              scenario.get("scenario", {}).get("name", ""),
            "supply_cut":        scenario.get("scenario", {}).get("supply_cut_percent", 0),
            "duration_days":     scenario.get("scenario", {}).get("duration_days", 0),
            "supply_gap_kbd":    scenario.get("impact", {}).get("supply_gap_kbd", 0),
            "new_brent":         scenario.get("impact", {}).get("new_brent_price", 0),
            "additional_cost_bn": scenario.get("impact", {}).get("additional_cost_bn_usd", 0),
            "spr_days":          scenario.get("impact", {}).get("spr_covers_days", 0),
            "response_plan":     scenario.get("response_plan", {}),
        }

    # ── Procurement state ─────────────────────────────────
    procurement_state = {}
    if procurement:
        plan = procurement.get("procurement_plan", [])
        procurement_state = {
            "gap_coverage_pct": procurement.get("gap_coverage_pct", 0),
            "top_suppliers":    [p["country"] for p in plan[:3]],
            "total_suppliers":  len(plan),
            "summary":          procurement.get("executive_summary", {}).get("executive_summary", ""),
            "daily_cost_mn":    procurement.get("executive_summary", {}).get("estimated_cost_per_day_mn_usd", 0),
        }

    # ── SPR state ─────────────────────────────────────────
    spr_state = {}
    if spr:
        schedule = spr.get("schedule", {})
        spr_state = {
            "usable_kbd":          schedule.get("usable_spr_kbd", 0),
            "phase1_draw_kbd":     schedule.get("phase1_draw_per_day_kbd", 0),
            "total_used_kbd":      schedule.get("total_spr_used_kbd", 0),
            "replenishment_day":   schedule.get("replenishment_start_day", 0),
            "policy":              spr.get("policy", {}).get("policy_recommendation", ""),
            "approval_urgency":    spr.get("policy", {}).get("approval_urgency", ""),
            "locations":           list(spr.get("spr_config", {}).get("locations", {}).keys()),
            "timeline":            spr.get("timeline", [])[:7],
        }

    # ── Commodity prices ──────────────────────────────────
    commodities = snapshot.get("commodities", {})

    # ── News intelligence ─────────────────────────────────
    # ── News intelligence ─────────────────────────────────
    news_sample = snapshot.get("news_sample", [])
    news_intel = {
        "total_articles":    snapshot.get("total_articles", len(news_sample)),
        "sample":            news_sample,
        "price_alerts":      snapshot.get("price_alerts", []),
    }

    # ── Immediate actions ─────────────────────────────────
    immediate_actions = overall_risk.get("immediate_actions", [])

    # ── Build complete twin ───────────────────────────────
    twin = {
        "timestamp":          datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "version":            "1.0",
        "master_risk": {
            "score":          risk_score,
            "level":          risk_level,
            "executive_summary": overall_risk.get("executive_summary", ""),
            "watch_list":     overall_risk.get("watch_list", []),
        },
        "corridors":          corridors,
        "commodities":        commodities,
        "active_scenario":    active_scenario,
        "procurement":        procurement_state,
        "spr":                spr_state,
        "news":               news_intel,
        "immediate_actions":  immediate_actions,
    }

    # Save
    os.makedirs("backend/data", exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(twin, f, indent=2)

    # Print summary
    print(f"\n  DIGITAL TWIN STATE")
    print(f"  {'='*40}")
    print(f"  Master risk score  : {risk_score}/100 ({risk_level})")
    print(f"  Corridors tracked  : {len(corridors)}")
    print(f"  Active scenario    : {active_scenario.get('name', 'None')}")
    print(f"  Supply gap         : {active_scenario.get('supply_gap_kbd', 0)} kbd")
    print(f"  Procurement cover  : {procurement_state.get('gap_coverage_pct', 0)}%")
    print(f"  Top suppliers      : {', '.join(procurement_state.get('top_suppliers', []))}")
    print(f"  SPR usable         : {spr_state.get('usable_kbd', 0)} kbd")
    print(f"  News articles      : {news_intel['total_articles']}")
    print(f"\n  CORRIDOR RISK LEVELS:")
    for name, data in corridors.items():
        print(f"  {name.replace('_',' ').title():<25} "
              f"{data['risk_level']:<10} ({data['risk_score']}/100)")
    print(f"\n  IMMEDIATE ACTIONS:")
    for action in immediate_actions[:3]:
        print(f"  → {action}")
    print(f"\n  Digital twin saved to: {OUTPUT_PATH}")
    print(f"{'='*60}")

    return twin

if __name__ == "__main__":
    twin = build_digital_twin()