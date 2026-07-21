import os
import json
import sys
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from backend.llm_client import ask_llm_json
from backend.knowledge.rag_store import populate_knowledge_base, query_regulations

OUTPUT_PATH = "backend/data/spr_recommendation.json"

INDIA_DAILY_CONSUMPTION_KBD = 5200   # thousand barrels PER DAY (a rate)

# India SPR. Key correction: SPR is a STOCK measured in thousand barrels (kb),
# NOT a rate in kbd. 5.33 MMT of crude ≈ 39,000 kb ≈ 7.5 days of consumption.
SPR_CONFIG = {
    "total_capacity_mmt":   5.33,
    "total_capacity_kb":    39000,    # thousand barrels held in storage (STOCK)
    "min_reserve_days":     3,        # days of consumption never to be touched
    "locations": {
        "Visakhapatnam": {"capacity_kb": 9750,  "state": "Andhra Pradesh"},
        "Mangalore":     {"capacity_kb": 11250, "state": "Karnataka"},
        "Padur":         {"capacity_kb": 18000, "state": "Karnataka"},
    },
    "replenishment_rate_kbd": 200,    # rate we can refill at (kbd)
    "approval_required":      "Cabinet Committee on Economic Affairs",
}


def _atomic_write(path, payload):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(payload, f, indent=2)
    os.replace(tmp, path)


def compute_spr_schedule(
    supply_gap_kbd,
    disruption_days,
    alternative_arrival_days,
    current_fill_percent=95.0
):
    """
    SPR is a STOCK (kb). Drawdown is a RATE (kbd). Days = stock / rate.

    Phase 1: before alternatives arrive — SPR covers the full gap
    Phase 2: alternatives have landed — SPR tops up the residual gap
    """
    total_stock_kb   = SPR_CONFIG["total_capacity_kb"]
    available_kb     = total_stock_kb * (current_fill_percent / 100)
    min_reserve_kb   = SPR_CONFIG["min_reserve_days"] * INDIA_DAILY_CONSUMPTION_KBD
    usable_kb        = max(0.0, available_kb - min_reserve_kb)

    # How long the usable stock lasts if we draw at the full gap rate
    if supply_gap_kbd > 0:
        spr_exhaustion_day = usable_kb / supply_gap_kbd
    else:
        spr_exhaustion_day = float(disruption_days)

    # Phase 1 — draw at the full gap rate until alternatives arrive
    phase1_days     = int(min(alternative_arrival_days, disruption_days))
    phase1_draw_kbd = float(supply_gap_kbd)
    phase1_total_kb = min(phase1_draw_kbd * phase1_days, usable_kb)

    # If the stock runs out before alternatives land, flag it
    spr_runs_out_before_alternatives = (
        supply_gap_kbd > 0 and spr_exhaustion_day < alternative_arrival_days
    )

    # Phase 2 — alternatives cover ~70% of the gap; SPR fills the remaining 30%
    phase2_days   = int(max(0, disruption_days - alternative_arrival_days))
    remaining_kb  = max(0.0, usable_kb - phase1_total_kb)

    if phase2_days > 0 and remaining_kb > 0:
        desired_phase2_kbd = supply_gap_kbd * 0.30
        max_sustainable_kbd = remaining_kb / phase2_days
        phase2_draw_kbd = min(desired_phase2_kbd, max_sustainable_kbd)
        phase2_total_kb = phase2_draw_kbd * phase2_days
    else:
        phase2_draw_kbd = 0.0
        phase2_total_kb = 0.0

    total_used_kb = phase1_total_kb + phase2_total_kb

    # Days of the crisis actually covered by SPR at the full gap rate
    days_covered = (total_used_kb / supply_gap_kbd) if supply_gap_kbd > 0 else float(disruption_days)
    days_covered = min(days_covered, float(disruption_days))
    days_uncovered = max(0.0, disruption_days - days_covered)

    replenishment_start_day = disruption_days + 7
    replenishment_rate_kbd  = SPR_CONFIG["replenishment_rate_kbd"]
    replenishment_days      = total_used_kb / replenishment_rate_kbd if replenishment_rate_kbd else 0

    return {
        # stocks (thousand barrels)
        "total_stock_kb":       round(total_stock_kb, 0),
        "available_spr_kb":     round(available_kb, 0),
        "min_reserve_kb":       round(min_reserve_kb, 0),
        "usable_spr_kb":        round(usable_kb, 0),
        "phase1_total_kb":      round(phase1_total_kb, 0),
        "phase2_total_kb":      round(phase2_total_kb, 0),
        "total_spr_used_kb":    round(total_used_kb, 0),
        # rates (thousand barrels per day)
        "phase1_draw_per_day_kbd": round(phase1_draw_kbd, 1),
        "phase2_draw_per_day_kbd": round(phase2_draw_kbd, 1),
        "replenishment_rate_kbd":  replenishment_rate_kbd,
        # durations (days)
        "phase1_days":              phase1_days,
        "phase2_days":              phase2_days,
        "spr_exhaustion_day":       round(spr_exhaustion_day, 1),
        "days_crisis_covered":      round(days_covered, 1),
        "days_uncovered":           round(days_uncovered, 1),
        "replenishment_start_day":  replenishment_start_day,
        "replenishment_days_needed": round(replenishment_days, 0),
        # flags
        "spr_runs_out_before_alternatives": spr_runs_out_before_alternatives,
        "fully_covers_crisis": days_uncovered <= 0,
    }


