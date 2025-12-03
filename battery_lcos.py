"""
Battery LCOS (Levelized Cost of Storage) Calculation Module
Implements LCOS methodology for battery energy storage systems
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import matplotlib.pyplot as plt


def calculate_wacc_nominal(debt_fraction: float, nominal_interest_rate: float,
                          tax_rate: float, nominal_cost_of_equity: float) -> float:
    """
    Calculate nominal Weighted Average Cost of Capital (WACC)

    WACC_nominal = DF × i_nom × (1 - τ) + (1 - DF) × COE_nom

    Args:
        debt_fraction: Percent of total capital financed with debt (%)
        nominal_interest_rate: Interest rate on debt (%)
        tax_rate: Combined federal and state tax rate (%)
        nominal_cost_of_equity: Rate of return on equity (%)

    Returns:
        Nominal WACC (%)
    """
    debt_fraction_decimal = debt_fraction / 100
    tax_rate_decimal = tax_rate / 100
    interest_rate_decimal = nominal_interest_rate / 100
    equity_rate_decimal = nominal_cost_of_equity / 100

    wacc_nominal = (debt_fraction_decimal * interest_rate_decimal * (1 - tax_rate_decimal) +
                   (1 - debt_fraction_decimal) * equity_rate_decimal)

    return wacc_nominal * 100  # Return as percentage


def calculate_wacc_real(wacc_nominal: float, inflation_rate: float) -> float:
    """
    Calculate real Weighted Average Cost of Capital (WACC)

    WACC_real = (1 + WACC_nominal) / (1 + inflation) - 1

    Args:
        wacc_nominal: Nominal WACC (%)
        inflation_rate: Inflation rate (%)

    Returns:
        Real WACC (%)
    """
    wacc_nominal_decimal = wacc_nominal / 100
    inflation_decimal = inflation_rate / 100

    wacc_real = (1 + wacc_nominal_decimal) / (1 + inflation_decimal) - 1

    return wacc_real * 100  # Return as percentage


def calculate_capital_recovery_factor(economic_life: int, wacc_real: float) -> float:
    """
    Calculate Capital Recovery Factor (CRF)

    CRF = d / (1 - (1 + d)^(-t))

    Args:
        economic_life: Economic life of the asset (years)
        wacc_real: Real WACC (%)

    Returns:
        Capital Recovery Factor (%)
    """
    d = wacc_real / 100  # Convert to decimal

    if d == 0:
        return 100 / economic_life  # Simple case when discount rate is 0

    crf = d / (1 - (1 + d) ** (-economic_life))
    return crf * 100  # Return as percentage


def calculate_construction_finance_factor(construction_period: int,
                                        capital_fractions: List[float],
                                        nominal_interest_rate: float,
                                        nominal_cost_of_equity: float,
                                        debt_fraction: float) -> float:
    """
    Calculate Construction Finance Factor (CFF)

    CFF = Σ(AI_c × CF_c × LC) + Σ(AE_c × CF_c × EC)

    Args:
        construction_period: Construction period (years)
        capital_fractions: List of capital fractions for each year (%)
        nominal_interest_rate: Nominal interest rate (%)
        nominal_cost_of_equity: Nominal cost of equity (%)
        debt_fraction: Debt fraction (%)

    Returns:
        Construction Finance Factor (%)
    """
    debt_fraction_decimal = debt_fraction / 100
    interest_rate_decimal = nominal_interest_rate / 100
    equity_rate_decimal = nominal_cost_of_equity / 100

    cff_debt = 0.0
    cff_equity = 0.0

    for c in range(construction_period + 1):
        if c < len(capital_fractions):
            cf_c = capital_fractions[c] / 100

            # Accumulated interest during construction
            ai_c = 1 + ((1 + interest_rate_decimal) ** (c + 0.5) - 1)

            # Accumulated equity during construction
            ae_c = 1 + ((1 + equity_rate_decimal) ** (c + 0.5) - 1)

            cff_debt += ai_c * cf_c * debt_fraction_decimal
            cff_equity += ae_c * cf_c * (1 - debt_fraction_decimal)

    cff = (cff_debt + cff_equity) * 100  # Convert to percentage
    return cff


def calculate_fixed_charge_rate(crf: float, tax_rate: float, pvd_macrs: float, cff: float) -> float:
    """
    Calculate Fixed Charge Rate (FCR)

    FCR = CRF × [(1 - τ × PVD_MACRS) / (1 - τ)] × CFF

    Args:
        crf: Capital Recovery Factor (%)
        tax_rate: Tax rate (%)
        pvd_macrs: Present Value of Depreciation (MACRS) - using simplified 1.0 for now
        cff: Construction Finance Factor (%)

    Returns:
        Fixed Charge Rate (%)
    """
    crf_decimal = crf / 100
    tax_rate_decimal = tax_rate / 100
    cff_decimal = cff / 100

    # For simplicity, using PVD_MACRS = 1.0 (can be enhanced with actual MACRS calculations)
    pvd_macrs = 1.0

    fcr = crf_decimal * ((1 - tax_rate_decimal * pvd_macrs) / (1 - tax_rate_decimal)) * cff_decimal
    return fcr * 100  # Return as percentage


def calculate_capex_pv(cash_flows: List[float], wacc_real: float, project_life: int) -> float:
    """
    Calculate Present Value of Capital Expenditures

    CAPEX_PV = Σ(CF_n / (1 + d)^n) for n=0 to N

    Args:
        cash_flows: List of cash flows for each year (€)
        wacc_real: Real WACC (%)
        project_life: Project life (years)

    Returns:
        Present value of capital expenditures (€)
    """
    d = wacc_real / 100  # Convert to decimal
    capex_pv = 0.0

    for n in range(min(len(cash_flows), project_life + 1)):
        capex_pv += cash_flows[n] / ((1 + d) ** n)

    return capex_pv


def calculate_annual_operating_hours(annual_discharge_hours: float) -> float:
    """
    Calculate annual hours discharged (AH)

    Args:
        annual_discharge_hours: Annual discharge hours

    Returns:
        Annual hours discharged
    """
    return annual_discharge_hours


def calculate_electricity_charging_cost(charging_cost_per_kwh: float,
                                      system_rte: float) -> float:
    """
    Calculate Electricity Charging Cost (ECC)

    ECC = charging_cost / RTE

    Args:
        charging_cost_per_kwh: Charging cost (€/kWh)
        system_rte: Round-trip efficiency (%)

    Returns:
        Electricity charging cost (€/kWh-discharge)
    """
    rte_decimal = system_rte / 100
    return charging_cost_per_kwh / rte_decimal


def calculate_battery_capex_schedule(battery_capacity_kwh: float,
                                   capex_per_kwh: float,
                                   replacement_years: int,
                                   replacement_cost_per_kwh: float,
                                   project_life: int) -> List[float]:
    """
    Calculate battery CAPEX schedule including replacements

    Args:
        battery_capacity_kwh: Battery capacity (kWh)
        capex_per_kwh: Initial CAPEX (€/kWh)
        replacement_years: Years between replacements
        replacement_cost_per_kwh: Replacement cost (€/kWh)
        project_life: Project life (years)

    Returns:
        List of CAPEX cash flows by year (€)
    """
    capex_schedule = [0.0] * (project_life + 1)

    # Initial CAPEX in year 0
    capex_schedule[0] = battery_capacity_kwh * capex_per_kwh

    # Replacement CAPEX
    if replacement_years > 0 and replacement_years <= project_life:
        replacement_years_list = list(range(replacement_years, project_life + 1, replacement_years))
        for year in replacement_years_list:
            if year <= project_life:
                capex_schedule[year] = battery_capacity_kwh * replacement_cost_per_kwh

    return capex_schedule


def calculate_lcos(fcr: float, capex_pv: float, annual_opex: float,
                  annual_discharge_hours: float, ecc: float) -> float:
    """
    Calculate Levelized Cost of Storage (LCOS)

    LCOS = [(FCR × CAPEX_PV) + O&M_Fixed] / AH + ECC

    Args:
        fcr: Fixed Charge Rate (%)
        capex_pv: Present value of capital expenditures (€)
        annual_opex: Annual fixed O&M (€/year)
        annual_discharge_hours: Annual hours discharged (hours/year)
        ecc: Electricity charging cost (€/kWh-discharge)

    Returns:
        LCOS (€/kWh-discharge)
    """
    fcr_decimal = fcr / 100

    if annual_discharge_hours == 0:
        return 0.0

    lcos = ((fcr_decimal * capex_pv) + annual_opex) / annual_discharge_hours + ecc
    return lcos


def calculate_battery_lcos_full(battery_capacity_kwh: float,
                              annual_discharge_hours: float,
                              charging_cost_per_kwh: float,
                              lcos_params: Dict,
                              capital_fractions: List[float] = None) -> Dict:
    """
    Calculate complete battery LCOS with all financial components

    Args:
        battery_capacity_kwh: Battery capacity (kWh)
        annual_discharge_hours: Annual discharge hours
        charging_cost_per_kwh: Charging cost (€/kWh)
        lcos_params: Dictionary of LCOS parameters

    Returns:
        Dictionary with all LCOS components and final LCOS value
    """
    # Extract parameters
    inflation_rate = lcos_params.get('inflation_rate', 2.8)
    debt_fraction = lcos_params.get('debt_fraction', 60.0)
    nominal_interest_rate = lcos_params.get('nominal_interest_rate', 5.0)
    tax_rate = lcos_params.get('tax_rate', 25.0)
    nominal_cost_of_equity = lcos_params.get('nominal_cost_of_equity', 8.0)
    economic_life = int(lcos_params.get('economic_life', 20))
    construction_period = int(lcos_params.get('construction_period', 1))

    # Get capital fractions - use passed parameter or extract from lcos_params
    if capital_fractions is None:
        capital_fractions = lcos_params.get('capital_fractions', [])
        if not capital_fractions:
            # Fallback to individual year parameters for backward compatibility
            capital_fractions = [
                lcos_params.get('capital_fraction_year_0', 70.0),
                lcos_params.get('capital_fraction_year_1', 30.0)
            ]
            # Ensure we have enough capital fractions for the construction period
            while len(capital_fractions) <= construction_period:
                capital_fractions.append(0.0)

    # Battery-specific parameters
    capex_per_kwh = lcos_params.get('battery_capex_per_kwh', 300.0)
    opex_percentage = lcos_params.get('battery_opex_percentage', 2.5)
    battery_efficiency = lcos_params.get('battery_efficiency', 85.0)
    replacement_years = int(lcos_params.get('battery_replacement_years', 10))
    replacement_cost_per_kwh = lcos_params.get('battery_replacement_cost', 200.0)

    # Step 1: Calculate WACC
    wacc_nominal = calculate_wacc_nominal(
        debt_fraction, nominal_interest_rate, tax_rate, nominal_cost_of_equity
    )

    wacc_real = calculate_wacc_real(wacc_nominal, inflation_rate)

    # Step 2: Calculate Capital Recovery Factor
    crf = calculate_capital_recovery_factor(economic_life, wacc_real)

    # Step 3: Calculate Construction Finance Factor
    cff = calculate_construction_finance_factor(
        construction_period, capital_fractions,
        nominal_interest_rate, nominal_cost_of_equity, debt_fraction
    )

    # Step 4: Calculate Fixed Charge Rate
    fcr = calculate_fixed_charge_rate(crf, tax_rate, 1.0, cff)  # PVD_MACRS = 1.0 for simplicity

    # Step 5: Calculate CAPEX schedule and present value
    capex_schedule = calculate_battery_capex_schedule(
        battery_capacity_kwh, capex_per_kwh, replacement_years,
        replacement_cost_per_kwh, economic_life
    )

    capex_pv = calculate_capex_pv(capex_schedule, wacc_real, economic_life)

    # Step 6: Calculate annual O&M
    annual_opex = capex_schedule[0] * (opex_percentage / 100)  # Based on initial CAPEX

    # Step 7: Calculate Electricity Charging Cost
    ecc = calculate_electricity_charging_cost(charging_cost_per_kwh, battery_efficiency)

    # Step 8: Calculate LCOS
    lcos = calculate_lcos(fcr, capex_pv, annual_opex, annual_discharge_hours, ecc)

    # Return all components
    return {
        'wacc_nominal': wacc_nominal,
        'wacc_real': wacc_real,
        'crf': crf,
        'cff': cff,
        'fcr': fcr,
        'capex_schedule': capex_schedule,
        'capex_pv': capex_pv,
        'annual_opex': annual_opex,
        'ecc': ecc,
        'lcos': lcos,
        'battery_capacity_kwh': battery_capacity_kwh,
        'annual_discharge_hours': annual_discharge_hours,
        'charging_cost_per_kwh': charging_cost_per_kwh
    }


def create_lcos_breakdown_chart(lcos_components: Dict) -> plt.Figure:
    """
    Create a breakdown chart showing LCOS components

    Args:
        lcos_components: Dictionary with LCOS calculation components

    Returns:
        Matplotlib figure
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

    # Financial components
    financial_labels = ['Capital Recovery', 'O&M Fixed', 'Electricity Charging']
    fcr_component = (lcos_components['fcr'] / 100) * lcos_components['capex_pv'] / lcos_components['annual_discharge_hours']
    om_component = lcos_components['annual_opex'] / lcos_components['annual_discharge_hours']
    ecc_component = lcos_components['ecc']

    financial_values = [fcr_component, om_component, ecc_component]
    colors_financial = ['#1f77b4', '#ff7f0e', '#2ca02c']

    ax1.pie(financial_values, labels=financial_labels, autopct='%1.1f%%',
            colors=colors_financial, startangle=90)
    ax1.set_title('LCOS Breakdown (€/kWh-discharge)')

    # Key ratios and rates
    ratios_labels = ['WACC Real', 'CRF', 'FCR', 'CFF']
    ratios_values = [
        lcos_components['wacc_real'],
        lcos_components['crf'],
        lcos_components['fcr'],
        lcos_components['cff']
    ]
    colors_ratios = ['#d62728', '#9467bd', '#8c564b', '#e377c2']

    bars = ax2.bar(ratios_labels, ratios_values, color=colors_ratios)
    ax2.set_ylabel('Percentage (%)')
    ax2.set_title('Financial Rates and Factors')

    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                f'{height:.1f}%', ha='center', va='bottom')

    plt.tight_layout()
    return fig


