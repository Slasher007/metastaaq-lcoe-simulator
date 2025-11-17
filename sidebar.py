"""
Sidebar configuration and parameter inputs for the MetaSTAAQ Dashboard
"""

import streamlit as st
import pandas as pd
from config import DEFAULT_PARAMS, PARAM_RANGES, MONTHS, STRATEGY_TYPES


def setup_sidebar_header():
    """Set up the sidebar header"""
    st.sidebar.markdown("### 🔧 Simulation Parameters")


def load_data_file(file_path):
    """Load the default data file"""
    try:
        return pd.read_csv(file_path)
    except FileNotFoundError:
        st.error("❌ Default data file not found. Please ensure the data file is in the correct location.")
        st.stop()


def create_year_selection(data_content):
    """Create year selection widget"""
    st.sidebar.markdown("#### 📅 Year Selection")
    available_years = sorted(data_content['Annee'].unique()) if 'Annee' in data_content.columns else [2024, 2025]
    selected_years = st.sidebar.multiselect(
        "Select years for analysis",
        options=available_years,
        default=[2024] if 2024 in available_years else available_years[:1]
    )
    return selected_years


def create_electrolyzer_parameters():
    """Create electrolyzer parameter inputs including economics"""
    with st.sidebar.expander("⚡ Electrolyser", expanded=True):
        st.markdown("**Technical Parameters**")
        electrolyser_power = st.slider(
            "Electrolyzer Power (MW)",
            min_value=PARAM_RANGES["electrolyser_power"]["min"],
            max_value=PARAM_RANGES["electrolyser_power"]["max"],
            value=DEFAULT_PARAMS["electrolyser_power"],
            step=PARAM_RANGES["electrolyser_power"]["step"],
            help="Power capacity of the electrolyzer in MW"
        )

        electrolyser_specific_consumption = st.slider(
            "Specific Consumption (kWh/Nm³ H₂)",
            min_value=PARAM_RANGES["electrolyser_specific_consumption"]["min"],
            max_value=PARAM_RANGES["electrolyser_specific_consumption"]["max"],
            value=DEFAULT_PARAMS["electrolyser_specific_consumption"],
            step=PARAM_RANGES["electrolyser_specific_consumption"]["step"],
            help="Energy consumption per cubic meter of hydrogen produced"
        )
    
        st.markdown("---")
        st.markdown("### Economic Parameters (LCOH)")
        
        # Project parameters
        electrolyzer_lifetime = st.slider(
            "Project Lifetime (years)",
            min_value=PARAM_RANGES["electrolyzer_lifetime"]["min"],
            max_value=PARAM_RANGES["electrolyzer_lifetime"]["max"],
            value=DEFAULT_PARAMS["electrolyzer_lifetime"],
            step=PARAM_RANGES["electrolyzer_lifetime"]["step"],
            help="Expected lifetime of the electrolyzer project"
        )
        
        electrolyzer_discount_rate = st.slider(
            "Discount Rate (%)",
            min_value=PARAM_RANGES["electrolyzer_discount_rate"]["min"],
            max_value=PARAM_RANGES["electrolyzer_discount_rate"]["max"],
            value=DEFAULT_PARAMS["electrolyzer_discount_rate"],
            step=PARAM_RANGES["electrolyzer_discount_rate"]["step"],
            help="Discount rate for LCOH calculation"
        )
        
        # ============================================
        # CAPEX SECTION
        # ============================================
        st.markdown("---")
        st.markdown("#### CapEx (Capital Expenditure)")
        
        with st.expander("CapEx Parameters", expanded=False):
            capex_transformer = st.number_input(
                "Poste de transformation (€)",
                min_value=PARAM_RANGES["capex_transformer"]["min"],
                max_value=PARAM_RANGES["capex_transformer"]["max"],
                value=DEFAULT_PARAMS["capex_transformer"],
                step=PARAM_RANGES["capex_transformer"]["step"],
                help="Transformer station cost"
            )
            
            capex_electrolyzer = st.number_input(
                "Electrolyseur (€)",
                min_value=PARAM_RANGES["capex_electrolyzer"]["min"],
                max_value=PARAM_RANGES["capex_electrolyzer"]["max"],
                value=DEFAULT_PARAMS["capex_electrolyzer"],
                step=PARAM_RANGES["capex_electrolyzer"]["step"],
                help="Electrolyzer unit cost"
            )
            
            capex_compressor = st.number_input(
                "Compresseur (€)",
                min_value=PARAM_RANGES["capex_compressor"]["min"],
                max_value=PARAM_RANGES["capex_compressor"]["max"],
                value=DEFAULT_PARAMS["capex_compressor"],
                step=PARAM_RANGES["capex_compressor"]["step"],
                help="Compressor cost"
            )
            
            capex_h2_storage = st.number_input(
                "Stockage H2 (€)",
                min_value=PARAM_RANGES["capex_h2_storage"]["min"],
                max_value=PARAM_RANGES["capex_h2_storage"]["max"],
                value=DEFAULT_PARAMS["capex_h2_storage"],
                step=PARAM_RANGES["capex_h2_storage"]["step"],
                help="H2 storage cost"
            )
            
            capex_piping = st.number_input(
                "Piping, ... (€)",
                min_value=PARAM_RANGES["capex_piping"]["min"],
                max_value=PARAM_RANGES["capex_piping"]["max"],
                value=DEFAULT_PARAMS["capex_piping"],
                step=PARAM_RANGES["capex_piping"]["step"],
                help="Piping and other infrastructure costs"
            )
            
            # Stack replacement
            stack_replacement_cost = st.number_input(
                "Stack Replacement Cost (€)",
                min_value=PARAM_RANGES["stack_replacement_cost"]["min"],
                max_value=PARAM_RANGES["stack_replacement_cost"]["max"],
                value=DEFAULT_PARAMS["stack_replacement_cost"],
                step=PARAM_RANGES["stack_replacement_cost"]["step"],
                help="Total cost for stack replacement"
            )
            
            stack_replacement_years = st.slider(
                "Stack Replacement Interval (years)",
                min_value=PARAM_RANGES["stack_replacement_years"]["min"],
                max_value=PARAM_RANGES["stack_replacement_years"]["max"],
                value=DEFAULT_PARAMS["stack_replacement_years"],
                step=PARAM_RANGES["stack_replacement_years"]["step"],
                help="Years between stack replacements"
            )
            
            # Others CapEx
            others_capex = st.number_input(
                "Others CapEx (€)",
                min_value=PARAM_RANGES["others_capex"]["min"],
                max_value=PARAM_RANGES["others_capex"]["max"],
                value=DEFAULT_PARAMS["others_capex"],
                step=PARAM_RANGES["others_capex"]["step"],
                help="Other capital expenditures"
            )
        
        # Calculate total CapEx
        electrolyzer_capex_total = (
            capex_transformer + 
            capex_electrolyzer + 
            capex_compressor + 
            capex_h2_storage + 
            capex_piping +
            stack_replacement_cost +
            others_capex
        )
        
        # Calculate and display annualized CapEx
        from calculate_lcoh import calculate_crf
        crf = calculate_crf(electrolyzer_discount_rate, electrolyzer_lifetime)
        electrolyzer_capex_annual = electrolyzer_capex_total * crf
        
        # Display totals
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total CapEx", f"{electrolyzer_capex_total:,.0f} €")
        with col2:
            st.metric("CapEx Annualized", f"{electrolyzer_capex_annual:,.0f} €/year")
        
        # ============================================
        # OPEX SECTION
        # ============================================
        st.markdown("---")
        st.markdown("#### OpEx (Operational Expenditure)")
        
        with st.expander("OpEx Parameters", expanded=False):
            st.info("OPEX = Electricity Cost + Water Cost + Others")
            
            st.markdown("**Water Costs**")
            water_price_per_m3 = st.number_input(
                "Water Price (€/m³)",
                min_value=PARAM_RANGES["water_price_per_m3"]["min"],
                max_value=PARAM_RANGES["water_price_per_m3"]["max"],
                value=DEFAULT_PARAMS["water_price_per_m3"],
                step=PARAM_RANGES["water_price_per_m3"]["step"],
                help="Unit price of water per cubic meter"
            )
            
            water_consumption_annual_m3 = st.number_input(
                "Water Consumption (m³/year)",
                min_value=PARAM_RANGES["water_consumption_annual_m3"]["min"],
                max_value=PARAM_RANGES["water_consumption_annual_m3"]["max"],
                value=DEFAULT_PARAMS["water_consumption_annual_m3"],
                step=PARAM_RANGES["water_consumption_annual_m3"]["step"],
                help="Annual water consumption in cubic meters"
            )
            
            st.markdown("**Others OpEx**")
            others_opex_annual = st.number_input(
                "Others OpEx (€/year)",
                min_value=PARAM_RANGES["others_opex_annual"]["min"],
                max_value=PARAM_RANGES["others_opex_annual"]["max"],
                value=DEFAULT_PARAMS["others_opex_annual"],
                step=PARAM_RANGES["others_opex_annual"]["step"],
                help="Other operational expenditures (e.g., consumables, utilities)"
            )
            
            st.caption("Electricity cost will be calculated from energy consumption and prices (PV, Spot, PPA)")
        
        # Calculate water cost
        water_cost_annual = water_price_per_m3 * water_consumption_annual_m3
        
        # Display total (electricity will be added during calculation)
        st.metric("Total OpEx (Water + Others)", f"{water_cost_annual + others_opex_annual:,.0f} €/year", 
                  help="Electricity cost will be added during LCOH calculation")
        
        # ============================================
        # MAINTENANCE SECTION
        # ============================================
        st.markdown("---")
        st.markdown("#### Maintenance Costs")
        
        with st.expander("Maintenance Parameters", expanded=False):
            st.info("Maintenance is calculated as a percentage of each CapEx component")
            
            st.markdown("**Maintenance Ratios (% of CapEx per year)**")
            col1, col2 = st.columns(2)
            with col1:
                maintenance_ratio_transformer = st.number_input(
                    "Poste transformation (%)",
                    min_value=PARAM_RANGES["maintenance_ratio_transformer"]["min"],
                    max_value=PARAM_RANGES["maintenance_ratio_transformer"]["max"],
                    value=DEFAULT_PARAMS["maintenance_ratio_transformer"],
                    step=PARAM_RANGES["maintenance_ratio_transformer"]["step"],
                    help="Annual maintenance as % of transformer CapEx"
                )
                
                maintenance_ratio_electrolyzer = st.number_input(
                    "Electrolyseur (%)",
                    min_value=PARAM_RANGES["maintenance_ratio_electrolyzer"]["min"],
                    max_value=PARAM_RANGES["maintenance_ratio_electrolyzer"]["max"],
                    value=DEFAULT_PARAMS["maintenance_ratio_electrolyzer"],
                    step=PARAM_RANGES["maintenance_ratio_electrolyzer"]["step"],
                    help="Annual maintenance as % of electrolyzer CapEx"
                )
                
                maintenance_ratio_compressor = st.number_input(
                    "Compresseur (%)",
                    min_value=PARAM_RANGES["maintenance_ratio_compressor"]["min"],
                    max_value=PARAM_RANGES["maintenance_ratio_compressor"]["max"],
                    value=DEFAULT_PARAMS["maintenance_ratio_compressor"],
                    step=PARAM_RANGES["maintenance_ratio_compressor"]["step"],
                    help="Annual maintenance as % of compressor CapEx"
                )
            
            with col2:
                maintenance_ratio_h2_storage = st.number_input(
                    "Stockage H2 (%)",
                    min_value=PARAM_RANGES["maintenance_ratio_h2_storage"]["min"],
                    max_value=PARAM_RANGES["maintenance_ratio_h2_storage"]["max"],
                    value=DEFAULT_PARAMS["maintenance_ratio_h2_storage"],
                    step=PARAM_RANGES["maintenance_ratio_h2_storage"]["step"],
                    help="Annual maintenance as % of H2 storage CapEx"
                )
                
                maintenance_ratio_piping = st.number_input(
                    "Piping, ... (%)",
                    min_value=PARAM_RANGES["maintenance_ratio_piping"]["min"],
                    max_value=PARAM_RANGES["maintenance_ratio_piping"]["max"],
                    value=DEFAULT_PARAMS["maintenance_ratio_piping"],
                    step=PARAM_RANGES["maintenance_ratio_piping"]["step"],
                    help="Annual maintenance as % of piping CapEx"
                )
            
            st.markdown("**Others Maintenance**")
            others_maintenance_annual = st.number_input(
                "Others Maintenance (€/year)",
                min_value=PARAM_RANGES["others_maintenance_annual"]["min"],
                max_value=PARAM_RANGES["others_maintenance_annual"]["max"],
                value=DEFAULT_PARAMS["others_maintenance_annual"],
                step=PARAM_RANGES["others_maintenance_annual"]["step"],
                help="Other maintenance costs"
            )
        
        # Calculate maintenance costs
        maintenance_transformer = capex_transformer * (maintenance_ratio_transformer / 100)
        maintenance_electrolyzer = capex_electrolyzer * (maintenance_ratio_electrolyzer / 100)
        maintenance_compressor = capex_compressor * (maintenance_ratio_compressor / 100)
        maintenance_h2_storage = capex_h2_storage * (maintenance_ratio_h2_storage / 100)
        maintenance_piping = capex_piping * (maintenance_ratio_piping / 100)
        
        # Total maintenance
        electrolyzer_maintenance_annual = (
            maintenance_transformer +
            maintenance_electrolyzer +
            maintenance_compressor +
            maintenance_h2_storage +
            maintenance_piping +
            others_maintenance_annual
        )
        
        # Display total
        st.metric("Total Maintenance", f"{electrolyzer_maintenance_annual:,.0f} €/year")
    
    # Calculate other_costs_annual (Others CapEx annualized + Others Maintenance)
    # Note: Others OpEx is handled separately in OPEX
    other_costs_annual = others_capex * calculate_crf(electrolyzer_discount_rate, electrolyzer_lifetime) + others_maintenance_annual
    
    electrolyzer_econ = {
        'capex_components': {
            'transformer': capex_transformer,
            'electrolyzer': capex_electrolyzer,
            'compressor': capex_compressor,
            'h2_storage': capex_h2_storage,
            'piping': capex_piping,
            'others': others_capex
        },
        'maintenance_ratios': {
            'transformer': maintenance_ratio_transformer,
            'electrolyzer': maintenance_ratio_electrolyzer,
            'compressor': maintenance_ratio_compressor,
            'h2_storage': maintenance_ratio_h2_storage,
            'piping': maintenance_ratio_piping
        },
        'maintenance_breakdown': {
            'transformer': maintenance_transformer,
            'electrolyzer': maintenance_electrolyzer,
            'compressor': maintenance_compressor,
            'h2_storage': maintenance_h2_storage,
            'piping': maintenance_piping,
            'others': others_maintenance_annual
        },
        'electrolyzer_capex_total': electrolyzer_capex_total,
        'electrolyzer_capex_annual': electrolyzer_capex_annual,
        'electrolyzer_lifetime': electrolyzer_lifetime,
        'electrolyzer_discount_rate': electrolyzer_discount_rate,
        'electrolyzer_maintenance_annual': electrolyzer_maintenance_annual,
        'water_price_per_m3': water_price_per_m3,
        'water_consumption_annual_m3': water_consumption_annual_m3,
        'water_cost_annual': water_cost_annual,
        'others_capex': others_capex,
        'others_opex_annual': others_opex_annual,
        'others_maintenance_annual': others_maintenance_annual,
        'other_costs_annual': other_costs_annual,
        'stack_replacement_cost': stack_replacement_cost,
        'stack_replacement_years': stack_replacement_years
    }
    
    return electrolyser_power, electrolyser_specific_consumption, electrolyzer_econ