def generate_daily_timeline(schedule, supply_gap_kbd, disruption_days, alternative_arrival_days):
    """Day-by-day SPR stock (kb) and draw rate (kbd)."""
    timeline  = []
    stock_kb  = schedule["usable_spr_kb"]

    for day in range(1, min(disruption_days, 30) + 1):
        if day <= alternative_arrival_days:
            desired_draw = schedule["phase1_draw_per_day_kbd"]
            phase        = "Phase 1 — SPR covering full gap"
            alt_supply   = 0.0
        else:
            desired_draw = schedule["phase2_draw_per_day_kbd"]
            phase        = "Phase 2 — Alternatives arrived, SPR supplementing"
            alt_supply   = round(supply_gap_kbd * 0.70, 1)

        # Can't draw more than remains
        draw = min(desired_draw, stock_kb)
        stock_kb = max(0.0, stock_kb - draw)

        # Days of cover left at the CURRENT draw rate
        if draw > 0:
            days_left = stock_kb / draw
        else:
            days_left = 999.0

        if stock_kb <= 0:
            status = "⚫ EXHAUSTED"
        elif days_left < 3:
            status = "🔴 CRITICAL"
        elif days_left < 5:
            status = "🟡 WARNING"
        else:
            status = "🟢 STABLE"

        timeline.append({
            "day":            day,
            "phase":          phase,
            "spr_draw_kbd":   round(draw, 1),
            "alt_supply_kbd": alt_supply,
            "spr_remaining_kb": round(stock_kb, 0),
            "spr_days_left":  round(min(days_left, 999), 1),
            "status":         status,
        })

    return timeline


