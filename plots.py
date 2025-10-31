"""
Plotting functions for the MetaSTAAQ Dashboard
"""

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import calendar
from matplotlib.patches import Rectangle
from config import PLOT_COLORS
from collections import defaultdict


def create_monthly_price_analysis_plot(data_content):
    """Create monthly price analysis bar chart with overall average line"""
    # Ensure 'Date' is datetime and extract year and month
    data_content['Date'] = pd.to_datetime(data_content['Date'])
    data_content['Year'] = data_content['Date'].dt.year
    data_content['Month'] = data_content['Date'].dt.month

    # Group by Year and Month and calculate the mean price
    monthly_avg_price = data_content.groupby(['Year', 'Month'])['Prix'].mean().reset_index()

    # Map month numbers to month names for better plotting
    monthly_avg_price['Month_Name'] = monthly_avg_price['Month'].apply(lambda x: calendar.month_name[x])

    # Pivot the table for plotting: Years as columns, Months as index
    pivot_table = monthly_avg_price.pivot(index='Month_Name', columns='Year', values='Prix')

    # Ensure the order of months is correct
    month_order = list(calendar.month_name)[1:]
    pivot_table = pivot_table.reindex(month_order)

    # Calculate the overall average price per month across all years
    overall_monthly_avg = pivot_table.mean(axis=1)

    # Plot the bar chart
    fig_price, ax_price = plt.subplots(figsize=(12, 6))
    ax_price = pivot_table.plot(kind='bar', figsize=(12, 6), ax=ax_price)

    # Add the line plot for the overall monthly average
    overall_monthly_avg.plot(ax=ax_price, color='red', linestyle='--', marker='o', label='Overall Monthly Average')

    # Add value labels to the points on the line plot
    for i, v in enumerate(overall_monthly_avg):
        ax_price.text(i, v, f"{v:.1f}", ha='center', va='bottom')

    plt.title('Average Monthly Price per Year with Overall Monthly Average')
    plt.xlabel('Month')
    plt.ylabel('Average Price (€/MWh)')
    plt.xticks(rotation=45, ha='right')
    plt.legend(title='Year')
    plt.tight_layout()
    
    return fig_price


