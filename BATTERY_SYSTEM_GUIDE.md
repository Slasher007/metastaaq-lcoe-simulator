# 🔋 Battery Arbitrage System - User Guide

## Overview

The Battery Arbitrage Optimization system is now integrated into your MetaSTAAQ dashboard as a **new tab**. It simulates a yearly energy management strategy for a hybrid PV-Battery-Electrolyser system with electricity market arbitrage.

## How to Access

1. Run your dashboard: `streamlit run dashboard.py`
2. Navigate to the **"🔋 Battery Arbitrage Optimization"** tab (next to "LCOE & Energy Analysis")

## System Components

### 1. Battery Energy Storage System (BESS)
- **Energy Capacity** (E_bat_max): Maximum storage capacity in MWh
- **Charge/Discharge Power**: Maximum power limits in MW
- **Round-trip Efficiency**: Typical 85-95% for Li-ion batteries
- **Depth of Discharge (DoD)**: How deeply the battery can discharge (80-100%)
- **Initial State of Charge**: Starting SoC on January 1st

### 2. Parametric Time Windows

The system operates in four distinct time windows each day:

#### 🌞 PV Charging Window (default: 10:00-16:00)
- All PV production charges the battery
- Excess PV is curtailed (not sold)
- Battery charges up to maximum capacity

#### 💰 Arbitrage Discharge Window (default: 16:00-23:00)
- Battery discharges to grid at **maximum power**
- Sells energy at evening peak prices
- Goal: empty battery before night charging

#### 🌙 Night Charging Window (default: 23:00-05:00)
- Charges from grid at low night prices
- Two modes:
  - **Always Charge**: Fill battery every night
  - **Price Threshold**: Only charge when price < X €/MWh

#### ⚡ Electrolyser Window (default: 05:00-10:00)
- Battery **exclusively** powers electrolyser
- **No grid purchase allowed**
- If battery insufficient → electrolyser runs reduced/stops (heavy penalty)

## Key Features

### Parametric Configuration
All time windows are **fully adjustable**. You can easily test scenarios like:
- PV Charging: 09:00-15:00 instead of 10:00-16:00
- Arbitrage: 17:00-00:00 instead of 16:00-23:00
- Custom electrolyser schedules

### Automatic Integration
- Uses **electrolyser power** from main dashboard configuration
- Uses **PV profile** from main dashboard PV configuration
- Uses **spot price data** from your CSV file

### Comprehensive Outputs

1. **Key Performance Indicators**
   - Net Profit (€/year and €/day)
   - Revenue from arbitrage
   - Cost of grid charging
   - H₂ production (tonnes, kg/day)
   - Battery cycles and average SoC

2. **Visualizations**
   - Battery State of Charge profile (zoomable by week)
   - Power flows (charging, discharging, electrolyser)
   - Monthly economics breakdown
   - Yearly cashflow
   - Hydrogen production statistics

3. **Detailed Statistics**
   - Energy flows (PV, grid, battery, curtailment)
   - Economic breakdown (revenue, costs, penalties)
   - Battery performance (SoC range, cycles, throughput)
   - Electrolyser performance (capacity factor, shortage hours)

## Optimization Objective

**Maximize yearly net profit:**

```
Net Profit = Revenue (selling to grid) 
           - Cost (buying from grid) 
           - Penalties (electrolyser shortages)
```

## Example Workflow

1. **Configure System in Sidebar**
   - Set battery capacity (e.g., 10 MWh)
   - Set charge/discharge power (e.g., 5 MW)
   - Adjust efficiency and DoD

2. **Set Time Windows**
   - Use the tabs to configure each operational window
   - Adjust start/end hours
   - Choose night charging strategy

3. **Run Optimization**
   - Click "🚀 Run Battery Optimization"
   - Wait for simulation (takes 5-30 seconds)

4. **Analyze Results**
   - Review KPIs at the top
   - Explore detailed tabs:
     - SoC & Power Flows
     - Economics
     - H₂ Production
     - Summary Statistics

