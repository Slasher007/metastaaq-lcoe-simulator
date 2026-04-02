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

import os
import glob
import re

def get_latest_data_file():
    """Find the most recent processed data file"""
    files = glob.glob('processed_donnees_prix_spot_*.csv')
    if not files:
        return 'processed_donnees_prix_spot_FR_2021_2025_month_12.csv' # Fallback
    
    # Sort by modification time to find the newest one
    files.sort(key=os.path.getmtime, reverse=True)
    return files[0]

# Default file paths
DEFAULT_DATA_FILE = 'processed_donnees_prix_spot_FR_2021_2025_month_12.csv'
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
    "h2_flowrate": 1042.0,  # Nm³/h - now an input parameter
    "electrolyser_specific_consumption": 4.8,  # kWh/Nm³ - now calculated from power and h2_flowrate
    "service_ratio": 0.98,
    "pv_price": 60.0,
    "ppa_price": 300.0,
    "target_price": 30.0,
    "pv_project_years": 20,
    "pv_surface_hectares": 1.0,
    "power_density_mwp_per_ha": 1.0,
    "storage_hours": 4.0,
    "pv_cost_per_wp": 1.0,
    "battery_cost_per_kwh": 200.0,
    "opex_percentage": 2.0,
    "discount_rate": 6.0,
    "pci_ch4_kwh_per_kg": 13.9,
    # Methanation parameters
    "ch4_flowrate": 260.0,  # Nm³/h - now an input parameter
    "methanation_cons_spec_ch4": 0.7,  # kWhₑ / Nm³ CH₄ - now calculated from ch4_flowrate
    # Electrolyzer Economics (for LCOH calculation)
    # CapEx Components
    "electrolyser_capex_transformer": 250000.0,
    "electrolyser_capex_electrolyzer": 5000000.0,
    "electrolyser_capex_compressor": 0.0,
    "electrolyser_capex_h2_storage": 50000.0,
    "electrolyser_capex_piping": 20000.0,
    "electrolyser_capex_stack_shift": 2000000.0,
    # Maintenance ratios (% of CapEx per year)
    "electrolyser_maintenance_ratio_transformer": 0.5,
    "electrolyser_maintenance_ratio_electrolyzer": 1.0,
    "electrolyser_maintenance_ratio_compressor": 2.0,
    "electrolyser_maintenance_ratio_h2_storage": 0.5,
    "electrolyser_maintenance_ratio_piping": 0.5,
    # Economics parameters
    "electrolyser_lifetime": 20,
    "electrolyser_discount_rate": 0.0,
    "electrolyser_opex_annual": 2168972.0,
    "electrolyser_maintenance_annual": 51600.0,
    "electrolyser_water_price_per_m3": 5.0,
    "electrolyser_water_consumption_annual_m3": 8180.0,
    "electrolyser_stack_replacement_years": 9,
    "electrolyser_stack_replacement_cost": 2000000.0,
    # Others costs by category
    "electrolyser_others_capex": 0.0,
    "electrolyser_others_opex_annual": 0.0,
    "electrolyser_others_maintenance_annual": 0.0,
    # Site and CO2 Supply Economics (Separate from methanation)
    # CapEx
    "site_capex": 252000.0,
    "appro_co2_capex": 250000.0,
    # OpEx - Annual costs (€/year)
    "site_opex": 0.0,
    "appro_co2_opex": 10974.0,
    # Maintenance - Annual costs (€/year)
    "site_maintenance": 1200.0,
    "appro_co2_maintenance": 2250.0,
    # Methanation Economics (for LCOCH4 calculation)
    # CapEx Components
    "methanation_capex_methanation_unit": 4000000.0,
    "methanation_capex_purification_unit": 0.0,
    "methanation_capex_compressor": 0.0,
    "methanation_capex_ch4_storage": 0.0,
    "methanation_capex_grid_injection": 20000.0,
    # Maintenance ratios (% of CapEx per year)
    "methanation_maintenance_ratio_methanation_unit": 1.0,
    "methanation_maintenance_ratio_purification_unit": 1.0,
    "methanation_maintenance_ratio_compressor": 2.0,
    "methanation_maintenance_ratio_ch4_storage": 0.5,
    "methanation_maintenance_ratio_grid_injection": 0.5,
    # OpEx - Electricity consumption (MWhe/year)
    "methanation_electricity_methanation_unit": 219.0,
    "methanation_electricity_purification_unit": 0.0,
    "methanation_electricity_compressor": 0.0,
    "methanation_electricity_ch4_storage": 0.0,
    "methanation_electricity_grid_injection": 0.0,
    # Economics parameters
    "methanation_lifetime": 20,
    "methanation_discount_rate": 0.0,
    # Others costs by category
    "methanation_others_capex": 0.0,
    "methanation_others_opex_annual": 0.0,
    "methanation_others_maintenance_annual": 0.0,
    # LCOS (Levelized Cost of Storage) parameters
    "lcos_inflation_rate": 2.8,  # Inflation rate (%)
    "lcos_debt_fraction": 20.0,  # Debt Fraction (%)
    "lcos_nominal_interest_rate": 8.0,  # Nominal interest rate (%)
    "lcos_tax_rate": 21.0,  # Tax rate (federal and state) (%)
    "lcos_nominal_cost_of_equity": 12.0,  # Nominal cost of equity (%)
    "lcos_economic_life": 20,  # Economic life (years)
    "lcos_construction_period": 1,  # Construction period (years)
    "lcos_capital_fraction_year_0": 70.0,  # Capital fraction in year 0 (%)
    "lcos_capital_fraction_year_1": 30.0,  # Capital fraction in year 1 (%)
    "lcos_capital_fraction_year_2": 0.0,  # Capital fraction in year 2 (%)
    "lcos_capital_fraction_year_3": 0.0,  # Capital fraction in year 3 (%)
    "lcos_pvd_macrs": 0.7,  # Present Value of Depreciation (MACRS)
    # Battery-specific LCOS parameters
    "lcos_battery_charging_power_kw": 5000.0,  # Charging Power (kW)
    "lcos_battery_duration_hours": 4.0,  # Duration (Hours)
    "lcos_battery_cycles_per_day": 1.0,  # Cycle per day
    "lcos_battery_operating_days_year": 358.0,  # Operating Days/Years
    "lcos_battery_capex_per_kw": 172.0,  # Initial Capex ($/kW)
    "lcos_battery_opex_fixed_per_kw_year": 20.0,  # Annual Fixed O&M ($/kW-year)
    "lcos_battery_replacement_cost_per_kw": 120.4,  # Battery replacement cost ($/kW)
    "lcos_battery_efficiency": 91.0,  # System Round-Trip Efficiency (%)
    "lcos_battery_replacement_years": 10,  # Battery replacement interval (years)
    "lcos_electricity_charging_cost": 0.042,  # Electricity Charging Cost ($/kWh-Purchased)
    # Legacy parameters for backward compatibility
    "lcos_battery_capex_per_kwh": 0.0,  # Battery CAPEX (€/kWh) - legacy
    "lcos_battery_opex_percentage": 2.5,  # Battery O&M (% of CAPEX per year) - legacy
}