def create_monthly_service_ratios(allow_edit=True, preset_ratios=None):
    """Create or display monthly service ratios in the sidebar.

    When allow_edit is False (Target Price strategy), the sliders are hidden and
    ratios are shown as read-only if available after simulation.
    """
    monthly_service_ratios = {}

    with st.sidebar.expander("📅 Service Ratios", expanded=True):
        if allow_edit:
            st.markdown("*Set individual availability ratios for each month (0.0 = off, 1.0 = always on)*")
            col1, col2 = st.columns(2)
            with col1:
                for month in MONTHS[:6]:
                    monthly_service_ratios[month] = st.slider(
                        f"{month[:3]}",
                        min_value=PARAM_RANGES["service_ratio"]["min"],
                        max_value=PARAM_RANGES["service_ratio"]["max"],
                        value=DEFAULT_PARAMS["service_ratio"],
                        step=PARAM_RANGES["service_ratio"]["step"],
                        key=f"service_{month}",
                        help=f"Service ratio for {month}"
                    )
            with col2:
                for month in MONTHS[6:]:
                    monthly_service_ratios[month] = st.slider(
                        f"{month[:3]}",
                        min_value=PARAM_RANGES["service_ratio"]["min"],
                        max_value=PARAM_RANGES["service_ratio"]["max"],
                        value=DEFAULT_PARAMS["service_ratio"],
                        step=PARAM_RANGES["service_ratio"]["step"],
                        key=f"service_{month}",
                        help=f"Service ratio for {month}"
                    )
        else:
            st.info("Service ratios are automatically computed from Target Price results.")
            # If preset ratios are provided (post-simulation), display them read-only
            if preset_ratios:
                for month in MONTHS:
                    ratio = preset_ratios.get(month, DEFAULT_PARAMS["service_ratio"])
                    st.write(f"**{month[:3]}**: {ratio:.0%}")
            # Return defaults initially; they will be overridden after simulation
            for month in MONTHS:
                monthly_service_ratios[month] = DEFAULT_PARAMS["service_ratio"]

    return monthly_service_ratios


