"""
Sidebar configuration and parameter inputs for the MetaSTAAQ Dashboard
"""

import streamlit as st
import pandas as pd
import pandas as pd
from config import DEFAULT_PARAMS, PARAM_RANGES, MONTHS, STRATEGY_TYPES, ELECTROLYZER_REFERENCES, METHANATION_PRESETS


def setup_sidebar_header():
    """Set up the sidebar header"""
    st.sidebar.markdown("### 🔧 Simulation Parameters")


def load_data_file(file_path=None, use_supabase=True):
    """
    Load spot price data from Supabase database
    
    Args:
        file_path: Deprecated - no longer used (data is loaded from Supabase only)
        use_supabase: Must be True (Supabase is the only data source)
        
    Returns:
        DataFrame with spot price data
        
    Raises:
        ConnectionError: If Supabase is not configured or unavailable
    """
    try:
        from supabase_service import load_spot_data_from_supabase, get_supabase_service
        
        service = get_supabase_service()
        
        if not service.is_connected:
            st.error("❌ **Supabase not connected!**\n\nPlease check your `.env` file has valid credentials:\n- `SUPABASE_URL`\n- `SUPABASE_ANON_KEY`")
            st.stop()
        
        df = load_spot_data_from_supabase()
        
        if df.empty:
            st.error("❌ **No data in Supabase!**\n\nRun the import script to load data:\n```\npython scripts/import_csv_to_supabase.py\n```")
            st.stop()
        
        st.sidebar.success("✅ Data loaded from Supabase")
        return df
        
    except ImportError as e:
        st.error(f"❌ **Supabase module not installed!**\n\nRun: `pip install supabase python-dotenv`\n\nError: {str(e)}")
        st.stop()
    except Exception as e:
        st.error(f"❌ **Supabase error:** {str(e)}")
        st.stop()


def create_year_selection(data_content):
    """Create an improved year selection widget with period summary"""
    st.sidebar.markdown("#### 📅 Time Horizon")
    
    if 'Annee' not in data_content.columns:
        st.sidebar.error("❌ Column 'Annee' not found in data.")
        return [], DEFAULT_PARAMS["electrolyser_lifetime"], DEFAULT_PARAMS["discount_rate"]
        
    # Sort years descending (most recent first) for better UX
    available_years = sorted(data_content['Annee'].unique(), reverse=True)
    
    # User's preferred default
    default_years = [2025] if 2025 in available_years else [available_years[0]]
    
    selected_years = st.sidebar.multiselect(
        "Select fiscal years for analysis",
        options=available_years,
        default=default_years,
        help="Data from selected years will be aggregated and averaged for the simulation."
    )
    
    if not selected_years:
        st.sidebar.warning("⚠️ Select at least one year to run simulation.")
    else:
        # Provide a quick summary of the selected dataset period
        if len(selected_years) > 1:
            y_min, y_max = min(selected_years), max(selected_years)
            st.sidebar.caption(f"📊 **Aggregated Period**: {y_min} → {y_max} ({len(selected_years)} years)")
        else:
            st.sidebar.caption(f"🎯 **Single Year Analysis**: {selected_years[0]}")
            
    st.sidebar.markdown("---")
    st.sidebar.markdown("#### 🏗️ Project General Parameters")
    
    project_lifetime = st.sidebar.slider(
        "Project Lifetime (years)",
        min_value=PARAM_RANGES["electrolyser_lifetime"]["min"],
        max_value=PARAM_RANGES["electrolyser_lifetime"]["max"],
        value=DEFAULT_PARAMS["electrolyser_lifetime"],
        step=PARAM_RANGES["electrolyser_lifetime"]["step"],
        help="Expected lifetime of the entire project"
    )
    
    discount_rate = st.sidebar.slider(
        "Discount Rate (%)",
        min_value=PARAM_RANGES["discount_rate"]["min"],
        max_value=PARAM_RANGES["discount_rate"]["max"],
        value=DEFAULT_PARAMS["discount_rate"],
        step=PARAM_RANGES["discount_rate"]["step"],
        help="Discount rate for LCOE/LCOH/LCOCH4 calculation"
    )
        
    return selected_years, project_lifetime, discount_rate


