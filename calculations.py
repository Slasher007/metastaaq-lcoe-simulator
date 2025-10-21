"""
Calculation functions for the MetaSTAAQ Dashboard
"""

import pandas as pd
import numpy as np
from config import PV_ENERGY_KWH


def calculate_derived_parameters(electrolyser_power, electrolyser_specific_consumption):
    """Calculate derived parameters from electrolyzer specifications"""
    h2_flowrate = round((electrolyser_power * 1000) / electrolyser_specific_consumption)
    stoechio_H2_CH4 = 4
    ch4_flowrate = round(h2_flowrate / stoechio_H2_CH4)
    ch4_density = 0.7168  # kg/Nm³ CH₄
    ch4_kg_per_day = ch4_flowrate * 24 * ch4_density
    
    return {
        'h2_flowrate': h2_flowrate,
        'ch4_flowrate': ch4_flowrate,
        'ch4_density': ch4_density,
        'ch4_kg_per_day': ch4_kg_per_day
    }


def calculate_monthly_ch4_production(monthly_service_ratios, ch4_flowrate, ch4_density):
    """Calculate monthly CH4 production based on service ratios"""
    monthly_ch4_production = {}
    
    for month, ratio in monthly_service_ratios.items():
        # Calculate days in month
        days_in_month = (31 if month in ["January", "March", "May", "July", "August", "October", "December"] 
                        else 30 if month != "February" else 28)
        
        monthly_ch4_production[month] = ch4_flowrate * 24 * ratio * days_in_month * ch4_density
    
    return monthly_ch4_production


def calculate_pv_energy_production(pv_surface_hectares, power_density_mwp_per_ha):
    """Calculate PV energy production based on surface area and power density"""
    estimated_power_mwp = pv_surface_hectares * power_density_mwp_per_ha
    estimated_power_kwp = estimated_power_mwp * 1000
    
    # Convert PV energy from kWh to MWh
    pv_energy_mwh = {month: kwh / 1000 for month, kwh in PV_ENERGY_KWH.items()}
    
    return {
        'estimated_power_mwp': estimated_power_mwp,
        'estimated_power_kwp': estimated_power_kwp,
        'pv_energy_mwh': pv_energy_mwh
    }


def calculate_battery_capacity(storage_hours, estimated_power_mwp):
    """Calculate battery capacity based on storage hours and power"""
    battery_capacity_mwh = storage_hours * estimated_power_mwp
    return battery_capacity_mwh


def calculate_capex_opex(estimated_power_kwp, pv_cost_per_wp, battery_capacity_mwh, 
                         battery_cost_per_kwh, opex_percentage, use_calculated_capex, 
                         use_calculated_opex, pv_capex=0, pv_opex=0):
    """Calculate CAPEX and OPEX for PV installation"""
    if use_calculated_capex:
        # estimated_power_kwp is in kWp; convert to Wp for €/Wp input
        pv_capex_calculated = (estimated_power_kwp * 1000) * pv_cost_per_wp
        # battery_capacity_mwh is in MWh; convert to kWh for cost per kWh
        battery_capex = (battery_capacity_mwh * 1000) * battery_cost_per_kwh
        total_capex_calculated = pv_capex_calculated + battery_capex
    else:
        pv_capex_calculated = pv_capex
        # battery_capacity_mwh is in MWh; convert to kWh for cost per kWh
        battery_capex = (battery_capacity_mwh * 1000) * battery_cost_per_kwh
        total_capex_calculated = pv_capex_calculated + battery_capex
    
    if use_calculated_opex:
        # OPEX should be calculated on total CAPEX (PV + Battery) when applicable
        pv_opex_calculated = total_capex_calculated * opex_percentage / 100
    else:
        pv_opex_calculated = pv_opex
    
    return {
        'pv_capex_calculated': pv_capex_calculated,
        'battery_capex': battery_capex,
        'total_capex_calculated': total_capex_calculated,
        'pv_opex_calculated': pv_opex_calculated
    }


