"""
Battery Energy Storage System (BESS) Configuration
Parametric time windows and battery parameters for PV-Battery-Electrolyser optimization
"""

# Parametric Time Windows (hours in 24h format)
# Defaults aligned with battery_integration operational windows (non-overlapping)
DEFAULT_TIME_WINDOWS = {
    # 1. PV-priority charging window
    "pv_charge_start": 11,  # 10:00 - Start PV charging
    "pv_charge_end": 16,    # 16:00 - End PV charging
    
    # 2. Evening arbitrage discharge window
    "arbitrage_discharge_start": 17,  # 17:00 - Start selling to grid
    "arbitrage_discharge_end": 22,    # 22:00 - End selling to grid
    
    # 3. Spot charging window (grid charging at spot prices)
    "night_charge_start": 23,  # 23:00 - Start spot grid charging
    "night_charge_end": 5,     # 04:00 - End spot grid charging (wraps midnight)
    
    # 4. Morning electrolyser supply window
    "electrolyser_start": 6,  # 05:00 - Start electrolyser operation
    "electrolyser_end": 10,    # 09:00 - End electrolyser operation
}

# Electrolyser Parameters for Battery Supply
DEFAULT_ELECTROLYSER_PARAMS = {
    "P_ely": 1.0,  # MW - Fixed power consumption when ON
    "specific_consumption": 4.8,  # kWh/kg H2 (typical alkaline: 4.5-5.5, PEM: 4.3-5.0)
    "min_load_ratio": 0.3,  # Minimum load ratio (30% of rated power)
    "startup_energy": 0.0,  # MWh - Energy required for startup (can be 0)
    "priority": "battery_only",  # Options: "battery_only", "battery_first_grid_backup"
}

# Battery Technical Parameters
DEFAULT_BATTERY_PARAMS = {
    # Energy capacity (aligned with battery_integration default UI)
    # Calculated as P_ely * PV charging window duration (6 hours)
    "E_bat_max": DEFAULT_ELECTROLYSER_PARAMS["P_ely"] * (DEFAULT_TIME_WINDOWS["pv_charge_end"] - DEFAULT_TIME_WINDOWS["pv_charge_start"]),
    
    # Power limits (based on electrolyser power)
    "P_charge_max": DEFAULT_ELECTROLYSER_PARAMS["P_ely"],  # MW - Maximum charge power (equals electrolyser power)
    "P_discharge_max": DEFAULT_ELECTROLYSER_PARAMS["P_ely"],  # MW - Maximum discharge power (equals electrolyser power)
    
    # Efficiency (one-way and round-trip)
    # Note: battery_integration recomputes eta_charge/eta_discharge from eta_rt
    "eta_charge": 1.0,  # Charging efficiency (one-way)
    "eta_discharge": 1.0,  # Discharging efficiency (one-way)
    "eta_rt": 1.0,  # Round-trip efficiency (UI default; losses modeled via economics, not physics)
    
    # State of Charge (SoC) constraints
    "SoC_min": 0.10,  # Minimum SoC (10% = 10% DoD protection)
    "SoC_max": 1.00,  # Maximum SoC (100%)
    "SoC_initial": 0.50,  # Initial SoC on Jan 1st 00:00 (50%)
    
    # Depth of Discharge
    "DoD_max": 1.00,  # Maximum allowed depth of discharge (100%)
    
    # Self-discharge
    "self_discharge_rate": 0.0001,  # Per hour (0.01% per hour = 2.4% per day for Li-ion)
}

# Penalty Parameters
# Set all penalties to zero to effectively disable penalty-based costs
PENALTY_PARAMS = {
    "electrolyser_shortage_penalty": 0.0,  # €/MWh - no shortage penalty
    "soc_violation_penalty": 0.0,         # €/MWh - no SoC violation penalty
    "curtailment_cost": 0.0,             # €/MWh - no PV curtailment cost
}

# Parameter Ranges for Sensitivity Analysis
BATTERY_PARAM_RANGES = {
    "E_bat_max": {"min": 5.0, "max": 50.0, "step": 5.0, "unit": "MWh"},
    "P_charge_max": {"min": 2.0, "max": 20.0, "step": 2.0, "unit": "MW"},
    "P_discharge_max": {"min": 2.0, "max": 20.0, "step": 2.0, "unit": "MW"},
    "eta_rt": {"min": 0.85, "max": 0.95, "step": 0.01, "unit": "-"},
    "DoD_max": {"min": 0.80, "max": 1.00, "step": 0.05, "unit": "-"},
}