def create_capex_schedule_chart(capex_schedule: List[float]) -> plt.Figure:
    """
    Create a chart showing CAPEX schedule over time

    Args:
        capex_schedule: List of CAPEX cash flows by year

    Returns:
        Matplotlib figure
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    years = list(range(len(capex_schedule)))
    ax.bar(years, capex_schedule, color='#1f77b4', alpha=0.7)

    ax.set_xlabel('Year')
    ax.set_ylabel('CAPEX (€)')
    ax.set_title('Battery CAPEX Schedule (including replacements)')
    ax.grid(True, alpha=0.3)

    # Add value labels on bars
    for i, v in enumerate(capex_schedule):
        if v > 0:
            ax.text(i, v + max(capex_schedule) * 0.01, f'{v:,.0f}',
                   ha='center', va='bottom', fontsize=9)

    plt.tight_layout()
    return fig


def render_battery_lcos_tab():
    """
    Render the Battery LCOS Analysis tab in the main dashboard
    """
    import streamlit as st
    from config import DEFAULT_PARAMS, PARAM_RANGES

    st.markdown("## 💰 Battery Levelized Cost of Storage (LCOS) Analysis")
    st.markdown("---")
    st.markdown("""
    Calculate the Levelized Cost of Storage (LCOS) for battery energy storage systems using comprehensive financial methodology.
    This analysis includes WACC calculations, capital recovery factors, construction finance factors, and complete financial component breakdown.
    """)

    # Create two columns for inputs and results
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### ⚙️ Battery & Financial Parameters")

        # Battery system parameters
        st.markdown("#### 🔋 Battery System Parameters")
        battery_capacity_mwh = st.number_input(
            "Battery Capacity (MWh)",
            min_value=0.1, max_value=1000.0, value=10.0, step=0.1,
            help="Total battery energy capacity in megawatt-hours"
        )

        annual_discharge_hours = st.number_input(
            "Annual Discharge Hours",
            min_value=1, max_value=8760, value=1000, step=10,
            help="Total hours of battery discharge per year"
        )

        charging_cost_per_kwh = st.number_input(
            "Charging Cost (€/kWh)",
            min_value=0.0, max_value=1.0, value=0.05, step=0.01,
            help="Electricity cost for charging the battery"
        )

        # Financial parameters
        st.markdown("#### 💼 Financial Parameters")
        inflation_rate = st.number_input(
            f"Inflation Rate (%)",
            min_value=PARAM_RANGES["lcos_inflation_rate"]["min"],
            max_value=PARAM_RANGES["lcos_inflation_rate"]["max"],
            value=DEFAULT_PARAMS["lcos_inflation_rate"],
            step=PARAM_RANGES["lcos_inflation_rate"]["step"],
            help="Annual inflation rate"
        )

        debt_fraction = st.number_input(
            f"Debt Fraction (%)",
            min_value=PARAM_RANGES["lcos_debt_fraction"]["min"],
            max_value=PARAM_RANGES["lcos_debt_fraction"]["max"],
            value=DEFAULT_PARAMS["lcos_debt_fraction"],
            step=PARAM_RANGES["lcos_debt_fraction"]["step"],
            help="Percentage of capital financed with debt"
        )

        nominal_interest_rate = st.number_input(
            f"Nominal Interest Rate (%)",
            min_value=PARAM_RANGES["lcos_nominal_interest_rate"]["min"],
            max_value=PARAM_RANGES["lcos_nominal_interest_rate"]["max"],
            value=DEFAULT_PARAMS["lcos_nominal_interest_rate"],
            step=PARAM_RANGES["lcos_nominal_interest_rate"]["step"],
            help="Interest rate on debt financing"
        )

        tax_rate = st.number_input(
            f"Tax Rate (%)",
            min_value=PARAM_RANGES["lcos_tax_rate"]["min"],
            max_value=PARAM_RANGES["lcos_tax_rate"]["max"],
            value=DEFAULT_PARAMS["lcos_tax_rate"],
            step=PARAM_RANGES["lcos_tax_rate"]["step"],
            help="Combined federal and state tax rate"
        )

        nominal_cost_of_equity = st.number_input(
            f"Nominal Cost of Equity (%)",
            min_value=PARAM_RANGES["lcos_nominal_cost_of_equity"]["min"],
            max_value=PARAM_RANGES["lcos_nominal_cost_of_equity"]["max"],
            value=DEFAULT_PARAMS["lcos_nominal_cost_of_equity"],
            step=PARAM_RANGES["lcos_nominal_cost_of_equity"]["step"],
            help="Rate of return required on equity"
        )

        economic_life = st.number_input(
            f"Economic Life (years)",
            min_value=PARAM_RANGES["lcos_economic_life"]["min"],
            max_value=PARAM_RANGES["lcos_economic_life"]["max"],
            value=DEFAULT_PARAMS["lcos_economic_life"],
            step=PARAM_RANGES["lcos_economic_life"]["step"],
            help="Economic lifetime of the battery system"
        )

        construction_period = st.number_input(
            f"Construction Period (years)",
            min_value=PARAM_RANGES["lcos_construction_period"]["min"],
            max_value=PARAM_RANGES["lcos_construction_period"]["max"],
            value=DEFAULT_PARAMS["lcos_construction_period"],
            step=PARAM_RANGES["lcos_construction_period"]["step"],
            help="Total construction period (years) - determines number of capital fraction inputs"
        )

        # Dynamic capital fraction inputs based on construction period
        st.markdown(f"#### 🏗️ Capital Fractions (Years 0-{construction_period})")
        capital_fractions = []
        for year in range(construction_period + 1):  # c = 0 to C inclusive
            param_name = f"lcos_capital_fraction_year_{year}"
            default_value = DEFAULT_PARAMS.get(param_name, 0.0)
            param_range = PARAM_RANGES.get(param_name, {"min": 0.0, "max": 100.0, "step": 5.0})

            cf_value = st.number_input(
                f"Capital Fraction Year {year} (%)",
                min_value=param_range["min"],
                max_value=param_range["max"],
                value=default_value,
                step=param_range["step"],
                help=f"Percentage of capital spent in construction year {year}"
            )
            capital_fractions.append(cf_value)

        # Validate that capital fractions sum to 100%
        total_cf = sum(capital_fractions)
        if abs(total_cf - 100.0) > 0.1:  # Allow small tolerance for floating point
            st.warning(f"⚠️ Capital fractions sum to {total_cf:.1f}%. They should sum to 100% for accurate CFF calculation.")

        # Battery-specific parameters
        st.markdown("#### 🔋 Battery Technology Parameters")
        battery_capex_per_kwh = st.number_input(
            f"Battery CAPEX (€/kWh)",
            min_value=PARAM_RANGES["lcos_battery_capex_per_kwh"]["min"],
            max_value=PARAM_RANGES["lcos_battery_capex_per_kwh"]["max"],
            value=DEFAULT_PARAMS["lcos_battery_capex_per_kwh"],
            step=PARAM_RANGES["lcos_battery_capex_per_kwh"]["step"],
            help="Battery capital expenditure per kWh"
        )

        battery_efficiency = st.number_input(
            f"Battery Efficiency (%)",
            min_value=PARAM_RANGES["lcos_battery_efficiency"]["min"],
            max_value=PARAM_RANGES["lcos_battery_efficiency"]["max"],
            value=DEFAULT_PARAMS["lcos_battery_efficiency"],
            step=PARAM_RANGES["lcos_battery_efficiency"]["step"],
            help="Battery round-trip efficiency"
        )

        battery_replacement_years = st.number_input(
            f"Battery Replacement Interval (years)",
            min_value=PARAM_RANGES["lcos_battery_replacement_years"]["min"],
            max_value=PARAM_RANGES["lcos_battery_replacement_years"]["max"],
            value=DEFAULT_PARAMS["lcos_battery_replacement_years"],
            step=PARAM_RANGES["lcos_battery_replacement_years"]["step"],
            help="Years between battery replacements"
        )

        battery_replacement_cost = st.number_input(
            f"Battery Replacement Cost (€/kWh)",
            min_value=PARAM_RANGES["lcos_battery_replacement_cost"]["min"],
            max_value=PARAM_RANGES["lcos_battery_replacement_cost"]["max"],
            value=DEFAULT_PARAMS["lcos_battery_replacement_cost"],
            step=PARAM_RANGES["lcos_battery_replacement_cost"]["step"],
            help="Cost of battery replacement per kWh"
        )

    with col2:
        st.markdown("### 📊 LCOS Results & Analysis")

        # Calculate button
        if st.button("🔄 Calculate LCOS", type="primary", use_container_width=True):
            with st.spinner("Calculating LCOS..."):

                # Prepare parameters
                battery_capacity_kwh = battery_capacity_mwh * 1000  # Convert to kWh

                lcos_params = {
                    'inflation_rate': inflation_rate,
                    'debt_fraction': debt_fraction,
                    'nominal_interest_rate': nominal_interest_rate,
                    'tax_rate': tax_rate,
                    'nominal_cost_of_equity': nominal_cost_of_equity,
                    'economic_life': economic_life,
                    'battery_capex_per_kwh': battery_capex_per_kwh,
                    'battery_efficiency': battery_efficiency,
                    'battery_replacement_years': battery_replacement_years,
                    'battery_replacement_cost': battery_replacement_cost,
                    'battery_opex_percentage': DEFAULT_PARAMS["lcos_battery_opex_percentage"],
                    'construction_period': construction_period,
                    'capital_fractions': capital_fractions
                }

                # Calculate LCOS
                try:
                    results = calculate_battery_lcos_full(
                        battery_capacity_kwh,
                        annual_discharge_hours,
                        charging_cost_per_kwh,
                        lcos_params,
                        capital_fractions
                    )

                    # Display main results
                    st.markdown("#### 🎯 LCOS Results")

                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.metric(
                            "**LCOS**",
                            f"€{results['lcos']:.3f}/kWh",
                            help="Levelized Cost of Storage"
                        )
                    with col_b:
                        st.metric(
                            "**Battery Capacity**",
                            f"{battery_capacity_mwh:.1f} MWh",
                            help="Total battery energy capacity"
                        )
                    with col_c:
                        st.metric(
                            "**Annual Discharge**",
                            f"{annual_discharge_hours:.0f} hours",
                            help="Total annual discharge hours"
                        )

                    # Financial components breakdown
                    st.markdown("#### 💰 Financial Components")

                    comp_col1, comp_col2, comp_col3 = st.columns(3)
                    with comp_col1:
                        st.metric("WACC (Real)", f"{results['wacc_real']:.2f}%")
                        st.metric("Capital Recovery Factor", f"{results['crf']:.2f}%")
                    with comp_col2:
                        st.metric("Construction Finance Factor", f"{results['cff']:.2f}%")
                        st.metric("Fixed Charge Rate", f"{results['fcr']:.2f}%")
                    with comp_col3:
                        st.metric("CAPEX (PV)", f"€{results['capex_pv']:,.0f}")
                        st.metric("Annual O&M", f"€{results['annual_opex']:,.0f}")

                    # Cost breakdown visualization
                    st.markdown("#### 📈 Cost Breakdown Analysis")
                    breakdown_fig = create_lcos_breakdown_chart(results)
                    st.pyplot(breakdown_fig)

                    # CAPEX schedule
                    st.markdown("#### 📅 CAPEX Schedule")
                    capex_fig = create_capex_schedule_chart(results['capex_schedule'])
                    st.pyplot(capex_fig)

                    # Detailed results table
                    st.markdown("#### 📋 Detailed Results")
                    detailed_data = {
                        'Component': [
                            'LCOS (€/kWh-discharge)',
                            'CAPEX Present Value (€)',
                            'Annual Fixed O&M (€/year)',
                            'Electricity Charging Cost (€/kWh-discharge)',
                            'WACC Nominal (%)',
                            'WACC Real (%)',
                            'Capital Recovery Factor (%)',
                            'Construction Finance Factor (%)',
                            'Fixed Charge Rate (%)',
                            'Battery Capacity (kWh)',
                            'Annual Discharge Hours',
                            'Charging Cost (€/kWh)'
                        ],
                        'Value': [
                            f"{results['lcos']:.4f}",
                            f"{results['capex_pv']:,.0f}",
                            f"{results['annual_opex']:,.0f}",
                            f"{results['ecc']:.4f}",
                            f"{results['wacc_nominal']:.2f}",
                            f"{results['wacc_real']:.2f}",
                            f"{results['crf']:.2f}",
                            f"{results['cff']:.2f}",
                            f"{results['fcr']:.2f}",
                            f"{results['battery_capacity_kwh']:,.0f}",
                            f"{results['annual_discharge_hours']:.0f}",
                            f"{results['charging_cost_per_kwh']:.4f}"
                        ]
                    }

                    detailed_df = pd.DataFrame(detailed_data)
                    st.dataframe(detailed_df, use_container_width=True, hide_index=True)

                except Exception as e:
                    st.error(f"❌ Error calculating LCOS: {str(e)}")
                    st.exception(e)

        else:
            # Show placeholder content when no calculation has been run
            st.info("👆 Adjust the parameters and click 'Calculate LCOS' to see results")

            # Show methodology summary
            st.markdown("#### 📖 LCOS Methodology")
            st.markdown("""
            **Levelized Cost of Storage (LCOS)** is calculated using:

            ```
            LCOS = [(FCR × CAPEX_PV) + O&M_Fixed] / AH + ECC
            ```

            Where:
            - **FCR**: Fixed Charge Rate (includes financing costs)
            - **CAPEX_PV**: Present Value of Capital Expenditures
            - **O&M_Fixed**: Annual fixed Operations & Maintenance costs
            - **AH**: Annual discharge hours
            - **ECC**: Electricity Charging Cost (adjusted for efficiency)
            """)

            # Show key equations
            st.markdown("#### 🔢 Key Financial Equations")
            equations_data = {
                'Component': [
                    'WACC (Nominal)',
                    'WACC (Real)',
                    'Capital Recovery Factor',
                    'Fixed Charge Rate'
                ],
                'Formula': [
                    'DF × i_nom × (1-τ) + (1-DF) × COE_nom',
                    '(1 + WACC_nom) / (1 + inflation) - 1',
                    'd / (1 - (1+d)^(-t))',
                    'CRF × [(1-τ×PVD_MACRS)/(1-τ)] × CFF'
                ]
            }
            equations_df = pd.DataFrame(equations_data)
            st.dataframe(equations_df, use_container_width=True, hide_index=True)
