"""
UI Components for the MetaSTAAQ Dashboard
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from config import CUSTOM_CSS, PV_IMAGES
import folium
from streamlit_folium import st_folium


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
        st.info("💡 Click on the map to update GPS coordinates")
        map_container = st.container(height=300)
        with map_container:
            lat = pv_params['lat']
            lon = pv_params['lon']
            m = folium.Map(location=[lat, lon], zoom_start=16, tiles="OpenStreetMap")
            folium.CircleMarker(
                location=[lat, lon],
                radius=10,
                color="blue",
                fill=True,
                fill_color="blue",
                fill_opacity=0.7,
                popup="PV Installation Location",
                tooltip="Click to update location"
            ).add_to(m)
            
            # Capture map clicks only (ignore zoom/pan events)
            map_data = st_folium(
                m, 
                width="100%", 
                height=300, 
                key="pv_map",
                returned_objects=["last_clicked"]
            )
            
            # Check if map was clicked and coordinates are different
            if map_data and map_data.get('last_clicked'):
                clicked_lat = map_data['last_clicked']['lat']
                clicked_lon = map_data['last_clicked']['lng']
                
                # Only update if coordinates actually changed (not just map navigation)
                if 'last_map_lat' not in st.session_state or 'last_map_lon' not in st.session_state:
                    st.session_state.last_map_lat = None
                    st.session_state.last_map_lon = None
                
                # Check if this is a new click (coordinates changed)
                if (st.session_state.last_map_lat != clicked_lat or 
                    st.session_state.last_map_lon != clicked_lon):
                    
                    # Store clicked coordinates in session state
                    st.session_state.map_clicked_lat = clicked_lat
                    st.session_state.map_clicked_lon = clicked_lon
                    st.session_state.last_map_lat = clicked_lat
                    st.session_state.last_map_lon = clicked_lon
                    
                    # Show success message
                    st.success(f"📍 Location updated: {clicked_lat:.4f}, {clicked_lon:.4f}")
                    # Trigger a rerun to update the sidebar inputs
                    st.rerun()
        
        graph_container = st.container(height=300)
        with graph_container:
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
        table_container = st.container(height=600)
        with table_container:
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
    st.markdown("### 📊 Simulation Results")
    if params_changed:
        st.info("🔄 Parameters changed - Results updating automatically...")


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


def display_metrics_section(target_price, actual_spot_price, price_diff, lcoe_result, go_enabled=False, go_cost_per_mwh=0.0, ppa_price=None, pv_price=None):
    """Display metrics section"""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("**Average Spot Price**", f"{actual_spot_price:.2f} €/MWh")
    
    with col2:
        if ppa_price is not None:
            st.metric("**PPA Cost**", f"{ppa_price:.2f} €/MWh")
    
    with col3:
        if pv_price is not None:
            st.metric("**PV Cost**", f"{pv_price:.2f} €/MWh")
    
    # Show GO information if enabled
    if go_enabled:
        effective_spot_price = actual_spot_price + go_cost_per_mwh
        st.info(f"🌱 **GO Certificate Enabled**: +{go_cost_per_mwh:.2f} €/MWh added to Spot price → Effective Spot Price: {effective_spot_price:.2f} €/MWh")
    
    st.metric("**Average Electricity Cost**", f"{lcoe_result:.2f} €/MWh")


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


def display_calculated_parameters(h2_flowrate, ch4_flowrate, avg_service_ratio, cons_spec_ch4=None, container=None):
    """Display calculated parameters in sidebar"""
    if container is None:
        container = st.sidebar
        
    container.markdown("#### 📊 Calculated Parameters")
    container.metric("H₂ Flow Rate", f"{h2_flowrate} Nm³/h")
    container.metric("CH₄ Flow Rate", f"{ch4_flowrate} Nm³/h")
    container.metric("Avg Service Ratio", f"{avg_service_ratio:.1%}")
    
    # Calculate and display methanation power consumption if cons_spec_ch4 is provided
    if cons_spec_ch4 is not None:
        # Puissance instantanée (kW) = Débit CH₄ (Nm³/h) × Cons Spec (kWh/Nm³)
        puissance_instantanee_kw = ch4_flowrate * cons_spec_ch4
        
        # Annual consumption (MWhe/year) = Puissance instantanée × Service Ratio × 8760 h / 1000
        annual_consumption_mwh = (puissance_instantanee_kw * avg_service_ratio * 8760) / 1000
        
        container.markdown("---")
        container.markdown("**⚡ Methanation Power**")
        container.metric(
            "Puissance Instantanée", 
            f"{puissance_instantanee_kw:.1f} kW",
            help=f"**Formula:** Débit CH₄ × Cons Spec CH₄\n\n"
                 f"**Calculation:** {ch4_flowrate} Nm³/h × {cons_spec_ch4} kWh/Nm³ = {puissance_instantanee_kw:.1f} kW"
        )
        container.metric(
            "Annual Elec. Consumption", 
            f"{annual_consumption_mwh:.1f} MWhe/year",
            help=f"**Formula:** Puissance instantanée × Service Ratio × 8760 h / 1000\n\n"
                 f"**Calculation:** {puissance_instantanee_kw:.1f} kW × {avg_service_ratio:.1%} × 8760 h / 1000 = {annual_consumption_mwh:.1f} MWhe/year"
        )


def display_pv_economics_summary(estimated_power_mwp, estimated_power_kwp, battery_capacity_mwh, 
                                pv_capex_calculated, battery_capex, total_capex_calculated, pv_opex,
                                battery_opex=0, total_opex=None, pv_lcoe_eur_per_mwh=None):
    """Display PV economics summary"""
    st.write(f"**Estimated Power**: {estimated_power_mwp:.2f} MWp ({estimated_power_kwp:,.0f} kWp)")
    
    if battery_capacity_mwh > 0:
        st.write(f"**Daily Battery Capacity**: {battery_capacity_mwh:.2f} MWh/day")
    
    # Display separate OpEx for PV and Battery
    if total_opex is None:
        total_opex = pv_opex + battery_opex
    
    # Create economics table
    if battery_capex > 0:
        # With battery - show both PV and Battery
        economics_data = {
            'Component': ['PV', 'Battery', '**TOTAL**'],
            'CAPEX (€)': [
                f"{pv_capex_calculated:,.0f}",
                f"{battery_capex:,.0f}",
                f"**{total_capex_calculated:,.0f}**"
            ],
            'OPEX (€/year)': [
                f"{pv_opex:,.0f}",
                f"{battery_opex:,.0f}",
                f"**{total_opex:,.0f}**"
            ]
        }
    else:
        # Without battery - show only PV
        economics_data = {
            'Component': ['PV'],
            'CAPEX (€)': [f"{pv_capex_calculated:,.0f}"],
            'OPEX (€/year)': [f"{pv_opex:,.0f}"]
        }
    
    df_economics = pd.DataFrame(economics_data)
    
    # Display table
    st.markdown("**Financial Summary:**")
    st.table(df_economics)
    
    if pv_lcoe_eur_per_mwh is not None:
        st.write(f"**PV LCOE**: {pv_lcoe_eur_per_mwh:.2f} €/MWh")


def display_lcoh_results(lcoh_results, avg_service_ratio=None, go_enabled=False, go_cost_per_mwh=0.0):
    """Display LCOH calculation results"""
    st.markdown("---")
    st.markdown("### 💧 Electrolyser Analysis")
    
    # Main metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("**LCOH**", f"{lcoh_results['lcoh_eur_per_kg']:.2f} €/kg H₂")
    with col2:
        st.metric("**LCOH**", f"{lcoh_results['lcoh_eur_per_mwh']:.1f} €/MWh H₂")
    with col3:
        st.metric("**H₂ Production**", f"{lcoh_results['h2_production_tonnes']:.1f} T/year")
    with col4:
        st.metric("**Total Annual Cost**", f"{lcoh_results['total_annual_cost']:,.0f} €")
    
    # Detailed breakdown
    with st.expander("📊 LCOH Cost Breakdown (€/kg H₂)", expanded=True):
        breakdown = lcoh_results['breakdown']
        
        # Get project lifetime for lifetime cost calculation
        project_lifetime = lcoh_results['annualized_costs']['lifetime']
        
        # Calculate lifetime costs
        # Note: OPEX = Electricity + Water + Others OpEx
        lifetime_capex = lcoh_results['annualized_costs']['capex_total']  # CapEx is already total
        lifetime_electricity = lcoh_results['annualized_costs']['opex_electricity'] * project_lifetime
        lifetime_water = lcoh_results['annualized_costs']['opex_water'] * project_lifetime
        lifetime_others_opex = lcoh_results['annualized_costs']['opex_others'] * project_lifetime
        lifetime_opex = lifetime_electricity + lifetime_water + lifetime_others_opex  # OPEX = Electricity + Water + Others
        lifetime_maintenance = lcoh_results['annualized_costs']['maintenance_annual'] * project_lifetime
        lifetime_stack = lcoh_results['annualized_costs']['stack_annual'] * project_lifetime
        lifetime_other = lcoh_results['annualized_costs']['other_annual'] * project_lifetime
        lifetime_total = lifetime_capex + lifetime_opex + lifetime_maintenance + lifetime_stack + lifetime_other
        
        # Calculate combined maintenance (includes stack replacement and others)
        total_maintenance_annual = (
            lcoh_results['annualized_costs']['maintenance_annual'] +
            lcoh_results['annualized_costs']['stack_annual'] +
            lcoh_results['annualized_costs']['other_annual']
        )
        lifetime_total_maintenance = (
            lifetime_maintenance + 
            lifetime_stack + 
            lifetime_other
        )
        maintenance_per_kg = (
            breakdown['maintenance'] + 
            breakdown['stack'] + 
            breakdown['other']
        )
        
        # Create breakdown dataframe - simplified to 3 main categories
        breakdown_data = {
            'Component': [
                'CapEx',
                'OpEx',
                'Maintenance',
                '**TOTAL LCOH**'
            ],
            'Cost (€/kg H₂)': [
                f"{breakdown['capex']:.3f}",
                f"{breakdown['opex']:.3f}",
                f"{maintenance_per_kg:.3f}",
                f"**{lcoh_results['lcoh_eur_per_kg']:.3f}**"
            ],
            'Annual Cost (€)': [
                f"{lcoh_results['annualized_costs']['capex_annualized']:,.0f}",
                f"{lcoh_results['annualized_costs']['opex_annual']:,.0f}",
                f"{total_maintenance_annual:,.0f}",
                f"**{lcoh_results['total_annual_cost']:,.0f}**"
            ],
            f'Lifetime Cost ({project_lifetime} years) (€)': [
                f"{lifetime_capex:,.0f}",
                f"{lifetime_opex:,.0f}",
                f"{lifetime_total_maintenance:,.0f}",
                f"**{lifetime_total:,.0f}**"
            ],
            'Percentage': [
                f"{(breakdown['capex']/lcoh_results['lcoh_eur_per_kg']*100):.1f}%",
                f"{(breakdown['opex']/lcoh_results['lcoh_eur_per_kg']*100):.1f}%",
                f"{(maintenance_per_kg/lcoh_results['lcoh_eur_per_kg']*100):.1f}%",
                "**100.0%**"
            ]
        }
        
        df_breakdown = pd.DataFrame(breakdown_data)
        
        # Create two columns: table on left, pie chart on right
        col_table, col_pie = st.columns([2, 1])
        
        with col_table:
            st.table(df_breakdown)
        
        with col_pie:
            # Create pie chart for LCOH breakdown
            # Prepare data for pie chart - 3 main categories
            pie_labels = [
                'CapEx',
                'OpEx',
                'Maintenance'
            ]
            pie_values = [
                breakdown['capex'],
                breakdown['opex'],
                maintenance_per_kg
            ]
            
            # Create pie chart
            fig_pie, ax_pie = plt.subplots(figsize=(7, 7))
            colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
            
            wedges, texts, autotexts = ax_pie.pie(
                pie_values,
                labels=pie_labels,
                autopct='%1.1f%%',
                startangle=90,
                colors=colors,
                pctdistance=0.85,
                explode=[0.05, 0.05, 0.05]  # Slight explode for all
            )
            
            # Enhance text
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
                autotext.set_fontsize(9)
            
            for text in texts:
                text.set_fontsize(10)
                text.set_fontweight('bold')
            
            # Create title with average service ratio if available
            title = 'LCOH Cost Breakdown'
            if avg_service_ratio is not None:
                title += f'\nService Ratio: {avg_service_ratio:.1%}'
            ax_pie.set_title(title, fontsize=12, fontweight='bold', pad=20)
            
            # Equal aspect ratio ensures that pie is drawn as a circle
            ax_pie.axis('equal')
            
            plt.tight_layout()
            st.pyplot(fig_pie)
        
        # Detailed Cost Breakdown Bar Charts
        st.markdown("#### 📊 Detailed Cost Breakdown")
        
        # Get CapEx and Maintenance components if available
        capex_components = lcoh_results['annualized_costs'].get('capex_components', {})
        maintenance_breakdown = lcoh_results['annualized_costs'].get('maintenance_breakdown', {})
        
        # Create 3 columns for 3 charts
        col1, col2, col3 = st.columns(3)
        
        # --- 1. CapEx Breakdown Chart ---
        with col1:
            st.markdown("##### CapEx Components")
            if capex_components:
                # Get components
                capex_data = {
                    'Transformer': capex_components.get('transformer', 0),
                    'Electrolyzer': capex_components.get('electrolyzer', 0),
                    'Compressor': capex_components.get('compressor', 0),
                    'H₂ Storage': capex_components.get('h2_storage', 0),
                    'Piping': capex_components.get('piping', 0),
                    'Stack Repl.': lcoh_results['annualized_costs'].get('stack_replacement_cost_total', 0),
                    'Others': capex_components.get('others', 0)
                }
                
                # Filter out zero values
                capex_data = {k: v for k, v in capex_data.items() if v > 0}
                
                if capex_data:
                    # Create figure
                    fig1, ax1 = plt.subplots(figsize=(6, 5))
                    
                    components = list(capex_data.keys())
                    values = list(capex_data.values())
                    colors = plt.cm.Blues(np.linspace(0.4, 0.9, len(components)))
                    
                    bars = ax1.barh(components, values, color=colors, edgecolor='black', linewidth=1.2)
                    
                    # Add value labels
                    for i, (bar, val) in enumerate(zip(bars, values)):
                        width = bar.get_width()
                        ax1.text(width, bar.get_y() + bar.get_height()/2,
                               f' €{val:,.0f}',
                               ha='left', va='center', fontsize=8, fontweight='bold')
                    
                    ax1.set_xlabel('Cost (€)', fontsize=10, fontweight='bold')
                    title1 = f'Total: €{sum(values):,.0f}'
                    if avg_service_ratio is not None:
                        title1 += f'\nService Ratio: {avg_service_ratio:.1%}'
                    ax1.set_title(title1, fontsize=11, fontweight='bold', pad=10)
                    ax1.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1e6:.1f}M' if x >= 1e6 else f'{x/1e3:.0f}K'))
                    ax1.grid(axis='x', alpha=0.3, linestyle='--')
                    ax1.set_axisbelow(True)
                    
                    plt.tight_layout()
                    st.pyplot(fig1)
                    plt.close()
            else:
                st.info("No CapEx breakdown available")
        
        # --- 2. OpEx Breakdown Chart ---
        with col2:
            st.markdown("##### OpEx Components")
            opex_data = {
                'Electricity': lifetime_electricity,
                'Water': lifetime_water,
                'Others': lifetime_others_opex
            }
            
            # Filter out zero values
            opex_data = {k: v for k, v in opex_data.items() if v > 0}
            
            if opex_data:
                # Create figure
                fig2, ax2 = plt.subplots(figsize=(6, 5))
                
                components = list(opex_data.keys())
                values = list(opex_data.values())
                colors = plt.cm.Oranges(np.linspace(0.4, 0.9, len(components)))
                
                bars = ax2.barh(components, values, color=colors, edgecolor='black', linewidth=1.2)
                
                # Add value labels
                for i, (bar, val) in enumerate(zip(bars, values)):
                    width = bar.get_width()
                    ax2.text(width, bar.get_y() + bar.get_height()/2,
                           f' €{val:,.0f}',
                           ha='left', va='center', fontsize=8, fontweight='bold')
                
                ax2.set_xlabel('Cost (€)', fontsize=10, fontweight='bold')
                title2 = f'Total: €{sum(values):,.0f}'
                if avg_service_ratio is not None:
                    title2 += f'\nService Ratio: {avg_service_ratio:.1%}'
                if go_enabled:
                    title2 += f'\n(Spot with GO: +{go_cost_per_mwh:.1f}€/MWh)'
                ax2.set_title(title2, fontsize=11, fontweight='bold', pad=10)
                ax2.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1e6:.1f}M' if x >= 1e6 else f'{x/1e3:.0f}K'))
                ax2.grid(axis='x', alpha=0.3, linestyle='--')
                ax2.set_axisbelow(True)
                
                plt.tight_layout()
                st.pyplot(fig2)
                plt.close()
            else:
                st.info("No OpEx breakdown available")
        
        # --- 3. Maintenance Breakdown Chart ---
        with col3:
            st.markdown("##### Maintenance Components")
            if maintenance_breakdown:
                maintenance_data = {
                    'Transformer': maintenance_breakdown.get('transformer', 0) * project_lifetime,
                    'Electrolyzer': maintenance_breakdown.get('electrolyzer', 0) * project_lifetime,
                    'Compressor': maintenance_breakdown.get('compressor', 0) * project_lifetime,
                    'H₂ Storage': maintenance_breakdown.get('h2_storage', 0) * project_lifetime,
                    'Piping': maintenance_breakdown.get('piping', 0) * project_lifetime,
                    'Others': maintenance_breakdown.get('others', 0) * project_lifetime
                }
                
                # Filter out zero values
                maintenance_data = {k: v for k, v in maintenance_data.items() if v > 0}
                
                if maintenance_data:
                    # Create figure
                    fig3, ax3 = plt.subplots(figsize=(6, 5))
                    
                    components = list(maintenance_data.keys())
                    values = list(maintenance_data.values())
                    colors = plt.cm.Greens(np.linspace(0.4, 0.9, len(components)))
                    
                    bars = ax3.barh(components, values, color=colors, edgecolor='black', linewidth=1.2)
                    
                    # Add value labels
                    for i, (bar, val) in enumerate(zip(bars, values)):
                        width = bar.get_width()
                        ax3.text(width, bar.get_y() + bar.get_height()/2,
                               f' €{val:,.0f}',
                               ha='left', va='center', fontsize=8, fontweight='bold')
                    
                    ax3.set_xlabel('Cost (€)', fontsize=10, fontweight='bold')
                    title3 = f'Total: €{sum(values):,.0f}'
                    if avg_service_ratio is not None:
                        title3 += f'\nService Ratio: {avg_service_ratio:.1%}'
                    ax3.set_title(title3, fontsize=11, fontweight='bold', pad=10)
                    ax3.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1e6:.1f}M' if x >= 1e6 else f'{x/1e3:.0f}K'))
                    ax3.grid(axis='x', alpha=0.3, linestyle='--')
                    ax3.set_axisbelow(True)
                    
                    plt.tight_layout()
                    st.pyplot(fig3)
                    plt.close()
            else:
                st.info("No Maintenance breakdown available")
        
        # Electricity breakdown by source
        st.markdown("#### ⚡ Electricity Cost Breakdown by Source")
        elec = lcoh_results['electricity_costs']
        
        elec_breakdown_data = {
            'Source': ['PV', 'Spot Market', 'PPA', '**TOTAL**'],
            'Energy (MWh)': [
                f"{elec['pv_energy']:.1f}",
                f"{elec['spot_energy']:.1f}",
                f"{elec['ppa_energy']:.1f}",
                f"**{elec['total_energy']:.1f}**"
            ],
            'Cost (€)': [
                f"{elec['pv_cost']:,.0f}",
                f"{elec['spot_cost']:,.0f}",
                f"{elec['ppa_cost']:,.0f}",
                f"**{elec['total_cost']:,.0f}**"
            ],
            'Share (%)': [
                f"{(elec['pv_energy']/elec['total_energy']*100):.1f}%" if elec['total_energy'] > 0 else "0%",
                f"{(elec['spot_energy']/elec['total_energy']*100):.1f}%" if elec['total_energy'] > 0 else "0%",
                f"{(elec['ppa_energy']/elec['total_energy']*100):.1f}%" if elec['total_energy'] > 0 else "0%",
                "**100.0%**"
            ],
            'Cost Share (%)': [
                f"{(elec['pv_cost']/elec['total_cost']*100):.1f}%" if elec['total_cost'] > 0 else "0%",
                f"{(elec['spot_cost']/elec['total_cost']*100):.1f}%" if elec['total_cost'] > 0 else "0%",
                f"{(elec['ppa_cost']/elec['total_cost']*100):.1f}%" if elec['total_cost'] > 0 else "0%",
                "**100.0%**"
            ]
        }
        
        df_elec_breakdown = pd.DataFrame(elec_breakdown_data)
        st.table(df_elec_breakdown)


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


def display_methanation_analysis(methanation_econ, ch4_flowrate, puissance_instantanee_kw, annual_consumption_mwh, avg_electricity_cost, avg_service_ratio=None):
    """Display Methanation Unit Analysis (separate from full LCOC)"""
    st.markdown("---")
    st.markdown("### 🔥 Methanation Unit Analysis")
    
    # Calculate CH4 yearly production
    ch4_density = 0.7168  # kg/Nm³ CH₄
    ch4_production_kg_year = ch4_flowrate * avg_service_ratio * 8760 * ch4_density
    ch4_production_tonnes_year = ch4_production_kg_year / 1000
    
    # Main metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("**CH₄ Flow Rate**", f"{ch4_flowrate:.0f} Nm³/h")
    with col2:
        st.metric("**Puissance Instantanée**", f"{puissance_instantanee_kw:.1f} kW",
                 help=f"Calculated: {ch4_flowrate:.0f} Nm³/h × {methanation_econ.get('cons_spec_ch4', 0.7)} kWh/Nm³")
    with col3:
        st.metric("**Annual Electricity**", f"{annual_consumption_mwh:.1f} MWhe",
                 help=f"Calculated: {puissance_instantanee_kw:.1f} kW × {avg_service_ratio:.1%} × 8760 h / 1000")
    with col4:
        st.metric("**Annual CH₄ Production**", f"{ch4_production_tonnes_year:.1f} T",
                 help=f"Calculated: {ch4_flowrate:.0f} Nm³/h × {avg_service_ratio:.1%} × 8760 h × {ch4_density} kg/Nm³ = {ch4_production_kg_year:,.0f} kg/year ({ch4_production_tonnes_year:.1f} T/year)")
    
    # Detailed breakdown
    with st.expander("📊 Methanation Cost Breakdown", expanded=True):
        # Get project lifetime
        project_lifetime = methanation_econ.get('methanation_lifetime', 20)
        
        # Get costs
        capex_annual = methanation_econ.get('methanation_capex_annual', 0)
        capex_total = methanation_econ.get('methanation_capex_total', 0)
        maintenance_annual = methanation_econ.get('methanation_maintenance_annual', 0)
        electricity_cost_annual = annual_consumption_mwh * avg_electricity_cost
        others_opex_annual = methanation_econ.get('others_opex_annual', 0)
        
        opex_annual = electricity_cost_annual + others_opex_annual
        total_annual = capex_annual + opex_annual + maintenance_annual
        
        # Lifetime costs
        lifetime_capex = capex_total
        lifetime_electricity = electricity_cost_annual * project_lifetime
        lifetime_others_opex = others_opex_annual * project_lifetime
        lifetime_opex = opex_annual * project_lifetime
        lifetime_maintenance = maintenance_annual * project_lifetime
        lifetime_total = lifetime_capex + lifetime_opex + lifetime_maintenance
        
        # Calculate cost per kg CH4
        capex_per_kg = capex_annual / ch4_production_kg_year if ch4_production_kg_year > 0 else 0
        opex_per_kg = opex_annual / ch4_production_kg_year if ch4_production_kg_year > 0 else 0
        maintenance_per_kg = maintenance_annual / ch4_production_kg_year if ch4_production_kg_year > 0 else 0
        total_per_kg = total_annual / ch4_production_kg_year if ch4_production_kg_year > 0 else 0
        
        # Create breakdown dataframe
        breakdown_data = {
            'Component': [
                'CapEx',
                'OpEx',
                'Maintenance',
                '**TOTAL**'
            ],
            'Cost (€/kg CH₄)': [
                f"{capex_per_kg:.3f}",
                f"{opex_per_kg:.3f}",
                f"{maintenance_per_kg:.3f}",
                f"**{total_per_kg:.3f}**"
            ],
            'Annual Cost (€)': [
                f"{capex_annual:,.0f}",
                f"{opex_annual:,.0f}",
                f"{maintenance_annual:,.0f}",
                f"**{total_annual:,.0f}**"
            ],
            f'Lifetime Cost ({project_lifetime} years) (€)': [
                f"{lifetime_capex:,.0f}",
                f"{lifetime_opex:,.0f}",
                f"{lifetime_maintenance:,.0f}",
                f"**{lifetime_total:,.0f}**"
            ],
            'Percentage': [
                f"{(capex_annual/total_annual*100):.1f}%" if total_annual > 0 else "0%",
                f"{(opex_annual/total_annual*100):.1f}%" if total_annual > 0 else "0%",
                f"{(maintenance_annual/total_annual*100):.1f}%" if total_annual > 0 else "0%",
                "**100.0%**"
            ]
        }
        
        df_breakdown = pd.DataFrame(breakdown_data)
        
        # Create two columns: table on left, pie chart on right
        col_table, col_pie = st.columns([2, 1])
        
        with col_table:
            st.table(df_breakdown)
        
        with col_pie:
            # Create pie chart
            pie_labels = ['CapEx', 'OpEx', 'Maintenance']
            pie_values = [capex_annual, opex_annual, maintenance_annual]
            
            fig_pie, ax_pie = plt.subplots(figsize=(7, 7))
            colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
            
            wedges, texts, autotexts = ax_pie.pie(
                pie_values,
                labels=pie_labels,
                autopct='%1.1f%%',
                startangle=90,
                colors=colors,
                pctdistance=0.85,
                explode=[0.05, 0.05, 0.05]
            )
            
            # Enhance text
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
                autotext.set_fontsize(9)
            
            for text in texts:
                text.set_fontsize(10)
                text.set_fontweight('bold')
            
            # Create title with average service ratio if available
            title = 'Methanation Cost Breakdown'
            if avg_service_ratio is not None:
                title += f'\nService Ratio: {avg_service_ratio:.1%}'
            ax_pie.set_title(title, fontsize=12, fontweight='bold', pad=20)
            
            ax_pie.axis('equal')
            
            plt.tight_layout()
            st.pyplot(fig_pie)
            plt.close()
        
        # Detailed Cost Breakdown Bar Charts
        st.markdown("#### 📊 Detailed Cost Breakdown")
        
        # Get CapEx and Maintenance components
        capex_components = methanation_econ.get('capex_components', {})
        maintenance_breakdown = methanation_econ.get('maintenance_breakdown', {})
        
        # Create 3 columns for 3 charts
        col1, col2, col3 = st.columns(3)
        
        # --- 1. CapEx Breakdown Chart ---
        with col1:
            st.markdown("##### CapEx Components")
            if capex_components:
                # Get components
                capex_data = {
                    'Methanation Unit': capex_components.get('methanation_unit', 0),
                    'Purification': capex_components.get('purification_unit', 0),
                    'Compressor': capex_components.get('compressor', 0),
                    'CH₄ Storage': capex_components.get('ch4_storage', 0),
                    'Grid Injection': capex_components.get('grid_injection', 0),
                    'Others': capex_components.get('others', 0)
                }
                
                # Filter out zero values
                capex_data = {k: v for k, v in capex_data.items() if v > 0}
                
                if capex_data:
                    # Create figure
                    fig1, ax1 = plt.subplots(figsize=(6, 5))
                    
                    components = list(capex_data.keys())
                    values = list(capex_data.values())
                    colors = plt.cm.Blues(np.linspace(0.4, 0.9, len(components)))
                    
                    bars = ax1.barh(components, values, color=colors, edgecolor='black', linewidth=1.2)
                    
                    # Add value labels
                    for i, (bar, val) in enumerate(zip(bars, values)):
                        width = bar.get_width()
                        ax1.text(width, bar.get_y() + bar.get_height()/2,
                               f' €{val:,.0f}',
                               ha='left', va='center', fontsize=8, fontweight='bold')
                    
                    ax1.set_xlabel('Cost (€)', fontsize=10, fontweight='bold')
                    title1 = f'Total: €{sum(values):,.0f}'
                    if avg_service_ratio is not None:
                        title1 += f'\nService Ratio: {avg_service_ratio:.1%}'
                    ax1.set_title(title1, fontsize=11, fontweight='bold', pad=10)
                    ax1.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1e6:.1f}M' if x >= 1e6 else f'{x/1e3:.0f}K'))
                    ax1.grid(axis='x', alpha=0.3, linestyle='--')
                    ax1.set_axisbelow(True)
                    
                    plt.tight_layout()
                    st.pyplot(fig1)
                    plt.close()
            else:
                st.info("No CapEx breakdown available")
        
        # --- 2. OpEx Breakdown Chart ---
        with col2:
            st.markdown("##### OpEx Components")
            opex_data = {
                'Electricity': lifetime_electricity,
                'Others': lifetime_others_opex
            }
            
            # Filter out zero values
            opex_data = {k: v for k, v in opex_data.items() if v > 0}
            
            if opex_data:
                # Create figure
                fig2, ax2 = plt.subplots(figsize=(6, 5))
                
                components = list(opex_data.keys())
                values = list(opex_data.values())
                colors = plt.cm.Oranges(np.linspace(0.4, 0.9, len(components)))
                
                bars = ax2.barh(components, values, color=colors, edgecolor='black', linewidth=1.2)
                
                # Add value labels
                for i, (bar, val) in enumerate(zip(bars, values)):
                    width = bar.get_width()
                    ax2.text(width, bar.get_y() + bar.get_height()/2,
                           f' €{val:,.0f}',
                           ha='left', va='center', fontsize=8, fontweight='bold')
                
                ax2.set_xlabel('Cost (€)', fontsize=10, fontweight='bold')
                title2 = f'Total: €{sum(values):,.0f}'
                if avg_service_ratio is not None:
                    title2 += f'\nService Ratio: {avg_service_ratio:.1%}'
                ax2.set_title(title2, fontsize=11, fontweight='bold', pad=10)
                ax2.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1e6:.1f}M' if x >= 1e6 else f'{x/1e3:.0f}K'))
                ax2.grid(axis='x', alpha=0.3, linestyle='--')
                ax2.set_axisbelow(True)
                
                plt.tight_layout()
                st.pyplot(fig2)
                plt.close()
            else:
                st.info("No OpEx breakdown available")
        
        # --- 3. Maintenance Breakdown Chart ---
        with col3:
            st.markdown("##### Maintenance Components")
            if maintenance_breakdown:
                maintenance_data = {
                    'Methanation Unit': maintenance_breakdown.get('methanation_unit', 0) * project_lifetime,
                    'Purification': maintenance_breakdown.get('purification_unit', 0) * project_lifetime,
                    'Compressor': maintenance_breakdown.get('compressor', 0) * project_lifetime,
                    'CH₄ Storage': maintenance_breakdown.get('ch4_storage', 0) * project_lifetime,
                    'Grid Injection': maintenance_breakdown.get('grid_injection', 0) * project_lifetime,
                    'Others': maintenance_breakdown.get('others', 0) * project_lifetime
                }
                
                # Filter out zero values
                maintenance_data = {k: v for k, v in maintenance_data.items() if v > 0}
                
                if maintenance_data:
                    # Create figure
                    fig3, ax3 = plt.subplots(figsize=(6, 5))
                    
                    components = list(maintenance_data.keys())
                    values = list(maintenance_data.values())
                    colors = plt.cm.Greens(np.linspace(0.4, 0.9, len(components)))
                    
                    bars = ax3.barh(components, values, color=colors, edgecolor='black', linewidth=1.2)
                    
                    # Add value labels
                    for i, (bar, val) in enumerate(zip(bars, values)):
                        width = bar.get_width()
                        ax3.text(width, bar.get_y() + bar.get_height()/2,
                               f' €{val:,.0f}',
                               ha='left', va='center', fontsize=8, fontweight='bold')
                    
                    ax3.set_xlabel('Cost (€)', fontsize=10, fontweight='bold')
                    title3 = f'Total: €{sum(values):,.0f}'
                    if avg_service_ratio is not None:
                        title3 += f'\nService Ratio: {avg_service_ratio:.1%}'
                    ax3.set_title(title3, fontsize=11, fontweight='bold', pad=10)
                    ax3.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1e6:.1f}M' if x >= 1e6 else f'{x/1e3:.0f}K'))
                    ax3.grid(axis='x', alpha=0.3, linestyle='--')
                    ax3.set_axisbelow(True)
                    
                    plt.tight_layout()
                    st.pyplot(fig3)
                    plt.close()
            else:
                st.info("No Maintenance breakdown available")
        
        # Electricity breakdown for methanation
        st.markdown("#### ⚡ Methanation Electricity Cost")
        st.info(f"**Formula:** Puissance instantanée = Débit CH₄ × Cons Spec CH₄\n\n"
                f"**Calculation:** {ch4_flowrate:.0f} Nm³/h × {methanation_econ.get('cons_spec_ch4', 0.7)} kWh/Nm³ = {puissance_instantanee_kw:.1f} kW\n\n"
                f"**Annual Consumption:** {puissance_instantanee_kw:.1f} kW × {avg_service_ratio:.1%} × 8760 h / 1000 = {annual_consumption_mwh:.1f} MWhe/year\n\n"
                f"**Total Electricity Cost:** {annual_consumption_mwh:.1f} MWh × {avg_electricity_cost:.2f} €/MWh = **{electricity_cost_annual:,.0f} €/year**")
    


def display_lcoc_results(lcoc_results, avg_service_ratio=None):
    """Display LCOC (Levelized Cost of CH4) calculation results"""
    st.markdown("---")
    st.markdown("### 🔥 LCOC (Levelized Cost of CH₄/Methane) Analysis")
    
    # Main metrics
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        st.metric("**LCOC**", f"{lcoc_results['lcoc_eur_per_kg']:.2f} €/kg CH₄")
    with col2:
        st.metric("**LCOC**", f"{lcoc_results['lcoc_eur_per_mwh']:.1f} €/MWh CH₄ PCI")
    with col3:
        st.metric("**CH₄ Production**", f"{lcoc_results['ch4_production_tonnes']:.1f} T/year")
    with col4:
        st.metric("**Total Annual Cost**", f"{lcoc_results['total_annual_cost']:,.0f} €")
    with col5:
        # Add tooltip with calculation details if available
        elec_help = None
        if 'puissance_instantanee_kw' in lcoc_results:
            ch4_flow = lcoc_results.get('ch4_flowrate_nm3h', 0)
            cons_spec = lcoc_results.get('cons_spec_ch4', 0.7)
            p_inst = lcoc_results['puissance_instantanee_kw']
            service = avg_service_ratio if avg_service_ratio else 0
            elec_help = (f"**Calculation:**\n\n"
                        f"1. Puissance instantanée = {ch4_flow:.0f} Nm³/h × {cons_spec} kWh/Nm³ = {p_inst:.1f} kW\n\n"
                        f"2. Annual consumption = {p_inst:.1f} kW × {service:.1%} (service ratio) × 8760 h / 1000 = {lcoc_results['methanation_electricity_mwh']:.1f} MWhe/year")
        st.metric("**Methanation Elec.**", f"{lcoc_results['methanation_electricity_mwh']:.1f} MWhe/year", help=elec_help)
    with col6:
        st.metric("**Avg. Elec. Cost**", f"{lcoc_results['avg_electricity_cost_per_mwh']:.2f} €/MWh")
    
    # Detailed breakdown
    with st.expander("📊 LCOC Cost Breakdown (€/kg CH₄)", expanded=True):
        breakdown = lcoc_results['breakdown']
        
        # Get project lifetime for lifetime cost calculation
        project_lifetime = lcoc_results['annualized_costs']['lifetime']
        
        # Calculate lifetime costs
        lifetime_capex = lcoc_results['annualized_costs']['capex_total']
        lifetime_electricity = lcoc_results['annualized_costs']['opex_electricity'] * project_lifetime
        lifetime_others_opex = lcoc_results['annualized_costs']['opex_others'] * project_lifetime
        lifetime_opex = lifetime_electricity + lifetime_others_opex
        lifetime_maintenance = lcoc_results['annualized_costs']['maintenance_annual'] * project_lifetime
        lifetime_other = lcoc_results['annualized_costs']['other_annual'] * project_lifetime
        
        # Get all component costs
        electrolyzer_costs = lcoc_results.get('electrolyzer_costs', {})
        methanation_costs = lcoc_results.get('methanation_costs', {})
        site_co2_costs = lcoc_results.get('site_co2_costs', {})
        
        electrolyzer_annual = electrolyzer_costs.get('total_annual', 0)
        methanation_annual = methanation_costs.get('total_annual', 0)
        site_co2_annual = site_co2_costs.get('total_annual', 0)
        
        electrolyzer_per_kg = electrolyzer_costs.get('total_component', 0)
        methanation_per_kg = methanation_costs.get('total_component', 0)
        site_co2_per_kg = site_co2_costs.get('total_component', 0)
        
        lifetime_electrolyzer = electrolyzer_annual * project_lifetime
        lifetime_methanation = methanation_annual * project_lifetime
        lifetime_site_co2 = site_co2_annual * project_lifetime
        
        lifetime_total = lifetime_electrolyzer + lifetime_methanation + lifetime_site_co2
        
        # Create breakdown dataframe - by financial component
        breakdown_data = {
            'Component': [
                'Electrolyser',
                'Methanation',
                'Site & CO₂',
                '**TOTAL LCOC**'
            ],
            'Cost (€/kg CH₄)': [
                f"{electrolyzer_per_kg:.3f}",
                f"{methanation_per_kg:.3f}",
                f"{site_co2_per_kg:.3f}",
                f"**{lcoc_results['lcoc_eur_per_kg']:.3f}**"
            ],
            'Annual Cost (€)': [
                f"{electrolyzer_annual:,.0f}",
                f"{methanation_annual:,.0f}",
                f"{site_co2_annual:,.0f}",
                f"**{lcoc_results['total_annual_cost']:,.0f}**"
            ],
            f'Lifetime Cost ({project_lifetime} years) (€)': [
                f"{lifetime_electrolyzer:,.0f}",
                f"{lifetime_methanation:,.0f}",
                f"{lifetime_site_co2:,.0f}",
                f"**{lifetime_total:,.0f}**"
            ],
            'Percentage': [
                f"{(electrolyzer_per_kg/lcoc_results['lcoc_eur_per_kg']*100):.1f}%" if lcoc_results['lcoc_eur_per_kg'] > 0 else "0%",
                f"{(methanation_per_kg/lcoc_results['lcoc_eur_per_kg']*100):.1f}%" if lcoc_results['lcoc_eur_per_kg'] > 0 else "0%",
                f"{(site_co2_per_kg/lcoc_results['lcoc_eur_per_kg']*100):.1f}%" if lcoc_results['lcoc_eur_per_kg'] > 0 else "0%",
                "**100.0%**"
            ]
        }
        
        df_breakdown = pd.DataFrame(breakdown_data)
        
        # Extract annual costs for each component (needed for pie charts and detailed breakdown)
        electrolyzer_capex_annual_cat = electrolyzer_costs.get('capex_annual', 0)
        electrolyzer_opex_annual_cat = electrolyzer_costs.get('opex_annual', 0)
        electrolyzer_maintenance_annual_cat = electrolyzer_costs.get('maintenance_annual', 0)
        
        methanation_capex_annual_cat = methanation_costs.get('capex_annual', 0)
        methanation_opex_annual_cat = methanation_costs.get('opex_annual', 0)
        methanation_maintenance_annual_cat = methanation_costs.get('maintenance_annual', 0)
        
        site_co2_capex_annual_cat = site_co2_costs.get('capex_annual', 0)
        site_co2_opex_annual_cat = site_co2_costs.get('opex_annual', 0)
        site_co2_maintenance_annual_cat = site_co2_costs.get('maintenance_annual', 0)
        
        # Get separate Site and CO2 costs
        site_capex_annual = site_co2_costs.get('site_capex_annual', 0)
        appro_co2_capex_annual = site_co2_costs.get('appro_co2_capex_annual', 0)
        
        site_opex_annual = site_co2_costs.get('site_opex_annual', 0)
        appro_co2_opex_annual = site_co2_costs.get('appro_co2_opex_annual', 0)
        
        site_maintenance_annual = site_co2_costs.get('site_maintenance_annual', 0)
        appro_co2_maintenance_annual = site_co2_costs.get('appro_co2_maintenance_annual', 0)
        
        # Create two columns: table on left, pie chart on right
        col_table, col_pie = st.columns([2, 1])
        
        with col_table:
            st.table(df_breakdown)
        
        with col_pie:
            # Create two pie charts side by side: Domain breakdown and Cost Type breakdown
            fig_pies, (ax_domain, ax_costtype) = plt.subplots(1, 2, figsize=(14, 6))
            
            # --- Pie Chart 1: Domain Breakdown ---
            pie_labels_domain = ['Electrolyser', 'Methanation', 'Site & CO₂']
            pie_values_domain = [electrolyzer_per_kg, methanation_per_kg, site_co2_per_kg]
            colors_domain = ['#1f77b4', '#ff7f0e', '#2ca02c']
            
            wedges1, texts1, autotexts1 = ax_domain.pie(
                pie_values_domain,
                labels=pie_labels_domain,
                autopct='%1.1f%%',
                startangle=90,
                colors=colors_domain,
                pctdistance=0.85,
                explode=[0.05, 0.05, 0.05]
            )
            
            # Enhance text for domain pie chart
            for autotext in autotexts1:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
                autotext.set_fontsize(9)
            
            for text in texts1:
                text.set_fontsize(9)
                text.set_fontweight('bold')
            
            ax_domain.set_title('LCOC by Domain', fontsize=11, fontweight='bold', pad=10)
            ax_domain.axis('equal')
            
            # --- Pie Chart 2: Cost Type Breakdown ---
            # Calculate total costs by type across all domains
            total_capex_annual = electrolyzer_capex_annual_cat + methanation_capex_annual_cat + site_co2_capex_annual_cat
            total_opex_annual = electrolyzer_opex_annual_cat + methanation_opex_annual_cat + site_co2_opex_annual_cat
            total_maintenance_annual = electrolyzer_maintenance_annual_cat + methanation_maintenance_annual_cat + site_co2_maintenance_annual_cat
            
            pie_labels_costtype = ['CapEx', 'OpEx', 'Maintenance']
            pie_values_costtype = [total_capex_annual, total_opex_annual, total_maintenance_annual]
            colors_costtype = ['#3498db', '#e74c3c', '#2ecc71']
            
            wedges2, texts2, autotexts2 = ax_costtype.pie(
                pie_values_costtype,
                labels=pie_labels_costtype,
                autopct='%1.1f%%',
                startangle=90,
                colors=colors_costtype,
                pctdistance=0.85,
                explode=[0.05, 0.05, 0.05]
            )
            
            # Enhance text for cost type pie chart
            for autotext in autotexts2:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
                autotext.set_fontsize(9)
            
            for text in texts2:
                text.set_fontsize(9)
                text.set_fontweight('bold')
            
            # Add service ratio to title if available
            title_costtype = 'LCOC by Cost Type'
            if avg_service_ratio is not None:
                title_costtype += f'\nService Ratio: {avg_service_ratio:.1%}'
            ax_costtype.set_title(title_costtype, fontsize=11, fontweight='bold', pad=10)
            ax_costtype.axis('equal')
            
            plt.tight_layout()
            st.pyplot(fig_pies)
            plt.close()
        
        
        # Detailed Cost Breakdown Structure
        st.markdown("#### 📋 Detailed Cost Breakdown")
        
        # Total by category (already calculated above)
        total_capex_annual_cat = electrolyzer_capex_annual_cat + methanation_capex_annual_cat + site_co2_capex_annual_cat
        total_opex_annual_cat = electrolyzer_opex_annual_cat + methanation_opex_annual_cat + site_co2_opex_annual_cat
        total_maintenance_annual_cat = electrolyzer_maintenance_annual_cat + methanation_maintenance_annual_cat + site_co2_maintenance_annual_cat
        
        # Create hierarchical breakdown
        detailed_breakdown_data = {
            'Cost Category': [
                '**INVESTISSEMENT (CapEx annualized)**',
                '  Site',
                '  Prod H₂',
                '  Methanation',
                '  Appro CO₂',
                '',
                '**OPEX ANNUEL**',
                '  Site',
                '  Prod H₂',
                '  Methanation',
                '  Appro CO₂',
                '',
                '**MAINTENANCE ANNUELLE**',
                '  Site',
                '  Prod H₂',
                '  Methanation',
                '  Appro CO₂',
                '',
                '**TOTAL ANNUEL**'
            ],
            'Annual Cost (€)': [
                f"**{total_capex_annual_cat:,.0f}**",
                f"{site_capex_annual:,.0f}",
                f"{electrolyzer_capex_annual_cat:,.0f}",
                f"{methanation_capex_annual_cat:,.0f}",
                f"{appro_co2_capex_annual:,.0f}",
                '',
                f"**{total_opex_annual_cat:,.0f}**",
                f"{site_opex_annual:,.0f}",
                f"{electrolyzer_opex_annual_cat:,.0f}",
                f"{methanation_opex_annual_cat:,.0f}",
                f"{appro_co2_opex_annual:,.0f}",
                '',
                f"**{total_maintenance_annual_cat:,.0f}**",
                f"{site_maintenance_annual:,.0f}",
                f"{electrolyzer_maintenance_annual_cat:,.0f}",
                f"{methanation_maintenance_annual_cat:,.0f}",
                f"{appro_co2_maintenance_annual:,.0f}",
                '',
                f"**{lcoc_results['total_annual_cost']:,.0f}**"
            ]
        }
        
        df_detailed_breakdown = pd.DataFrame(detailed_breakdown_data)
        
        # Style the dataframe
        def style_breakdown_rows(row):
            if row.name in [0, 6, 12, 18]:  # Bold rows (category headers and total)
                return ['background-color: #1f77b4; color: white; font-weight: bold'] * len(row)
            elif row.name in [5, 11, 17]:  # Empty separator rows
                return ['background-color: white; height: 5px'] * len(row)
            else:
                return ['padding-left: 20px'] * len(row)
        
        styled_breakdown = df_detailed_breakdown.style.apply(style_breakdown_rows, axis=1)
        st.dataframe(styled_breakdown, hide_index=True, use_container_width=True)
        
        # Add domain-specific expandable breakdowns
        st.markdown("#### 🔍 Domain-Specific Cost Breakdowns")
        st.info("Expand each domain below to see detailed CAPEX, OPEX, and Maintenance breakdown")
        
        # --- Electrolyser Domain Breakdown ---
        with st.expander("⚡ Electrolyser Cost Breakdown", expanded=False):
            col_elec_1, col_elec_2 = st.columns(2)
            
            with col_elec_1:
                st.markdown("**Annual Costs**")
                elec_breakdown_data = {
                    'Category': ['CapEx', 'OpEx', 'Maintenance'],
                    'Annual Cost (€)': [
                        f"{electrolyzer_capex_annual_cat:,.0f}",
                        f"{electrolyzer_opex_annual_cat:,.0f}",
                        f"{electrolyzer_maintenance_annual_cat:,.0f}"
                    ],
                    'Cost per kg CH₄ (€)': [
                        f"{electrolyzer_costs.get('capex_component', 0):.4f}",
                        f"{electrolyzer_costs.get('opex_component', 0):.4f}",
                        f"{electrolyzer_costs.get('maintenance_component', 0):.4f}"
                    ],
                    'Percentage of Electrolyser': [
                        f"{(electrolyzer_capex_annual_cat/electrolyzer_annual*100):.1f}%" if electrolyzer_annual > 0 else "0%",
                        f"{(electrolyzer_opex_annual_cat/electrolyzer_annual*100):.1f}%" if electrolyzer_annual > 0 else "0%",
                        f"{(electrolyzer_maintenance_annual_cat/electrolyzer_annual*100):.1f}%" if electrolyzer_annual > 0 else "0%"
                    ]
                }
                st.table(pd.DataFrame(elec_breakdown_data))
            
            with col_elec_2:
                st.markdown("**Contribution to Total LCOC**")
                st.metric("Total Electrolyser Cost", f"{electrolyzer_annual:,.0f} €/year")
                st.metric("Cost per kg CH₄", f"{electrolyzer_per_kg:.4f} €/kg")
                st.metric("% of Total LCOC", 
                         f"{(electrolyzer_per_kg/lcoc_results['lcoc_eur_per_kg']*100):.1f}%" if lcoc_results['lcoc_eur_per_kg'] > 0 else "0%")
        
        # --- Methanation Domain Breakdown ---
        with st.expander("🔥 Methanation Cost Breakdown", expanded=False):
            col_meth_1, col_meth_2 = st.columns(2)
            
            with col_meth_1:
                st.markdown("**Annual Costs**")
                meth_breakdown_data = {
                    'Category': ['CapEx', 'OpEx', 'Maintenance'],
                    'Annual Cost (€)': [
                        f"{methanation_capex_annual_cat:,.0f}",
                        f"{methanation_opex_annual_cat:,.0f}",
                        f"{methanation_maintenance_annual_cat:,.0f}"
                    ],
                    'Cost per kg CH₄ (€)': [
                        f"{methanation_costs.get('capex_component', 0):.4f}",
                        f"{methanation_costs.get('opex_component', 0):.4f}",
                        f"{methanation_costs.get('maintenance_component', 0):.4f}"
                    ],
                    'Percentage of Methanation': [
                        f"{(methanation_capex_annual_cat/methanation_annual*100):.1f}%" if methanation_annual > 0 else "0%",
                        f"{(methanation_opex_annual_cat/methanation_annual*100):.1f}%" if methanation_annual > 0 else "0%",
                        f"{(methanation_maintenance_annual_cat/methanation_annual*100):.1f}%" if methanation_annual > 0 else "0%"
                    ]
                }
                st.table(pd.DataFrame(meth_breakdown_data))
                
                # Add OpEx sub-breakdown
                st.markdown("**OpEx Sub-components**")
                st.write(f"• Electricity: {lcoc_results['methanation_electricity_cost']:,.0f} €/year")
                st.write(f"• Others: {methanation_costs.get('opex_annual', 0) - lcoc_results['methanation_electricity_cost']:,.0f} €/year")
            
            with col_meth_2:
                st.markdown("**Contribution to Total LCOC**")
                st.metric("Total Methanation Cost", f"{methanation_annual:,.0f} €/year")
                st.metric("Cost per kg CH₄", f"{methanation_per_kg:.4f} €/kg")
                st.metric("% of Total LCOC", 
                         f"{(methanation_per_kg/lcoc_results['lcoc_eur_per_kg']*100):.1f}%" if lcoc_results['lcoc_eur_per_kg'] > 0 else "0%")
        
        # --- Site & CO2 Domain Breakdown ---
        with st.expander("🏭 Site & CO₂ Supply Cost Breakdown", expanded=False):
            col_site_1, col_site_2 = st.columns(2)
            
            with col_site_1:
                st.markdown("**Annual Costs by Category**")
                site_co2_breakdown_data = {
                    'Category': ['CapEx', 'OpEx', 'Maintenance'],
                    'Annual Cost (€)': [
                        f"{site_co2_capex_annual_cat:,.0f}",
                        f"{site_co2_opex_annual_cat:,.0f}",
                        f"{site_co2_maintenance_annual_cat:,.0f}"
                    ],
                    'Cost per kg CH₄ (€)': [
                        f"{site_co2_costs.get('capex_component', 0):.4f}",
                        f"{site_co2_costs.get('opex_component', 0):.4f}",
                        f"{site_co2_costs.get('maintenance_component', 0):.4f}"
                    ],
                    'Percentage of Site & CO₂': [
                        f"{(site_co2_capex_annual_cat/site_co2_annual*100):.1f}%" if site_co2_annual > 0 else "0%",
                        f"{(site_co2_opex_annual_cat/site_co2_annual*100):.1f}%" if site_co2_annual > 0 else "0%",
                        f"{(site_co2_maintenance_annual_cat/site_co2_annual*100):.1f}%" if site_co2_annual > 0 else "0%"
                    ]
                }
                st.table(pd.DataFrame(site_co2_breakdown_data))
                
                # Add Site vs CO2 breakdown
                st.markdown("**Site vs CO₂ Supply Breakdown**")
                site_total = site_capex_annual + site_opex_annual + site_maintenance_annual
                co2_total = appro_co2_capex_annual + appro_co2_opex_annual + appro_co2_maintenance_annual
                
                st.write(f"**Site Total:** {site_total:,.0f} €/year")
                st.write(f"  • CapEx: {site_capex_annual:,.0f} €")
                st.write(f"  • OpEx: {site_opex_annual:,.0f} €")
                st.write(f"  • Maintenance: {site_maintenance_annual:,.0f} €")
                st.write("")
                st.write(f"**CO₂ Supply Total:** {co2_total:,.0f} €/year")
                st.write(f"  • CapEx: {appro_co2_capex_annual:,.0f} €")
                st.write(f"  • OpEx: {appro_co2_opex_annual:,.0f} €")
                st.write(f"  • Maintenance: {appro_co2_maintenance_annual:,.0f} €")
            
            with col_site_2:
                st.markdown("**Contribution to Total LCOC**")
                st.metric("Total Site & CO₂ Cost", f"{site_co2_annual:,.0f} €/year")
                st.metric("Cost per kg CH₄", f"{site_co2_per_kg:.4f} €/kg")
                st.metric("% of Total LCOC", 
                         f"{(site_co2_per_kg/lcoc_results['lcoc_eur_per_kg']*100):.1f}%" if lcoc_results['lcoc_eur_per_kg'] > 0 else "0%")
        
        
        # Detailed Cost Breakdown Bar Charts
        st.markdown("#### 📊 Detailed Cost Breakdown by Component")
        
        # Get CapEx and Maintenance components if available
        capex_components = lcoc_results['annualized_costs'].get('capex_components', {})
        maintenance_breakdown = lcoc_results['annualized_costs'].get('maintenance_breakdown', {})
        
        # Create 3 columns for 3 charts
        col1, col2, col3 = st.columns(3)
        
        # --- 1. CapEx Breakdown Chart ---
        with col1:
            st.markdown("##### CapEx Components")
            if capex_components:
                capex_data = {
                    'Methanation Unit': capex_components.get('methanation_unit', 0),
                    'Purification': capex_components.get('purification_unit', 0),
                    'Compressor': capex_components.get('compressor', 0),
                    'CH₄ Storage': capex_components.get('ch4_storage', 0),
                    'Grid Injection': capex_components.get('grid_injection', 0),
                    'Others': capex_components.get('others', 0)
                }
                
                # Filter out zero values
                capex_data = {k: v for k, v in capex_data.items() if v > 0}
                
                if capex_data:
                    fig1, ax1 = plt.subplots(figsize=(6, 5))
                    components = list(capex_data.keys())
                    values = list(capex_data.values())
                    colors = plt.cm.Blues(np.linspace(0.4, 0.9, len(components)))
                    bars = ax1.barh(components, values, color=colors, edgecolor='black', linewidth=1.2)
                    
                    for bar, val in zip(bars, values):
                        width = bar.get_width()
                        ax1.text(width, bar.get_y() + bar.get_height()/2,
                               f' €{val:,.0f}',
                               ha='left', va='center', fontsize=8, fontweight='bold')
                    
                    ax1.set_xlabel('Cost (€)', fontsize=10, fontweight='bold')
                    title1 = f'Total: €{sum(values):,.0f}'
                    if avg_service_ratio is not None:
                        title1 += f'\nService Ratio: {avg_service_ratio:.1%}'
                    ax1.set_title(title1, fontsize=11, fontweight='bold', pad=10)
                    ax1.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1e6:.1f}M' if x >= 1e6 else f'{x/1e3:.0f}K'))
                    ax1.grid(axis='x', alpha=0.3, linestyle='--')
                    ax1.set_axisbelow(True)
                    plt.tight_layout()
                    st.pyplot(fig1)
                    plt.close()
            else:
                st.info("No CapEx breakdown available")
        
        # --- 2. OpEx Breakdown Chart ---
        with col2:
            st.markdown("##### OpEx Components")
            opex_data = {
                'Electricity': lifetime_electricity,
                'Others': lifetime_others_opex
            }
            
            # Filter out zero values
            opex_data = {k: v for k, v in opex_data.items() if v > 0}
            
            if opex_data:
                fig2, ax2 = plt.subplots(figsize=(6, 5))
                components = list(opex_data.keys())
                values = list(opex_data.values())
                colors = plt.cm.Oranges(np.linspace(0.4, 0.9, len(components)))
                bars = ax2.barh(components, values, color=colors, edgecolor='black', linewidth=1.2)
                
                for bar, val in zip(bars, values):
                    width = bar.get_width()
                    ax2.text(width, bar.get_y() + bar.get_height()/2,
                           f' €{val:,.0f}',
                           ha='left', va='center', fontsize=8, fontweight='bold')
                
                ax2.set_xlabel('Cost (€)', fontsize=10, fontweight='bold')
                title2 = f'Total: €{sum(values):,.0f}'
                if avg_service_ratio is not None:
                    title2 += f'\nService Ratio: {avg_service_ratio:.1%}'
                ax2.set_title(title2, fontsize=11, fontweight='bold', pad=10)
                ax2.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1e6:.1f}M' if x >= 1e6 else f'{x/1e3:.0f}K'))
                ax2.grid(axis='x', alpha=0.3, linestyle='--')
                ax2.set_axisbelow(True)
                plt.tight_layout()
                st.pyplot(fig2)
                plt.close()
            else:
                st.info("No OpEx breakdown available")
        
        # --- 3. Maintenance Breakdown Chart ---
        with col3:
            st.markdown("##### Maintenance Components")
            if maintenance_breakdown:
                maintenance_data = {
                    'Methanation Unit': maintenance_breakdown.get('methanation_unit', 0) * project_lifetime,
                    'Purification': maintenance_breakdown.get('purification_unit', 0) * project_lifetime,
                    'Compressor': maintenance_breakdown.get('compressor', 0) * project_lifetime,
                    'CH₄ Storage': maintenance_breakdown.get('ch4_storage', 0) * project_lifetime,
                    'Grid Injection': maintenance_breakdown.get('grid_injection', 0) * project_lifetime,
                    'Others': maintenance_breakdown.get('others', 0) * project_lifetime
                }
                
                # Filter out zero values
                maintenance_data = {k: v for k, v in maintenance_data.items() if v > 0}
                
                if maintenance_data:
                    fig3, ax3 = plt.subplots(figsize=(6, 5))
                    components = list(maintenance_data.keys())
                    values = list(maintenance_data.values())
                    colors = plt.cm.Greens(np.linspace(0.4, 0.9, len(components)))
                    bars = ax3.barh(components, values, color=colors, edgecolor='black', linewidth=1.2)
                    
                    for bar, val in zip(bars, values):
                        width = bar.get_width()
                        ax3.text(width, bar.get_y() + bar.get_height()/2,
                               f' €{val:,.0f}',
                               ha='left', va='center', fontsize=8, fontweight='bold')
                    
                    ax3.set_xlabel('Cost (€)', fontsize=10, fontweight='bold')
                    title3 = f'Total: €{sum(values):,.0f}'
                    if avg_service_ratio is not None:
                        title3 += f'\nService Ratio: {avg_service_ratio:.1%}'
                    ax3.set_title(title3, fontsize=11, fontweight='bold', pad=10)
                    ax3.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1e6:.1f}M' if x >= 1e6 else f'{x/1e3:.0f}K'))
                    ax3.grid(axis='x', alpha=0.3, linestyle='--')
                    ax3.set_axisbelow(True)
                    plt.tight_layout()
                    st.pyplot(fig3)
                    plt.close()
            else:
                st.info("No Maintenance breakdown available")
        
        # Electricity breakdown for methanation with chart
        st.markdown("#### ⚡ Methanation Electricity Cost")
        
        col_info, col_chart = st.columns([1, 1])
        
        with col_info:
            st.info(f"**Total methanation electricity:** {lcoc_results['methanation_electricity_mwh']:.1f} MWhe/year\n\n"
                    f"**Average electricity cost:** {lcoc_results['avg_electricity_cost_per_mwh']:.2f} €/MWh\n\n"
                    f"**Total electricity cost:** {lcoc_results['methanation_electricity_cost']:,.0f} €/year")
        
        with col_chart:
            # Create bar chart for electricity breakdown
            fig_elec, ax_elec = plt.subplots(figsize=(6, 4))
            
            categories = ['Consumption\n(MWhe)', 'Unit Cost\n(€/MWh)', 'Total Cost\n(€/year)']
            values = [
                lcoc_results['methanation_electricity_mwh'],
                lcoc_results['avg_electricity_cost_per_mwh'],
                lcoc_results['methanation_electricity_cost']
            ]
            colors = ['#4ECDC4', '#FF6B6B', '#FFD93D']
            
            bars = ax_elec.bar(categories, values, color=colors, edgecolor='black', linewidth=1.5, alpha=0.8)
            
            # Add value labels on bars
            for bar, val in zip(bars, values):
                height = bar.get_height()
                ax_elec.text(bar.get_x() + bar.get_width()/2., height,
                           f'{val:,.1f}' if val < 1000 else f'{val:,.0f}',
                           ha='center', va='bottom', fontsize=10, fontweight='bold')
            
            ax_elec.set_ylabel('Value', fontsize=10, fontweight='bold')
            ax_elec.set_title('Methanation Electricity Metrics', fontsize=12, fontweight='bold', pad=15)
            ax_elec.grid(axis='y', alpha=0.3, linestyle='--')
            ax_elec.set_axisbelow(True)
            
            plt.tight_layout()
            st.pyplot(fig_elec)
            plt.close()
        
        # Component Costs Summary with Charts
        st.markdown("#### 💰 Annual Costs by Component")
        
        # Create comprehensive cost comparison chart
        components = []
        capex_values = []
        opex_values = []
        maintenance_values = []
        total_values = []
        cost_per_kg_values = []
        
        # Electrolyzer
        components.append('Electrolyser')
        capex_values.append(electrolyzer_costs.get('capex_annual', 0))
        opex_values.append(electrolyzer_costs.get('opex_annual', 0))
        maintenance_values.append(electrolyzer_costs.get('maintenance_annual', 0))
        total_values.append(electrolyzer_annual)
        cost_per_kg_values.append(electrolyzer_per_kg)
        
        # Methanation
        components.append('Methanation')
        capex_values.append(methanation_costs.get('capex_annual', 0))
        opex_values.append(methanation_costs.get('opex_annual', 0))
        maintenance_values.append(methanation_costs.get('maintenance_annual', 0))
        total_values.append(methanation_annual)
        cost_per_kg_values.append(methanation_per_kg)
        
        # Site & CO2
        if site_co2_annual > 0:
            components.append('Site & CO₂')
            capex_values.append(site_co2_costs.get('capex_annual', 0))
            opex_values.append(site_co2_costs.get('opex_annual', 0))
            maintenance_values.append(site_co2_costs.get('maintenance_annual', 0))
            total_values.append(site_co2_annual)
            cost_per_kg_values.append(site_co2_per_kg)
        
        # Create stacked bar chart for cost breakdown
        fig_costs, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        # Chart 1: Stacked bar chart showing CapEx, OpEx, Maintenance
        x_pos = np.arange(len(components))
        bar_width = 0.6
        
        p1 = ax1.bar(x_pos, capex_values, bar_width, label='CapEx', color='#1f77b4', edgecolor='black', linewidth=1.2)
        p2 = ax1.bar(x_pos, opex_values, bar_width, bottom=capex_values, label='OpEx', color='#ff7f0e', edgecolor='black', linewidth=1.2)
        p3 = ax1.bar(x_pos, maintenance_values, bar_width, 
                     bottom=np.array(capex_values) + np.array(opex_values),
                     label='Maintenance', color='#2ca02c', edgecolor='black', linewidth=1.2)
        
        # Add total value labels on top of stacked bars
        for i, (total, comp) in enumerate(zip(total_values, components)):
            ax1.text(i, total, f'€{total:,.0f}', ha='center', va='bottom', fontsize=9, fontweight='bold')
        
        ax1.set_ylabel('Annual Cost (€/year)', fontsize=11, fontweight='bold')
        ax1.set_title('Annual Cost Breakdown by Component', fontsize=13, fontweight='bold', pad=15)
        ax1.set_xticks(x_pos)
        ax1.set_xticklabels(components, fontsize=10, fontweight='bold')
        ax1.legend(loc='upper left', fontsize=10)
        ax1.grid(axis='y', alpha=0.3, linestyle='--')
        ax1.set_axisbelow(True)
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1e6:.1f}M' if x >= 1e6 else f'{x/1e3:.0f}K'))
        
        # Chart 2: Cost per kg CH4
        bars2 = ax2.bar(x_pos, cost_per_kg_values, bar_width, color=['#4ECDC4', '#FF6B6B', '#FFD93D'][:len(components)],
                       edgecolor='black', linewidth=1.2, alpha=0.85)
        
        # Add value labels
        for i, (bar, val) in enumerate(zip(bars2, cost_per_kg_values)):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                   f'{val:.3f} €',
                   ha='center', va='bottom', fontsize=10, fontweight='bold')
        
        ax2.set_ylabel('Cost (€/kg CH₄)', fontsize=11, fontweight='bold')
        ax2.set_title('Cost per kg CH₄ by Component', fontsize=13, fontweight='bold', pad=15)
        ax2.set_xticks(x_pos)
        ax2.set_xticklabels(components, fontsize=10, fontweight='bold')
        ax2.grid(axis='y', alpha=0.3, linestyle='--')
        ax2.set_axisbelow(True)
        
        plt.tight_layout()
        st.pyplot(fig_costs)
        plt.close()
        
        # Summary table
        st.markdown("##### 📋 Cost Summary Table")
        summary_data = {
            'Component': components,
            'CapEx (€/year)': [f"{v:,.0f}" for v in capex_values],
            'OpEx (€/year)': [f"{v:,.0f}" for v in opex_values],
            'Maintenance (€/year)': [f"{v:,.0f}" for v in maintenance_values],
            'Total (€/year)': [f"{v:,.0f}" for v in total_values],
            'Cost (€/kg CH₄)': [f"{v:.3f}" for v in cost_per_kg_values]
        }
        
        df_summary = pd.DataFrame(summary_data)
        st.table(df_summary)
