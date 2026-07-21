import os
import json
import chromadb
from datetime import datetime

# Initialize ChromaDB — stores everything locally in a folder
CHROMA_PATH = "backend/data/chroma_db"
client      = chromadb.PersistentClient(path=CHROMA_PATH)

# Our knowledge collections
COLLECTIONS = {
    "incidents":    "historical_incidents",
    "regulations":  "regulatory_documents",
    "procurement":  "procurement_decisions",
    "geopolitical": "geopolitical_events",
}

# ── Seed data — Historical incidents ─────────────────────
HISTORICAL_INCIDENTS = [
    {
        "id":       "INC001",
        "title":    "2019 Strait of Hormuz Tanker Attacks",
        "date":     "2019-06-13",
        "corridor": "hormuz",
        "type":     "military",
        "severity": 8,
        "content":  """Two oil tankers were attacked near the Strait of Hormuz in June 2019.
        The Front Altair and Kokuka Courageous were struck by suspected mines or torpedoes.
        Brent crude prices jumped 4% immediately. India was forced to seek alternative
        suppliers from West Africa. The incident lasted 3 weeks before shipping normalized.
        Key lesson: India needs 30-day strategic reserve minimum for Hormuz disruptions.""",
        "impact":   "Brent +4%, India sourced from Nigeria and Angola as backup",
        "resolution": "US Navy escort program established, shipping resumed in 3 weeks",
    },
    {
        "id":       "INC002",
        "title":    "2021 Suez Canal Blockage — Ever Given",
        "date":     "2021-03-23",
        "corridor": "suez",
        "type":     "weather",
        "severity": 7,
        "content":  """Container ship Ever Given ran aground in Suez Canal for 6 days.
        Blocked approximately $9.6 billion worth of trade per day. Oil tankers were
        diverted around Cape of Good Hope adding 7-10 days to journey. Brent crude
        rose 6% during blockage. India's refineries had 15 days buffer stock which
        was sufficient. Cape of Good Hope route proved viable alternative.""",
        "impact":   "Brent +6%, Cape route activated, 7-10 day delivery delay",
        "resolution": "Ship refloated after 6 days, backlog cleared in 2 weeks",
    },
    {
        "id":       "INC003",
        "title":    "2022 Russia Ukraine War — Oil Sanctions",
        "date":     "2022-02-24",
        "corridor": "multiple",
        "type":     "sanctions",
        "severity": 9,
        "content":  """Russia invaded Ukraine triggering unprecedented Western sanctions.
        EU and US banned Russian oil imports. India opportunistically increased Russian
        crude imports from 2% to 38% of total supply taking advantage of steep discounts.
        Brent crude peaked at $139/barrel in March 2022. India saved approximately
        $35 billion by buying discounted Russian crude. Price cap of $60/barrel imposed
        by G7 in December 2022. Russia rerouted exports to India and China.""",
        "impact":   "Brent peaked $139, India shifted to 38% Russian crude at discount",
        "resolution": "India diversified to Russian supply, Western nations found alternatives",
    },
    {
        "id":       "INC004",
        "title":    "2023-2024 Houthi Red Sea Attacks",
        "date":     "2023-11-19",
        "corridor": "red_sea",
        "type":     "military",
        "severity": 8,
        "content":  """Houthi rebels began attacking commercial shipping in Red Sea
        in solidarity with Gaza conflict. Over 100 vessels attacked by end of 2024.
        Major shipping companies diverted to Cape of Good Hope. Red Sea traffic
        dropped 50%. Shipping costs rose 300%. India's imports via Suez increased
        journey time by 10-14 days. LNG and oil tankers avoided Red Sea entirely.
        US-led Operation Prosperity Guardian launched but attacks continued.""",
        "impact":   "Shipping costs +300%, Red Sea traffic -50%, journey +14 days",
        "resolution": "Ongoing as of 2026 — Cape of Good Hope now primary route",
    },
    {
        "id":       "INC005",
        "title":    "2025 US-Iran Standoff — Brent Spike",
        "date":     "2025-04-15",
        "corridor": "hormuz",
        "type":     "political",
        "severity": 7,
        "content":  """Renewed US-Iran tensions over nuclear program caused Brent crude
        to spike 8% in a single trading session. Iran threatened to close Strait of
        Hormuz. India's strategic petroleum reserves were drawn down by 2 days worth.
        Indian refiners scrambled to spot market paying 15% premium. Incident resolved
        diplomatically in 3 weeks. India identified need for 30-day SPR minimum.""",
        "impact":   "Brent +8% single session, India paid 15% spot market premium",
        "resolution": "Diplomatic resolution in 3 weeks, Iran backed down on Hormuz threat",
    },
    {
        "id":       "INC006",
        "title":    "OPEC+ Emergency Production Cut 2023",
        "date":     "2023-04-02",
        "corridor": "none",
        "type":     "economic",
        "severity": 6,
        "content":  """OPEC+ announced surprise production cut of 1.16 million barrels
        per day in April 2023. Saudi Arabia led the cut with 500,000 bpd reduction.
        Brent jumped 8% on announcement day. India faced higher import costs of
        approximately $2 billion additional annually. India accelerated negotiations
        with non-OPEC suppliers including USA, Canada, and Brazil.""",
        "impact":   "Brent +8%, India import costs +$2B annually",
        "resolution": "India diversified to US, Canadian crude as partial offset",
    },
]