def calculate_energy_breakdown(extended_info, monthly_service_ratios, electrolyser_power, 
                              pv_energy_mwh, include_battery, battery_capacity_mwh):
    """Calculate energy breakdown for each month"""
    monthly_spot_energy = {}
    monthly_ppa_energy = {}
    
    # Calculate spot and PPA energy from extended_info
    for month in monthly_service_ratios.keys():
        spot_energy_total = 0
        ppa_energy_total = 0
        
        for year_str in extended_info:
            if month in extended_info[year_str]:
                info = extended_info[year_str][month]
                spot_hours = info.get('spot_hours', 0)
                ppa_hours = info.get('ppa_hours', 0)
                
                spot_energy_total += spot_hours * electrolyser_power
                ppa_energy_total += ppa_hours * electrolyser_power
        
        # Average across years if multiple years present
        num_years = len([y for y in extended_info if month in extended_info[y]])
        if num_years > 0:
            monthly_spot_energy[month] = spot_energy_total / num_years
            monthly_ppa_energy[month] = ppa_energy_total / num_years
        else:
            # Fallback to existing calculation
            monthly_spot_energy[month] = 0
            monthly_ppa_energy[month] = 0
    
    # Calculate energy breakdown using actual spot/PPA hours from extended_info
    pv_direct_mwh = {}
    spot_energy_mwh = {}
    ppa_energy_mwh = {}
    
    for month, pv_energy in pv_energy_mwh.items():
        # PV directly covers part of consumption
        direct_pv_usage = pv_energy
        
        # Get actual spot and PPA energy from hours breakdown
        actual_spot_energy = monthly_spot_energy.get(month, 0)
        actual_ppa_energy = monthly_ppa_energy.get(month, 0)
        
        # Cap spot and PPA energy by remaining consumption needs
        total_grid_energy = actual_spot_energy + actual_ppa_energy
        
        if include_battery and battery_capacity_mwh > 0:
            # With battery: PV can cover more consumption
            max_consumption = electrolyser_power * 24 * 30  # Rough monthly max
            remaining_after_pv = max(0, max_consumption - direct_pv_usage)
            
            # Battery can store excess PV energy
            excess_pv = max(0, direct_pv_usage - max_consumption)
            battery_stored_pv = min(excess_pv, battery_capacity_mwh)
            
            # Spot energy split between direct and battery
            spot_direct_energy = min(actual_spot_energy, remaining_after_pv)
            spot_battery_energy = max(0, actual_spot_energy - spot_direct_energy)
            
            pv_direct_mwh[month] = min(direct_pv_usage, max_consumption)
            spot_energy_mwh[month] = spot_direct_energy
            ppa_energy_mwh[month] = actual_ppa_energy
            
            # Add battery energy to spot
            spot_energy_mwh[month] += spot_battery_energy + battery_stored_pv
        else:
            # Without battery: simple allocation
            pv_direct_mwh[month] = direct_pv_usage
            spot_energy_mwh[month] = actual_spot_energy
            ppa_energy_mwh[month] = actual_ppa_energy
    
    return {
        'pv_direct_mwh': pv_direct_mwh,
        'spot_energy_mwh': spot_energy_mwh,
        'ppa_energy_mwh': ppa_energy_mwh,
        'monthly_spot_energy': monthly_spot_energy,
        'monthly_ppa_energy': monthly_ppa_energy
    }


