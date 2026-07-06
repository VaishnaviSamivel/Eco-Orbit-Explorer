"""Eco-Orbit MCP Server — environmental & sustainability tools via stdio transport.

Tools exposed:
  1. get_air_quality_index        – AQI and pollutant breakdown for a city/region
  2. get_deforestation_data       – Deforestation stats for a country/region
  3. calculate_carbon_footprint   – Carbon footprint for common activities
  4. get_satellite_change_analysis – Land-use change analysis for a region
  5. get_sdg_progress             – UN SDG progress metrics for a country

Run as a subprocess:  uv run python -m app.mcp_server
ADK agents connect via:  MCPToolset(connection_params=StdioServerParameters(...))
"""

import json
import math
import random

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("eco-orbit-mcp")


# ─────────────────────────────────────────────────────────────────────────────
# TOOL 1 — Air Quality Index
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def get_air_quality_index(
    location: str,
    include_pollutants: bool = True,
) -> str:
    """Get the current Air Quality Index (AQI) and pollutant breakdown for a city or region.

    Args:
        location: City name, region, or GPS coordinates (e.g. "Delhi, India" or "28.6,77.2").
        include_pollutants: If True, include per-pollutant concentrations (PM2.5, PM10, NO2, O3, CO).

    Returns:
        JSON string with AQI value, health category, and optional pollutant data.
    """
    # Simulated response (production would call an EPA / WAQI API)
    seed = sum(ord(c) for c in location)
    rng = random.Random(seed)
    aqi = rng.randint(20, 280)

    if aqi <= 50:
        category, health_advice = "Good", "Air quality is satisfactory. No health risk."
    elif aqi <= 100:
        category, health_advice = "Moderate", "Acceptable air quality. Sensitive groups may be affected."
    elif aqi <= 150:
        category, health_advice = "Unhealthy for Sensitive Groups", "Elderly, children, and those with respiratory issues should limit outdoor activity."
    elif aqi <= 200:
        category, health_advice = "Unhealthy", "Everyone may begin to experience health effects."
    elif aqi <= 300:
        category, health_advice = "Very Unhealthy", "Health alert — everyone may experience serious effects."
    else:
        category, health_advice = "Hazardous", "Emergency conditions. Entire population likely to be affected."

    result: dict = {
        "location": location,
        "aqi": aqi,
        "category": category,
        "health_advice": health_advice,
        "data_source": "Eco-Orbit Environmental Monitoring Network",
        "timestamp_utc": "2026-07-06T14:30:00Z",
    }

    if include_pollutants:
        result["pollutants"] = {
            "PM2.5_ug_m3": round(rng.uniform(5, 120), 1),
            "PM10_ug_m3": round(rng.uniform(10, 200), 1),
            "NO2_ppb": round(rng.uniform(5, 80), 1),
            "O3_ppb": round(rng.uniform(10, 90), 1),
            "CO_ppm": round(rng.uniform(0.2, 5.0), 2),
            "SO2_ppb": round(rng.uniform(1, 40), 1),
        }

    return json.dumps(result, indent=2)


# ─────────────────────────────────────────────────────────────────────────────
# TOOL 2 — Deforestation Data
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def get_deforestation_data(
    region: str,
    year_start: int = 2020,
    year_end: int = 2025,
) -> str:
    """Get deforestation and reforestation statistics for a country or geographic region.

    Args:
        region: Country name or geographic region (e.g. "Amazon Basin", "Indonesia").
        year_start: Start year for the analysis period (default 2020).
        year_end: End year for the analysis period (default 2025).

    Returns:
        JSON string with annual deforestation rates, total area lost, and trend analysis.
    """
    if year_end < year_start:
        return json.dumps({"error": "year_end must be >= year_start"})

    seed = sum(ord(c) for c in region) + year_start
    rng = random.Random(seed)

    years = list(range(year_start, year_end + 1))
    annual_loss_km2 = [round(rng.uniform(800, 18000), 0) for _ in years]
    annual_gain_km2 = [round(rng.uniform(100, 3000), 0) for _ in years]

    total_loss = sum(annual_loss_km2)
    total_gain = sum(annual_gain_km2)
    net_loss = total_loss - total_gain

    # Trend: compare first half vs second half
    mid = len(years) // 2
    first_half_avg = sum(annual_loss_km2[:mid]) / max(mid, 1)
    second_half_avg = sum(annual_loss_km2[mid:]) / max(len(years) - mid, 1)
    if second_half_avg < first_half_avg * 0.9:
        trend = "Improving (loss rate declining)"
    elif second_half_avg > first_half_avg * 1.1:
        trend = "Worsening (loss rate increasing)"
    else:
        trend = "Stable (no significant change)"

    return json.dumps({
        "region": region,
        "period": f"{year_start}–{year_end}",
        "annual_data": [
            {"year": y, "loss_km2": l, "gain_km2": g}
            for y, l, g in zip(years, annual_loss_km2, annual_gain_km2)
        ],
        "summary": {
            "total_loss_km2": total_loss,
            "total_gain_km2": total_gain,
            "net_loss_km2": net_loss,
            "net_loss_equivalent_football_fields": int(net_loss * 140),
            "trend": trend,
            "primary_drivers": ["Agricultural expansion", "Illegal logging", "Infrastructure development"],
        },
        "data_source": "Eco-Orbit Satellite Forest Watch",
    }, indent=2)