REGULATORY_DOCS = [
    {
        "id":      "REG001",
        "title":   "India Strategic Petroleum Reserve Policy",
        "content": """India maintains Strategic Petroleum Reserves at Visakhapatnam,
        Mangalore, and Padur with total capacity of 5.33 million metric tonnes — 
        approximately 9.5 days of national consumption. Policy mandates minimum
        7-day operational reserve at all times. SPR drawdown requires Cabinet
        Committee on Economic Affairs approval. Replenishment must occur within
        90 days of drawdown. India plans to expand SPR to 12 days coverage by 2027.""",
    },
    {
        "id":      "REG002",
        "title":   "OISD Guidelines for Oil Import Operations",
        "content": """Oil Industry Safety Directorate guidelines mandate minimum
        15-day inventory at refineries. Emergency procurement procedures allow
        bypassing normal tender process for disruptions exceeding 7 days.
        Refinery grade compatibility must be verified before emergency procurement.
        Indian refineries classified into three categories based on crude processing
        flexibility. Tier 1 refineries like Jamnagar can process any grade.""",
    },
    {
        "id":      "REG003",
        "title":   "PPAC Emergency Response Protocol",
        "content": """Petroleum Planning and Analysis Cell protocol for supply
        emergencies. Level 1 alert: price spike above 15% in 30 days — increase
        monitoring. Level 2 alert: supply disruption above 10% — activate SPR.
        Level 3 alert: disruption above 25% — invoke emergency import procedures.
        Inter-ministerial committee convened within 24 hours of Level 2 alert.""",
    },
]

def get_or_create_collection(name):
    """Get existing collection or create new one."""
    try:
        return client.get_collection(name)
    except Exception:
        return client.create_collection(name)

