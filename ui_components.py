"""
UI Components for the MetaSTAAQ Dashboard
"""

import streamlit as st
import pandas as pd
from config import CUSTOM_CSS, PV_IMAGES


def setup_page_config():
    """Set up the page configuration and custom CSS"""
    st.set_page_config(
        page_title="MetaSTAAQ - LCOE Simulation Dashboard",
        page_icon="⚡",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def display_header():
    """Display the main header"""
    st.markdown('<p class="main-header">⚡ MetaSTAAQ LCOE Simulation Dashboard</p>', unsafe_allow_html=True)


def display_sidebar_logo():
    """Display the sidebar logo"""
    try:
        st.sidebar.image("STAAQ_HD.jpg", width=180)
    except FileNotFoundError:
        st.sidebar.warning("⚠️ Logo file 'STAAQ_HD.jpg' not found")


def display_pv_images():
    """Display PV monthly energy bar chart and parameters table"""
    st.markdown("### ☀️ PV Installation")
    
    if 'pv_energy_data' not in st.session_state or 'pv_params' not in st.session_state:
        st.warning("PV data not available yet.")
        return
    
    pv_energy_mwh = st.session_state.pv_energy_data['pv_energy_mwh']
    pv_params = st.session_state.pv_params
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Create bar chart
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(8, 5))
        months = list(pv_energy_mwh.keys())
        values = list(pv_energy_mwh.values())
        bars = ax.bar(months, values, color='blue')
        ax.set_xlabel('Month')
        ax.set_ylabel('Energy (MWh)')
        ax.set_title('Monthly PV Energy Production')
        plt.xticks(rotation=45, ha='right')

        # Add value labels
        for bar in bars:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                height,
                f'{height:.1f}',
                ha='center',
                va='bottom',
                fontsize=9
            )

        plt.tight_layout()
        st.pyplot(fig)
    
    with col2:
        st.markdown("#### Current PV Parameters")
        yearly_pv_mwh = sum(pv_energy_mwh.values())
        param_data = {
            'Parameter': [
                'Surface Area (ha)',
                'Power Density (MWp/ha)',
                'Latitude',
                'Longitude',
                'System Loss (%)',
                'Project Lifetime (years)',
                'Cost per Wp (€)',
                'Include Battery',
                'Storage Hours',
                'Battery Cost per kWh (€)',
                'Yearly PV Energy (MWh)',
                'Database used',
                'PV technology'
            ],
            'Value': [
                f"{pv_params['pv_surface_hectares']:.1f}",
                f"{pv_params['power_density_mwp_per_ha']:.1f}",
                f"{pv_params['lat']:.4f}",
                f"{pv_params['lon']:.4f}",
                f"{pv_params['loss']:.1f}",
                f"{pv_params['pv_project_years']}",
                f"{pv_params['pv_cost_per_wp']:.2f}",
                'Yes' if pv_params['include_battery'] else 'No',
                f"{pv_params['storage_hours']:.1f}" if pv_params['include_battery'] else 'N/A',
                f"{pv_params['battery_cost_per_kwh']:.0f}" if pv_params['include_battery'] else 'N/A',
                f"{yearly_pv_mwh:.1f}",
                "PVGIS-SARAH3",
                "Crystalline silicon"
            ]
        }
        param_df = pd.DataFrame(param_data)
        st.table(param_df)
    
    st.info("📍 **PV Installation with tracking system**: Analysis based on selected parameters. Data source: PVGIS (Photovoltaic Geographical Information System)")


def display_parameter_change_info(params_changed):
    """Display parameter change information"""
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("### 📊 Simulation Results")
        if params_changed:
            st.info("🔄 Parameters changed - Results updating automatically...")

    with col2:
        manual_refresh = st.button("🔄 Manual Refresh", help="Force refresh the simulation")
        return manual_refresh


