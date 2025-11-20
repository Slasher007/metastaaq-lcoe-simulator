"""
Battery Arbitrage Dashboard
Main interface for running PV-Battery-Electrolyser optimization with arbitrage
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

# Import battery modules
from battery_config import (
    DEFAULT_BATTERY_PARAMS, DEFAULT_TIME_WINDOWS, DEFAULT_ELECTROLYSER_PARAMS,
    validate_time_windows, calculate_max_hydrogen_production
)
from battery_optimizer import BatteryOptimizer, distribute_monthly_pv_to_hourly
from battery_visualization import (
    plot_soc_profile, plot_power_flows, plot_economics_breakdown,
    plot_monthly_summary, plot_yearly_cashflow, plot_hydrogen_production
)
from battery_sensitivity import (
    SensitivityAnalyzer, plot_single_parameter_sensitivity, 
    plot_two_parameter_heatmap, run_complete_sensitivity_analysis
)


# Page configuration
st.set_page_config(
    page_title="Battery Arbitrage Optimizer",
    page_icon="🔋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .section-header {
        font-size: 1.8rem;
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
""", unsafe_allow_html=True)


def load_spot_price_data(filepath):
    """Load spot price data from CSV"""
    df = pd.read_csv(filepath)
    df['Date'] = pd.to_datetime(df['Date'])
    df['timestamp'] = df.apply(lambda row: row['Date'] + timedelta(hours=row['Heure']), axis=1)
    return df


def create_hourly_timestamps(year=2021):
    """Create hourly timestamps for a full year"""
    start_date = datetime(year, 1, 1, 0, 0, 0)
    timestamps = [start_date + timedelta(hours=i) for i in range(8760)]
    return np.array(timestamps)


