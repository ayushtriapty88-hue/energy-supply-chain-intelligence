# ⚡ Energy Supply Chain Intelligence

**AI-Driven Energy Supply Chain Resilience for Import-Dependent Economies**

A real-time intelligence platform that monitors India's crude-oil supply chain, detects geopolitical threats before they become crises, models disruption scenarios and their economic impact, and generates executable procurement rerouting recommendations — turning a reactive crisis response into a managed, anticipatory process.

Runs **fully local** on free open-source AI (Ollama + Llama 3.2). No paid API keys are required to run the system.

---

## 60-Second Evaluation Path (for judges)

If you have two minutes, do exactly this:

1. Open the dashboard at **http://localhost:3000**
2. On the landing screen, click **"Take the guided tour"** — a 17-step walkthrough explains every panel automatically.
3. Go to the **Scenario** tab → click **"Hormuz Full Closure"**. Wait ~2–4 minutes (local AI inference).
4. Watch the whole dashboard recompute: supply gap **2,059 kbd**, Brent **→ $101**, refinery utilisation **85% → 44%**, a ranked procurement plan, and an SPR drawdown schedule — all generated from one click.
5. Open the **Map** tab and click any dot (corridor, supplier, or India) to inspect its live data and static facts.

That path demonstrates the full signal → score → simulate → reroute → advise pipeline.

---

## What It Does — the Five Agents

The brief's five suggested systems are all implemented and chained end-to-end:

| # | Agent | What it does | File |
|---|-------|--------------|------|
| 1 | **Geopolitical Risk Intelligence** | Ingests news, AIS vessel data, sanctions and commodity prices → a live 0–100 risk score per corridor and supplier, grounded in RAG historical precedent. | `geopolitical_agent.py` |
| 2 | **Disruption Scenario Modeller** | Simulates 5 events (Hormuz full/partial closure, OPEC+ cut, Red Sea shutdown, Russia embargo) → cascading impacts on refinery run rates, fuel prices, and GDP. | `scenario_modeller.py` |
| 3 | **Adaptive Procurement Orchestrator** | Ranks alternative crude suppliers by spot price, delivery time, sanctions risk, and refinery-grade compatibility → an actionable procurement plan. | `procurement_orchestrator.py` |
| 4 | **Strategic Reserve Optimisation** | Models phased SPR drawdown against the supply gap → exhaustion day, days covered, and replenishment window. | `spr_agent.py` |
| 5 | **Supply Chain Digital Twin** | Fuses every agent's output into one unified, geospatial, persistent state object driving the dashboard. | `digital_twin.py` |

---

## Architecture

Three layers, orchestrated top to bottom (see `architecture_diagram.svg` / `.png`):

- **Data Ingestion** — `news_fetcher`, `ais_fetcher`, `commodity_fetcher`, `sanctions_fetcher`, unified by `scheduler.py` into `latest_snapshot.json`.
- **Knowledge Base** — `rag_store.py` (ChromaDB + LangChain, 6 historical incidents + 3 regulatory docs) and `llm_client.py` (Ollama local + Claude fallback, JSON mode).
- **AI Agents** — the five agents above, chained, feeding the **Digital Twin**.
- **API & Frontend** — `main.py` (FastAPI, port 8000) serves the twin to a **React** dashboard (port 3000) with 7 tabs, a real-world geospatial map, and a guided tour.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| AI (local) | Ollama + Llama 3.2, Claude API fallback |
| RAG memory | ChromaDB + LangChain |
| Backend | FastAPI + Python |
| Frontend | React + Recharts + react-simple-maps |
| News data | NewsAPI + RSS + GDELT |
| Price data | Yahoo Finance |
| Shipping data | Simulated AIS (realistic; upgradeable to live feed) |
| Sanctions | Curated database + refinery-grade compatibility |

---

## Setup & Run

### Prerequisites
- **Python 3.11+**
- **Node.js 18+** (for the React frontend)
- **Ollama** installed and running, with a model pulled:
  ```bash
  ollama pull llama3.2
  ```
  Confirm it is running: `ollama ps` should list the model, or `curl http://localhost:11434` should return "Ollama is running".

