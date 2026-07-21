import subprocess
import sys

SCRIPTS = [
    "backend/ingestion/scheduler.py",
    "backend/agents/geopolitical_agent.py",
    "backend/agents/scenario_modeller.py",
    "backend/agents/procurement_orchestrator.py",
    "backend/agents/spr_agent.py",
    "backend/agents/digital_twin.py",
]

print("Running full pipeline...")
for script in SCRIPTS:
    print(f"\n→ {script}")
    subprocess.run([sys.executable, script])

print("\n✅ Pipeline complete — refresh your dashboard!")