5. **Iterate**
   - Adjust parameters
   - Re-run to compare scenarios
   - Find optimal configuration

## Sensitivity Analysis

For comprehensive sensitivity analysis (testing multiple parameter combinations), use the command-line tool:

```bash
python run_battery_optimization.py --help
python run_battery_optimization.py --battery-capacity 20 --year 2022
python run_battery_optimization.py --sensitivity  # Full sensitivity analysis
```

## Tips for Best Results

1. **Battery Sizing**
   - Larger capacity → more arbitrage revenue BUT higher costs
   - Match capacity to electrolyser energy needs
   - Typical ratio: 2-4 hours of electrolyser operation

2. **Time Window Optimization**
   - Align discharge window with peak price hours
   - Ensure electrolyser window has enough battery energy
   - Leave buffer between windows

3. **Night Charging Strategy**
   - "Always Charge" is simpler but may buy at higher prices
   - "Price Threshold" can reduce costs but risk insufficient charge

4. **Electrolyser Matching**
   - Battery must support full electrolyser window
   - Required energy = P_ely × window_duration
   - Account for discharge efficiency and DoD limits

## Constraints

The optimizer respects these hard constraints:

- Battery SoC between SoC_min and SoC_max at all times
- Charge/discharge power limits never exceeded
- Electrolyser can ONLY use battery (no grid)
- No direct PV → electrolyser connection
- PV curtailment (not sold during PV charging window)

## Output Files

When using command-line tool, results are saved to `battery_results/`:
- `hourly_results_YEAR.csv` - Full hourly simulation
- `summary_YEAR.json` - Summary statistics
- `configuration_YEAR.json` - Parameters used
- `visualizations/` - All charts as PNG files
- `sensitivity_analysis/` - Parameter sensitivity results

## Typical Results

**Example System:**
- Battery: 10 MWh capacity, 5 MW power
- Electrolyser: 5 MW
- PV: 10 MW peak

**Typical Annual Results:**
- Net Profit: 50,000 - 200,000 €/year (depends on price spreads)
- H₂ Production: 200-400 tonnes/year
- Battery Cycles: 300-500 cycles/year
- Electrolyser Capacity Factor: 20-40%

## Troubleshooting

**Issue: Electrolyser has many shortage hours**
- Increase battery capacity
- Extend night charging window
- Reduce electrolyser window duration
- Increase battery charge power

**Issue: Low arbitrage revenue**
- Check spot price data (needs price variation)
- Adjust discharge window to peak price hours
- Increase discharge power
- Increase battery capacity

**Issue: High penalties**
- Battery too small for electrolyser demand
- Insufficient night charging
- Check time window conflicts

## Technical Details

**Simulation Resolution:** Hourly (8760 hours/year)

**Battery Model:**
- Charge efficiency: √(η_rt)
- Discharge efficiency: √(η_rt)
- Self-discharge: ~0.01%/hour
- Hard SoC constraints

**Electrolyser Model:**
- Fixed power consumption when ON
- Minimum load ratio (e.g., 30%)
- Shutdown if below minimum load

**Economic Model:**
- Revenue = Discharge_energy × Spot_price
- Cost = Charge_energy × Spot_price
- Penalty = 10,000 €/MWh for shortages

## Support Files

The battery system consists of:
- `battery_config.py` - Configuration and parameters
- `battery_optimizer.py` - Core simulation engine
- `battery_visualization.py` - Plotting functions
- `battery_integration.py` - Dashboard integration
- `battery_sensitivity.py` - Sensitivity analysis tools
- `run_battery_optimization.py` - Command-line interface

## Next Steps

1. **Run your first optimization** with default parameters
2. **Understand the baseline** results
3. **Experiment with time windows** (easiest parameter to adjust)
4. **Test battery sizing** variations
5. **Run sensitivity analysis** to find optimal configuration
6. **Compare scenarios** for investment decisions

---

For questions or issues, check the main MetaSTAAQ documentation or contact support.

