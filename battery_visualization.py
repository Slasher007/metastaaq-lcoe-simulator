"""
Visualization functions for Battery Energy Management System results
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
from matplotlib.patches import Rectangle
import calendar


def plot_soc_profile(df_results, time_window_days=7, start_day=0, time_windows=None, 
                     battery_params=None, save_path=None):
    """
    Plot battery State of Charge profile over time
    
    Args:
        df_results: DataFrame with simulation results
        time_window_days: Number of days to display (for zoomed view)
        start_day: Starting day for the window
        time_windows: Dict of operational time windows (for shading)
        battery_params: Dict of battery parameters
        save_path: Optional path to save figure
    
    Returns:
        matplotlib Figure
    """
    fig, ax = plt.subplots(figsize=(14, 6))
    
    # Select time window
    hours_to_display = time_window_days * 24
    start_idx = start_day * 24
    end_idx = start_idx + hours_to_display
    
    df_window = df_results.iloc[start_idx:end_idx].copy()
    
    # Plot SoC
    ax.plot(df_window['timestamp'], df_window['soc'] * 100, 
            linewidth=2, color='blue', label='State of Charge')
    
    # Add constraint lines
    if battery_params:
        soc_min = battery_params.get('SoC_min', 0.1) * 100
        soc_max = battery_params.get('SoC_max', 1.0) * 100
        ax.axhline(y=soc_min, color='red', linestyle='--', linewidth=1.5, 
                   alpha=0.7, label=f'Min SoC ({soc_min:.0f}%)')
        ax.axhline(y=soc_max, color='green', linestyle='--', linewidth=1.5, 
                   alpha=0.7, label=f'Max SoC ({soc_max:.0f}%)')
    
    # Shade operational windows
    if time_windows:
        _add_time_window_shading(ax, df_window, time_windows)
    
    ax.set_xlabel('Time', fontsize=12, fontweight='bold')
    ax.set_ylabel('State of Charge (%)', fontsize=12, fontweight='bold')
    ax.set_title(f'Battery State of Charge Profile (Days {start_day} to {start_day + time_window_days})', 
                 fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best')
    ax.set_ylim(0, 105)
    
    # Format x-axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
    plt.xticks(rotation=45, ha='right')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    
    return fig


def plot_power_flows(df_results, time_window_days=7, start_day=0, save_path=None):
    """
    Plot power flows (charging, discharging, electrolyser, curtailment)
    
    Returns:
        matplotlib Figure
    """
    fig, axes = plt.subplots(3, 1, figsize=(14, 12), sharex=True)
    
    # Select time window
    hours_to_display = time_window_days * 24
    start_idx = start_day * 24
    end_idx = start_idx + hours_to_display
    
    df_window = df_results.iloc[start_idx:end_idx].copy()
    
    # Plot 1: Charging and Discharging
    ax1 = axes[0]
    
    # Separate charging by source based on window
    # Create temporary series for plotting
    pv_charge = df_window.apply(lambda x: x['battery_charge_mw'] if x['window_type'] == 'pv_charge' else 0, axis=1)
    grid_charge = df_window.apply(lambda x: x['battery_charge_mw'] if x['window_type'] == 'night_charge' else 0, axis=1)
    
    # Separate discharging by destination
    grid_discharge = df_window.apply(lambda x: x['battery_discharge_mw'] if x['window_type'] == 'arbitrage_discharge' else 0, axis=1)
    # ely_discharge is handled in Plot 2
    
    ax1.fill_between(df_window['timestamp'], 0, pv_charge, 
                     color='gold', alpha=0.7, label='PV to Battery')
    ax1.fill_between(df_window['timestamp'], 0, grid_charge, 
                     color='green', alpha=0.7, label='Grid to Battery')
    ax1.fill_between(df_window['timestamp'], 0, -grid_discharge, 
                     color='blue', alpha=0.7, label='Battery to Grid (Arbitrage)')
    ax1.set_ylabel('Power (MW)', fontsize=11, fontweight='bold')
    ax1.set_title('Battery Charging and Discharging', fontsize=12, fontweight='bold')
    ax1.legend(loc='upper right')
    ax1.grid(True, alpha=0.3)
    ax1.axhline(y=0, color='black', linewidth=0.8)
    
    # Plot 2: Electrolyser Operation
    ax2 = axes[1]
    
    # Electrolyser supply from battery
    ely_discharge = df_window.apply(lambda x: x['battery_discharge_mw'] if x['window_type'] == 'electrolyser' else 0, axis=1)
    
    ax2.fill_between(df_window['timestamp'], 0, ely_discharge, 
                     color='purple', alpha=0.7, label='Battery to Electrolyser')
    ax2.fill_between(df_window['timestamp'], 0, -df_window['ely_shortage_mw'], 
                     color='red', alpha=0.5, label='Electrolyser Shortage')
    ax2.set_ylabel('Power (MW)', fontsize=11, fontweight='bold')
    ax2.set_title('Electrolyser Power Supply', fontsize=12, fontweight='bold')
    ax2.legend(loc='upper right')
    ax2.grid(True, alpha=0.3)
    ax2.axhline(y=0, color='black', linewidth=0.8)
    
    # Plot 3: PV Production and Curtailment
    ax3 = axes[2]
    ax3.fill_between(df_window['timestamp'], 0, df_window['pv_available_mw'], 
                     color='orange', alpha=0.5, label='PV Available')
    ax3.fill_between(df_window['timestamp'], 0, df_window['pv_curtailed_mw'], 
                     color='gray', alpha=0.7, label='PV Curtailed')
    ax3.set_xlabel('Time', fontsize=12, fontweight='bold')
    ax3.set_ylabel('Power (MW)', fontsize=11, fontweight='bold')
    ax3.set_title('PV Production and Curtailment', fontsize=12, fontweight='bold')
    ax3.legend(loc='upper right')
    ax3.grid(True, alpha=0.3)
    
    # Format x-axis
    ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.xticks(rotation=45, ha='right')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    
    return fig


def plot_economics_breakdown(df_results, time_window_days=30, start_day=0, save_path=None):
    """
    Plot economics breakdown (revenue, costs, net cashflow)
    
    Returns:
        matplotlib Figure
    """
    fig, axes = plt.subplots(2, 1, figsize=(14, 10), sharex=True)
    
    # Select time window
    hours_to_display = time_window_days * 24
    start_idx = start_day * 24
    end_idx = start_idx + hours_to_display
    
    df_window = df_results.iloc[start_idx:end_idx].copy()
    
    # Aggregate by day for clearer visualization
    df_daily = df_window.copy()
    df_daily['date'] = df_daily['timestamp'].dt.date
    df_daily_agg = df_daily.groupby('date').agg({
        'revenue_arbitrage': 'sum',
        'cost_charging': 'sum',
        'cost_penalties': 'sum',
        'net_cashflow': 'sum',
        'spot_price_eur_mwh': 'mean'
    }).reset_index()
    df_daily_agg['date'] = pd.to_datetime(df_daily_agg['date'])
    
    # Plot 1: Revenue and Costs
    ax1 = axes[0]
    width = 0.7
    x_pos = np.arange(len(df_daily_agg))
    
    ax1.bar(x_pos, df_daily_agg['revenue_arbitrage'], width, 
            color='green', alpha=0.7, label='Revenue (Arbitrage)')
    ax1.bar(x_pos, -df_daily_agg['cost_charging'], width, 
            color='red', alpha=0.7, label='Cost (Grid Charging)')
    ax1.bar(x_pos, -df_daily_agg['cost_penalties'], width, 
            bottom=-df_daily_agg['cost_charging'],
            color='darkred', alpha=0.7, label='Penalties')
    
    ax1.set_ylabel('Daily Cashflow (€)', fontsize=11, fontweight='bold')
    ax1.set_title('Daily Revenue and Costs', fontsize=12, fontweight='bold')
    ax1.legend(loc='upper right')
    ax1.grid(True, alpha=0.3, axis='y')
    ax1.axhline(y=0, color='black', linewidth=1)
    
    # Plot 2: Net Cashflow and Spot Price
    ax2 = axes[1]
    ax2_twin = ax2.twinx()
    
    # Net cashflow bars
    colors = ['green' if x > 0 else 'red' for x in df_daily_agg['net_cashflow']]
    ax2.bar(x_pos, df_daily_agg['net_cashflow'], width, 
            color=colors, alpha=0.7, label='Net Cashflow')
    
    # Spot price line
    ax2_twin.plot(x_pos, df_daily_agg['spot_price_eur_mwh'], 
                  color='blue', linewidth=2, marker='o', markersize=4,
                  label='Avg Spot Price')
    
    ax2.set_xlabel('Date', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Daily Net Cashflow (€)', fontsize=11, fontweight='bold')
    ax2_twin.set_ylabel('Avg Spot Price (€/MWh)', fontsize=11, fontweight='bold', color='blue')
    ax2_twin.tick_params(axis='y', labelcolor='blue')
    ax2.set_title('Daily Net Cashflow and Spot Price', fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3, axis='y')
    ax2.axhline(y=0, color='black', linewidth=1)
    
    # X-axis labels
    ax2.set_xticks(x_pos[::max(1, len(x_pos)//10)])  # Show ~10 labels
    ax2.set_xticklabels([d.strftime('%Y-%m-%d') for d in df_daily_agg['date'].iloc[::max(1, len(x_pos)//10)]], 
                        rotation=45, ha='right')
    
    # Combine legends
    lines1, labels1 = ax2.get_legend_handles_labels()
    lines2, labels2 = ax2_twin.get_legend_handles_labels()
    ax2.legend(lines1 + lines2, labels1 + labels2, loc='upper right')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    
    return fig


def plot_monthly_summary(summary, save_path=None):
    """
    Plot monthly summary statistics
    
    Args:
        summary: Dictionary with summary statistics from optimizer
    
    Returns:
        matplotlib Figure
    """
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # Summary metrics
    metrics = [
        ('Energy Flows (MWh)', [
            ('PV Available', summary['total_pv_available_mwh']),
            ('PV to Battery', summary['total_pv_to_battery_mwh']),
            ('PV Curtailed', summary['total_pv_curtailed_mwh']),
            ('Grid to Battery', summary['total_grid_to_battery_mwh']),
            ('Battery to Grid', summary['total_battery_to_grid_mwh']),
            ('Battery to Ely', summary['total_battery_to_ely_mwh']),
        ]),
        ('Economics (€)', [
            ('Revenue', summary['total_revenue_eur']),
            ('Cost', -summary['total_cost_eur']),
            ('Penalties', -summary['total_penalties_eur']),
            ('Net Profit', summary['net_profit_eur']),
        ]),
        ('Battery Stats', [
            ('Avg SoC (%)', summary['avg_soc'] * 100),
            ('Min SoC (%)', summary['min_soc'] * 100),
            ('Max SoC (%)', summary['max_soc'] * 100),
            ('Equivalent Cycles', summary['equivalent_cycles']),
        ]),
        ('Electrolyser Stats', [
            ('H₂ Production (tonnes)', summary['total_h2_production_tonnes']),
            ('Operating Hours', summary['ely_operating_hours']),
            ('Shortage Hours', summary['ely_shortage_hours']),
            ('Capacity Factor (%)', summary['ely_capacity_factor'] * 100),
        ]),
    ]
    
    for idx, (title, data) in enumerate(metrics):
        ax = axes[idx // 2, idx % 2]
        
        labels = [item[0] for item in data]
        values = [item[1] for item in data]
        
        colors = ['green' if v >= 0 else 'red' for v in values]
        
        y_pos = np.arange(len(labels))
        ax.barh(y_pos, values, color=colors, alpha=0.7)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels)
        ax.set_xlabel('Value', fontsize=10, fontweight='bold')
        ax.set_title(title, fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='x')
        ax.axvline(x=0, color='black', linewidth=1)
        
        # Add value labels
        for i, v in enumerate(values):
            ax.text(v, i, f'  {v:.1f}', va='center', fontsize=9, fontweight='bold')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    
    return fig


def plot_yearly_cashflow(df_results, save_path=None):
    """
    Plot yearly cashflow breakdown by month
    
    Returns:
        matplotlib Figure
    """
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Aggregate by month
    df_monthly = df_results.copy()
    df_monthly['month'] = df_monthly['timestamp'].dt.to_period('M')
    df_monthly_agg = df_monthly.groupby('month').agg({
        'revenue_arbitrage': 'sum',
        'cost_charging': 'sum',
        'cost_penalties': 'sum',
        'net_cashflow': 'sum',
    }).reset_index()
    
    df_monthly_agg['month_str'] = df_monthly_agg['month'].astype(str)
    
    # Plot stacked bars
    x_pos = np.arange(len(df_monthly_agg))
    width = 0.6
    
    ax.bar(x_pos, df_monthly_agg['revenue_arbitrage'], width, 
           color='green', alpha=0.7, label='Revenue')
    ax.bar(x_pos, -df_monthly_agg['cost_charging'], width, 
           color='red', alpha=0.7, label='Charging Cost')
    ax.bar(x_pos, -df_monthly_agg['cost_penalties'], width,
           bottom=-df_monthly_agg['cost_charging'],
           color='darkred', alpha=0.7, label='Penalties')
    
    # Add net cashflow line
    ax.plot(x_pos, df_monthly_agg['net_cashflow'], 
            color='blue', linewidth=2.5, marker='o', markersize=8,
            label='Net Cashflow', zorder=10)
    
    ax.set_xticks(x_pos)
    ax.set_xticklabels(df_monthly_agg['month_str'], rotation=45, ha='right')
    ax.set_xlabel('Month', fontsize=12, fontweight='bold')
    ax.set_ylabel('Cashflow (€)', fontsize=12, fontweight='bold')
    ax.set_title('Monthly Cashflow Breakdown', fontsize=14, fontweight='bold')
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3, axis='y')
    ax.axhline(y=0, color='black', linewidth=1)
    
    # Add total annotation
    total_revenue = df_monthly_agg['revenue_arbitrage'].sum()
    total_cost = df_monthly_agg['cost_charging'].sum()
    total_penalties = df_monthly_agg['cost_penalties'].sum()
    net_profit = total_revenue - total_cost - total_penalties
    
    textstr = f'Annual Summary:\n'
    textstr += f'Revenue: {total_revenue:,.0f} €\n'
    textstr += f'Cost: {total_cost:,.0f} €\n'
    textstr += f'Penalties: {total_penalties:,.0f} €\n'
    textstr += f'Net Profit: {net_profit:,.0f} €'
    
    ax.text(0.02, 0.98, textstr, transform=ax.transAxes,
            verticalalignment='top', bbox=dict(boxstyle='round', 
            facecolor='wheat', alpha=0.8), fontsize=10, fontweight='bold')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    
    return fig


def plot_hydrogen_production(df_results, electrolyser_params, save_path=None):
    """
    Plot hydrogen production statistics
    
    Returns:
        matplotlib Figure
    """
    fig, axes = plt.subplots(2, 1, figsize=(12, 10))
    
    # Aggregate by day
    df_daily = df_results.copy()
    
    # Reconstruct ely_power_mw for aggregation
    df_daily['ely_power_mw'] = df_daily.apply(
        lambda row: row['battery_discharge_mw'] if row['window_type'] == 'electrolyser' else 0, axis=1
    )
    
    df_daily['date'] = df_daily['timestamp'].dt.date
    df_daily_agg = df_daily.groupby('date').agg({
        'ely_h2_production_kg': 'sum',
        'ely_power_mw': 'mean',
        'ely_shortage_mw': 'sum',
    }).reset_index()
    df_daily_agg['date'] = pd.to_datetime(df_daily_agg['date'])
    
    # Plot 1: Daily H2 production
    ax1 = axes[0]
    ax1.bar(df_daily_agg['date'], df_daily_agg['ely_h2_production_kg'], 
            color='purple', alpha=0.7, width=0.8)
    ax1.set_ylabel('H₂ Production (kg/day)', fontsize=11, fontweight='bold')
    ax1.set_title('Daily Hydrogen Production', fontsize=12, fontweight='bold')
    ax1.grid(True, alpha=0.3, axis='y')
    
    # Add target line (if electrolyser runs full-time)
    target_h2_per_day = (electrolyser_params['P_ely'] * 1000 * 
                         (electrolyser_params.get('ely_hours_per_day', 5)) / 
                         electrolyser_params['specific_consumption'])
    ax1.axhline(y=target_h2_per_day, color='red', linestyle='--', 
                linewidth=2, label=f'Target ({target_h2_per_day:.1f} kg/day)')
    ax1.legend(loc='best')
    
    # Plot 2: Electrolyser capacity factor
    ax2 = axes[1]
    df_monthly = df_results.copy()
    
    # Reconstruct ely_power_mw
    df_monthly['ely_power_mw'] = df_monthly.apply(
        lambda row: row['battery_discharge_mw'] if row['window_type'] == 'electrolyser' else 0, axis=1
    )
    
    df_monthly['month'] = df_monthly['timestamp'].dt.to_period('M')
    df_monthly_agg = df_monthly.groupby('month').agg({
        'ely_power_mw': 'mean',
        'ely_shortage_mw': 'mean',
    }).reset_index()
    df_monthly_agg['month_str'] = df_monthly_agg['month'].astype(str)
    df_monthly_agg['capacity_factor'] = (df_monthly_agg['ely_power_mw'] / 
                                          electrolyser_params['P_ely'] * 100)
    
    x_pos = np.arange(len(df_monthly_agg))
    ax2.bar(x_pos, df_monthly_agg['capacity_factor'], 
            color='blue', alpha=0.7, width=0.6)
    ax2.set_xticks(x_pos)
    ax2.set_xticklabels(df_monthly_agg['month_str'], rotation=45, ha='right')
    ax2.set_xlabel('Month', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Capacity Factor (%)', fontsize=11, fontweight='bold')
    ax2.set_title('Monthly Electrolyser Capacity Factor', fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3, axis='y')
    ax2.set_ylim(0, 100)
    
    # Add value labels
    for i, v in enumerate(df_monthly_agg['capacity_factor']):
        ax2.text(i, v + 2, f'{v:.1f}%', ha='center', fontsize=9, fontweight='bold')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    
    return fig


def _add_time_window_shading(ax, df_window, time_windows):
    """
    Add colored shading to plot to indicate operational time windows
    """
    window_colors = {
        'pv_charge': ('gold', 'PV Charge'),
        'arbitrage_discharge': ('lightblue', 'Arbitrage'),
        'night_charge': ('lightgreen', 'Night Charge'),
        'electrolyser': ('lavender', 'Electrolyser'),
        'idle': ('lightgray', 'Idle'),
    }
    
    # Get unique window types in the data
    unique_windows = df_window['window_type'].unique()
    
    # Add shading for each contiguous window period
    prev_window = None
    start_time = None
    
    for i, row in df_window.iterrows():
        current_window = row['window_type']
        
        if current_window != prev_window:
            # End previous window
            if prev_window and start_time and prev_window in window_colors:
                color, label = window_colors[prev_window]
                ax.axvspan(start_time, row['timestamp'], 
                          alpha=0.2, color=color)
            
            # Start new window
            start_time = row['timestamp']
            prev_window = current_window
    
    # Close last window
    if prev_window and start_time and prev_window in window_colors:
        color, label = window_colors[prev_window]
        ax.axvspan(start_time, df_window.iloc[-1]['timestamp'], 
                  alpha=0.2, color=color)
    
    # Add legend patches for windows
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor=window_colors[w][0], alpha=0.3, 
                            label=window_colors[w][1])
                      for w in unique_windows if w in window_colors]
    
    if legend_elements:
        # Add to existing legend
        handles, labels = ax.get_legend_handles_labels()
        ax.legend(handles=handles + legend_elements, labels=labels + [e.get_label() for e in legend_elements],
                 loc='best', fontsize=9)


def create_comprehensive_report(df_results, summary, battery_params, time_windows, 
                                electrolyser_params, save_dir='battery_reports'):
    """
    Create a comprehensive PDF report with all visualizations
    
    Args:
        df_results: Simulation results DataFrame
        summary: Summary statistics dict
        battery_params: Battery parameters dict
        time_windows: Time windows dict
        electrolyser_params: Electrolyser parameters dict
        save_dir: Directory to save report figures
    
    Returns:
        List of figure paths
    """
    import os
    os.makedirs(save_dir, exist_ok=True)
    
    figures = []
    
    # 1. SoC Profile (first week)
    fig1 = plot_soc_profile(df_results, time_window_days=7, start_day=0, 
                           time_windows=time_windows, battery_params=battery_params,
                           save_path=os.path.join(save_dir, '01_soc_week1.png'))
    figures.append('01_soc_week1.png')
    plt.close(fig1)
    
    # 2. SoC Profile (summer week)
    fig2 = plot_soc_profile(df_results, time_window_days=7, start_day=180, 
                           time_windows=time_windows, battery_params=battery_params,
                           save_path=os.path.join(save_dir, '02_soc_summer.png'))
    figures.append('02_soc_summer.png')
    plt.close(fig2)
    
    # 3. Power Flows (first week)
    fig3 = plot_power_flows(df_results, time_window_days=7, start_day=0,
                           save_path=os.path.join(save_dir, '03_power_flows_week1.png'))
    figures.append('03_power_flows_week1.png')
    plt.close(fig3)
    
    # 4. Economics (first month)
    fig4 = plot_economics_breakdown(df_results, time_window_days=30, start_day=0,
                                   save_path=os.path.join(save_dir, '04_economics_month1.png'))
    figures.append('04_economics_month1.png')
    plt.close(fig4)
    
    # 5. Monthly Summary
    fig5 = plot_monthly_summary(summary, 
                               save_path=os.path.join(save_dir, '05_monthly_summary.png'))
    figures.append('05_monthly_summary.png')
    plt.close(fig5)
    
    # 6. Yearly Cashflow
    fig6 = plot_yearly_cashflow(df_results, 
                                save_path=os.path.join(save_dir, '06_yearly_cashflow.png'))
    figures.append('06_yearly_cashflow.png')
    plt.close(fig6)
    
    # 7. Hydrogen Production
    fig7 = plot_hydrogen_production(df_results, electrolyser_params,
                                   save_path=os.path.join(save_dir, '07_hydrogen_production.png'))
    figures.append('07_hydrogen_production.png')
    plt.close(fig7)
    
    return figures