def create_operation_strategy_selection():
    """Create operation strategy selection"""
    st.sidebar.markdown("#### 🎯 Operation Strategy")
    strategy_type = st.sidebar.selectbox(
        "Choose Operation Strategy",
        options=STRATEGY_TYPES,
        index=0,
        help="Select the strategy for electrolyzer operation optimization"
    )
    return strategy_type


def create_price_parameters(strategy_type):
    """Create price parameter inputs"""
    with st.sidebar.expander("💰 Price", expanded=True):
        if strategy_type == "Service Ratio-Based":
            st.info("ℹ️ Service Ratio strategy cumulates spot hours while keeping average cost below PPA price.")
        else:
            st.info("ℹ️ Target Price strategy cumulates spot hours while keeping cumulative average below target price.")
        
        # Target prices (single price for Target Price-Based strategy)
        target_prices = []
        if strategy_type == "Target Price-Based":
            st.markdown("**Target Price (€/MWh):**")
            target_prices.append(st.slider(
                "Target Spot Price",
                min_value=PARAM_RANGES["target_price"]["min"],
                max_value=PARAM_RANGES["target_price"]["max"],
                value=DEFAULT_PARAMS["target_price"],
                step=PARAM_RANGES["target_price"]["step"],
                help="Electrolyzer cumulates hours while cumulative average ≤ this target price"
            ))
        else:
            target_prices = [DEFAULT_PARAMS["target_price"]]

        pv_price = st.slider(
            "PV Price (€/MWh)",
            min_value=PARAM_RANGES["pv_price"]["min"],
            max_value=PARAM_RANGES["pv_price"]["max"],
            value=DEFAULT_PARAMS["pv_price"],
            step=PARAM_RANGES["pv_price"]["step"],
            help="Price for photovoltaic energy"
        )

        ppa_price = st.slider(
            "PPA Price (€/MWh)",
            min_value=PARAM_RANGES["ppa_price"]["min"],
            max_value=PARAM_RANGES["ppa_price"]["max"],
            value=DEFAULT_PARAMS["ppa_price"],
            step=PARAM_RANGES["ppa_price"]["step"],
            help="Power Purchase Agreement price"
        )
        
        # GO (Guarantee of Origin) Certificate for Spot
        st.markdown("---")
        st.markdown("**🌱 GO Certificate for Spot**")
        go_enabled = st.checkbox(
            "Enable GO for Spot",
            value=False,
            help="Add Guarantee of Origin certificate cost to Spot energy"
        )
        
        go_cost_per_mwh = 0.0
        if go_enabled:
            go_cost_per_mwh = st.slider(
                "GO Cost (€/MWh)",
                min_value=3.0,
                max_value=10.0,
                value=10.0,
                step=0.5,
                help="Additional cost per MWh for Guarantee of Origin certificate"
            )
            st.info(f"💡 GO cost of +{go_cost_per_mwh}€/MWh will be added to each MWh from Spot")

    return target_prices, pv_price, ppa_price, go_enabled, go_cost_per_mwh