def display_strategy_info(strategy_type, target_price, ppa_price, pv_price):
    """Display strategy-specific information"""
    st.write(f"**🎯 Strategy Details: {strategy_type}**")
    
    if strategy_type == "Service Ratio-Based":
        st.write(f"• **Strategy**: Cumulate spot hours while average cost < PPA price")
        st.write(f"• **Price Logic**: Use spot price when spot ≤ PPA, otherwise use PPA price")
        st.write(f"• **Optimization**: Maximize operating hours below PPA price threshold")
        st.write(f"• **No Target Price**: Hours determined by PPA price constraint only")
    else:  # Target Price-Based
        st.write(f"• **Strategy**: Cumulate spot hours while average price ≤ target price")
        st.write(f"• **Target Price**: {target_price:.0f} €/MWh cumulative average limit")
        st.write(f"• **Logic**: Sort hours by price, add cheapest first until cumulative average exceeds target")
        st.write(f"• **Mode**: Single target price threshold for all analysis periods")


def display_metrics_section(target_price, actual_spot_price, price_diff, lcoe_result):
    """Display metrics section"""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("**Target Average Spot Price**", f"{target_price:.0f} €/MWh")
    
    with col2:
        st.metric("**Actual Average Spot Price**", f"{actual_spot_price:.2f} €/MWh")
    
    with col3:
        st.metric("**Spot Price Difference**", f"{price_diff:.2f} €/MWh", 
                 delta=f"{price_diff:.2f} €/MWh" if price_diff != 0 else None)
    
    st.metric(f"**LCOE (Levelized Cost of Energy) for {actual_spot_price:.2f}€/MWh actual average spot price:**", 
             f"{lcoe_result:.2f} €/MWh")


def display_monthly_ch4_production(monthly_production_tonnes, service_ratios):
    """Display monthly CH4 production summary"""
    st.sidebar.markdown("#### 📊 Monthly CH4 Production")
    total_yearly_ch4_tonnes = sum(monthly_production_tonnes.values())
    st.sidebar.metric("Yearly CH₄ Production", f"{total_yearly_ch4_tonnes:,.0f} Tonnes")
    
    # Add expandable section for monthly details
    with st.sidebar.expander("📅 Monthly Details"):
        for month, production in monthly_production_tonnes.items():
            service_pct = service_ratios.get(month, 0) * 100
            st.write(f"**{month[:3]}**: {production:.1f} Tonnes ({service_pct:.0f}%)")


def display_calculated_parameters(h2_flowrate, ch4_flowrate, avg_service_ratio):
    """Display calculated parameters in sidebar"""
    st.sidebar.markdown("#### 📊 Calculated Parameters")
    st.sidebar.metric("H₂ Flow Rate", f"{h2_flowrate} Nm³/h")
    st.sidebar.metric("CH₄ Flow Rate", f"{ch4_flowrate} Nm³/h")
    st.sidebar.metric("Avg Service Ratio", f"{avg_service_ratio:.1%}")


def display_pv_economics_summary(estimated_power_mwp, estimated_power_kwp, battery_capacity_mwh, 
                                pv_capex_calculated, battery_capex, total_capex_calculated, pv_opex,
                                pv_lcoe_eur_per_mwh=None):
    """Display PV economics summary"""
    st.write(f"**Estimated Power**: {estimated_power_mwp:.2f} MWp ({estimated_power_kwp:,.0f} kWp)")
    
    if battery_capacity_mwh > 0:
        st.write(f"**Daily Battery Capacity**: {battery_capacity_mwh:.2f} MWh/day")
    
    st.write(f"**Calculated CAPEX**:")
    st.write(f"• PV: {pv_capex_calculated:,.0f} €")
    if battery_capex > 0:
        st.write(f"• Battery: {battery_capex:,.0f} €")
    st.write(f"• **Total: {total_capex_calculated:,.0f} €**")
    
    st.write(f"**Calculated OPEX**: {pv_opex:,.0f} €/year")
    if pv_lcoe_eur_per_mwh is not None:
        st.write(f"**PV LCOE**: {pv_lcoe_eur_per_mwh:.2f} €/MWh")


def create_loading_spinner(message="Running simulation..."):
    """Create a loading spinner"""
    return st.spinner(message)


def display_error_message(message):
    """Display error message"""
    st.error(message)


def display_warning_message(message):
    """Display warning message"""
    st.warning(message)


def display_info_message(message):
    """Display info message"""
    st.info(message)


def display_success_message(message):
    """Display success message"""
    st.success(message)