def create_price_distribution_box_plot(data_content):
    """Create box plot showing price distribution by month"""
    fig_box, ax_box = plt.subplots(figsize=(12, 6))

    # Create box plot for price distribution by month
    box_data = []
    box_labels = []
    month_order = list(calendar.month_name)[1:]  # January to December

    for month_num in range(1, 13):
        month_name = calendar.month_name[month_num]
        # Get all prices for this month across all years
        month_data = data_content[data_content['Month'] == month_num]['Prix']
        if len(month_data) > 0:
            box_data.append(month_data)
            box_labels.append(month_name)

    # Create the box plot
    bp = ax_box.boxplot(box_data, labels=box_labels, patch_artist=True)

    # Color the boxes with different colors
    colors = plt.cm.Set3(range(len(box_data)))
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)

    # Customize the plot
    ax_box.set_title('Electricity Price Distribution by Month', fontweight='bold', fontsize=14)
    ax_box.set_xlabel('Month')
    ax_box.set_ylabel('Price (€/MWh)')
    ax_box.grid(True, alpha=0.3)

    # Rotate x-axis labels for better readability
    plt.xticks(rotation=45, ha='right')

    # Add statistics text box
    stats_text = f"Dataset: {len(data_content)} data points\nYears: {sorted(data_content['Year'].unique())}"
    ax_box.text(0.02, 0.98, stats_text, transform=ax_box.transAxes, 
               verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

    plt.tight_layout()
    return fig_box


def create_service_ratios_chart(monthly_service_ratios):
    """Create bar chart for monthly service ratios"""
    fig_service, ax_service = plt.subplots(figsize=(12, 4))
    bars = ax_service.bar(range(len(monthly_service_ratios)), 
                         list(monthly_service_ratios.values()),
                         color=['lightgreen' if ratio >= 0.9 else 'orange' if ratio >= 0.5 else 'lightcoral' 
                               for ratio in monthly_service_ratios.values()])

    # Add value labels on bars
    for i, (month, ratio) in enumerate(monthly_service_ratios.items()):
        ax_service.text(i, ratio + 0.01, f'{ratio:.0%}', 
                       ha='center', va='bottom', fontweight='bold', fontsize=10)

    ax_service.set_xticks(range(len(monthly_service_ratios)))
    ax_service.set_xticklabels([month[:3] for month in monthly_service_ratios.keys()], rotation=45)
    ax_service.set_ylabel('Service Ratio')
    avg_sr = sum(monthly_service_ratios.values()) / len(monthly_service_ratios) if monthly_service_ratios else 0
    ax_service.set_title(f'Monthly Service Ratios (Avg: {avg_sr:.1%})\n(Green: ≥90%, Orange: 50-90%, Red: <50%)')
    ax_service.set_ylim(0, 1.1)
    ax_service.grid(True, alpha=0.3)
    plt.tight_layout()
    
    return fig_service


def create_operating_hours_chart(df_result, extended_info, strategy_type, pv_energy_mwh=None, electrolyser_power=None, monthly_service_ratios=None):
    """Create operating hours chart with PV/Spot/PPA breakdown"""
    fig1, ax1 = plt.subplots(figsize=(12, 6))
    df_plot = df_result.T
    monthly_avg = df_plot.mean(axis=1)
    
    # Create separate dataframes for PV, spot and PPA hours
    pv_hours_data = pd.DataFrame(index=df_plot.index, columns=df_plot.columns, dtype=float)
    spot_hours_data = pd.DataFrame(index=df_plot.index, columns=df_plot.columns, dtype=float)
    ppa_hours_data = pd.DataFrame(index=df_plot.index, columns=df_plot.columns, dtype=float)
    
    for year in df_plot.columns:
        for month in df_plot.index:
            # Calculate PV hours from energy if provided
            if pv_energy_mwh and electrolyser_power and month in pv_energy_mwh:
                pv_hours = pv_energy_mwh[month] / electrolyser_power if electrolyser_power > 0 else 0
                pv_hours_data.loc[month, year] = pv_hours
            else:
                pv_hours_data.loc[month, year] = 0
            
            if str(year) in extended_info and month in extended_info[str(year)]:
                info = extended_info[str(year)][month]
                spot_hours_data.loc[month, year] = info.get('spot_hours', 0)
                ppa_hours_data.loc[month, year] = info.get('ppa_hours', 0)
            else:
                # Fallback: use total hours for spot, no PPA
                spot_hours_data.loc[month, year] = df_plot.loc[month, year]
                ppa_hours_data.loc[month, year] = 0

            # If Service Ratio-Based and monthly_service_ratios provided, enforce forced total hours:
            # - Keep PV hours anchored to pv_energy_mwh / electrolyser_power
            # - Scale Spot/PPA proportionally to fill the remaining forced hours
            if strategy_type == "Service Ratio-Based" and monthly_service_ratios is not None:
                ratio = monthly_service_ratios.get(month, 1.0)
                days_per_month = {"January": 31, "February": 28, "March": 31, "April": 30, "May": 31, "June": 30,
                                  "July": 31, "August": 31, "September": 30, "October": 31, "November": 30, "December": 31}
                forced_total = int(round(days_per_month.get(month, 30) * 24 * ratio))

                pv_val = float(pv_hours_data.loc[month, year])
                spot_val = float(spot_hours_data.loc[month, year])
                ppa_val = float(ppa_hours_data.loc[month, year])
                grid_total = spot_val + ppa_val

                # Integer allocation to avoid off-by-one totals in labels
                if forced_total < 0:
                    forced_total = 0
                pv_int = int(round(pv_val))
                if pv_int >= forced_total:
                    pv_hours_data.loc[month, year] = float(forced_total)
                    spot_hours_data.loc[month, year] = 0.0
                    ppa_hours_data.loc[month, year] = 0.0
                else:
                    remaining = forced_total - pv_int
                    if grid_total > 0:
                        spot_prop = spot_val / grid_total
                        # Allocate integer hours proportionally
                        spot_int = int(round(remaining * spot_prop))
                        # Ensure bounds
                        if spot_int < 0:
                            spot_int = 0
                        if spot_int > remaining:
                            spot_int = remaining
                        ppa_int = remaining - spot_int
                        pv_hours_data.loc[month, year] = float(pv_int)
                        spot_hours_data.loc[month, year] = float(spot_int)
                        ppa_hours_data.loc[month, year] = float(ppa_int)
                    else:
                        # No grid hours available; assign PV and leave remainder unfilled
                        pv_hours_data.loc[month, year] = float(pv_int)
                        spot_hours_data.loc[month, year] = 0.0
                        ppa_hours_data.loc[month, year] = 0.0

    if len(df_plot.columns) == 1:
        # Single year - create stacked bars with PV/Spot/PPA
        year = df_plot.columns[0]
        x_pos = np.arange(len(df_plot.index))
        width = 0.6
        
        pv_values = pv_hours_data[year].values
        spot_values = spot_hours_data[year].values
        ppa_values = ppa_hours_data[year].values
        
        # Stack: PV at bottom, Spot in middle, PPA on top
        ax1.bar(x_pos, pv_values, width, label=f'{year} (PV)', color=PLOT_COLORS.get('pv', 'gold'), alpha=0.8)
        ax1.bar(x_pos, spot_values, width, bottom=pv_values, label=f'{year} (Spot)', color=PLOT_COLORS['spot'], alpha=0.8)
        ax1.bar(x_pos, ppa_values, width, bottom=pv_values + spot_values, label=f'{year} (PPA)', color=PLOT_COLORS['ppa'], alpha=0.5)
        
        # Add value labels
        for j in range(len(x_pos)):
            pv_val = pv_values[j]
            spot_val = spot_values[j]
            ppa_val = ppa_values[j]
            total = pv_val + spot_val + ppa_val
            if total > 0:
                ax1.text(x_pos[j], total + 5, f'{int(total)}h', ha='center', va='bottom', fontsize=9, fontweight='bold')
                if pv_val > 20:
                    ax1.text(x_pos[j], pv_val/2, f'PV:{int(pv_val)}', ha='center', va='center', fontsize=8, color='white', fontweight='bold')
                if spot_val > 20:
                    ax1.text(x_pos[j], pv_val + spot_val/2, f'S:{int(spot_val)}', ha='center', va='center', fontsize=8, color='white', fontweight='bold')
                if ppa_val > 20:
                    ax1.text(x_pos[j], pv_val + spot_val + ppa_val/2, f'P:{int(ppa_val)}', ha='center', va='center', fontsize=8, color='white', fontweight='bold')
    else:
        # Multi-year - show a single stacked bar per month using average values
        x_pos = np.arange(len(df_plot.index))
        width = 0.6
        
        # Compute average PV, spot and PPA hours across selected years per month
        pv_avg_values = pv_hours_data.mean(axis=1).values
        spot_avg_values = spot_hours_data.mean(axis=1).values
        ppa_avg_values = ppa_hours_data.mean(axis=1).values
        
        # Stack: PV at bottom, Spot in middle, PPA on top
        ax1.bar(x_pos, pv_avg_values, width, label='PV (avg)', color=PLOT_COLORS.get('pv', 'gold'), alpha=0.8)
        ax1.bar(x_pos, spot_avg_values, width, bottom=pv_avg_values, label='Spot (avg)', color=PLOT_COLORS['spot'], alpha=0.8)
        ax1.bar(x_pos, ppa_avg_values, width, bottom=pv_avg_values + spot_avg_values, label='PPA (avg)', color=PLOT_COLORS['ppa'], alpha=0.5)
        
        # Add value labels (same as single-year view)
        for j in range(len(x_pos)):
            pv_val = float(pv_avg_values[j]) if not np.isnan(pv_avg_values[j]) else 0.0
            spot_val = float(spot_avg_values[j]) if not np.isnan(spot_avg_values[j]) else 0.0
            ppa_val = float(ppa_avg_values[j]) if not np.isnan(ppa_avg_values[j]) else 0.0
            total = pv_val + spot_val + ppa_val
            if total > 0:
                ax1.text(x_pos[j], total + 5, f'{int(round(total))}h', ha='center', va='bottom', fontsize=9, fontweight='bold')
                if pv_val > 20:
                    ax1.text(x_pos[j], pv_val/2, f'PV:{int(round(pv_val))}', ha='center', va='center', fontsize=8, color='white', fontweight='bold')
                if spot_val > 20:
                    ax1.text(x_pos[j], pv_val + spot_val/2, f'S:{int(round(spot_val))}', ha='center', va='center', fontsize=8, color='white', fontweight='bold')
                if ppa_val > 20:
                    ax1.text(x_pos[j], pv_val + spot_val + ppa_val/2, f'P:{int(round(ppa_val))}', ha='center', va='center', fontsize=8, color='white', fontweight='bold')
    
    ax1.set_xticks(x_pos)
    ax1.set_xticklabels(df_plot.index, rotation=45, ha='right')
    ax1.set_ylabel('Hours')
    avg_sr = 0
    if monthly_service_ratios:
        avg_sr = sum(monthly_service_ratios.values()) / len(monthly_service_ratios)
    title_suffix = f" - Avg Service Ratio: {avg_sr:.1%}" if monthly_service_ratios else ""
    ax1.set_title(f'Operating Hours Chart ({strategy_type}){title_suffix}')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Add average line (without value labels on top)
    ax1.plot(x_pos, monthly_avg, color='red', linestyle='--', marker='o', linewidth=2, markersize=6, label='Average')
    
    handles, labels = ax1.get_legend_handles_labels()
    ax1.legend(handles, labels, loc='upper right')
    plt.tight_layout()
    
    return fig1


def create_energy_coverage_chart(df_plot_data, include_battery, battery_capacity_mwh, integrate_ppa, monthly_service_ratios=None, max_monthly_energy_mwh_by_month=None):
    """Create energy coverage stacked bar chart
    If max_monthly_energy_mwh_by_month is provided, percentages are computed relative
    to the full-month 24h energy baseline for each month; otherwise relative to row totals.
    """
    fig2, ax3 = plt.subplots(figsize=(12, 6))
    
    # Choose columns and colors based on battery inclusion
    if include_battery and battery_capacity_mwh > 0:
        plot_columns = ['PV', 'Spot Direct', 'Spot Battery'] + (['PPA'] if integrate_ppa else [])
        plot_colors = ['blue', 'darkgreen', 'lightgreen'] + (['red'] if integrate_ppa else [])
    else:
        plot_columns = ['PV', 'Spot'] + (['PPA'] if integrate_ppa else [])
        plot_colors = ['blue', 'green'] + (['red'] if integrate_ppa else [])
    
    # Build percentage dataframe for plotting (y-axis as %)
    percentages_df = df_plot_data[plot_columns].copy()
    if max_monthly_energy_mwh_by_month is not None:
        # Compute percentages against provided monthly maxima (e.g., 24h baseline)
        denom_series = pd.Series({m: max_monthly_energy_mwh_by_month.get(m, 0) for m in percentages_df.index})
        # Avoid zero denominators by falling back to row totals
        fallback_totals = percentages_df.sum(axis=1)
        safe_denom = denom_series.where(denom_series > 0, fallback_totals).replace(0, 1)
        percentages_df = (percentages_df.T / safe_denom).T * 100.0
        # Cap values at 100% to keep stacks within bounds
        percentages_df = percentages_df.clip(upper=100)
    else:
        row_totals = percentages_df.sum(axis=1).replace(0, 1)  # avoid division by zero
        percentages_df = (percentages_df.T / row_totals).T * 100.0

    percentages_df.plot(kind='bar', stacked=True, ax=ax3, color=plot_colors)
    
    # Add cumulative totals/coverage on top of bars
    for i, month in enumerate(df_plot_data.index):
        # Compute total energy for the month (MWh)
        if include_battery and battery_capacity_mwh > 0:
            total_energy = (df_plot_data.loc[month, 'PV'] +
                            df_plot_data.loc[month, 'Spot Direct'] +
                            df_plot_data.loc[month, 'Spot Battery'] +
                            (df_plot_data.loc[month, 'PPA'] if integrate_ppa else 0))
        else:
            total_energy = (df_plot_data.loc[month, 'PV'] +
                            df_plot_data.loc[month, 'Spot'] +
                            (df_plot_data.loc[month, 'PPA'] if integrate_ppa else 0))

        if total_energy > 0:
            if max_monthly_energy_mwh_by_month is not None:
                denom = max_monthly_energy_mwh_by_month.get(month, 0)
                coverage_pct = (total_energy / denom * 100.0) if denom and denom > 0 else 0.0
                label_text = f'{coverage_pct:.0f}%\n({total_energy:.1f})'
            else:
                label_text = f'{total_energy:.1f}'
            ax3.text(i, 102, label_text,
                     ha='center', va='bottom', fontsize=9, fontweight='bold',
                     color='black')
    
    # Add percentage labels inside bars with white text
    for i, month in enumerate(df_plot_data.index):
        if include_battery and battery_capacity_mwh > 0:
            pv_val = df_plot_data.loc[month, 'PV']
            spot_direct_val = df_plot_data.loc[month, 'Spot Direct']
            spot_battery_val = df_plot_data.loc[month, 'Spot Battery']
            ppa_val = df_plot_data.loc[month, 'PPA'] if integrate_ppa else 0

            total_plotted = pv_val + spot_direct_val + spot_battery_val + ppa_val

            if total_plotted > 0:
                # Percentages for positioning
                if max_monthly_energy_mwh_by_month is not None:
                    denom = max_monthly_energy_mwh_by_month.get(month, 0)
                    denom = denom if denom and denom > 0 else total_plotted
                    pv_pct = (pv_val / denom) * 100
                    spot_direct_pct = (spot_direct_val / denom) * 100
                    spot_battery_pct = (spot_battery_val / denom) * 100
                    ppa_pct = (ppa_val / denom) * 100 if integrate_ppa else 0
                else:
                    pv_pct = (pv_val / total_plotted) * 100
                    spot_direct_pct = (spot_direct_val / total_plotted) * 100
                    spot_battery_pct = (spot_battery_val / total_plotted) * 100
                    ppa_pct = (ppa_val / total_plotted) * 100 if integrate_ppa else 0

                pv_mid = pv_pct / 2
                spot_direct_mid = pv_pct + (spot_direct_pct / 2)
                spot_battery_mid = pv_pct + spot_direct_pct + (spot_battery_pct / 2)
                ppa_mid = pv_pct + spot_direct_pct + spot_battery_pct + (ppa_pct / 2)

                if pv_pct > 3:
                    pv_label = f'{pv_pct:.1f}%' if max_monthly_energy_mwh_by_month is not None else f'{pv_val:.1f}'
                    ax3.text(i, pv_mid, pv_label,
                             ha='center', va='center', color='black', fontweight='bold', fontsize=9)

                if spot_direct_pct > 3:
                    sd_label = f'{spot_direct_pct:.1f}%' if max_monthly_energy_mwh_by_month is not None else f'{spot_direct_val:.1f}'
                    ax3.text(i, spot_direct_mid, sd_label,
                             ha='center', va='center', color='black', fontweight='bold', fontsize=9)

                if spot_battery_pct > 3:
                    sb_label = f'{spot_battery_pct:.1f}%' if max_monthly_energy_mwh_by_month is not None else f'{spot_battery_val:.1f}'
                    ax3.text(i, spot_battery_mid, sb_label,
                             ha='center', va='center', color='black', fontweight='bold', fontsize=9)

                if integrate_ppa and ppa_pct > 3:
                    ppa_label = f'{ppa_pct:.1f}%' if max_monthly_energy_mwh_by_month is not None else f'{ppa_val:.1f}'
                    ax3.text(i, ppa_mid, ppa_label,
                             ha='center', va='center', color='black', fontweight='bold', fontsize=9)
        else:
            # Original logic without battery
            pv_val = df_plot_data.loc[month, 'PV']
            spot_val = df_plot_data.loc[month, 'Spot']
            ppa_val = df_plot_data.loc[month, 'PPA'] if integrate_ppa else 0

            total_plotted = pv_val + spot_val + ppa_val

            if total_plotted > 0:
                if max_monthly_energy_mwh_by_month is not None:
                    denom = max_monthly_energy_mwh_by_month.get(month, 0)
                    denom = denom if denom and denom > 0 else total_plotted
                    pv_pct = (pv_val / denom) * 100
                    spot_pct = (spot_val / denom) * 100
                    ppa_pct = (ppa_val / denom) * 100 if integrate_ppa else 0
                else:
                    pv_pct = (pv_val / total_plotted) * 100
                    spot_pct = (spot_val / total_plotted) * 100
                    ppa_pct = (ppa_val / total_plotted) * 100 if integrate_ppa else 0

                pv_mid = pv_pct / 2
                spot_mid = pv_pct + (spot_pct / 2)
                ppa_mid = pv_pct + spot_pct + (ppa_pct / 2)

                if pv_pct > 3:
                    pv_label = f'{pv_pct:.1f}%' if max_monthly_energy_mwh_by_month is not None else f'{pv_val:.1f}'
                    ax3.text(i, pv_mid, pv_label,
                             ha='center', va='center', color='black', fontweight='bold', fontsize=9)

                if spot_pct > 3:
                    spot_label = f'{spot_pct:.1f}%' if max_monthly_energy_mwh_by_month is not None else f'{spot_val:.1f}'
                    ax3.text(i, spot_mid, spot_label,
                             ha='center', va='center', color='black', fontweight='bold', fontsize=9)

                if integrate_ppa and ppa_pct > 3:
                    ppa_label = f'{ppa_pct:.1f}%' if max_monthly_energy_mwh_by_month is not None else f'{ppa_val:.1f}'
                    ax3.text(i, ppa_mid, ppa_label,
                             ha='center', va='center', color='black', fontweight='bold', fontsize=9)
    
    # Set chart title based on battery inclusion and average service ratio
    avg_sr = 0
    if monthly_service_ratios:
        avg_sr = sum(monthly_service_ratios.values()) / len(monthly_service_ratios)
    avg_suffix = f' (Avg SR: {avg_sr:.1%})' if monthly_service_ratios else ''
    if include_battery and battery_capacity_mwh > 0:
        chart_title = f'Monthly Energy Coverage{avg_suffix} (incl. {battery_capacity_mwh:.1f} MWh Daily Battery Storage)'
    else:
        chart_title = f'Monthly Energy Coverage{avg_suffix}'
    
    ax3.set_title(chart_title)
    ax3.set_xlabel('Month')
    ax3.set_ylabel('Coverage (%)')
    ax3.set_ylim(0, 110)
    ax3.tick_params(axis='x', rotation=45)

    if max_monthly_energy_mwh_by_month is None:
        ax4 = ax3.twinx()
        totals = df_plot_data[plot_columns].sum(axis=1)
        if not totals.empty:
            ax4.plot(range(len(df_plot_data.index)), totals.values, color='black', marker='o', linestyle='-', linewidth=2, markersize=8, label='Total Energy (MWh)')
            ax4.set_ylabel('Total Energy (MWh)')
            ax4.set_ylim(0, totals.max() * 1.1)
            ax4.legend(loc='upper right')
    
    plt.tight_layout()
    return fig2


def create_energy_distribution_pie_chart(df_plot_data, include_battery, battery_capacity_mwh, integrate_ppa, monthly_service_ratios=None):
    """Create pie chart for energy distribution"""
    # Calculate total energy for each source
    total_pv_energy = sum(df_plot_data['PV'])
    total_spot_energy = sum(df_plot_data['Spot'])
    total_ppa_energy = sum(df_plot_data['PPA']) if integrate_ppa else 0
    
    # Create pie chart data
    if include_battery and battery_capacity_mwh > 0:
        total_pv_energy = sum(df_plot_data['PV'])
        total_spot_direct_energy = sum(df_plot_data['Spot Direct'])
        total_spot_battery_energy = sum(df_plot_data['Spot Battery'])
        pie_data = [total_pv_energy, total_spot_direct_energy, total_spot_battery_energy] + ([total_ppa_energy] if integrate_ppa else [])
        pie_labels = ['PV', 'Spot Direct', 'Spot Battery'] + (['PPA'] if integrate_ppa else [])
        pie_colors = ['blue', 'darkgreen', 'lightgreen'] + (['red'] if integrate_ppa else [])
    else:
        pie_data = [total_pv_energy, total_spot_energy] + ([total_ppa_energy] if integrate_ppa else [])
        pie_labels = ['PV', 'Spot'] + (['PPA'] if integrate_ppa else [])
        pie_colors = ['blue', 'green'] + (['red'] if integrate_ppa else [])
    
    # Filter out zero values for cleaner pie chart
    filtered_data = []
    filtered_labels = []
    filtered_colors = []
    
    for i, value in enumerate(pie_data):
        if value > 0:
            filtered_data.append(value)
            filtered_labels.append(pie_labels[i])
            filtered_colors.append(pie_colors[i])
    
    if not filtered_data:  # No data to plot
        return None
        
    fig3, ax4 = plt.subplots(figsize=(6, 4))
    
    # Calculate percentages
    total_energy = sum(filtered_data)
    percentages = [value/total_energy*100 for value in filtered_data]
    
    # Create pie chart with better label positioning
    wedges, texts, autotexts = ax4.pie(
        filtered_data, 
        labels=filtered_labels,
        colors=filtered_colors,
        autopct='%1.1f%%',  # Show all percentages
        startangle=90,
        pctdistance=0.85,  # Distance of percentage labels from center
        labeldistance=1.1,  # Distance of labels from center
        textprops={'fontsize': 10, 'fontweight': 'bold'}
    )
    
    # Style the percentage labels
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontweight('bold')
        autotext.set_bbox(dict(boxstyle='round,pad=0.2', facecolor='black', alpha=0.7))
    
    # Style the labels
    for i, (text, value) in enumerate(zip(texts, filtered_data)):
        text.set_fontweight('bold')
        text.set_fontsize(11)
        # Add energy value to the label
        original_text = text.get_text()
        text.set_text(f'{original_text}\n({value:.1f} MWh)')
        text.set_bbox(dict(boxstyle='round,pad=0.3', 
                         facecolor='white', 
                         edgecolor=filtered_colors[i], 
                         alpha=0.9))
    
    # Set pie chart title including average service ratio
    avg_sr = 0
    if monthly_service_ratios:
        avg_sr = sum(monthly_service_ratios.values()) / len(monthly_service_ratios)
    avg_suffix = f' (Avg SR: {avg_sr:.1%})' if monthly_service_ratios else ''
    if include_battery and battery_capacity_mwh > 0:
        pie_title = f'Energy Distribution{avg_suffix} (with {battery_capacity_mwh:.1f} MWh Daily Battery Storage)'
    else:
        pie_title = f'Energy Distribution{avg_suffix}'
    
    ax4.set_title(pie_title, fontweight='bold', fontsize=12)
    plt.tight_layout()
    
    return fig3


def create_hourly_slots_by_weekday_boxplot(data_content, target_price):
    """
    Create boxplot showing the distribution of selected hourly slots by day of week
    for the Target Price-Based strategy.
    
    This shows which hours of the day (0-23) are typically selected for operation
    on each day of the week (Monday to Sunday).
    
    Parameters:
        data_content (pd.DataFrame): DataFrame containing electricity price data
        target_price (float): Target spot price threshold (€/MWh)
    
    Returns:
        matplotlib.figure.Figure: The created figure
    """
    # Import the function to get selected hours from Target Price-Based strategy
    from calculate_operation_strategies import get_selected_hours_details_target_price
    
    # Get the hours selected by the actual Target Price-Based strategy
    selected_hours_details = get_selected_hours_details_target_price(data_content, target_price)
    
    # Map English day names to French for display and proper ordering
    day_mapping_en_to_fr = {
        'Monday': 'Lundi',
        'Tuesday': 'Mardi',
        'Wednesday': 'Mercredi',
        'Thursday': 'Jeudi',
        'Friday': 'Vendredi',
        'Saturday': 'Samedi',
        'Sunday': 'Dimanche'
    }
    
    # Group selected hours by day of week
    selected_hours_by_weekday = {
        'Monday': [],
        'Tuesday': [],
        'Wednesday': [],
        'Thursday': [],
        'Friday': [],
        'Saturday': [],
        'Sunday': []
    }
    
    for hour_detail in selected_hours_details:
        weekday = hour_detail['day_of_week']
        if weekday in selected_hours_by_weekday:
            selected_hours_by_weekday[weekday].append(hour_detail['hour'])
    
    # Create boxplot
    fig, ax = plt.subplots(figsize=(14, 7))
    
    # Prepare data for boxplot
    weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    box_data = []
    box_labels = []
    
    for day in weekday_order:
        day_fr = day_mapping_en_to_fr[day]
        if selected_hours_by_weekday[day]:
            box_data.append(selected_hours_by_weekday[day])
            box_labels.append(f'{day_fr}\n(n={len(selected_hours_by_weekday[day])})')
        else:
            box_data.append([])
            box_labels.append(f'{day_fr}\n(n=0)')
    
    # Create the boxplot
    bp = ax.boxplot(box_data, labels=box_labels, patch_artist=True, 
                    showmeans=True, meanline=True,
                    showfliers=False,  # Don't show outliers as default markers
                    boxprops=dict(facecolor='lightblue', alpha=0.5),
                    medianprops=dict(color='red', linewidth=2.5),
                    meanprops=dict(color='darkgreen', linewidth=2.5, linestyle='--'),
                    whiskerprops=dict(linewidth=1.5),
                    capprops=dict(linewidth=1.5))
    
    # Customize colors for each day
    colors = plt.cm.Set3(range(7))
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.5)
    
    # Add individual points (scatter plot) for each day
    for i, (day_data, color) in enumerate(zip(box_data, colors), 1):
        if len(day_data) > 0:
            # Add jitter to x-coordinates to avoid overlapping points
            x_positions = np.random.normal(i, 0.04, size=len(day_data))
            ax.scatter(x_positions, day_data, alpha=0.4, s=20, color=color, 
                      edgecolors='black', linewidths=0.5, zorder=3)
    
    # Customize the plot
    ax.set_title(f'Distribution of Selected Hourly Slots by Weekday\n'
                 f'Daily Purchase Strategy (Target Price: {target_price}€/MWh)',
                 fontweight='bold', fontsize=14, pad=20)
    ax.set_xlabel('Weekday', fontsize=12, fontweight='bold')
    ax.set_ylabel('Hour of the Day (0-23h)', fontsize=12, fontweight='bold')
    ax.set_ylim(-1, 24)
    ax.set_yticks(range(0, 24, 2))
    ax.grid(True, alpha=0.3, axis='y')
    
    # Add horizontal reference lines for day periods
    ax.axhspan(0, 6, alpha=0.1, color='blue', label='Night (0-6h)')
    ax.axhspan(6, 12, alpha=0.1, color='yellow', label='Morning (6-12h)')
    ax.axhspan(12, 18, alpha=0.1, color='orange', label='Afternoon (12-18h)')
    ax.axhspan(18, 24, alpha=0.1, color='purple', label='Evening (18-24h)')
    
    # Add legend for median and mean
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], color='red', linewidth=2, label='Median'),
        Line2D([0], [0], color='green', linewidth=2, linestyle='--', label='Mean')
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=10)
    
    # Add statistics summary
    total_selected_hours = len(selected_hours_details)
    unique_dates = len(set([detail['date'] for detail in selected_hours_details]))
    avg_hours_per_day = total_selected_hours / unique_dates if unique_dates > 0 else 0
    
    stats_text = f"Total hours selected: {total_selected_hours}\n"
    stats_text += f"Days analyzed: {unique_dates}\n"
    stats_text += f"Average: {avg_hours_per_day:.1f}h/day\n"
    stats_text += f"Target price: {target_price}€/MWh"
    ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
            verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
            fontsize=10)
    
    plt.tight_layout()
    return fig


