"""
Configuration constants and settings for the MetaSTAAQ Dashboard
"""

# Page Configuration
PAGE_CONFIG = {
    "page_title": "MetaSTAAQ - LCOE Simulation Dashboard",
    "page_icon": "⚡",
    "layout": "wide",
    "initial_sidebar_state": "expanded"
}

# Default file paths
DEFAULT_DATA_FILE = 'processed_donnees_prix_spot_fr_2021_2025_month_8.csv'
LOGO_FILE = "STAAQ_HD.jpg"

# PV Images
PV_IMAGES = {
    "location": "meaux_maps_location.png",
    "simulation": "meaux_simulation_output.png", 
    "config": "meaux_pv_config.png"
}

# Month names
MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]

# Default parameter values
DEFAULT_PARAMS = {
    "electrolyser_power": 5.0,
    "electrolyser_specific_consumption": 4.8,
    "service_ratio": 0.98,
    "pv_price": 0.0,
    "ppa_price": 80.0,
    "target_price": 30.0,
    "pv_project_years": 20,
    "pv_surface_hectares": 1.0,
    "power_density_mwp_per_ha": 1.0,
    "storage_hours": 4.0,
    "pv_cost_per_wp": 0.8,
    "battery_cost_per_kwh": 200.0,
    "opex_percentage": 2.0,
    "discount_rate": 6.0,
    "pci_ch4_kwh_per_kg": 13.9,
    # Electrolyzer Economics (for LCOH calculation)
    "electrolyzer_capex_total": 7320000.0,
    "electrolyzer_lifetime": 20,
    "electrolyzer_discount_rate": 7.0,
    "electrolyzer_opex_annual": 1317744.0,
    "electrolyzer_maintenance_annual": 51600.0,
    "water_price_per_m3": 5.0,
    "water_consumption_annual_m3": 8180.0,
    "other_costs_annual": 0.0,
    "stack_replacement_years": 9,
    "stack_replacement_cost": 2000000.0
}

# Parameter ranges
PARAM_RANGES = {
    "electrolyser_power": {"min": 0.25, "max": 20.0, "step": 0.25},
    "electrolyser_specific_consumption": {"min": 4.0, "max": 6.0, "step": 0.1},
    "service_ratio": {"min": 0.0, "max": 1.0, "step": 0.01},
    "pv_price": {"min": 0.0, "max": 100.0, "step": 5.0},
    "ppa_price": {"min": 40.0, "max": 120.0, "step": 5.0},
    "target_price": {"min": 20.0, "max": 100.0, "step": 5.0},
    "pv_project_years": {"min": 15, "max": 30, "step": 1},
    "pv_surface_hectares": {"min": 0.1, "max": 20.0, "step": 0.1},
    "power_density_mwp_per_ha": {"min": 0.5, "max": 3.0, "step": 0.1},
    "storage_hours": {"min": 0.0, "max": 12.0, "step": 0.5},
    "pv_cost_per_wp": {"min": 0.3, "max": 2.0, "step": 0.05},
    "battery_cost_per_kwh": {"min": 100.0, "max": 500.0, "step": 10.0},
    "opex_percentage": {"min": 0.5, "max": 5.0, "step": 0.1},
    "discount_rate": {"min": 2.0, "max": 12.0, "step": 0.5},
    "pci_ch4_kwh_per_kg": {"min": 10.0, "max": 20.0, "step": 0.1},
    # Electrolyzer Economics ranges
    "electrolyzer_capex_total": {"min": 1000000.0, "max": 50000000.0, "step": 100000.0},
    "electrolyzer_lifetime": {"min": 5, "max": 30, "step": 1},
    "electrolyzer_discount_rate": {"min": 1.0, "max": 15.0, "step": 0.5},
    "electrolyzer_opex_annual": {"min": 0.0, "max": 10000000.0, "step": 10000.0},
    "electrolyzer_maintenance_annual": {"min": 0.0, "max": 500000.0, "step": 1000.0},
    "water_price_per_m3": {"min": 0.0, "max": 20.0, "step": 0.1},
    "water_consumption_annual_m3": {"min": 0.0, "max": 50000.0, "step": 100.0},
    "other_costs_annual": {"min": 0.0, "max": 100000.0, "step": 1000.0},
    "stack_replacement_years": {"min": 3, "max": 15, "step": 1},
    "stack_replacement_cost": {"min": 0.0, "max": 10000000.0, "step": 50000.0}
}

# CSS Styles
CUSTOM_CSS = """
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 2rem;
        font-weight: bold;
        color: #2e7d32;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
</style>
"""

# Strategy types
STRATEGY_TYPES = ["Service Ratio-Based", "Target Price-Based"]

# Colors for plots
PLOT_COLORS = {
    "spot": "blue",
    "ppa": "green", 
    "pv": "orange",
    "battery": "purple",
    "grid": "red"
}
