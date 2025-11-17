"""
Calculate LCOCH4 (Levelized Cost of CH4) for methanation with energy sources
"""

import numpy as np
from calculate_lcoh import calculate_crf


def calculate_methanation_annualized_costs(
    methanation_capex_total,
    methanation_lifetime,
    methanation_discount_rate,
    methanation_maintenance_annual,
    electricity_cost_annual,
    other_costs_annual,
    others_opex_annual=0.0
):
    """
    Calculate annualized costs for the methanation unit
    
    Args:
        methanation_capex_total: Total capital expenditure (€)
        methanation_lifetime: Project lifetime (years)
        methanation_discount_rate: Discount rate in %
        methanation_maintenance_annual: Annual maintenance cost (€/year)
        electricity_cost_annual: Annual electricity cost (€/year)
        other_costs_annual: Other annual costs (€/year)
        others_opex_annual: Additional operational costs (€/year)
    
    Returns:
        dict with annualized cost breakdown
    """
    # Calculate CRF and annualize CapEx
    crf = calculate_crf(methanation_discount_rate, methanation_lifetime)
    capex_annualized = methanation_capex_total * crf
    
    # Annual costs
    maintenance_annual = methanation_maintenance_annual
    other_annual = other_costs_annual
    
    # OPEX is calculated as: Electricity + Others OpEx
    opex_annual = electricity_cost_annual + others_opex_annual
    
    # Total annualized costs
    total_annualized = capex_annualized + opex_annual + maintenance_annual + other_annual
    
    result = {
        'capex_total': methanation_capex_total,
        'capex_annualized': capex_annualized,
        'crf': crf,
        'lifetime': methanation_lifetime,
        'opex_annual': opex_annual,
        'opex_electricity': electricity_cost_annual,
        'opex_others': others_opex_annual,
        'maintenance_annual': maintenance_annual,
        'other_annual': other_annual,
        'total_annualized': total_annualized
    }
    
    return result


def add_capex_components_to_result(result, methanation_economics):
    """
    Add CapEx components details to the result if available
    
    Args:
        result: The annualized costs result dict
        methanation_economics: The economics dict with potential capex_components
    
    Returns:
        Updated result dict
    """
    if 'capex_components' in methanation_economics:
        result['capex_components'] = methanation_economics['capex_components']
    
    if 'maintenance_ratios' in methanation_economics:
        result['maintenance_ratios'] = methanation_economics['maintenance_ratios']
    
    if 'maintenance_breakdown' in methanation_economics:
        result['maintenance_breakdown'] = methanation_economics['maintenance_breakdown']
    
    return result


def calculate_ch4_production_annual(
    h2_production_kg,
    h2_to_ch4_efficiency=0.95
):
    """
    Calculate annual CH4 production from H2 input
    
    Sabatier reaction: CO2 + 4H2 → CH4 + 2H2O
    Stoichiometry: 4 moles H2 (8 kg) → 1 mole CH4 (16 kg)
    Therefore: CH4_kg = H2_kg * (16/8) = H2_kg * 2.0 (theoretical)
    With efficiency: CH4_kg = H2_kg * 2.0 * efficiency
    
    Args:
        h2_production_kg: Annual H2 production in kg
        h2_to_ch4_efficiency: Methanation efficiency (default 0.95 = 95%)
    
    Returns:
        Annual CH4 production in kg
    """
    # Stoichiometric conversion: 4 H2 → 1 CH4
    # 4 * 2 g/mol H2 = 8 g → 16 g CH4
    # Therefore: 1 kg H2 → 2 kg CH4 (stoichiometric)
    stoichiometric_ratio = 2.0
    ch4_production_kg = h2_production_kg * stoichiometric_ratio * h2_to_ch4_efficiency
    
    return ch4_production_kg


def calculate_lcoch4(
    h2_production_kg,
    methanation_economics,
    electricity_costs_for_methanation,
    h2_to_ch4_efficiency=0.95
):
    """
    Calculate LCOCH4 (Levelized Cost of CH4) in €/kg CH₄
    
    LCOCH4 = (CapEx_ann + O&M_ann + Electricity_cost_ann + Other_costs) / CH4_production_ann
    
    Args:
        h2_production_kg: Annual H2 production in kg (from electrolyzer)
        methanation_economics: dict with methanation economic parameters
        electricity_costs_for_methanation: Electricity costs for methanation process
        h2_to_ch4_efficiency: Methanation efficiency (default 0.95)
    
    Returns:
        dict with LCOCH4 and detailed breakdown
    """
    # 1. Calculate CH4 production from H2 input
    ch4_production_kg = calculate_ch4_production_annual(h2_production_kg, h2_to_ch4_efficiency)
    
    # 2. Calculate annualized methanation costs
    annualized_costs = calculate_methanation_annualized_costs(
        methanation_economics.get('methanation_capex_total', 0),
        methanation_economics.get('methanation_lifetime', 20),
        methanation_economics.get('methanation_discount_rate', 0.0),
        methanation_economics.get('methanation_maintenance_annual', 0),
        electricity_costs_for_methanation,
        methanation_economics.get('other_costs_annual', 0),
        methanation_economics.get('others_opex_annual', 0.0)
    )
    
    # Add CapEx components details if available
    annualized_costs = add_capex_components_to_result(annualized_costs, methanation_economics)
    
    # 3. Calculate LCOCH4
    total_annual_cost = annualized_costs['total_annualized']
    
    lcoch4_eur_per_kg = total_annual_cost / ch4_production_kg if ch4_production_kg > 0 else 0
    
    # Also calculate in €/MWh CH4 (using LHV of CH4 = 13.9 kWh/kg)
    ch4_lhv_kwh_per_kg = 13.9
    lcoch4_eur_per_mwh = lcoch4_eur_per_kg * (1000 / ch4_lhv_kwh_per_kg)
    
    # Breakdown by component (€/kg CH4)
    capex_component = annualized_costs['capex_annualized'] / ch4_production_kg if ch4_production_kg > 0 else 0
    electricity_component = annualized_costs['opex_electricity'] / ch4_production_kg if ch4_production_kg > 0 else 0
    others_opex_component = annualized_costs['opex_others'] / ch4_production_kg if ch4_production_kg > 0 else 0
    opex_component = electricity_component + others_opex_component  # OPEX = Electricity + Others
    maintenance_component = annualized_costs['maintenance_annual'] / ch4_production_kg if ch4_production_kg > 0 else 0
    other_component = annualized_costs['other_annual'] / ch4_production_kg if ch4_production_kg > 0 else 0
    
    # Get electricity consumption details
    electricity_consumption = methanation_economics.get('electricity_consumption', {})
    
    return {
        'lcoch4_eur_per_kg': lcoch4_eur_per_kg,
        'lcoch4_eur_per_mwh': lcoch4_eur_per_mwh,
        'ch4_production_kg': ch4_production_kg,
        'ch4_production_tonnes': ch4_production_kg / 1000,
        'h2_input_kg': h2_production_kg,
        'h2_input_tonnes': h2_production_kg / 1000,
        'h2_to_ch4_efficiency': h2_to_ch4_efficiency,
        'total_annual_cost': total_annual_cost,
        'annualized_costs': annualized_costs,
        'electricity_consumption': electricity_consumption,
        'breakdown': {
            'capex': capex_component,
            'opex': opex_component,
            'electricity': electricity_component,
            'others_opex': others_opex_component,
            'maintenance': maintenance_component,
            'other': other_component
        }
    }