def run_spr_agent():
    print(f"\n{'='*60}")
    print(f"SPR OPTIMISATION AGENT")
    print(f"Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    populate_knowledge_base()

    try:
        with open("backend/data/scenario_analysis.json") as f:
            scenario = json.load(f)
        supply_gap_kbd  = scenario["impact"]["supply_gap_kbd"]
        disruption_days = scenario["scenario"]["duration_days"]
        scenario_name   = scenario["scenario"]["name"]
        brent_price     = scenario["impact"]["new_brent_price"]
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        supply_gap_kbd  = 824.0
        disruption_days = 14
        scenario_name   = "Hormuz Partial Disruption"
        brent_price     = 83.83

    try:
        with open("backend/data/procurement_recommendations.json") as f:
            procurement = json.load(f)
        plan = procurement.get("procurement_plan", [])
        alternative_arrival_days = min(
            [p["delivery_days"] for p in plan], default=18
        )
        top_supplier = plan[0]["country"] if plan else "Nigeria"
    except (FileNotFoundError, json.JSONDecodeError):
        alternative_arrival_days = 18
        top_supplier             = "Nigeria"

    print(f"\n  Scenario         : {scenario_name}")
    print(f"  Supply gap       : {supply_gap_kbd} kbd")
    print(f"  Disruption length: {disruption_days} days")
    print(f"  Alt. arrival     : Day {alternative_arrival_days}")
    print(f"  Top supplier     : {top_supplier}")

    print(f"\n[1/4] Computing optimal SPR drawdown schedule...")
    schedule = compute_spr_schedule(
        supply_gap_kbd           = supply_gap_kbd,
        disruption_days          = disruption_days,
        alternative_arrival_days = alternative_arrival_days,
    )

    print(f"\n  SPR STATUS (stock in thousand barrels, draw rate in kbd):")
    print(f"  Total capacity   : {schedule['total_stock_kb']} kb")
    print(f"  Available (95%)  : {schedule['available_spr_kb']} kb")
    print(f"  Minimum reserve  : {schedule['min_reserve_kb']} kb (never touch)")
    print(f"  Usable SPR       : {schedule['usable_spr_kb']} kb")
    print(f"  Exhausted on     : Day {schedule['spr_exhaustion_day']} "
          f"if drawn at the full {supply_gap_kbd} kbd gap rate")

    print(f"\n  DRAWDOWN PLAN:")
    print(f"  Phase 1 (Days 1–{schedule['phase1_days']}): "
          f"draw {schedule['phase1_draw_per_day_kbd']} kbd/day "
          f"→ {schedule['phase1_total_kb']} kb total")
    if schedule["phase2_days"] > 0:
        print(f"  Phase 2 (Days {schedule['phase1_days']+1}–{disruption_days}): "
              f"draw {schedule['phase2_draw_per_day_kbd']} kbd/day "
              f"→ {schedule['phase2_total_kb']} kb total")
    print(f"  Total SPR used   : {schedule['total_spr_used_kb']} kb")
    print(f"  Crisis covered   : {schedule['days_crisis_covered']} of {disruption_days} days")
    print(f"  Days uncovered   : {schedule['days_uncovered']}")

    if schedule["spr_runs_out_before_alternatives"]:
        print(f"\n  ⚠ SPR is exhausted on Day {schedule['spr_exhaustion_day']}, "
              f"BEFORE alternatives arrive on Day {alternative_arrival_days}. "
              f"Demand-side rationing required.")

    print(f"\n[2/4] Generating day-by-day timeline...")
    timeline = generate_daily_timeline(
        schedule, supply_gap_kbd, disruption_days, alternative_arrival_days
    )

    print(f"\n  DAY-BY-DAY SPR STATUS (first 10 days):")
    print(f"  {'Day':<5} {'Draw kbd':<11} {'Stock kb':<11} {'Days Left':<11} {'Status'}")
    print(f"  {'-'*58}")
    for t in timeline[:10]:
        print(f"  {t['day']:<5} {t['spr_draw_kbd']:<11} "
              f"{t['spr_remaining_kb']:<11} {t['spr_days_left']:<11} {t['status']}")

    print(f"\n[3/4] Checking regulatory requirements...")
    regs = query_regulations("SPR drawdown emergency approval procedure")
    for r in regs[:1]:
        print(f"  Regulation: {r['metadata']['title']}")
        print(f"  {r['content'][:150]}...")

    print(f"\n[4/4] Generating policy recommendation...")
    prompt = f"""You are an SPR policy advisor to India's Petroleum Ministry.

Crisis: {scenario_name}
Supply gap: {supply_gap_kbd} kbd for {disruption_days} days
Usable SPR stock: {schedule['usable_spr_kb']} thousand barrels
Phase 1 draw: {schedule['phase1_draw_per_day_kbd']} kbd/day for {schedule['phase1_days']} days
SPR exhausted on Day {schedule['spr_exhaustion_day']} at full draw rate
Alternatives arrive Day {alternative_arrival_days} from {top_supplier}
Days of the crisis SPR can cover: {schedule['days_crisis_covered']}; uncovered: {schedule['days_uncovered']}
Replenishment starts Day {schedule['replenishment_start_day']}
Approval body: {SPR_CONFIG['approval_required']}

Use ONLY these figures. Do not invent numbers.
Return ONLY valid JSON, no markdown:
{{"policy_recommendation":"two sentences for the petroleum minister","approval_urgency":"IMMEDIATE","communication_to_states":"one sentence","replenishment_strategy":"one sentence","risk_if_delayed":"one sentence"}}"""

    policy = ask_llm_json(prompt)

    if not policy:
        print("  [LLM] Failed — using deterministic fallback policy.")
        policy = {
            "policy_recommendation": (
                f"Initiate Phase 1 SPR release of {schedule['phase1_draw_per_day_kbd']} kbd/day "
                f"immediately, pending CCEA approval. This covers "
                f"{schedule['days_crisis_covered']} of {disruption_days} crisis days."
            ),
            "approval_urgency":       "IMMEDIATE",
            "communication_to_states": "Alert state fuel distributors to prepare rationing protocols.",
            "replenishment_strategy": (
                f"Begin replenishment at {schedule['replenishment_rate_kbd']} kbd from Day "
                f"{schedule['replenishment_start_day']}, sourcing from {top_supplier}."
            ),
            "risk_if_delayed": (
                f"SPR exhausts on Day {schedule['spr_exhaustion_day']}, "
                f"leaving {schedule['days_uncovered']} days of the crisis uncovered."
            ),
        }

    for k, v in {
        "policy_recommendation": "",
        "approval_urgency": "IMMEDIATE",
        "communication_to_states": "",
        "replenishment_strategy": "",
        "risk_if_delayed": "",
    }.items():
        policy.setdefault(k, v)

    output = {
        "timestamp":  datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "scenario":   scenario_name,
        "supply_gap_kbd":  supply_gap_kbd,
        "disruption_days": disruption_days,
        "alternative_arrival_days": alternative_arrival_days,
        "top_supplier": top_supplier,
        "spr_config": SPR_CONFIG,
        "schedule":   schedule,
        "timeline":   timeline,
        "policy":     policy,
        "locations":  SPR_CONFIG["locations"],
    }

    _atomic_write(OUTPUT_PATH, output)

    print(f"\n{'='*60}")
    print(f"SPR POLICY RECOMMENDATION")
    print(f"{'='*60}")
    print(f"  {policy.get('policy_recommendation','')}")
    print(f"  Approval urgency : {policy.get('approval_urgency','')}")
    print(f"  States advisory  : {policy.get('communication_to_states','')}")
    print(f"  Replenishment    : {policy.get('replenishment_strategy','')}")
    print(f"  Risk if delayed  : {policy.get('risk_if_delayed','')}")
    print(f"\n  SPR locations (storage capacity in thousand barrels):")
    for loc, data in SPR_CONFIG["locations"].items():
        print(f"  → {loc:<20} {data['capacity_kb']} kb — {data['state']}")
    print(f"\n  Full SPR plan saved to: {OUTPUT_PATH}")
    print(f"{'='*60}")

    return output


if __name__ == "__main__":
    run_spr_agent()