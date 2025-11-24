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
from battery_optimizer import BatteryOptimizer, distribute_monthly_pv_to_hourly_from_dataframe, generate_typical_pv_profile
from battery_visualization import (
    plot_soc_profile, plot_power_flows, plot_economics_breakdown,
    plot_yearly_cashflow, plot_hydrogen_production
)


def render_battery_arbitrage_tab(data_content, electrolyser_power, pv_energy_data, pv_price=0.0, ppa_price=0.0):
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
    
    # Add computed columns
    data_content['Week'] = data_content['Date'].dt.isocalendar().week
    data_content['DayOfWeek'] = data_content['Date'].dt.day_name()

    # Filter first week
    mask = data_content['Week'] == 1 # & data_content['Jours'] == 'Tuesday'
    data_content = data_content[mask]
    
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
    
    # Filter data to only include Tuesday
    mask = data_content['Jours'] == 'Tuesday'
    data_content = data_content[mask]
    
    # Initialize session state for filters if not exists
    if 'filter_years' not in st.session_state:
        st.session_state.filter_years = available_years
    if 'filter_months' not in st.session_state:
        st.session_state.filter_months = available_months
    if 'filter_week_enabled' not in st.session_state:
        st.session_state.filter_week_enabled = False
    if 'filter_weeks' not in st.session_state:
        st.session_state.filter_weeks = available_weeks[:4] if len(available_weeks) >= 4 else available_weeks
    if 'filter_day_enabled' not in st.session_state:
        st.session_state.filter_day_enabled = False
    if 'filter_days' not in st.session_state:
        st.session_state.filter_days = available_days
    
    # Data filtering controls - make hideable with expander
    with st.expander("🔍 Data Filters", expanded=False):
        st.markdown("Filter spot price data for analysis and optimization")
        
        # Create filter columns
        filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)
        
        with filter_col1:
            # Year filter
            st.multiselect(
                "📅 Year(s)",
                options=available_years,
                default=st.session_state.filter_years,
                help="Select one or more years to include",
                key='filter_years'
            )
        
        with filter_col2:
            # Month filter
            st.multiselect(
                "📆 Month(s)",
                options=available_months,
                default=st.session_state.filter_months,
                help="Select one or more months to include",
                key='filter_months'
            )
        
        with filter_col3:
            # Week filter (using week of year)
            st.checkbox("Filter by Week", value=st.session_state.filter_week_enabled, key='filter_week_enabled')
            if st.session_state.filter_week_enabled:
                st.multiselect(
                    "Week(s)",
                    options=available_weeks,
                    default=st.session_state.filter_weeks,
                    help="Select specific weeks (1-52)",
                    key='filter_weeks'
                )
        
        with filter_col4:
            # Day of week filter
            st.checkbox("Filter by Day of Week", value=st.session_state.filter_day_enabled, key='filter_day_enabled')
            if st.session_state.filter_day_enabled:
                st.multiselect(
                    "📅 Day(s) of Week",
                    options=available_days,
                    default=st.session_state.filter_days,
                    help="Select specific days (e.g., weekdays only)",
                    key='filter_days'
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
            st.session_state.filter_config = {
                'years': st.session_state.filter_years,
                'months': st.session_state.filter_months,
                'weeks': st.session_state.filter_weeks if st.session_state.filter_week_enabled else None,
                'week_enabled': st.session_state.filter_week_enabled,
                'days': st.session_state.filter_days if st.session_state.filter_day_enabled else None,
                'day_enabled': st.session_state.filter_day_enabled
            }
    
    # Apply filters if they have been applied at least once
    if st.session_state.filters_applied and 'filter_config' in st.session_state:
        filtered_data = data_content.copy()
        config = st.session_state.filter_config
        
        # Apply year filter
        if config['years']:
            filtered_data = filtered_data[filtered_data['Annee'].isin(config['years'])]
        
        # Apply month filter
        if config['months']:
            filtered_data = filtered_data[filtered_data['Mois'].isin(config['months'])]
        
        # Apply week filter
        if config['week_enabled'] and config['weeks']:
            filtered_data = filtered_data[filtered_data['Week'].isin(config['weeks'])]
        
        # Apply day of week filter
        if config['day_enabled'] and config['days']:
            filtered_data = filtered_data[filtered_data['DayOfWeek'].isin(config['days'])]
        
        # Display filter summary with statistics
        total_hours_original = len(data_content)
        total_hours_filtered = len(filtered_data)
        filter_percentage = (total_hours_filtered / total_hours_original * 100) if total_hours_original > 0 else 0
        
        # Calculate some statistics on filtered data
        avg_price_filtered = filtered_data['Prix'].mean()
        min_price_filtered = filtered_data['Prix'].min()
        max_price_filtered = filtered_data['Prix'].max()
        
        col_stat1, col_stat2, col_stat3, col_stat4, col_stat5 = st.columns(5)
        with col_stat1:
            st.metric("Filtered Hours", f"{total_hours_filtered:,}", 
                     delta=f"{filter_percentage:.1f}% of total")
        with col_stat2:
            st.metric("Days Selected", f"{len(config['days']) if config['day_enabled'] else 7}")
        with col_stat3:
            st.metric("Avg Price", f"{avg_price_filtered:.1f} €/MWh")
        with col_stat4:
            st.metric("Min Price", f"{min_price_filtered:.1f} €/MWh")
        with col_stat5:
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
                key='bat_dod'
            )
            
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
    ax_price.set_title('Electricity Spot Price Distribution by Hour and Operational Windows', 
                      fontsize=14, fontweight='bold')
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
            hours_of_day = data_content['Heure'].values
            
            # Use typical PV profile
            pv_profile = generate_typical_pv_profile(hours_of_day, peak_power_mw=battery_params['P_charge_max'])
            # Prepare PV profile using month names from Mois column
            # pv_profile = distribute_monthly_pv_to_hourly_from_dataframe(
            #     pv_energy_data['pv_energy_mwh'],
            #     data_content
            # )
            
            # Create optimizer
            optimizer = BatteryOptimizer(
                battery_params=battery_params,
                time_windows=time_windows,
                electrolyser_params=electrolyser_params,
                pv_price=pv_price
            )
            
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
            ax.set_title(f'Battery SoC Profile (Days {week_selector} to {week_selector + 7})', fontweight='bold')
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
            axes[0].set_title('Battery Charging/Discharging', fontweight='bold')
            axes[0].legend()
            axes[0].grid(True, alpha=0.3)
            
            # Electrolyser
            axes[1].fill_between(range(len(df_window)), 0, ely_discharge, 
                                color='purple', alpha=0.7, label='Battery to Electrolyser')
            axes[1].fill_between(range(len(df_window)), 0, -df_window['ely_shortage_mw'], 
                                color='red', alpha=0.5, label='Shortage')
            axes[1].set_ylabel('Power (MW)', fontweight='bold')
            axes[1].set_title('Electrolyser Supply', fontweight='bold')
            axes[1].legend()
            axes[1].grid(True, alpha=0.3)
            
            # PV
            axes[2].fill_between(range(len(df_window)), 0, df_window['pv_profile_mw'], 
                                color='orange', alpha=0.5, label='PV Production')
            axes[2].set_xlabel('Hour', fontweight='bold')
            axes[2].set_ylabel('Power (MW)', fontweight='bold')
            axes[2].set_title('PV Production', fontweight='bold')
            axes[2].legend()
            axes[2].grid(True, alpha=0.3)
            
            plt.tight_layout()
            st.pyplot(fig_power_simple)
            plt.close(fig_power_simple)
        
        with res_tab4:
            col_run_left, col_run_right = st.columns([1, 4])
            with col_run_left:
                if st.button("🔁 Run Simulation", key="run_simulation_operational", use_container_width=True):
                    st.session_state['battery_optimization_run'] = False
                    rerun_fn = getattr(st, "rerun", None) or getattr(st, "experimental_rerun", None)
                    if rerun_fn:
                        rerun_fn()
                    else:
                        st.warning("Cannot rerun automatically; please rerun the app manually.")
            st.markdown("#### Operational Windows Analysis")
            
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
            print(df_win[['battery_available_mwh', 'battery_charge_mw', 'battery_discharge_mw', 'spot_price_eur_mwh', 'net_cashflow', 'window_type']])
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
            st.markdown("##### 📉 Hourly Power Consumption Cost Analysis (vs PPA Baseline)")
            
            # Prepare hourly data
            df_hourly_cost = df_results.copy()
            
            # Calculate costs based on window type
            df_hourly_cost['pv_charge_cost'] = df_hourly_cost.apply(
                lambda x: x['battery_charge_mw'] * pv_price if x['window_type'] == 'pv_charge' else 0, axis=1
            )
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
            df_hourly_cost['ppa_baseline_cost'] = electrolyser_power * ppa_price
            
            # Group by hour of day
            hourly_profile = df_hourly_cost.groupby('hour_of_day').agg({
                'pv_charge_cost': 'sum',
                'grid_charge_cost': 'sum',
                'revenue_sell_to_grid': 'sum',
                'ely_supply_savings': 'sum',
                'ppa_baseline_cost': 'sum'
            })
            
            fig_hourly_cost, ax = plt.subplots(figsize=(12, 6))
            
            # Stacked bars for System Costs
            ax.bar(hourly_profile.index, hourly_profile['grid_charge_cost'], label='Grid Charging Cost', color='red', alpha=0.7)
            ax.bar(hourly_profile.index, hourly_profile['pv_charge_cost'], bottom=hourly_profile['grid_charge_cost'], label='PV Charging Cost', color='gold', alpha=0.7)
            
            # Revenue as negative bars - explicitly labeled as "Sell to Grid"
            ax.bar(hourly_profile.index, -hourly_profile['revenue_sell_to_grid'], label='Sell to Grid Revenue', color='green', alpha=0.7)
            
            # Supply to Electrolyser savings as negative bars (cost avoided)
            ax.bar(hourly_profile.index, -hourly_profile['ely_supply_savings'], label='Supply to Electrolyser', color='purple', alpha=0.7)
            
            # Add cost labels on each bar (only show if value is significant)
            for hour in hourly_profile.index:
                # Grid charging cost (at base)
                if hourly_profile.loc[hour, 'grid_charge_cost'] > 0:
                    ax.text(hour, hourly_profile.loc[hour, 'grid_charge_cost'] / 2, 
                           f"{hourly_profile.loc[hour, 'grid_charge_cost']:.0f}€", 
                           ha='center', va='center', fontsize=8, color='black', fontweight='bold')
                
                # PV charging cost (stacked on top)
                if hourly_profile.loc[hour, 'pv_charge_cost'] > 0:
                    ax.text(hour, hourly_profile.loc[hour, 'grid_charge_cost'] + hourly_profile.loc[hour, 'pv_charge_cost'] / 2, 
                           f"{hourly_profile.loc[hour, 'pv_charge_cost']:.0f}€", 
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
            ax.plot(hourly_profile.index, hourly_profile['ppa_baseline_cost'], label=f'PPA Baseline Cost (Constant {electrolyser_power}MW @ {ppa_price} €/MWh)', color='purple', linewidth=3, linestyle='-', marker='o')
            
            ax.set_xticks(range(24))
            ax.set_xlabel('Hour of Day', fontweight='bold')
            ax.set_ylabel('Total Cumulated Cost (€)', fontweight='bold')
            ax.set_title('Hourly Cash Flows', fontweight='bold')
            ax.legend()
            ax.grid(True, alpha=0.3)
            ax.axhline(0, color='black', linewidth=0.8)
            
            st.pyplot(fig_hourly_cost)
            plt.close(fig_hourly_cost)

            # --- Chart 3: Selected Hours & Spot Prices per Operational Window ---
            st.markdown("##### ⏰ Selected Hours and Spot Prices by Operational Window")
            df_hours = df_results[['hour_of_day', 'spot_price_eur_mwh', 'window_type']].copy()
            df_hours['window_name'] = df_hours['window_type'].map(window_map)
            # Drop idle/undefined windows so only true operational windows are shown
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
            ax.set_title('Spot Prices at Selected Hours per Operational Window', fontweight='bold')
            ax.grid(True, alpha=0.3)
            ax.legend()

            plt.tight_layout()
            st.pyplot(fig_win_hours)
            plt.close(fig_win_hours)


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
        
        # Key Performance Indicators - moved to bottom
        st.markdown("### 📊 Key Performance Indicators")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric(
                "Net Profit",
                f"{summary['net_profit_eur']:,.0f} €",
                delta=f"{summary['net_profit_eur']/365:.0f} €/day"
            )
        
        with col2:
            st.metric(
                "Revenue (Sell + Ely)",
                f"{summary['total_revenue_eur']:,.0f} €",
                delta=f"Sell: {summary['total_revenue_arbitrage_eur']:,.0f} €, Ely: {summary['total_ely_value_eur']:,.0f} €"
            )
        
        with col3:
            st.metric(
                "Charging Cost (Grid + PV)",
                f"{summary['total_cost_eur']:,.0f} €",
                delta=f"Grid: {summary['total_cost_charging_eur']:,.0f} €, PV: {summary['total_pv_cost_eur']:,.0f} €"
            )
        
        with col4:
            st.metric(
                "H₂ Production",
                f"{summary['total_h2_production_tonnes']:.1f} t",
                delta=f"{summary['h2_cost_eur_per_kg']:.2f} €/kg"
            )
        
        with col5:
            st.metric(
                "Battery Cycles",
                f"{summary['equivalent_cycles']:.0f}",
                delta=f"{summary['avg_soc']:.0%} avg SoC"
            )
    
    else:
        st.info("👆 Configure battery parameters and time windows above, then click '🚀 Run Battery Optimization' to start the simulation")
        
        # Show example configuration help
        with st.expander("💡 Quick Start Guide", expanded=False):
            st.markdown("""
            **Getting Started:**
            
            1. **Review Data Filters** (optional)
               - Filter by year, month, week, or day of week
               - Click '🔄 Apply Filters' to update data
            
            2. **Check Price Distribution Chart**
               - Identify peak price hours (good for discharge)
               - Identify low price hours (good for charging)
            
            3. **Configure Battery** (left column)
               - Start with defaults or adjust capacity/power
               - Set efficiency and depth of discharge
            
            4. **Set Time Windows** (right column)
               - Use default windows or customize
               - Align with your price patterns
            
            5. **Click 'Run Battery Optimization'**
               - Wait 5-30 seconds for results
               - Review KPIs and detailed analysis
            
            **Default Configuration:**
            - Battery: 10 MWh capacity, 5 MW power
            - PV Charging: 10:00-16:00
            - Arbitrage: 16:00-23:00
            - Spot Charging: 23:00-05:00
            - Electrolyser: 05:00-10:00
            """)
        
        # Show example time windows
        st.markdown("### 📋 Default Operating Strategy")
        st.markdown("""
        **1. PV Charging (10:00-16:00)**
        - All PV production charges the battery
        - Excess PV is curtailed
        
        **2. Arbitrage Discharge (16:00-23:00)**
        - Discharge to grid at maximum power
        - Sell energy at evening peak prices
        - Goal: empty battery for spot charging
        
        **3. Spot Charging (23:00-05:00)**
        - Charge from grid at spot market prices
        - Prepare battery for electrolyser operation
        
        **4. Electrolyser Operation (05:00-10:00)**
        - Battery exclusively powers electrolyser
        - No grid purchase allowed
        - Produce hydrogen for the day
        
        **Objective:** Maximize net profit = Revenue (arbitrage) - Cost (charging) - Penalties (shortages)
        """)

