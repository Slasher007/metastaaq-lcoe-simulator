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
    create_energy_distribution_pie_chart, create_consecutive_slots_distributions, create_consecutive_slots_heatmap
)
from calculations import (
    calculate_derived_parameters, calculate_monthly_ch4_production, calculate_pv_energy_production,
    calculate_battery_capacity, calculate_capex_opex, calculate_energy_breakdown,
    calculate_monthly_breakdown, calculate_yearly_totals, calculate_pv_economics, calculate_pv_lcoe
)

import os
import time


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
    
    # Strategy selection before service ratios
    electrolyser_power, electrolyser_specific_consumption = create_electrolyzer_parameters()
    strategy_type = create_operation_strategy_selection()
    if strategy_type == "Target Price-Based":
        monthly_service_ratios = create_monthly_service_ratios(allow_edit=False, preset_ratios=st.session_state.get('computed_service_ratios'))
    else:
        monthly_service_ratios = create_monthly_service_ratios(allow_edit=True)
    target_prices, pv_price, ppa_price = create_price_parameters(strategy_type)
    pv_params = create_pv_installation_parameters()
    st.session_state.pv_params = pv_params
    
    # Calculate PV energy production early for display
    pv_energy_data = calculate_pv_energy_production(
        pv_params['pv_surface_hectares'], 
        pv_params['power_density_mwp_per_ha'],
        pv_params['lat'],
        pv_params['lon'],
        pv_params['loss']
    )
    st.session_state.pv_energy_data = pv_energy_data
    
    # Calculate derived parameters
    derived_params = calculate_derived_parameters(electrolyser_power, electrolyser_specific_consumption)
    monthly_ch4_production = calculate_monthly_ch4_production(
        monthly_service_ratios, derived_params['ch4_flowrate'], derived_params['ch4_density']
    )
    
    # Calculate average service ratio (use computed ratios for Target Price when available)
    computed_ratios_state = st.session_state.get('computed_service_ratios') if strategy_type == "Target Price-Based" else None
    if computed_ratios_state and len(computed_ratios_state) == len(monthly_service_ratios):
        avg_service_ratio = sum(computed_ratios_state.values()) / len(computed_ratios_state)
    else:
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

    current_params['strategy_type'] = strategy_type

    params_changed = st.session_state.last_params != current_params
    st.session_state.last_params = current_params.copy()

    # Display parameter change info
    display_parameter_change_info(params_changed)

    if 'last_strategy_type' not in st.session_state:
        st.session_state.last_strategy_type = strategy_type

    strategy_changed_to_target = (st.session_state.last_strategy_type != strategy_type) and strategy_type == "Target Price-Based"
    st.session_state.last_strategy_type = strategy_type

    auto_refresh = st.sidebar.checkbox("Enable auto-refresh on data changes", value=False, help="Checks for data file changes every 10 seconds and re-runs simulation if changed.")

    data_changed = False
    if auto_refresh:
        current_mtime = os.path.getmtime(DEFAULT_DATA_FILE)
        if 'last_data_mtime' not in st.session_state:
            st.session_state.last_data_mtime = current_mtime
        if current_mtime > st.session_state.last_data_mtime:
            st.session_state.last_data_mtime = current_mtime
            data_content = load_data_file(DEFAULT_DATA_FILE)
            if selected_years:
                data_content = data_content[data_content['Annee'].isin(selected_years)]
            data_changed = True

        if 'last_check' not in st.session_state:
            st.session_state.last_check = time.time()
        if time.time() - st.session_state.last_check > 10:
            st.session_state.last_check = time.time()
            st.rerun()

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
        st.write(f"**Current average service ratio:** {avg_service_ratio:.1%}")
    
    # Move PV images section here (after Current Monthly Service Ratios)
    display_pv_images()

    # Manual refresh button (only for Target Price-Based strategy)
    if strategy_type == "Target Price-Based":
        # Style the button with green background
        st.markdown("""
        <style>
        .green-button button {
            background-color: green !important;
            color: white !important;
        }
        </style>
        """, unsafe_allow_html=True)
        st.markdown('<div class="green-button">', unsafe_allow_html=True)
        manual_refresh = st.button("Run Simulation", help="Force refresh the simulation")
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        manual_refresh = False

    # Run simulation
    run_simulation = params_changed or data_changed or manual_refresh or 'simulation_run' not in st.session_state or strategy_changed_to_target
    
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
                        st.markdown("### 🎯 Analyzing with {} Strategy:".format(strategy_type))
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
                        
                        # Force monthly operating hours to service ratio × days × 24 when using Service Ratio-Based strategy
                        if strategy_type == "Service Ratio-Based":
                            try:
                                days_per_month = {
                                    "January": 31, "February": 28, "March": 31, "April": 30,
                                    "May": 31, "June": 30, "July": 31, "August": 31,
                                    "September": 30, "October": 31, "November": 30, "December": 31
                                }
                                for year_str, months_dict in result.items():
                                    for month_name, _hours in months_dict.items():
                                        ratio = monthly_service_ratios.get(month_name, 1.0)
                                        total_hours_available = days_per_month.get(month_name, 30) * 24
                                        forced_hours = int(round(total_hours_available * ratio))

                                        # Update result hours to forced value
                                        result[year_str][month_name] = forced_hours

                                        # Update service ratio metadata (keep spot/ppa hours as computed; chart will rescale)
                                        info = extended_info.get(year_str, {}).get(month_name, {})
                                        if info is not None:
                                            denom = total_hours_available if total_hours_available > 0 else 1
                                            info['service_ratio'] = (forced_hours / denom)
                                            if year_str in extended_info and month_name in extended_info[year_str]:
                                                extended_info[year_str][month_name] = info
                            except Exception as _e:
                                # Non-fatal: continue with existing values
                                pass

                        df_result = display_table(result)
                        
                        # Calculate differences
                        df_hour_diff = calculate_percentage_difference(df_result, expected_monthly_hours)
                        df_power_consumption = df_result * electrolyser_power
                        
                        # Display results
                        if strategy_type == "Service Ratio-Based":
                            st.markdown("### 📊 Operating Hours per Month (Service Ratio Strategy):")
                        else:
                            st.markdown("### 📊 Operating Hours per Month (Target Price Strategy):")
                        st.dataframe(df_result, width='stretch')
                        
                        # Calculate PV energy production
                        pv_energy_data = calculate_pv_energy_production(
                            pv_params['pv_surface_hectares'], 
                            pv_params['power_density_mwp_per_ha'],
                            pv_params['lat'],
                            pv_params['lon'],
                            pv_params['loss']
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
                        
                        # Compute service ratios from actual hours for Target Price strategy (for titles)
                        recomputed_service = None
                        if strategy_type == "Target Price-Based":
                            days_per_month_title = {
                                "January": 31, "February": 28, "March": 31, "April": 30,
                                "May": 31, "June": 30, "July": 31, "August": 31,
                                "September": 30, "October": 31, "November": 30, "December": 31
                            }
                            recomputed_service = {}
                            for month in monthly_service_ratios.keys():
                                actual_hours = df_result[month].mean() if month in df_result.columns else 0
                                if pd.isna(actual_hours):
                                    actual_hours = 0
                                total_hours_available = days_per_month_title.get(month, 30) * 24
                                recomputed_service[month] = (actual_hours / total_hours_available) if total_hours_available > 0 else 0
                            st.session_state['computed_service_ratios'] = recomputed_service

                        # Create operating hours chart
                        if strategy_type == "Service Ratio-Based":
                            st.markdown("### 📈 Operating Hours Chart (Service Ratio Strategy):")
                        else:
                            st.markdown("### 📈 Operating Hours Chart (Target Price Strategy):")
                        
                        fig1 = create_operating_hours_chart(
                            df_result,
                            extended_info,
                            strategy_type,
                            pv_energy_data['pv_energy_mwh'],
                            electrolyser_power,
                            recomputed_service if strategy_type == "Target Price-Based" else monthly_service_ratios
                        )
                        st.pyplot(fig1)
                        
                        # Show hourly slots by weekday boxplot for Target Price-Based strategy
                        if strategy_type == "Target Price-Based":
                            st.markdown("#### 📊 Distribution of Consecutive Slot Lengths")
                            years_str = ", ".join(map(str, sorted(selected_years))) if selected_years else "All"
                            st.markdown(f"**Daily Purchase Strategy** - Target Price: {target_price}€/MWh | Years: {years_str}")
                            fig_week, fig_month = create_consecutive_slots_distributions(data_content, target_price)
                            st.markdown("##### By Weekday")
                            st.pyplot(fig_week)
                            st.markdown("##### By Month")
                            st.pyplot(fig_month)
                            st.markdown("##### Heatmap Matrix (Avg Length by Month/Weekday)")
                            fig_heat = create_consecutive_slots_heatmap(data_content, target_price)
                            st.pyplot(fig_heat)
                        
                        # PV images already displayed above; skip duplicate here
                        
                        # Calculate actual spot price
                        if strategy_type == "Target Price-Based":
                            # Use weighted average of selected spot hours across months/years
                            total_selected_hours = 0
                            total_selected_cost = 0.0
                            for year_str in extended_info:
                                for month_name, info in extended_info.get(year_str, {}).items():
                                    selected_hours = int(info.get('spot_hours', 0) or 0)
                                    avg_cost_selected = info.get('final_avg_cost', None)
                                    if avg_cost_selected is None or selected_hours <= 0:
                                        continue
                                    total_selected_hours += selected_hours
                                    total_selected_cost += avg_cost_selected * selected_hours
                            actual_spot_price = (total_selected_cost / total_selected_hours) if total_selected_hours > 0 else data_content['Prix'].mean()
                        else:
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
                        if strategy_type == "Target Price-Based":
                            coverage_title = f"### 🔋 Monthly Energy Coverage (Target Price Strategy) - Based on Actual Operating Hours:" if not (pv_params['include_battery'] and battery_capacity_mwh > 0) else f"### 🔋 Monthly Energy Coverage (Target Price Strategy, with {battery_capacity_mwh:.1f} MWh Daily Battery Storage) - Based on Actual Operating Hours:"
                        else:
                            coverage_title = f"### 🔋 Monthly Energy Coverage (Service Ratio Strategy) " if not (pv_params['include_battery'] and battery_capacity_mwh > 0) else f"### 🔋 Monthly Energy Coverage (Service Ratio Strategy, with {battery_capacity_mwh:.1f} MWh Daily Battery Storage) - Spot/PPA Breakdown:"
                        st.markdown(coverage_title, unsafe_allow_html=True)
                        
                        # Prepare data for plotting based on strategy type
                        days_per_month = {
                            "January": 31, "February": 28, "March": 31, "April": 30,
                            "May": 31, "June": 30, "July": 31, "August": 31,
                            "September": 30, "October": 31, "November": 30, "December": 31
                        }
                        pv_list = []
                        spot_list = []
                        ppa_list = []
                        for month in monthly_service_ratios.keys():
                            if strategy_type == "Target Price-Based":
                                # Target Price-Based strategy: use actual operating hours from strategy calculation
                                # Get actual operating hours from df_result (average across years)
                                actual_hours = df_result[month].mean() if month in df_result.columns else 0
                                if pd.isna(actual_hours):
                                    actual_hours = 0
                                required_mwh = actual_hours * electrolyser_power
                                # Compute service ratio from actual hours and calendar days
                                days_per_month = {
                                    "January": 31, "February": 28, "March": 31, "April": 30,
                                    "May": 31, "June": 30, "July": 31, "August": 31,
                                    "September": 30, "October": 31, "November": 30, "December": 31
                                }
                                total_hours_available = days_per_month.get(month, 30) * 24
                                computed_ratio = (actual_hours / total_hours_available) if total_hours_available > 0 else 0
                                if 'computed_service_ratios' not in st.session_state:
                                    st.session_state['computed_service_ratios'] = {}
                                st.session_state['computed_service_ratios'][month] = computed_ratio
                                
                                pv_avail_mwh = pv_energy_data['pv_energy_mwh'].get(month, 0)
                                pv_mwh = min(pv_avail_mwh, required_mwh)
                                remaining_mwh = max(0, required_mwh - pv_mwh)
                                
                                # Target Price-Based strategy uses only spot hours (no PPA mixing)
                                spot_mwh = remaining_mwh
                                ppa_mwh = 0
                            else:
                                # Service Ratio-Based strategy: use forced hours based on service ratios
                                ratio = monthly_service_ratios.get(month, 1.0)
                                forced_hours = int(round(days_per_month.get(month, 30) * 24 * ratio))
                                required_mwh = forced_hours * electrolyser_power

                                pv_avail_mwh = pv_energy_data['pv_energy_mwh'].get(month, 0)
                                pv_mwh = min(pv_avail_mwh, required_mwh)
                                remaining_mwh = max(0, required_mwh - pv_mwh)

                                # Service Ratio-Based strategy: determine Spot/PPA shares from extended_info
                                total_spot_hours = 0
                                total_ppa_hours = 0
                                for year_str in extended_info:
                                    if month in extended_info[year_str]:
                                        info = extended_info[year_str][month]
                                        total_spot_hours += int(info.get('spot_hours', 0) or 0)
                                        total_ppa_hours += int(info.get('ppa_hours', 0) or 0)
                                grid_hours = total_spot_hours + total_ppa_hours
                                if grid_hours > 0:
                                    spot_ratio = total_spot_hours / grid_hours
                                    ppa_ratio = total_ppa_hours / grid_hours
                                else:
                                    spot_ratio = 1.0
                                    ppa_ratio = 0.0

                                spot_mwh = remaining_mwh * spot_ratio
                                ppa_mwh = remaining_mwh * ppa_ratio

                            pv_list.append(pv_mwh)
                            spot_list.append(spot_mwh)
                            ppa_list.append(ppa_mwh)

                        df_plot_data = pd.DataFrame({
                            'PV': pv_list,
                            'Spot': spot_list,
                            'PPA': ppa_list
                        }, index=list(monthly_service_ratios.keys()))
                        
                        if pv_params['include_battery'] and battery_capacity_mwh > 0:
                            # Add battery columns
                            df_plot_data['Spot Direct'] = df_plot_data['Spot'] * 0.7  # Estimate 70% direct
                            df_plot_data['Spot Battery'] = df_plot_data['Spot'] * 0.3  # Estimate 30% battery
                            df_plot_data['Spot'] = df_plot_data['Spot Direct'] + df_plot_data['Spot Battery']
                        
                        # Create energy coverage chart
                        # PPA integration logic based on strategy type
                        if strategy_type == "Target Price-Based":
                            integrate_ppa = False  # Target Price-Based strategy doesn't use PPA
                        else:
                            integrate_ppa = ppa_price >= 60  # Service Ratio-Based: integrate PPA if price >= 60€/MWh
                        # For Target Price-Based, set 24h-per-day baseline (electrolyser_power × days × 24)
                        max_monthly_energy = None
                        if strategy_type == "Target Price-Based":
                            max_monthly_energy = {m: electrolyser_power * 24 * days_per_month[m] for m in days_per_month}
                        fig2 = create_energy_coverage_chart(
                            df_plot_data,
                            pv_params['include_battery'],
                            battery_capacity_mwh,
                            integrate_ppa,
                            monthly_service_ratios=(recomputed_service if strategy_type == "Target Price-Based" else monthly_service_ratios),
                            max_monthly_energy_mwh_by_month=max_monthly_energy
                        )
                        st.pyplot(fig2)
                        
                        # Modify the pie chart section to have two pies side by side
                        pie_section_title = f"### 🥧 Energy Coverage Distribution (with {pv_params['storage_hours']}h Daily Battery):" if pv_params['include_battery'] and battery_capacity_mwh > 0 else "### 🥧 Energy Coverage Distribution:"
                        st.markdown(pie_section_title, unsafe_allow_html=True)
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("**Detailed Distribution**")
                            pie_service_ratios = recomputed_service if strategy_type == "Target Price-Based" else monthly_service_ratios
                            fig3 = create_energy_distribution_pie_chart(
                                df_plot_data,
                                pv_params['include_battery'],
                                battery_capacity_mwh,
                                integrate_ppa,
                                pie_service_ratios
                            )
                            if fig3:
                                st.pyplot(fig3)
                        with col2:
                            st.markdown("**Renewable vs Non-Renewable**")
                            total_pv = sum(df_plot_data['PV'])
                            total_ppa = sum(df_plot_data.get('PPA', pd.Series([0])))
                            total_renewable = total_pv + total_ppa
                            total_non_renewable = sum(df_plot_data['Spot'])
                            total_energy = total_renewable + total_non_renewable
                            if total_energy > 0:
                                pie_data = [total_renewable, total_non_renewable]
                                pie_labels = ['Renewable', 'Non-Renewable']
                                pie_colors = ['green', 'gray']
                                fig4, ax4 = plt.subplots(figsize=(6, 4))
                                wedges, texts, autotexts = ax4.pie(
                                    pie_data,
                                    labels=pie_labels,
                                    colors=pie_colors,
                                    autopct='%1.1f%%',
                                    startangle=90,
                                    pctdistance=0.85,
                                    labeldistance=1.1,
                                    textprops={'fontsize': 10, 'fontweight': 'bold'}
                                )
                                for autotext in autotexts:
                                    autotext.set_color('white')
                                    autotext.set_fontweight('bold')
                                    autotext.set_bbox(dict(boxstyle='round,pad=0.2', facecolor='black', alpha=0.7))
                                for i, (text, value) in enumerate(zip(texts, pie_data)):
                                    text.set_fontweight('bold')
                                    text.set_fontsize(11)
                                    original_text = text.get_text()
                                    text.set_text(f'{original_text}\n({value:.1f} MWh)')
                                    text.set_bbox(dict(boxstyle='round,pad=0.3', 
                                                       facecolor='white', 
                                                       edgecolor=pie_colors[i], 
                                                       alpha=0.9))
                                # Remove title to match heights
                                # ax4.set_title('Renewable vs Non-Renewable Distribution')
                                plt.tight_layout()
                                st.pyplot(fig4)
                        
                        # Display metrics
                        display_metrics_section(target_price, actual_spot_price, price_diff, lcoe)

                        # For Target Price-Based, display computed service ratios and derived CH4 production
                        if strategy_type == "Target Price-Based":
                            # Recompute monthly CH4 production from computed ratios
                            computed_ratios = st.session_state.get('computed_service_ratios', {})
                            recomputed_service = {m: computed_ratios.get(m, 0.0) for m in monthly_service_ratios.keys()}
                            recomputed_monthly_ch4 = calculate_monthly_ch4_production(
                                recomputed_service, derived_params['ch4_flowrate'], derived_params['ch4_density']
                            )
                            display_monthly_ch4_production(recomputed_monthly_ch4, recomputed_service)
                            # Show computed service ratios chart
                            st.markdown("#### 📅 Computed Monthly Service Ratios (Target Price Strategy)")
                            fig_service_computed = create_service_ratios_chart(recomputed_service)
                            st.pyplot(fig_service_computed)
                        
                        # Calculate monthly breakdown (use computed ratios for Target Price-Based)
                        ratios_for_breakdown = recomputed_service if strategy_type == "Target Price-Based" else monthly_service_ratios
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
                        # Reorder columns: keep 'Month' first, move totals and avg cost to the far right
                        move_right = [
                            'Total Energy (MWh)',
                            'Total Cost (€)',
                            'Avg Cost (€/MWh)'
                        ]
                        current_cols = list(breakdown_df.columns)
                        # Ensure 'Month' stays first if present
                        head_cols = ['Month'] if 'Month' in current_cols else []
                        # Middle columns exclude head and move_right
                        mid_cols = [c for c in current_cols if c not in head_cols + move_right]
                        # Right columns in specified order, only if present
                        right_cols = [c for c in move_right if c in current_cols]
                        breakdown_df = breakdown_df[head_cols + mid_cols + right_cols]
                        
                        # Style the dataframe
                        def highlight_yearly_row(row):
                            if row.name == len(breakdown_df) - 1:  # Last row (yearly total)
                                return ['background-color: #1f77b4; color: white; font-weight: bold'] * len(row)
                            return [''] * len(row)
                        
                        styled_df = breakdown_df.style.apply(highlight_yearly_row, axis=1)
                        
                        st.markdown("### 📊 Monthly Energy Breakdown:")
                        st.dataframe(styled_df, width='stretch')
                        
                        # Calculate PV economics
                        # For Target Price-Based: use recomputed CH4 from computed service ratios
                        if strategy_type == "Target Price-Based":
                            computed_ratios = st.session_state.get('computed_service_ratios', {})
                            recomputed_service = {m: computed_ratios.get(m, 0.0) for m in monthly_service_ratios.keys()}
                            recomputed_monthly_ch4 = calculate_monthly_ch4_production(
                                recomputed_service, derived_params['ch4_flowrate'], derived_params['ch4_density']
                            )
                            total_yearly_ch4_kg = sum(recomputed_monthly_ch4.values())
                        else:
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
                        
                        # Compute PV LCOE (€/MWh) using yearly PV production
                        yearly_pv_mwh = sum(pv_energy_data['pv_energy_mwh'].values())
                        pv_lcoe_value = calculate_pv_lcoe(
                            yearly_pv_mwh,
                            capex_opex_data['total_capex_calculated'],
                            capex_opex_data['pv_opex_calculated'],
                            pv_params['pv_project_years'],
                            pv_params['discount_rate']
                        )

                        # Display PV economics summary including PV LCOE
                        display_pv_economics_summary(
                            pv_energy_data['estimated_power_mwp'],
                            pv_energy_data['estimated_power_kwp'],
                            battery_capacity_mwh,
                            capex_opex_data['pv_capex_calculated'],
                            capex_opex_data['battery_capex'],
                            capex_opex_data['total_capex_calculated'],
                            capex_opex_data['pv_opex_calculated'],
                            pv_lcoe_eur_per_mwh=pv_lcoe_value
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