def create_electrolyzer_parameters(project_lifetime, discount_rate):
    """Create electrolyzer parameter inputs including economics"""
    with st.sidebar.expander("⚡ Electrolyser", expanded=False):
        st.markdown("**Technical Parameters**")
        
        # Manufacturer Reference Selection
        use_reference = st.checkbox("Use Manufacturer Reference?", value=False, help="Select standard electrolyzer models")
        
        if use_reference:
            ref_power_options = list(ELECTROLYZER_REFERENCES.keys())
            selected_ref_power = st.selectbox("Select Model Power (MW)", options=ref_power_options, index=2) # Default 5MW
            
            ref_data = ELECTROLYZER_REFERENCES[selected_ref_power]
            electrolyser_power = selected_ref_power
            h2_flowrate = ref_data["h2_flowrate"]
            
            st.info(f"**Model Specs:**\n- Power: {electrolyser_power} MW\n- Flow Rate: {h2_flowrate} Nm³/h")
        else:
            electrolyser_power = st.slider(
                "Electrolyzer Power (MW)",
                min_value=PARAM_RANGES["electrolyser_power"]["min"],
                max_value=PARAM_RANGES["electrolyser_power"]["max"],
                value=DEFAULT_PARAMS["electrolyser_power"],
                step=PARAM_RANGES["electrolyser_power"]["step"],
                help="Power capacity of the electrolyzer in MW"
            )

            # H₂ Flow Rate is now an INPUT parameter
            h2_flowrate = st.slider(
                "H₂ Flow Rate (Nm³/h)",
                min_value=PARAM_RANGES["h2_flowrate"]["min"],
                max_value=PARAM_RANGES["h2_flowrate"]["max"],
                value=DEFAULT_PARAMS["h2_flowrate"],
                step=PARAM_RANGES["h2_flowrate"]["step"],
                help="Hydrogen flow rate in normal cubic meters per hour"
            )
        
        # Calculate Specific Consumption as OUTPUT
        if h2_flowrate > 0:
            electrolyser_specific_consumption = (electrolyser_power * 1000) / h2_flowrate
        else:
            electrolyser_specific_consumption = DEFAULT_PARAMS["electrolyser_specific_consumption"]
        
        # Display the calculated specific consumption
        st.metric(
            "Specific Consumption (calculated)",
            f"{electrolyser_specific_consumption:.2f} kWh/Nm³ H₂",
            help="Calculated from Power and H₂ Flow Rate: (Power × 1000) / H₂ Flow Rate"
        )
    
        st.markdown("---")
        st.markdown("### Economic Parameters (LCOH)")
        
        # Project parameters are now coming from create_year_selection
        electrolyzer_lifetime = project_lifetime
        electrolyzer_discount_rate = discount_rate
        
        st.caption(f"⏱️ Project Lifetime: {electrolyzer_lifetime} years (defined above)")
        st.caption(f"📉 Discount Rate: {electrolyzer_discount_rate}% (defined above)")
        
        # ============================================
        # CAPEX SECTION
        # ============================================
        st.markdown("---")
        st.markdown("#### CapEx (Capital Expenditure)")
        
        with st.expander("CapEx Parameters", expanded=False):
            capex_transformer = st.number_input(
                "Poste de transformation (€)",
                min_value=PARAM_RANGES["electrolyser_capex_transformer"]["min"],
                max_value=PARAM_RANGES["electrolyser_capex_transformer"]["max"],
                value=DEFAULT_PARAMS["electrolyser_capex_transformer"],
                step=PARAM_RANGES["electrolyser_capex_transformer"]["step"],
                help="Transformer station cost"
            )
            
            capex_electrolyzer = st.number_input(
                "Electrolyseur (€)",
                min_value=PARAM_RANGES["electrolyser_capex_electrolyzer"]["min"],
                max_value=PARAM_RANGES["electrolyser_capex_electrolyzer"]["max"],
                value=DEFAULT_PARAMS["electrolyser_capex_electrolyzer"],
                step=PARAM_RANGES["electrolyser_capex_electrolyzer"]["step"],
                help="Electrolyzer unit cost"
            )
            
            capex_compressor = st.number_input(
                "Compresseur (€)",
                min_value=PARAM_RANGES["electrolyser_capex_compressor"]["min"],
                max_value=PARAM_RANGES["electrolyser_capex_compressor"]["max"],
                value=DEFAULT_PARAMS["electrolyser_capex_compressor"],
                step=PARAM_RANGES["electrolyser_capex_compressor"]["step"],
                help="Compressor cost"
            )
            
            capex_h2_storage = st.number_input(
                "Stockage H2 (€)",
                min_value=PARAM_RANGES["electrolyser_capex_h2_storage"]["min"],
                max_value=PARAM_RANGES["electrolyser_capex_h2_storage"]["max"],
                value=DEFAULT_PARAMS["electrolyser_capex_h2_storage"],
                step=PARAM_RANGES["electrolyser_capex_h2_storage"]["step"],
                help="H2 storage cost"
            )
            
            capex_piping = st.number_input(
                "Piping, ... (€)",
                min_value=PARAM_RANGES["electrolyser_capex_piping"]["min"],
                max_value=PARAM_RANGES["electrolyser_capex_piping"]["max"],
                value=DEFAULT_PARAMS["electrolyser_capex_piping"],
                step=PARAM_RANGES["electrolyser_capex_piping"]["step"],
                help="Piping and other infrastructure costs"
            )
            
            # Stack replacement
            stack_replacement_cost = st.number_input(
                "Stack Replacement Cost (€)",
                min_value=PARAM_RANGES["electrolyser_stack_replacement_cost"]["min"],
                max_value=PARAM_RANGES["electrolyser_stack_replacement_cost"]["max"],
                value=DEFAULT_PARAMS["electrolyser_stack_replacement_cost"],
                step=PARAM_RANGES["electrolyser_stack_replacement_cost"]["step"],
                help="Total cost for stack replacement"
            )
            
            stack_replacement_years = st.slider(
                "Stack Replacement Interval (years)",
                min_value=PARAM_RANGES["electrolyser_stack_replacement_years"]["min"],
                max_value=PARAM_RANGES["electrolyser_stack_replacement_years"]["max"],
                value=DEFAULT_PARAMS["electrolyser_stack_replacement_years"],
                step=PARAM_RANGES["electrolyser_stack_replacement_years"]["step"],
                help="Years between stack replacements"
            )
            
            # Others CapEx
            others_capex = st.number_input(
                "Others CapEx (€)",
                min_value=PARAM_RANGES["electrolyser_others_capex"]["min"],
                max_value=PARAM_RANGES["electrolyser_others_capex"]["max"],
                value=DEFAULT_PARAMS["electrolyser_others_capex"],
                step=PARAM_RANGES["electrolyser_others_capex"]["step"],
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
        st.metric("CapEx Annualized", f"{electrolyzer_capex_annual:,.0f} €/year")
        st.metric("Total CapEx", f"{electrolyzer_capex_total:,.0f} €")
        
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
                min_value=PARAM_RANGES["electrolyser_water_price_per_m3"]["min"],
                max_value=PARAM_RANGES["electrolyser_water_price_per_m3"]["max"],
                value=DEFAULT_PARAMS["electrolyser_water_price_per_m3"],
                step=PARAM_RANGES["electrolyser_water_price_per_m3"]["step"],
                help="Unit price of water per cubic meter"
            )
            
            water_consumption_annual_m3 = st.number_input(
                "Water Consumption (m³/year)",
                min_value=PARAM_RANGES["electrolyser_water_consumption_annual_m3"]["min"],
                max_value=PARAM_RANGES["electrolyser_water_consumption_annual_m3"]["max"],
                value=DEFAULT_PARAMS["electrolyser_water_consumption_annual_m3"],
                step=PARAM_RANGES["electrolyser_water_consumption_annual_m3"]["step"],
                help="Annual water consumption in cubic meters"
            )
            
            st.markdown("**Others OpEx**")
            others_opex_annual = st.number_input(
                "Others OpEx (€/year)",
                min_value=PARAM_RANGES["electrolyser_others_opex_annual"]["min"],
                max_value=PARAM_RANGES["electrolyser_others_opex_annual"]["max"],
                value=DEFAULT_PARAMS["electrolyser_others_opex_annual"],
                step=PARAM_RANGES["electrolyser_others_opex_annual"]["step"],
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
                    min_value=PARAM_RANGES["electrolyser_maintenance_ratio_transformer"]["min"],
                    max_value=PARAM_RANGES["electrolyser_maintenance_ratio_transformer"]["max"],
                    value=DEFAULT_PARAMS["electrolyser_maintenance_ratio_transformer"],
                    step=PARAM_RANGES["electrolyser_maintenance_ratio_transformer"]["step"],
                    help="Annual maintenance as % of transformer CapEx"
                )
                
                maintenance_ratio_electrolyzer = st.number_input(
                    "Electrolyseur (%)",
                    min_value=PARAM_RANGES["electrolyser_maintenance_ratio_electrolyzer"]["min"],
                    max_value=PARAM_RANGES["electrolyser_maintenance_ratio_electrolyzer"]["max"],
                    value=DEFAULT_PARAMS["electrolyser_maintenance_ratio_electrolyzer"],
                    step=PARAM_RANGES["electrolyser_maintenance_ratio_electrolyzer"]["step"],
                    help="Annual maintenance as % of electrolyzer CapEx"
                )
                
                maintenance_ratio_compressor = st.number_input(
                    "Compresseur (%)",
                    min_value=PARAM_RANGES["electrolyser_maintenance_ratio_compressor"]["min"],
                    max_value=PARAM_RANGES["electrolyser_maintenance_ratio_compressor"]["max"],
                    value=DEFAULT_PARAMS["electrolyser_maintenance_ratio_compressor"],
                    step=PARAM_RANGES["electrolyser_maintenance_ratio_compressor"]["step"],
                    help="Annual maintenance as % of compressor CapEx"
                )
            
            with col2:
                maintenance_ratio_h2_storage = st.number_input(
                    "Stockage H2 (%)",
                    min_value=PARAM_RANGES["electrolyser_maintenance_ratio_h2_storage"]["min"],
                    max_value=PARAM_RANGES["electrolyser_maintenance_ratio_h2_storage"]["max"],
                    value=DEFAULT_PARAMS["electrolyser_maintenance_ratio_h2_storage"],
                    step=PARAM_RANGES["electrolyser_maintenance_ratio_h2_storage"]["step"],
                    help="Annual maintenance as % of H2 storage CapEx"
                )
                
                maintenance_ratio_piping = st.number_input(
                    "Piping, ... (%)",
                    min_value=PARAM_RANGES["electrolyser_maintenance_ratio_piping"]["min"],
                    max_value=PARAM_RANGES["electrolyser_maintenance_ratio_piping"]["max"],
                    value=DEFAULT_PARAMS["electrolyser_maintenance_ratio_piping"],
                    step=PARAM_RANGES["electrolyser_maintenance_ratio_piping"]["step"],
                    help="Annual maintenance as % of piping CapEx"
                )
            
            st.markdown("**Others Maintenance**")
            others_maintenance_annual = st.number_input(
                "Others Maintenance (€/year)",
                min_value=PARAM_RANGES["electrolyser_others_maintenance_annual"]["min"],
                max_value=PARAM_RANGES["electrolyser_others_maintenance_annual"]["max"],
                value=DEFAULT_PARAMS["electrolyser_others_maintenance_annual"],
                step=PARAM_RANGES["electrolyser_others_maintenance_annual"]["step"],
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
    
    return electrolyser_power, h2_flowrate, electrolyser_specific_consumption, electrolyzer_econ


def create_methanation_parameters(electrolyser_power=None, electrolyser_specific_consumption=None, project_lifetime=None, discount_rate=None):
    """Create methanation parameter inputs including economics
    
    Args:
        electrolyser_power: Electrolyzer power in MW (optional, for calculation display)
        electrolyser_specific_consumption: Specific consumption in kWh/Nm³ H₂ (optional, for calculation display)
        project_lifetime: Unified project lifetime
        discount_rate: Unified discount rate
    """
    with st.sidebar.expander("🔥 Methanation", expanded=False):
        st.markdown("**Methanation Technology**")
        meth_tech = st.radio(
            "Select Technology",
            options=list(METHANATION_PRESETS.keys()),
            index=0,
            horizontal=True,
            help="Choose between Biological and Catalytic methanation to load preset parameters."
        )
        
        # Load preset for selected technology
        preset = METHANATION_PRESETS[meth_tech]
        
        st.markdown("**Economic Parameters (LCOCH4)**")
        
        # Project parameters are now coming from create_year_selection
        methanation_lifetime = project_lifetime if project_lifetime is not None else DEFAULT_PARAMS["methanation_lifetime"]
        methanation_discount_rate = discount_rate if discount_rate is not None else DEFAULT_PARAMS["methanation_discount_rate"]
        
        st.caption(f"⏱️ Project Lifetime: {methanation_lifetime} years (defined above)")
        st.caption(f"📉 Discount Rate: {methanation_discount_rate}% (defined above)")
        
        # Technical Parameters
        st.markdown("---")
        st.markdown("**Technical Parameters**")
        
        # CH₄ Flow Rate is now an INPUT parameter
        ch4_flowrate = st.slider(
            "CH₄ Flow Rate (Nm³/h)",
            min_value=PARAM_RANGES["ch4_flowrate"]["min"],
            max_value=PARAM_RANGES["ch4_flowrate"]["max"],
            value=DEFAULT_PARAMS["ch4_flowrate"],
            step=PARAM_RANGES["ch4_flowrate"]["step"],
            help="Methane flow rate in normal cubic meters per hour",
            key="methanation_ch4_flowrate"
        )
        
        # Calculate Specific Consumption as OUTPUT (simple approach for now)
        cons_spec_ch4 = preset["cons_spec_ch4"]
        
        # Display the calculated specific consumption
        st.metric(
            "Cons Spec CH₄ (from preset)",
            f"{cons_spec_ch4:.2f} kWhₑ/Nm³ CH₄",
            help=f"Specific consumption for {meth_tech} methanation."
        )
        
        st.markdown("---")
        # cons_spec_ch4 is now calculated above (removed slider)
        
        # ============================================
        # CAPEX SECTION
        # ============================================
        st.markdown("---")
        st.markdown("#### CapEx (Capital Expenditure)")
        
        with st.expander("CapEx Parameters", expanded=False):
            capex_methanation_unit = st.number_input(
                "Unité de méthanation (€)",
                min_value=PARAM_RANGES["methanation_capex_methanation_unit"]["min"],
                max_value=PARAM_RANGES["methanation_capex_methanation_unit"]["max"],
                value=preset["capex_methanation_unit"],
                step=PARAM_RANGES["methanation_capex_methanation_unit"]["step"],
                help="Methanation unit cost",
                key=f"methanation_capex_methanation_unit_{meth_tech}"
            )
            
            capex_purification_unit = st.number_input(
                "Unité de purification & analyse (€)",
                min_value=PARAM_RANGES["methanation_capex_purification_unit"]["min"],
                max_value=PARAM_RANGES["methanation_capex_purification_unit"]["max"],
                value=preset["capex_purification_unit"],
                step=PARAM_RANGES["methanation_capex_purification_unit"]["step"],
                help="Purification and analysis unit cost",
                key=f"methanation_capex_purification_unit_{meth_tech}"
            )
            
            capex_compressor = st.number_input(
                "Compresseur (€)",
                min_value=PARAM_RANGES["methanation_capex_compressor"]["min"],
                max_value=PARAM_RANGES["methanation_capex_compressor"]["max"],
                value=preset["capex_compressor"],
                step=PARAM_RANGES["methanation_capex_compressor"]["step"],
                help="Compressor cost",
                key=f"methanation_capex_compressor_{meth_tech}"
            )
            
            capex_ch4_storage = st.number_input(
                "Stockage CH4 (€)",
                min_value=PARAM_RANGES["methanation_capex_ch4_storage"]["min"],
                max_value=PARAM_RANGES["methanation_capex_ch4_storage"]["max"],
                value=preset["capex_ch4_storage"],
                step=PARAM_RANGES["methanation_capex_ch4_storage"]["step"],
                help="CH4 storage cost",
                key=f"methanation_capex_ch4_storage_{meth_tech}"
            )
            
            capex_grid_injection = st.number_input(
                "Injection réseau (€)",
                min_value=PARAM_RANGES["methanation_capex_grid_injection"]["min"],
                max_value=PARAM_RANGES["methanation_capex_grid_injection"]["max"],
                value=preset["capex_grid_injection"],
                step=PARAM_RANGES["methanation_capex_grid_injection"]["step"],
                help="Grid injection cost",
                key=f"methanation_capex_grid_injection_{meth_tech}"
            )
            
            # Others CapEx
            others_capex = st.number_input(
                "Others CapEx (€)",
                min_value=PARAM_RANGES["methanation_others_capex"]["min"],
                max_value=PARAM_RANGES["methanation_others_capex"]["max"],
                value=preset["others_capex"],
                step=PARAM_RANGES["methanation_others_capex"]["step"],
                help="Other capital expenditures",
                key=f"methanation_others_capex_{meth_tech}"
            )
        
        # Calculate total CapEx
        methanation_capex_total = (
            capex_methanation_unit + 
            capex_purification_unit + 
            capex_compressor + 
            capex_ch4_storage + 
            capex_grid_injection +
            others_capex
        )
        
        # Calculate and display annualized CapEx
        from calculate_lcoh import calculate_crf
        crf = calculate_crf(methanation_discount_rate, methanation_lifetime)
        methanation_capex_annual = methanation_capex_total * crf
        
        # Display totals
        st.metric("CapEx Annualized", f"{methanation_capex_annual:,.0f} €/year")
        st.metric("Total CapEx", f"{methanation_capex_total:,.0f} €")
        
        # ============================================
        # OPEX SECTION - Electricity Consumption
        # ============================================
        st.markdown("---")
        st.markdown("#### OpEx (Operational Expenditure)")
        
        with st.expander("OpEx Parameters - Electricity Consumption", expanded=False):
            st.markdown("**Electricity Consumption (MWhe/year)**")
            
            # Calculate methanation unit consumption if electrolyzer parameters are provided
            if electrolyser_power is not None and electrolyser_specific_consumption is not None:
                # Calculate CH4 flowrate
                h2_flowrate = (electrolyser_power * 1000) / electrolyser_specific_consumption
                ch4_flowrate_calc = h2_flowrate / 4  # Stoichiometry H2:CH4 = 4:1
                
                # Calculate instantaneous power
                puissance_instantanee_kw = ch4_flowrate_calc * cons_spec_ch4
                
                # Estimate with a default service ratio of 0.98 for display (will be recalculated with actual ratio later)
                estimated_service_ratio = 0.98
                elec_methanation_unit_estimated = (puissance_instantanee_kw * estimated_service_ratio * 8760) / 1000
                
                # Display calculated value with tooltip
                st.metric(
                    "🔄 Unité de méthanation (auto-calculated)",
                    f"{elec_methanation_unit_estimated:.1f} MWhe/year",
                    help=f"**Calculation Details:**\n\n"
                         f"**Step 1: CH₄ Flow Rate**\n"
                         f"• H₂ flow rate = {electrolyser_power} MW × 1000 / {electrolyser_specific_consumption} kWh/Nm³ = {h2_flowrate:.0f} Nm³/h\n"
                         f"• CH₄ flow rate = {h2_flowrate:.0f} / 4 (stoichiometry) = {ch4_flowrate_calc:.0f} Nm³/h\n\n"
                         f"**Step 2: Instantaneous Power**\n"
                         f"• Puissance = {ch4_flowrate_calc:.0f} Nm³/h × {cons_spec_ch4} kWh/Nm³ = {puissance_instantanee_kw:.1f} kW\n\n"
                         f"**Step 3: Annual Consumption**\n"
                         f"• Consumption = {puissance_instantanee_kw:.1f} kW × {estimated_service_ratio:.0%} × 8760 h / 1000 = {elec_methanation_unit_estimated:.1f} MWhe/year\n\n"
                         f"_Estimated with {estimated_service_ratio:.0%} service ratio. Final value calculated with actual service ratio in results._"
                )
                
                elec_methanation_unit = elec_methanation_unit_estimated  # Will be overridden with actual calculation
            else:
                st.caption("🔄 **Unité de méthanation**: Calculated automatically. See 'Calculated Parameters' section for details.")
                elec_methanation_unit = DEFAULT_PARAMS["methanation_electricity_methanation_unit"]  # Placeholder
            
            elec_purification_unit = st.number_input(
                "Unité de purification & analyse (MWhe/year)",
                min_value=PARAM_RANGES["methanation_electricity_purification_unit"]["min"],
                max_value=PARAM_RANGES["methanation_electricity_purification_unit"]["max"],
                value=DEFAULT_PARAMS["methanation_electricity_purification_unit"],
                step=PARAM_RANGES["methanation_electricity_purification_unit"]["step"],
                help="Annual electricity consumption for purification unit",
                key="methanation_electricity_purification_unit"
            )
            
            elec_compressor = st.number_input(
                "Compresseur (MWhe/year)",
                min_value=PARAM_RANGES["methanation_electricity_compressor"]["min"],
                max_value=PARAM_RANGES["methanation_electricity_compressor"]["max"],
                value=DEFAULT_PARAMS["methanation_electricity_compressor"],
                step=PARAM_RANGES["methanation_electricity_compressor"]["step"],
                help="Annual electricity consumption for compressor",
                key="methanation_electricity_compressor"
            )
            
            elec_ch4_storage = st.number_input(
                "Stockage CH4 (MWhe/year)",
                min_value=PARAM_RANGES["methanation_electricity_ch4_storage"]["min"],
                max_value=PARAM_RANGES["methanation_electricity_ch4_storage"]["max"],
                value=DEFAULT_PARAMS["methanation_electricity_ch4_storage"],
                step=PARAM_RANGES["methanation_electricity_ch4_storage"]["step"],
                help="Annual electricity consumption for CH4 storage",
                key="methanation_electricity_ch4_storage"
            )
            
            elec_grid_injection = st.number_input(
                "Injection réseau (MWhe/year)",
                min_value=PARAM_RANGES["methanation_electricity_grid_injection"]["min"],
                max_value=PARAM_RANGES["methanation_electricity_grid_injection"]["max"],
                value=DEFAULT_PARAMS["methanation_electricity_grid_injection"],
                step=PARAM_RANGES["methanation_electricity_grid_injection"]["step"],
                help="Annual electricity consumption for grid injection",
                key="methanation_electricity_grid_injection"
            )
            
            st.markdown("**Others OpEx**")
            others_opex_annual = st.number_input(
                "Others OpEx (€/year)",
                min_value=PARAM_RANGES["methanation_others_opex_annual"]["min"],
                max_value=PARAM_RANGES["methanation_others_opex_annual"]["max"],
                value=DEFAULT_PARAMS["methanation_others_opex_annual"],
                step=PARAM_RANGES["methanation_others_opex_annual"]["step"],
                help="Other operational expenditures",
                key="methanation_others_opex_annual"
            )
            
            st.caption("Electricity cost will be calculated from energy consumption and prices (PV, Spot, PPA)")
        
        # Calculate total electricity consumption
        total_electricity_mwh = (
            elec_methanation_unit + 
            elec_purification_unit + 
            elec_compressor + 
            elec_ch4_storage + 
            elec_grid_injection
        )
        
        # Display OpEx breakdown info
        st.info(f"💡 **Total OpEx Calculation**:\n\n"
                f"• Electricity: {total_electricity_mwh:,.0f} MWhe/year × Electricity Price (€/MWh)\n\n"
                f"• Others OpEx: {others_opex_annual:,.0f} €/year\n\n"
                f"• **Total OpEx** = (Electricity Cost) + (Others OpEx)\n\n"
                f"_Note: Electricity price will be calculated from PV, Spot, and PPA mix_")
        
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
                maintenance_ratio_methanation_unit = st.number_input(
                    "Unité de méthanation (%)",
                    min_value=PARAM_RANGES["methanation_maintenance_ratio_methanation_unit"]["min"],
                    max_value=PARAM_RANGES["methanation_maintenance_ratio_methanation_unit"]["max"],
                    value=preset["maintenance_ratios"]["methanation_unit"],
                    step=PARAM_RANGES["methanation_maintenance_ratio_methanation_unit"]["step"],
                    help="Annual maintenance as % of methanation unit CapEx",
                    key=f"methanation_maintenance_ratio_methanation_unit_{meth_tech}"
                )
                
                maintenance_ratio_purification_unit = st.number_input(
                    "Unité de purification & analyse (%)",
                    min_value=PARAM_RANGES["methanation_maintenance_ratio_purification_unit"]["min"],
                    max_value=PARAM_RANGES["methanation_maintenance_ratio_purification_unit"]["max"],
                    value=preset["maintenance_ratios"]["purification_unit"],
                    step=PARAM_RANGES["methanation_maintenance_ratio_purification_unit"]["step"],
                    help="Annual maintenance as % of purification unit CapEx",
                    key=f"methanation_maintenance_ratio_purification_unit_{meth_tech}"
                )
                
                maintenance_ratio_compressor = st.number_input(
                    "Compresseur (%)",
                    min_value=PARAM_RANGES["methanation_maintenance_ratio_compressor"]["min"],
                    max_value=PARAM_RANGES["methanation_maintenance_ratio_compressor"]["max"],
                    value=preset["maintenance_ratios"]["compressor"],
                    step=PARAM_RANGES["methanation_maintenance_ratio_compressor"]["step"],
                    help="Annual maintenance as % of compressor CapEx",
                    key=f"methanation_maintenance_ratio_compressor_{meth_tech}"
                )
            
            with col2:
                maintenance_ratio_ch4_storage = st.number_input(
                    "Stockage CH4 (%)",
                    min_value=PARAM_RANGES["methanation_maintenance_ratio_ch4_storage"]["min"],
                    max_value=PARAM_RANGES["methanation_maintenance_ratio_ch4_storage"]["max"],
                    value=preset["maintenance_ratios"]["ch4_storage"],
                    step=PARAM_RANGES["methanation_maintenance_ratio_ch4_storage"]["step"],
                    help="Annual maintenance as % of CH4 storage CapEx",
                    key=f"methanation_maintenance_ratio_ch4_storage_{meth_tech}"
                )
                
                maintenance_ratio_grid_injection = st.number_input(
                    "Injection réseau (%)",
                    min_value=PARAM_RANGES["methanation_maintenance_ratio_grid_injection"]["min"],
                    max_value=PARAM_RANGES["methanation_maintenance_ratio_grid_injection"]["max"],
                    value=preset["maintenance_ratios"]["grid_injection"],
                    step=PARAM_RANGES["methanation_maintenance_ratio_grid_injection"]["step"],
                    help="Annual maintenance as % of grid injection CapEx",
                    key=f"methanation_maintenance_ratio_grid_injection_{meth_tech}"
                )
            
            st.markdown("**Others Maintenance**")
            others_maintenance_annual = st.number_input(
                "Others Maintenance (€/year)",
                min_value=PARAM_RANGES["methanation_others_maintenance_annual"]["min"],
                max_value=PARAM_RANGES["methanation_others_maintenance_annual"]["max"],
                value=DEFAULT_PARAMS["methanation_others_maintenance_annual"],
                step=PARAM_RANGES["methanation_others_maintenance_annual"]["step"],
                help="Other maintenance costs",
                key="methanation_others_maintenance_annual"
            )
        
        # Calculate maintenance costs
        maintenance_methanation_unit = capex_methanation_unit * (maintenance_ratio_methanation_unit / 100)
        maintenance_purification_unit = capex_purification_unit * (maintenance_ratio_purification_unit / 100)
        maintenance_compressor = capex_compressor * (maintenance_ratio_compressor / 100)
        maintenance_ch4_storage = capex_ch4_storage * (maintenance_ratio_ch4_storage / 100)
        maintenance_grid_injection = capex_grid_injection * (maintenance_ratio_grid_injection / 100)
        
        # Total maintenance
        methanation_maintenance_annual = (
            maintenance_methanation_unit +
            maintenance_purification_unit +
            maintenance_compressor +
            maintenance_ch4_storage +
            maintenance_grid_injection +
            others_maintenance_annual
        )
        
        # Display total
        st.metric("Total Maintenance", f"{methanation_maintenance_annual:,.0f} €/year")
        
        # ============================================
        # CH4 PROPERTIES
        # ============================================
        st.markdown("---")
        st.markdown("#### CH₄ Properties")
        
        pci_ch4_kwh_per_kg = st.slider(
            "PCI CH₄ (kWh/kg)",
            min_value=PARAM_RANGES["pci_ch4_kwh_per_kg"]["min"],
            max_value=PARAM_RANGES["pci_ch4_kwh_per_kg"]["max"],
            value=DEFAULT_PARAMS["pci_ch4_kwh_per_kg"],
            step=PARAM_RANGES["pci_ch4_kwh_per_kg"]["step"],
            help="Lower heating value of methane",
            key="methanation_pci_ch4"
        )
    
    
    # Calculate other_costs_annual (Others CapEx annualized + Others Maintenance)
    # Note: Others OpEx is handled separately in OPEX
    other_costs_annual = others_capex * calculate_crf(methanation_discount_rate, methanation_lifetime) + others_maintenance_annual
    
    methanation_econ = {
        'capex_components': {
            'methanation_unit': capex_methanation_unit,
            'purification_unit': capex_purification_unit,
            'compressor': capex_compressor,
            'ch4_storage': capex_ch4_storage,
            'grid_injection': capex_grid_injection,
            'others': others_capex
        },
        'maintenance_ratios': {
            'methanation_unit': maintenance_ratio_methanation_unit,
            'purification_unit': maintenance_ratio_purification_unit,
            'compressor': maintenance_ratio_compressor,
            'ch4_storage': maintenance_ratio_ch4_storage,
            'grid_injection': maintenance_ratio_grid_injection
        },
        'maintenance_breakdown': {
            'methanation_unit': maintenance_methanation_unit,
            'purification_unit': maintenance_purification_unit,
            'compressor': maintenance_compressor,
            'ch4_storage': maintenance_ch4_storage,
            'grid_injection': maintenance_grid_injection,
            'others': others_maintenance_annual
        },
        'electricity_consumption': {
            'methanation_unit': elec_methanation_unit,
            'purification_unit': elec_purification_unit,
            'compressor': elec_compressor,
            'ch4_storage': elec_ch4_storage,
            'grid_injection': elec_grid_injection,
            'total': total_electricity_mwh
        },
        'methanation_capex_total': methanation_capex_total,
        'methanation_capex_annual': methanation_capex_annual,
        'methanation_lifetime': methanation_lifetime,
        'methanation_discount_rate': methanation_discount_rate,
        'methanation_maintenance_annual': methanation_maintenance_annual,
        'others_capex': others_capex,
        'others_opex_annual': others_opex_annual,
        'others_maintenance_annual': others_maintenance_annual,
        'other_costs_annual': other_costs_annual,
        'pci_ch4_kwh_per_kg': pci_ch4_kwh_per_kg,
        'cons_spec_ch4': cons_spec_ch4,  # Specific consumption kWh/Nm³ (calculated)
        'ch4_flowrate': ch4_flowrate  # CH4 flow rate Nm³/h (input parameter)
    }
    
    return ch4_flowrate, cons_spec_ch4, methanation_econ


def create_site_co2_parameters():
    """Create Site and CO2 Supply parameter inputs"""
    with st.sidebar.expander("🏭 Site & CO2 Supply", expanded=False):
        # ============================================
        # CAPEX SECTION
        # ============================================
        st.markdown("---")
        st.markdown("#### CapEx (Capital Expenditure)")
        
        with st.expander("CapEx Parameters", expanded=False):
            site_capex = st.number_input(
                "Site (€)",
                min_value=PARAM_RANGES["site_capex"]["min"],
                max_value=PARAM_RANGES["site_capex"]["max"],
                value=DEFAULT_PARAMS["site_capex"],
                step=PARAM_RANGES["site_capex"]["step"],
                help="Site preparation and infrastructure cost",
                key="site_capex_input"
            )
            
            appro_co2_capex = st.number_input(
                "CO2 Supply Infrastructure (€)",
                min_value=PARAM_RANGES["appro_co2_capex"]["min"],
                max_value=PARAM_RANGES["appro_co2_capex"]["max"],
                value=DEFAULT_PARAMS["appro_co2_capex"],
                step=PARAM_RANGES["appro_co2_capex"]["step"],
                help="CO2 supply infrastructure cost",
                key="appro_co2_capex_input"
            )
        
        # Calculate total CapEx
        total_site_co2_capex = site_capex + appro_co2_capex
        
        # Display total
        st.metric("Total CapEx", f"{total_site_co2_capex:,.0f} €")
        
        # ============================================
        # OPEX SECTION
        # ============================================
        st.markdown("---")
        st.markdown("#### OpEx (Operational Expenditure)")
        
        with st.expander("OpEx Parameters", expanded=False):
            site_opex = st.number_input(
                "Site OpEx (€/year)",
                min_value=PARAM_RANGES["site_opex"]["min"],
                max_value=PARAM_RANGES["site_opex"]["max"],
                value=DEFAULT_PARAMS["site_opex"],
                step=PARAM_RANGES["site_opex"]["step"],
                help="Annual operational costs for site",
                key="site_opex_input"
            )
            
            appro_co2_opex = st.number_input(
                "CO2 Supply OpEx (€/year)",
                min_value=PARAM_RANGES["appro_co2_opex"]["min"],
                max_value=PARAM_RANGES["appro_co2_opex"]["max"],
                value=DEFAULT_PARAMS["appro_co2_opex"],
                step=PARAM_RANGES["appro_co2_opex"]["step"],
                help="Annual CO2 supply and procurement costs",
                key="appro_co2_opex_input"
            )
        
        # Calculate total OpEx
        total_site_co2_opex = site_opex + appro_co2_opex
        
        # Display total
        st.metric("Total OpEx", f"{total_site_co2_opex:,.0f} €/year")
        
        # ============================================
        # MAINTENANCE SECTION
        # ============================================
        st.markdown("---")
        st.markdown("#### Maintenance Costs")
        
        with st.expander("Maintenance Parameters", expanded=False):
            site_maintenance = st.number_input(
                "Site Maintenance (€/year)",
                min_value=PARAM_RANGES["site_maintenance"]["min"],
                max_value=PARAM_RANGES["site_maintenance"]["max"],
                value=DEFAULT_PARAMS["site_maintenance"],
                step=PARAM_RANGES["site_maintenance"]["step"],
                help="Annual maintenance costs for site",
                key="site_maintenance_input"
            )
            
            appro_co2_maintenance = st.number_input(
                "CO2 Supply Maintenance (€/year)",
                min_value=PARAM_RANGES["appro_co2_maintenance"]["min"],
                max_value=PARAM_RANGES["appro_co2_maintenance"]["max"],
                value=DEFAULT_PARAMS["appro_co2_maintenance"],
                step=PARAM_RANGES["appro_co2_maintenance"]["step"],
                help="Annual maintenance costs for CO2 supply infrastructure",
                key="appro_co2_maintenance_input"
            )
        
        # Calculate total Maintenance
        total_site_co2_maintenance = site_maintenance + appro_co2_maintenance
        
        # Display total
        st.metric("Total Maintenance", f"{total_site_co2_maintenance:,.0f} €/year")
    
    site_co2_econ = {
        'site_capex': site_capex,
        'appro_co2_capex': appro_co2_capex,
        'total_capex': total_site_co2_capex,
        'site_opex': site_opex,
        'appro_co2_opex': appro_co2_opex,
        'total_opex': total_site_co2_opex,
        'site_maintenance': site_maintenance,
        'appro_co2_maintenance': appro_co2_maintenance,
        'total_maintenance': total_site_co2_maintenance
    }
    
    return site_co2_econ


def create_monthly_service_ratios(allow_edit=True, preset_ratios=None):
    """Create or display monthly service ratios in the sidebar.

    When allow_edit is False (Target Price strategy), the sliders are hidden and
    ratios are shown as read-only if available after simulation.
    """
    monthly_service_ratios = {}

    with st.sidebar.expander("📅 Service Ratios", expanded=False):
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
    with st.sidebar.expander("💰 Price", expanded=False):
        if strategy_type == "Service Ratio-Based":
            st.info("ℹ️ Service Ratio strategy cumulates spot hours while keeping average cost below PPA price.")
        elif strategy_type == "Target Price-Based":
            st.info("ℹ️ Target Price strategy cumulates spot hours while keeping cumulative average below target price.")
        elif strategy_type == "Optimize Global Annual Service Ratio":
            st.info("ℹ️ Optimizes monthly ratios to achieve a precise Global Annual Service Ratio.")
        elif strategy_type == "Target LCOCh4":
            st.info("ℹ️ Finds the optimal service ratio to achieve a specific Target LCOCh4.")
        
        # Target parameters depends on strategy
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
        elif strategy_type == "Optimize Global Annual Service Ratio":
            st.markdown("**Optimization Target:**")
            # Reuse a slider or create new one in session state
            if 'annual_service_ratio_target' not in st.session_state:
                st.session_state.annual_service_ratio_target = 0.90
            
            annual_target = st.slider(
                "Global Annual Service Ratio Target",
                min_value=0.1,
                max_value=1.0,
                value=st.session_state.annual_service_ratio_target,
                step=0.01,
                help="Target annual service ratio (e.g. 0.95 for 95%)"
            )
            st.session_state.annual_service_ratio_target = annual_target
            # Use dummy target price list to maintain interface compatibility
            target_prices = [0.0] 
        elif strategy_type == "Target LCOCh4":
            st.markdown("**Optimization Target:**")
            if 'target_lcoch4' not in st.session_state:
                st.session_state.target_lcoch4 = 100.0
                
            target_lcoch4 = st.slider(
                "Target LCOCh4 (€/MWh)",
                min_value=40.0,
                max_value=300.0,
                value=st.session_state.target_lcoch4,
                step=5.0,
                help="Target Levelized Cost of Methane"
            )
            st.session_state.target_lcoch4 = target_lcoch4
            target_prices = [0.0]
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




def create_pv_installation_parameters(project_lifetime=None, discount_rate=None):
    """Create PV installation parameter inputs"""
    with st.sidebar.expander("☀️ PV Installation", expanded=False):
        # Project parameters are now coming from create_year_selection
        pv_project_years = project_lifetime if project_lifetime is not None else DEFAULT_PARAMS["pv_project_years"]
        
        st.caption(f"⏱️ Project Lifetime: {pv_project_years} years (defined above)")

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

        use_calculated_capex = st.checkbox(
            "Use Calculated CAPEX",
            value=True,
            help="Use calculated CAPEX based on power and costs"
        )

        pv_capex = 0
        if use_calculated_capex:
            # estimated_power_kwp is in kWp; convert to Wp for €/Wp input
            pv_capex_calculated = (estimated_power_kwp * 1000) * pv_cost_per_wp
            
            st.write(f"**Calculated CAPEX**:")
            st.write(f"• PV: {pv_capex_calculated:,.0f} €")
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

        pv_discount_rate = discount_rate if discount_rate is not None else DEFAULT_PARAMS["discount_rate"]
        st.caption(f"📉 Discount Rate: {pv_discount_rate}% (defined above)")

        use_calculated_opex = st.checkbox(
            "Use Calculated OPEX",
            value=True,
            help="Use calculated OPEX based on CAPEX percentage"
        )

        pv_opex = 0
        if use_calculated_opex:
            pv_opex_calculated = pv_capex_calculated * opex_percentage / 100
            pv_opex = pv_opex_calculated
            
            st.write(f"**Calculated OPEX ({opex_percentage}% of CAPEX)**:")
            st.write(f"• PV: {pv_opex_calculated:,.0f} €/year")
        else:
            pv_opex = st.number_input(
                "PV OPEX (€/year)",
                min_value=0,
                value=0,
                step=1000,
                help="Manual PV OPEX input"
            )
        
        # Maintenance section (PV only)
        st.markdown("---")
        st.markdown("#### 🔧 Maintenance")
        
        pv_maintenance_percentage = st.slider(
            "PV Maintenance (% of PV CAPEX/year)",
            min_value=0.0,
            max_value=5.0,
            value=1.0,
            step=0.1,
            help="Annual PV maintenance cost as percentage of PV CAPEX"
        )
        
        if use_calculated_capex:
            pv_maintenance = pv_capex_calculated * pv_maintenance_percentage / 100
            st.write(f"• PV Maintenance: {pv_maintenance:,.0f} €/year")
        else:
            pv_maintenance = pv_capex * pv_maintenance_percentage / 100
            st.write(f"• PV Maintenance: {pv_maintenance:,.0f} €/year")
        
        # Financial Summary
        st.markdown("---")
        st.markdown("#### 💰 Financial Summary")
        
        st.info(f"**PV Annual Costs:**\n\n"
               f"• CAPEX (annualized): Calculated in LCOE\n\n"
               f"• OpEx: {pv_opex:,.0f} €/year\n\n"
               f"• Maintenance: {pv_maintenance:,.0f} €/year\n\n"
               f"• **Total Annual O&M**: {pv_opex + pv_maintenance:,.0f} €/year")

    # Calculate final values for return
    if use_calculated_capex:
        final_pv_capex = pv_capex_calculated
    else:
        final_pv_capex = pv_capex
    
    return {
        'pv_project_years': pv_project_years,
        'pv_surface_hectares': pv_surface_hectares,
        'power_density_mwp_per_ha': power_density_mwp_per_ha,
        'estimated_power_mwp': estimated_power_mwp,
        'estimated_power_kwp': estimated_power_kwp,
        'pv_cost_per_wp': pv_cost_per_wp,
        'use_calculated_capex': use_calculated_capex,
        'pv_capex': pv_capex,
        'opex_percentage': opex_percentage,
        'discount_rate': pv_discount_rate,
        'use_calculated_opex': use_calculated_opex,
        'pv_opex': pv_opex,
        'pv_maintenance_percentage': pv_maintenance_percentage,
        'pv_maintenance': pv_maintenance,
        'pv_capex_calculated': final_pv_capex,
        'lat': lat,
        'lon': lon,
        'loss': loss
    }


def create_battery_parameters(estimated_pv_power_mwp=None):
    """Create battery storage parameter inputs — independent from PV.
    
    Args:
        estimated_pv_power_mwp: PV estimated power (MWp) for reference display only
    
    Returns:
        dict with battery parameters
    """
    with st.sidebar.expander("🔋 Battery Storage", expanded=False):
        include_battery = st.checkbox(
            "Include Battery Storage",
            value=False,
            help="Add a battery energy storage system to the analysis"
        )
        
        if not include_battery:
            return {
                'include_battery': False,
                'battery_power_mw': 0,
                'charging_hours': 0,
                'battery_capacity_mwh': 0,
                'battery_cost_per_kwh': 0,
                'battery_maintenance_percentage': 1.0,
                'battery_capex': 0,
                'battery_opex': 0,
                'battery_opex_pct': 2.0,
                'battery_maintenance': 0,
            }
        
        st.markdown("**Battery Sizing**")
        
        battery_power_mw = st.number_input(
            "Battery Power (MW)",
            min_value=0.1,
            max_value=100.0,
            value=5.0,
            step=0.5,
            help="Maximum charge/discharge power of the battery system"
        )
        
        charging_hours = st.slider(
            "Charging Hours (h)",
            min_value=1,
            max_value=24,
            value=4,
            step=1,
            help="Number of hours the battery charges per day (determines energy capacity)"
        )
        
        # Auto-calculated capacity
        battery_capacity_mwh = battery_power_mw * charging_hours
        
        col_cap1, col_cap2 = st.columns(2)
        with col_cap1:
            st.metric("Battery Power", f"{battery_power_mw:.1f} MW")
        with col_cap2:
            st.metric("Battery Capacity", f"{battery_capacity_mwh:.1f} MWh",
                     delta=f"{charging_hours}h × {battery_power_mw:.1f} MW",
                     delta_color="off")
        
        if estimated_pv_power_mwp:
            st.caption(f"📐 PV Reference Power: {estimated_pv_power_mwp:.1f} MWp")
        
        st.markdown("---")
        st.markdown("**Battery Economics**")
        
        battery_cost_per_kwh = st.slider(
            "Battery Cost (€/kWh)",
            min_value=100,
            max_value=800,
            value=DEFAULT_PARAMS["battery_cost_per_kwh"],
            step=10,
            help="Cost per kWh of battery storage capacity"
        )
        
        # Calculate battery CAPEX
        battery_capex = (battery_capacity_mwh * 1000) * battery_cost_per_kwh
        
        st.markdown("---")
        st.markdown("#### 🔧 Battery Maintenance")
        
        battery_maintenance_percentage = st.slider(
            "Battery Maintenance (% of Battery CAPEX/year)",
            min_value=0.0,
            max_value=5.0,
            value=1.0,
            step=0.1,
            help="Annual battery maintenance cost as percentage of battery CAPEX",
            key="battery_maint_pct"
        )
        
        battery_maintenance = battery_capex * battery_maintenance_percentage / 100
        
        # Battery OPEX (as % of battery CAPEX, same as PV opex %)
        battery_opex_pct = st.slider(
            "Battery OPEX (% of Battery CAPEX/year)",
            min_value=0.0,
            max_value=10.0,
            value=2.0,
            step=0.5,
            help="Annual battery operational expenditure as percentage of battery CAPEX",
            key="battery_opex_pct"
        )
        battery_opex = battery_capex * battery_opex_pct / 100
        
        # Financial Summary
        st.markdown("---")
        st.markdown("#### 💰 Battery Financial Summary")
        
        st.info(
            f"**Battery System:**\n\n"
            f"• Power: **{battery_power_mw:.1f} MW** | Capacity: **{battery_capacity_mwh:.1f} MWh** "
            f"({charging_hours}h × {battery_power_mw:.1f} MW)\n\n"
            f"• CAPEX: **{battery_capex:,.0f} €** ({battery_cost_per_kwh} €/kWh)\n\n"
            f"• OpEx: **{battery_opex:,.0f} €/year**\n\n"
            f"• Maintenance: **{battery_maintenance:,.0f} €/year**\n\n"
            f"• **Total Annual O&M**: **{battery_opex + battery_maintenance:,.0f} €/year**"
        )
        
        return {
            'include_battery': True,
            'battery_power_mw': battery_power_mw,
            'charging_hours': charging_hours,
            'battery_capacity_mwh': battery_capacity_mwh,
            'battery_cost_per_kwh': battery_cost_per_kwh,
            'battery_maintenance_percentage': battery_maintenance_percentage,
            'battery_capex': battery_capex,
            'battery_opex': battery_opex,
            'battery_maintenance': battery_maintenance,
            'battery_opex_pct': battery_opex_pct,
        }


def get_current_parameters(selected_years, electrolyser_power, h2_flowrate,
                          monthly_service_ratios, target_prices, pv_price, ppa_price, pv_params,
                          battery_params=None,
                          go_enabled=False, go_cost_per_mwh=0.0, electrolyzer_econ=None, methanation_econ=None):
    """Get current parameters for change detection"""
    params = {
        'years': tuple(sorted(selected_years)) if selected_years else (),
        'power': electrolyser_power,
        'h2_flowrate': h2_flowrate,
        'monthly_service_ratios': tuple(sorted(monthly_service_ratios.items())),
        'target_prices': tuple(target_prices),
        'pv_price': pv_price,
        'ppa_price': ppa_price,
        'go_enabled': go_enabled,
        'go_cost_per_mwh': go_cost_per_mwh,
        'pv_project_years': pv_params['pv_project_years'],
        'pv_surface_hectares': pv_params['pv_surface_hectares'],
        'power_density_mwp_per_ha': pv_params['power_density_mwp_per_ha'],
        'pv_cost_per_wp': pv_params['pv_cost_per_wp'],
        'use_calculated_capex': pv_params['use_calculated_capex'],
        'opex_percentage': pv_params['opex_percentage'],
        'use_calculated_opex': pv_params['use_calculated_opex'],
        'pv_capex': pv_params['pv_capex'],
        'pv_opex': pv_params['pv_opex'],
        'pv_maintenance_percentage': pv_params['pv_maintenance_percentage'],
        'pv_maintenance': pv_params['pv_maintenance'],
        'lat': pv_params['lat'],
        'lon': pv_params['lon'],
        'loss': pv_params['loss']
    }
    
    # Add battery parameters if provided
    if battery_params:
        params.update({
            'include_battery': battery_params.get('include_battery', False),
            'battery_power_mw': battery_params.get('battery_power_mw', 0),
            'charging_hours': battery_params.get('charging_hours', 0),
            'battery_capacity_mwh': battery_params.get('battery_capacity_mwh', 0),
            'battery_cost_per_kwh': battery_params.get('battery_cost_per_kwh', 0),
            'battery_maintenance_percentage': battery_params.get('battery_maintenance_percentage', 1.0),
            'battery_capex': battery_params.get('battery_capex', 0),
            'battery_opex': battery_params.get('battery_opex', 0),
            'battery_maintenance': battery_params.get('battery_maintenance', 0),
            'battery_opex_pct': battery_params.get('battery_opex_pct', 2.0),
        })
    
    # Add electrolyzer economics if provided
    if electrolyzer_econ:
        params.update({
            'electrolyser_capex_transformer': electrolyzer_econ['capex_components']['transformer'],
            'electrolyser_capex_electrolyzer': electrolyzer_econ['capex_components']['electrolyzer'],
            'electrolyser_capex_compressor': electrolyzer_econ['capex_components']['compressor'],
            'electrolyser_capex_h2_storage': electrolyzer_econ['capex_components']['h2_storage'],
            'electrolyser_capex_piping': electrolyzer_econ['capex_components']['piping'],
            'electrolyser_others_capex': electrolyzer_econ['others_capex'],
            'electrolyser_maintenance_ratio_transformer': electrolyzer_econ['maintenance_ratios']['transformer'],
            'electrolyser_maintenance_ratio_electrolyzer': electrolyzer_econ['maintenance_ratios']['electrolyzer'],
            'electrolyser_maintenance_ratio_compressor': electrolyzer_econ['maintenance_ratios']['compressor'],
            'electrolyser_maintenance_ratio_h2_storage': electrolyzer_econ['maintenance_ratios']['h2_storage'],
            'electrolyser_maintenance_ratio_piping': electrolyzer_econ['maintenance_ratios']['piping'],
            'electrolyser_others_opex_annual': electrolyzer_econ['others_opex_annual'],
            'electrolyser_others_maintenance_annual': electrolyzer_econ['others_maintenance_annual'],
            'electrolyser_capex_total': electrolyzer_econ['electrolyzer_capex_total'],
            'electrolyser_capex_annual': electrolyzer_econ['electrolyzer_capex_annual'],
            'electrolyser_lifetime': electrolyzer_econ['electrolyzer_lifetime'],
            'electrolyser_discount_rate': electrolyzer_econ['electrolyzer_discount_rate'],
            'electrolyser_maintenance_annual': electrolyzer_econ['electrolyzer_maintenance_annual'],
            'electrolyser_water_price_per_m3': electrolyzer_econ['water_price_per_m3'],
            'electrolyser_water_consumption_annual_m3': electrolyzer_econ['water_consumption_annual_m3'],
            'electrolyser_water_cost_annual': electrolyzer_econ['water_cost_annual'],
            'electrolyser_other_costs_annual': electrolyzer_econ['other_costs_annual'],
            'electrolyser_stack_replacement_cost': electrolyzer_econ['stack_replacement_cost'],
            'electrolyser_stack_replacement_years': electrolyzer_econ['stack_replacement_years']
        })

    # Add methanation economics if provided
    if methanation_econ:
        params.update({
            'methanation_lifetime': methanation_econ['methanation_lifetime'],
            'methanation_discount_rate': methanation_econ['methanation_discount_rate'],
            'methanation_cons_spec_ch4': methanation_econ.get('cons_spec_ch4'),
            'methanation_capex_total': methanation_econ['methanation_capex_total'],
            'methanation_others_opex_annual': methanation_econ['others_opex_annual'],
            'methanation_maintenance_annual': methanation_econ['methanation_maintenance_annual']
        })
    
    return params
