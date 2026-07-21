import sys
import os
import json
import time
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from backend.ingestion.news_fetcher      import fetch_all_news
from backend.ingestion.ais_fetcher       import fetch_all_corridors, get_overall_supply_risk
from backend.ingestion.commodity_fetcher import fetch_all_commodities, get_price_spike_alert
from backend.ingestion.sanctions_fetcher import fetch_sanctions_summary

# Where we save the latest snapshot
SNAPSHOT_PATH = "backend/data/latest_snapshot.json"

def compute_combined_risk(ais_overall, commodity_data, news_articles):
    """
    Combine AIS risk + commodity price risk + news signal count
    into one master risk score for the whole supply chain.
    """
    # AIS corridor risk (40% weight)
    ais_score = ais_overall["overall_risk_score"] * 0.40

    # Commodity price risk (35% weight)
    commodity_scores = []
    for key, data in commodity_data.items():
        commodity_scores.append(data["risk"]["score"])
    avg_commodity_score = sum(commodity_scores) / len(commodity_scores) if commodity_scores else 0
    commodity_score = avg_commodity_score * 0.35

    # News signal intensity (25% weight)
    # Count articles with high-risk keywords
    risk_keywords = [
        "attack", "sanction", "closure", "blockade",
        "missile", "seized", "disruption", "embargo", "conflict"
    ]
    risk_article_count = sum(
        1 for a in news_articles
        if any(kw in (a.get("title","") + a.get("summary","")).lower()
               for kw in risk_keywords)
    )
    # Cap news score at 100
    news_score = min(risk_article_count * 5, 100) * 0.25

    total_score = round(ais_score + commodity_score + news_score, 1)

    level = "LOW"
    if total_score >= 70:
        level = "CRITICAL"
    elif total_score >= 50:
        level = "HIGH"
    elif total_score >= 25:
        level = "MEDIUM"

    return {
        "total_score":      total_score,
        "level":            level,
        "breakdown": {
            "ais_component":       round(ais_score, 1),
            "commodity_component": round(commodity_score, 1),
            "news_component":      round(news_score, 1),
        }
    }

def run_pipeline():
    """Run all 4 ingestion sources and combine into one snapshot."""
    print(f"\n{'='*60}")
    print(f"ENERGY SUPPLY CHAIN INTELLIGENCE PIPELINE")
    print(f"Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    # Step 1 — News
    print("\n[1/4] Fetching news & geopolitical signals...")
    news_articles = fetch_all_news()

    # Step 2 — AIS
    print("\n[2/4] Fetching AIS vessel tracking...")
    corridor_data = fetch_all_corridors()
    ais_overall   = get_overall_supply_risk(corridor_data)

    # Step 3 — Commodities
    print("\n[3/4] Fetching commodity prices...")
    commodity_data = fetch_all_commodities()
    price_alerts   = get_price_spike_alert(commodity_data)

    # Step 4 — Sanctions
    print("\n[4/4] Loading sanctions & trade data...")
    sanctions_data = fetch_sanctions_summary()

    # Step 5 — Combine into master risk score
    combined_risk = compute_combined_risk(ais_overall, commodity_data, news_articles)

    # Step 6 — Build snapshot
    snapshot = {
        "timestamp":       datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "combined_risk":   combined_risk,
        "ais":             ais_overall,
        "commodities":     {k: {"price": v["price"], "unit": v["unit"],
                                "risk_level": v["risk"]["level"],
                                "risk_score": v["risk"]["score"]}
                            for k, v in commodity_data.items()},
        "price_alerts":    price_alerts,
        "news_count":      len(news_articles),
        "news_sample":     [{"title": a["title"], "source": a["source"]}
                            for a in news_articles[:60]],
        "corridors":       {k: {"risk_score": v["risk_score"],
                                "vessels_moving": v["vessels_moving"],
                                "vessels_stopped": v["vessels_stopped"]}
                            for k, v in corridor_data.items()},
        "active_sanctions": len(sanctions_data["sanctions"]),
    }

    # Step 7 — Save snapshot to file
    os.makedirs("backend/data", exist_ok=True)
    with open(SNAPSHOT_PATH, "w") as f:
        json.dump(snapshot, f, indent=2)

    # Step 8 — Print master summary
    print(f"\n{'='*60}")
    print(f"MASTER RISK SUMMARY")
    print(f"{'='*60}")
    print(f"  Overall Risk Score : {combined_risk['total_score']}/100")
    print(f"  Risk Level         : {combined_risk['level']}")
    print(f"  AIS Component      : {combined_risk['breakdown']['ais_component']}/40")
    print(f"  Commodity Component: {combined_risk['breakdown']['commodity_component']}/35")
    print(f"  News Component     : {combined_risk['breakdown']['news_component']}/25")
    print(f"  News articles      : {len(news_articles)}")
    print(f"  Price alerts       : {len(price_alerts)}")
    print(f"  Active sanctions   : {snapshot['active_sanctions']}")
    print(f"\n  Snapshot saved to  : {SNAPSHOT_PATH}")
    print(f"{'='*60}")

    if combined_risk["level"] in ["HIGH", "CRITICAL"]:
        print(f"\n  ⚠ ALERT: Risk level is {combined_risk['level']}")
        print(f"  Triggering AI agents for scenario analysis...")
    else:
        print(f"\n  ✓ Risk within manageable range — monitoring continues")

    return snapshot

def run_continuous(interval_minutes=30):
    """Run pipeline continuously every N minutes."""
    print(f"Starting continuous monitoring (every {interval_minutes} min)")
    print("Press Ctrl+C to stop\n")
    while True:
        try:
            run_pipeline()
            print(f"\nNext run in {interval_minutes} minutes...")
            time.sleep(interval_minutes * 60)
        except KeyboardInterrupt:
            print("\nMonitoring stopped.")
            break

if __name__ == "__main__":
    # Run once for testing
    snapshot = run_pipeline()