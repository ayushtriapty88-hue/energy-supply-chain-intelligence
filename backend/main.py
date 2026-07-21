import json
import os
import subprocess
import sys
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Energy Supply Chain Intelligence API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = "backend/data"

VALID_SCENARIOS = [
    "hormuz_closure",
    "hormuz_partial",
    "red_sea_closure",
    "opec_emergency_cut",
    "russia_sanctions",
]

# Agents that must re-run AFTER a new scenario is chosen,
# because they all read scenario_analysis.json
DOWNSTREAM_AGENTS = [
    "backend/agents/procurement_orchestrator.py",
    "backend/agents/spr_agent.py",
    "backend/agents/digital_twin.py",
]

# Full refresh chain (geopolitical first, then scenario, then downstream)
FULL_AGENT_CHAIN = [
    "backend/agents/geopolitical_agent.py",
    "backend/agents/scenario_modeller.py",
] + DOWNSTREAM_AGENTS


def load(filename):
    path = os.path.join(DATA_DIR, filename)
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return {"error": f"{filename} not found — run pipeline first"}
    except json.JSONDecodeError:
        return {"error": f"{filename} is being written — retry in a moment"}


def run_script(script, *args):
    """Run an agent script and block until it finishes."""
    cmd = [sys.executable, script, *args]
    result = subprocess.run(cmd, cwd=os.getcwd())
    if result.returncode != 0:
        raise RuntimeError(f"{script} exited with code {result.returncode}")


@app.get("/")
def root():
    return {"status": "Energy Supply Chain Intelligence API running"}


@app.get("/api/twin")
def get_digital_twin():
    return load("digital_twin.json")


@app.get("/api/snapshot")
def get_snapshot():
    return load("latest_snapshot.json")


@app.get("/api/geopolitical")
def get_geopolitical():
    return load("geopolitical_analysis.json")


@app.get("/api/scenario")
def get_scenario():
    return load("scenario_analysis.json")


@app.get("/api/procurement")
def get_procurement():
    return load("procurement_recommendations.json")


@app.get("/api/spr")
def get_spr():
    return load("spr_recommendation.json")


@app.get("/api/active-scenario")
def get_active_scenario():
    """Which scenario is currently driving the dashboard."""
    return load("active_scenario.json")


@app.get("/api/scenarios")
def list_scenarios():
    """List selectable scenarios for the frontend."""
    return {"scenarios": VALID_SCENARIOS}


@app.post("/api/run-pipeline")
def run_pipeline():
    """Trigger full data ingestion refresh (news, AIS, prices, sanctions)."""
    try:
        run_script("backend/ingestion/scheduler.py")
        return {
            "status": "complete",
            "finished_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/run-scenario/{scenario_key}")
def run_scenario(scenario_key: str):
    """
    Run a specific scenario AND rebuild every agent that depends on it.
    This is blocking — it returns only when the dashboard data is fully updated.
    The frontend must NOT call /api/run-agents after this.
    """
    if scenario_key not in VALID_SCENARIOS:
        return {"error": f"Invalid scenario. Choose from: {VALID_SCENARIOS}"}

    try:
        # 1. Run the chosen scenario. The modeller persists the choice
        #    to active_scenario.json so later runs don't reset it.
        run_script("backend/agents/scenario_modeller.py", scenario_key)

        # 2. Rebuild procurement, SPR and digital twin from the NEW scenario.
        for script in DOWNSTREAM_AGENTS:
            run_script(script)

        return {
            "status": "complete",
            "scenario_key": scenario_key,
            "finished_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/run-agents")
def run_agents():
    """
    Refresh all agents. The scenario modeller will re-use whatever scenario
    the user last selected (from active_scenario.json), so this no longer
    silently resets the dashboard back to hormuz_partial.
    """
    try:
        for script in FULL_AGENT_CHAIN:
            run_script(script)
        return {
            "status": "complete",
            "finished_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    except Exception as e:
        return {"error": str(e)}