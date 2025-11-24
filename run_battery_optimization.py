"""
Command-line runner for Battery Energy Management System optimization
Standalone script for running optimization without Streamlit dashboard
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import argparse
import json
import os

from battery_config import (
    DEFAULT_BATTERY_PARAMS, DEFAULT_TIME_WINDOWS, DEFAULT_ELECTROLYSER_PARAMS,
    validate_time_windows
)
from battery_optimizer import BatteryOptimizer, distribute_monthly_pv_to_hourly, generate_typical_pv_profile
from battery_visualization import create_comprehensive_report
from battery_sensitivity import run_complete_sensitivity_analysis


def load_spot_price_data(filepath, year=None):
    """Load spot price data from CSV"""
    df = pd.read_csv(filepath)
    df['Date'] = pd.to_datetime(df['Date'])
    df['timestamp'] = df.apply(lambda row: row['Date'] + timedelta(hours=row['Heure']), axis=1)
    
    if year:
        df = df[df['Date'].dt.year == year]
    
    return df


def main():
    parser = argparse.ArgumentParser(
        description='Battery Energy Management System Optimization',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default parameters
  python run_battery_optimization.py
  
  # Run with custom battery size and year
  python run_battery_optimization.py --battery-capacity 20 --year 2022
  
  # Run with custom time windows
  python run_battery_optimization.py --pv-start 9 --pv-end 17
  
  # Run sensitivity analysis
  python run_battery_optimization.py --sensitivity
        """
    )
    
    # Data options
    parser.add_argument('--data-file', type=str, 
                       default='processed_donnees_prix_spot_fr_2021_2025_month_8.csv',
                       help='Path to spot price data CSV file')
    parser.add_argument('--year', type=int, default=2021,
                       help='Year to simulate (2021-2025)')
    
    # Battery parameters
    parser.add_argument('--battery-capacity', type=float, default=10.0,
                       help='Battery energy capacity (MWh)')
    parser.add_argument('--battery-power-charge', type=float, default=5.0,
                       help='Battery charge power (MW)')
    parser.add_argument('--battery-power-discharge', type=float, default=5.0,
                       help='Battery discharge power (MW)')
    parser.add_argument('--battery-efficiency', type=float, default=0.92,
                       help='Battery round-trip efficiency')
    parser.add_argument('--battery-dod', type=float, default=0.90,
                       help='Maximum depth of discharge')
    
    # Time windows
    parser.add_argument('--pv-start', type=int, default=10,
                       help='PV charging window start (hour, 0-23)')
    parser.add_argument('--pv-end', type=int, default=16,
                       help='PV charging window end (hour, 0-23)')
    parser.add_argument('--arbitrage-start', type=int, default=16,
                       help='Arbitrage discharge window start (hour, 0-23)')
    parser.add_argument('--arbitrage-end', type=int, default=23,
                       help='Arbitrage discharge window end (hour, 0-23)')
    parser.add_argument('--night-start', type=int, default=23,
                       help='Night charging window start (hour, 0-23)')
    parser.add_argument('--night-end', type=int, default=5,
                       help='Night charging window end (hour, 0-23)')
    parser.add_argument('--ely-start', type=int, default=5,
                       help='Electrolyser window start (hour, 0-23)')
    parser.add_argument('--ely-end', type=int, default=10,
                       help='Electrolyser window end (hour, 0-23)')
    
    # Electrolyser parameters
    parser.add_argument('--ely-power', type=float, default=5.0,
                       help='Electrolyser power (MW)')
    parser.add_argument('--ely-consumption', type=float, default=4.8,
                       help='Electrolyser specific consumption (kWh/kg H2)')
    
    # PV parameters
    parser.add_argument('--pv-peak-power', type=float, default=10.0,
                       help='PV peak power (MW)')
    parser.add_argument('--pv-monthly-file', type=str, default=None,
                       help='JSON file with monthly PV energy (MWh)')
    
    # Analysis options
    parser.add_argument('--sensitivity', action='store_true',
                       help='Run comprehensive sensitivity analysis')
    parser.add_argument('--output-dir', type=str, default='battery_results',
                       help='Output directory for results')
    
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    print("="*80)
    print("BATTERY ENERGY MANAGEMENT SYSTEM OPTIMIZATION")
    print("="*80)
    
    # Load data
    print(f"\n📁 Loading spot price data from {args.data_file}...")
    try:
        df_prices = load_spot_price_data(args.data_file, year=args.year)
        print(f"✅ Loaded {len(df_prices)} hourly price records for {args.year}")
        print(f"   Price range: {df_prices['Prix'].min():.2f} - {df_prices['Prix'].max():.2f} €/MWh")
        print(f"   Average price: {df_prices['Prix'].mean():.2f} €/MWh")
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return
    
    # Prepare parameters
    battery_params = DEFAULT_BATTERY_PARAMS.copy()
    battery_params['E_bat_max'] = args.battery_capacity
    battery_params['P_charge_max'] = args.battery_power_charge
    battery_params['P_discharge_max'] = args.battery_power_discharge
    battery_params['eta_rt'] = args.battery_efficiency
    battery_params['eta_charge'] = np.sqrt(args.battery_efficiency)
    battery_params['eta_discharge'] = np.sqrt(args.battery_efficiency)
    battery_params['DoD_max'] = args.battery_dod
    
    time_windows = {
        'pv_charge_start': args.pv_start,
        'pv_charge_end': args.pv_end,
        'arbitrage_discharge_start': args.arbitrage_start,
        'arbitrage_discharge_end': args.arbitrage_end,
        'night_charge_start': args.night_start,
        'night_charge_end': args.night_end,
        'electrolyser_start': args.ely_start,
        'electrolyser_end': args.ely_end,
    }
    
    electrolyser_params = DEFAULT_ELECTROLYSER_PARAMS.copy()
    electrolyser_params['P_ely'] = args.ely_power
    electrolyser_params['specific_consumption'] = args.ely_consumption
    
    # Validate time windows
    is_valid, validation_msg = validate_time_windows(time_windows)
    if not is_valid:
        print(f"⚠️  WARNING: {validation_msg}")
    
    # Display configuration
    print("\n⚙️  SYSTEM CONFIGURATION")
    print("-"*80)
    print(f"Battery:")
    print(f"  Capacity: {battery_params['E_bat_max']:.1f} MWh")
    print(f"  Charge Power: {battery_params['P_charge_max']:.1f} MW")
    print(f"  Discharge Power: {battery_params['P_discharge_max']:.1f} MW")
    print(f"  Round-trip Efficiency: {battery_params['eta_rt']:.1%}")
    print(f"  Max DoD: {battery_params['DoD_max']:.1%}")
    
    print(f"\nElectrolyser:")
    print(f"  Power: {electrolyser_params['P_ely']:.1f} MW")
    print(f"  Specific Consumption: {electrolyser_params['specific_consumption']:.1f} kWh/kg H₂")
    
    print(f"\nOperational Time Windows:")
    print(f"  PV Charging: {time_windows['pv_charge_start']:02d}:00 - {time_windows['pv_charge_end']:02d}:00")
    print(f"  Arbitrage Discharge: {time_windows['arbitrage_discharge_start']:02d}:00 - {time_windows['arbitrage_discharge_end']:02d}:00")
    print(f"  Night Charging: {time_windows['night_charge_start']:02d}:00 - {time_windows['night_charge_end']:02d}:00")
    print(f"  Electrolyser: {time_windows['electrolyser_start']:02d}:00 - {time_windows['electrolyser_end']:02d}:00")
    
    # Prepare PV profile
    print(f"\n☀️  Preparing PV profile...")
    timestamps = df_prices['timestamp'].values
    spot_prices = df_prices['Prix'].values
    
    if args.pv_monthly_file:
        with open(args.pv_monthly_file, 'r') as f:
            pv_energy_monthly = json.load(f)
        pv_profile = distribute_monthly_pv_to_hourly(pv_energy_monthly, timestamps)
        print(f"   Using monthly PV data from {args.pv_monthly_file}")
    else:
        pv_profile = generate_typical_pv_profile(timestamps, peak_power_mw=args.pv_peak_power)
        print(f"   Generated typical PV profile with {args.pv_peak_power:.1f} MW peak power")
    
    print(f"   Total PV production: {pv_profile.sum():.1f} MWh/year")
    
    # Run optimization
    print("\n🚀 RUNNING OPTIMIZATION")
    print("-"*80)
    
    optimizer = BatteryOptimizer(
        battery_params=battery_params,
        time_windows=time_windows,
        electrolyser_params=electrolyser_params
    )
    
    df_results, summary = optimizer.simulate_year(pv_profile, spot_prices, timestamps)
    
    # Display results
    print("\n✅ OPTIMIZATION COMPLETE")
    print("="*80)
    print("\n📊 KEY RESULTS")
    print("-"*80)
    
    print(f"\n💰 Economics:")
    print(f"   Total Revenue (Arbitrage):  {summary['total_revenue_eur']:>15,.0f} €")
    print(f"   Total Cost (Grid Charging): {summary['total_cost_eur']:>15,.0f} €")
    print(f"   Total Penalties:            {summary['total_penalties_eur']:>15,.0f} €")
    print(f"   NET PROFIT:                 {summary['net_profit_eur']:>15,.0f} €")
    print(f"   Daily Average Profit:       {summary['net_profit_eur']/365:>15,.0f} €/day")
    
    print(f"\n⚡ Hydrogen Production:")
    print(f"   Total Production:           {summary['total_h2_production_tonnes']:>15,.1f} tonnes")
    print(f"   Daily Average:              {summary['total_h2_production_kg']/365:>15,.1f} kg/day")
    print(f"   H₂ Cost:                    {summary['h2_cost_eur_per_kg']:>15,.2f} €/kg")
    
    print(f"\n🔋 Battery Statistics:")
    print(f"   Average SoC:                {summary['avg_soc']:>15,.1%}")
    print(f"   SoC Range:                  {summary['min_soc']:.1%} - {summary['max_soc']:.1%}")
    print(f"   Equivalent Cycles:          {summary['equivalent_cycles']:>15,.0f}")
    print(f"   Energy Throughput:          {summary['total_battery_to_grid_mwh'] + summary['total_battery_to_ely_mwh']:>15,.0f} MWh")
    
    print(f"\n⚡ Electrolyser Performance:")
    print(f"   Operating Hours:            {summary['ely_operating_hours']:>15,.0f} hours")
    print(f"   Shortage Hours:             {summary['ely_shortage_hours']:>15,.0f} hours")
    print(f"   Capacity Factor:            {summary['ely_capacity_factor']:>15,.1%}")
    
    print(f"\n☀️  PV Utilization:")
    print(f"   PV Available:               {summary['total_pv_available_mwh']:>15,.0f} MWh")
    print(f"   PV to Battery:              {summary['total_pv_to_battery_mwh']:>15,.0f} MWh")
    print(f"   Utilization Rate:           {summary['pv_utilization_rate']:>15,.1%}")
    
    # Save results
    print(f"\n💾 SAVING RESULTS")
    print("-"*80)
    
    # Save hourly results
    results_file = os.path.join(args.output_dir, f'hourly_results_{args.year}.csv')
    df_results.to_csv(results_file, index=False)
    print(f"   Hourly results saved to: {results_file}")
    
    # Save summary
    summary_file = os.path.join(args.output_dir, f'summary_{args.year}.json')
    with open(summary_file, 'w') as f:
        # Convert non-serializable types
        summary_clean = {k: float(v) if isinstance(v, (np.integer, np.floating)) else v 
                        for k, v in summary.items() if not isinstance(v, dict)}
        json.dump(summary_clean, f, indent=2)
    print(f"   Summary saved to: {summary_file}")
    
    # Save configuration
    config_file = os.path.join(args.output_dir, f'configuration_{args.year}.json')
    with open(config_file, 'w') as f:
        config = {
            'battery_params': battery_params,
            'time_windows': time_windows,
            'electrolyser_params': electrolyser_params,
            'year': args.year
        }
        json.dump(config, f, indent=2)
    print(f"   Configuration saved to: {config_file}")
    
    # Generate comprehensive report
    print(f"\n📈 Generating visualization report...")
    report_dir = os.path.join(args.output_dir, 'visualizations')
    figures = create_comprehensive_report(
        df_results, summary, battery_params, time_windows, 
        electrolyser_params, save_dir=report_dir
    )
    print(f"   {len(figures)} figures saved to: {report_dir}/")
    
    # Sensitivity analysis
    if args.sensitivity:
        print(f"\n🔬 RUNNING SENSITIVITY ANALYSIS")
        print("-"*80)
        print("   This may take 10-30 minutes...")
        
        sensitivity_dir = os.path.join(args.output_dir, 'sensitivity_analysis')
        sensitivity_results = run_complete_sensitivity_analysis(
            pv_profile, spot_prices, timestamps,
            battery_params, time_windows, electrolyser_params,
            save_dir=sensitivity_dir
        )
        
        print(f"   Sensitivity analysis complete!")
        print(f"   Results saved to: {sensitivity_dir}/")
    
    print("\n" + "="*80)
    print("OPTIMIZATION COMPLETE")
    print("="*80)
    print(f"\nAll results saved to: {args.output_dir}/")
    print("\nNext steps:")
    print(f"  - View visualizations in: {report_dir}/")
    print(f"  - Analyze hourly results in: {results_file}")
    if args.sensitivity:
        print(f"  - Review sensitivity analysis in: {sensitivity_dir}/")
    print(f"\nTo run the interactive dashboard:")
    print(f"  streamlit run battery_arbitrage_dashboard.py")
    print()


if __name__ == "__main__":
    main()

