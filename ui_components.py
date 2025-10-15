"""
UI Components for the MetaSTAAQ Dashboard
"""

import streamlit as st
import pandas as pd
from config import CUSTOM_CSS, PV_IMAGES, PV_ENERGY_KWH


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
    """Display PV installation images"""
    st.markdown("### ☀️ Monthly PV Production (Meaux Location)")
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
        st.write(f"• **Strategy**: Operate only when spot price ≤ target price")
        if len(target_price) > 1:
            st.write(f"• **Multi-year Mode**: Using monthly average adjustments for consistency")
        else:
            st.write(f"• **Single-year Mode**: Using direct target price threshold")


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
                                pv_capex_calculated, battery_capex, total_capex_calculated, pv_opex):
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
