import os
import json
import sys
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from backend.llm_client  import ask_llm, ask_llm_json
from backend.knowledge.rag_store import (
    populate_knowledge_base,
    query_similar_incidents,
    query_regulations,
)

SNAPSHOT_PATH = "backend/data/latest_snapshot.json"
OUTPUT_PATH   = "backend/data/geopolitical_analysis.json"

def load_snapshot():
    with open(SNAPSHOT_PATH) as f:
        return json.load(f)

def analyse_corridor(corridor_name, corridor_data, news_sample):
    """
    For each shipping corridor:
    1. Pull similar historical incidents from RAG
    2. Ask LLM to assess current risk with historical context
    """
    print(f"\n  Analysing {corridor_name.replace('_',' ').title()}...")

    # Step 1 — Find similar historical incidents
    query = f"{corridor_name} oil tanker disruption attack sanctions shipping risk"
    similar = query_similar_incidents(query, n_results=2, corridor=corridor_name)

    # Build historical context string
    historical_context = ""
    if similar:
        historical_context = "\n\nRELEVANT HISTORICAL INCIDENTS:\n"
        for inc in similar:
            historical_context += f"""
- {inc['metadata']['title']} ({inc['metadata']['date']})
  Impact: {inc['metadata']['impact']}
  Severity at time: {inc['metadata']['severity']}/10
"""

    # Step 2 — Build relevant news context
    risk_keywords = [
        corridor_name.replace("_", " "),
        "hormuz", "red sea", "suez", "iran", "houthi",
        "sanction", "attack", "tanker", "opec"
    ]
    relevant_news = [
        a for a in news_sample
        if any(kw in (a.get("title","") + a.get("summary","")).lower()
               for kw in risk_keywords)
    ][:5]

    news_context = ""
    if relevant_news:
        news_context = "\n\nRECENT RELEVANT NEWS:\n"
        for n in relevant_news:
            news_context += f"- {n['title']} ({n['source']})\n"

    # Step 3 — Ask LLM for risk assessment
    prompt = f"""You are an energy supply chain risk analyst for India.

Assess the current risk level for the {corridor_name.replace('_',' ').upper()} shipping corridor.

CURRENT DATA:
- Vessels moving  : {corridor_data['vessels_moving']}
- Vessels stopped : {corridor_data['vessels_stopped']}
- Current risk score: {corridor_data['risk_score']}/100
{historical_context}
{news_context}

Return ONLY this JSON:
{{
    "corridor": "{corridor_name}",
    "risk_score": number between 0-100,
    "risk_level": "LOW|MEDIUM|HIGH|CRITICAL",
    "primary_threat": "one sentence describing main threat",
    "historical_precedent": "which past incident is most similar and what happened",
    "recommendation": "one concrete action India should take now",
    "confidence": number between 0.0-1.0
}}"""

    result = ask_llm_json(prompt)

    if not result:
        # Fallback if LLM fails
        result = {
            "corridor":             corridor_name,
            "risk_score":           corridor_data["risk_score"],
            "risk_level":           "MEDIUM" if corridor_data["risk_score"] > 20 else "LOW",
            "primary_threat":       "Unable to assess — using sensor data only",
            "historical_precedent": "No similar incident retrieved",
            "recommendation":       "Continue monitoring",
            "confidence":           0.3,
        }

    return result, similar

def run_geopolitical_agent():
    print(f"\n{'='*60}")
    print(f"GEOPOLITICAL RISK INTELLIGENCE AGENT")
    print(f"Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    # Load latest data snapshot
    print("\n[1/4] Loading latest pipeline snapshot...")
    snapshot = load_snapshot()

    # Ensure knowledge base is ready
    print("[2/4] Connecting to knowledge base...")
    populate_knowledge_base()

    # Analyse each corridor
    print("[3/4] Analysing corridors with AI + historical context...")
    corridor_analyses = {}
    all_similar       = {}

    for corridor_name, corridor_data in snapshot["corridors"].items():
        analysis, similar = analyse_corridor(
            corridor_name,
            corridor_data,
            snapshot.get("news_sample", [])
        )
        corridor_analyses[corridor_name] = analysis
        all_similar[corridor_name]       = [
            s["metadata"]["title"] for s in similar
        ]

    # Step 4 — Overall assessment
    print("\n[4/4] Generating overall supply chain assessment...")
    scores = [a["risk_score"] for a in corridor_analyses.values()]
    avg_score = sum(scores) / len(scores) if scores else 0

    overall_prompt = f"""You are India's chief energy security advisor.

Based on these corridor risk assessments, give an overall supply chain risk summary.

CORRIDOR RISKS:
{json.dumps({k: {'risk_level': v['risk_level'],
                  'risk_score': v['risk_score'],
                  'primary_threat': v['primary_threat']}
             for k, v in corridor_analyses.items()}, indent=2)}

CURRENT COMMODITY PRICES:
- Brent Crude: {snapshot['commodities']['brent_crude']['price']} USD/barrel
- WTI: {snapshot['commodities']['wti_crude']['price']} USD/barrel

NEWS SIGNALS: {snapshot['news_count']} articles monitored

Return ONLY this JSON:
{{
    "overall_risk_score": number 0-100,
    "overall_risk_level": "LOW|MEDIUM|HIGH|CRITICAL",
    "executive_summary": "2-3 sentences for a minister to read",
    "immediate_actions": ["action1", "action2", "action3"],
    "watch_list": ["thing to watch 1", "thing to watch 2"]
}}"""

    overall = ask_llm_json(overall_prompt)

    if not overall:
        overall = {
            "overall_risk_score":  round(avg_score, 1),
            "overall_risk_level":  "MEDIUM",
            "executive_summary":   "Supply chain under moderate stress. Hormuz and Red Sea elevated.",
            "immediate_actions":   ["Monitor Hormuz corridor", "Check SPR levels"],
            "watch_list":          ["Iran nuclear talks", "Houthi activity"],
        }

    # Build final output
    output = {
        "timestamp":          datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "agent":              "GeopoliticalRiskIntelligenceAgent",
        "overall":            overall,
        "corridors":          corridor_analyses,
        "historical_matches": all_similar,
    }

    # Save output
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)

    # Print summary
    print(f"\n{'='*60}")
    print(f"GEOPOLITICAL RISK ASSESSMENT COMPLETE")
    print(f"{'='*60}")
    print(f"  Overall Risk Score : {overall.get('overall_risk_score', 'N/A')}/100")
    print(f"  Overall Risk Level : {overall.get('overall_risk_level', 'N/A')}")
    print(f"\n  Executive Summary:")
    print(f"  {overall.get('executive_summary', 'N/A')}")
    print(f"\n  Immediate Actions:")
    for action in overall.get("immediate_actions", []):
        print(f"  → {action}")
    print(f"\n  Watch List:")
    for item in overall.get("watch_list", []):
        print(f"  👁 {item}")
    print(f"\n  Corridor Breakdown:")
    for corridor, analysis in corridor_analyses.items():
        print(f"  {corridor.replace('_',' ').title():25} "
              f"{analysis['risk_level']:8} "
              f"({analysis['risk_score']}/100)")
    print(f"\n  Full analysis saved to: {OUTPUT_PATH}")
    print(f"{'='*60}")

    return output

if __name__ == "__main__":
    run_geopolitical_agent()