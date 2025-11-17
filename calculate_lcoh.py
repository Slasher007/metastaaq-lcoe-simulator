"""
Calculate LCOH (Levelized Cost of Hydrogen) for electrolyzer with 3 energy sources
"""

import numpy as np


def calculate_crf(discount_rate, lifetime):
    """
    Calculate Capital Recovery Factor (CRF) for annualization
    
    CRF = r(1+r)^n / ((1+r)^n - 1)
    
    Args:
        discount_rate: Discount rate in percentage (e.g., 5 for 5%)
        lifetime: Project lifetime in years
    
    Returns:
        Capital Recovery Factor
    """
    r = discount_rate / 100  # Convert % to decimal
    n = lifetime
    if r == 0:
        return 1 / n
    return (r * (1 + r)**n) / ((1 + r)**n - 1)


def calculate_electrolyzer_annualized_costs(
    electrolyzer_capex_total,
    electrolyzer_lifetime,
    electrolyzer_discount_rate,
    electrolyzer_maintenance_annual,
    water_cost_annual,
    other_costs_annual,
    stack_replacement_cost,
    stack_replacement_years,
    electricity_cost_annual,
    water_price_per_m3=None,
    water_consumption_annual_m3=None
):
    """
    Calculate annualized costs for the electrolyzer
    
    Args:
        electrolyzer_capex_total: Total capital expenditure (€)
        electrolyzer_lifetime: Project lifetime (years)
        electrolyzer_discount_rate: Discount rate in %
        electrolyzer_maintenance_annual: Annual maintenance cost (€/year)
        water_cost_annual: Annual water cost (€/year)
        other_costs_annual: Other annual costs (€/year)
        stack_replacement_cost: Total cost for stack replacement (€)
        stack_replacement_years: Years between stack replacements
        electricity_cost_annual: Annual electricity cost (€/year) - for OPEX calculation
        water_price_per_m3: Optional - Water price per m³ (for display)
        water_consumption_annual_m3: Optional - Water consumption in m³/year (for display)
    
    Returns:
        dict with annualized cost breakdown
    """
    # Calculate CRF and annualize CapEx
    crf = calculate_crf(electrolyzer_discount_rate, electrolyzer_lifetime)
    capex_annualized = electrolyzer_capex_total * crf
    
    # Annual costs
    maintenance_annual = electrolyzer_maintenance_annual
    water_annual = water_cost_annual
    other_annual = other_costs_annual
    
    # OPEX is calculated as: Electricity + Water
    opex_annual = electricity_cost_annual + water_annual
    
    # Stack replacement cost (annualized using CRF)
    # Annualize over replacement interval
    stack_crf = calculate_crf(electrolyzer_discount_rate, stack_replacement_years)
    stack_annual = stack_replacement_cost * stack_crf
    
    # Total annualized costs
    # Note: OPEX already includes electricity and water, so we don't add them separately
    total_annualized = capex_annualized + opex_annual + maintenance_annual + other_annual + stack_annual
    
    result = {
        'capex_total': electrolyzer_capex_total,
        'capex_annualized': capex_annualized,
        'crf': crf,
        'lifetime': electrolyzer_lifetime,
        'opex_annual': opex_annual,
        'opex_electricity': electricity_cost_annual,
        'opex_water': water_annual,
        'maintenance_annual': maintenance_annual,
        'water_annual': water_annual,
        'other_annual': other_annual,
        'stack_replacement_cost_total': stack_replacement_cost,
        'stack_annual': stack_annual,
        'total_annualized': total_annualized
    }
    
    # Add water details if provided
    if water_price_per_m3 is not None and water_consumption_annual_m3 is not None:
        result['water_details'] = {
            'price_per_m3': water_price_per_m3,
            'consumption_m3': water_consumption_annual_m3
        }
    
    return result


def add_capex_components_to_result(result, electrolyzer_economics):
    """
    Add CapEx components details to the result if available
    
    Args:
        result: The annualized costs result dict
        electrolyzer_economics: The economics dict with potential capex_components
    
    Returns:
        Updated result dict
    """
    if 'capex_components' in electrolyzer_economics:
        result['capex_components'] = electrolyzer_economics['capex_components']
    
    return result


