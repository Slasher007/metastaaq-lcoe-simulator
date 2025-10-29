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
    "pci_ch4_kwh_per_kg": 13.9
}

# Parameter ranges
PARAM_RANGES = {
    "electrolyser_power": {"min": 1.0, "max": 20.0, "step": 0.5},
    "electrolyser_specific_consumption": {"min": 4.0, "max": 6.0, "step": 0.1},
    "service_ratio": {"min": 0.0, "max": 1.0, "step": 0.01},
    "pv_price": {"min": 0.0, "max": 100.0, "step": 5.0},
    "ppa_price": {"min": 40.0, "max": 120.0, "step": 5.0},
    "target_price": {"min": 20.0, "max": 100.0, "step": 5.0},
    "pv_project_years": {"min": 15, "max": 30, "step": 1},
    "pv_surface_hectares": {"min": 0.1, "max": 10.0, "step": 0.1},
    "power_density_mwp_per_ha": {"min": 0.5, "max": 3.0, "step": 0.1},
    "storage_hours": {"min": 0.0, "max": 12.0, "step": 0.5},
    "pv_cost_per_wp": {"min": 0.3, "max": 2.0, "step": 0.05},
    "battery_cost_per_kwh": {"min": 100.0, "max": 500.0, "step": 10.0},
    "opex_percentage": {"min": 0.5, "max": 5.0, "step": 0.1},
    "discount_rate": {"min": 2.0, "max": 12.0, "step": 0.5},
    "pci_ch4_kwh_per_kg": {"min": 10.0, "max": 20.0, "step": 0.1}
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
