"""
Sensitivity Analysis for Battery Energy Management System
Test variations in time windows, battery sizing, and electrolyser power
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from itertools import product
from battery_optimizer import BatteryOptimizer
from battery_config import (
    DEFAULT_BATTERY_PARAMS, DEFAULT_TIME_WINDOWS, DEFAULT_ELECTROLYSER_PARAMS,
    TIME_WINDOW_RANGES, BATTERY_PARAM_RANGES, ELECTROLYSER_PARAM_RANGES
)


class SensitivityAnalyzer:
    """
    Perform sensitivity analysis on battery system parameters and time windows
    """
    
    def __init__(self, base_battery_params=None, base_time_windows=None, 
                 base_electrolyser_params=None):
        """
        Initialize sensitivity analyzer with base case parameters
        """
        self.base_battery_params = base_battery_params or DEFAULT_BATTERY_PARAMS.copy()
        self.base_time_windows = base_time_windows or DEFAULT_TIME_WINDOWS.copy()
        self.base_electrolyser_params = base_electrolyser_params or DEFAULT_ELECTROLYSER_PARAMS.copy()
    
    def time_window_sensitivity(self, pv_profile, spot_prices, timestamps, 
                               param_name, param_values, fixed_params=None):
        """
        Analyze sensitivity to a single time window parameter
        
        Args:
            pv_profile: Array of PV production [MW]
            spot_prices: Array of spot prices [€/MWh]
            timestamps: Array of timestamps
            param_name: Name of time window parameter to vary
            param_values: List of values to test
            fixed_params: Optional dict of other parameters to override
        
        Returns:
            DataFrame with results for each parameter value
        """
        results = []
        
        for value in param_values:
            # Create modified time windows
            time_windows = self.base_time_windows.copy()
            if fixed_params:
                time_windows.update(fixed_params)
            time_windows[param_name] = value
            
            # Run simulation
            optimizer = BatteryOptimizer(
                battery_params=self.base_battery_params,
                time_windows=time_windows,
                electrolyser_params=self.base_electrolyser_params
            )
            
            df_results, summary = optimizer.simulate_year(pv_profile, spot_prices, timestamps)
            
            # Store key metrics
            results.append({
                'parameter': param_name,
                'value': value,
                'net_profit_eur': summary['net_profit_eur'],
                'total_revenue_eur': summary['total_revenue_eur'],
                'total_cost_eur': summary['total_cost_eur'],
                'total_h2_tonnes': summary['total_h2_production_tonnes'],
                'ely_capacity_factor': summary['ely_capacity_factor'],
                'pv_utilization': summary['pv_utilization_rate'],
                'equivalent_cycles': summary['equivalent_cycles'],
                'avg_soc': summary['avg_soc'],
                'h2_cost_eur_per_kg': summary['h2_cost_eur_per_kg'],
            })
        
        return pd.DataFrame(results)
    
    def battery_sizing_sensitivity(self, pv_profile, spot_prices, timestamps,
                                   capacity_values_mwh, power_values_mw=None):
        """
        Analyze sensitivity to battery capacity and power ratings
        
        Args:
            capacity_values_mwh: List of battery capacities to test [MWh]
            power_values_mw: List of power ratings to test [MW] (if None, use capacity/2)
        
        Returns:
            DataFrame with results
        """
        results = []
        
        for capacity in capacity_values_mwh:
            if power_values_mw is None:
                # Use C-rate of 0.5 (capacity/2)
                power_list = [capacity / 2]
            else:
                power_list = power_values_mw
            
            for power in power_list:
                # Create modified battery params
                battery_params = self.base_battery_params.copy()
                battery_params['E_bat_max'] = capacity
                battery_params['P_charge_max'] = power
                battery_params['P_discharge_max'] = power
                
                # Run simulation
                optimizer = BatteryOptimizer(
                    battery_params=battery_params,
                    time_windows=self.base_time_windows,
                    electrolyser_params=self.base_electrolyser_params
                )
                
                df_results, summary = optimizer.simulate_year(pv_profile, spot_prices, timestamps)
                
                # Store key metrics
                results.append({
                    'capacity_mwh': capacity,
                    'power_mw': power,
                    'c_rate': power / capacity if capacity > 0 else 0,
                    'net_profit_eur': summary['net_profit_eur'],
                    'total_revenue_eur': summary['total_revenue_eur'],
                    'total_cost_eur': summary['total_cost_eur'],
                    'total_h2_tonnes': summary['total_h2_production_tonnes'],
                    'ely_capacity_factor': summary['ely_capacity_factor'],
                    'equivalent_cycles': summary['equivalent_cycles'],
                    'profit_per_mwh_capacity': summary['net_profit_eur'] / capacity if capacity > 0 else 0,
                })
        
        return pd.DataFrame(results)
    
    def electrolyser_sizing_sensitivity(self, pv_profile, spot_prices, timestamps,
                                       power_values_mw):
        """
        Analyze sensitivity to electrolyser power rating
        
        Args:
            power_values_mw: List of electrolyser power ratings to test [MW]
        
        Returns:
            DataFrame with results
        """
        results = []
        
        for power in power_values_mw:
            # Create modified electrolyser params
            ely_params = self.base_electrolyser_params.copy()
            ely_params['P_ely'] = power
            
            # Run simulation
            optimizer = BatteryOptimizer(
                battery_params=self.base_battery_params,
                time_windows=self.base_time_windows,
                electrolyser_params=ely_params
            )
            
            df_results, summary = optimizer.simulate_year(pv_profile, spot_prices, timestamps)
            
            # Store key metrics
            results.append({
                'ely_power_mw': power,
                'net_profit_eur': summary['net_profit_eur'],
                'total_h2_tonnes': summary['total_h2_production_tonnes'],
                'ely_capacity_factor': summary['ely_capacity_factor'],
                'ely_operating_hours': summary['ely_operating_hours'],
                'ely_shortage_hours': summary['ely_shortage_hours'],
                'h2_cost_eur_per_kg': summary['h2_cost_eur_per_kg'],
            })
        
        return pd.DataFrame(results)
    
    def two_parameter_sensitivity(self, pv_profile, spot_prices, timestamps,
                                  param1_name, param1_values, 
                                  param2_name, param2_values,
                                  param_type='time_window'):
        """
        Analyze sensitivity to two parameters simultaneously (creates heatmap)
        
        Args:
            param1_name: First parameter name
            param1_values: List of values for first parameter
            param2_name: Second parameter name
            param2_values: List of values for second parameter
            param_type: 'time_window', 'battery', or 'electrolyser'
        
        Returns:
            DataFrame with results for all combinations
        """
        results = []
        
        total_combinations = len(param1_values) * len(param2_values)
        print(f"Running {total_combinations} simulations...")
        
        for i, (val1, val2) in enumerate(product(param1_values, param2_values)):
            if (i + 1) % 10 == 0:
                print(f"Progress: {i+1}/{total_combinations}")
            
            # Create modified parameters based on type
            if param_type == 'time_window':
                time_windows = self.base_time_windows.copy()
                time_windows[param1_name] = val1
                time_windows[param2_name] = val2
                battery_params = self.base_battery_params
                ely_params = self.base_electrolyser_params
                
            elif param_type == 'battery':
                time_windows = self.base_time_windows
                battery_params = self.base_battery_params.copy()
                battery_params[param1_name] = val1
                battery_params[param2_name] = val2
                ely_params = self.base_electrolyser_params
                
            elif param_type == 'electrolyser':
                time_windows = self.base_time_windows
                battery_params = self.base_battery_params
                ely_params = self.base_electrolyser_params.copy()
                ely_params[param1_name] = val1
                ely_params[param2_name] = val2
            
            else:
                raise ValueError(f"Unknown param_type: {param_type}")
            
            # Run simulation
            try:
                optimizer = BatteryOptimizer(
                    battery_params=battery_params,
                    time_windows=time_windows,
                    electrolyser_params=ely_params
                )
                
                df_results, summary = optimizer.simulate_year(pv_profile, spot_prices, timestamps)
                
                # Store key metrics
                results.append({
                    param1_name: val1,
                    param2_name: val2,
                    'net_profit_eur': summary['net_profit_eur'],
                    'total_revenue_eur': summary['total_revenue_eur'],
                    'total_cost_eur': summary['total_cost_eur'],
                    'total_h2_tonnes': summary['total_h2_production_tonnes'],
                    'ely_capacity_factor': summary['ely_capacity_factor'],
                    'h2_cost_eur_per_kg': summary['h2_cost_eur_per_kg'],
                })
            except Exception as e:
                print(f"Error with {param1_name}={val1}, {param2_name}={val2}: {e}")
                results.append({
                    param1_name: val1,
                    param2_name: val2,
                    'net_profit_eur': np.nan,
                    'total_revenue_eur': np.nan,
                    'total_cost_eur': np.nan,
                    'total_h2_tonnes': np.nan,
                    'ely_capacity_factor': np.nan,
                    'h2_cost_eur_per_kg': np.nan,
                })
        
        return pd.DataFrame(results)


def plot_single_parameter_sensitivity(df_sensitivity, param_name, metric='net_profit_eur', 
                                      save_path=None):
    """
    Plot sensitivity to a single parameter
    
    Args:
        df_sensitivity: DataFrame from sensitivity analysis
        param_name: Parameter name
        metric: Metric to plot on y-axis
        save_path: Optional path to save figure
    
    Returns:
        matplotlib Figure
    """
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    metrics_to_plot = [
        ('net_profit_eur', 'Net Profit (€)', 'green'),
        ('total_h2_tonnes', 'H₂ Production (tonnes)', 'purple'),
        ('ely_capacity_factor', 'Electrolyser Capacity Factor', 'blue'),
        ('h2_cost_eur_per_kg', 'H₂ Cost (€/kg)', 'red'),
    ]
    
    for idx, (metric_col, ylabel, color) in enumerate(metrics_to_plot):
        ax = axes[idx // 2, idx % 2]
        
        if metric_col in df_sensitivity.columns:
            ax.plot(df_sensitivity['value'], df_sensitivity[metric_col], 
                   marker='o', linewidth=2, markersize=8, color=color)
            ax.set_xlabel(f'{param_name}', fontsize=11, fontweight='bold')
            ax.set_ylabel(ylabel, fontsize=11, fontweight='bold')
            ax.set_title(f'{ylabel} vs {param_name}', fontsize=12, fontweight='bold')
            ax.grid(True, alpha=0.3)
            
            # Add value labels
            for x, y in zip(df_sensitivity['value'], df_sensitivity[metric_col]):
                ax.text(x, y, f'{y:.1f}', fontsize=8, ha='center', va='bottom')
    
    plt.suptitle(f'Sensitivity Analysis: {param_name}', fontsize=14, fontweight='bold')
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    
    return fig


def plot_two_parameter_heatmap(df_sensitivity, param1_name, param2_name, 
                               metric='net_profit_eur', save_path=None):
    """
    Plot 2D heatmap for two-parameter sensitivity analysis
    
    Args:
        df_sensitivity: DataFrame from two_parameter_sensitivity
        param1_name: First parameter name (x-axis)
        param2_name: Second parameter name (y-axis)
        metric: Metric to display in heatmap
        save_path: Optional path to save figure
    
    Returns:
        matplotlib Figure
    """
    # Pivot data for heatmap
    pivot_data = df_sensitivity.pivot(index=param2_name, columns=param1_name, values=metric)
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Create heatmap
    sns.heatmap(pivot_data, annot=True, fmt='.0f', cmap='RdYlGn', 
                cbar_kws={'label': metric}, ax=ax, linewidths=0.5)
    
    ax.set_xlabel(param1_name, fontsize=12, fontweight='bold')
    ax.set_ylabel(param2_name, fontsize=12, fontweight='bold')
    ax.set_title(f'{metric} Sensitivity: {param1_name} vs {param2_name}', 
                fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    
    return fig


def plot_comprehensive_sensitivity_table(df_battery_sizing, df_ely_sizing, 
                                         df_time_windows, save_path=None):
    """
    Create comprehensive sensitivity summary table
    
    Args:
        df_battery_sizing: Battery sizing sensitivity results
        df_ely_sizing: Electrolyser sizing sensitivity results
        df_time_windows: Time window sensitivity results (list of DataFrames)
        save_path: Optional path to save figure
    
    Returns:
        matplotlib Figure with table
    """
    fig, ax = plt.subplots(figsize=(16, 10))
    ax.axis('off')
    
    # Create summary table data
    table_data = []
    
    # Battery sizing summary
    table_data.append(['**BATTERY SIZING**', '', '', '', ''])
    table_data.append(['Capacity (MWh)', 'Power (MW)', 'Net Profit (€)', 
                      'H₂ (tonnes)', 'Profit/MWh (€)'])
    for _, row in df_battery_sizing.iterrows():
        table_data.append([
            f"{row['capacity_mwh']:.1f}",
            f"{row['power_mw']:.1f}",
            f"{row['net_profit_eur']:,.0f}",
            f"{row['total_h2_tonnes']:.1f}",
            f"{row['profit_per_mwh_capacity']:.0f}"
        ])
    
    table_data.append(['', '', '', '', ''])
    
    # Electrolyser sizing summary
    table_data.append(['**ELECTROLYSER SIZING**', '', '', '', ''])
    table_data.append(['Power (MW)', 'Net Profit (€)', 'H₂ (tonnes)', 
                      'Capacity Factor', 'H₂ Cost (€/kg)'])
    for _, row in df_ely_sizing.iterrows():
        table_data.append([
            f"{row['ely_power_mw']:.1f}",
            f"{row['net_profit_eur']:,.0f}",
            f"{row['total_h2_tonnes']:.1f}",
            f"{row['ely_capacity_factor']:.1%}",
            f"{row['h2_cost_eur_per_kg']:.2f}"
        ])
    
    # Time windows summary
    if df_time_windows:
        table_data.append(['', '', '', '', ''])
        table_data.append(['**TIME WINDOWS**', '', '', '', ''])
        
        for df_tw in df_time_windows:
            param_name = df_tw['parameter'].iloc[0]
            table_data.append([f'{param_name}', 'Net Profit (€)', 'H₂ (tonnes)', 
                              'Ely CF', 'PV Util.'])
            for _, row in df_tw.iterrows():
                table_data.append([
                    f"{row['value']}",
                    f"{row['net_profit_eur']:,.0f}",
                    f"{row['total_h2_tonnes']:.1f}",
                    f"{row['ely_capacity_factor']:.1%}",
                    f"{row['pv_utilization']:.1%}"
                ])
            table_data.append(['', '', '', '', ''])
    
    # Create table
    table = ax.table(cellText=table_data, cellLoc='left', loc='center',
                    colWidths=[0.2, 0.2, 0.2, 0.2, 0.2])
    
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 2)
    
    # Style header rows
    for i, row_data in enumerate(table_data):
        if row_data[0].startswith('**'):
            for j in range(5):
                table[(i, j)].set_facecolor('#4CAF50')
                table[(i, j)].set_text_props(weight='bold', color='white')
    
    plt.title('Comprehensive Sensitivity Analysis Summary', 
             fontsize=16, fontweight='bold', pad=20)
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    
    return fig


def run_complete_sensitivity_analysis(pv_profile, spot_prices, timestamps,
                                      base_battery_params, base_time_windows, 
                                      base_electrolyser_params,
                                      save_dir='sensitivity_analysis'):
    """
    Run complete sensitivity analysis and generate all plots
    
    Args:
        pv_profile: PV production profile [MW]
        spot_prices: Spot price array [€/MWh]
        timestamps: Timestamp array
        base_battery_params: Base battery parameters
        base_time_windows: Base time windows
        base_electrolyser_params: Base electrolyser parameters
        save_dir: Directory to save results
    
    Returns:
        Dictionary with all sensitivity results
    """
    import os
    os.makedirs(save_dir, exist_ok=True)
    
    analyzer = SensitivityAnalyzer(base_battery_params, base_time_windows, 
                                   base_electrolyser_params)
    
    results = {}
    
    print("1. Battery sizing sensitivity...")
    df_battery = analyzer.battery_sizing_sensitivity(
        pv_profile, spot_prices, timestamps,
        capacity_values_mwh=[5, 10, 15, 20, 30, 40, 50]
    )
    results['battery_sizing'] = df_battery
    df_battery.to_csv(os.path.join(save_dir, 'battery_sizing_sensitivity.csv'), index=False)
    
    print("2. Electrolyser sizing sensitivity...")
    df_ely = analyzer.electrolyser_sizing_sensitivity(
        pv_profile, spot_prices, timestamps,
        power_values_mw=[2, 3, 5, 7, 10, 12, 15]
    )
    results['electrolyser_sizing'] = df_ely
    df_ely.to_csv(os.path.join(save_dir, 'electrolyser_sizing_sensitivity.csv'), index=False)
    
    print("3. Time window sensitivity...")
    time_window_params = [
        ('pv_charge_start', [8, 9, 10, 11, 12]),
        ('pv_charge_end', [14, 15, 16, 17, 18]),
        ('arbitrage_discharge_start', [15, 16, 17, 18]),
        ('arbitrage_discharge_end', [21, 22, 23, 24]),
        ('electrolyser_start', [4, 5, 6, 7]),
        ('electrolyser_end', [9, 10, 11, 12]),
    ]
    
    results['time_windows'] = []
    for param_name, param_values in time_window_params:
        print(f"  - {param_name}...")
        df_tw = analyzer.time_window_sensitivity(
            pv_profile, spot_prices, timestamps,
            param_name, param_values
        )
        results['time_windows'].append(df_tw)
        df_tw.to_csv(os.path.join(save_dir, f'tw_sensitivity_{param_name}.csv'), index=False)
        
        # Plot individual parameter
        fig = plot_single_parameter_sensitivity(
            df_tw, param_name, 
            save_path=os.path.join(save_dir, f'plot_tw_{param_name}.png')
        )
        plt.close(fig)
    
    print("4. Two-parameter sensitivity (capacity vs power)...")
    df_2param = analyzer.two_parameter_sensitivity(
        pv_profile, spot_prices, timestamps,
        'E_bat_max', [10, 20, 30, 40, 50],
        'P_charge_max', [5, 10, 15, 20, 25],
        param_type='battery'
    )
    results['capacity_vs_power'] = df_2param
    df_2param.to_csv(os.path.join(save_dir, 'capacity_vs_power_sensitivity.csv'), index=False)
    
    # Plot heatmap
    fig = plot_two_parameter_heatmap(
        df_2param, 'E_bat_max', 'P_charge_max', 'net_profit_eur',
        save_path=os.path.join(save_dir, 'heatmap_capacity_vs_power.png')
    )
    plt.close(fig)
    
    print("5. Generating summary table...")
    fig_table = plot_comprehensive_sensitivity_table(
        df_battery, df_ely, results['time_windows'],
        save_path=os.path.join(save_dir, 'sensitivity_summary_table.png')
    )
    plt.close(fig_table)
    
    print(f"Sensitivity analysis complete! Results saved to {save_dir}/")
    
    return results

