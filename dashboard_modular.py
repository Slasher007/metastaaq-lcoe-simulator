"""
MetaSTAAQ LCOE Simulation Dashboard - Modular Version
"""

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import io
import base64
import calendar
from mpl_toolkits.mplot3d import Axes3D

# Import individual functions to have better control over plotting
from calculate_max_hours import calculate_max_hours
from calculate_operation_strategies import calculate_hybrid_strategy
from display_table import display_table
from calculate_percentage_difference import calculate_percentage_difference
from get_required_hours_per_month_custom import get_required_hours_per_month_custom
from get_expected_monthly_power_cons_custom import get_expected_monthly_power_cons_custom
from calculate_lcoe import calculate_lcoe

# Import modular components
from config import DEFAULT_DATA_FILE, STRATEGY_TYPES
from ui_components import (
    setup_page_config, display_header, display_sidebar_logo, display_pv_images,
    display_parameter_change_info, display_strategy_info, display_metrics_section,
    display_monthly_ch4_production, display_calculated_parameters, display_pv_economics_summary,
    create_loading_spinner, display_error_message, display_warning_message, 
    display_info_message, display_success_message
)
from sidebar import (
    setup_sidebar_header, load_data_file, create_year_selection, create_electrolyzer_parameters,
    create_monthly_service_ratios, create_operation_strategy_selection, create_price_parameters,
    create_pv_installation_parameters, get_current_parameters
)
from plots import (
    create_monthly_price_analysis_plot, create_price_distribution_box_plot,
    create_service_ratios_chart, create_operating_hours_chart, create_energy_coverage_chart,
    create_energy_distribution_pie_chart
)
from calculations import (
    calculate_derived_parameters, calculate_monthly_ch4_production, calculate_pv_energy_production,
    calculate_battery_capacity, calculate_capex_opex, calculate_energy_breakdown,
    calculate_monthly_breakdown, calculate_yearly_totals, calculate_pv_economics
)


