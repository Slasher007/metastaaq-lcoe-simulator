"""
Battery Arbitrage Integration Module
Functions to integrate battery optimization into the main dashboard
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

from battery_config import (
    DEFAULT_BATTERY_PARAMS, DEFAULT_TIME_WINDOWS, DEFAULT_ELECTROLYSER_PARAMS,
    validate_time_windows
)

DEFAULT_BATTERY_COST_EUR_PER_MWH = 300 # €/MWh
from battery_optimizer import BatteryOptimizer, generate_typical_pv_profile, load_pv_profile
from battery_visualization import (
    plot_soc_profile, plot_power_flows, plot_economics_breakdown,
    plot_yearly_cashflow, plot_hydrogen_production
)


def render_battery_arbitrage_tab(data_content, electrolyser_power, pv_energy_data, pv_price=0.0, ppa_price=0.0, avg_service_ratio=0.0):
    """
    Render the battery arbitrage optimization tab in the main dashboard
    
    Args:
        data_content: DataFrame with spot price data
        electrolyser_power: Electrolyser power from main dashboard (MW)
        pv_energy_data: PV energy data dict from main dashboard
        pv_price: PV electricity price (€/MWh)
        ppa_price: PPA electricity price (€/MWh) for baseline comparison
    """
    st.markdown("## 🔋 Battery Energy Storage & Arbitrage Optimization")
    st.markdown("---")
    
    # Ensure Date column is datetime and prepare data
    if not pd.api.types.is_datetime64_any_dtype(data_content['Date']):
        data_content['Date'] = pd.to_datetime(data_content['Date'])
    
    # Filter data to only include December 2023
    #start_date = '2023-12-01'
    #end_date = '2023-12-01'
    #start_date = '2025-01-01'
    #end_date = '2025-12-31'
    #mask = (data_content['Date'] >= start_date) & (data_content['Date'] <= end_date)
    #data_content = data_content[mask]

    # Add computed columns
    data_content['Week'] = data_content['Date'].dt.isocalendar().week
    data_content['DayOfWeek'] = data_content['Date'].dt.day_name()
    
    # Get available options
    available_years = sorted(data_content['Annee'].unique())
    month_names_short = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                        'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    available_months = sorted(data_content['Mois'].unique(), 
                             key=lambda x: ['January', 'February', 'March', 'April', 'May', 'June',
                                           'July', 'August', 'September', 'October', 'November', 'December'].index(x))
    available_weeks = sorted(data_content['Week'].unique())
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    available_days = [day for day in day_order if day in data_content['DayOfWeek'].unique()]
    
    # Initialize session state for filters if not exists
    if 'filter_year' not in st.session_state:
        st.session_state.filter_year = available_years[0] if available_years else None  # Single year selection
    if 'filter_months' not in st.session_state:
        st.session_state.filter_months = available_months  # Keep for backward compatibility
    if 'filter_week' not in st.session_state:
        st.session_state.filter_week = None  # Single week selection or None
    if 'filter_day' not in st.session_state:
        st.session_state.filter_day = None  # Single day selection or None

    # Initialize processed filter values
    if 'selected_filter_year' not in st.session_state:
        st.session_state.selected_filter_year = st.session_state.filter_year
    if 'selected_filter_months' not in st.session_state:
        st.session_state.selected_filter_months = available_months  # Default to all months
    if 'selected_filter_week' not in st.session_state:
        st.session_state.selected_filter_week = st.session_state.filter_week
    if 'selected_filter_day' not in st.session_state:
        st.session_state.selected_filter_day = st.session_state.filter_day
    
    # Data filtering controls - make hideable with expander
    with st.expander("🔍 Data Filters", expanded=False):
        st.markdown("Filter spot price data for analysis and optimization")
        
        # Create filter columns
        filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)
        
        with filter_col1:
            # Year filter (single selection)
            current_year = st.session_state.get('selected_filter_year', st.session_state.filter_year)
            st.selectbox(
                "📅 Year",
                options=available_years,
                index=available_years.index(current_year) if current_year in available_years else 0,
                help="Select a year to include",
                key='filter_year'
            )
        
        with filter_col2:
            # Month filter (single selection or None)
            month_options = ["All months"] + available_months
            current_month_value = st.session_state.get('selected_filter_months', st.session_state.filter_months)
            # For months, we need to handle the case where it's a list vs single value
            if isinstance(current_month_value, list):
                current_month = "All months"  # If it's a list, default to all months for compatibility
            else:
                current_month = current_month_value if current_month_value is not None else "All months"
            st.selectbox(
                "📆 Month",
                options=month_options,
                index=month_options.index(current_month) if current_month in month_options else 0,
                help="Select a specific month or 'All months'",
                key='filter_month_selection'
            )
        
        with filter_col3:
            # Week filter (single selection or None)
            week_options = ["All weeks"] + [f"Week {w}" for w in available_weeks]
            current_week_value = st.session_state.get('selected_filter_week', st.session_state.filter_week)
            current_week = f"Week {current_week_value}" if current_week_value is not None else "All weeks"
            st.selectbox(
                "Week",
                options=week_options,
                index=week_options.index(current_week) if current_week in week_options else 0,
                help="Select a specific week or 'All weeks'",
                key='filter_week_selection'
            )
        
        with filter_col4:
            # Day of week filter (single selection or None)
            day_options = ["All days"] + available_days
            current_day_value = st.session_state.get('selected_filter_day', st.session_state.filter_day)
            current_day = current_day_value if current_day_value is not None else "All days"
            st.selectbox(
                "📅 Day of Week",
                options=day_options,
                index=day_options.index(current_day) if current_day in day_options else 0,
                help="Select a specific day or 'All days'",
                key='filter_day_selection'
            )
        
        # Apply Filters Button
        st.markdown("")  # Add spacing
        apply_filters_btn = st.button("🔄 Apply Filters", type="primary", use_container_width=True, 
                                      help="Click to apply selected filters and update analysis")
        
        # Only apply filters if button was clicked or if filters were previously applied
        if 'filters_applied' not in st.session_state:
            st.session_state.filters_applied = False
        
        if apply_filters_btn:
            st.session_state.filters_applied = True
            st.session_state.battery_optimization_run = False

            # Get current widget values and process them
            selected_year = st.session_state.filter_year

            # Parse month selection
            month_selection = st.session_state.filter_month_selection
            selected_months = available_months if month_selection == "All months" else [month_selection]

            # Parse week selection
            week_selection = st.session_state.filter_week_selection
            selected_week = None if week_selection == "All weeks" else int(week_selection.replace("Week ", ""))

            # Parse day selection
            day_selection = st.session_state.filter_day_selection
            selected_day = None if day_selection == "All days" else day_selection

            # Store processed filter values in separate session state variables
            st.session_state.selected_filter_year = selected_year
            st.session_state.selected_filter_months = selected_months
            st.session_state.selected_filter_week = selected_week
            st.session_state.selected_filter_day = selected_day

            st.session_state.filter_config = {
                'year': selected_year,
                'months': selected_months,
                'week': selected_week,
                'day': selected_day
            }
    
    # Apply filters if they have been applied at least once
    if st.session_state.filters_applied and 'filter_config' in st.session_state:
        filtered_data = data_content.copy()
        config = st.session_state.filter_config
        
        # Apply year filter (single year)
        if config['year']:
            filtered_data = filtered_data[filtered_data['Annee'] == config['year']]

        # Apply month filter
        if config['months']:
            filtered_data = filtered_data[filtered_data['Mois'].isin(config['months'])]

        # Apply week filter (single week or None)
        if config['week'] is not None:
            filtered_data = filtered_data[filtered_data['Week'] == config['week']]

        # Apply day of week filter (single day or None)
        if config['day'] is not None:
            filtered_data = filtered_data[filtered_data['DayOfWeek'] == config['day']]
        
        # Display filter summary with statistics
        total_hours_original = len(data_content)
        total_hours_filtered = len(filtered_data)
        filter_percentage = (total_hours_filtered / total_hours_original * 100) if total_hours_original > 0 else 0
        
        # Calculate some statistics on filtered data
        avg_price_filtered = filtered_data['Prix'].mean()
        min_price_filtered = filtered_data['Prix'].min()
        max_price_filtered = filtered_data['Prix'].max()
        
        col_stat1, col_stat2, col_stat3, col_stat4, col_stat5, col_stat6 = st.columns(6)
        with col_stat1:
            st.metric("Filtered Hours", f"{total_hours_filtered:,}",
                     delta=f"{filter_percentage:.1f}% of total")
        with col_stat2:
            month_info = "All months" if len(config['months']) > 1 else (config['months'][0] if config['months'] else "None")
            st.metric("Month Filter", month_info)
        with col_stat3:
            day_info = config['day'] if config['day'] else "All days"
            st.metric("Day Filter", day_info)
        with col_stat4:
            st.metric("Avg Price", f"{avg_price_filtered:.1f} €/MWh")
        with col_stat5:
            st.metric("Min Price", f"{min_price_filtered:.1f} €/MWh")
        with col_stat6:
            st.metric("Max Price", f"{max_price_filtered:.1f} €/MWh")
        
        if total_hours_filtered == 0:
            st.error("❌ No data matches the selected filters. Please adjust your filter criteria.")
            return
        
        if total_hours_filtered < 8760:
            st.warning(f"⚠️ Note: Using {total_hours_filtered:,} hours (< 1 year). Results may not represent full annual performance.")
        
        # Update data_content to use filtered data for the rest of the analysis
        data_content = filtered_data
    else:
        # Use original data by default
        filtered_data = data_content
    
    # Configuration section - make it hideable with expander - MOVED BEFORE CHART
    with st.expander("⚙️ Battery Configuration & Operational Time Windows", expanded=False):
        # Configuration in columns
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("⚙️ Battery Configuration")
            
            if 'battery_cost_per_mwh' not in st.session_state:
                st.session_state.battery_cost_per_mwh = DEFAULT_BATTERY_COST_EUR_PER_MWH
            
            # Calculate default capacity based on electrolyser power and PV window
            # Capacity = Power * Duration
            default_pv_duration = DEFAULT_TIME_WINDOWS['pv_charge_end'] - DEFAULT_TIME_WINDOWS['pv_charge_start']
            default_capacity = float(electrolyser_power * default_pv_duration)
            
            # Battery parameters with session state keys
            st.number_input(
                "Energy Capacity (MWh)", 
                min_value=1.0, max_value=50.0, value=default_capacity, step=0.5,
                help=f"Maximum battery energy storage capacity (Default: {electrolyser_power} MW × {default_pv_duration}h = {default_capacity} MWh)",
                key='bat_capacity'
            )
            
            st.number_input(
                "Charge Power (MW)", 
                min_value=0.5, max_value=25.0, value=float(electrolyser_power), step=0.5,
                help="Maximum charging power (default: electrolyser power)",
                key='bat_charge_power'
            )
            
            st.number_input(
                "Discharge Power (MW)", 
                min_value=0.5, max_value=25.0, value=float(electrolyser_power), step=0.5,
                help="Maximum discharging power (default: electrolyser power)",
                key='bat_discharge_power'
            )
            
            st.slider(
                "Round-trip Efficiency", 
                min_value=0.80, max_value=1.00, value=float(DEFAULT_BATTERY_PARAMS['eta_rt']), step=0.01,
                help="Battery round-trip efficiency",
                key='bat_efficiency'
            )
            
            st.slider(
                "Max Depth of Discharge", 
                min_value=0.80, max_value=1.00, value=float(DEFAULT_BATTERY_PARAMS['DoD_max']), step=0.05,
                key='bat_dod',
                on_change=reset_optimization
            )
            
            # Financial parameters for LCOS
            st.markdown("##### 💰 Financial Baseline Parameters")
            
            col_fin1, col_fin2 = st.columns(2)
            with col_fin1:
                capex_mwh = st.number_input(
                    "CAPEX (€/MWh)", 
                    min_value=50000, max_value=500000, value=int(DEFAULT_FINANCIAL_PARAMS['capex_per_mwh']), step=5000,
                    help="Capital expenditure per MWh of capacity",
                    key='bat_capex_mwh',
                    on_change=reset_optimization
                )
                discount_rate = st.slider(
                    "Discount Rate (%)", 
                    min_value=0.0, max_value=20.0, value=float(DEFAULT_FINANCIAL_PARAMS['discount_rate'] * 100), step=0.5,
                    help="Weighted Average Cost of Capital (WACC)",
                    key='bat_discount_rate_pct',
                    on_change=reset_optimization
                ) / 100.0
            
            with col_fin2:
                lifetime_years = st.number_input(
                    "Project Lifetime (Years)", 
                    min_value=5, max_value=30, value=int(DEFAULT_FINANCIAL_PARAMS['project_lifetime_years']), step=1,
                    help="Duration of the project for amortization",
                    key='bat_lifetime',
                    on_change=reset_optimization
                )
                opex_pct = st.slider(
                    "Annual OPEX (% of CAPEX)", 
                    min_value=0.0, max_value=5.0, value=float(DEFAULT_FINANCIAL_PARAMS['opex_percent_capex'] * 100), step=0.1,
                    help="Fixed annual operating expenses",
                    key='bat_opex_pct',
                    on_change=reset_optimization
                ) / 100.0
            
            cycles_per_year = st.number_input(
                "Expected Cycles per Year", 
                min_value=50, max_value=500, value=int(DEFAULT_FINANCIAL_PARAMS['cycles_per_year']), step=1,
                help="Assumed number of full discharge cycles per year for baseline LCOS",
                key='bat_cycles_per_year',
                on_change=reset_optimization
            )

            # Build financial params dict
            fin_params = {
                'capex_per_mwh': capex_mwh,
                'discount_rate': discount_rate,
                'project_lifetime_years': lifetime_years,
                'opex_percent_capex': opex_pct,
                'cycles_per_year': cycles_per_year
            }

            # Dynamically calculate LCOS based on user inputs
            temp_params = DEFAULT_BATTERY_PARAMS.copy()
            temp_params['E_bat_max'] = st.session_state.get('bat_capacity', float(DEFAULT_BATTERY_PARAMS['E_bat_max']))
            temp_params['eta_rt'] = st.session_state.get('bat_efficiency', float(DEFAULT_BATTERY_PARAMS['eta_rt']))
            lcos_live = calculate_bess_lcos(temp_params, fin_params=fin_params)
            
            st.markdown("---")
            st.markdown("##### 📈 Levelized Cost of Storage (LCOS)")
            st.metric(
                label="LCOS per MWh delivered", 
                value=f"{lcos_live['lcos_per_mwh']:,.1f} €/MWh",
                help=f"Calculated rigorously from CAPEX, representing the baseline cost."
            )
            st.metric(
                label="Cost per Daily Cycle", 
                value=f"{lcos_live['cost_per_cycle']:,.1f} €/day",
                help="The cost of one full battery charge/discharge cycle per day."
            )
            st.markdown("---")
            
            # Electrolyser parameters (from main dashboard)
            st.subheader("⚡ Electrolyser")
            st.info(f"Using electrolyser power from main config: **{electrolyser_power:.1f} MW**")
        
        with col2:
            st.subheader("⏰ Operational Time Windows")
            st.markdown("*Configure time windows for each operational mode (24-hour format)*")
            
            # Use tabs for time windows - all bound to session state
            tw_tab1, tw_tab2, tw_tab3, tw_tab4 = st.tabs([
                "🌞 PV Charging", "💰 Sell to grid", "⚡ Grid Charging", "🔋 Supply to Electrolyser"
            ])
            
            with tw_tab1:
                col_a, col_b = st.columns(2)
                with col_a:
                    st.number_input(
                        "Start Hour", 0, 23, DEFAULT_TIME_WINDOWS['pv_charge_start'], 1, key='pv_start',
                        help="PV charging window start (e.g., 10 = 10:00)"
                    )
                with col_b:
                    st.number_input(
                        "End Hour", 0, 23, DEFAULT_TIME_WINDOWS['pv_charge_end'], 1, key='pv_end',
                        help="PV charging window end"
                    )
                st.caption("All PV production charges the battery. Excess PV is curtailed.")
            
            with tw_tab2:
                col_a, col_b = st.columns(2)
                with col_a:
                    st.number_input(
                        "Start Hour", 0, 23, DEFAULT_TIME_WINDOWS['sell_to_grid_start'], 1, key='arb_start',
                        help="Arbitrage discharge start"
                    )
                with col_b:
                    st.number_input(
                        "End Hour", 0, 23, DEFAULT_TIME_WINDOWS['sell_to_grid_end'], 1, key='arb_end',
                        help="Arbitrage discharge end"
                    )
                st.caption("Sell stored battery energy to the grid at high prices.")
            
            with tw_tab3:
                col_a, col_b = st.columns(2)
                with col_a:
                    st.number_input(
                        "Start Hour", 0, 23, DEFAULT_TIME_WINDOWS['grid_charging_start'], 1, key='night_start',
                        help="Night charging window start"
                    )
                with col_b:
                    st.number_input(
                        "End Hour", 0, 23, DEFAULT_TIME_WINDOWS['grid_charging_end'], 1, key='night_end',
                        help="Night charging window end (can be < start for midnight wrap)"
                    )
                
                st.caption("Buy from grid during low prices (can wrap midnight: 23-04 means 23:00-04:00).")
            
            with tw_tab4:
                col_a, col_b = st.columns(2)
                with col_a:
                    st.number_input(
                        "Start Hour", 0, 23, DEFAULT_TIME_WINDOWS['electrolyser_start'], 1, key='ely_start',
                        help="Electrolyser supply window start"
                    )
                with col_b:
                    st.number_input(
                        "End Hour", 0, 23, DEFAULT_TIME_WINDOWS['electrolyser_end'], 1, key='ely_end',
                        help="Electrolyser supply window end"
                    )
                st.caption("Discharge battery to supply the electrolyser.")
    
    # Create price distribution by hour scatter plot
    fig_price_hour, ax_price = plt.subplots(figsize=(14, 6))
    
    # Add shaded regions for operational time windows (behind the data)
    # Get time windows from session state or use defaults (configured to avoid overlap)
    pv_start = st.session_state.get('pv_start', DEFAULT_TIME_WINDOWS['pv_charge_start'])
    pv_end = st.session_state.get('pv_end', DEFAULT_TIME_WINDOWS['pv_charge_end'])
    arb_start = st.session_state.get('arb_start', DEFAULT_TIME_WINDOWS['sell_to_grid_start'])
    arb_end = st.session_state.get('arb_end', DEFAULT_TIME_WINDOWS['sell_to_grid_end'])
    night_start = st.session_state.get('night_start', DEFAULT_TIME_WINDOWS['grid_charging_start'])
    night_end = st.session_state.get('night_end', DEFAULT_TIME_WINDOWS['grid_charging_end'])
    ely_start = st.session_state.get('ely_start', DEFAULT_TIME_WINDOWS['electrolyser_start'])
    ely_end = st.session_state.get('ely_end', DEFAULT_TIME_WINDOWS['electrolyser_end'])
    
    # PV Charging window [start, end] inclusive -> shade [start-0.5, end+0.5]
    ax_price.axvspan(pv_start - 0.5, pv_end + 0.5, alpha=0.15, color='gold', zorder=1)
    
    # Sell to grid (Arbitrage) window [start, end] inclusive
    ax_price.axvspan(arb_start - 0.5, arb_end + 0.5, alpha=0.15, color='green', zorder=1)
    
    # Buy from grid (Night/Spot Charging) window - may wrap around midnight
    if night_start > night_end:
        # Wraps around midnight (e.g., 23-04)
        # Shade from start-0.5 to 23.5 (end of hour 23)
        ax_price.axvspan(night_start - 0.5, 23.5 + 0.5, alpha=0.15, color='red', zorder=1) # Covers start to 23
        # Shade from -0.5 (start of hour 0) to end+0.5
        ax_price.axvspan(-0.5, night_end + 0.5, alpha=0.15, color='red', zorder=1)
    else:
        # Same day
        ax_price.axvspan(night_start - 0.5, night_end + 0.5, alpha=0.15, color='red', zorder=1)
    
    # Supply to Electrolyser window
    ax_price.axvspan(ely_start - 0.5, ely_end + 0.5, alpha=0.15, color='purple', zorder=1)
    
    # Prepare data for scatter plot by hour
    means = []
    medians = []
    colors_gradient = plt.cm.RdYlGn_r(np.linspace(0.2, 0.8, 24))
    
    for hour in range(24):
        hour_data = data_content[data_content['Heure'] == hour]['Prix']
        if len(hour_data) > 0:
            # Add jitter to x-coordinates to avoid overlapping points
            x_positions = np.random.normal(hour, 0.15, size=len(hour_data))
            
            # Calculate mean for color coding
            mean_val = np.mean(hour_data)
            means.append(mean_val)
            medians.append(np.median(hour_data))
            
            # Scatter plot for this hour
            ax_price.scatter(x_positions, hour_data, alpha=0.3, s=10, 
                           color='steelblue', edgecolors='none', zorder=2)
    
    # Color-code the average line by price level
    sorted_means = sorted(means)
    colors_for_means = []
    for mean_val in means:
        rank = sorted_means.index(mean_val)
        color_idx = int((rank / len(sorted_means)) * 23)
        colors_for_means.append(colors_gradient[color_idx])
    
    # Plot mean line with color-coded segments
    for i in range(len(means)):
        if i < len(means) - 1:
            ax_price.plot([i, i+1], [means[i], means[i+1]], 
                         color=colors_for_means[i], linewidth=3, zorder=3)
    # Add marker for means
    ax_price.scatter(range(24), means, color=colors_for_means, s=100, 
                    edgecolors='black', linewidths=1.5, zorder=4, 
                    marker='o', label='Mean Price')
    
    # Plot median line
    ax_price.plot(range(24), medians, color='red', linewidth=2, 
                 linestyle='--', marker='s', markersize=6, 
                 label='Median Price', zorder=3)
    
    # Set x-axis ticks and labels
    ax_price.set_xticks(range(24))
    ax_price.set_xticklabels([f'{h:02d}h' for h in range(24)], rotation=0)
    ax_price.set_xlim(-0.5, 23.5)
    
    ax_price.set_xlabel('Hour of Day', fontsize=12, fontweight='bold')
    ax_price.set_ylabel('Spot Price (€/MWh)', fontsize=12, fontweight='bold')
    n_data_points = len(data_content)
    title = f'Electricity Spot Price Distribution by Hour and Operational Windows\nElectrolyser Power: {electrolyser_power:.1f} MW | Data Points: {n_data_points:,}'
    ax_price.set_title(title, fontsize=14, fontweight='bold')
    ax_price.grid(True, alpha=0.3, axis='y')
    ax_price.legend(loc='upper left', fontsize=9)
    
    # Add text labels for each time slot - dynamically positioned based on time windows
    y_max = ax_price.get_ylim()[1]
    text_y_position = y_max * 0.95  # Position text at 95% of max y value
    
    # Buy from grid - center in the night window
    if night_start > night_end:
        # Wraps around midnight - center between midnight and morning
        night_center = (night_end + 1) / 2
    else:
        night_center = (night_start + night_end + 1) / 2
    ax_price.text(night_center, text_y_position, 'Grid Charging',
                 ha='center', va='top', fontsize=10, fontweight='bold',
                 color='darkred', bbox=dict(boxstyle='round,pad=0.5', 
                 facecolor='white', edgecolor='darkred', alpha=0.8), zorder=5)
    
    # Supply to Electrolyser - center in electrolyser window
    ely_center = (ely_start + ely_end + 1) / 2
    ax_price.text(ely_center, text_y_position, 'Supply to\nElectrolyser', 
                 ha='center', va='top', fontsize=10, fontweight='bold',
                 color='purple', bbox=dict(boxstyle='round,pad=0.5', 
                 facecolor='white', edgecolor='purple', alpha=0.8), zorder=5)
    
    # PV Charging - center in PV window
    pv_center = (pv_start + pv_end + 1) / 2
    ax_price.text(pv_center, text_y_position, 'PV Charging', 
                 ha='center', va='top', fontsize=10, fontweight='bold',
                 color='darkgoldenrod', bbox=dict(boxstyle='round,pad=0.5', 
                 facecolor='white', edgecolor='darkgoldenrod', alpha=0.8), zorder=5)
    
    # Sell to grid - center in arbitrage window
    arb_center = (arb_start + arb_end + 1) / 2
    ax_price.text(arb_center, text_y_position, 'Sell to grid', 
                 ha='center', va='top', fontsize=10, fontweight='bold',
                 color='darkgreen', bbox=dict(boxstyle='round,pad=0.5', 
                 facecolor='white', edgecolor='darkgreen', alpha=0.8), zorder=5)
    
    # Add statistics box
    avg_price = data_content['Prix'].mean()
    min_price = data_content['Prix'].min()
    max_price = data_content['Prix'].max()
    stats_text = f'Dataset Statistics:\n'
    stats_text += f'Avg: {avg_price:.1f} €/MWh\n'
    stats_text += f'Min: {min_price:.1f} €/MWh\n'
    stats_text += f'Max: {max_price:.1f} €/MWh'
    ax_price.text(0.98, 0.97, stats_text, transform=ax_price.transAxes,
                 verticalalignment='top', horizontalalignment='right',
                 bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
                 fontsize=9)
    
    plt.tight_layout()
    st.pyplot(fig_price_hour)
    plt.close(fig_price_hour)
    
    # Auto-run optimization on page load
    if 'battery_optimization_run' not in st.session_state:
        st.session_state['battery_optimization_run'] = False
    
    # Auto-run on first load
    if not st.session_state.get('battery_optimization_run', False):
        # Build configuration from session state
        battery_params = DEFAULT_BATTERY_PARAMS.copy()
        battery_params['E_bat_max'] = st.session_state.get('bat_capacity', float(DEFAULT_BATTERY_PARAMS['E_bat_max']))
        battery_params['P_charge_max'] = st.session_state.get('bat_charge_power', float(DEFAULT_BATTERY_PARAMS['P_charge_max']))
        battery_params['P_discharge_max'] = st.session_state.get('bat_discharge_power', float(DEFAULT_BATTERY_PARAMS['P_discharge_max']))
        battery_params['eta_rt'] = st.session_state.get('bat_efficiency', float(DEFAULT_BATTERY_PARAMS['eta_rt']))
        battery_params['eta_charge'] = np.sqrt(battery_params['eta_rt'])
        battery_params['eta_discharge'] = np.sqrt(battery_params['eta_rt'])
        battery_params['DoD_max'] = st.session_state.get('bat_dod', float(DEFAULT_BATTERY_PARAMS['DoD_max']))
        battery_params['cost_per_mwh'] = st.session_state.get('battery_cost_per_mwh', DEFAULT_BATTERY_COST_EUR_PER_MWH)
        
        time_windows = DEFAULT_TIME_WINDOWS.copy()
        time_windows['pv_charge_start'] = st.session_state.get('pv_start', DEFAULT_TIME_WINDOWS['pv_charge_start'])
        time_windows['pv_charge_end'] = st.session_state.get('pv_end', DEFAULT_TIME_WINDOWS['pv_charge_end'])
        time_windows['sell_to_grid_start'] = st.session_state.get('arb_start', DEFAULT_TIME_WINDOWS['sell_to_grid_start'])
        time_windows['sell_to_grid_end'] = st.session_state.get('arb_end', DEFAULT_TIME_WINDOWS['sell_to_grid_end'])
        time_windows['grid_charging_start'] = st.session_state.get('night_start', DEFAULT_TIME_WINDOWS['grid_charging_start'])
        time_windows['grid_charging_end'] = st.session_state.get('night_end', DEFAULT_TIME_WINDOWS['grid_charging_end'])
        time_windows['electrolyser_start'] = st.session_state.get('ely_start', DEFAULT_TIME_WINDOWS['electrolyser_start'])
        time_windows['electrolyser_end'] = st.session_state.get('ely_end', DEFAULT_TIME_WINDOWS['electrolyser_end'])
        
        electrolyser_params = DEFAULT_ELECTROLYSER_PARAMS.copy()
        electrolyser_params['P_ely'] = electrolyser_power
        
        # Validate time windows
        is_valid, validation_msg = validate_time_windows(time_windows)
        if not is_valid:
            st.error(f"⚠️ Time window configuration issue: {validation_msg}")
            st.stop()
        
        with st.spinner("Running battery optimization..."):
            # Use existing columns from CSV data
            spot_prices = data_content['Prix'].values
            
            # Generate realistic PV profile using PVGIS data
            pv_profile = None
            pv_params = st.session_state.get('pv_params', None)
            use_real_pv = False
            
            # Check if PV parameters are available and valid
            if pv_params is not None:
                # Validate required PV parameters
                    try:
                        # Extract years from data for PVGIS query
                        available_years = sorted(data_content['Annee'].unique())
                        startyear = int(min(available_years)) if available_years else 2020
                        endyear = int(max(available_years)) if available_years else 2024
                        
                        # Prepare PV parameters for load_pv_profile
                        pv_params_dict = {
                            'pv_surface_hectares': pv_params.get('pv_surface_hectares'),
                            'power_density_mwp_per_ha': pv_params.get('power_density_mwp_per_ha'),
                            'lat': pv_params.get('lat'),
                            'lon': pv_params.get('lon'),
                            'loss': pv_params.get('loss', 14)
                        }
                        
                        # Validate parameter values
                        if not all(isinstance(pv_params_dict[k], (int, float)) and pv_params_dict[k] > 0 
                                  for k in ['pv_surface_hectares', 'power_density_mwp_per_ha', 'lat', 'lon']):
                            raise ValueError("Invalid PV parameter values")
                        
                        # Generate realistic PV profile from PVGIS
                        with st.spinner(f"🌞 Fetching real PV data from PVGIS (years {startyear}-{endyear})..."):
                            data_content = load_pv_profile(
                                data_content=data_content,
                                pv_params=pv_params_dict,
                                startyear=startyear,
                                endyear=endyear
                            )
                        
                        print('Total PV production:', data_content['PV_MW'].sum())
                        print(data_content[['Date', 'Heure','Mois','Jours','PV_MW']][:24])

                        pv_profile = data_content['PV_MW'].values

                        # Validate PV profile
                        if pv_profile is None or len(pv_profile) == 0:
                            raise ValueError("PV profile is empty")
                        
                        # Check if profile has variation (not constant)
                        unique_values = len(np.unique(pv_profile))
                        pv_min = pv_profile.min()
                        pv_max = pv_profile.max()
                        pv_mean = pv_profile.mean()
                        
                        if unique_values == 1:
                            st.warning(f"⚠️ PV profile appears constant ({pv_mean:.2f} MW). This may indicate an issue with PVGIS data.")
                        else:
                            use_real_pv = True
                            st.success(f"✅ Real PV data loaded: {len(pv_profile)} hours, {unique_values} unique values")
                            st.info(f"📊 PV Profile range: {pv_min:.2f} - {pv_max:.2f} MW (avg: {pv_mean:.2f} MW, total: {pv_profile.sum():.1f} MWh)")
                            
                    except Exception as e:
                        import traceback
                        error_details = traceback.format_exc()
                        st.error(f"❌ Error generating real PV profile from PVGIS: {str(e)}")
                        with st.expander("🔍 Error details"):
                            st.code(error_details)
                        st.warning("⚠️ Falling back to typical (constant) PV profile...")
            else:
                # Fallback to typical profile if PV params not available
                st.warning("⚠️ PV parameters not available in session state. Using typical (constant) PV profile.")
                st.info("💡 Tip: Configure PV installation parameters in the main dashboard to use real PV data.")
            # Store flag indicating if real PV data was used
            st.session_state['battery_used_real_pv'] = use_real_pv
            
            # Create optimizer
            optimizer = BatteryOptimizer(
                battery_params=battery_params,
                time_windows=time_windows,
                electrolyser_params=electrolyser_params,
                pv_price=pv_price
            )

            hours_of_day = data_content['Heure'].values
            
            # Run simulation with hours instead of timestamps
            df_results, summary = optimizer.simulate_year(pv_profile, spot_prices, hours_of_day)
            #print("simulation is run")
            #print('PV profile:', pv_profile)
            # Store results in session state
            st.session_state['battery_results'] = df_results
            st.session_state['battery_summary'] = summary
            st.session_state['battery_params'] = battery_params
            st.session_state['battery_time_windows'] = time_windows
            st.session_state['battery_optimization_run'] = True
    
    # Display results only if optimization has been run
    if st.session_state.get('battery_optimization_run', False) and 'battery_results' in st.session_state:
        df_results = st.session_state['battery_results']
        summary = st.session_state['battery_summary']
        battery_params = st.session_state['battery_params']
        time_windows = st.session_state['battery_time_windows']
        
        # Show PV data source indicator
        used_real_pv = st.session_state.get('battery_used_real_pv', False)
        if used_real_pv:
            st.success("✅ Using **real PV production data** from PVGIS (location-specific, hourly variation)")
        else:
            st.warning("⚠️ Using **typical (constant) PV profile**. Configure PV parameters in main dashboard for real data.")
        
        # Detailed results tabs
        st.markdown("---")
        res_tab4, res_tab1, res_tab5 = st.tabs([
            "📊 Op. Windows",
            "📈 SoC & Power Flows",
            "📋 Summary"
        ])
        
        with res_tab1:
            st.markdown("#### Battery State of Charge")
            week_selector = st.slider("View Week (starting day)", 0, 358, 0, 7, key='battery_week')
            
            # Simple SoC plot without timestamps
            st.markdown("##### SoC Profile")
            fig_soc_simple, ax = plt.subplots(figsize=(14, 6))
            
            start_idx = week_selector * 24
            end_idx = min(start_idx + 7 * 24, len(df_results))
            df_window = df_results.iloc[start_idx:end_idx]
            
            ax.plot(range(len(df_window)), df_window['soc'] * 100, linewidth=2, color='blue', label='SoC')
            ax.axhline(y=battery_params['SoC_min'] * 100, color='red', linestyle='--', label='Min SoC')
            ax.axhline(y=battery_params['SoC_max'] * 100, color='green', linestyle='--', label='Max SoC')
            ax.set_xlabel('Hour', fontweight='bold')
            ax.set_ylabel('State of Charge (%)', fontweight='bold')
            n_data_points = len(df_results)
            service_ratio_pct = avg_service_ratio * 100
            title = f'Battery SoC Profile (Days {week_selector} to {week_selector + 7})\nElectrolyser Power: {electrolyser_power:.1f} MW | Service Ratio: {service_ratio_pct:.1f}% | Data Points: {n_data_points:,}'
            ax.set_title(title, fontweight='bold')
            ax.grid(True, alpha=0.3)
            ax.legend()
            ax.set_ylim(0, 105)
            plt.tight_layout()
            st.pyplot(fig_soc_simple)
            plt.close(fig_soc_simple)
            
            st.markdown("#### Power Flows")
            fig_power_simple, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)
            
            # Charging/Discharging
            # Reconstruct separate flows for plotting
            pv_charge = df_window.apply(lambda x: x['battery_charge_mw'] if x['window_type'] == 'pv_charge' else 0, axis=1)
            grid_charge = df_window.apply(lambda x: x['battery_charge_mw'] if x['window_type'] == 'grid_charging' else 0, axis=1)
            grid_discharge = df_window.apply(lambda x: x['battery_discharge_mw'] if x['window_type'] == 'sell_to_grid' else 0, axis=1)
            ely_discharge = df_window.apply(lambda x: x['battery_discharge_mw'] if x['window_type'] == 'electrolyser' else 0, axis=1)

            axes[0].fill_between(range(len(df_window)), 0, pv_charge, 
                                color='gold', alpha=0.7, label='PV to Battery')
            axes[0].fill_between(range(len(df_window)), 0, grid_charge, 
                                color='green', alpha=0.7, label='Grid to Battery')
            axes[0].fill_between(range(len(df_window)), 0, -grid_discharge, 
                                color='blue', alpha=0.7, label='Battery to Grid')
            axes[0].set_ylabel('Power (MW)', fontweight='bold')
            n_data_points = len(df_results)
            service_ratio_pct = avg_service_ratio * 100
            title_base = f'Electrolyser Power: {electrolyser_power:.1f} MW | Service Ratio: {service_ratio_pct:.1f}% | Data Points: {n_data_points:,}'
            axes[0].set_title(f'Battery Charging/Discharging\n{title_base}', fontweight='bold')
            axes[0].legend()
            axes[0].grid(True, alpha=0.3)
            
            # Electrolyser
            axes[1].fill_between(range(len(df_window)), 0, ely_discharge, 
                                color='purple', alpha=0.7, label='Battery to Electrolyser')
            axes[1].fill_between(range(len(df_window)), 0, -df_window['ely_shortage_mw'], 
                                color='red', alpha=0.5, label='Shortage')
            axes[1].set_ylabel('Power (MW)', fontweight='bold')
            axes[1].set_title(f'Electrolyser Supply\n{title_base}', fontweight='bold')
            axes[1].legend()
            axes[1].grid(True, alpha=0.3)
            
            # PV
            axes[2].fill_between(range(len(df_window)), 0, df_window['pv_profile_mw'], 
                                color='orange', alpha=0.5, label='PV Production')
            axes[2].set_xlabel('Hour', fontweight='bold')
            axes[2].set_ylabel('Power (MW)', fontweight='bold')
            axes[2].set_title(f'PV Production\n{title_base}', fontweight='bold')
            axes[2].legend()
            axes[2].grid(True, alpha=0.3)
            
            plt.tight_layout()
            st.pyplot(fig_power_simple)
            plt.close(fig_power_simple)
            
            # Cumulative Hourly PV Production
            st.markdown("#### Cumulative Hourly PV Production")
            st.markdown("Total PV production aggregated by hour of day across the entire year")
            
            # Group by hour of day and sum PV production
            df_results['hour_of_day'] = df_results['hour_of_day'].astype(int)
            hourly_pv_cumulative = df_results.groupby('hour_of_day')['pv_profile_mw'].sum().reset_index()
            hourly_pv_cumulative.columns = ['hour', 'cumulative_pv_mwh']
            
            # Create barplot
            fig_pv_cumulative, ax = plt.subplots(figsize=(14, 6))
            bars = ax.bar(hourly_pv_cumulative['hour'], hourly_pv_cumulative['cumulative_pv_mwh'], 
                         color='orange', alpha=0.7, edgecolor='darkorange', linewidth=1.5)
            
            # Add value labels on top of bars
            for bar in bars:
                height = bar.get_height()
                if height > 0:
                    ax.text(bar.get_x() + bar.get_width()/2., height,
                           f'{height:.4f}',
                           ha='center', va='bottom', fontsize=9, fontweight='bold')
            
            ax.set_xlabel('Hour of Day', fontweight='bold', fontsize=12)
            ax.set_ylabel('Cumulative PV Production (MWh)', fontweight='bold', fontsize=12)
            ax.set_title('Cumulative Hourly PV Production (Total across entire year)', 
                        fontweight='bold', fontsize=14)
            ax.set_xticks(range(24))
            ax.set_xticklabels([f'{h:02d}:00' for h in range(24)], rotation=45, ha='right')
            ax.grid(True, alpha=0.3, axis='y')
            ax.set_axisbelow(True)
            
            # Add summary statistics
            total_pv = hourly_pv_cumulative['cumulative_pv_mwh'].sum()
            max_hour = hourly_pv_cumulative.loc[hourly_pv_cumulative['cumulative_pv_mwh'].idxmax(), 'hour']
            max_value = hourly_pv_cumulative['cumulative_pv_mwh'].max()
            
            # Add text box with statistics
            stats_text = f'Total: {total_pv:,.4f} MWh/year\nPeak Hour: {max_hour:02d}:00 ({max_value:,.4f} MWh)'
            ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
                   fontsize=10, verticalalignment='top',
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
            
            plt.tight_layout()
            st.pyplot(fig_pv_cumulative)
            plt.close(fig_pv_cumulative)
        
        with res_tab4:
            
            # Window name mapping (no explicit idle window)
            window_map = {
                'pv_charge': 'PV Charging',
                'sell_to_grid': 'Sell to Grid',
                'grid_charging': 'Grid Charging',
                'electrolyser': 'Supply to Electrolyser',
                'idle': None  # treat idle as undefined for this analysis
            }
            
            # Create working dataframe and drop idle/undefined windows
            df_win = df_results.copy()
            df_win['window_name'] = df_win['window_type'].map(window_map)
            #print(df_win[['battery_available_mwh', 'battery_charge_mw', 'battery_discharge_mw', 'spot_price_eur_mwh', 'net_cashflow', 'window_type']])
            df_win = df_win[df_win['window_name'].notna()]
            
            # Calculate 'Value' of Electrolyser supply (Avoided Grid Cost)
            # Value = Energy supplied * Spot Price at that hour
            # Only counts when window is 'electrolyser'
            df_win['ely_value_eur'] = df_win.apply(
                lambda x: x['battery_discharge_mw'] * x['spot_price_eur_mwh'] if x['window_type'] == 'electrolyser' else 0, 
                axis=1
            )
            
            # For simplicity, treat PV charging energy as having a cost equal to spot price
            # This approximates the case where the electrolyser effectively uses grid-priced power
            # UPDATE: PV Charging cost is now fixed by PV Price (€/MWh)
            df_win['pv_cost_eur'] = df_win.apply(
                lambda x: x['battery_charge_mw'] * pv_price if x['window_type'] == 'pv_charge' else 0,
                axis=1
            )
            
            # Group statistics
            # Note: since we group by window_name, we can just sum charge/discharge columns
            # The window name ensures we are summing the right type of flow
            win_stats = df_win.groupby('window_name').agg({
                'battery_charge_mw': 'sum',       # Energy In (PV or Grid)
                'battery_discharge_mw': 'sum',    # Energy Out (Grid or Ely)
                'revenue_arbitrage': 'sum',       # Revenue
                'cost_charging': 'sum',           # Cost
                'cost_penalties': 'sum',          # Penalties
                'pv_cost_eur': 'sum',             # PV charging valued at spot price
                'ely_value_eur': 'sum'            # Compensation Value
            })
            
            # Rename columns to match expected structure for readability
            # Note: This is a bit of a hack, but maps the generic columns to specific ones based on the row (window)
            # But simpler is just to rely on the row index.
            
            # Ensure specific order of windows (no Idle)
            order = ['PV Charging', 'Sell to Grid', 'Grid Charging', 'Supply to Electrolyser']
            win_stats = win_stats.reindex([w for w in order if w in win_stats.index]).fillna(0)
            
            # --- Chart 1: Hourly Power Consumption Cost Analysis ---
            st.markdown("##### 📉 Hourly Cash Flows")
            
            # Prepare hourly data
            df_hourly_cost = df_results.copy()
            
            # Calculate costs based on window type
            df_hourly_cost['grid_charge_cost'] = df_hourly_cost.apply(
                lambda x: x['battery_charge_mw'] * x['spot_price_eur_mwh'] if x['window_type'] == 'grid_charging' else 0, axis=1
            )
            
            # Split arbitrage revenue by operation window
            # We only expect revenue in the arbitrage discharge window, but let's be generic
            # We want to see the revenue/cost impact of "Selling to Grid" specifically
            # Since 'battery_discharge_mw' generates revenue in arbitrage window
            df_hourly_cost['revenue_sell_to_grid'] = df_hourly_cost.apply(
                lambda x: x['battery_discharge_mw'] * x['spot_price_eur_mwh'] if x['window_type'] == 'sell_to_grid' else 0, axis=1
            )
            
            # Supply to Electrolyser: This represents a cost savings compared to PPA
            # When battery supplies electrolyser, we avoid buying at spot price
            # The "cost impact" is: Energy supplied * (Spot Price - 0) = negative cost (savings)
            df_hourly_cost['ely_supply_savings'] = df_hourly_cost.apply(
                lambda x: x['battery_discharge_mw'] * x['spot_price_eur_mwh'] if x['window_type'] == 'electrolyser' else 0, axis=1
            )
            
            # PPA Baseline: Cost if we bought the electrolyser input energy at PPA price
            # The baseline assumes constant electrolyser operation powered by PPA
            # So we use the full electrolyser power capacity for PPA baseline calculation
            df_hourly_cost['ppa_baseline_cost'] = df_hourly_cost.apply(
                lambda x: electrolyser_power * ppa_price if ppa_price > 0 and x['spot_price_eur_mwh'] > ppa_price else 0,
                axis=1
            )
            df_hourly_cost['pv_baseline_cost'] = df_hourly_cost.apply(
                lambda x: x['battery_charge_mw'] * pv_price if x['window_type'] == 'pv_charge' else 0,
                axis=1
            )
            # Use the live rigorously evaluated LCOS value immediately
            battery_cost_per_mwh = lcos_live.get('lcos_per_mwh', 0.0)
            discharge_windows = {'sell_to_grid', 'electrolyser'}
            df_hourly_cost['battery_lcos_cost'] = df_hourly_cost.apply(
                lambda x: x['battery_discharge_mw'] * battery_cost_per_mwh if x['window_type'] in discharge_windows else 0,
                axis=1
            )
            df_hourly_cost['grid_supply_price'] = df_hourly_cost.apply(
                lambda x: x['spot_price_eur_mwh'] if (ppa_price == 0 or x['spot_price_eur_mwh'] <= ppa_price) else np.nan,
                axis=1
            )

            scaling_factor = electrolyser_power
            for col in ['grid_charge_cost', 'revenue_sell_to_grid', 'ely_supply_savings',
                        'ppa_baseline_cost', 'pv_baseline_cost', 'battery_lcos_cost', 'grid_supply_price']:
                df_hourly_cost[col] = df_hourly_cost[col] * scaling_factor
            
            df_hourly_cost['net_cashflow'] = (
                df_hourly_cost['grid_charge_cost']
                + df_hourly_cost['pv_baseline_cost']
                + df_hourly_cost['battery_lcos_cost']
                - df_hourly_cost['revenue_sell_to_grid']
                - df_hourly_cost['ely_supply_savings']
            )
            
            st.session_state['battery_cash_totals'] = {
                'grid_cost': float(df_hourly_cost['grid_charge_cost'].sum()),
                'pv_cost': float(df_hourly_cost['pv_baseline_cost'].sum()),
                'battery_cost': float(df_hourly_cost['battery_lcos_cost'].sum()),
                'ppa_cost': float(df_hourly_cost['ppa_baseline_cost'].sum()),
                'sell_revenue': float(df_hourly_cost['revenue_sell_to_grid'].sum()),
                'ely_savings': float(df_hourly_cost['ely_supply_savings'].sum()),
                'net_cashflow': float(df_hourly_cost['net_cashflow'].sum())
            }
            
            #print(df_hourly_cost.columns)
            subset_columns = ['window_type',
                                'spot_price_eur_mwh',
                                'grid_charge_cost', 'revenue_sell_to_grid',
                                'ely_supply_savings', 'ppa_baseline_cost', 'pv_baseline_cost',
                                'battery_lcos_cost', 'grid_supply_price','net_cashflow',]
            print(df_hourly_cost[subset_columns])
            # Group by hour of day
            hourly_profile = df_hourly_cost.groupby('hour_of_day').agg({
                'grid_charge_cost': 'sum',
                'revenue_sell_to_grid': 'sum',
                'ely_supply_savings': 'sum',
                'ppa_baseline_cost': 'sum',
                'pv_baseline_cost': 'sum',
                'battery_lcos_cost': 'sum'
            })
            hourly_profile['net_cashflow'] = (
                hourly_profile['grid_charge_cost']
                + hourly_profile['pv_baseline_cost']
                + hourly_profile['battery_lcos_cost']
                - hourly_profile['revenue_sell_to_grid']
                - hourly_profile['ely_supply_savings']
            )
            grid_supply_series = df_hourly_cost.groupby('hour_of_day')['grid_supply_price'].mean().dropna()
             
            #print(df_hourly_cost)

            fig_hourly_cost, ax = plt.subplots(figsize=(12, 6))
            
            # Stacked bars for System Costs
            ax.bar(hourly_profile.index, hourly_profile['grid_charge_cost'], label='Grid to Battery', color='red', alpha=0.7)
            
            # Revenue as negative bars - explicitly labeled as "Sell to Grid"
            ax.bar(hourly_profile.index, -hourly_profile['revenue_sell_to_grid'], label='Battery to Grid', color='green', alpha=0.7)
            
            # Supply to Electrolyser savings as negative bars (cost avoided)
            ax.bar(hourly_profile.index, -hourly_profile['ely_supply_savings'], label='Battery to Electrolyser', color='purple', alpha=0.7)
            
            # Add cost labels on each bar (only show if value is significant)
            for hour in hourly_profile.index:
                # Grid charging cost (at base)
                if hourly_profile.loc[hour, 'grid_charge_cost'] > 0:
                    ax.text(hour, hourly_profile.loc[hour, 'grid_charge_cost'] / 2, 
                           f"{hourly_profile.loc[hour, 'grid_charge_cost']:.0f}€", 
                           ha='center', va='center', fontsize=8, color='black', fontweight='bold')
                
                # Sell to Grid revenue (negative)
                if hourly_profile.loc[hour, 'revenue_sell_to_grid'] > 0:
                    ax.text(hour, -hourly_profile.loc[hour, 'revenue_sell_to_grid'] / 2, 
                           f"-{hourly_profile.loc[hour, 'revenue_sell_to_grid']:.0f}€", 
                           ha='center', va='center', fontsize=8, color='black', fontweight='bold')
                
                # Supply to Electrolyser savings (negative)
                if hourly_profile.loc[hour, 'ely_supply_savings'] > 0:
                    ax.text(hour, -hourly_profile.loc[hour, 'ely_supply_savings'] / 2, 
                           f"-{hourly_profile.loc[hour, 'ely_supply_savings']:.0f}€", 
                           ha='center', va='center', fontsize=8, color='black', fontweight='bold')
            
            # PPA Baseline as a line (Constant PPA supply)
            ax.plot(hourly_profile.index, hourly_profile['ppa_baseline_cost'], label=f'PPA ({ppa_price} €/MWh)', color='orange', linewidth=2, alpha=0.8, linestyle='-', marker='o')
            pv_series = hourly_profile['pv_baseline_cost'].replace(0, np.nan)
            ax.plot(hourly_profile.index, pv_series, label=f'PV LCOE ({pv_price} €/MWh)', color='gold', linewidth=1.5, alpha=0.7, linestyle='--', marker='s')
            battery_series = hourly_profile['battery_lcos_cost'].replace(0, np.nan)
            battery_label = f'Battery LCOS ({battery_cost_per_mwh:.0f} €/MWh)'
            ax.plot(hourly_profile.index, battery_series, label=battery_label, color='gray', linewidth=1.5, alpha=0.7, linestyle='-.', marker='^')
            ax.plot(grid_supply_series.index, grid_supply_series.values, label='Grid to Electrolyser', color='blue', linewidth=1.5, alpha=0.7, linestyle=':', marker='d')
            net_series = hourly_profile['net_cashflow']
            ax.plot(net_series.index, net_series.values, label='Net Cashflow', color='black', linewidth=2, alpha=0.8, linestyle='-', marker='o')
            ax.fill_between(net_series.index, 0, net_series.values, where=net_series.values>=0, color='red', alpha=0.1)
            ax.fill_between(net_series.index, 0, net_series.values, where=net_series.values<0, color='green', alpha=0.1)
            for hour, value in net_series.items():
                if value != 0:
                    va = 'bottom' if value >= 0 else 'top'
                    offset = 3 if value >= 0 else -3
                    ax.text(hour, value + offset, f"{value:,.0f}€", ha='center', va=va, fontsize=8, color='red', fontweight='bold')
            
            ax.set_xticks(range(24))
            ax.set_xlabel('Hour of Day', fontweight='bold')
            ax.set_ylabel('Total Cumulated Cost (€)', fontweight='bold')
            n_data_points = len(df_results)
            service_ratio_pct = avg_service_ratio * 100
            title = f'Hourly Cash Flows\nElectrolyser Power: {electrolyser_power:.1f} MW | Service Ratio: {service_ratio_pct:.1f}% | Data Points: {n_data_points:,}'
            ax.set_title(title, fontweight='bold')
            ax.legend()
            ax.grid(True, alpha=0.3)
            ax.axhline(0, color='black', linewidth=0.8)
            
            st.pyplot(fig_hourly_cost)
            plt.close(fig_hourly_cost)

        with res_tab5:
            st.markdown("#### Complete Summary Statistics")
            
            summary_data = {
                'Category': [
                    'Energy Flows', '', '', '', '',
                    'Economics', '', '', '',
                    'Battery', '', '', '',
                    'Electrolyser', '', ''
                ],
                'Metric': [
                    'PV Available', 'PV to Battery',
                    'Grid to Battery', 'Battery to Grid', 'Battery to Electrolyser',
                    'Revenue', 'Cost', 'Penalties', 'Net Profit',
                    'Avg SoC', 'SoC Range', 'Cycles', 'Throughput',
                    'H₂ Production', 'Capacity Factor', 'Cost per kg'
                ],
                'Value': [
                    f"{summary['total_pv_available_mwh']:.1f} MWh",
                    f"{summary['total_pv_to_battery_mwh']:.1f} MWh",
                    f"{summary['total_grid_to_battery_mwh']:.1f} MWh",
                    f"{summary['total_battery_to_grid_mwh']:.1f} MWh",
                    f"{summary['total_battery_to_ely_mwh']:.1f} MWh",
                    f"{summary['total_revenue_eur']:,.0f} €",
                    f"{summary['total_cost_eur']:,.0f} €",
                    f"{summary['total_penalties_eur']:,.0f} €",
                    f"{summary['net_profit_eur']:,.0f} €",
                    f"{summary['avg_soc']:.1%}",
                    f"{summary['min_soc']:.0%} - {summary['max_soc']:.0%}",
                    f"{summary['equivalent_cycles']:.0f}",
                    f"{summary['total_battery_to_grid_mwh'] + summary['total_battery_to_ely_mwh']:.0f} MWh",
                    f"{summary['total_h2_production_tonnes']:.1f} tonnes",
                    f"{summary['ely_capacity_factor']:.1%}",
                    f"{summary['h2_cost_eur_per_kg']:.2f} €/kg"
                ]
            }
            st.table(pd.DataFrame(summary_data))
        
        cash_totals = st.session_state.get('battery_cash_totals')
        if cash_totals:
            revenue_total = cash_totals['sell_revenue'] + cash_totals['ely_savings']
            cost_total = cash_totals['grid_cost'] + cash_totals['pv_cost'] + cash_totals['battery_cost']
            net_cash = cost_total - revenue_total
        else:
            revenue_total = summary['total_revenue_eur']
            cost_total = summary['total_cost_eur']
            net_cash = cost_total - revenue_total
        
        col_rev, col_cost, col_net = st.columns(3)
        
        def _kpi_card(label, value, color_bg, color_text, sign_prefix=""):
            st.markdown(
                f"""
                <div style="
                    border-radius:8px;
                    padding:16px;
                    background-color:{color_bg};
                    color:{color_text};
                    text-align:center;
                    font-weight:bold;
                ">
                    <div style="font-size:14px; text-transform:uppercase; letter-spacing:1px;">{label}</div>
                    <div style="font-size:24px; margin-top:6px;">{sign_prefix}{value:,.0f} €</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        
        with col_rev:
            _kpi_card("Revenue (Battery Output)", revenue_total, "#e6f4ea", "#1b4332", "+")
        
        with col_cost:
            _kpi_card("Supply Cost (Grid + PV + Battery)", cost_total, "#fdecea", "#8a1c1c", "-")
        
        with col_net:
            card_color = "#fdecea" if net_cash >= 0 else "#e6f4ea"
            card_text = "#8a1c1c" if net_cash >= 0 else "#1b4332"
            net_sign = "-" if net_cash >= 0 else "+"
            _kpi_card("Net Cashflow", abs(net_cash), card_color, card_text, net_sign)
        
        # --- Chart 3: Selected Hours & Spot Prices per Operational Window ---
        st.markdown("##### ⏰ Selected Hours and Spot Prices by Operational Window")
        df_hours = df_results[['hour_of_day', 'spot_price_eur_mwh', 'window_type']].copy()
        df_hours['window_name'] = df_hours['window_type'].map(window_map)
        df_hours = df_hours[df_hours['window_name'].notna()]

        fig_win_hours, ax = plt.subplots(figsize=(12, 4))

        colors = {
            'PV Charging': 'gold',
            'Sell to Grid': 'green',
            'Grid Charging': 'red',
            'Supply to Electrolyser': 'purple',
        }

        for w in order:
            sub = df_hours[df_hours['window_name'] == w]
            if sub.empty:
                continue
            ax.scatter(
                sub['hour_of_day'],
                sub['spot_price_eur_mwh'],
                label=w,
                alpha=0.7,
                s=25,
                color=colors.get(w, 'gray'),
                edgecolors='none'
            )

        ax.set_xticks(range(24))
        ax.set_xlabel('Hour of Day', fontweight='bold')
        ax.set_ylabel('Spot Price (€/MWh)', fontweight='bold')
        n_data_points = len(df_results)
        service_ratio_pct = avg_service_ratio * 100
        title = f'Spot Prices at Selected Hours per Operational Window\nElectrolyser Power: {electrolyser_power:.1f} MW | Service Ratio: {service_ratio_pct:.1f}% | Data Points: {n_data_points:,}'
        ax.set_title(title, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend()

        plt.tight_layout()
        st.pyplot(fig_win_hours)
        plt.close(fig_win_hours)
    
    else:
        st.info("👆 Configure battery parameters and time windows above, then click '🚀 Run Battery Optimization' to start the simulation")