# Parameter ranges
PARAM_RANGES = {
    "electrolyser_power": {"min": 0.25, "max": 20.0, "step": 0.25},
    "h2_flowrate": {"min": 100.0, "max": 5000.0, "step": 1.0},  # Nm³/h
    "electrolyser_specific_consumption": {"min": 4.0, "max": 6.0, "step": 0.1},  # Still kept for backward compatibility
    "service_ratio": {"min": 0.0, "max": 1.0, "step": 0.01},
    "pv_price": {"min": 0.0, "max": 100.0, "step": 5.0},
    "ppa_price": {"min": 40.0, "max": 300.0, "step": 5.0},
    "target_price": {"min": 20.0, "max": 100.0, "step": 5.0},
    "pv_project_years": {"min": 15, "max": 30, "step": 1},
    "pv_surface_hectares": {"min": 0.1, "max": 20.0, "step": 0.1},
    "power_density_mwp_per_ha": {"min": 0.5, "max": 3.0, "step": 0.1},
    "storage_hours": {"min": 0.0, "max": 12.0, "step": 0.5},
    "pv_cost_per_wp": {"min": 0.3, "max": 2.0, "step": 0.05},
    "battery_cost_per_kwh": {"min": 100.0, "max": 500.0, "step": 10.0},
    "opex_percentage": {"min": 0.5, "max": 5.0, "step": 0.1},
    "discount_rate": {"min": 0.0, "max": 12.0, "step": 0.5},
    "pci_ch4_kwh_per_kg": {"min": 10.0, "max": 20.0, "step": 0.1},
    # Methanation parameters
    "ch4_flowrate": {"min": 50.0, "max": 2000.0, "step": 10.0},  # Nm³/h
    "methanation_cons_spec_ch4": {"min": 0.1, "max": 2.0, "step": 0.1},  # Still kept for backward compatibility
    # Electrolyzer Economics ranges
    # CapEx Components ranges
    "electrolyser_capex_transformer": {"min": 0.0, "max": 5000000.0, "step": 10000.0},
    "electrolyser_capex_electrolyzer": {"min": 0.0, "max": 20000000.0, "step": 100000.0},
    "electrolyser_capex_compressor": {"min": 0.0, "max": 5000000.0, "step": 10000.0},
    "electrolyser_capex_h2_storage": {"min": 0.0, "max": 5000000.0, "step": 10000.0},
    "electrolyser_capex_piping": {"min": 0.0, "max": 1000000.0, "step": 5000.0},
    "electrolyser_capex_stack_shift": {"min": 0.0, "max": 10000000.0, "step": 100000.0},
    # Maintenance ratios ranges
    "electrolyser_maintenance_ratio_transformer": {"min": 0.0, "max": 10.0, "step": 0.1},
    "electrolyser_maintenance_ratio_electrolyzer": {"min": 0.0, "max": 10.0, "step": 0.1},
    "electrolyser_maintenance_ratio_compressor": {"min": 0.0, "max": 10.0, "step": 0.1},
    "electrolyser_maintenance_ratio_h2_storage": {"min": 0.0, "max": 10.0, "step": 0.1},
    "electrolyser_maintenance_ratio_piping": {"min": 0.0, "max": 10.0, "step": 0.1},
    # Economics parameters ranges
    "electrolyser_lifetime": {"min": 5, "max": 30, "step": 1},
    "electrolyser_discount_rate": {"min": 0.0, "max": 15.0, "step": 0.5},
    "electrolyser_opex_annual": {"min": 0.0, "max": 10000000.0, "step": 10000.0},
    "electrolyser_maintenance_annual": {"min": 0.0, "max": 500000.0, "step": 1000.0},
    "electrolyser_water_price_per_m3": {"min": 0.0, "max": 20.0, "step": 0.1},
    "electrolyser_water_consumption_annual_m3": {"min": 0.0, "max": 50000.0, "step": 100.0},
    "electrolyser_stack_replacement_years": {"min": 3, "max": 15, "step": 1},
    "electrolyser_stack_replacement_cost": {"min": 0.0, "max": 10000000.0, "step": 50000.0},
    # Others costs ranges
    "electrolyser_others_capex": {"min": 0.0, "max": 5000000.0, "step": 10000.0},
    "electrolyser_others_opex_annual": {"min": 0.0, "max": 1000000.0, "step": 1000.0},
    "electrolyser_others_maintenance_annual": {"min": 0.0, "max": 500000.0, "step": 1000.0},
    # Site and CO2 Supply ranges
    "site_capex": {"min": 0.0, "max": 2000000.0, "step": 1000.0},
    "appro_co2_capex": {"min": 0.0, "max": 2000000.0, "step": 1000.0},
    "site_opex": {"min": 0.0, "max": 500000.0, "step": 1000.0},
    "appro_co2_opex": {"min": 0.0, "max": 500000.0, "step": 1000.0},
    "site_maintenance": {"min": 0.0, "max": 100000.0, "step": 100.0},
    "appro_co2_maintenance": {"min": 0.0, "max": 100000.0, "step": 100.0},
    # Methanation Economics ranges
    # CapEx Components ranges
    "methanation_capex_methanation_unit": {"min": 0.0, "max": 20000000.0, "step": 100000.0},
    "methanation_capex_purification_unit": {"min": 0.0, "max": 10000000.0, "step": 100000.0},
    "methanation_capex_compressor": {"min": 0.0, "max": 5000000.0, "step": 10000.0},
    "methanation_capex_ch4_storage": {"min": 0.0, "max": 5000000.0, "step": 10000.0},
    "methanation_capex_grid_injection": {"min": 0.0, "max": 1000000.0, "step": 5000.0},
    # Maintenance ratios ranges
    "methanation_maintenance_ratio_methanation_unit": {"min": 0.0, "max": 10.0, "step": 0.1},
    "methanation_maintenance_ratio_purification_unit": {"min": 0.0, "max": 10.0, "step": 0.1},
    "methanation_maintenance_ratio_compressor": {"min": 0.0, "max": 10.0, "step": 0.1},
    "methanation_maintenance_ratio_ch4_storage": {"min": 0.0, "max": 10.0, "step": 0.1},
    "methanation_maintenance_ratio_grid_injection": {"min": 0.0, "max": 10.0, "step": 0.1},
    # OpEx - Electricity consumption ranges (MWhe/year)
    "methanation_electricity_methanation_unit": {"min": 0.0, "max": 10000.0, "step": 10.0},
    "methanation_electricity_purification_unit": {"min": 0.0, "max": 5000.0, "step": 10.0},
    "methanation_electricity_compressor": {"min": 0.0, "max": 5000.0, "step": 10.0},
    "methanation_electricity_ch4_storage": {"min": 0.0, "max": 1000.0, "step": 10.0},
    "methanation_electricity_grid_injection": {"min": 0.0, "max": 1000.0, "step": 10.0},
    # Economics parameters ranges
    "methanation_lifetime": {"min": 5, "max": 30, "step": 1},
    "methanation_discount_rate": {"min": 0.0, "max": 15.0, "step": 0.5},
    # Others costs ranges
    "methanation_others_capex": {"min": 0.0, "max": 5000000.0, "step": 10000.0},
    "methanation_others_opex_annual": {"min": 0.0, "max": 1000000.0, "step": 1000.0},
    "methanation_others_maintenance_annual": {"min": 0.0, "max": 500000.0, "step": 1000.0},
    # LCOS parameter ranges
    "lcos_inflation_rate": {"min": 0.0, "max": 10.0, "step": 0.1},
    "lcos_debt_fraction": {"min": 0.0, "max": 100.0, "step": 5.0},
    "lcos_nominal_interest_rate": {"min": 0.0, "max": 15.0, "step": 0.1},
    "lcos_tax_rate": {"min": 0.0, "max": 50.0, "step": 1.0},
    "lcos_nominal_cost_of_equity": {"min": 0.0, "max": 20.0, "step": 0.1},
    "lcos_economic_life": {"min": 5, "max": 30, "step": 1},
    "lcos_construction_period": {"min": 1, "max": 3, "step": 1},
    "lcos_capital_fraction_year_0": {"min": 0.0, "max": 100.0, "step": 5.0},
    "lcos_capital_fraction_year_1": {"min": 0.0, "max": 100.0, "step": 5.0},
    "lcos_capital_fraction_year_2": {"min": 0.0, "max": 100.0, "step": 5.0},
    "lcos_capital_fraction_year_3": {"min": 0.0, "max": 100.0, "step": 5.0},
    "lcos_pvd_macrs": {"min": 0.0, "max": 1.0, "step": 0.05},
    # Battery-specific LCOS parameter ranges
    "lcos_battery_charging_power_kw": {"min": 1000.0, "max": 500000.0, "step": 1000.0},
    "lcos_battery_duration_hours": {"min": 1.0, "max": 24.0, "step": 1.0},
    "lcos_battery_cycles_per_day": {"min": 0.5, "max": 10.0, "step": 0.5},
    "lcos_battery_operating_days_year": {"min": 200.0, "max": 365.0, "step": 5.0},
    "lcos_battery_capex_per_kw": {"min": 50.0, "max": 10000.0, "step": 10.0},
    "lcos_battery_opex_fixed_per_kw_year": {"min": 0.0, "max": 10000.0, "step": 0.5},
    "lcos_battery_replacement_cost_per_kw": {"min": 30.0, "max": 30000.0, "step": 10.0},
    "lcos_battery_efficiency": {"min": 70.0, "max": 95.0, "step": 1.0},
    "lcos_battery_replacement_years": {"min": 5, "max": 20, "step": 1},
    "lcos_electricity_charging_cost": {"min": 0.01, "max": 1000.0, "step": 0.01},
    # Legacy parameter ranges for backward compatibility
    "lcos_battery_capex_per_kwh": {"min": 100.0, "max": 1000.0, "step": 10.0},
    "lcos_battery_opex_percentage": {"min": 0.5, "max": 100.0, "step": 0.1}
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
    /* Enhanced table header styling */
    .stDataFrame thead tr th {
        background-color: #1f77b4 !important;
        color: white !important;
        font-weight: bold !important;
        padding: 12px 8px !important;
        text-align: center !important;
    }
    /* For st.table() headers */
    table thead tr th {
        background-color: #1f77b4 !important;
        color: white !important;
        font-weight: bold !important;
        padding: 12px 8px !important;
        text-align: center !important;
    }
    /* Table body styling for better readability */
    .stDataFrame tbody tr:hover {
        background-color: #f5f5f5 !important;
    }
    table tbody tr:hover {
        background-color: #f5f5f5 !important;
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