def main():
    """Main dashboard function"""
    # Setup page configuration and header
    setup_page_config()
    display_header()
    display_sidebar_logo()
    
    # Setup sidebar
    setup_sidebar_header()
    
    # Load data
    data_content = load_data_file(DEFAULT_DATA_FILE)
    
    # Create sidebar widgets
    selected_years = create_year_selection(data_content)
    
    # Filter data by selected years
    if selected_years:
        data_content = data_content[data_content['Annee'].isin(selected_years)]
    
    # Get parameters from sidebar
    electrolyser_power, electrolyser_specific_consumption = create_electrolyzer_parameters()
    strategy_type = create_operation_strategy_selection()
    if strategy_type == "Target Price-Based":
        monthly_service_ratios = create_monthly_service_ratios(allow_edit=False, preset_ratios=st.session_state.get('computed_service_ratios'))
    else:
        monthly_service_ratios = create_monthly_service_ratios(allow_edit=True)
    target_prices, pv_price, ppa_price = create_price_parameters(strategy_type)
    pv_params = create_pv_installation_parameters()
    
    # Calculate derived parameters
    derived_params = calculate_derived_parameters(electrolyser_power, electrolyser_specific_consumption)
    monthly_ch4_production = calculate_monthly_ch4_production(
        monthly_service_ratios, derived_params['ch4_flowrate'], derived_params['ch4_density']
    )
    
    # Calculate average service ratio
    avg_service_ratio = sum(monthly_service_ratios.values()) / len(monthly_service_ratios)
    
    # Display calculated parameters in sidebar
    display_calculated_parameters(
        derived_params['h2_flowrate'], 
        derived_params['ch4_flowrate'], 
        avg_service_ratio
    )
    
    # Display monthly CH4 production
    if strategy_type == "Service Ratio-Based":
        display_monthly_ch4_production(monthly_ch4_production, monthly_service_ratios)
    
    # Parameter change detection
    if 'last_params' not in st.session_state:
        st.session_state.last_params = {}
    
    current_params = get_current_parameters(
        selected_years, electrolyser_power, electrolyser_specific_consumption,
        monthly_service_ratios, target_prices, pv_price, ppa_price, pv_params
    )
    
    params_changed = st.session_state.last_params != current_params
    st.session_state.last_params = current_params.copy()
    
    # Display parameter change info and manual refresh button
    manual_refresh = display_parameter_change_info(params_changed)
    
    # Create analysis plots
    st.markdown("#### 📈 Average Monthly Price Analysis")
    fig_price = create_monthly_price_analysis_plot(data_content)
    st.pyplot(fig_price)
    
    st.markdown("#### 📦 Price Distribution by Month (Box Plot)")
    fig_box = create_price_distribution_box_plot(data_content)
    st.pyplot(fig_box)
    
    if strategy_type == "Service Ratio-Based":
        st.markdown("#### 📅 Current Monthly Service Ratios")
        fig_service = create_service_ratios_chart(monthly_service_ratios)
        st.pyplot(fig_service)
    
    # Run simulation
    run_simulation = params_changed or manual_refresh or 'simulation_run' not in st.session_state
    
    if run_simulation:
        if data_content.empty:
            display_error_message("❌ No data available. Please upload a valid CSV file.")
        else:
            results_placeholder = st.empty()
            
            loading_message = "🚀 Running simulation..."
            with create_loading_spinner(loading_message):
                try:
                    # Run simulation for each target price
                    all_results = []
                    
                    for i, target_price in enumerate(target_prices):
                        st.write(f"**Analyzing with {strategy_type} Strategy:**")
                        display_strategy_info(strategy_type, target_price, ppa_price, pv_price)
                        
                        # Run simulation components using selected strategy
                        expected_monthly_hours = get_required_hours_per_month_custom(monthly_service_ratios)
                        expected_monthly_power = get_expected_monthly_power_cons_custom(electrolyser_power, expected_monthly_hours)
                        
                        # Choose strategy based on user selection
                        if strategy_type == "Service Ratio-Based":
                            strategy_key = 'service_ratio'
                            initial_service_ratio = 0.98
                            result, extended_info = calculate_hybrid_strategy(
                                data_content, target_price, ppa_price, pv_price, 
                                strategy_key, 
                                initial_service_ratio=initial_service_ratio,
                                return_extended_info=True
                            )
                        else:  # Target Price-Based
                            strategy_key = 'target_price'
                            result, extended_info = calculate_hybrid_strategy(
                                data_content, target_price, ppa_price, pv_price, 
                                strategy_key, return_extended_info=True
                            )
                        
                        df_result = display_table(result)
                        
                        # Calculate differences
                        df_hour_diff = calculate_percentage_difference(df_result, expected_monthly_hours)
                        df_power_consumption = df_result * electrolyser_power
                        
                        # Display results
                        if strategy_type == "Service Ratio-Based":
                            st.write("**📊 Operating Hours per Month (Service Ratio Strategy):**")
                        else:
                            st.write("**📊 Available Hours per Month:**")
                        st.dataframe(df_result, width='stretch')
                        
                        # Calculate PV energy production
                        pv_energy_data = calculate_pv_energy_production(
                            pv_params['pv_surface_hectares'], 
                            pv_params['power_density_mwp_per_ha']
                        )
                        
                        # Calculate battery capacity if included
                        battery_capacity_mwh = 0
                        if pv_params['include_battery']:
                            battery_capacity_mwh = calculate_battery_capacity(
                                pv_params['storage_hours'], 
                                pv_energy_data['estimated_power_mwp']
                            )
                        
                        # Calculate CAPEX and OPEX
                        capex_opex_data = calculate_capex_opex(
                            pv_energy_data['estimated_power_kwp'],
                            pv_params['pv_cost_per_wp'],
                            battery_capacity_mwh,
                            pv_params['battery_cost_per_kwh'],
                            pv_params['opex_percentage'],
                            pv_params['use_calculated_capex'],
                            pv_params['use_calculated_opex'],
                            pv_params['pv_capex'],
                            pv_params['pv_opex']
                        )
                        
                        # Calculate energy breakdown
                        energy_breakdown = calculate_energy_breakdown(
                            extended_info, monthly_service_ratios, electrolyser_power,
                            pv_energy_data['pv_energy_mwh'], pv_params['include_battery'], battery_capacity_mwh
                        )
                        
                        # Create operating hours chart
                        if strategy_type == "Service Ratio-Based":
                            st.write("**📈 Operating Hours Chart (Service Ratio Strategy):**")
                        else:
                            st.write("**📈 Available Hours Chart:**")
                        
                        fig1 = create_operating_hours_chart(df_result, extended_info, strategy_type, 
                                                            pv_energy_data['pv_energy_mwh'], electrolyser_power)
                        st.pyplot(fig1)
                        
                        # Display PV images
                        display_pv_images()
                        
                        # Calculate actual spot price
                        actual_spot_price = data_content['Prix'].mean()
                        
                        # Calculate price difference
                        price_diff = actual_spot_price - target_price
                        
                        # Calculate LCOE
                        pv_energy_dict = pv_energy_data['pv_energy_mwh']
                        spot_energy_dict = energy_breakdown['spot_energy_mwh']
                        ppa_energy_dict = energy_breakdown['ppa_energy_mwh']
                        
                        lcoe = calculate_lcoe(pv_energy_dict, spot_energy_dict, ppa_energy_dict, 
                                            pv_price, actual_spot_price, ppa_price)
                        
                        # Create energy coverage chart
                        coverage_title = f"**🔋 Monthly Energy Coverage (with {battery_capacity_mwh:.1f} MWh Daily Battery Storage) - Spot/PPA Breakdown:**" if pv_params['include_battery'] and battery_capacity_mwh > 0 else "**🔋 Monthly Energy Coverage - Spot/PPA Breakdown:**"
                        st.write(coverage_title)
                        
                        # Prepare data for plotting
                        df_plot_data = pd.DataFrame({
                            'PV': [pv_energy_data['pv_energy_mwh'][month] for month in monthly_service_ratios.keys()],
                            'Spot': [energy_breakdown['spot_energy_mwh'][month] for month in monthly_service_ratios.keys()],
                            'PPA': [energy_breakdown['ppa_energy_mwh'][month] for month in monthly_service_ratios.keys()]
                        }, index=list(monthly_service_ratios.keys()))
                        
                        if pv_params['include_battery'] and battery_capacity_mwh > 0:
                            # Add battery columns
                            df_plot_data['Spot Direct'] = df_plot_data['Spot'] * 0.7  # Estimate 70% direct
                            df_plot_data['Spot Battery'] = df_plot_data['Spot'] * 0.3  # Estimate 30% battery
                            df_plot_data['Spot'] = df_plot_data['Spot Direct'] + df_plot_data['Spot Battery']
                        
                        # Create energy coverage chart
                        integrate_ppa = ppa_price >= 60  # Only integrate PPA if price >= 60€/MWh
                        fig2 = create_energy_coverage_chart(df_plot_data, pv_params['include_battery'], battery_capacity_mwh, integrate_ppa)
                        st.pyplot(fig2)
                        
                        # Create pie chart
                        pie_section_title = f"**🥧 Energy Coverage Distribution (with {pv_params['storage_hours']}h Daily Battery):**" if pv_params['include_battery'] and battery_capacity_mwh > 0 else "**🥧 Energy Coverage Distribution:**"
                        st.write(pie_section_title)
                        
                        fig3 = create_energy_distribution_pie_chart(df_plot_data, pv_params['include_battery'], battery_capacity_mwh, integrate_ppa)
                        if fig3:
                            st.pyplot(fig3)
                        
                        # Display metrics
                        display_metrics_section(target_price, actual_spot_price, price_diff, lcoe)

                        # For Target Price-Based, compute and display service ratios from results
                        if strategy_type == "Target Price-Based":
                            days_per_month = {
                                "January": 31, "February": 28, "March": 31, "April": 30,
                                "May": 31, "June": 30, "July": 31, "August": 31,
                                "September": 30, "October": 31, "November": 30, "December": 31
                            }
                            computed_ratios = {}
                            for month in monthly_service_ratios.keys():
                                actual_hours = df_result[month].mean() if month in df_result.columns else 0
                                if pd.isna(actual_hours):
                                    actual_hours = 0
                                total_hours_available = days_per_month.get(month, 30) * 24
                                computed_ratios[month] = (actual_hours / total_hours_available) if total_hours_available > 0 else 0
                            st.session_state['computed_service_ratios'] = computed_ratios

                            recomputed_monthly_ch4 = calculate_monthly_ch4_production(
                                computed_ratios, derived_params['ch4_flowrate'], derived_params['ch4_density']
                            )
                            display_monthly_ch4_production(recomputed_monthly_ch4, computed_ratios)
                        
                        # Calculate monthly breakdown (use computed ratios for Target Price-Based)
                        ratios_for_breakdown = st.session_state.get('computed_service_ratios', monthly_service_ratios) if strategy_type == "Target Price-Based" else monthly_service_ratios
                        monthly_breakdown = calculate_monthly_breakdown(
                            df_plot_data, ratios_for_breakdown, pv_price,
                            actual_spot_price, ppa_price, pv_params['include_battery'],
                            battery_capacity_mwh, integrate_ppa
                        )
                        
                        # Calculate yearly totals
                        yearly_average = calculate_yearly_totals(
                            df_plot_data, pv_params['include_battery'], battery_capacity_mwh,
                            integrate_ppa, pv_price, actual_spot_price, ppa_price
                        )
                        
                        # Create breakdown dataframe
                        breakdown_df = pd.DataFrame(monthly_breakdown)
                        breakdown_df = pd.concat([breakdown_df, pd.DataFrame([yearly_average])], ignore_index=True)
                        
                        # Style the dataframe
                        def highlight_yearly_row(row):
                            if row.name == len(breakdown_df) - 1:  # Last row (yearly total)
                                return ['background-color: #1f77b4; color: white; font-weight: bold'] * len(row)
                            return [''] * len(row)
                        
                        styled_df = breakdown_df.style.apply(highlight_yearly_row, axis=1)
                        
                        st.write("**📊 Monthly Energy Breakdown:**")
                        st.dataframe(styled_df, width='stretch')
                        
                        # Calculate PV economics
                        total_yearly_ch4_kg = sum(monthly_ch4_production.values())
                        # Avoid double counting when battery columns are present
                        if pv_params['include_battery'] and battery_capacity_mwh > 0:
                            cols_to_sum = ['PV', 'Spot Direct', 'Spot Battery']
                            if integrate_ppa and 'PPA' in df_plot_data.columns:
                                cols_to_sum.append('PPA')
                            total_energy_consumed = sum(df_plot_data[cols_to_sum].sum(axis=1))
                        else:
                            cols_to_sum = ['PV', 'Spot']
                            if integrate_ppa and 'PPA' in df_plot_data.columns:
                                cols_to_sum.append('PPA')
                            total_energy_consumed = sum(df_plot_data[cols_to_sum].sum(axis=1))
                        
                        pv_economics = calculate_pv_economics(
                            sum(df_plot_data['PV']), total_energy_consumed, total_yearly_ch4_kg,
                            pv_params['pci_ch4_kwh_per_kg'], capex_opex_data['total_capex_calculated'],
                            capex_opex_data['pv_opex_calculated'], pv_params['pv_project_years'],
                            pv_params['discount_rate']
                        )
                        
                        # Display PV economics
                        st.markdown("---")
                        st.markdown("#### ☀️ PV Installation Economics Results")
                        
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("**Total Yearly CH₄ Production**", f"{total_yearly_ch4_kg:,.0f} kg")
                        with col2:
                            st.metric("**PV Yearly Energy Ratio**", f"{pv_economics['pv_energy_ratio']:.1%}")
                        with col3:
                            st.metric("**PV-specific Yearly CH₄ Production**", f"{pv_economics['pv_ch4_production_kg']:,.0f} kg")
                        with col4:
                            st.metric("**PV-specific Yearly GWh PCI CH₄**", f"{pv_economics['yearly_GWh_PCI_ch4_pv']:.2f} GWh")
                        
                        # Display PV economics summary
                        display_pv_economics_summary(
                            pv_energy_data['estimated_power_mwp'],
                            pv_energy_data['estimated_power_kwp'],
                            battery_capacity_mwh,
                            capex_opex_data['pv_capex_calculated'],
                            capex_opex_data['battery_capex'],
                            capex_opex_data['total_capex_calculated'],
                            capex_opex_data['pv_opex_calculated']
                        )
                        
                        # Store results
                        all_results.append({
                            'target_price': target_price,
                            'actual_spot_price': actual_spot_price,
                            'df_result': df_result,
                            'df_power_consumption': df_power_consumption,
                            'monthly_avg_hours': df_result.mean().mean(),
                            'monthly_avg_power': df_power_consumption.mean().mean(),
                            'lcoe': lcoe
                        })
                        
                        if i < len(target_prices) - 1:
                            st.markdown("---")
                
                except Exception as e:
                    display_error_message(f"❌ Error during simulation: {str(e)}")
                    st.exception(e)
            
            # Mark simulation as run
            st.session_state.simulation_run = True


if __name__ == "__main__":
    main()
