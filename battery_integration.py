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
    NIGHT_CHARGE_STRATEGY, validate_time_windows
)
from battery_optimizer import BatteryOptimizer, distribute_monthly_pv_to_hourly_from_dataframe
from battery_visualization import (
    plot_soc_profile, plot_power_flows, plot_economics_breakdown,
    plot_yearly_cashflow, plot_hydrogen_production
)


def render_battery_arbitrage_tab(data_content, electrolyser_power, pv_energy_data):
    """
    Render the battery arbitrage optimization tab in the main dashboard
    
    Args:
        data_content: DataFrame with spot price data
        electrolyser_power: Electrolyser power from main dashboard (MW)
        pv_energy_data: PV energy data dict from main dashboard
    """
    st.markdown("## 🔋 Battery Energy Storage & Arbitrage Optimization")
    st.markdown("""
    Optimize battery operation with parametric time windows for:
    - PV-priority charging
    - Evening arbitrage discharge
    - Spot grid charging  
    - Morning electrolyser supply
    """)
    st.markdown("---")
    
    # Data filtering controls
    st.markdown("### 🔍 Data Filters")
    st.markdown("Filter spot price data for analysis and optimization")
    
    # Ensure Date column is datetime
    if not pd.api.types.is_datetime64_any_dtype(data_content['Date']):
        data_content['Date'] = pd.to_datetime(data_content['Date'])
    
    # Create filter columns
    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)
    
    with filter_col1:
        # Year filter
        available_years = sorted(data_content['Annee'].unique())
        selected_years = st.multiselect(
            "📅 Year(s)",
            options=available_years,
            default=available_years,
            help="Select one or more years to include"
        )
    
    with filter_col2:
        # Month filter
        month_names_short = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                            'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        available_months = sorted(data_content['Mois'].unique(), 
                                 key=lambda x: ['January', 'February', 'March', 'April', 'May', 'June',
                                               'July', 'August', 'September', 'October', 'November', 'December'].index(x))
        selected_months = st.multiselect(
            "📆 Month(s)",
            options=available_months,
            default=available_months,
            help="Select one or more months to include"
        )
    
    with filter_col3:
        # Week filter (using week of year)
        data_content['Week'] = data_content['Date'].dt.isocalendar().week
        available_weeks = sorted(data_content['Week'].unique())
        week_filter_enabled = st.checkbox("Filter by Week", value=False)
        if week_filter_enabled:
            selected_weeks = st.multiselect(
                "Week Number(s)",
                options=available_weeks,
                default=available_weeks[:4] if len(available_weeks) >= 4 else available_weeks,
                help="Select specific weeks (1-52)"
            )
        else:
            selected_weeks = available_weeks
    
    with filter_col4:
        # Day of week filter
        data_content['DayOfWeek'] = data_content['Date'].dt.day_name()
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        available_days = [day for day in day_order if day in data_content['DayOfWeek'].unique()]
        
        day_filter_enabled = st.checkbox("Filter by Day of Week", value=False)
        if day_filter_enabled:
            # Quick preset buttons
            preset_col1, preset_col2, preset_col3 = st.columns(3)
            with preset_col1:
                if st.button("🏢 Weekdays", help="Monday to Friday", key='preset_weekdays'):
                    st.session_state.day_preset = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
            with preset_col2:
                if st.button("🏖️ Weekend", help="Saturday and Sunday", key='preset_weekend'):
                    st.session_state.day_preset = ['Saturday', 'Sunday']
            with preset_col3:
                if st.button("🌐 All Days", help="All 7 days", key='preset_all'):
                    st.session_state.day_preset = available_days
            
            # Get default from preset if available
            default_days = st.session_state.get('day_preset', available_days)
            default_days = [d for d in default_days if d in available_days]
            
            selected_days = st.multiselect(
                "📅 Day(s) of Week",
                options=available_days,
                default=default_days,
                help="Select specific days (e.g., weekdays only)"
            )
        else:
            selected_days = available_days
    
    # Apply Filters Button
    st.markdown("")  # Add spacing
    apply_filters_btn = st.button("🔄 Apply Filters", type="primary", use_container_width=True, 
                                  help="Click to apply selected filters and update analysis")
    
    # Only apply filters if button was clicked or if filters were previously applied
    if 'filters_applied' not in st.session_state:
        st.session_state.filters_applied = False
    
    if apply_filters_btn:
        st.session_state.filters_applied = True
        st.session_state.filter_config = {
            'years': selected_years,
            'months': selected_months,
            'weeks': selected_weeks if week_filter_enabled else None,
            'week_enabled': week_filter_enabled,
            'days': selected_days if day_filter_enabled else None,
            'day_enabled': day_filter_enabled
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
        # Show info message when filters haven't been applied yet
        st.info("👆 Select your filter criteria above and click '🔄 Apply Filters' to update the analysis")
        # Use original data by default
        filtered_data = data_content
    
    st.markdown("---")
    
    # Price distribution analysis to help configure time windows
    st.markdown("### 📊 Spot Price Analysis by Hour (Filtered Data)")
    st.markdown("Understanding hourly price patterns helps optimize time window configuration")
    
    # Create price distribution by hour box plot
    fig_price_hour, ax_price = plt.subplots(figsize=(14, 6))
    
    # Prepare data for box plot by hour
    box_data_hour = []
    box_labels_hour = []
    for hour in range(24):
        hour_data = data_content[data_content['Heure'] == hour]['Prix']
        if len(hour_data) > 0:
            box_data_hour.append(hour_data)
            box_labels_hour.append(f'{hour:02d}h')
    
    # Create box plot
    bp = ax_price.boxplot(box_data_hour, labels=box_labels_hour, patch_artist=True,
                          showmeans=True, meanline=True,
                          boxprops=dict(facecolor='lightblue', alpha=0.7),
                          medianprops=dict(color='red', linewidth=2),
                          meanprops=dict(color='darkgreen', linewidth=2, linestyle='--'),
                          whiskerprops=dict(linewidth=1.5),
                          capprops=dict(linewidth=1.5))
    
    # Color boxes by typical price level
    colors_gradient = plt.cm.RdYlGn_r(np.linspace(0.2, 0.8, 24))
    means = [np.mean(data) for data in box_data_hour]
    sorted_means = sorted(means)
    for i, (patch, mean_val) in enumerate(zip(bp['boxes'], means)):
        # Color based on price rank (lower price = greener)
        rank = sorted_means.index(mean_val)
        color_idx = int((rank / len(sorted_means)) * 23)
        patch.set_facecolor(colors_gradient[color_idx])
        patch.set_alpha(0.7)
    
    # Add shaded regions for typical time windows
    ax_price.axvspan(10, 16, alpha=0.15, color='gold', label='PV Charging (10-16h)')
    ax_price.axvspan(16, 23, alpha=0.15, color='blue', label='Arbitrage Discharge (16-23h)')
    ax_price.axvspan(-0.5, 5, alpha=0.15, color='green', label='Spot Charging (23-05h)')
    ax_price.axvspan(23, 24.5, alpha=0.15, color='green')
    ax_price.axvspan(5, 10, alpha=0.15, color='purple', label='Electrolyser (05-10h)')
    
    ax_price.set_xlabel('Hour of Day', fontsize=12, fontweight='bold')
    ax_price.set_ylabel('Spot Price (€/MWh)', fontsize=12, fontweight='bold')
    ax_price.set_title('Electricity Spot Price Distribution by Hour of Day', 
                      fontsize=14, fontweight='bold')
    ax_price.grid(True, alpha=0.3, axis='y')
    ax_price.legend(loc='upper left', fontsize=9)
    
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
    
    # Key insights
    peak_hours = [i for i, mean in enumerate(means) if mean > np.percentile(means, 75)]
    low_hours = [i for i, mean in enumerate(means) if mean < np.percentile(means, 25)]
    
    col_insight1, col_insight2 = st.columns(2)
    with col_insight1:
        st.info(f"**🔴 Peak Price Hours:** {', '.join([f'{h}h' for h in peak_hours])} - Optimal for arbitrage discharge")
    with col_insight2:
        st.success(f"**🟢 Low Price Hours:** {', '.join([f'{h}h' for h in low_hours])} - Optimal for grid charging")
    
    st.markdown("---")
    
    # Configuration in columns
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("⚙️ Battery Configuration")
        
        # Battery parameters
        battery_params = DEFAULT_BATTERY_PARAMS.copy()
        
        battery_params['E_bat_max'] = st.number_input(
            "Energy Capacity (MWh)", 
            min_value=5.0, max_value=50.0, value=10.0, step=1.0,
            help="Maximum battery energy storage capacity"
        )
        
        battery_params['P_charge_max'] = st.number_input(
            "Charge Power (MW)", 
            min_value=2.0, max_value=25.0, value=5.0, step=1.0,
            help="Maximum charging power"
        )
        
        battery_params['P_discharge_max'] = st.number_input(
            "Discharge Power (MW)", 
            min_value=2.0, max_value=25.0, value=5.0, step=1.0,
            help="Maximum discharging power"
        )
        
        battery_params['eta_rt'] = st.slider(
            "Round-trip Efficiency", 
            min_value=0.80, max_value=0.98, value=0.92, step=0.01,
            help="Battery round-trip efficiency"
        )
        
        battery_params['eta_charge'] = np.sqrt(battery_params['eta_rt'])
        battery_params['eta_discharge'] = np.sqrt(battery_params['eta_rt'])
        
        battery_params['DoD_max'] = st.slider(
            "Max Depth of Discharge", 
            min_value=0.80, max_value=1.00, value=0.90, step=0.05
        )
        
        # Electrolyser parameters (from main dashboard)
        st.subheader("⚡ Electrolyser")
        electrolyser_params = DEFAULT_ELECTROLYSER_PARAMS.copy()
        electrolyser_params['P_ely'] = electrolyser_power
        
        st.info(f"Using electrolyser power from main config: **{electrolyser_power:.1f} MW**")
    
    with col2:
        st.subheader("⏰ Operational Time Windows")
        st.markdown("*Configure time windows for each operational mode (24-hour format)*")
        
        time_windows = DEFAULT_TIME_WINDOWS.copy()
        
        # Use tabs for time windows
        tw_tab1, tw_tab2, tw_tab3, tw_tab4 = st.tabs([
            "🌞 PV Charging", "💰 Arbitrage", "⚡ Spot Charging", "🔋 Electrolyser"
        ])
        
        with tw_tab1:
            col_a, col_b = st.columns(2)
            with col_a:
                time_windows['pv_charge_start'] = st.number_input(
                    "Start Hour", 0, 23, 10, 1, key='pv_start',
                    help="PV charging window start (e.g., 10 = 10:00)"
                )
            with col_b:
                time_windows['pv_charge_end'] = st.number_input(
                    "End Hour", 0, 23, 16, 1, key='pv_end',
                    help="PV charging window end"
                )
            st.caption("All PV production charges the battery. Excess PV is curtailed.")
        
        with tw_tab2:
            col_a, col_b = st.columns(2)
            with col_a:
                time_windows['arbitrage_discharge_start'] = st.number_input(
                    "Start Hour", 0, 23, 16, 1, key='arb_start',
                    help="Arbitrage discharge window start"
                )
            with col_b:
                time_windows['arbitrage_discharge_end'] = st.number_input(
                    "End Hour", 0, 23, 23, 1, key='arb_end',
                    help="Arbitrage discharge window end"
                )
            st.caption("Discharge battery to grid at max power to sell energy.")
        
        with tw_tab3:
            col_a, col_b = st.columns(2)
            with col_a:
                time_windows['night_charge_start'] = st.number_input(
                    "Start Hour", 0, 23, 23, 1, key='night_start',
                    help="Spot charging window start"
                )
            with col_b:
                time_windows['night_charge_end'] = st.number_input(
                    "End Hour", 0, 23, 5, 1, key='night_end',
                    help="Spot charging window end"
                )
            
            night_strategy = NIGHT_CHARGE_STRATEGY.copy()
            charge_mode = st.radio(
                "Strategy",
                ["Always Charge", "Price Threshold"],
                index=0,
                horizontal=True,
                key='night_mode'
            )
            night_strategy['mode'] = 'always_charge' if charge_mode == "Always Charge" else 'price_threshold'
            
            if night_strategy['mode'] == 'price_threshold':
                night_strategy['price_threshold'] = st.number_input(
                    "Max Price (€/MWh)", 0.0, 200.0, 50.0, 5.0, key='night_price'
                )
            
            st.caption("Charge from grid at spot market prices.")
        
        with tw_tab4:
            col_a, col_b = st.columns(2)
            with col_a:
                time_windows['electrolyser_start'] = st.number_input(
                    "Start Hour", 0, 23, 5, 1, key='ely_start',
                    help="Electrolyser operation window start"
                )
            with col_b:
                time_windows['electrolyser_end'] = st.number_input(
                    "End Hour", 0, 23, 10, 1, key='ely_end',
                    help="Electrolyser operation window end"
                )
            st.caption("Battery exclusively powers electrolyser (no grid purchase).")
    
    # Validate time windows
    is_valid, validation_msg = validate_time_windows(time_windows)
    if not is_valid:
        st.warning(f"⚠️ Time window configuration issue: {validation_msg}")
    
    # Run button
    st.markdown("---")
    run_battery_opt = st.button("🚀 Run Battery Optimization", type="primary", use_container_width=True)
    
    if run_battery_opt:
        with st.spinner("Running battery optimization..."):
            # Use existing columns from CSV data
            spot_prices = data_content['Prix'].values
            hours_of_day = data_content['Heure'].values
            
            # Prepare PV profile using month names from Mois column
            pv_profile = distribute_monthly_pv_to_hourly_from_dataframe(
                pv_energy_data['pv_energy_mwh'],
                data_content
            )
            
            # Create optimizer
            optimizer = BatteryOptimizer(
                battery_params=battery_params,
                time_windows=time_windows,
                electrolyser_params=electrolyser_params,
                night_charge_strategy=night_strategy
            )
            
            # Run simulation with hours instead of timestamps
            df_results, summary = optimizer.simulate_year(pv_profile, spot_prices, hours_of_day)
            
            # Store results in session state
            st.session_state['battery_results'] = df_results
            st.session_state['battery_summary'] = summary
            st.session_state['battery_params'] = battery_params
            st.session_state['battery_time_windows'] = time_windows
        
        st.success("✅ Battery optimization complete!")
    
    # Display results
    if 'battery_results' in st.session_state:
        df_results = st.session_state['battery_results']
        summary = st.session_state['battery_summary']
        battery_params = st.session_state['battery_params']
        time_windows = st.session_state['battery_time_windows']
        
        # Key metrics
        st.markdown("---")
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
                "Revenue",
                f"{summary['total_revenue_eur']:,.0f} €",
                delta=f"Sell: {summary['avg_arbitrage_price_eur_mwh']:.1f} €/MWh"
            )
        
        with col3:
            st.metric(
                "Grid Cost",
                f"{summary['total_cost_eur']:,.0f} €",
                delta=f"Buy: {summary['avg_charging_price_eur_mwh']:.1f} €/MWh"
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
        
        # Detailed results tabs
        st.markdown("---")
        res_tab1, res_tab2, res_tab3, res_tab4 = st.tabs([
            "📈 SoC & Power Flows",
            "💰 Economics",
            "⚡ H₂ Production",
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
            axes[0].fill_between(range(len(df_window)), 0, df_window['pv_to_battery_mw'], 
                                color='gold', alpha=0.7, label='PV to Battery')
            axes[0].fill_between(range(len(df_window)), 0, df_window['grid_to_battery_mw'], 
                                color='green', alpha=0.7, label='Grid to Battery')
            axes[0].fill_between(range(len(df_window)), 0, -df_window['battery_to_grid_mw'], 
                                color='blue', alpha=0.7, label='Battery to Grid')
            axes[0].set_ylabel('Power (MW)', fontweight='bold')
            axes[0].set_title('Battery Charging/Discharging', fontweight='bold')
            axes[0].legend()
            axes[0].grid(True, alpha=0.3)
            
            # Electrolyser
            axes[1].fill_between(range(len(df_window)), 0, df_window['battery_to_ely_mw'], 
                                color='purple', alpha=0.7, label='Battery to Electrolyser')
            axes[1].fill_between(range(len(df_window)), 0, -df_window['ely_shortage_mw'], 
                                color='red', alpha=0.5, label='Shortage')
            axes[1].set_ylabel('Power (MW)', fontweight='bold')
            axes[1].set_title('Electrolyser Supply', fontweight='bold')
            axes[1].legend()
            axes[1].grid(True, alpha=0.3)
            
            # PV
            axes[2].fill_between(range(len(df_window)), 0, df_window['pv_available_mw'], 
                                color='orange', alpha=0.5, label='PV Available')
            axes[2].fill_between(range(len(df_window)), 0, df_window['pv_curtailed_mw'], 
                                color='gray', alpha=0.7, label='PV Curtailed')
            axes[2].set_xlabel('Hour', fontweight='bold')
            axes[2].set_ylabel('Power (MW)', fontweight='bold')
            axes[2].set_title('PV Production', fontweight='bold')
            axes[2].legend()
            axes[2].grid(True, alpha=0.3)
            
            plt.tight_layout()
            st.pyplot(fig_power_simple)
            plt.close(fig_power_simple)
        
        with res_tab2:
            st.markdown("#### Economics Breakdown")
            
            # Simple monthly cashflow chart
            fig_cash, ax = plt.subplots(figsize=(12, 6))
            
            # Group by month (assuming sequential hourly data)
            hours_per_month = []
            month_labels = []
            revenue_monthly = []
            cost_monthly = []
            net_monthly = []
            
            current_month_hours = 0
            current_revenue = 0
            current_cost = 0
            month_idx = 0
            
            for i in range(len(df_results)):
                current_revenue += df_results.iloc[i]['revenue_arbitrage']
                current_cost += df_results.iloc[i]['cost_charging']
                current_month_hours += 1
                
                # Approximate month boundaries (every ~730 hours)
                if current_month_hours >= 730 or i == len(df_results) - 1:
                    revenue_monthly.append(current_revenue)
                    cost_monthly.append(current_cost)
                    net_monthly.append(current_revenue - current_cost)
                    month_labels.append(f'M{month_idx+1}')
                    current_month_hours = 0
                    current_revenue = 0
                    current_cost = 0
                    month_idx += 1
            
            x_pos = np.arange(len(month_labels))
            width = 0.6
            
            ax.bar(x_pos, revenue_monthly, width, color='green', alpha=0.7, label='Revenue')
            ax.bar(x_pos, [-c for c in cost_monthly], width, color='red', alpha=0.7, label='Cost')
            ax.plot(x_pos, net_monthly, color='blue', linewidth=2.5, marker='o', markersize=8, label='Net', zorder=10)
            
            ax.set_xticks(x_pos)
            ax.set_xticklabels(month_labels)
            ax.set_xlabel('Month', fontweight='bold')
            ax.set_ylabel('Cashflow (€)', fontweight='bold')
            ax.set_title('Monthly Cashflow Breakdown', fontweight='bold')
            ax.legend()
            ax.grid(True, alpha=0.3, axis='y')
            ax.axhline(y=0, color='black', linewidth=1)
            
            plt.tight_layout()
            st.pyplot(fig_cash)
            plt.close(fig_cash)
            
            # Monthly table - simple grouping by ~730 hours
            st.markdown("#### Monthly Breakdown")
            monthly_data = []
            month_idx = 0
            for i in range(0, len(df_results), 730):
                month_df = df_results.iloc[i:i+730]
                monthly_data.append({
                    'Month': f'Month {month_idx+1}',
                    'Revenue (€)': month_df['revenue_arbitrage'].sum(),
                    'Cost (€)': month_df['cost_charging'].sum(),
                    'Net (€)': month_df['net_cashflow'].sum(),
                    'Discharged (MWh)': month_df['battery_to_grid_mw'].sum(),
                    'Charged (MWh)': month_df['grid_to_battery_mw'].sum()
                })
                month_idx += 1
            
            df_monthly_summary = pd.DataFrame(monthly_data)
            st.dataframe(df_monthly_summary.style.format({
                'Revenue (€)': '{:,.0f}',
                'Cost (€)': '{:,.0f}',
                'Net (€)': '{:,.0f}',
                'Discharged (MWh)': '{:.1f}',
                'Charged (MWh)': '{:.1f}'
            }), use_container_width=True)
        
        with res_tab3:
            st.markdown("#### Hydrogen Production")
            
            # Simple H2 production chart
            fig_h2, ax = plt.subplots(figsize=(12, 6))
            
            # Group by day (every 24 hours)
            daily_h2 = []
            for day in range(0, len(df_results), 24):
                day_total = df_results.iloc[day:day+24]['ely_h2_production_kg'].sum()
                daily_h2.append(day_total)
            
            ax.bar(range(len(daily_h2)), daily_h2, color='purple', alpha=0.7)
            ax.set_xlabel('Day', fontweight='bold')
            ax.set_ylabel('H₂ Production (kg/day)', fontweight='bold')
            ax.set_title('Daily Hydrogen Production', fontweight='bold')
            ax.grid(True, alpha=0.3, axis='y')
            
            # Add target line
            target_h2 = (electrolyser_params['P_ely'] * 1000 * 5) / electrolyser_params['specific_consumption']
            ax.axhline(y=target_h2, color='red', linestyle='--', linewidth=2, label=f'Target ({target_h2:.1f} kg/day)')
            ax.legend()
            
            plt.tight_layout()
            st.pyplot(fig_h2)
            plt.close(fig_h2)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Operating Hours", f"{summary['ely_operating_hours']:.0f}")
            with col2:
                st.metric("Capacity Factor", f"{summary['ely_capacity_factor']:.1%}")
            with col3:
                st.metric("Shortage Hours", f"{summary['ely_shortage_hours']:.0f}")
        
        with res_tab4:
            st.markdown("#### Complete Summary Statistics")
            
            summary_data = {
                'Category': [
                    'Energy Flows', '', '', '', '', '',
                    'Economics', '', '', '',
                    'Battery', '', '', '',
                    'Electrolyser', '', ''
                ],
                'Metric': [
                    'PV Available', 'PV to Battery', 'PV Curtailed',
                    'Grid to Battery', 'Battery to Grid', 'Battery to Electrolyser',
                    'Revenue', 'Cost', 'Penalties', 'Net Profit',
                    'Avg SoC', 'SoC Range', 'Cycles', 'Throughput',
                    'H₂ Production', 'Capacity Factor', 'Cost per kg'
                ],
                'Value': [
                    f"{summary['total_pv_available_mwh']:.1f} MWh",
                    f"{summary['total_pv_to_battery_mwh']:.1f} MWh",
                    f"{summary['total_pv_curtailed_mwh']:.1f} MWh",
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
    
    else:
        st.info("👆 Configure battery parameters and time windows above, then click 'Run Battery Optimization'")
        
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