def calculate_monthly_breakdown(df_plot_data, monthly_service_ratios, pv_price, 
                               actual_spot_price, ppa_price, include_battery, 
                               battery_capacity_mwh, integrate_ppa):
    """Calculate detailed monthly breakdown for display"""
    monthly_breakdown = []
    
    for month in df_plot_data.index:
        if include_battery and battery_capacity_mwh > 0:
            pv_energy = df_plot_data.loc[month, 'PV']
            spot_direct_energy = df_plot_data.loc[month, 'Spot Direct']
            spot_battery_energy = df_plot_data.loc[month, 'Spot Battery']
            ppa_energy = df_plot_data.loc[month, 'PPA'] if integrate_ppa else 0
            
            total_energy = pv_energy + spot_direct_energy + spot_battery_energy + ppa_energy
            
            # Calculate coverage ratios
            pv_ratio = (pv_energy / total_energy * 100) if total_energy > 0 else 0
            spot_direct_ratio = (spot_direct_energy / total_energy * 100) if total_energy > 0 else 0
            spot_battery_ratio = (spot_battery_energy / total_energy * 100) if total_energy > 0 else 0
            ppa_ratio = (ppa_energy / total_energy * 100) if (total_energy > 0 and integrate_ppa) else 0
            
            # Calculate costs
            pv_cost = pv_energy * pv_price
            spot_direct_cost = spot_direct_energy * actual_spot_price
            spot_battery_cost = spot_battery_energy * actual_spot_price * 0.8  # 20% discount for battery
            ppa_cost = (ppa_energy * ppa_price) if integrate_ppa else 0
            total_cost = pv_cost + spot_direct_cost + spot_battery_cost + ppa_cost
            
            # Service ratio and shutdown
            service_ratio_pct = monthly_service_ratios.get(month, 1.0) * 100
            shutdown_hours = 24 * 30 * (1 - monthly_service_ratios.get(month, 1.0))
            
            monthly_breakdown.append({
                'Month': month,
                'PV Energy (MWh)': f"{pv_energy:.1f}",
                'PV Coverage (%)': f"{pv_ratio:.1f}%",
                'PV Cost (€)': f"{pv_cost:,.0f}",
                'Spot Direct Energy (MWh)': f"{spot_direct_energy:.1f}",
                'Spot Direct Coverage (%)': f"{spot_direct_ratio:.1f}%",
                'Spot Direct Cost (€)': f"{spot_direct_cost:,.0f}",
                'Spot Battery Energy (MWh)': f"{spot_battery_energy:.1f}",
                'Spot Battery Coverage (%)': f"{spot_battery_ratio:.1f}%",
                'Spot Battery Cost (€)': f"{spot_battery_cost:,.0f}",
                'Total Energy (MWh)': f"{total_energy:.1f}",
                'Total Cost (€)': f"{total_cost:,.0f}",
                'Avg Cost (€/MWh)': f"{total_cost/total_energy:.2f}" if total_energy > 0 else "0.00",
                'Service Ratio (%)': f"{service_ratio_pct:.1f}%",
                'Shutdown Hours': f"{shutdown_hours:.0f}h"
            })
            
            if integrate_ppa:
                monthly_breakdown[-1].update({
                    'PPA Energy (MWh)': f"{ppa_energy:.1f}",
                    'PPA Coverage (%)': f"{ppa_ratio:.1f}%",
                    'PPA Cost (€)': f"{ppa_cost:,.0f}"
                })
        else:
            # Original logic without battery
            pv_energy = df_plot_data.loc[month, 'PV']
            spot_energy = df_plot_data.loc[month, 'Spot']
            ppa_energy = df_plot_data.loc[month, 'PPA'] if integrate_ppa else 0
            
            total_energy = pv_energy + spot_energy + ppa_energy
            
            # Calculate coverage ratios
            pv_ratio = (pv_energy / total_energy * 100) if total_energy > 0 else 0
            spot_ratio = (spot_energy / total_energy * 100) if total_energy > 0 else 0
            ppa_ratio = (ppa_energy / total_energy * 100) if (total_energy > 0 and integrate_ppa) else 0
            
            # Calculate costs
            pv_cost = pv_energy * pv_price
            spot_cost = spot_energy * actual_spot_price
            ppa_cost = (ppa_energy * ppa_price) if integrate_ppa else 0
            total_cost = pv_cost + spot_cost + ppa_cost
            
            # Service ratio and shutdown
            service_ratio_pct = monthly_service_ratios.get(month, 1.0) * 100
            shutdown_hours = 24 * 30 * (1 - monthly_service_ratios.get(month, 1.0))
            
            monthly_breakdown.append({
                'Month': month,
                'PV Energy (MWh)': f"{pv_energy:.1f}",
                'PV Coverage (%)': f"{pv_ratio:.1f}%",
                'PV Cost (€)': f"{pv_cost:,.0f}",
                'Spot Energy (MWh)': f"{spot_energy:.1f}",
                'Spot Coverage (%)': f"{spot_ratio:.1f}%",
                'Spot Cost (€)': f"{spot_cost:,.0f}",
                'Total Energy (MWh)': f"{total_energy:.1f}",
                'Total Cost (€)': f"{total_cost:,.0f}",
                'Avg Cost (€/MWh)': f"{total_cost/total_energy:.2f}" if total_energy > 0 else "0.00",
                'Service Ratio (%)': f"{service_ratio_pct:.1f}%",
                'Shutdown Hours': f"{shutdown_hours:.0f}h"
            })
            
            if integrate_ppa:
                monthly_breakdown[-1].update({
                    'PPA Energy (MWh)': f"{ppa_energy:.1f}",
                    'PPA Coverage (%)': f"{ppa_ratio:.1f}%",
                    'PPA Cost (€)': f"{ppa_cost:,.0f}"
                })
    
    return monthly_breakdown


