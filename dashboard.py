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

# Set page configuration
st.set_page_config(
    page_title="MetaSTAAQ - LCOE Simulation Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 1.5rem;
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

st.markdown('<p class="main-header">⚡ MetaSTAAQ LCOE Simulation Dashboard</p>', unsafe_allow_html=True)

# Sidebar with logo and parameters
try:
    st.sidebar.image("STAAQ_HD.jpg", width=180)
except FileNotFoundError:
    st.sidebar.warning("⚠️ Logo file 'STAAQ_HD.jpg' not found")

st.sidebar.markdown("### 🔧 Simulation Parameters")

# Load default data file
default_file_path = 'processed_donnees_prix_spot_fr_2021_2025_month_8.csv'
try:
    data_content = pd.read_csv(default_file_path)
except FileNotFoundError:
    st.error("❌ Default data file not found. Please ensure the data file is in the correct location.")
    st.stop()

# Year selection
st.sidebar.markdown("#### 📅 Year Selection")
available_years = sorted(data_content['Annee'].unique()) if 'Annee' in data_content.columns else [2024, 2025]
selected_years = st.sidebar.multiselect(
    "Select years for analysis",
    options=available_years,
    default=[2024] if 2024 in available_years else available_years[:1]
)

# Filter data by selected years
if selected_years:
    data_content = data_content[data_content['Annee'].isin(selected_years)]

# Electrolyzer parameters
with st.sidebar.expander("⚡ Electrolyser", expanded=True):
    electrolyser_power = st.slider(
        "Electrolyzer Power (MW)",
        min_value=1.0,
        max_value=20.0,
        value=5.0,
        step=0.5,
        help="Power capacity of the electrolyzer in MW"
    )

    electrolyser_specific_consumption = st.slider(
        "Specific Consumption (kWh/Nm³ H₂)",
        min_value=4.0,
        max_value=6.0,
        value=4.8,
        step=0.1,
        help="Energy consumption per cubic meter of hydrogen produced"
    )

# Monthly Service Ratios
months = ["January", "February", "March", "April", "May", "June", 
          "July", "August", "September", "October", "November", "December"]

# Initialize monthly_service_ratios dictionary
monthly_service_ratios = {}

# Create expandable section for service ratios
with st.sidebar.expander("📅 Service Ratios", expanded=True):
    st.markdown("*Set individual availability ratios for each month (0.0 = off, 1.0 = always on)*")
    
    # Create two columns for better layout
    col1, col2 = st.columns(2)
    
    # First 6 months in left column
    with col1:
        for month in months[:6]:
            monthly_service_ratios[month] = st.slider(
                f"{month[:3]}",  # Short month name
                min_value=0.0,
                max_value=1.0,
                value=0.98,
                step=0.01,
                key=f"service_{month}",
                help=f"Service ratio for {month}"
            )
    
    # Last 6 months in right column  
    with col2:
        for month in months[6:]:
            monthly_service_ratios[month] = st.slider(
                f"{month[:3]}",  # Short month name
                min_value=0.0,
                max_value=1.0,
                value=0.98,
                step=0.01,
                key=f"service_{month}",
                help=f"Service ratio for {month}"
            )


# Calculate average service ratio for display purposes
avg_service_ratio = sum(monthly_service_ratios.values()) / len(monthly_service_ratios)

# Operation Strategy Selection
st.sidebar.markdown("#### 🎯 Operation Strategy")
strategy_type = st.sidebar.selectbox(
    "Choose Operation Strategy",
    options=["Service Ratio-Based", "Target Price-Based"],
    index=0,
    help="Select the strategy for electrolyzer operation optimization"
)

# Strategy-specific parameters
if strategy_type == "Service Ratio-Based":
    st.info("ℹ️ Service Ratio strategy automatically determines optimal hours based on PPA price threshold.")
    initial_service_ratio = 0.98  # Not used, but kept for compatibility

# Price parameters
with st.sidebar.expander("💰 Price", expanded=True):
    if strategy_type == "Service Ratio-Based":
        st.info("ℹ️ Service Ratio strategy cumulates spot hours while keeping average cost below PPA price.")
        # For Service Ratio strategy, we don't need target price - it's determined by PPA price
        # But we keep it for compatibility with the function signature
        target_prices = [30]  # Fixed value, not used in the algorithm
    else:
        target_prices = [st.slider(
            "Average Target Spot Price (€/MWh)",
            min_value=5,
            max_value=50,
            value=30,
            step=1
        )]

    # PV and PPA Price Parameters
    pv_price = st.slider(
        "PV Price (€/MWh)",
        min_value=0,
        max_value=100,
        value=0,
        step=5,
        help="Price of photovoltaic energy"
    )

    ppa_price = st.slider(
        "PPA Price (€/MWh)",
        min_value=15,
        max_value=200,
        value=80,
        step=5,
        help="Power Purchase Agreement price"
    )

    # If PPA price is below threshold, we will exclude PPA from charts and calculations
    integrate_ppa = ppa_price >= 60

# PV Installation Economics Parameters
with st.sidebar.expander("☀️ PV Installation", expanded=True):
    pv_project_years = st.slider(
        "Project Lifetime",
        min_value=10,
        max_value=30,
        value=20,
        step=1,
        help="Project lifetime in years"
    )
    
    # Surface and Power Estimation
    pv_surface_hectares = st.number_input(
        "Surface (hectares)",
        min_value=0.1,
        max_value=100.0,
        value=1.0,
        step=0.1,
        help="Surface area of PV installation in hectares"
    )
    
    # Estimate power from surface (typical: 0.5-1.0 MWp per hectare)
    power_density_mwp_per_ha = st.slider(
        "Power Density (MWp/ha)",
        min_value=0.3,
        max_value=1.2,
        value=0.8,
        step=0.1,
        help="Power density in MWp per hectare (typical range: 0.5-1.0)"
    )
    
    estimated_power_mwp = pv_surface_hectares * power_density_mwp_per_ha
    estimated_power_kwp = estimated_power_mwp * 1000
    
    st.write(f"**Estimated Power**: {estimated_power_mwp:.2f} MWp ({estimated_power_kwp:,.0f} kWp)")
    
    # Cost parameters based on industry data
    pv_cost_per_wp = st.slider(
        "PV Cost (€/Wp)",
        min_value=0.7,
        max_value=1.2,
        value=0.9,
        step=0.05,
        help="PV cost per Wp (0.7-0.8 €/Wp ground >500kWp, 0.8-1.0 €/Wp for 1-10MWp). Source: ADEME - Coûts énergies renouvelables 2022 - https://www.geothermies.fr/sites/default/files/inline-files/ademe_couts-energies-renouvelables-et-recuperation-donnees2022-011599.pdf"
    )
    

    # Battery configuration
    include_battery = st.checkbox(
        "Include Battery Storage",
        value=False,
        help="Include battery storage in CAPEX calculation"
    )
    
    if include_battery:
        storage_hours = st.slider(
            "Storage Hours",
            min_value=1,
            max_value=12,
            value=4,
            step=1,
            help="Number of hours of PV production that can be stored in battery"
        )
        # Battery capacity = PV power × storage hours
        battery_capacity_mwh = estimated_power_mwp * storage_hours
        st.write(f"**Daily Battery Capacity**: {battery_capacity_mwh:.2f} MWh/day ({storage_hours}h × {estimated_power_mwp:.2f} MWp)")
    else:
        battery_capacity_mwh = 0
        storage_hours = 0
    
   
    if include_battery:
        battery_cost_per_kwh = st.slider(
            "Battery Cost (€/kWh)",
            min_value=200,
            max_value=500,
            value=325,
            step=25,
            help="Battery system cost per kWh (250-400 €/kWh typical range)"
        )
    
    # Calculate CAPEX
    estimated_power_wp = estimated_power_kwp * 1000  # Convert kWp to Wp
    pv_capex_calculated = estimated_power_wp * pv_cost_per_wp
    battery_capex = battery_capacity_mwh * 1000 * battery_cost_per_kwh if include_battery else 0
    total_capex_calculated = pv_capex_calculated + battery_capex
    
    # Option to use calculated or manual CAPEX
    use_calculated_capex = st.checkbox(
        "Use Calculated CAPEX",
        value=True,
        help="Use automatically calculated CAPEX based on surface and costs"
    )
    
    if use_calculated_capex:
        pv_capex = total_capex_calculated
        st.write(f"**Calculated CAPEX**:")
        st.write(f"• PV: {pv_capex_calculated:,.0f} €")
        if include_battery:
            st.write(f"• Battery: {battery_capex:,.0f} €")
        st.write(f"• **Total: {total_capex_calculated:,.0f} €**")
    else:
        pv_capex = st.number_input(
            "Manual CAPEX (€)",
            min_value=0,
            max_value=50000000,
            value=int(total_capex_calculated),
            step=10000,
            help="Manual capital expenditure for PV installation"
        )
    
    # OPEX calculation based on CAPEX percentage
    opex_percentage = st.slider(
        "OPEX (% of CAPEX/year)",
        min_value=1.0,
        max_value=2.0,
        value=1.5,
        step=0.1,
        help="Annual operational expenditure as percentage of CAPEX (typical range: 1-2%)"
    )
    
    # Discount rate for LCOE calculation
    discount_rate = st.slider(
        "Discount Rate (%)",
        min_value=3.0,
        max_value=12.0,
        value=7.0,
        step=0.5,
        help="Discount rate for LCOE calculation (typical range: 5-10%)"
    )
    
    # Option to use calculated or manual OPEX
    use_calculated_opex = st.checkbox(
        "Use Calculated OPEX",
        value=True,
        help="Use automatically calculated OPEX based on CAPEX percentage"
    )
    
    if use_calculated_opex:
        pv_opex = pv_capex * (opex_percentage / 100)
        st.write(f"**Calculated OPEX**: {pv_opex:,.0f} €/year ({opex_percentage}% of CAPEX)")
    else:
        pv_opex = st.number_input(
            "Manual OPEX (€/year)",
            min_value=0,
            max_value=500000,
            value=int(pv_capex * (opex_percentage / 100)) if pv_capex > 0 else 21560,
            step=1000,
            help="Manual annual operational expenditure for PV installation"
        )
    
    pci_ch4_kwh_per_kg = st.slider(
        "PCI CH₄ (kWh/kg)",
        min_value=10.0,
        max_value=20.0,
        value=13.9,
        step=0.1,
        help="Lower Calorific Value of CH₄ in kWh per kg"
    )



# Calculate derived parameters
h2_flowrate = round((electrolyser_power * 1000) / electrolyser_specific_consumption)
stoechio_H2_CH4 = 4
ch4_flowrate = round(h2_flowrate / stoechio_H2_CH4)
ch4_density = 0.7168  # kg/Nm³ CH₄
ch4_kg_per_day = ch4_flowrate * 24 * ch4_density

# Calculate monthly CH4 production based on service ratios
monthly_ch4_production = {
    month: ch4_flowrate * 24 * ratio * (31 if month in ["January", "March", "May", "July", "August", "October", "December"] 
                                       else 30 if month != "February" else 28) * ch4_density
    for month, ratio in monthly_service_ratios.items()
}


# Display calculated parameters
st.sidebar.markdown("#### 📊 Calculated Parameters")
st.sidebar.metric("H₂ Flow Rate", f"{h2_flowrate} Nm³/h")
st.sidebar.metric("CH₄ Flow Rate", f"{ch4_flowrate} Nm³/h")
st.sidebar.metric("Avg Service Ratio", f"{avg_service_ratio:.1%}")

# Show monthly CH4 production summary
total_yearly_ch4_kg = sum(monthly_ch4_production.values())
total_yearly_ch4_tonnes = total_yearly_ch4_kg / 1000
st.sidebar.metric("Yearly CH₄ Production", f"{total_yearly_ch4_tonnes:,.0f} Tonnes")

# PV Economics Parameters will be calculated in results section with actual PV energy data

# Add expandable section for monthly details
with st.sidebar.expander("📅 Monthly Details"):
    for month, production in monthly_ch4_production.items():
        monthly_production_tonnes = production / 1000
        service_pct = monthly_service_ratios[month] * 100
        st.write(f"**{month[:3]}**: {monthly_production_tonnes:.1f} Tonnes ({service_pct:.0f}%)")

# Add parameter change detection using session state
if 'last_params' not in st.session_state:
    st.session_state.last_params = {}

# Current parameters
current_params = {
    'years': tuple(sorted(selected_years)) if selected_years else (),
    'power': electrolyser_power,
    'consumption': electrolyser_specific_consumption,
    'monthly_service_ratios': tuple(sorted(monthly_service_ratios.items())),
    'target_prices': tuple(target_prices),
    'pv_price': pv_price,
    'ppa_price': ppa_price,
    'pv_project_years': pv_project_years,
    'pv_surface_hectares': pv_surface_hectares,
    'power_density_mwp_per_ha': power_density_mwp_per_ha,
    'include_battery': include_battery,
    'storage_hours': storage_hours if include_battery else 0,
    'pv_cost_per_wp': pv_cost_per_wp,
    'battery_cost_per_kwh': battery_cost_per_kwh if include_battery else 0,
    'use_calculated_capex': use_calculated_capex,
    'opex_percentage': opex_percentage,
    'use_calculated_opex': use_calculated_opex,
    'pv_capex': pv_capex,
    'pv_opex': pv_opex,
    'pci_ch4_kwh_per_kg': pci_ch4_kwh_per_kg
}

# Check if parameters have changed
params_changed = st.session_state.last_params != current_params

# Update session state
st.session_state.last_params = current_params.copy()

# Add manual refresh button (optional)
col1, col2 = st.columns([3, 1])
with col1:
    st.markdown("### 📊 Simulation Results")
    if params_changed:
        st.info("🔄 Parameters changed - Results updating automatically...")

with col2:
    manual_refresh = st.button("🔄 Manual Refresh", help="Force refresh the simulation")

# Add monthly price analysis figure before service ratios
st.markdown("#### 📈 Average Monthly Price Analysis")

# Ensure 'Date' is datetime and extract year and month
data_content['Date'] = pd.to_datetime(data_content['Date'])
data_content['Year'] = data_content['Date'].dt.year
data_content['Month'] = data_content['Date'].dt.month

# Group by Year and Month and calculate the mean price
monthly_avg_price = data_content.groupby(['Year', 'Month'])['Prix'].mean().reset_index()

# Map month numbers to month names for better plotting
monthly_avg_price['Month_Name'] = monthly_avg_price['Month'].apply(lambda x: calendar.month_name[x])

# Pivot the table for plotting: Years as columns, Months as index
pivot_table = monthly_avg_price.pivot(index='Month_Name', columns='Year', values='Prix')

# Ensure the order of months is correct
month_order = list(calendar.month_name)[1:]
pivot_table = pivot_table.reindex(month_order)

# Calculate the overall average price per month across all years
overall_monthly_avg = pivot_table.mean(axis=1)

# Plot the bar chart
fig_price, ax_price = plt.subplots(figsize=(12, 6))
ax_price = pivot_table.plot(kind='bar', figsize=(12, 6), ax=ax_price)

# Add the line plot for the overall monthly average
overall_monthly_avg.plot(ax=ax_price, color='red', linestyle='--', marker='o', label='Overall Monthly Average')

# Add value labels to the points on the line plot
for i, v in enumerate(overall_monthly_avg):
    ax_price.text(i, v, f"{v:.1f}", ha='center', va='bottom')

plt.title('Average Monthly Price per Year with Overall Monthly Average')
plt.xlabel('Month')
plt.ylabel('Average Price (€/MWh)')
plt.xticks(rotation=45, ha='right')
plt.legend(title='Year')
plt.tight_layout()
st.pyplot(fig_price)

# Add box plot figure showing price distribution per month
st.markdown("#### 📦 Price Distribution by Month (Box Plot)")

# Create box plot figure
fig_box, ax_box = plt.subplots(figsize=(12, 6))

# Create box plot for price distribution by month
box_data = []
box_labels = []
month_order = list(calendar.month_name)[1:]  # January to December

for month_num in range(1, 13):
    month_name = calendar.month_name[month_num]
    # Get all prices for this month across all years
    month_data = data_content[data_content['Month'] == month_num]['Prix']
    if len(month_data) > 0:
        box_data.append(month_data)
        box_labels.append(month_name)

# Create the box plot
bp = ax_box.boxplot(box_data, labels=box_labels, patch_artist=True)

# Color the boxes with different colors
colors = plt.cm.Set3(range(len(box_data)))
for patch, color in zip(bp['boxes'], colors):
    patch.set_facecolor(color)
    patch.set_alpha(0.7)

# Customize the plot
ax_box.set_title('Electricity Price Distribution by Month', fontweight='bold', fontsize=14)
ax_box.set_xlabel('Month')
ax_box.set_ylabel('Price (€/MWh)')
ax_box.grid(True, alpha=0.3)

# Rotate x-axis labels for better readability
plt.xticks(rotation=45, ha='right')

# Add statistics text box
stats_text = f"Dataset: {len(data_content)} data points\nYears: {sorted(data_content['Year'].unique())}"
ax_box.text(0.02, 0.98, stats_text, transform=ax_box.transAxes, 
           verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

plt.tight_layout()
st.pyplot(fig_box)

# Add a visual summary of monthly service ratios before results
st.markdown("#### 📅 Current Monthly Service Ratios")
service_ratio_df = pd.DataFrame({
    'Month': list(monthly_service_ratios.keys()),
    'Service Ratio': [f"{ratio:.1%}" for ratio in monthly_service_ratios.values()],
    'Service Ratio (Decimal)': list(monthly_service_ratios.values())
})

# Create a bar chart for service ratios
fig_service, ax_service = plt.subplots(figsize=(12, 4))
bars = ax_service.bar(range(len(monthly_service_ratios)), 
                     list(monthly_service_ratios.values()),
                     color=['lightgreen' if ratio >= 0.9 else 'orange' if ratio >= 0.5 else 'lightcoral' 
                           for ratio in monthly_service_ratios.values()])

# Add value labels on bars
for i, (month, ratio) in enumerate(monthly_service_ratios.items()):
    ax_service.text(i, ratio + 0.01, f'{ratio:.0%}', 
                   ha='center', va='bottom', fontweight='bold', fontsize=10)

ax_service.set_xticks(range(len(monthly_service_ratios)))
ax_service.set_xticklabels([month[:3] for month in monthly_service_ratios.keys()], rotation=45)
ax_service.set_ylabel('Service Ratio')
ax_service.set_title('Monthly Service Ratios (Green: ≥90%, Orange: 50-90%, Red: <50%)')
ax_service.set_ylim(0, 1.1)
ax_service.grid(True, alpha=0.3)

plt.tight_layout()
st.pyplot(fig_service)

# Auto-run simulation when parameters change or manual refresh is clicked
run_simulation = params_changed or manual_refresh or 'simulation_run' not in st.session_state

if run_simulation:
    if data_content.empty:
        st.error("❌ No data available. Please upload a valid CSV file.")
    else:
        # Create placeholder for results
        results_placeholder = st.empty()
        
        # Show appropriate loading message
        loading_message = "🔄 Updating simulation with new parameters..." if params_changed else "🚀 Running simulation..."
        
        with st.spinner(loading_message):
            try:
                # Run custom simulation with Streamlit-compatible plotting
                all_results = []
                
                for i, target_price in enumerate(target_prices):
                    st.write(f"**Analyzing with {strategy_type} Strategy:**")
                    if strategy_type == "Service Ratio-Based":
                        st.write(f"**PPA Price Threshold: {ppa_price} €/MWh | PV Price: {pv_price} €/MWh**")
                    else:
                        st.write(f"**Target Price: {target_price} €/MWh | PPA Price: {ppa_price} €/MWh | PV Price: {pv_price} €/MWh**")
                    
                    # Run simulation components using selected strategy
                    expected_monthly_hours = get_required_hours_per_month_custom(monthly_service_ratios)
                    expected_monthly_power = get_expected_monthly_power_cons_custom(electrolyser_power, expected_monthly_hours)
                    
                    # Choose strategy based on user selection
                    if strategy_type == "Service Ratio-Based":
                        strategy_key = 'service_ratio'
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
                    df_power_diff = calculate_percentage_difference(df_power_consumption, expected_monthly_power)
                    
                    # Display results table with strategy-appropriate labeling
                    if strategy_type == "Service Ratio-Based":
                        st.write("**📊 Operating Hours per Month (Service Ratio Strategy):**")
                    else:
                        st.write("**📊 Available Hours per Month:**")
                    st.dataframe(df_result, width='stretch')
                    
                    # Display strategy-specific information
                    st.write(f"**🎯 Strategy Details: {strategy_type}**")
                    if strategy_type == "Service Ratio-Based":
                        st.write(f"• **Strategy**: Cumulate spot hours while average cost < PPA price")
                        st.write(f"• **Price Logic**: Use spot price when spot ≤ PPA, otherwise use PPA price")
                        st.write(f"• **Optimization**: Maximize operating hours below PPA price threshold")
                        st.write(f"• **No Target Price**: Hours determined by PPA price constraint only")
                    else:  # Target Price-Based
                        st.write(f"• **Strategy**: Operate only when spot price ≤ target price")
                        if len(selected_years) > 1:
                            st.write(f"• **Multi-year Mode**: Using monthly average adjustments for consistency")
                        else:
                            st.write(f"• **Single-year Mode**: Using direct target price threshold")
                    
                    # Create and display charts using full width
                    if strategy_type == "Service Ratio-Based":
                        st.write("**📈 Operating Hours Chart (Service Ratio Strategy):**")
                    else:
                        st.write("**📈 Available Hours Chart:**")
                    
                    # Chart 1: Available Hours with Extended Hours Visualization (Full Width)
                    fig1, ax1 = plt.subplots(figsize=(12, 6))
                    df_plot = df_result.T
                    monthly_avg = df_plot.mean(axis=1)
                    
                    # Create separate dataframes for spot and PPA hours
                    spot_hours_data = pd.DataFrame(index=df_plot.index, columns=df_plot.columns, dtype=float)
                    ppa_hours_data = pd.DataFrame(index=df_plot.index, columns=df_plot.columns, dtype=float)
                    
                    for year in df_plot.columns:
                        for month in df_plot.index:
                            if str(year) in extended_info and month in extended_info[str(year)]:
                                info = extended_info[str(year)][month]
                                
                                # Handle different extended_info structures
                                if 'spot_hours' in info and 'ppa_hours' in info:
                                    # Service Ratio Strategy structure with spot/PPA breakdown
                                    spot_hours_data.loc[month, year] = info.get('spot_hours', 0)
                                    ppa_hours_data.loc[month, year] = info.get('ppa_hours', 0)
                                elif 'base_hours' in info and 'extended_hours' in info:
                                    # Original calculate_max_hours structure - treat base as spot, extended as PPA
                                    spot_hours_data.loc[month, year] = info['base_hours']
                                    ppa_hours_data.loc[month, year] = info['extended_hours']
                                elif 'target_hours' in info:
                                    # New strategy structure - treat all as spot hours for now
                                    total_hours = info.get('target_hours', info.get('qualifying_hours', 0))
                                    spot_hours_data.loc[month, year] = total_hours
                                    ppa_hours_data.loc[month, year] = 0
                                else:
                                    # Fallback
                                    total_hours = info.get('total_hours', 0)
                                    spot_hours_data.loc[month, year] = total_hours
                                    ppa_hours_data.loc[month, year] = 0
                            else:
                                spot_hours_data.loc[month, year] = df_plot.loc[month, year] if pd.notna(df_plot.loc[month, year]) else 0
                                ppa_hours_data.loc[month, year] = 0
                    
                    # Fill NaN values with 0
                    spot_hours_data = spot_hours_data.fillna(0)
                    ppa_hours_data = ppa_hours_data.fillna(0)
                    
                    # Create manual bar chart to properly handle stacked visualization
                    x_pos = range(len(df_plot.index))
                    width = 0.8 / len(df_plot.columns)  # Width of bars
                    
                    # Colors for different years
                    colors = plt.cm.tab10(range(len(df_plot.columns)))
                    
                    # Plot bars for each year
                    for i, year in enumerate(df_plot.columns):
                        x_offset = [x + width * (i - len(df_plot.columns)/2 + 0.5) for x in x_pos]
                        
                        # Spot hours (bottom layer)
                        spot_values = spot_hours_data[year].values
                        ax1.bar(x_offset, spot_values, width, 
                               label=f'{year} (Spot)' if i == 0 else "", color=colors[i], alpha=0.8)
                        
                        # PPA hours (stacked on top)
                        ppa_values = ppa_hours_data[year].values
                        ax1.bar(x_offset, ppa_values, width, 
                               bottom=spot_values, color=colors[i], alpha=0.5, 
                               label=f'{year} (PPA)' if i == 0 else "")
                        
                        # Add cumulative hour annotations on top of stacked bars
                        for j, (x, spot_val, ppa_val) in enumerate(zip(x_offset, spot_values, ppa_values)):
                            total_hours = spot_val + ppa_val
                            if total_hours > 0:
                                # Display total cumulative hours on top of the bar
                                ax1.text(x, total_hours + 5, f'{int(total_hours)}h', 
                                        ha='center', va='bottom', fontsize=9, fontweight='bold', 
                                        color='black')
                                
                                # Optionally show breakdown inside bars if there's enough space
                                if spot_val > 20:  # Only show if spot section is large enough
                                    ax1.text(x, spot_val/2, f'S:{int(spot_val)}', 
                                            ha='center', va='center', fontsize=8, fontweight='bold', 
                                            color='white')
                                
                                if ppa_val > 20:  # Only show if PPA section is large enough
                                    ax1.text(x, spot_val + ppa_val/2, f'P:{int(ppa_val)}', 
                                            ha='center', va='center', fontsize=8, fontweight='bold', 
                                            color='white')
                    
                    # Set x-axis labels
                    ax1.set_xticks(x_pos)
                    ax1.set_xticklabels(df_plot.index)
                    
                    # Plot mean values as prominent points with labels
                    ax1.plot(range(len(monthly_avg)), monthly_avg.values, 
                           color='red', linestyle='--', marker='o', markersize=8, 
                           linewidth=2, label='Monthly Average', markerfacecolor='red', 
                           markeredgecolor='white', markeredgewidth=2)
                    
                    # Add value labels on the mean points
                    for i, (month, value) in enumerate(monthly_avg.items()):
                        ax1.annotate(f'{value:.0f}h', 
                                   (i, value), 
                                   textcoords="offset points", 
                                   xytext=(0, 10), 
                                   ha='center', 
                                   fontsize=9, 
                                   fontweight='bold',
                                   color='red',
                                   bbox=dict(boxstyle='round,pad=0.3', 
                                           facecolor='white', 
                                           edgecolor='red', 
                                           alpha=0.8))
                    
                    # Add legend entries for spot and PPA hours
                    from matplotlib.patches import Rectangle
                    handles, labels = ax1.get_legend_handles_labels()
                    
                    # Add spot and PPA legend entries
                    has_spot_hours = spot_hours_data.sum().sum() > 0
                    has_ppa_hours = ppa_hours_data.sum().sum() > 0
                    
                    if has_spot_hours:
                        spot_patch = Rectangle((0, 0), 1, 1, facecolor='blue', alpha=0.8, label='Spot Hours')
                        handles.append(spot_patch)
                        labels.append('Spot Hours')
                    
                    if has_ppa_hours:
                        ppa_patch = Rectangle((0, 0), 1, 1, facecolor='blue', alpha=0.5, label='PPA Hours')
                        handles.append(ppa_patch)
                        labels.append('PPA Hours')
                    
                    ax1.set_xlabel('Month')
                    if strategy_type == "Service Ratio-Based":
                        ax1.set_ylabel('Operating Hours')
                    else:
                        ax1.set_ylabel('Available Hours')
                    if strategy_type == "Service Ratio-Based":
                        ax1.set_title(f'Operating Hours - {strategy_type} Strategy (PPA Threshold: {ppa_price}€/MWh)\nStacked: Spot Hours + PPA Hours with Cumulative Totals')
                    else:
                        ax1.set_title(f'Available Hours - {strategy_type} Strategy (Target: {target_price}€/MWh)\nStacked: Spot Hours + PPA Hours with Cumulative Totals')
                    ax1.tick_params(axis='x', rotation=45)
                    ax1.legend(handles=handles, labels=labels, loc='upper right')
                    
                    # Add second y-axis for power consumption
                    #ax2 = ax1.twinx()
                    #max_power_consumption = electrolyser_power * 24
                    #ax2.set_ylabel('Power Consumption (MWh/day)', color='blue')
                    #ax2.set_ylim(0, max_power_consumption)
                    #ax2.tick_params(axis='y', labelcolor='blue')
                    
                    plt.tight_layout()
                    st.pyplot(fig1)
                    
                    # PV Production Chart Section
                    st.write("**☀️ Monthly PV Production (Meaux Location):**")
                    try:
                        # Create 2x2 grid layout for the images
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.image("meaux_maps_location.png", caption="Meaux Location Map", width='stretch')
                            st.image("meaux_simulation_output.png", caption="Simulation Output", width='stretch')
                        
                        with col2:
                            st.image("meaux_pv_config.png", caption="PV Configuration", width='stretch')
                            st.image("monthly_pv_meaux.png", caption="Monthly PV Energy Production", width='stretch')
                        
                        st.info("📍 **PV Installation with tracking system**: Analysis based on 1 hectare solar panel surface area in Meaux. Data source: PVGIS (Photovoltaic Geographical Information System)")
                    except FileNotFoundError as e:
                        st.warning(f"⚠️ One or more PV images not found: {str(e)}")
                    
                    # Update section header based on battery inclusion
                    if include_battery and battery_capacity_mwh > 0:
                        coverage_title = f"**🔋 Monthly Energy Coverage (with {storage_hours}h Daily Battery Storage) - Spot/PPA Breakdown:**"
                    else:
                        coverage_title = "**🔋 Monthly Energy Coverage - Spot/PPA Breakdown:**"
                    
                    st.write(coverage_title)
                    
                    # Chart 2: Energy Coverage (Full Width)
                    pv_energy_kwh = {
                        "January": 53458.33, "February": 80213.5, "March": 130815.4,
                        "April": 173641.0, "May": 180419.5, "June":187157.5 ,
                        "July": 191786.5, "August": 171279.3, "September": 148726.1,
                        "October": 102391.7, "November": 62860.4, "December": 55020.23
                    }
                    pv_energy_mwh = {month: kwh / 1000 for month, kwh in pv_energy_kwh.items()}
                    
                    days_in_month = {
                        "January": 31, "February": 28, "March": 31, "April": 30,
                        "May": 31, "June": 30, "July": 31, "August": 31,
                        "September": 30, "October": 31, "November": 30, "December": 31
                    }
                    
                    monthly_available_power = df_power_consumption.mean().to_dict()
                    max_monthly_consumption = {
                        month: electrolyser_power * 24 * monthly_service_ratios[month] * days_in_month[month]
                        for month in days_in_month
                    }
                    
                    # Calculate actual spot and PPA energy based on hours breakdown from extended_info
                    monthly_spot_energy = {}
                    monthly_ppa_energy = {}
                    
                    for month in calendar.month_name[1:]:  # January to December
                        spot_energy_total = 0
                        ppa_energy_total = 0
                        
                        # Sum across all years in extended_info
                        for year_str in extended_info:
                            if month in extended_info[year_str]:
                                info = extended_info[year_str][month]
                                spot_hours = info.get('spot_hours', 0) or 0
                                ppa_hours = info.get('ppa_hours', 0) or 0
                                
                                # Convert hours to energy (hours * electrolyzer power)
                                spot_energy_total += spot_hours * electrolyser_power
                                ppa_energy_total += ppa_hours * electrolyser_power
                        
                        # Average across years if multiple years present
                        num_years = len([y for y in extended_info if month in extended_info[y]])
                        if num_years > 0:
                            monthly_spot_energy[month] = spot_energy_total / num_years
                            monthly_ppa_energy[month] = ppa_energy_total / num_years
                        else:
                            # Fallback to existing calculation
                            monthly_spot_energy[month] = monthly_available_power.get(month, 0)
                            monthly_ppa_energy[month] = 0
                    
                    # Calculate energy breakdown using actual spot/PPA hours from extended_info
                    pv_direct_mwh = {}
                    spot_energy_mwh = {}
                    ppa_energy_mwh = {}
                    
                    for month, pv_energy in pv_energy_mwh.items():
                        max_consumption = max_monthly_consumption.get(month, 0)
                        
                        # PV directly covers part of consumption
                        direct_pv_usage = min(pv_energy, max_consumption)
                        
                        # Get actual spot and PPA energy from hours breakdown
                        actual_spot_energy = monthly_spot_energy.get(month, 0)
                        actual_ppa_energy = monthly_ppa_energy.get(month, 0)
                        
                        # Remaining consumption after PV
                        remaining_after_pv = max_consumption - direct_pv_usage
                        
                        # Cap spot and PPA energy by remaining consumption needs
                        total_grid_energy = actual_spot_energy + actual_ppa_energy
                        if total_grid_energy > remaining_after_pv and total_grid_energy > 0:
                            # Scale down proportionally if total grid energy exceeds remaining needs
                            scale_factor = remaining_after_pv / total_grid_energy
                            actual_spot_energy *= scale_factor
                            actual_ppa_energy *= scale_factor
                        
                        pv_direct_mwh[month] = direct_pv_usage
                        spot_energy_mwh[month] = actual_spot_energy
                        ppa_energy_mwh[month] = actual_ppa_energy if integrate_ppa else 0
                    
                    # Create DataFrame with actual spot/PPA breakdown
                    if include_battery and battery_capacity_mwh > 0:
                        # For battery case, split spot energy into direct and battery components
                        spot_direct_mwh = {}
                        spot_battery_mwh = {}
                        
                        for month in spot_energy_mwh:
                            total_spot = spot_energy_mwh[month]
                            days_in_current_month = days_in_month.get(month, 30)
                            monthly_battery_capacity = battery_capacity_mwh * days_in_current_month
                            
                            # Assume battery gets cheapest 30% of spot energy (up to battery capacity)
                            battery_portion = min(total_spot * 0.3, monthly_battery_capacity, total_spot)
                            direct_portion = total_spot - battery_portion
                            
                            spot_direct_mwh[month] = direct_portion
                            spot_battery_mwh[month] = battery_portion
                        
                        df_plot_data = pd.DataFrame({
                            'Maximum Consumption (MWh)': pd.Series(max_monthly_consumption),
                            'PV': pd.Series(pv_direct_mwh),
                            'Spot Direct': pd.Series(spot_direct_mwh),
                            'Spot Battery': pd.Series(spot_battery_mwh),
                            'PPA': pd.Series(ppa_energy_mwh)
                        })
                        
                        # Calculate combined spot for compatibility
                        df_plot_data['Spot'] = df_plot_data['Spot Direct'] + df_plot_data['Spot Battery']
                        
                    else:
                        # Without battery: use direct spot/PPA breakdown
                        df_plot_data = pd.DataFrame({
                            'Maximum Consumption (MWh)': pd.Series(max_monthly_consumption),
                            'PV': pd.Series(pv_direct_mwh),
                            'Spot': pd.Series(spot_energy_mwh),
                            'PPA': pd.Series(ppa_energy_mwh)
                        })
                    
                    month_order = list(calendar.month_name)[1:]
                    df_plot_data = df_plot_data.reindex(month_order)
                    
                    # Calculate weighted average spot price from extended_info
                    def calculate_weighted_avg_spot_price(extended_info, df_result):
                        """Calculate weighted average spot price based on actual hours and prices"""
                        total_hours = 0
                        total_cost = 0
                        
                        for year_str in extended_info:
                            for month in extended_info[year_str]:
                                info = extended_info[year_str][month]
                                
                                # Handle different extended_info structures
                                if 'total_hours' in info:
                                    hours = info['total_hours'] if info['total_hours'] is not None else 0
                                elif 'target_hours' in info:
                                    hours = info['target_hours'] if info['target_hours'] is not None else 0
                                elif 'qualifying_hours' in info:
                                    hours = info['qualifying_hours'] if info['qualifying_hours'] is not None else 0
                                else:
                                    hours = 0
                                
                                # Get average price - different field names in different strategies
                                avg_price = info.get('actual_avg_price', info.get('average_cost', info.get('average_qualifying_price', target_price)))
                                
                                if hours > 0 and avg_price > 0:
                                    total_hours += hours
                                    total_cost += hours * avg_price
                        
                        return total_cost / total_hours if total_hours > 0 else target_price
                    
                    actual_spot_price = calculate_weighted_avg_spot_price(extended_info, df_result)
                    
                    # Calculate LCOE using actual weighted average spot price
                    pv_energy_dict = df_plot_data['PV'].to_dict()
                    spot_energy_dict = df_plot_data['Spot'].to_dict()
                    ppa_energy_dict = df_plot_data['PPA'].to_dict()
                    
                    lcoe = calculate_lcoe(pv_energy_dict, spot_energy_dict, ppa_energy_dict, 
                                        pv_price, actual_spot_price, ppa_price)
                    
                    fig2, ax3 = plt.subplots(figsize=(12, 6))
                    
                    # Choose columns and colors based on battery inclusion
                    if include_battery and battery_capacity_mwh > 0:
                        plot_columns = ['PV', 'Spot Direct', 'Spot Battery'] + (['PPA'] if integrate_ppa else [])
                        plot_colors = ['blue', 'darkgreen', 'lightgreen'] + (['red'] if integrate_ppa else [])
                    else:
                        plot_columns = ['PV', 'Spot'] + (['PPA'] if integrate_ppa else [])
                        plot_colors = ['blue', 'green'] + (['red'] if integrate_ppa else [])
                    
                    df_plot_data[plot_columns].plot(
                        kind='bar', stacked=True, ax=ax3, color=plot_colors
                    )
                    
                    # Add cumulative energy totals on top of bars
                    for i, month in enumerate(df_plot_data.index):
                        # Calculate total energy for this month
                        if include_battery and battery_capacity_mwh > 0:
                            total_energy = (df_plot_data.loc[month, 'PV'] + 
                                          df_plot_data.loc[month, 'Spot Direct'] + 
                                          df_plot_data.loc[month, 'Spot Battery'] + 
                                          (df_plot_data.loc[month, 'PPA'] if integrate_ppa else 0))
                        else:
                            total_energy = (df_plot_data.loc[month, 'PV'] + 
                                          df_plot_data.loc[month, 'Spot'] + 
                                          (df_plot_data.loc[month, 'PPA'] if integrate_ppa else 0))
                        
                        # Add total energy label on top of bar
                        if total_energy > 0:
                            ax3.text(i, total_energy + (total_energy * 0.02), f'{total_energy:.1f} MWh', 
                                    ha='center', va='bottom', fontsize=9, fontweight='bold', 
                                    color='black')
                    
                    # Add percentage labels inside bars with white text
                    for i, month in enumerate(df_plot_data.index):
                        if include_battery and battery_capacity_mwh > 0:
                            pv_val = df_plot_data.loc[month, 'PV']
                            spot_direct_val = df_plot_data.loc[month, 'Spot Direct']
                            spot_battery_val = df_plot_data.loc[month, 'Spot Battery']
                            ppa_val = df_plot_data.loc[month, 'PPA'] if integrate_ppa else 0
                            
                            total_plotted = pv_val + spot_direct_val + spot_battery_val + ppa_val
                            
                            if total_plotted > 0:
                                # Calculate percentages
                                pv_pct = (pv_val / total_plotted) * 100
                                spot_direct_pct = (spot_direct_val / total_plotted) * 100
                                spot_battery_pct = (spot_battery_val / total_plotted) * 100
                                ppa_pct = (ppa_val / total_plotted) * 100 if integrate_ppa else 0
                                
                                # Position for text (middle of each bar segment)
                                pv_mid = pv_val / 2
                                spot_direct_mid = pv_val + (spot_direct_val / 2)
                                spot_battery_mid = pv_val + spot_direct_val + (spot_battery_val / 2)
                                ppa_mid = pv_val + spot_direct_val + spot_battery_val + (ppa_val / 2)
                                
                                # Add percentage text if segment is large enough
                                if pv_pct > 3:
                                    ax3.text(i, pv_mid, f'{pv_pct:.1f}%', 
                                            ha='center', va='center', color='white', fontweight='bold', fontsize=9)
                                
                                if spot_direct_pct > 3:
                                    ax3.text(i, spot_direct_mid, f'{spot_direct_pct:.1f}%', 
                                            ha='center', va='center', color='white', fontweight='bold', fontsize=9)
                                
                                if spot_battery_pct > 3:
                                    ax3.text(i, spot_battery_mid, f'{spot_battery_pct:.1f}%', 
                                            ha='center', va='center', color='white', fontweight='bold', fontsize=9)
                                
                                if integrate_ppa and ppa_pct > 3:
                                    ax3.text(i, ppa_mid, f'{ppa_pct:.1f}%', 
                                            ha='center', va='center', color='white', fontweight='bold', fontsize=9)
                        else:
                            # Original logic without battery
                            pv_val = df_plot_data.loc[month, 'PV']
                            spot_val = df_plot_data.loc[month, 'Spot']
                            ppa_val = df_plot_data.loc[month, 'PPA'] if integrate_ppa else 0
                            
                            total_plotted = pv_val + spot_val + ppa_val
                            
                            if total_plotted > 0:
                                # Calculate percentages based on plotted total
                                pv_pct = (pv_val / total_plotted) * 100
                                spot_pct = (spot_val / total_plotted) * 100
                                ppa_pct = (ppa_val / total_plotted) * 100 if integrate_ppa else 0
                                
                                # Position for text (middle of each bar segment)
                                pv_mid = pv_val / 2
                                spot_mid = pv_val + (spot_val / 2)
                                ppa_mid = pv_val + spot_val + (ppa_val / 2)
                                
                                # Add percentage text if segment is large enough
                                if pv_pct > 3:
                                    ax3.text(i, pv_mid, f'{pv_pct:.1f}%', 
                                            ha='center', va='center', color='white', fontweight='bold', fontsize=9)
                                
                                if spot_pct > 3:
                                    ax3.text(i, spot_mid, f'{spot_pct:.1f}%', 
                                            ha='center', va='center', color='white', fontweight='bold', fontsize=9)
                                
                                if integrate_ppa and ppa_pct > 3:
                                    ax3.text(i, ppa_mid, f'{ppa_pct:.1f}%', 
                                            ha='center', va='center', color='white', fontweight='bold', fontsize=9)
                    
                    # Set chart title based on battery inclusion
                    if include_battery and battery_capacity_mwh > 0:
                        chart_title = f'Monthly Energy Coverage (incl. {battery_capacity_mwh:.1f} MWh Daily Battery Storage)\nStacked: PV + Spot Energy + PPA Energy with Cumulative Totals'
                    else:
                        chart_title = 'Monthly Energy Coverage\nStacked: PV + Spot Energy + PPA Energy with Cumulative Totals'
                    
                    ax3.set_title(chart_title)
                    ax3.set_xlabel('Month')
                    ax3.set_ylabel('Energy (MWh)')
                    ax3.tick_params(axis='x', rotation=45)
                    
                    plt.tight_layout()
                    st.pyplot(fig2)
                    
                    # Create pie chart for energy coverage distribution
                    if include_battery and battery_capacity_mwh > 0:
                        pie_section_title = f"**🥧 Energy Coverage Distribution (with {storage_hours}h Daily Battery):**"
                    else:
                        pie_section_title = "**🥧 Energy Coverage Distribution:**"
                    
                    st.write(pie_section_title)
                    
                    # Calculate total energy for each source
                    total_pv_energy = sum(df_plot_data['PV'])
                    total_spot_energy = sum(df_plot_data['Spot'])
                    total_ppa_energy = sum(df_plot_data['PPA']) if integrate_ppa else 0
                    total_energy_consumed = total_pv_energy + total_spot_energy + total_ppa_energy
                    
                    # Calculate PV-specific CH₄ production and economics
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
                    
                    # Create pie chart data
                    if include_battery and battery_capacity_mwh > 0:
                        total_pv_energy = sum(df_plot_data['PV'])
                        total_spot_direct_energy = sum(df_plot_data['Spot Direct'])
                        total_spot_battery_energy = sum(df_plot_data['Spot Battery'])
                        pie_data = [total_pv_energy, total_spot_direct_energy, total_spot_battery_energy] + ([total_ppa_energy] if integrate_ppa else [])
                        pie_labels = ['PV', 'Spot Direct', 'Spot Battery'] + (['PPA'] if integrate_ppa else [])
                        pie_colors = ['blue', 'darkgreen', 'lightgreen'] + (['red'] if integrate_ppa else [])
                    else:
                        pie_data = [total_pv_energy, total_spot_energy] + ([total_ppa_energy] if integrate_ppa else [])
                        pie_labels = ['PV', 'Spot'] + (['PPA'] if integrate_ppa else [])
                        pie_colors = ['blue', 'green'] + (['red'] if integrate_ppa else [])
                    
                    # Filter out zero values for cleaner pie chart
                    filtered_data = []
                    filtered_labels = []
                    filtered_colors = []
                    
                    for i, value in enumerate(pie_data):
                        if value > 0:
                            filtered_data.append(value)
                            filtered_labels.append(pie_labels[i])
                            filtered_colors.append(pie_colors[i])
                    
                    if filtered_data:  # Only create pie chart if there's data
                        fig3, ax4 = plt.subplots(figsize=(6, 4))
                        
                        # Calculate percentages
                        total_energy = sum(filtered_data)
                        percentages = [value/total_energy*100 for value in filtered_data]
                        
                        # Create pie chart with better label positioning
                        wedges, texts, autotexts = ax4.pie(
                            filtered_data, 
                            labels=filtered_labels,
                            colors=filtered_colors,
                            autopct='%1.1f%%',  # Show all percentages
                            startangle=90,
                            pctdistance=0.85,  # Distance of percentage labels from center
                            labeldistance=1.1,  # Distance of labels from center
                            textprops={'fontsize': 10, 'fontweight': 'bold'}
                        )
                        
                        # Style the percentage labels
                        for autotext in autotexts:
                            autotext.set_color('white')
                            autotext.set_fontweight('bold')
                            autotext.set_bbox(dict(boxstyle='round,pad=0.2', facecolor='black', alpha=0.7))
                        
                        # Style the labels
                        for i, (text, value) in enumerate(zip(texts, filtered_data)):
                            text.set_fontweight('bold')
                            text.set_fontsize(11)
                            # Add energy value to the label
                            original_text = text.get_text()
                            text.set_text(f'{original_text}\n({value:.1f} MWh)')
                            text.set_bbox(dict(boxstyle='round,pad=0.3', 
                                             facecolor='white', 
                                             edgecolor=filtered_colors[i], 
                                             alpha=0.9))
                        
                        # Set pie chart title based on battery inclusion
                        if include_battery and battery_capacity_mwh > 0:
                            pie_chart_title = f'Energy Coverage Distribution\n(Daily Battery: {storage_hours}h = {battery_capacity_mwh:.1f} MWh/day)'
                        else:
                            pie_chart_title = 'Energy Coverage Distribution'
                        
                        ax4.set_title(pie_chart_title, fontsize=14, fontweight='bold', pad=20)
                        
                        # Equal aspect ratio ensures that pie is drawn as a circle
                        ax4.axis('equal')
                        
                        plt.tight_layout()
                        st.pyplot(fig3)
                    
                    # Display pricing information
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("**Target Average Spot Price**", f"{target_price:.0f} €/MWh")
                    with col2:
                        st.metric("**Actual Average Spot Price**", f"{actual_spot_price:.2f} €/MWh")
                    with col3:
                        price_diff = actual_spot_price - target_price
                        st.metric("**Spot Price Difference**", f"{price_diff:.2f} €/MWh", 
                                 delta=f"{price_diff:.2f} €/MWh")
                    
                    # Display LCOE
                    st.metric(f"**LCOE (Levelized Cost of Energy) for {actual_spot_price:.2f}€/MWh actual average spot price:**", 
                             f"{lcoe:.2f} €/MWh")
                    
                    # Create detailed monthly breakdown table
                    st.write("**📊 Monthly Energy Breakdown:**")
                    
                    monthly_breakdown = []
                    for month in df_plot_data.index:
                        if include_battery and battery_capacity_mwh > 0:
                            pv_energy = df_plot_data.loc[month, 'PV']
                            spot_direct_energy = df_plot_data.loc[month, 'Spot Direct']
                            spot_battery_energy = df_plot_data.loc[month, 'Spot Battery']
                            spot_energy = spot_direct_energy + spot_battery_energy
                            ppa_energy = df_plot_data.loc[month, 'PPA']
                            total_energy = pv_energy + spot_direct_energy + spot_battery_energy + ppa_energy
                        else:
                            pv_energy = df_plot_data.loc[month, 'PV']
                            spot_energy = df_plot_data.loc[month, 'Spot']
                            ppa_energy = df_plot_data.loc[month, 'PPA']
                            total_energy = pv_energy + spot_energy + ppa_energy
                        
                        # Get actual average price for this month from extended_info
                        month_spot_price = target_price  # fallback
                        for year_str in extended_info:
                            if month in extended_info[year_str]:
                                info = extended_info[year_str][month]
                                # Handle different extended_info structures
                                month_spot_price = info.get('actual_avg_price', info.get('average_cost', info.get('average_qualifying_price', target_price)))
                                break  # Use first year found (or could average across years)
                        
                        # Calculate coverage ratios and costs
                        if include_battery and battery_capacity_mwh > 0:
                            pv_ratio = (pv_energy / total_energy * 100) if total_energy > 0 else 0
                            spot_direct_ratio = (spot_direct_energy / total_energy * 100) if total_energy > 0 else 0
                            spot_battery_ratio = (spot_battery_energy / total_energy * 100) if total_energy > 0 else 0
                            ppa_ratio = (ppa_energy / total_energy * 100) if (total_energy > 0 and integrate_ppa) else 0
                            
                            # Calculate costs using actual monthly spot price
                            pv_cost = pv_energy * pv_price
                            spot_direct_cost = spot_direct_energy * month_spot_price
                            # Battery uses cheaper spot energy (estimate 20% discount)
                            battery_month_price = battery_avg_price.get(month, month_spot_price)
                            spot_battery_cost = spot_battery_energy * battery_month_price
                            ppa_cost = (ppa_energy * ppa_price) if integrate_ppa else 0
                            total_cost = pv_cost + spot_direct_cost + spot_battery_cost + (ppa_cost if integrate_ppa else 0)
                            
                            # Service ratio and shutdown
                            service_ratio_pct = monthly_service_ratios.get(month, 1.0) * 100
                            shutdown_hours = days_in_month.get(month, 30) * 24 * (1 - monthly_service_ratios.get(month, 1.0))
                            
                            row = {
                                'Month': month,
                                'PV Energy (MWh)': f"{pv_energy:.1f}",
                                'PV Coverage (%)': f"{pv_ratio:.1f}%",
                                'PV Cost (€)': f"{pv_cost:,.0f}",
                                'Spot Direct (MWh)': f"{spot_direct_energy:.1f}",
                                'Spot Direct (%)': f"{spot_direct_ratio:.1f}%",
                                'Spot Direct Cost (€)': f"{spot_direct_cost:,.0f}",
                                'Spot Battery (MWh)': f"{spot_battery_energy:.1f}",
                                'Spot Battery (%)': f"{spot_battery_ratio:.1f}%",
                                'Spot Battery Cost (€)': f"{spot_battery_cost:,.0f}",
                                'Total Energy (MWh)': f"{total_energy:.1f}",
                                'Total Cost (€)': f"{total_cost:,.0f}",
                                'Avg Cost (€/MWh)': f"{total_cost/total_energy:.2f}" if total_energy > 0 else "0.00",
                                'Service Ratio (%)': f"{service_ratio_pct:.1f}%",
                                'Shutdown (h)': f"{shutdown_hours:.0f}"
                            }
                            if integrate_ppa:
                                row.update({
                                    'PPA Energy (MWh)': f"{ppa_energy:.1f}",
                                    'PPA Coverage (%)': f"{ppa_ratio:.1f}%",
                                    'PPA Cost (€)': f"{ppa_cost:,.0f}"
                                })
                            monthly_breakdown.append(row)
                        else:
                            # Original structure without battery
                            pv_ratio = (pv_energy / total_energy * 100) if total_energy > 0 else 0
                            spot_ratio = (spot_energy / total_energy * 100) if total_energy > 0 else 0
                            ppa_ratio = (ppa_energy / total_energy * 100) if (total_energy > 0 and integrate_ppa) else 0
                            
                            # Calculate costs using actual monthly spot price
                            pv_cost = pv_energy * pv_price
                            spot_cost = spot_energy * month_spot_price
                            ppa_cost = (ppa_energy * ppa_price) if integrate_ppa else 0
                            total_cost = pv_cost + spot_cost + (ppa_cost if integrate_ppa else 0)
                            
                            # Service ratio and shutdown
                            service_ratio_pct = monthly_service_ratios.get(month, 1.0) * 100
                            shutdown_hours = days_in_month.get(month, 30) * 24 * (1 - monthly_service_ratios.get(month, 1.0))
                            
                            row = {
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
                                'Shutdown (h)': f"{shutdown_hours:.0f}"
                            }
                            if integrate_ppa:
                                row.update({
                                    'PPA Energy (MWh)': f"{ppa_energy:.1f}",
                                    'PPA Coverage (%)': f"{ppa_ratio:.1f}%",
                                    'PPA Cost (€)': f"{ppa_cost:,.0f}"
                                })
                            monthly_breakdown.append(row)
                    
                    breakdown_df = pd.DataFrame(monthly_breakdown)
                    
                    # Calculate yearly totals and averages
                    if include_battery and battery_capacity_mwh > 0:
                        total_pv_energy = sum(df_plot_data['PV'])
                        total_spot_direct_energy = sum(df_plot_data['Spot Direct'])
                        total_spot_battery_energy = sum(df_plot_data['Spot Battery'])
                        total_spot_energy = total_spot_direct_energy + total_spot_battery_energy
                        total_ppa_energy = sum(df_plot_data['PPA']) if integrate_ppa else 0
                        total_energy_year = total_pv_energy + total_spot_direct_energy + total_spot_battery_energy + total_ppa_energy
                        
                        total_pv_cost = total_pv_energy * pv_price
                        total_spot_direct_cost = total_spot_direct_energy * actual_spot_price
                        # Battery uses cheaper spot energy (average discount)
                        avg_battery_discount = 0.8  # 20% discount estimate
                        total_spot_battery_cost = total_spot_battery_energy * actual_spot_price * avg_battery_discount
                        total_ppa_cost = (total_ppa_energy * ppa_price) if integrate_ppa else 0
                        total_cost_year = total_pv_cost + total_spot_direct_cost + total_spot_battery_cost + (total_ppa_cost if integrate_ppa else 0)
                        
                        # Calculate yearly averages for percentages
                        avg_pv_ratio = (total_pv_energy / total_energy_year * 100) if total_energy_year > 0 else 0
                        avg_spot_direct_ratio = (total_spot_direct_energy / total_energy_year * 100) if total_energy_year > 0 else 0
                        avg_spot_battery_ratio = (total_spot_battery_energy / total_energy_year * 100) if total_energy_year > 0 else 0
                        avg_ppa_ratio = (total_ppa_energy / total_energy_year * 100) if (total_energy_year > 0 and integrate_ppa) else 0
                        
                        # Add yearly average row with battery breakdown
                        yearly_average = {
                            'Month': '📊 YEARLY TOTAL',
                            'PV Energy (MWh)': f"{total_pv_energy:.1f}",
                            'PV Coverage (%)': f"{avg_pv_ratio:.1f}%",
                            'PV Cost (€)': f"{total_pv_cost:,.0f}",
                            'Spot Direct (MWh)': f"{total_spot_direct_energy:.1f}",
                            'Spot Direct (%)': f"{avg_spot_direct_ratio:.1f}%",
                            'Spot Direct Cost (€)': f"{total_spot_direct_cost:,.0f}",
                            'Spot Battery (MWh)': f"{total_spot_battery_energy:.1f}",
                            'Spot Battery (%)': f"{avg_spot_battery_ratio:.1f}%",
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
                        
                        # Add yearly average row
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
                    
                    # Add the yearly row to the dataframe
                    breakdown_df = pd.concat([breakdown_df, pd.DataFrame([yearly_average])], ignore_index=True)
                    
                    # Style the dataframe to highlight the yearly total row
                    def highlight_yearly_row(row):
                        if row.name == len(breakdown_df) - 1:  # Last row (yearly total)
                            return ['background-color: #1f77b4; color: white; font-weight: bold'] * len(row)
                        return [''] * len(row)
                    
                    styled_df = breakdown_df.style.apply(highlight_yearly_row, axis=1)
                    
                    st.dataframe(styled_df, width='stretch')
                    
                    # Calculate and display cost per KG of CH4 produced
                    total_yearly_ch4_kg = sum(monthly_ch4_production.values())
                    cost_per_kg_ch4 = total_cost_year / total_yearly_ch4_kg if total_yearly_ch4_kg > 0 else 0
                    
                    # Display cost per KG CH4 alongside LCOE
                    #st.metric(f"**Energy Cost per KG CH₄ for {actual_spot_price:.2f}€/MWh actual average spot price:**", 
                             #f"{cost_per_kg_ch4:.2f} €/kg CH₄")
                    
                    # Display PV Economics Results
                    st.markdown("---")
                    st.markdown("#### ☀️ PV Installation Economics Results")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("**Total Yearly CH₄ Production**", f"{total_yearly_ch4_kg:,.0f} kg")
                    with col2:
                        st.metric("**PV Yearly Energy Ratio**", f"{pv_energy_ratio:.1%}")
                    with col3:
                        st.metric("**PV-specific Yearly CH₄ Production**", f"{pv_ch4_production_kg:,.0f} kg")
                    with col4:
                        st.metric("**PV-specific Yearly GWh PCI CH₄**", f"{yearly_GWh_PCI_ch4_pv:.2f} GWh")
                    
                    # LCOE Calculation for CH4 (excluding methanation costs)
                    # Using formula: LCOE_CH4 = Sum(CAPEX_t + O&M_t)/(1+r)^t / Sum(CH4_Output_t)/(1+r)^t
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
                    
                    # Key PV Economics Metrics displayed side by side
                    economics_col1, economics_col2 = st.columns(2)
                    with economics_col1:
                        st.metric("**€/MWh PCI CH₄ (PV-specific)**", f"{euro_per_MWh_PCI_CH4_pv:.2f} €/MWh")
                    with economics_col2:
                        st.metric("**LCOE CH₄ (PV-specific, excl. methanation)**", f"{lcoe_ch4_euro_per_kg:.2f} €/kg CH₄")
                    
                    # Additional PV Economics Details
                    st.markdown("**PV Installation Details:**")
                    pv_breakdown_col1, pv_breakdown_col2 = st.columns(2)
                    
                    with pv_breakdown_col1:
                        st.write(f"• **Surface**: {pv_surface_hectares} hectares")
                        st.write(f"• **Power Density**: {power_density_mwp_per_ha} MWp/ha")
                        st.write(f"• **Estimated Power**: {estimated_power_mwp:.2f} MWp")
                        if include_battery:
                            st.write(f"• **Storage Hours**: {storage_hours}h")
                            st.write(f"• **Battery Capacity**: {battery_capacity_mwh:.1f} MWh")
                        st.write(f"• **Project Lifetime**: {pv_project_years} years")
                        st.write(f"• **Discount Rate**: {discount_rate:.1f}%")
                    
                    with pv_breakdown_col2:
                        st.write(f"• **PV Cost**: {pv_cost_per_wp:.2f} €/Wp")
                        if include_battery:
                            st.write(f"• **Battery Cost**: {battery_cost_per_kwh} €/kWh")
                        st.write(f"• **CAPEX**: {pv_capex:,.0f} €")
                        st.write(f"• **Annual OPEX**: {pv_opex:,.0f} €/year")
                        st.write(f"• **PCI CH₄**: {pci_ch4_kwh_per_kg} kWh/kg")
                    
                    # Financial Summary
                    st.markdown("**Financial Summary:**")
                    financial_col1, financial_col2 = st.columns(2)
                    
                    with financial_col1:
                        st.write(f"• **Total OPEX over {pv_project_years} years**: {pv_opex * pv_project_years:,.0f} €")
                        st.write(f"• **Total Investment**: {pv_capex + (pv_opex * pv_project_years):,.0f} €")
                    
                    with financial_col2:
                        st.write(f"• **PV Energy**: {total_pv_energy:.1f} MWh/year")
                        st.write(f"• **PV CH₄ Production**: {pv_ch4_production_kg/1000:.1f} tonnes/year")
                    
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
                

                

                
                # Add comprehensive 3D analysis (only when PPA is integrated)
                st.markdown("---")
                if integrate_ppa:
                    st.write("**🎯 Complete 3D Analysis: All Three Price Sources:**")
                else:
                    st.write("**🎯 3D Analysis skipped:** PPA excluded (PPA < 60€/MWh)")

                base_pv_energy = sum(df_plot_data['PV'])
                base_spot_energy = sum(df_plot_data['Spot'])
                base_ppa_energy = sum(df_plot_data['PPA'])
                total_energy = base_pv_energy + base_spot_energy + base_ppa_energy

                if total_energy > 0:
                    # Create a comprehensive figure with multiple visualization approaches
                    fig_complete = plt.figure(figsize=(16, 12))
                    
                    # Method 1: 3D Scatter plot with color coding
                    ax1 = fig_complete.add_subplot(221, projection='3d')
                    
                    # Create sample points across all three dimensions
                    n_samples = 100
                    pv_samples = np.random.uniform(0, 100, n_samples)
                    ppa_samples = np.random.uniform(50, 150, n_samples)
                    spot_samples = np.random.uniform(5, 50, n_samples)
                    
                    # Calculate LCOE for each sample point
                    lcoe_samples = []
                    for i in range(n_samples):
                        pv_cost = base_pv_energy * pv_samples[i]
                        spot_cost = base_spot_energy * spot_samples[i]
                        ppa_cost = base_ppa_energy * ppa_samples[i]
                        lcoe = (pv_cost + spot_cost + ppa_cost) / total_energy
                        lcoe_samples.append(lcoe)
                    
                    # Create 3D scatter plot with color-coded LCOE
                    scatter = ax1.scatter(pv_samples, ppa_samples, spot_samples, 
                                        c=lcoe_samples, cmap='viridis', s=50, alpha=0.7)
                    
                    # Add current point
                    current_lcoe_3d = (base_pv_energy * pv_price + base_spot_energy * actual_spot_price + base_ppa_energy * ppa_price) / total_energy
                    ax1.scatter([pv_price], [ppa_price], [actual_spot_price], 
                              color='red', s=200, marker='*', label=f'Current: {current_lcoe_3d:.2f}€/MWh')
                    
                    ax1.set_xlabel('PV Price (€/MWh)')
                    ax1.set_ylabel('PPA Price (€/MWh)')
                    ax1.set_zlabel('Spot Price (€/MWh)')
                    ax1.set_title('3D Price Space\n(Color = LCOE)', fontweight='bold')
                    ax1.legend()
                    
                    # Add colorbar for scatter plot
                    cbar1 = plt.colorbar(scatter, ax=ax1, shrink=0.8, aspect=20)
                    cbar1.set_label('LCOE (€/MWh)')
                    
                    # Method 2: Multiple 2D contour plots
                    ax2 = fig_complete.add_subplot(222)
                    
                    # Create contour plot for PV vs PPA (at current spot price)
                    pv_contour = np.linspace(0, 100, 20)
                    ppa_contour = np.linspace(50, 150, 20)
                    PV_cont, PPA_cont = np.meshgrid(pv_contour, ppa_contour)
                    
                    LCOE_contour = np.zeros_like(PV_cont)
                    for i in range(len(ppa_contour)):
                        for j in range(len(pv_contour)):
                            pv_cost = base_pv_energy * PV_cont[i, j]
                            spot_cost = base_spot_energy * actual_spot_price  # Fixed spot
                            ppa_cost = base_ppa_energy * PPA_cont[i, j]
                            LCOE_contour[i, j] = (pv_cost + spot_cost + ppa_cost) / total_energy
                    
                    contour = ax2.contourf(PV_cont, PPA_cont, LCOE_contour, levels=15, cmap='viridis', alpha=0.8)
                    contour_lines = ax2.contour(PV_cont, PPA_cont, LCOE_contour, levels=15, colors='black', alpha=0.4, linewidths=0.5)
                    ax2.clabel(contour_lines, inline=True, fontsize=8, fmt='%.1f')
                    
                    # Add current point
                    ax2.plot(pv_price, ppa_price, 'r*', markersize=15, label=f'Current: {current_lcoe_3d:.2f}€/MWh')
                    
                    ax2.set_xlabel('PV Price (€/MWh)')
                    ax2.set_ylabel('PPA Price (€/MWh)')
                    ax2.set_title(f'LCOE Contours: PV vs PPA\n(Spot = {actual_spot_price:.2f}€/MWh)', fontweight='bold')
                    ax2.legend()
                    
                    plt.colorbar(contour, ax=ax2, label='LCOE (€/MWh)')
                    
                    # Method 3: Parallel coordinates plot
                    ax3 = fig_complete.add_subplot(223)
                    
                    # Create multiple scenarios
                    n_scenarios = 50
                    scenarios_pv = np.linspace(0, 100, n_scenarios)
                    scenarios_ppa = np.linspace(50, 150, n_scenarios)
                    scenarios_spot = np.linspace(5, 50, n_scenarios)
                    
                    # Calculate LCOE for different scenarios
                    for i in range(0, n_scenarios, 5):  # Every 5th scenario to avoid clutter
                        pv_p = scenarios_pv[i]
                        ppa_p = scenarios_ppa[i]
                        spot_p = scenarios_spot[i]
                        
                        lcoe_scenario = (base_pv_energy * pv_p + base_spot_energy * spot_p + base_ppa_energy * ppa_p) / total_energy
                        
                        # Normalize values for parallel coordinates
                        pv_norm = pv_p / 100
                        ppa_norm = (ppa_p - 50) / 100
                        spot_norm = (spot_p - 5) / 45
                        lcoe_norm = (lcoe_scenario - min(lcoe_samples)) / (max(lcoe_samples) - min(lcoe_samples))
                        
                        # Plot line connecting all dimensions
                        ax3.plot([0, 1, 2, 3], [pv_norm, ppa_norm, spot_norm, lcoe_norm], 
                                alpha=0.3, color=plt.cm.viridis(lcoe_norm))
                    
                    # Current scenario
                    current_pv_norm = pv_price / 100
                    current_ppa_norm = (ppa_price - 50) / 100
                    current_spot_norm = (actual_spot_price - 5) / 45
                    current_lcoe_norm = (current_lcoe_3d - min(lcoe_samples)) / (max(lcoe_samples) - min(lcoe_samples))
                    
                    ax3.plot([0, 1, 2, 3], [current_pv_norm, current_ppa_norm, current_spot_norm, current_lcoe_norm], 
                            'r-', linewidth=3, marker='o', markersize=8, label='Current Configuration')
                    
                    ax3.set_xticks([0, 1, 2, 3])
                    ax3.set_xticklabels(['PV\n(0-100€)', 'PPA\n(50-150€)', 'Spot\n(5-50€)', 'LCOE\n(normalized)'])
                    ax3.set_ylabel('Normalized Values (0-1)')
                    ax3.set_title('Parallel Coordinates:\nPrice Dependencies', fontweight='bold')
                    ax3.legend()
                    ax3.grid(True, alpha=0.3)
                    
                    # Method 4: Heatmap matrix showing price combinations
                    ax4 = fig_complete.add_subplot(224)
                    
                    # Create a simplified grid for heatmap
                    pv_heat = np.linspace(0, 100, 10)
                    ppa_heat = np.linspace(50, 150, 10)
                    
                    # Use current spot price
                    spot_fixed = actual_spot_price
                    
                    heat_matrix = np.zeros((len(ppa_heat), len(pv_heat)))
                    for i, ppa_p in enumerate(ppa_heat):
                        for j, pv_p in enumerate(pv_heat):
                            pv_cost = base_pv_energy * pv_p
                            spot_cost = base_spot_energy * spot_fixed
                            ppa_cost = base_ppa_energy * ppa_p
                            heat_matrix[i, j] = (pv_cost + spot_cost + ppa_cost) / total_energy
                    
                    heatmap = ax4.imshow(heat_matrix, cmap='viridis', aspect='auto', origin='lower')
                    
                    # Add text annotations
                    for i in range(len(ppa_heat)):
                        for j in range(len(pv_heat)):
                            text = ax4.text(j, i, f'{heat_matrix[i, j]:.1f}',
                                          ha="center", va="center", color="white", fontsize=8)
                    
                    # Find current position in grid
                    current_j = np.argmin(np.abs(pv_heat - pv_price))
                    current_i = np.argmin(np.abs(ppa_heat - ppa_price))
                    ax4.plot(current_j, current_i, 'r*', markersize=20)
                    
                    ax4.set_xticks(range(len(pv_heat)))
                    ax4.set_xticklabels([f'{x:.0f}' for x in pv_heat])
                    ax4.set_yticks(range(len(ppa_heat)))
                    ax4.set_yticklabels([f'{y:.0f}' for y in ppa_heat])
                    ax4.set_xlabel('PV Price (€/MWh)')
                    ax4.set_ylabel('PPA Price (€/MWh)')
                    ax4.set_title(f'LCOE Heatmap\n(Spot = {spot_fixed}€/MWh)', fontweight='bold')
                    
                    plt.colorbar(heatmap, ax=ax4, label='LCOE (€/MWh)')
                    
                    plt.suptitle('Comprehensive LCOE Analysis: All Three Price Sources', 
                                fontsize=16, fontweight='bold', y=0.98)
                    plt.tight_layout()
                    st.pyplot(fig_complete)
                else:
                    st.warning("⚠️ No energy data available for 3D analysis. Please check the simulation parameters.")
                
                # Mark simulation as completed
                st.session_state.simulation_run = True
                
            except Exception as e:
                st.error(f"❌ Error running simulation: {str(e)}")
                st.exception(e)  # Show full error details for debugging
else:
    # Show message when no simulation needs to be run
    if 'simulation_run' in st.session_state:
        st.success("✅ Simulation up to date. Change any parameter above to refresh results.")
    else:
        st.info("👆 Adjust parameters in the sidebar to start the simulation.")



# Footer
st.markdown("---")
st.markdown(
    f"""
    <div style='text-align: center; color: #666;'>
        <p>MetaSTAAQ LCOE Simulation Dashboard | 
        Built with Streamlit | 
        Data-driven energy analysis</p>
        <p style='margin-top: 10px; font-size: 14px;'>
        © STAAQ Technology All Rights Reserved {pd.Timestamp.now().year}
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

# Instructions
with st.expander("ℹ️ How to use this dashboard"):
    st.markdown("""
    1. **Select Years**: Choose which years to include in the analysis
    2. **Set Parameters**: Adjust electrolyzer power, consumption, and service ratio
    3. **Set Target Price**: Adjust the average target spot price for analysis
    4. **Auto-Update**: Results update automatically when you change any parameter!
    5. **Manual Refresh**: Use the "Manual Refresh" button if needed
    6. **View Results**: Charts and tables are displayed below the parameters
    
    
    **Data Source**: The dashboard uses pre-loaded spot price data for France (2021-2025).
    """)
