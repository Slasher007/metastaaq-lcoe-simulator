# 🔋 Battery Arbitrage - Quick Start Guide

## ✅ Integration Complete!

The battery arbitrage optimization system is now fully integrated into your MetaSTAAQ dashboard!

## 🚀 How to Use

### 1. Start Your Dashboard
```bash
streamlit run dashboard.py
```

### 2. Navigate to Battery Tab
Look for the **second tab** at the top:
- Tab 1: "📊 LCOE & Energy Analysis" (your existing dashboard)
- **Tab 2: "🔋 Battery Arbitrage Optimization"** ← Click here!

### 3. Configure System

#### Left Column - Battery Configuration
- **Energy Capacity**: 5-50 MWh (default: 10 MWh)
- **Charge/Discharge Power**: 2-25 MW (default: 5 MW)
- **Round-trip Efficiency**: 80-98% (default: 92%)
- **Max Depth of Discharge**: 80-100% (default: 90%)

**Note:** Electrolyser power is automatically taken from your main dashboard settings!

#### Right Column - Time Windows
Configure four operational windows (all adjustable):

**🌞 PV Charging** (default: 10:00-16:00)
- PV charges battery
- Excess curtailed

**💰 Arbitrage** (default: 16:00-23:00)
- Discharge to grid
- Sell at peak prices

**🌙 Night Charge** (default: 23:00-05:00)
- Charge from grid
- Low night prices

**⚡ Electrolyser** (default: 05:00-10:00)
- Battery powers electrolyser
- No grid purchase

### 4. Run Optimization
Click the green **"🚀 Run Battery Optimization"** button

Wait 5-30 seconds for simulation to complete.

### 5. View Results

#### Top Metrics
- Net Profit (€/year and €/day)
- Revenue from arbitrage
- Grid charging costs
- H₂ production (tonnes/year, kg/day, €/kg)
- Battery cycles and average SoC

#### Detailed Tabs

**📈 SoC & Power Flows**
- Battery state of charge profile
- Zoomable by week (use slider)
- Charging/discharging flows
- Electrolyser operation
- PV production and curtailment

**💰 Economics**
- Monthly cashflow breakdown
- Revenue vs costs
- Net profit trend
- Detailed monthly table

**⚡ H₂ Production**
- Daily hydrogen production
- Capacity factor
- Operating hours
- Shortage analysis

**📋 Summary**
- Complete statistics table
- Energy flows
- Economic metrics
- Battery performance
- Electrolyser performance

## 📊 Data Integration

The system automatically uses:
- ✅ Your **spot price data** from CSV (Prix column)
- ✅ Your **electrolyser power** from main config
- ✅ Your **PV profile** from main dashboard
- ✅ Selected **year** from main dashboard

No need to configure data twice!

## 💡 Tips for Success

### Battery Sizing
- Start with **10 MWh capacity**, **5 MW power**
- Increase if electrolyser has shortages
- Typical ratio: 2-4 hours of electrolyser operation

### Time Windows
- Default windows are optimized for French market
- Adjust based on your actual price patterns
- Keep electrolyser window after night charging

### Interpreting Results

**Good Performance:**
- Net profit > 50,000 €/year
- Electrolyser capacity factor > 30%
- Low shortage hours (< 100/year)
- Battery cycles: 300-500/year

**Issues to Fix:**
- High shortage hours → Increase battery capacity
- Low net profit → Check price spreads, adjust arbitrage window
- High penalties → Battery too small for electrolyser

## 🎯 Example Scenario

**System:**
- Battery: 10 MWh, 5 MW
- Electrolyser: 5 MW (from your config)
- PV: From your dashboard
- Year: 2021

**Expected Results:**
- Net Profit: ~100,000 €/year
- H₂ Production: ~250 tonnes/year
- Battery Cycles: ~350/year
- Electrolyser CF: ~35%

## 🔧 Troubleshooting

**Error: "Battery Arbitrage module not available"**
→ Ensure these files are in your project folder:
- `battery_config.py`
- `battery_optimizer.py`
- `battery_visualization.py`
- `battery_integration.py`

**Simulation takes too long**
→ Normal for first run (up to 30 seconds)
→ Results are cached for parameter changes

**Strange results**
→ Check time windows don't conflict
→ Ensure battery capacity sufficient for electrolyser
→ Verify PV profile is reasonable

## 📈 Next Steps

1. **Run baseline** with default parameters
2. **Experiment** with time windows (easiest to adjust)
3. **Test sizing** variations (battery capacity, power)
4. **Compare scenarios** for different years
5. **Document best configuration** for your use case

## 🎓 Advanced Features

For **comprehensive sensitivity analysis** of multiple parameters, use the command-line tool:

```bash
python run_battery_optimization.py --help
python run_battery_optimization.py --battery-capacity 20 --year 2022
python run_battery_optimization.py --sensitivity  # Full analysis
```

Results saved to `battery_results/` folder.

## 📚 Full Documentation

See `BATTERY_SYSTEM_GUIDE.md` for complete technical documentation.

---

**Ready to optimize? Click the 🔋 Battery Arbitrage Optimization tab and start!**

