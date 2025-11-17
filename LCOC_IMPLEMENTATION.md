# LCOC (Levelized Cost of CH₄) Implementation

## Overview
This document describes the implementation of CH₄ (methane) production cost calculation (LCOC - Levelized Cost of CH₄) similar to the existing LCOH (Levelized Cost of Hydrogen) analysis.

## Files Modified

### 1. `calculate_lcoh.py`
Added new functions for LCOC calculation:

#### New Functions:
- **`calculate_ch4_production_annual(h2_production_kg)`**
  - Calculates annual CH₄ production from H₂ production
  - Uses Sabatier reaction stoichiometry: CO₂ + 4H₂ → CH₄ + 2H₂O
  - Conversion ratio: 1 kg H₂ produces ~1.99 kg CH₄

- **`calculate_methanation_annualized_costs(...)`**
  - Calculates annualized costs for the methanation unit
  - Components: CapEx, OpEx (electricity + others), Maintenance, Other costs
  - Uses Capital Recovery Factor (CRF) for annualization

- **`add_methanation_capex_components_to_result(...)`**
  - Adds detailed CapEx components breakdown to results
  - Includes maintenance ratios and breakdown

- **`calculate_methanation_electricity_cost(...)`**
  - Calculates total annual electricity cost for methanation
  - Uses electricity consumption (MWh) × average electricity cost (€/MWh)

- **`calculate_lcoc(...)`**
  - Main function to calculate LCOC in €/kg CH₄
  - Formula: LCOC = (CapEx_ann + OpEx_ann + Maintenance + Other costs) / CH₄_production_ann
  - Returns detailed breakdown including:
    - LCOC in €/kg CH₄ and €/MWh CH₄
    - CH₄ production (kg and tonnes)
    - H₂ consumption (kg and tonnes)
    - Total annual cost
    - Cost breakdown by component

### 2. `ui_components.py`
Added new display function:

#### New Function:
- **`display_lcoc_results(lcoc_results, avg_service_ratio=None)`**
  - Displays LCOC calculation results in the dashboard
  - Shows main metrics:
    - LCOC in €/kg CH₄ and €/MWh CH₄
    - CH₄ production
    - H₂ consumption
    - Methanation electricity consumption
    - Average electricity cost
  - Displays detailed cost breakdown table
  - Shows pie chart for cost distribution
  - Displays detailed bar charts for:
    - CapEx components (Methanation Unit, Purification, Compressor, etc.)
    - OpEx components (Electricity, Others)
    - Maintenance components

### 3. `dashboard.py`
Integrated LCOC calculation into the dashboard:

#### Changes:
- Added import for `calculate_lcoc` from `calculate_lcoh`
- Added import for `display_lcoc_results` from `ui_components`
- Added LCOC calculation after LCOH calculation:
  ```python
  lcoc_results = calculate_lcoc(
      lcoh_results['h2_production_kg'],
      methanation_econ,
      avg_electricity_cost
  )
  display_lcoc_results(lcoc_results, avg_service_ratio)
  ```

### 4. `config.py` (No changes needed)
Already contains methanation economics parameters:
- CapEx components (methanation unit, purification, compressor, CH₄ storage, grid injection)
- Maintenance ratios for each component
- Electricity consumption parameters (MWhe/year)
- Project lifetime and discount rate

### 5. `sidebar.py` (No changes needed)
Already contains `create_methanation_parameters()` function that creates UI controls for:
- Project lifetime and discount rate
- CapEx components with expandable controls
- OpEx parameters (electricity consumption by component)
- Maintenance ratios and costs
- Returns `methanation_econ` dictionary with all parameters

## How It Works

### Step 1: User Input
Users configure methanation parameters in the sidebar:
- CapEx for each component (methanation unit, purification, compressor, storage, grid injection)
- Maintenance ratios (% of CapEx per year)
- Electricity consumption for each component (MWhe/year)
- Project lifetime and discount rate

### Step 2: H₂ Production
The electrolyzer produces H₂, and the production is calculated by `calculate_lcoh()`:
- Returns `h2_production_kg` (annual production in kg)

### Step 3: CH₄ Production
The methanation unit converts H₂ to CH₄:
- Uses Sabatier reaction stoichiometry
- 1 kg H₂ → 1.99 kg CH₄

### Step 4: Cost Calculation
LCOC is calculated as:
```
LCOC = Total Annual Cost / CH₄ Production

Where Total Annual Cost = 
  CapEx_annualized + 
  OpEx_annual (Electricity + Others) + 
  Maintenance_annual + 
  Other_costs_annual
```

### Step 5: Display Results
The dashboard displays:
1. **Main Metrics**: LCOC, CH₄ production, H₂ consumption, electricity cost
2. **Cost Breakdown Table**: CapEx, OpEx, Maintenance (€/kg, annual, lifetime)
3. **Pie Chart**: Visual distribution of costs
4. **Detailed Bar Charts**: CapEx, OpEx, and Maintenance components

## Key Features

1. **Integrated with LCOH**: Uses the same average electricity cost from LCOH calculation
2. **Detailed Component Breakdown**: Shows costs for each methanation component
3. **Stoichiometric Accuracy**: Uses correct H₂ to CH₄ conversion ratio
4. **Flexible Configuration**: All parameters are configurable through the sidebar
5. **Visual Representation**: Multiple charts and tables for easy understanding

## Example Output

### LCOC Metrics:
- **LCOC**: 2.50 €/kg CH₄
- **LCOC**: 179.86 €/MWh CH₄ (using LHV = 13.9 kWh/kg)
- **CH₄ Production**: 398.0 T/year (from 200 T H₂/year)
- **Total Annual Cost**: 995,000 €

### Cost Breakdown:
- **CapEx**: 40% (1.00 €/kg CH₄)
- **OpEx**: 45% (1.13 €/kg CH₄)
- **Maintenance**: 15% (0.37 €/kg CH₄)

## Usage

1. Run the dashboard: `streamlit run dashboard.py`
2. Configure electrolyzer parameters in the sidebar
3. Configure methanation parameters in the "🔥 Methanation" expander
4. Run the simulation
5. View LCOH results first, then LCOC results below

## Notes

- LCOC calculation requires LCOH to be calculated first (to get H₂ production)
- Electricity cost for methanation uses the average electricity cost from the overall energy mix
- CH₄ LHV (Lower Heating Value) is set to 13.9 kWh/kg (configurable in the calculation)
- The implementation follows the same pattern as LCOH for consistency

## Future Enhancements

Potential improvements:
1. Add CO₂ cost/supply parameters
2. Include heat recovery economics
3. Add methanation efficiency variations
4. Support multiple methanation technologies
5. Include degradation curves for methanation catalyst