def create_pv_installation_parameters():
    """Create PV installation parameter inputs"""
    with st.sidebar.expander("☀️ PV Installation", expanded=True):
        pv_project_years = st.slider(
            "Project Lifetime (years)",
            min_value=PARAM_RANGES["pv_project_years"]["min"],
            max_value=PARAM_RANGES["pv_project_years"]["max"],
            value=DEFAULT_PARAMS["pv_project_years"],
            step=PARAM_RANGES["pv_project_years"]["step"],
            help="Expected lifetime of the PV installation"
        )

        pv_surface_hectares = st.number_input(
            "Surface Area (hectares)",
            min_value=PARAM_RANGES["pv_surface_hectares"]["min"],
            max_value=PARAM_RANGES["pv_surface_hectares"]["max"],
            value=DEFAULT_PARAMS["pv_surface_hectares"],
            step=PARAM_RANGES["pv_surface_hectares"]["step"],
            help="Total surface area for PV installation"
        )

        power_density_mwp_per_ha = st.slider(
            "Power Density (MWp/hectare)",
            min_value=PARAM_RANGES["power_density_mwp_per_ha"]["min"],
            max_value=PARAM_RANGES["power_density_mwp_per_ha"]["max"],
            value=DEFAULT_PARAMS["power_density_mwp_per_ha"],
            step=PARAM_RANGES["power_density_mwp_per_ha"]["step"],
            help="Power density of PV installation per hectare"
        )

        st.markdown("#### PVGIS Parameters")
        
        # Initialize session state for coordinates if not exists
        if 'pv_lat' not in st.session_state:
            st.session_state.pv_lat = 48.9667
        if 'pv_lon' not in st.session_state:
            st.session_state.pv_lon = 2.8500
        
        # Check if coordinates were updated from map click
        if 'map_clicked_lat' in st.session_state and 'map_clicked_lon' in st.session_state:
            st.session_state.pv_lat = st.session_state.map_clicked_lat
            st.session_state.pv_lon = st.session_state.map_clicked_lon
            # Clear the temporary clicked values
            del st.session_state.map_clicked_lat
            del st.session_state.map_clicked_lon
        
        lat = st.number_input("Latitude", value=st.session_state.pv_lat, step=0.0001, format="%.4f", key="lat_input")
        lon = st.number_input("Longitude", value=st.session_state.pv_lon, step=0.0001, format="%.4f", key="lon_input")
        
        # Update session state if user manually changes the inputs
        st.session_state.pv_lat = lat
        st.session_state.pv_lon = lon
        
        loss = st.number_input("System Loss (%)", value=14.0, min_value=0.0, max_value=50.0, step=0.1)

        # Calculate estimated power
        estimated_power_mwp = pv_surface_hectares * power_density_mwp_per_ha
        estimated_power_kwp = estimated_power_mwp * 1000
        st.write(f"**Estimated Power**: {estimated_power_mwp:.2f} MWp ({estimated_power_kwp:,.0f} kWp)")

        pv_cost_per_wp = st.slider(
            "PV Cost (€/Wp)",
            min_value=PARAM_RANGES["pv_cost_per_wp"]["min"],
            max_value=PARAM_RANGES["pv_cost_per_wp"]["max"],
            value=DEFAULT_PARAMS["pv_cost_per_wp"],
            step=PARAM_RANGES["pv_cost_per_wp"]["step"],
            help="Cost per watt peak for PV installation"
        )

        include_battery = st.checkbox(
            "Include Battery Storage",
            value=False,
            help="Include battery storage in the analysis"
        )

        storage_hours = 0
        battery_cost_per_kwh = 0
        if include_battery:
            storage_hours = st.slider(
                "Storage Hours",
                min_value=PARAM_RANGES["storage_hours"]["min"],
                max_value=PARAM_RANGES["storage_hours"]["max"],
                value=DEFAULT_PARAMS["storage_hours"],
                step=PARAM_RANGES["storage_hours"]["step"],
                help="Daily storage capacity in hours"
            )

            battery_capacity_mwh = storage_hours * estimated_power_mwp
            st.write(f"**Daily Battery Capacity**: {battery_capacity_mwh:.2f} MWh/day ({storage_hours}h × {estimated_power_mwp:.2f} MWp)")

            battery_cost_per_kwh = st.slider(
                "Battery Cost (€/kWh)",
                min_value=PARAM_RANGES["battery_cost_per_kwh"]["min"],
                max_value=PARAM_RANGES["battery_cost_per_kwh"]["max"],
                value=DEFAULT_PARAMS["battery_cost_per_kwh"],
                step=PARAM_RANGES["battery_cost_per_kwh"]["step"],
                help="Cost per kWh for battery storage"
            )

        use_calculated_capex = st.checkbox(
            "Use Calculated CAPEX",
            value=True,
            help="Use calculated CAPEX based on power and costs"
        )

        pv_capex = 0
        if use_calculated_capex:
            # estimated_power_kwp is in kWp; convert to Wp for €/Wp input
            pv_capex_calculated = (estimated_power_kwp * 1000) * pv_cost_per_wp
            # Convert MWh to kWh for cost per kWh
            battery_capex = (battery_capacity_mwh * 1000) * battery_cost_per_kwh if include_battery else 0
            total_capex_calculated = pv_capex_calculated + battery_capex
            
            st.write(f"**Calculated CAPEX**:")
            st.write(f"• PV: {pv_capex_calculated:,.0f} €")
            if include_battery:
                st.write(f"• Battery: {battery_capex:,.0f} €")
            st.write(f"• **Total: {total_capex_calculated:,.0f} €**")
        else:
            pv_capex = st.number_input(
                "PV CAPEX (€)",
                min_value=0,
                value=0,
                step=1000,
                help="Manual PV CAPEX input"
            )

        opex_percentage = st.slider(
            "OPEX Percentage (%)",
            min_value=PARAM_RANGES["opex_percentage"]["min"],
            max_value=PARAM_RANGES["opex_percentage"]["max"],
            value=DEFAULT_PARAMS["opex_percentage"],
            step=PARAM_RANGES["opex_percentage"]["step"],
            help="Annual OPEX as percentage of CAPEX"
        )

        discount_rate = st.slider(
            "Discount Rate (%)",
            min_value=PARAM_RANGES["discount_rate"]["min"],
            max_value=PARAM_RANGES["discount_rate"]["max"],
            value=DEFAULT_PARAMS["discount_rate"],
            step=PARAM_RANGES["discount_rate"]["step"],
            help="Discount rate for LCOE calculation"
        )

        use_calculated_opex = st.checkbox(
            "Use Calculated OPEX",
            value=True,
            help="Use calculated OPEX based on CAPEX percentage"
        )

        pv_opex = 0
        if use_calculated_opex:
            # Calculate OPEX from total CAPEX (PV + Battery)
            if use_calculated_capex:
                total_capex_for_opex = total_capex_calculated
            else:
                # Convert MWh to kWh for cost per kWh
                manual_battery_capex = ((battery_capacity_mwh * 1000) * battery_cost_per_kwh) if include_battery else 0
                total_capex_for_opex = pv_capex + manual_battery_capex

            pv_opex = total_capex_for_opex * opex_percentage / 100
            st.write(f"**Calculated OPEX**: {pv_opex:,.0f} €/year ({opex_percentage}% of total CAPEX)")
        else:
            pv_opex = st.number_input(
                "PV OPEX (€/year)",
                min_value=0,
                value=0,
                step=1000,
                help="Manual PV OPEX input"
            )

        pci_ch4_kwh_per_kg = st.slider(
            "PCI CH₄ (kWh/kg)",
            min_value=PARAM_RANGES["pci_ch4_kwh_per_kg"]["min"],
            max_value=PARAM_RANGES["pci_ch4_kwh_per_kg"]["max"],
            value=DEFAULT_PARAMS["pci_ch4_kwh_per_kg"],
            step=PARAM_RANGES["pci_ch4_kwh_per_kg"]["step"],
            help="Lower heating value of methane"
        )

    return {
        'pv_project_years': pv_project_years,
        'pv_surface_hectares': pv_surface_hectares,
        'power_density_mwp_per_ha': power_density_mwp_per_ha,
        'estimated_power_mwp': estimated_power_mwp,
        'estimated_power_kwp': estimated_power_kwp,
        'pv_cost_per_wp': pv_cost_per_wp,
        'include_battery': include_battery,
        'storage_hours': storage_hours,
        'battery_capacity_mwh': battery_capacity_mwh if include_battery else 0,
        'battery_cost_per_kwh': battery_cost_per_kwh,
        'use_calculated_capex': use_calculated_capex,
        'pv_capex': pv_capex,
        'opex_percentage': opex_percentage,
        'discount_rate': discount_rate,
        'use_calculated_opex': use_calculated_opex,
        'pv_opex': pv_opex,
        'pci_ch4_kwh_per_kg': pci_ch4_kwh_per_kg,
        'lat': lat,
        'lon': lon,
        'loss': loss
    }