def main():
    """Main dashboard function"""
    
    # Header
    st.markdown('<div class="main-header">🔋 PV-Battery-Electrolyser Arbitrage Optimizer</div>', 
                unsafe_allow_html=True)
    st.markdown("**Optimize energy management strategy with parametric time windows and battery arbitrage**")
    st.markdown("---")
    
    # Sidebar - Configuration
    st.sidebar.header("⚙️ System Configuration")
    
    # Data loading
    st.sidebar.subheader("📁 Data Source")
    data_file = st.sidebar.text_input(
        "Spot Price Data File", 
        value="processed_donnees_prix_spot_fr_2021_2025_month_8.csv",
        help="CSV file with columns: Date, Heure, Prix"
    )
    
    # Simulation year
    sim_year = st.sidebar.selectbox("Simulation Year", [2021, 2022, 2023, 2024, 2025], index=0)
    
    # Load data
    try:
        df_prices = load_spot_price_data(data_file)
        df_prices_year = df_prices[df_prices['Date'].dt.year == sim_year].copy()
        st.sidebar.success(f"✅ Loaded {len(df_prices_year)} hourly price records for {sim_year}")
    except Exception as e:
        st.error(f"❌ Error loading data: {e}")
        return
    
    # Battery Parameters
    st.sidebar.subheader("🔋 Battery Parameters")
    battery_params = DEFAULT_BATTERY_PARAMS.copy()
    
    battery_params['E_bat_max'] = st.sidebar.slider(
        "Energy Capacity (MWh)", 
        min_value=5.0, max_value=50.0, value=float(DEFAULT_BATTERY_PARAMS['E_bat_max']), step=1.0,
        help="Maximum battery energy storage capacity"
    )
    
    battery_params['P_charge_max'] = st.sidebar.slider(
        "Charge Power (MW)", 
        min_value=2.0, max_value=25.0, value=float(DEFAULT_BATTERY_PARAMS['P_charge_max']), step=1.0,
        help="Maximum charging power"
    )
    
    battery_params['P_discharge_max'] = st.sidebar.slider(
        "Discharge Power (MW)", 
        min_value=2.0, max_value=25.0, value=float(DEFAULT_BATTERY_PARAMS['P_discharge_max']), step=1.0,
        help="Maximum discharging power"
    )
    
    battery_params['eta_rt'] = st.sidebar.slider(
        "Round-trip Efficiency", 
        min_value=0.80, max_value=1.00, value=float(DEFAULT_BATTERY_PARAMS['eta_rt']), step=0.01,
        help="Battery round-trip efficiency (charge + discharge losses)"
    )
    
    # Calculate one-way efficiencies from round-trip
    battery_params['eta_charge'] = np.sqrt(battery_params['eta_rt'])
    battery_params['eta_discharge'] = np.sqrt(battery_params['eta_rt'])
    
    battery_params['DoD_max'] = st.sidebar.slider(
        "Max Depth of Discharge", 
        min_value=0.80, max_value=1.00, value=float(DEFAULT_BATTERY_PARAMS['DoD_max']), step=0.05,
        help="Maximum allowed depth of discharge"
    )
    
    battery_params['SoC_initial'] = st.sidebar.slider(
        "Initial SoC (Jan 1)", 
        min_value=0.1, max_value=1.0, value=float(DEFAULT_BATTERY_PARAMS['SoC_initial']), step=0.05,
        help="Initial state of charge on January 1st at 00:00"
    )
    
    # Time Windows
    st.sidebar.subheader("⏰ Operational Time Windows")
    st.sidebar.markdown("*All times in 24-hour format (0-23)*")
    
    time_windows = DEFAULT_TIME_WINDOWS.copy()
    
    with st.sidebar.expander("🌞 PV Charging Window", expanded=False):
        time_windows['pv_charge_start'] = st.slider(
            "PV Charge Start (hour)", 0, 23, DEFAULT_TIME_WINDOWS['pv_charge_start'], 1,
            help="Start of PV-priority charging"
        )
        time_windows['pv_charge_end'] = st.slider(
            "PV Charge End (hour)", 0, 23, DEFAULT_TIME_WINDOWS['pv_charge_end'], 1,
            help="End of PV-priority charging"
        )
    
    with st.sidebar.expander("💰 Arbitrage Discharge Window", expanded=False):
        time_windows['arbitrage_discharge_start'] = st.slider(
            "Arbitrage Start (hour)", 0, 23, DEFAULT_TIME_WINDOWS['arbitrage_discharge_start'], 1,
            help="Start of evening arbitrage discharge"
        )
        time_windows['arbitrage_discharge_end'] = st.slider(
            "Arbitrage End (hour)", 0, 23, DEFAULT_TIME_WINDOWS['arbitrage_discharge_end'], 1,
            help="End of evening arbitrage discharge"
        )
    
    with st.sidebar.expander("🌙 Night Charging Window", expanded=False):
        time_windows['night_charge_start'] = st.slider(
            "Night Charge Start (hour)", 0, 23, DEFAULT_TIME_WINDOWS['night_charge_start'], 1,
            help="Start of night charging from grid"
        )
        time_windows['night_charge_end'] = st.slider(
            "Night Charge End (hour)", 0, 23, DEFAULT_TIME_WINDOWS['night_charge_end'], 1,
            help="End of night charging from grid"
        )
        
        # Night charging strategy from UI (no global NIGHT_CHARGE_STRATEGY constant)
        charge_mode = st.radio(
            "Night Charging Strategy",
            ["Always Charge", "Price Threshold"],
            index=0,
            help="Always charge or only when price is below threshold"
        )
        night_strategy = {
            "mode": 'always_charge' if charge_mode == "Always Charge" else 'price_threshold',
            "price_threshold": 50.0,
        }
        
        if night_strategy['mode'] == 'price_threshold':
            night_strategy['price_threshold'] = st.number_input(
                "Price Threshold (€/MWh)", 
                min_value=0.0, max_value=200.0, value=50.0, step=5.0
            )
    
    with st.sidebar.expander("⚡ Electrolyser Window", expanded=False):
        time_windows['electrolyser_start'] = st.slider(
            "Electrolyser Start (hour)", 0, 23, DEFAULT_TIME_WINDOWS['electrolyser_start'], 1,
            help="Start of electrolyser operation"
        )
        time_windows['electrolyser_end'] = st.slider(
            "Electrolyser End (hour)", 0, 23, DEFAULT_TIME_WINDOWS['electrolyser_end'], 1,
            help="End of electrolyser operation"
        )
    
    # Validate time windows
    is_valid, validation_msg = validate_time_windows(time_windows)
    if not is_valid:
        st.sidebar.warning(f"⚠️ Time window issue: {validation_msg}")
    
    # Electrolyser Parameters
    st.sidebar.subheader("⚡ Electrolyser Parameters")
    electrolyser_params = DEFAULT_ELECTROLYSER_PARAMS.copy()
    
    electrolyser_params['P_ely'] = st.sidebar.slider(
        "Electrolyser Power (MW)", 
        min_value=1.0, max_value=15.0, value=float(DEFAULT_ELECTROLYSER_PARAMS['P_ely']), step=0.5,
        help="Fixed power consumption when electrolyser is ON"
    )
    
    electrolyser_params['specific_consumption'] = st.sidebar.number_input(
        "Specific Consumption (kWh/kg H₂)", 
        min_value=4.0, max_value=6.0, value=float(DEFAULT_ELECTROLYSER_PARAMS['specific_consumption']), step=0.1,
        help="Energy required to produce 1 kg of hydrogen"
    )
    
    electrolyser_params['min_load_ratio'] = st.sidebar.slider(
        "Minimum Load Ratio", 
        min_value=0.0, max_value=0.5, value=float(DEFAULT_ELECTROLYSER_PARAMS['min_load_ratio']), step=0.05,
        help="Minimum operating load as fraction of rated power"
    )
    
    # PV Configuration
    st.sidebar.subheader("☀️ PV Configuration")
    pv_mode = st.sidebar.radio(
        "PV Data Source",
        ["Use Existing PV Profile", "Import from Main Dashboard", "Generate Simple Profile"],
        index=0
    )
    
    if pv_mode == "Import from Main Dashboard":
        # Try to import PV data from session state (if coming from main dashboard)
        if 'pv_energy_data' in st.session_state:
            pv_energy_monthly = st.session_state.pv_energy_data['pv_energy_mwh']
            st.sidebar.success("✅ Using PV data from main dashboard")
        else:
            st.sidebar.warning("⚠️ No PV data in session. Using default profile.")
            pv_energy_monthly = None
    elif pv_mode == "Generate Simple Profile":
        peak_power = st.sidebar.slider(
            "PV Peak Power (MW)", 
            min_value=1.0, max_value=30.0, value=10.0, step=1.0
        )
        pv_energy_monthly = None  # Will generate in optimizer
    else:
        # Use default monthly values (example)
        pv_energy_monthly = {
            'January': 200, 'February': 250, 'March': 350, 'April': 450,
            'May': 550, 'June': 600, 'July': 620, 'August': 580,
            'September': 450, 'October': 350, 'November': 220, 'December': 180
        }
        st.sidebar.info("Using default monthly PV profile")
    
    # Run simulation button
    st.sidebar.markdown("---")
    run_simulation = st.sidebar.button("🚀 Run Optimization", type="primary", use_container_width=True)
    
    # Main content area
    if run_simulation:
        with st.spinner("Running optimization..."):
            # Prepare data
            timestamps = df_prices_year['timestamp'].values
            spot_prices = df_prices_year['Prix'].values
            
            # Prepare PV profile
            if pv_energy_monthly:
                pv_profile = distribute_monthly_pv_to_hourly(pv_energy_monthly, timestamps)
            else:
                # Simple generation
                from battery_optimizer import generate_typical_pv_profile
                pv_profile = generate_typical_pv_profile(timestamps, peak_power_mw=peak_power if pv_mode == "Generate Simple Profile" else 10.0)
            
            # Create optimizer
            optimizer = BatteryOptimizer(
                battery_params=battery_params,
                time_windows=time_windows,
                electrolyser_params=electrolyser_params,
                night_charge_strategy=night_strategy,
                pv_price=0.0  # Default to 0 if not integrated with main dashboard pricing
            )
            
            # Run simulation
            df_results, summary = optimizer.simulate_year(pv_profile, spot_prices, timestamps)
            
            # Store in session state
            st.session_state['battery_results'] = df_results
            st.session_state['battery_summary'] = summary
            st.session_state['battery_params'] = battery_params
            st.session_state['time_windows'] = time_windows
            st.session_state['electrolyser_params'] = electrolyser_params
        
        st.success("✅ Optimization complete!")
    
    # Display results if available
    if 'battery_results' in st.session_state:
        df_results = st.session_state['battery_results']
        summary = st.session_state['battery_summary']
        battery_params = st.session_state['battery_params']
        time_windows = st.session_state['time_windows']
        electrolyser_params = st.session_state['electrolyser_params']
        
        # Key Metrics
        st.markdown('<div class="section-header">📊 Key Performance Indicators</div>', 
                   unsafe_allow_html=True)
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric(
                "Net Profit",
                f"{summary['net_profit_eur']:,.0f} €",
                delta=f"{summary['net_profit_eur']/365:.0f} €/day"
            )
        
        with col2:
            st.metric(
                "Total Revenue",
                f"{summary['total_revenue_eur']:,.0f} €",
                delta=f"{summary['avg_arbitrage_price_eur_mwh']:.1f} €/MWh avg"
            )
        
        with col3:
            st.metric(
                "H₂ Production",
                f"{summary['total_h2_production_tonnes']:.1f} tonnes",
                delta=f"{summary['total_h2_production_kg']/365:.1f} kg/day"
            )
        
        with col4:
            st.metric(
                "Battery Cycles",
                f"{summary['equivalent_cycles']:.0f}",
                delta=f"{summary['avg_soc']:.1%} avg SoC"
            )
        
        with col5:
            st.metric(
                "Electrolyser CF",
                f"{summary['ely_capacity_factor']:.1%}",
                delta=f"{summary['ely_operating_hours']:.0f} hours"
            )
        
        # Tabs for different views
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📈 Power Flows & SoC", 
            "💰 Economics", 
            "⚡ Hydrogen Production",
            "📊 Summary Statistics",
            "🔬 Sensitivity Analysis"
        ])
        
        with tab1:
            st.markdown("### Battery State of Charge")
            
            # Week selector
            week_start = st.slider("Select start day for detailed view", 0, 358, 0, 7)
            
            fig_soc = plot_soc_profile(
                df_results, 
                time_window_days=7, 
                start_day=week_start,
                time_windows=time_windows,
                battery_params=battery_params
            )
            st.pyplot(fig_soc)
            plt.close(fig_soc)
            
            st.markdown("### Power Flows")
            fig_power = plot_power_flows(df_results, time_window_days=7, start_day=week_start)
            st.pyplot(fig_power)
            plt.close(fig_power)
        
        with tab2:
            st.markdown("### Economics Breakdown")
            
            fig_econ = plot_economics_breakdown(df_results, time_window_days=30, start_day=0)
            st.pyplot(fig_econ)
            plt.close(fig_econ)
            
            st.markdown("### Yearly Cashflow")
            fig_cashflow = plot_yearly_cashflow(df_results)
            st.pyplot(fig_cashflow)
            plt.close(fig_cashflow)
            
            # Detailed economics table
            st.markdown("### Monthly Economics Summary")
            df_monthly = df_results.copy()
            df_monthly['month'] = df_monthly['timestamp'].dt.to_period('M')
            df_monthly_summary = df_monthly.groupby('month').agg({
                'revenue_arbitrage': 'sum',
                'cost_charging': 'sum',
                'cost_penalties': 'sum',
                'net_cashflow': 'sum',
                'battery_to_grid_mw': 'sum',
                'grid_to_battery_mw': 'sum',
            }).reset_index()
            df_monthly_summary.columns = [
                'Month', 'Revenue (€)', 'Cost (€)', 'Penalties (€)', 
                'Net Cashflow (€)', 'Discharged (MWh)', 'Charged (MWh)'
            ]
            st.dataframe(df_monthly_summary, use_container_width=True)
        
        with tab3:
            st.markdown("### Hydrogen Production Statistics")
            
            fig_h2 = plot_hydrogen_production(df_results, electrolyser_params)
            st.pyplot(fig_h2)
            plt.close(fig_h2)
            
            # H2 production details
            st.markdown("### Daily Hydrogen Production Statistics")
            daily_h2 = df_results.groupby(df_results['timestamp'].dt.date)['ely_h2_production_kg'].sum()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Average Daily Production", f"{daily_h2.mean():.1f} kg/day")
            with col2:
                st.metric("Maximum Daily Production", f"{daily_h2.max():.1f} kg/day")
            with col3:
                st.metric("Minimum Daily Production", f"{daily_h2.min():.1f} kg/day")
        
        with tab4:
            st.markdown("### Summary Statistics")
            
            fig_summary = plot_monthly_summary(summary)
            st.pyplot(fig_summary)
            plt.close(fig_summary)
            
            # Detailed statistics table
            st.markdown("### Detailed Metrics")
            metrics_data = {
                'Category': [
                    'Energy Flows', '', '', '', '', '',
                    'Economics', '', '', '',
                    'Battery', '', '', '',
                    'Electrolyser', '', '', ''
                ],
                'Metric': [
                    'PV Available', 'PV to Battery', 'PV Curtailed', 'Grid to Battery', 
                    'Battery to Grid', 'Battery to Electrolyser',
                    'Total Revenue', 'Total Cost', 'Total Penalties', 'Net Profit',
                    'Avg SoC', 'Min SoC', 'Max SoC', 'Equivalent Cycles',
                    'Operating Hours', 'Shortage Hours', 'Capacity Factor', 'H₂ Cost'
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
                    f"{summary['min_soc']:.1%}",
                    f"{summary['max_soc']:.1%}",
                    f"{summary['equivalent_cycles']:.0f}",
                    f"{summary['ely_operating_hours']:.0f}",
                    f"{summary['ely_shortage_hours']:.0f}",
                    f"{summary['ely_capacity_factor']:.1%}",
                    f"{summary['h2_cost_eur_per_kg']:.2f} €/kg"
                ]
            }
            st.table(pd.DataFrame(metrics_data))
        
        with tab5:
            st.markdown("### Sensitivity Analysis")
            st.info("Select parameters to analyze sensitivity")
            
            sensitivity_type = st.selectbox(
                "Analysis Type",
                ["Single Parameter", "Two Parameter Heatmap", "Comprehensive Analysis"]
            )
            
            if sensitivity_type == "Single Parameter":
                param_category = st.selectbox(
                    "Parameter Category",
                    ["Time Windows", "Battery Sizing", "Electrolyser Sizing"]
                )
                
                if param_category == "Time Windows":
                    param_name = st.selectbox(
                        "Parameter",
                        ["pv_charge_start", "pv_charge_end", "arbitrage_discharge_start",
                         "arbitrage_discharge_end", "electrolyser_start", "electrolyser_end"]
                    )
                    param_values = st.text_input(
                        "Values to test (comma-separated)",
                        value="8,9,10,11,12" if "start" in param_name else "14,15,16,17,18"
                    )
                    param_values = [int(v.strip()) for v in param_values.split(',')]
                    
                    if st.button("Run Sensitivity Analysis"):
                        with st.spinner("Running analysis..."):
                            timestamps = df_prices_year['timestamp'].values
                            spot_prices = df_prices_year['Prix'].values
                            if pv_energy_monthly:
                                pv_profile = distribute_monthly_pv_to_hourly(pv_energy_monthly, timestamps)
                            else:
                                from battery_optimizer import generate_typical_pv_profile
                                pv_profile = generate_typical_pv_profile(timestamps, 10.0)
                            
                            analyzer = SensitivityAnalyzer(battery_params, time_windows, electrolyser_params)
                            df_sens = analyzer.time_window_sensitivity(
                                pv_profile, spot_prices, timestamps,
                                param_name, param_values
                            )
                            
                            fig_sens = plot_single_parameter_sensitivity(df_sens, param_name)
                            st.pyplot(fig_sens)
                            plt.close(fig_sens)
                            
                            st.dataframe(df_sens, use_container_width=True)
                
                elif param_category == "Battery Sizing":
                    st.info("Analyzing battery capacity sensitivity...")
                    capacity_values = st.text_input(
                        "Capacity values (MWh, comma-separated)",
                        value="5,10,15,20,30,40,50"
                    )
                    capacity_values = [float(v.strip()) for v in capacity_values.split(',')]
                    
                    if st.button("Run Battery Sizing Analysis"):
                        with st.spinner("Running analysis..."):
                            timestamps = df_prices_year['timestamp'].values
                            spot_prices = df_prices_year['Prix'].values
                            if pv_energy_monthly:
                                pv_profile = distribute_monthly_pv_to_hourly(pv_energy_monthly, timestamps)
                            else:
                                from battery_optimizer import generate_typical_pv_profile
                                pv_profile = generate_typical_pv_profile(timestamps, 10.0)
                            
                            analyzer = SensitivityAnalyzer(battery_params, time_windows, electrolyser_params)
                            df_battery_sens = analyzer.battery_sizing_sensitivity(
                                pv_profile, spot_prices, timestamps,
                                capacity_values
                            )
                            
                            # Plot results
                            fig, ax = plt.subplots(figsize=(10, 6))
                            ax.plot(df_battery_sens['capacity_mwh'], df_battery_sens['net_profit_eur'],
                                   marker='o', linewidth=2, markersize=8, color='green')
                            ax.set_xlabel('Battery Capacity (MWh)', fontsize=12, fontweight='bold')
                            ax.set_ylabel('Net Profit (€)', fontsize=12, fontweight='bold')
                            ax.set_title('Battery Capacity Sensitivity', fontsize=14, fontweight='bold')
                            ax.grid(True, alpha=0.3)
                            st.pyplot(fig)
                            plt.close(fig)
                            
                            st.dataframe(df_battery_sens, use_container_width=True)
            
            elif sensitivity_type == "Two Parameter Heatmap":
                st.info("Two-parameter heatmap analysis")
                
                col1, col2 = st.columns(2)
                with col1:
                    param1 = st.selectbox("Parameter 1 (X-axis)", 
                                         ["E_bat_max", "P_charge_max", "pv_charge_start"])
                    values1 = st.text_input("Values 1", value="10,20,30,40,50")
                
                with col2:
                    param2 = st.selectbox("Parameter 2 (Y-axis)", 
                                         ["P_charge_max", "E_bat_max", "arbitrage_discharge_start"])
                    values2 = st.text_input("Values 2", value="5,10,15,20,25")
                
                if st.button("Run 2D Sensitivity"):
                    st.info("This analysis may take several minutes...")
                    # Implementation would go here
                    st.warning("Feature coming soon! Use command-line tools for comprehensive 2D analysis.")
            
            else:  # Comprehensive Analysis
                st.info("Comprehensive sensitivity analysis runs multiple scenarios")
                st.warning("This analysis can take 10-30 minutes depending on parameter ranges.")
                
                if st.button("Run Comprehensive Analysis"):
                    st.info("For comprehensive analysis, use the command-line tool: `python run_battery_sensitivity.py`")
    
    else:
        # Initial instructions
        st.info("👈 Configure parameters in the sidebar and click '🚀 Run Optimization' to start")
        
        st.markdown("""
        ### 📋 System Overview
        
        This optimizer simulates a **PV-Battery-Electrolyser system** with electricity market arbitrage.
        
        **Operating Strategy:**
        
        1. **PV Charging Window** (default 10:00-16:00)
           - All PV production charges the battery (up to power/capacity limits)
           - Excess PV is curtailed
        
        2. **Arbitrage Discharge Window** (default 16:00-23:00)
           - Battery discharges to grid at maximum power
           - Revenue from selling at spot market prices
           - Goal: empty battery for cheap night charging
        
        3. **Night Charging Window** (default 23:00-05:00)
           - Charge battery from grid (at low night prices)
           - Can use always-charge or price-threshold strategy
        
        4. **Electrolyser Window** (default 05:00-10:00)
           - Battery exclusively powers electrolyser
           - No grid purchase allowed
           - Hydrogen production for the day
        
        **Objective:** Maximize yearly net profit = Revenue (arbitrage) - Cost (grid charging) - Penalties (electrolyser shortages)
        
        **Outputs:**
        - Hourly battery SoC profile
        - Power flows (PV, grid, electrolyser)
        - Yearly cashflow breakdown
        - Hydrogen production statistics
        - Sensitivity analysis on key parameters
        """)


if __name__ == "__main__":
    main()