def calculate_annual_electricity_cost(
    pv_energy_mwh_dict,
    spot_energy_mwh_dict,
    ppa_energy_mwh_dict,
    pv_price,
    spot_price,
    ppa_price,
    go_enabled=False,
    go_cost_per_mwh=0.0
):
    """
    Calculate total annual electricity cost from all sources
    
    Args:
        pv_energy_mwh_dict: Monthly PV energy consumption {month: MWh}
        spot_energy_mwh_dict: Monthly spot energy consumption {month: MWh}
        ppa_energy_mwh_dict: Monthly PPA energy consumption {month: MWh}
        pv_price: PV price per MWh (€/MWh)
        spot_price: Spot price per MWh (€/MWh)
        ppa_price: PPA price per MWh (€/MWh)
        go_enabled: Whether GO certificates are enabled for spot
        go_cost_per_mwh: GO certificate cost per MWh (€/MWh)
    
    Returns:
        dict with total cost and breakdown
    """
    # Calculate effective spot price including GO
    effective_spot_price = spot_price + (go_cost_per_mwh if go_enabled else 0.0)
    
    total_pv_energy = sum(pv_energy_mwh_dict.values())
    total_spot_energy = sum(spot_energy_mwh_dict.values())
    total_ppa_energy = sum(ppa_energy_mwh_dict.values())
    
    pv_cost = total_pv_energy * pv_price
    spot_cost = total_spot_energy * effective_spot_price
    ppa_cost = total_ppa_energy * ppa_price
    
    total_cost = pv_cost + spot_cost + ppa_cost
    total_energy = total_pv_energy + total_spot_energy + total_ppa_energy
    
    # Calculate weighted average electricity cost
    avg_electricity_cost = total_cost / total_energy if total_energy > 0 else 0
    
    return {
        'pv_cost': pv_cost,
        'spot_cost': spot_cost,
        'ppa_cost': ppa_cost,
        'total_cost': total_cost,
        'total_energy': total_energy,
        'avg_electricity_cost': avg_electricity_cost,
        'pv_energy': total_pv_energy,
        'spot_energy': total_spot_energy,
        'ppa_energy': total_ppa_energy
    }


def calculate_h2_production_annual(
    electrolyzer_power_mw,
    electrolyzer_specific_consumption_kwh_per_nm3,
    monthly_service_ratios
):
    """
    Calculate annual H2 production in kg
    
    Args:
        electrolyzer_power_mw: Electrolyzer power in MW
        electrolyzer_specific_consumption_kwh_per_nm3: kWh per Nm³ H₂
        monthly_service_ratios: dict {month: ratio}
    
    Returns:
        Annual H2 production in kg
    """
    # Days per month
    days_per_month = {
        "January": 31, "February": 28, "March": 31, "April": 30,
        "May": 31, "June": 30, "July": 31, "August": 31,
        "September": 30, "October": 31, "November": 30, "December": 31
    }
    
    # H2 production calculation
    h2_flowrate_nm3_per_h = (electrolyzer_power_mw * 1000) / electrolyzer_specific_consumption_kwh_per_nm3
    
    # H2 density at STP
    h2_density_kg_per_nm3 = 0.08988  # kg/Nm³
    
    total_h2_kg = 0
    for month, ratio in monthly_service_ratios.items():
        days = days_per_month.get(month, 30)
        hours = days * 24 * ratio
        h2_kg_month = h2_flowrate_nm3_per_h * hours * h2_density_kg_per_nm3
        total_h2_kg += h2_kg_month
    
    return total_h2_kg


