import requests
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# EIA API - completely free, just needs registration at eia.gov/opendata
# We also use a free fallback that needs no key at all
EIA_API_KEY = os.getenv("EIA_API_KEY", "")

# Commodity definitions with their EIA series IDs
COMMODITIES = {
    "brent_crude": {
        "name":        "Brent Crude Oil",
        "unit":        "USD/barrel",
        "eia_series":  "PET.RBRTE.D",
        "description": "Global benchmark — what India pays for imports",
        "threshold_high":  90.0,
        "threshold_crisis": 110.0,
    },
    "wti_crude": {
        "name":        "WTI Crude Oil",
        "unit":        "USD/barrel",
        "eia_series":  "PET.RCLC1.D",
        "description": "US benchmark — tracks Brent closely",
        "threshold_high":  85.0,
        "threshold_crisis": 105.0,
    },
    "natural_gas": {
        "name":        "Natural Gas (Henry Hub)",
        "unit":        "USD/MMBtu",
        "eia_series":  "NG.RNGWHHD.D",
        "description": "LNG price indicator",
        "threshold_high":  4.0,
        "threshold_crisis": 8.0,
    },
}

def fetch_from_eia(series_id):
    """Fetch price data from EIA API if key is available."""
    if not EIA_API_KEY:
        return None
    try:
        url = f"https://api.eia.gov/v2/seriesid/{series_id}"
        params = {"api_key": EIA_API_KEY, "length": 5}
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        series = data.get("response", {}).get("data", [])
        if series:
            latest = series[0]
            return {
                "price": float(latest.get("value", 0)),
                "date":  latest.get("period", ""),
            }
    except Exception as e:
        print(f"  [EIA] Error fetching {series_id}: {e}")
    return None

def fetch_from_open_api(commodity_key):
    """
    Free fallback using open commodity price APIs.
    No API key needed.
    """
    try:
        # Using commodities-api.com free public endpoint
        commodity_map = {
            "brent_crude": "BRNT",
            "wti_crude":   "CRUDEOIL",
            "natural_gas": "NG",
        }
        symbol = commodity_map.get(commodity_key)
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}=F"
        params = {"interval": "1d", "range": "5d"}
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, params=params, headers=headers, timeout=10)
        data = response.json()
        price = data["chart"]["result"][0]["meta"]["regularMarketPrice"]
        return {
            "price": round(float(price), 2),
            "date":  datetime.now().strftime("%Y-%m-%d"),
        }
    except Exception:
        return None

def get_simulated_price(commodity_key):
    """
    Realistic simulated prices as final fallback.
    Based on June 2026 approximate market values.
    """
    simulated = {
        "brent_crude":  {"price": 74.85, "date": datetime.now().strftime("%Y-%m-%d")},
        "wti_crude":    {"price": 71.20, "date": datetime.now().strftime("%Y-%m-%d")},
        "natural_gas":  {"price": 2.95,  "date": datetime.now().strftime("%Y-%m-%d")},
    }
    return simulated.get(commodity_key)

def assess_price_risk(commodity_key, price):
    """Turn a price into a risk signal."""
    thresholds = COMMODITIES[commodity_key]
    high     = thresholds["threshold_high"]
    crisis   = thresholds["threshold_crisis"]

    if price >= crisis:
        return {"level": "CRITICAL", "score": 90, "action": "Trigger emergency procurement"}
    elif price >= high:
        return {"level": "HIGH",     "score": 65, "action": "Activate alternative sourcing"}
    elif price >= high * 0.85:
        return {"level": "MEDIUM",   "score": 35, "action": "Monitor closely"}
    else:
        return {"level": "LOW",      "score": 10, "action": "Normal operations"}

def fetch_all_commodities():
    print(f"\n{'='*50}")
    print(f"Commodity Prices at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}")

    results = {}

    for key, meta in COMMODITIES.items():
        print(f"\n[{meta['name'].upper()}]")

        # Try EIA first, then Yahoo Finance, then simulation
        price_data = fetch_from_eia(meta["eia_series"])
        source = "EIA API"

        if not price_data:
            price_data = fetch_from_open_api(key)
            source = "Yahoo Finance"

        if not price_data:
            price_data = get_simulated_price(key)
            source = "Simulated (realistic)"

        price  = price_data["price"]
        risk   = assess_price_risk(key, price)

        results[key] = {
            "name":        meta["name"],
            "price":       price,
            "unit":        meta["unit"],
            "date":        price_data["date"],
            "source":      source,
            "description": meta["description"],
            "risk":        risk,
        }

        print(f"  Price  : {price} {meta['unit']}")
        print(f"  Source : {source}")
        print(f"  Risk   : {risk['level']} (score: {risk['score']}/100)")
        print(f"  Action : {risk['action']}")

    return results

def get_price_spike_alert(commodity_data):
    """Check if any commodity has spiked into HIGH or CRITICAL territory."""
    alerts = []
    for key, data in commodity_data.items():
        if data["risk"]["level"] in ["HIGH", "CRITICAL"]:
            alerts.append({
                "commodity": data["name"],
                "price":     data["price"],
                "unit":      data["unit"],
                "level":     data["risk"]["level"],
                "action":    data["risk"]["action"],
            })
    return alerts

if __name__ == "__main__":
    commodity_data = fetch_all_commodities()

    alerts = get_price_spike_alert(commodity_data)
    print(f"\n{'='*50}")
    if alerts:
        print(f"⚠ PRICE ALERTS ({len(alerts)} active)")
        print(f"{'='*50}")
        for alert in alerts:
            print(f"  {alert['commodity']}: {alert['price']} {alert['unit']} — {alert['level']}")
            print(f"  Action: {alert['action']}")
    else:
        print("✓ No price alerts — all commodities within normal range")
    print(f"{'='*50}")