### 1. Backend dependencies
```bash
cd energy-resilience
python -m venv venv
venv\Scripts\activate            # Windows
# source venv/bin/activate       # macOS / Linux
pip install -r requirements.txt
```

If there is no `requirements.txt`, install the core packages:
```bash
pip install feedparser chromadb langchain fastapi uvicorn yfinance requests python-dotenv
```

### 2. Frontend dependencies
```bash
cd frontend
npm install
npm install react-simple-maps --legacy-peer-deps
cd ..
```

### 3. Run everything (one command)
```bash
python run_all.py
```
This runs the full data pipeline, starts the FastAPI backend (port 8000), and launches the React frontend (port 3000).

To skip the (slow) pipeline and boot straight to the dashboard using existing data:
```bash
python run_all.py --no-pipeline
```

### 4. Open
- **Dashboard:** http://localhost:3000
- **API:** http://localhost:8000

---

## Dashboard Tabs

| Tab | Shows |
|-----|-------|
| **Overview** | Master risk score, corridor risk chart, commodity prices, watch list, live news |
| **News** | Full monitored news feed + active sanctions |
| **Corridors** | Per-chokepoint deep-dive: vessels, AI threat, recommended action |
| **Scenario** | Trigger any of 5 disruptions; see instant economic impact + response plan |
| **Map** | Real-world geospatial map; click any point for its full profile |
| **Procurement** | Ranked suppliers + adaptive procurement plan with gap coverage & cost |
| **SPR** | Day-by-day strategic-reserve drawdown timeline + policy recommendation |

---

## Scenario Assumptions (explicit & testable)

Per the brief's evaluation focus, all scenario assumptions are explicit and live in code, not hidden:

- **India baseline** (`scenario_modeller.py` → `INDIA_BASELINE`): 5,200 kbd consumption, 88% import dependency, 45% Hormuz dependency, 9.5-day SPR, ~$74.85 baseline Brent, $3.9T GDP.
- **Per-scenario parameters**: supply-cut %, duration, price-shock %, affected corridor — all defined in the `SCENARIOS` dictionary.
- **Economics** (supply gap, cost/day, GDP exposure, refinery utilisation, SPR coverage) are computed deterministically in Python; the LLM only writes the narrative explanation, never the numbers.

This means every figure the system reports can be traced to a stated assumption and recomputed.

---

## Project Structure

```
energy-resilience/
├── backend/
│   ├── ingestion/       # news, AIS, commodity, sanctions fetchers + scheduler
│   ├── agents/          # 5 AI agents
│   ├── knowledge/       # ChromaDB RAG store
│   ├── data/            # JSON state (snapshot, twin, scenario, etc.)
│   ├── llm_client.py    # Ollama + Claude fallback
│   └── main.py          # FastAPI server
├── frontend/
│   └── src/
│       ├── App.js         # 7-tab dashboard
│       ├── WorldMap.js    # real-world geospatial map
│       ├── LandingScreen.js
│       └── GuidedTour.js  # 17-step walkthrough
├── run_all.py           # one-command startup
└── run_pipeline.py      # data refresh
```

---

## Deliverables

- ✅ **Working Prototype** — this repository
- ✅ **Architecture Diagram** — `architecture_diagram.svg` / `.png`
- ✅ **Presentation Deck** — `Energy_Supply_Chain_Intelligence_Deck.pptx`
- ✅ **Demo Video** — see `DEMO_SCRIPT.md` for the recording walkthrough

---

## Notes for Evaluators

- The first AI call after startup is slow (the model loads into memory). Running one scenario to "warm up" makes subsequent runs faster.
- Shipping data is realistic simulated AIS; the `ais_fetcher` is structured so a live feed (e.g. aisstream.io) can be dropped in without changing anything downstream.
- The system is designed to run offline after setup — no live internet is required once Ollama and the data snapshot are in place.