def get_current_parameters(selected_years, electrolyser_power, electrolyser_specific_consumption,
                          monthly_service_ratios, target_prices, pv_price, ppa_price, pv_params,
                          go_enabled=False, go_cost_per_mwh=0.0, electrolyzer_econ=None):
    """Get current parameters for change detection"""
    params = {
        'years': tuple(sorted(selected_years)) if selected_years else (),
        'power': electrolyser_power,
        'consumption': electrolyser_specific_consumption,
        'monthly_service_ratios': tuple(sorted(monthly_service_ratios.items())),
        'target_prices': tuple(target_prices),
        'pv_price': pv_price,
        'ppa_price': ppa_price,
        'go_enabled': go_enabled,
        'go_cost_per_mwh': go_cost_per_mwh,
        'pv_project_years': pv_params['pv_project_years'],
        'pv_surface_hectares': pv_params['pv_surface_hectares'],
        'power_density_mwp_per_ha': pv_params['power_density_mwp_per_ha'],
        'include_battery': pv_params['include_battery'],
        'storage_hours': pv_params['storage_hours'],
        'pv_cost_per_wp': pv_params['pv_cost_per_wp'],
        'battery_cost_per_kwh': pv_params['battery_cost_per_kwh'],
        'use_calculated_capex': pv_params['use_calculated_capex'],
        'opex_percentage': pv_params['opex_percentage'],
        'use_calculated_opex': pv_params['use_calculated_opex'],
        'pv_capex': pv_params['pv_capex'],
        'pv_opex': pv_params['pv_opex'],
        'pci_ch4_kwh_per_kg': pv_params['pci_ch4_kwh_per_kg'],
        'lat': pv_params['lat'],
        'lon': pv_params['lon'],
        'loss': pv_params['loss']
    }
    
    # Add electrolyzer economics if provided
    if electrolyzer_econ:
        params.update({
            'capex_transformer': electrolyzer_econ['capex_components']['transformer'],
            'capex_electrolyzer': electrolyzer_econ['capex_components']['electrolyzer'],
            'capex_compressor': electrolyzer_econ['capex_components']['compressor'],
            'capex_h2_storage': electrolyzer_econ['capex_components']['h2_storage'],
            'capex_piping': electrolyzer_econ['capex_components']['piping'],
            'others_capex': electrolyzer_econ['others_capex'],
            'maintenance_ratio_transformer': electrolyzer_econ['maintenance_ratios']['transformer'],
            'maintenance_ratio_electrolyzer': electrolyzer_econ['maintenance_ratios']['electrolyzer'],
            'maintenance_ratio_compressor': electrolyzer_econ['maintenance_ratios']['compressor'],
            'maintenance_ratio_h2_storage': electrolyzer_econ['maintenance_ratios']['h2_storage'],
            'maintenance_ratio_piping': electrolyzer_econ['maintenance_ratios']['piping'],
            'others_opex_annual': electrolyzer_econ['others_opex_annual'],
            'others_maintenance_annual': electrolyzer_econ['others_maintenance_annual'],
            'electrolyzer_capex_total': electrolyzer_econ['electrolyzer_capex_total'],
            'electrolyzer_capex_annual': electrolyzer_econ['electrolyzer_capex_annual'],
            'electrolyzer_lifetime': electrolyzer_econ['electrolyzer_lifetime'],
            'electrolyzer_discount_rate': electrolyzer_econ['electrolyzer_discount_rate'],
            'electrolyzer_maintenance_annual': electrolyzer_econ['electrolyzer_maintenance_annual'],
            'water_price_per_m3': electrolyzer_econ['water_price_per_m3'],
            'water_consumption_annual_m3': electrolyzer_econ['water_consumption_annual_m3'],
            'water_cost_annual': electrolyzer_econ['water_cost_annual'],
            'other_costs_annual': electrolyzer_econ['other_costs_annual'],
            'stack_replacement_cost': electrolyzer_econ['stack_replacement_cost'],
            'stack_replacement_years': electrolyzer_econ['stack_replacement_years']
        })
    
    return params