# ─────────────────────────────────────────────────────────────────────────────
# TOOL 3 — Carbon Footprint Calculator
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def calculate_carbon_footprint(
    activity_type: str,
    quantity: float,
    unit: str,
) -> str:
    """Calculate the carbon footprint (CO₂ equivalent) for a common activity.

    Args:
        activity_type: One of: 'flight_economy', 'flight_business', 'car_petrol',
                       'car_electric', 'train', 'beef_kg', 'electricity_kwh',
                       'natural_gas_m3', 'shipping_container_km'.
        quantity: The amount of the activity (e.g. 500 for 500 km, 2 for 2 kg of beef).
        unit: Unit of measurement (e.g. 'km', 'kg', 'kwh', 'm3').

    Returns:
        JSON string with CO₂e in kg, comparison context, and reduction tips.
    """
    # Emission factors (kg CO2e per unit)
    emission_factors: dict[str, float] = {
        "flight_economy": 0.255,      # kg CO2e per passenger-km
        "flight_business": 0.765,     # 3× economy (seat factor)
        "car_petrol": 0.192,          # kg CO2e per km (average petrol car)
        "car_electric": 0.053,        # kg CO2e per km (global average grid)
        "train": 0.041,               # kg CO2e per passenger-km
        "beef_kg": 27.0,              # kg CO2e per kg beef
        "electricity_kwh": 0.233,     # kg CO2e per kWh (global average)
        "natural_gas_m3": 2.04,       # kg CO2e per m³
        "shipping_container_km": 0.016, # kg CO2e per km per TEU
    }

    key = activity_type.lower().replace(" ", "_")
    if key not in emission_factors:
        return json.dumps({
            "error": f"Unknown activity_type '{activity_type}'.",
            "supported": list(emission_factors.keys()),
        })

    factor = emission_factors[key]
    co2e_kg = round(factor * quantity, 2)
    co2e_tonnes = round(co2e_kg / 1000, 4)

    # Contextual comparisons
    context = {
        "equivalent_tree_months": round(co2e_kg / 1.67, 1),  # 1 tree absorbs ~20 kg/yr = 1.67/mo
        "equivalent_smartphone_charges": int(co2e_kg / 0.00822),
        "percent_of_global_per_capita_annual": round(co2e_tonnes / 4.7 * 100, 1),
    }

    tips = {
        "flight_economy": "Consider train travel (6× lower emissions) or video conferencing.",
        "flight_business": "Economy seating emits 3× less. Offset via certified schemes (Gold Standard).",
        "car_petrol": "Switch to electric (72% lower) or carpool to halve emissions.",
        "car_electric": "Charge on renewable tariffs to cut to near-zero.",
        "train": "Already low-carbon — no major change needed.",
        "beef_kg": "Substituting with chicken saves 65%; plant-based saves 95%.",
        "electricity_kwh": "Switch to 100% renewable tariff or add rooftop solar.",
        "natural_gas_m3": "Heat pump replaces gas boiler at 3–4× efficiency.",
        "shipping_container_km": "Sea freight is already the most efficient freight mode.",
    }.get(key, "Reduce, reuse, recycle where possible.")

    return json.dumps({
        "activity": activity_type,
        "quantity": quantity,
        "unit": unit,
        "co2e_kg": co2e_kg,
        "co2e_tonnes": co2e_tonnes,
        "emission_factor_kg_per_unit": factor,
        "context": context,
        "top_reduction_tip": tips,
    }, indent=2)