def find_consecutive_runs(hours):
    if not hours:
        return []
    sorted_hours = sorted(set(hours))
    runs = []
    start = sorted_hours[0]
    for i in range(1, len(sorted_hours)):
        if sorted_hours[i] != sorted_hours[i-1] + 1:
            runs.append(sorted_hours[i-1] - start + 1)
            start = sorted_hours[i]
    runs.append(sorted_hours[-1] - start + 1)
    return runs

def create_consecutive_slots_distributions(data_content, target_price):
    from calculate_operation_strategies import get_selected_hours_details_target_price
    selected_hours_details = get_selected_hours_details_target_price(data_content, target_price)
    lengths_by_weekday = defaultdict(list)
    lengths_by_month = defaultdict(list)
    date_to_hours = defaultdict(list)
    for detail in selected_hours_details:
        date_to_hours[detail['date']].append(detail['hour'])
    for date, hours in date_to_hours.items():
        runs = find_consecutive_runs(hours)
        detail = next(d for d in selected_hours_details if d['date'] == date)
        weekday = detail['day_of_week']
        month = pd.to_datetime(date).month_name()
        for length in runs:
            lengths_by_weekday[weekday].append(length)
            lengths_by_month[month].append(length)
    # Weekday boxplot
    weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    box_data_week = []
    box_labels_week = []
    for day in weekday_order:
        data = lengths_by_weekday[day]
        box_data_week.append(data)
        box_labels_week.append(f'{day}\n(n={len(data)})')
    fig_week, ax_week = plt.subplots(figsize=(14, 7))
    bp_week = ax_week.boxplot(box_data_week, labels=box_labels_week, patch_artist=True, 
                              showmeans=True, meanline=True,
                              showfliers=False,
                              boxprops=dict(facecolor='lightblue', alpha=0.5),
                              medianprops=dict(color='red', linewidth=2.5),
                              meanprops=dict(color='darkgreen', linewidth=2.5, linestyle='--'),
                              whiskerprops=dict(linewidth=1.5),
                              capprops=dict(linewidth=1.5))
    colors = plt.cm.Set3(range(7))
    for patch, color in zip(bp_week['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.5)
    for i, (data, color) in enumerate(zip(box_data_week, colors), 1):
        if data:
            x_pos = np.random.normal(i, 0.04, len(data))
            ax_week.scatter(x_pos, data, alpha=0.4, s=20, color=color, edgecolors='black', linewidths=0.5, zorder=3)
    ax_week.set_title(f'Distribution of Consecutive Slot Lengths by Weekday\nDaily Purchase Strategy (Target Price: {target_price}€/MWh)',
                      fontweight='bold', fontsize=14, pad=20)
    ax_week.set_xlabel('Weekday', fontsize=12, fontweight='bold')
    ax_week.set_ylabel('Slot Length (hours)', fontsize=12, fontweight='bold')
    ax_week.set_ylim(0, 25)
    ax_week.set_yticks(range(0, 26, 2))
    ax_week.grid(True, alpha=0.3, axis='y')
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], color='red', linewidth=2, label='Median'),
        Line2D([0], [0], color='green', linewidth=2, linestyle='--', label='Mean')
    ]
    ax_week.legend(handles=legend_elements, loc='upper right', fontsize=10)
    total_slots = sum(len(lengths_by_weekday[day]) for day in weekday_order)
    total_days = len(date_to_hours)
    avg_slots_per_day = total_slots / total_days if total_days > 0 else 0
    all_lengths = [l for ls in lengths_by_weekday.values() for l in ls]
    avg_length = np.mean(all_lengths) if all_lengths else 0
    stats_text = f"Total slots: {total_slots}\nDays analyzed: {total_days}\nAvg. slots/day: {avg_slots_per_day:.1f}\nAvg. length: {avg_length:.1f}h\nTarget price: {target_price}€/MWh"
    ax_week.text(0.02, 0.98, stats_text, transform=ax_week.transAxes,
                 verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
                 fontsize=10)
    # Monthly boxplot
    month_order = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
    box_data_month = []
    box_labels_month = []
    for month in month_order:
        data = lengths_by_month[month]
        box_data_month.append(data)
        box_labels_month.append(f'{month[:3]}\n(n={len(data)})')
    fig_month, ax_month = plt.subplots(figsize=(14, 7))
    bp_month = ax_month.boxplot(box_data_month, labels=box_labels_month, patch_artist=True, 
                               showmeans=True, meanline=True,
                               showfliers=False,
                               boxprops=dict(facecolor='lightblue', alpha=0.5),
                               medianprops=dict(color='red', linewidth=2.5),
                               meanprops=dict(color='darkgreen', linewidth=2.5, linestyle='--'),
                               whiskerprops=dict(linewidth=1.5),
                               capprops=dict(linewidth=1.5))
    colors_month = plt.cm.Set3(range(12))
    for patch, color in zip(bp_month['boxes'], colors_month):
        patch.set_facecolor(color)
        patch.set_alpha(0.5)
    for i, (data, color) in enumerate(zip(box_data_month, colors_month), 1):
        if data:
            x_pos = np.random.normal(i, 0.04, len(data))
            ax_month.scatter(x_pos, data, alpha=0.4, s=20, color=color, edgecolors='black', linewidths=0.5, zorder=3)
    ax_month.set_title(f'Distribution of Consecutive Slot Lengths by Month\nDaily Purchase Strategy (Target Price: {target_price}€/MWh)',
                       fontweight='bold', fontsize=14, pad=20)
    ax_month.set_xlabel('Month', fontsize=12, fontweight='bold')
    ax_month.set_ylabel('Slot Length (hours)', fontsize=12, fontweight='bold')
    ax_month.set_ylim(0, 25)
    ax_month.set_yticks(range(0, 26, 2))
    ax_month.grid(True, alpha=0.3, axis='y')
    ax_month.legend(handles=legend_elements, loc='upper right', fontsize=10)
    ax_month.text(0.02, 0.98, stats_text, transform=ax_month.transAxes,
                  verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
                  fontsize=10)
    plt.tight_layout()
    return fig_week, fig_month