def calculate_lcoh(
    electrolyzer_power_mw,
    electrolyzer_specific_consumption_kwh_per_nm3,
    monthly_service_ratios,
    electrolyzer_economics,
    pv_energy_mwh_dict,
    spot_energy_mwh_dict,
    ppa_energy_mwh_dict,
    pv_price,
    spot_price,
    ppa_price,
    go_enabled=False,
    go_cost_per_mwh=0.0
):
    """
    Calculate LCOH (Levelized Cost of Hydrogen) in €/kg H₂
    
    LCOH = (CapEx_ann + O&M_ann + Electricity_cost_ann + Other_costs) / H2_production_ann
    
    Args:
        electrolyzer_power_mw: Electrolyzer power in MW
        electrolyzer_specific_consumption_kwh_per_nm3: kWh/Nm³ H₂
        monthly_service_ratios: dict {month: ratio}
        electrolyzer_economics: dict with electrolyzer economic parameters
        pv_energy_mwh_dict: Monthly PV energy {month: MWh}
        spot_energy_mwh_dict: Monthly spot energy {month: MWh}
        ppa_energy_mwh_dict: Monthly PPA energy {month: MWh}
        pv_price: PV price (€/MWh)
        spot_price: Spot price (€/MWh)
        ppa_price: PPA price (€/MWh)
        go_enabled: Whether GO certificates are enabled
        go_cost_per_mwh: GO certificate cost (€/MWh)
    
    Returns:
        dict with LCOH and detailed breakdown
    """
    # 1. Calculate annual electricity cost first (needed for OPEX)
    electricity_costs = calculate_annual_electricity_cost(
        pv_energy_mwh_dict,
        spot_energy_mwh_dict,
        ppa_energy_mwh_dict,
        pv_price,
        spot_price,
        ppa_price,
        go_enabled,
        go_cost_per_mwh
    )
    
    # 2. Calculate annualized electrolyzer costs (including OPEX = electricity + water)
    annualized_costs = calculate_electrolyzer_annualized_costs(
        electrolyzer_economics.get('electrolyzer_capex_total', electrolyzer_economics.get('electrolyzer_capex_annual', 0) / calculate_crf(electrolyzer_economics.get('electrolyzer_discount_rate', 5.0), electrolyzer_economics.get('electrolyzer_lifetime', 10))),
        electrolyzer_economics.get('electrolyzer_lifetime', 20),
        electrolyzer_economics.get('electrolyzer_discount_rate', 5.0),
        electrolyzer_economics['electrolyzer_maintenance_annual'],
        electrolyzer_economics['water_cost_annual'],
        electrolyzer_economics['other_costs_annual'],
        electrolyzer_economics['stack_replacement_cost'],
        electrolyzer_economics['stack_replacement_years'],
        electricity_costs['total_cost'],
        electrolyzer_economics.get('water_price_per_m3'),
        electrolyzer_economics.get('water_consumption_annual_m3')
    )
    
    # Add CapEx components details if available
    annualized_costs = add_capex_components_to_result(annualized_costs, electrolyzer_economics)
    
    # 3. Calculate annual H2 production
    h2_production_kg = calculate_h2_production_annual(
        electrolyzer_power_mw,
        electrolyzer_specific_consumption_kwh_per_nm3,
        monthly_service_ratios
    )
    
    # 4. Calculate LCOH
    # Note: total_annualized already includes electricity cost (via OPEX), so we don't add it again
    total_annual_cost = annualized_costs['total_annualized']
    
    lcoh_eur_per_kg = total_annual_cost / h2_production_kg if h2_production_kg > 0 else 0
    
    # Also calculate in €/MWh H2 (using LHV of H2 = 33.33 kWh/kg)
    h2_lhv_kwh_per_kg = 33.33
    lcoh_eur_per_mwh = lcoh_eur_per_kg * (1000 / h2_lhv_kwh_per_kg)
    
    # Breakdown by component (€/kg H2)
    # Note: OPEX = Electricity + Water, so we break it down for display
    capex_component = annualized_costs['capex_annualized'] / h2_production_kg if h2_production_kg > 0 else 0
    electricity_component = annualized_costs['opex_electricity'] / h2_production_kg if h2_production_kg > 0 else 0
    water_component = annualized_costs['opex_water'] / h2_production_kg if h2_production_kg > 0 else 0
    opex_component = electricity_component + water_component  # OPEX = Electricity + Water
    maintenance_component = annualized_costs['maintenance_annual'] / h2_production_kg if h2_production_kg > 0 else 0
    other_component = annualized_costs['other_annual'] / h2_production_kg if h2_production_kg > 0 else 0
    stack_component = annualized_costs['stack_annual'] / h2_production_kg if h2_production_kg > 0 else 0
    
    return {
        'lcoh_eur_per_kg': lcoh_eur_per_kg,
        'lcoh_eur_per_mwh': lcoh_eur_per_mwh,
        'h2_production_kg': h2_production_kg,
        'h2_production_tonnes': h2_production_kg / 1000,
        'total_annual_cost': total_annual_cost,
        'annualized_costs': annualized_costs,
        'electricity_costs': electricity_costs,
        'breakdown': {
            'capex': capex_component,
            'opex': opex_component,
            'maintenance': maintenance_component,
            'water': water_component,
            'other': other_component,
            'stack': stack_component,
            'electricity': electricity_component
        }
    }