def populate_knowledge_base():
    """Load all seed data into ChromaDB."""
    print(f"\n{'='*50}")
    print(f"Populating Knowledge Base")
    print(f"{'='*50}")

    # Load incidents
    collection = get_or_create_collection(COLLECTIONS["incidents"])
    existing   = collection.count()

    if existing == 0:
        print(f"\n[Incidents] Loading {len(HISTORICAL_INCIDENTS)} historical incidents...")
        collection.add(
            documents=[inc["content"] for inc in HISTORICAL_INCIDENTS],
            metadatas=[{
                "id":       inc["id"],
                "title":    inc["title"],
                "date":     inc["date"],
                "corridor": inc["corridor"],
                "type":     inc["type"],
                "severity": inc["severity"],
                "impact":   inc["impact"],
            } for inc in HISTORICAL_INCIDENTS],
            ids=[inc["id"] for inc in HISTORICAL_INCIDENTS],
        )
        print(f"  ✓ Loaded {len(HISTORICAL_INCIDENTS)} incidents")
    else:
        print(f"  ✓ Incidents already loaded ({existing} records)")

    # Load regulatory docs
    reg_collection = get_or_create_collection(COLLECTIONS["regulations"])
    existing_regs  = reg_collection.count()

    if existing_regs == 0:
        print(f"\n[Regulations] Loading {len(REGULATORY_DOCS)} documents...")
        reg_collection.add(
            documents=[doc["content"] for doc in REGULATORY_DOCS],
            metadatas=[{"id": doc["id"], "title": doc["title"]}
                       for doc in REGULATORY_DOCS],
            ids=[doc["id"] for doc in REGULATORY_DOCS],
        )
        print(f"  ✓ Loaded {len(REGULATORY_DOCS)} regulatory documents")
    else:
        print(f"  ✓ Regulations already loaded ({existing_regs} records)")

    print(f"\n  Knowledge base ready at: {CHROMA_PATH}")

def query_similar_incidents(query_text, n_results=3, corridor=None):
    """Find historical incidents similar to current situation."""
    collection = get_or_create_collection(COLLECTIONS["incidents"])

    where = {"corridor": corridor} if corridor else None
    try:
        results = collection.query(
            query_texts=[query_text],
            n_results=min(n_results, collection.count()),
            where=where,
        )
        incidents = []
        for i in range(len(results["ids"][0])):
            incidents.append({
                "id":       results["ids"][0][i],
                "content":  results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i],
            })
        return incidents
    except Exception as e:
        print(f"  [RAG] Query error: {e}")
        return []

def query_regulations(query_text, n_results=2):
    """Find relevant regulatory guidance for a situation."""
    collection = get_or_create_collection(COLLECTIONS["regulations"])
    try:
        results = collection.query(
            query_texts=[query_text],
            n_results=min(n_results, collection.count()),
        )
        docs = []
        for i in range(len(results["ids"][0])):
            docs.append({
                "id":       results["ids"][0][i],
                "content":  results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
            })
        return docs
    except Exception as e:
        print(f"  [RAG] Regulation query error: {e}")
        return []

def add_new_incident(incident_data):
    """Add a new incident to the knowledge base in real time."""
    collection = get_or_create_collection(COLLECTIONS["incidents"])
    new_id     = f"INC{collection.count() + 1:03d}"
    collection.add(
        documents=[incident_data["content"]],
        metadatas=[{
            "id":       new_id,
            "title":    incident_data.get("title", ""),
            "date":     datetime.now().strftime("%Y-%m-%d"),
            "corridor": incident_data.get("corridor", "none"),
            "type":     incident_data.get("type", "unknown"),
            "severity": incident_data.get("severity", 5),
            "impact":   incident_data.get("impact", ""),
        }],
        ids=[new_id],
    )
    print(f"  ✓ Added new incident {new_id} to knowledge base")
    return new_id

if __name__ == "__main__":
    # Populate the knowledge base
    populate_knowledge_base()

    # Test Query 1 — find similar incidents to current Hormuz situation
    print(f"\n{'='*50}")
    print("TEST QUERY 1 — Hormuz threat similar incidents")
    print(f"{'='*50}")
    results = query_similar_incidents(
        "Iran threatening to close Strait of Hormuz, tankers diverted",
        n_results=2
    )
    for r in results:
        print(f"\n  Match: {r['metadata']['title']}")
        print(f"  Date : {r['metadata']['date']}")
        print(f"  Type : {r['metadata']['type']}")
        print(f"  Impact: {r['metadata']['impact']}")

    # Test Query 2 — find regulations for emergency procurement
    print(f"\n{'='*50}")
    print("TEST QUERY 2 — Emergency procurement regulations")
    print(f"{'='*50}")
    regs = query_regulations("emergency procurement during supply disruption")
    for r in regs:
        print(f"\n  Regulation: {r['metadata']['title']}")
        print(f"  Preview   : {r['content'][:120]}...")

    print(f"\n✓ RAG knowledge base working correctly")