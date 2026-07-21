import subprocess
import sys
import os
import time
import threading


def run_pipeline():
    """Run all data pipeline and agents first."""
    print("\n" + "="*50)
    print("STEP 1 — Running data pipeline...")
    print("="*50)

    scripts = [
        "backend/ingestion/scheduler.py",
        "backend/agents/geopolitical_agent.py",
        "backend/agents/scenario_modeller.py",
        "backend/agents/procurement_orchestrator.py",
        "backend/agents/spr_agent.py",
        "backend/agents/digital_twin.py",
    ]

    for script in scripts:
        print(f"\n→ Running {script}...")
        subprocess.run([sys.executable, script])

    print("\n✅ Pipeline complete!")


def run_backend():
    """Start FastAPI backend server."""
    print("\n" + "="*50)
    print("STEP 2 — Starting backend API on port 8000...")
    print("="*50)
    subprocess.run([
        sys.executable, "-m", "uvicorn",
        "backend.main:app",
        "--host", "0.0.0.0",
        "--port", "8000",
        # --reload REMOVED: WatchFiles was watching backend/data/, so every JSON
        # write by an agent could restart the server mid-request.
        # Re-add it only while actively editing code, never during a demo.
    ])


def run_frontend():
    """Start React frontend."""
    print("\n" + "="*50)
    print("STEP 3 — Starting frontend on port 3000...")
    print("="*50)
    subprocess.run(
        "npm start",
        shell=True,
        cwd=os.path.join(os.getcwd(), "frontend")
    )


if __name__ == "__main__":
    # Optional: skip the (slow) pipeline with `python run_all.py --no-pipeline`
    skip_pipeline = "--no-pipeline" in sys.argv

    if skip_pipeline:
        print("\n⏩ Skipping pipeline — serving existing data in backend/data/")
    else:
        run_pipeline()

    print("\n" + "="*50)
    print("Starting servers...")
    print("="*50)

    backend_thread  = threading.Thread(target=run_backend,  daemon=True)
    frontend_thread = threading.Thread(target=run_frontend, daemon=True)

    backend_thread.start()
    time.sleep(3)   # Give backend a moment before the frontend starts polling
    frontend_thread.start()

    print("\n✅ Everything is running!")
    print("   Dashboard → http://localhost:3000")
    print("   API       → http://localhost:8000")
    print("\nPress Ctrl+C to stop everything.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")