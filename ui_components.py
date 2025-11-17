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


def display_lcoh_results(lcoh_results, avg_service_ratio=None, go_enabled=False, go_cost_per_mwh=0.0):
    """Display LCOH calculation results"""
    st.markdown("---")
    st.markdown("### 💧 LCOH (Levelized Cost of Hydrogen) Analysis")
    
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


def display_lcoc_results(lcoc_results, avg_service_ratio=None):
    """Display LCOC (Levelized Cost of CH4) calculation results"""
    st.markdown("---")
    st.markdown("### 🔥 LCOC (Levelized Cost of CH₄/Methane) Analysis")
    
    # Main metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("**LCOC**", f"{lcoc_results['lcoc_eur_per_kg']:.2f} €/kg CH₄")
    with col2:
        st.metric("**LCOC**", f"{lcoc_results['lcoc_eur_per_mwh']:.1f} €/MWh CH₄")
    with col3:
        st.metric("**CH₄ Production**", f"{lcoc_results['ch4_production_tonnes']:.1f} T/year")
    with col4:
        st.metric("**Total Annual Cost**", f"{lcoc_results['total_annual_cost']:,.0f} €")
    
    # Show H2 input
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("**H₂ Consumption**", f"{lcoc_results['h2_consumption_tonnes']:.1f} T/year")
    with col2:
        st.metric("**H₂ to CH₄ Ratio**", f"1 : {lcoc_results['ch4_production_kg']/lcoc_results['h2_consumption_kg']:.2f}")
    with col3:
        st.metric("**Methanation Elec.**", f"{lcoc_results['methanation_electricity_mwh']:.1f} MWh/year")
    with col4:
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
        lifetime_total = lifetime_capex + lifetime_opex + lifetime_maintenance + lifetime_other
        
        # Calculate combined maintenance
        total_maintenance_annual = (
            lcoc_results['annualized_costs']['maintenance_annual'] +
            lcoc_results['annualized_costs']['other_annual']
        )
        lifetime_total_maintenance = lifetime_maintenance + lifetime_other
        maintenance_per_kg = breakdown['maintenance'] + breakdown['other']
        
        # Create breakdown dataframe - simplified to 3 main categories
        breakdown_data = {
            'Component': [
                'CapEx',
                'OpEx',
                'Maintenance',
                '**TOTAL LCOC**'
            ],
            'Cost (€/kg CH₄)': [
                f"{breakdown['capex']:.3f}",
                f"{breakdown['opex']:.3f}",
                f"{maintenance_per_kg:.3f}",
                f"**{lcoc_results['lcoc_eur_per_kg']:.3f}**"
            ],
            'Annual Cost (€)': [
                f"{lcoc_results['annualized_costs']['capex_annualized']:,.0f}",
                f"{lcoc_results['annualized_costs']['opex_annual']:,.0f}",
                f"{total_maintenance_annual:,.0f}",
                f"**{lcoc_results['total_annual_cost']:,.0f}**"
            ],
            f'Lifetime Cost ({project_lifetime} years) (€)': [
                f"{lifetime_capex:,.0f}",
                f"{lifetime_opex:,.0f}",
                f"{lifetime_total_maintenance:,.0f}",
                f"**{lifetime_total:,.0f}**"
            ],
            'Percentage': [
                f"{(breakdown['capex']/lcoc_results['lcoc_eur_per_kg']*100):.1f}%" if lcoc_results['lcoc_eur_per_kg'] > 0 else "0%",
                f"{(breakdown['opex']/lcoc_results['lcoc_eur_per_kg']*100):.1f}%" if lcoc_results['lcoc_eur_per_kg'] > 0 else "0%",
                f"{(maintenance_per_kg/lcoc_results['lcoc_eur_per_kg']*100):.1f}%" if lcoc_results['lcoc_eur_per_kg'] > 0 else "0%",
                "**100.0%**"
            ]
        }
        
        df_breakdown = pd.DataFrame(breakdown_data)
        
        # Create two columns: table on left, pie chart on right
        col_table, col_pie = st.columns([2, 1])
        
        with col_table:
            st.table(df_breakdown)
        
        with col_pie:
            # Create pie chart for LCOC breakdown
            pie_labels = ['CapEx', 'OpEx', 'Maintenance']
            pie_values = [breakdown['capex'], breakdown['opex'], maintenance_per_kg]
            
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
            title = 'LCOC Cost Breakdown'
            if avg_service_ratio is not None:
                title += f'\nService Ratio: {avg_service_ratio:.1%}'
            ax_pie.set_title(title, fontsize=12, fontweight='bold', pad=20)
            
            ax_pie.axis('equal')
            plt.tight_layout()
            st.pyplot(fig_pie)
        
        # Detailed Cost Breakdown Bar Charts
        st.markdown("#### 📊 Detailed Cost Breakdown")
        
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
        
        # Electricity breakdown for methanation
        st.markdown("#### ⚡ Methanation Electricity Cost")
        st.info(f"Total methanation electricity: **{lcoc_results['methanation_electricity_mwh']:.1f} MWh/year**  \n"
                f"Average electricity cost: **{lcoc_results['avg_electricity_cost_per_mwh']:.2f} €/MWh**  \n"
                f"Total electricity cost: **{lcoc_results['methanation_electricity_cost']:,.0f} €/year**")
