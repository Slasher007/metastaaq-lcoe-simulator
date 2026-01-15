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
from battery_optimizer import BatteryOptimizer, generate_typical_pv_profile
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
        'sell_to_grid_start': args.arbitrage_start,
        'sell_to_grid_end': args.arbitrage_end,
        'grid_charging_start': args.night_start,
        'grid_charging_end': args.night_end,
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
    print(f"  Sell to Grid: {time_windows['sell_to_grid_start']:02d}:00 - {time_windows['sell_to_grid_end']:02d}:00")
    print(f"  Grid Charging: {time_windows['grid_charging_start']:02d}:00 - {time_windows['grid_charging_end']:02d}:00")
    print(f"  Electrolyser: {time_windows['electrolyser_start']:02d}:00 - {time_windows['electrolyser_end']:02d}:00")
    
    # Prepare PV profile
    print(f"\n☀️  Preparing PV profile...")
    timestamps = df_prices['timestamp'].values
    spot_prices = df_prices['Prix'].values
    
    if args.pv_monthly_file:
        print(f"   ⚠️ Monthly PV files are no longer supported. Ignoring {args.pv_monthly_file} and using a typical profile instead.")
    
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
    

if __name__ == "__main__":
    main()