TIME_WINDOW_RANGES = {
    "pv_charge_start": {"min": 8, "max": 12, "step": 1, "unit": "hour"},
    "pv_charge_end": {"min": 14, "max": 18, "step": 1, "unit": "hour"},
    "arbitrage_discharge_start": {"min": 15, "max": 18, "step": 1, "unit": "hour"},
    "arbitrage_discharge_end": {"min": 22, "max": 24, "step": 1, "unit": "hour"},
    "night_charge_start": {"min": 22, "max": 24, "step": 1, "unit": "hour"},
    "night_charge_end": {"min": 4, "max": 7, "step": 1, "unit": "hour"},
    "electrolyser_start": {"min": 4, "max": 8, "step": 1, "unit": "hour"},
    "electrolyser_end": {"min": 9, "max": 12, "step": 1, "unit": "hour"},
}

ELECTROLYSER_PARAM_RANGES = {
    "P_ely": {"min": 1.0, "max": 15.0, "step": 1.0, "unit": "MW"},
}


def validate_time_windows(time_windows):
    """
    Validate that time windows don't overlap inappropriately
    Returns: (is_valid, error_message)
    """
    tw = time_windows
    
    # Check that windows are properly ordered (with wrapping for overnight)
    # PV charging should be during day
    if tw["pv_charge_start"] >= tw["pv_charge_end"]:
        return False, "PV charge window: start must be before end"
    
    # Arbitrage discharge should start when PV ends or after
    # (allowing some overlap is OK, the optimizer handles priority)
    
    # Spot charging wraps around midnight
    if tw["night_charge_start"] < tw["night_charge_end"]:
        return False, "Spot charge window should wrap around midnight (start > end)"
    
    # Electrolyser should start when spot charge ends
    if tw["electrolyser_start"] >= tw["electrolyser_end"]:
        return False, "Electrolyser window: start must be before end"
    
    # Electrolyser should end when PV charging starts (or before)
    if tw["electrolyser_end"] > tw["pv_charge_start"]:
        return False, "Electrolyser should end before or when PV charging starts"
    
    return True, "Valid"


def get_window_duration(start_hour, end_hour):
    """
    Calculate duration of a time window in hours
    Handles windows that wrap around midnight
    """
    if start_hour <= end_hour:
        return end_hour - start_hour
    else:
        # Wraps around midnight
        return (24 - start_hour) + end_hour


def is_hour_in_window(hour, start_hour, end_hour):
    """
    Check if an hour is within a time window
    Handles windows that wrap around midnight
    
    Args:
        hour: Hour to check (0-23)
        start_hour: Window start hour (0-23)
        end_hour: Window end hour (0-23)
    
    Returns:
        bool: True if hour is in window
    """
    # Use inclusive bounds [start_hour, end_hour] for window membership.
    # For normal windows (e.g., 10:00–16:00) this means hours 10,11,12,13,14,15,16.
    # For wrap-around windows (e.g., 23:00–04:00) this means 23,0,1,2,3,4.
    if start_hour <= end_hour:
        # Normal window
        return start_hour <= hour <= end_hour
    else:
        # Window wraps around midnight
        return hour >= start_hour or hour <= end_hour


def calculate_max_hydrogen_production(battery_params, electrolyser_params, time_windows):
    """
    Calculate theoretical maximum daily hydrogen production
    based on electrolyser window and battery capacity
    
    Returns:
        dict with max_h2_kg_per_day, required_energy_mwh, etc.
    """
    ely_duration = get_window_duration(
        time_windows["electrolyser_start"],
        time_windows["electrolyser_end"]
    )
    
    # Energy required for electrolyser during its window
    required_energy_mwh = electrolyser_params["P_ely"] * ely_duration
    
    # Available battery energy (considering DoD limits)
    available_energy_mwh = battery_params["E_bat_max"] * battery_params["DoD_max"]
    
    # Check if battery can support full electrolyser operation
    can_support_full_operation = available_energy_mwh >= required_energy_mwh
    
    # Hydrogen production (kg/day)
    if can_support_full_operation:
        energy_to_ely_mwh = required_energy_mwh
    else:
        energy_to_ely_mwh = available_energy_mwh
    
    h2_production_kg = (energy_to_ely_mwh * 1000) / electrolyser_params["specific_consumption"]
    
    return {
        "max_h2_kg_per_day": h2_production_kg,
        "required_energy_mwh": required_energy_mwh,
        "available_energy_mwh": available_energy_mwh,
        "can_support_full_operation": can_support_full_operation,
        "electrolyser_duration_hours": ely_duration,
        "capacity_utilization": min(1.0, available_energy_mwh / required_energy_mwh) if required_energy_mwh > 0 else 0
    }