def calculate_yearly_totals(df_plot_data, include_battery, battery_capacity_mwh, 
                           integrate_ppa, pv_price, actual_spot_price, ppa_price):
    """Calculate yearly totals and averages"""
    if include_battery and battery_capacity_mwh > 0:
        total_pv_energy = sum(df_plot_data['PV'])
        total_spot_direct_energy = sum(df_plot_data['Spot Direct'])
        total_spot_battery_energy = sum(df_plot_data['Spot Battery'])
        total_spot_energy = total_spot_direct_energy + total_spot_battery_energy
        total_ppa_energy = sum(df_plot_data['PPA']) if integrate_ppa else 0
        total_energy_year = total_pv_energy + total_spot_direct_energy + total_spot_battery_energy + total_ppa_energy
        
        total_pv_cost = total_pv_energy * pv_price
        total_spot_direct_cost = total_spot_direct_energy * actual_spot_price
        avg_battery_discount = 0.8  # 20% discount estimate
        total_spot_battery_cost = total_spot_battery_energy * actual_spot_price * avg_battery_discount
        total_ppa_cost = (total_ppa_energy * ppa_price) if integrate_ppa else 0
        total_cost_year = total_pv_cost + total_spot_direct_cost + total_spot_battery_cost + (total_ppa_cost if integrate_ppa else 0)
        
        # Calculate yearly averages for percentages
        avg_pv_ratio = (total_pv_energy / total_energy_year * 100) if total_energy_year > 0 else 0
        avg_spot_direct_ratio = (total_spot_direct_energy / total_energy_year * 100) if total_energy_year > 0 else 0
        avg_spot_battery_ratio = (total_spot_battery_energy / total_energy_year * 100) if total_energy_year > 0 else 0
        avg_ppa_ratio = (total_ppa_energy / total_energy_year * 100) if (total_energy_year > 0 and integrate_ppa) else 0
        
        yearly_average = {
            'Month': '📊 YEARLY TOTAL',
            'PV Energy (MWh)': f"{total_pv_energy:.1f}",
            'PV Coverage (%)': f"{avg_pv_ratio:.1f}%",
            'PV Cost (€)': f"{total_pv_cost:,.0f}",
            'Spot Direct Energy (MWh)': f"{total_spot_direct_energy:.1f}",
            'Spot Direct Coverage (%)': f"{avg_spot_direct_ratio:.1f}%",
            'Spot Direct Cost (€)': f"{total_spot_direct_cost:,.0f}",
            'Spot Battery Energy (MWh)': f"{total_spot_battery_energy:.1f}",
            'Spot Battery Coverage (%)': f"{avg_spot_battery_ratio:.1f}%",
            'Spot Battery Cost (€)': f"{total_spot_battery_cost:,.0f}",
            'Total Energy (MWh)': f"{total_energy_year:.1f}",
            'Total Cost (€)': f"{total_cost_year:,.0f}",
            'Avg Cost (€/MWh)': f"{total_cost_year/total_energy_year:.2f}" if total_energy_year > 0 else "0.00"
        }
        
        if integrate_ppa:
            yearly_average.update({
                'PPA Energy (MWh)': f"{total_ppa_energy:.1f}",
                'PPA Coverage (%)': f"{avg_ppa_ratio:.1f}%",
                'PPA Cost (€)': f"{total_ppa_cost:,.0f}"
            })
    else:
        # Original logic without battery
        total_pv_energy = sum(df_plot_data['PV'])
        total_spot_energy = sum(df_plot_data['Spot'])
        total_ppa_energy = sum(df_plot_data['PPA']) if integrate_ppa else 0
        total_energy_year = total_pv_energy + total_spot_energy + total_ppa_energy
        
        total_pv_cost = total_pv_energy * pv_price
        total_spot_cost = total_spot_energy * actual_spot_price
        total_ppa_cost = (total_ppa_energy * ppa_price) if integrate_ppa else 0
        total_cost_year = total_pv_cost + total_spot_cost + (total_ppa_cost if integrate_ppa else 0)
        
        # Calculate yearly averages for percentages
        avg_pv_ratio = (total_pv_energy / total_energy_year * 100) if total_energy_year > 0 else 0
        avg_spot_ratio = (total_spot_energy / total_energy_year * 100) if total_energy_year > 0 else 0
        avg_ppa_ratio = (total_ppa_energy / total_energy_year * 100) if (total_energy_year > 0 and integrate_ppa) else 0
        
        yearly_average = {
            'Month': '📊 YEARLY TOTAL',
            'PV Energy (MWh)': f"{total_pv_energy:.1f}",
            'PV Coverage (%)': f"{avg_pv_ratio:.1f}%",
            'PV Cost (€)': f"{total_pv_cost:,.0f}",
            'Spot Energy (MWh)': f"{total_spot_energy:.1f}",
            'Spot Coverage (%)': f"{avg_spot_ratio:.1f}%",
            'Spot Cost (€)': f"{total_spot_cost:,.0f}",
            'Total Energy (MWh)': f"{total_energy_year:.1f}",
            'Total Cost (€)': f"{total_cost_year:,.0f}",
            'Avg Cost (€/MWh)': f"{total_cost_year/total_energy_year:.2f}" if total_energy_year > 0 else "0.00"
        }
        
        if integrate_ppa:
            yearly_average.update({
                'PPA Energy (MWh)': f"{total_ppa_energy:.1f}",
                'PPA Coverage (%)': f"{avg_ppa_ratio:.1f}%",
                'PPA Cost (€)': f"{total_ppa_cost:,.0f}"
            })
    
    return yearly_average