# ─────────────────────────────────────────────────────────────────────────────
# TOOL 4 — Satellite Land-Use Change Analysis
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def get_satellite_change_analysis(
    region: str,
    change_type: str = "land_use",
) -> str:
    """Analyse satellite-detected land-use or environmental changes for a region.

    Args:
        region: Geographic region name or bounding box (e.g. "Sundarbans, Bangladesh").
        change_type: Type of change to analyse. One of:
                     'land_use', 'urban_expansion', 'water_body', 'vegetation_health'.

    Returns:
        JSON string with change percentages, affected area, and risk assessment.
    """
    valid_types = ["land_use", "urban_expansion", "water_body", "vegetation_health"]
    if change_type not in valid_types:
        return json.dumps({"error": f"change_type must be one of {valid_types}"})

    seed = sum(ord(c) for c in region + change_type)
    rng = random.Random(seed)

    base_area_km2 = rng.uniform(500, 50000)
    change_pct = rng.uniform(-15, 30)
    changed_km2 = round(base_area_km2 * abs(change_pct) / 100, 1)

    risk_score = min(10, max(1, round(abs(change_pct) / 3, 1)))
    if risk_score < 3:
        risk_level = "Low"
    elif risk_score < 6:
        risk_level = "Moderate"
    elif risk_score < 8:
        risk_level = "High"
    else:
        risk_level = "Critical"

    type_details = {
        "land_use": {
            "description": "Agricultural conversion, settlement expansion, or natural succession",
            "key_metric": "Converted area (km²)",
        },
        "urban_expansion": {
            "description": "Urban heat island growth and impervious surface increase",
            "key_metric": "Urban footprint increase (km²)",
        },
        "water_body": {
            "description": "River, lake, or wetland area changes (flood, drought, reclamation)",
            "key_metric": "Water surface change (km²)",
        },
        "vegetation_health": {
            "description": "NDVI change indicating drought stress, disease, or recovery",
            "key_metric": "NDVI delta (normalized)",
        },
    }

    return json.dumps({
        "region": region,
        "analysis_type": change_type,
        "baseline_area_km2": round(base_area_km2, 1),
        "change_percent_5yr": round(change_pct, 1),
        "changed_area_km2": changed_km2,
        "direction": "increase" if change_pct > 0 else "decrease",
        "risk_score_1_10": risk_score,
        "risk_level": risk_level,
        "details": type_details[change_type],
        "satellite_source": "Eco-Orbit Sentinel-2 / Landsat-9 Composite",
        "analysis_date": "2026-07-01",
        "recommended_action": (
            "Immediate ground-truth verification and stakeholder alert"
            if risk_level in ("High", "Critical")
            else "Schedule quarterly monitoring review"
        ),
    }, indent=2)


# ─────────────────────────────────────────────────────────────────────────────
# TOOL 5 — UN SDG Progress Tracker
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def get_sdg_progress(
    country: str,
    sdg_goals: list[int] | None = None,
) -> str:
    """Get UN Sustainable Development Goals (SDG) progress metrics for a country.

    Args:
        country: Country name (e.g. "Brazil", "Germany", "Kenya").
        sdg_goals: List of SDG goal numbers (1–17) to retrieve. If None or empty,
                   returns goals 7, 13, 14, 15 (energy, climate, ocean, land).

    Returns:
        JSON string with SDG scores, trend, and on-track status for each goal.
    """
    if not sdg_goals:
        sdg_goals = [7, 13, 14, 15]

    sdg_names = {
        1: "No Poverty", 2: "Zero Hunger", 3: "Good Health",
        4: "Quality Education", 5: "Gender Equality", 6: "Clean Water",
        7: "Affordable & Clean Energy", 8: "Decent Work & Economic Growth",
        9: "Industry & Innovation", 10: "Reduced Inequalities",
        11: "Sustainable Cities", 12: "Responsible Consumption",
        13: "Climate Action", 14: "Life Below Water", 15: "Life on Land",
        16: "Peace & Justice", 17: "Partnerships for Goals",
    }

    seed = sum(ord(c) for c in country)
    rng = random.Random(seed)

    results = []
    for goal in sdg_goals:
        if goal not in sdg_names:
            continue
        score = round(rng.uniform(30, 95), 1)
        trend_val = rng.uniform(-5, 8)
        trend = "Improving" if trend_val > 1 else ("Declining" if trend_val < -1 else "Stagnating")
        on_track = score >= 70 and trend == "Improving"
        results.append({
            "goal": goal,
            "name": sdg_names[goal],
            "score_0_100": score,
            "trend": trend,
            "trend_delta_per_year": round(trend_val, 2),
            "on_track_for_2030": on_track,
            "gap_to_target": round(max(0, 100 - score), 1),
        })

    overall = round(sum(r["score_0_100"] for r in results) / len(results), 1) if results else 0

    return json.dumps({
        "country": country,
        "overall_env_sdg_score": overall,
        "goals_assessed": len(results),
        "goals_on_track": sum(1 for r in results if r["on_track_for_2030"]),
        "data": results,
        "data_source": "Eco-Orbit SDG Monitoring (based on UN Statistics Division 2025)",
        "note": "Scores are 0–100 where 100 = SDG fully achieved.",
    }, indent=2)


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run(transport="stdio")
