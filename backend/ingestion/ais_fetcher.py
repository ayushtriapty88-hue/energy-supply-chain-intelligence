import requests
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# Key oil shipping corridors with their geographic bounding boxes
# Format: [min_lat, max_lat, min_lon, max_lon]
CORRIDORS = {
    "strait_of_hormuz": {
        "bbox": [25.0, 27.0, 56.0, 60.0],
        "description": "Strait of Hormuz — 40% of global LNG passes here",
        "risk_weight": 0.45,
    },
    "red_sea": {
        "bbox": [12.0, 30.0, 32.0, 44.0],
        "description": "Red Sea — Houthi attack zone",
        "risk_weight": 0.30,
    },
    "suez_canal": {
        "bbox": [29.5, 31.5, 32.0, 33.0],
        "description": "Suez Canal — Europe-Asia shortcut",
        "risk_weight": 0.15,
    },
    "cape_of_good_hope": {
        "bbox": [-35.0, -25.0, 15.0, 25.0],
        "description": "Cape of Good Hope — alternative route",
        "risk_weight": 0.10,
    },
}

# Simulated vessel data per corridor
# In production replace with MarineTraffic API or AISHub
SIMULATED_VESSELS = {
    "strait_of_hormuz": [
        {"mmsi": "477123456", "name": "GULF CARRIER",    "type": "Tanker", "speed": 12.3, "status": "underway"},
        {"mmsi": "477234567", "name": "HORMUZ STAR",     "type": "Tanker", "speed": 0.0,  "status": "anchored"},
        {"mmsi": "477345678", "name": "PERSIAN EAGLE",   "type": "Tanker", "speed": 11.8, "status": "underway"},
        {"mmsi": "477456789", "name": "ARABIAN KNIGHT",  "type": "Tanker", "speed": 9.2,  "status": "underway"},
        {"mmsi": "477567890", "name": "IRAN EXPRESS",    "type": "Tanker", "speed": 0.0,  "status": "stopped"},
    ],
    "red_sea": [
        {"mmsi": "566111111", "name": "RED SEA PEARL",   "type": "Tanker", "speed": 8.1,  "status": "underway"},
        {"mmsi": "566222222", "name": "ADEN SPIRIT",     "type": "Tanker", "speed": 0.0,  "status": "diverted"},
        {"mmsi": "566333333", "name": "BIMCO STAR",      "type": "Tanker", "speed": 14.2, "status": "underway"},
    ],
    "suez_canal": [
        {"mmsi": "622111111", "name": "SUEZ NAVIGATOR",  "type": "Tanker", "speed": 7.5,  "status": "underway"},
        {"mmsi": "622222222", "name": "CAIRO TRADER",    "type": "Tanker", "speed": 6.9,  "status": "underway"},
    ],
    "cape_of_good_hope": [
        {"mmsi": "655111111", "name": "CAPE PIONEER",    "type": "Tanker", "speed": 15.1, "status": "underway"},
        {"mmsi": "655222222", "name": "SOUTHERN CROSS",  "type": "Tanker", "speed": 14.8, "status": "underway"},
        {"mmsi": "655333333", "name": "INDIAN BREEZE",   "type": "Tanker", "speed": 13.9, "status": "underway"},
        {"mmsi": "655444444", "name": "AFRICA ROUTE",    "type": "Tanker", "speed": 12.5, "status": "underway"},
    ],
}

def get_corridor_status(corridor_name):
    vessels = SIMULATED_VESSELS.get(corridor_name, [])
    total = len(vessels)
    moving = sum(1 for v in vessels if v["status"] == "underway")
    stopped = sum(1 for v in vessels if v["status"] in ["stopped", "diverted", "anchored"])
    avg_speed = sum(v["speed"] for v in vessels) / total if total > 0 else 0

    # Risk score: more stopped/diverted = higher risk
    congestion_ratio = stopped / total if total > 0 else 0
    risk_score = round(congestion_ratio * 100, 1)

    return {
        "corridor":         corridor_name,
        "description":      CORRIDORS[corridor_name]["description"],
        "total_vessels":    total,
        "vessels_moving":   moving,
        "vessels_stopped":  stopped,
        "avg_speed_knots":  round(avg_speed, 1),
        "congestion_ratio": round(congestion_ratio, 2),
        "risk_score":       risk_score,
        "risk_weight":      CORRIDORS[corridor_name]["risk_weight"],
        "vessels":          vessels,
        "timestamp":        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

def fetch_all_corridors():
    print(f"\n{'='*50}")
    print(f"AIS Vessel Tracking at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}")

    results = {}
    for corridor_name in CORRIDORS:
        status = get_corridor_status(corridor_name)
        results[corridor_name] = status

        print(f"\n[{corridor_name.upper().replace('_',' ')}]")
        print(f"  Vessels tracked : {status['total_vessels']}")
        print(f"  Moving          : {status['vessels_moving']}")
        print(f"  Stopped/Diverted: {status['vessels_stopped']}")
        print(f"  Avg speed       : {status['avg_speed_knots']} knots")
        print(f"  Risk score      : {status['risk_score']}/100")

    return results

def get_overall_supply_risk(corridor_data):
    weighted_risk = 0
    for name, data in corridor_data.items():
        weight = CORRIDORS[name]["risk_weight"]
        weighted_risk += data["risk_score"] * weight

    level = "LOW"
    if weighted_risk > 60:
        level = "CRITICAL"
    elif weighted_risk > 40:
        level = "HIGH"
    elif weighted_risk > 20:
        level = "MEDIUM"

    return {
        "overall_risk_score": round(weighted_risk, 1),
        "risk_level":         level,
        "timestamp":          datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

if __name__ == "__main__":
    corridor_data = fetch_all_corridors()
    overall = get_overall_supply_risk(corridor_data)

    print(f"\n{'='*50}")
    print(f"OVERALL SUPPLY CHAIN RISK")
    print(f"{'='*50}")
    print(f"  Score : {overall['overall_risk_score']}/100")
    print(f"  Level : {overall['risk_level']}")