def calculate_pv_economics(total_pv_energy, total_energy_consumed, total_yearly_ch4_kg, 
                          pci_ch4_kwh_per_kg, pv_capex, pv_opex, pv_project_years, 
                          discount_rate):
    """Calculate PV-specific economics"""
    if total_energy_consumed > 0:
        pv_energy_ratio = total_pv_energy / total_energy_consumed
        pv_ch4_production_kg = total_yearly_ch4_kg * pv_energy_ratio
        yearly_GWh_PCI_ch4_pv = (pv_ch4_production_kg * pci_ch4_kwh_per_kg) / 1000000  # Convert kWh to GWh
        
        if yearly_GWh_PCI_ch4_pv > 0:
            euro_per_MWh_PCI_CH4_pv = (pv_capex + (pv_opex * pv_project_years)) / (yearly_GWh_PCI_ch4_pv * pv_project_years * 1000)  # Convert GWh to MWh
        else:
            euro_per_MWh_PCI_CH4_pv = 0
    else:
        pv_energy_ratio = 0
        pv_ch4_production_kg = 0
        yearly_GWh_PCI_ch4_pv = 0
        euro_per_MWh_PCI_CH4_pv = 0
    
    # LCOE Calculation for CH4 (excluding methanation costs)
    discount_rate_decimal = discount_rate / 100
    
    # Calculate discounted costs (CAPEX in year 0, OPEX annually)
    discounted_costs = pv_capex  # CAPEX at year 0 (already in present value)
    for year in range(1, pv_project_years + 1):
        discounted_costs += pv_opex / ((1 + discount_rate_decimal) ** year)
    
    # Calculate discounted CH4 output (assuming constant annual production)
    discounted_ch4_output = 0
    for year in range(1, pv_project_years + 1):
        discounted_ch4_output += pv_ch4_production_kg / ((1 + discount_rate_decimal) ** year)
    
    # Calculate LCOE in €/kg CH4
    lcoe_ch4_euro_per_kg = discounted_costs / discounted_ch4_output if discounted_ch4_output > 0 else 0
    
    return {
        'pv_energy_ratio': pv_energy_ratio,
        'pv_ch4_production_kg': pv_ch4_production_kg,
        'yearly_GWh_PCI_ch4_pv': yearly_GWh_PCI_ch4_pv,
        'euro_per_MWh_PCI_CH4_pv': euro_per_MWh_PCI_CH4_pv,
        'lcoe_ch4_euro_per_kg': lcoe_ch4_euro_per_kg
    }
