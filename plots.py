"""
Plotting functions for the MetaSTAAQ Dashboard
"""

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import calendar
from matplotlib.patches import Rectangle
from config import PLOT_COLORS


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
    ax_service.set_title('Monthly Service Ratios (Green: ≥90%, Orange: 50-90%, Red: <50%)')
    ax_service.set_ylim(0, 1.1)
    ax_service.grid(True, alpha=0.3)
    plt.tight_layout()
    
    return fig_service


def create_operating_hours_chart(df_result, extended_info, strategy_type, pv_energy_mwh=None, electrolyser_power=None):
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
                spot_hours_data.loc[month, year] = df_plot.loc[month, year]
                ppa_hours_data.loc[month, year] = 0

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
    ax1.set_title(f'Operating Hours Chart ({strategy_type})')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Add average line (without value labels on top)
    ax1.plot(x_pos, monthly_avg, color='red', linestyle='--', marker='o', linewidth=2, markersize=6, label='Average')
    
    handles, labels = ax1.get_legend_handles_labels()
    ax1.legend(handles, labels, loc='upper right')
    plt.tight_layout()
    
    return fig1


def create_energy_coverage_chart(df_plot_data, include_battery, battery_capacity_mwh, integrate_ppa):
    """Create energy coverage stacked bar chart"""
    fig2, ax3 = plt.subplots(figsize=(12, 6))
    
    # Choose columns and colors based on battery inclusion
    if include_battery and battery_capacity_mwh > 0:
        plot_columns = ['PV', 'Spot Direct', 'Spot Battery'] + (['PPA'] if integrate_ppa else [])
        plot_colors = ['blue', 'darkgreen', 'lightgreen'] + (['red'] if integrate_ppa else [])
    else:
        plot_columns = ['PV', 'Spot'] + (['PPA'] if integrate_ppa else [])
        plot_colors = ['blue', 'green'] + (['red'] if integrate_ppa else [])
    
    df_plot_data[plot_columns].plot(
        kind='bar', stacked=True, ax=ax3, color=plot_colors
    )
    
    # Add cumulative energy totals on top of bars
    for i, month in enumerate(df_plot_data.index):
        # Calculate total energy for this month
        if include_battery and battery_capacity_mwh > 0:
            total_energy = (df_plot_data.loc[month, 'PV'] + 
                          df_plot_data.loc[month, 'Spot Direct'] + 
                          df_plot_data.loc[month, 'Spot Battery'] + 
                          (df_plot_data.loc[month, 'PPA'] if integrate_ppa else 0))
        else:
            total_energy = (df_plot_data.loc[month, 'PV'] + 
                          df_plot_data.loc[month, 'Spot'] + 
                          (df_plot_data.loc[month, 'PPA'] if integrate_ppa else 0))
        
        # Add total energy label on top of bar
        if total_energy > 0:
            ax3.text(i, total_energy + (total_energy * 0.02), f'{total_energy:.1f} MWh', 
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
                # Calculate percentages
                pv_pct = (pv_val / total_plotted) * 100
                spot_direct_pct = (spot_direct_val / total_plotted) * 100
                spot_battery_pct = (spot_battery_val / total_plotted) * 100
                ppa_pct = (ppa_val / total_plotted) * 100 if integrate_ppa else 0
                
                # Position for text (middle of each bar segment)
                pv_mid = pv_val / 2
                spot_direct_mid = pv_val + (spot_direct_val / 2)
                spot_battery_mid = pv_val + spot_direct_val + (spot_battery_val / 2)
                ppa_mid = pv_val + spot_direct_val + spot_battery_val + (ppa_val / 2)
                
                # Add percentage text if segment is large enough
                if pv_pct > 3:
                    ax3.text(i, pv_mid, f'{pv_pct:.1f}%', 
                            ha='center', va='center', color='white', fontweight='bold', fontsize=9)
                
                if spot_direct_pct > 3:
                    ax3.text(i, spot_direct_mid, f'{spot_direct_pct:.1f}%', 
                            ha='center', va='center', color='white', fontweight='bold', fontsize=9)
                
                if spot_battery_pct > 3:
                    ax3.text(i, spot_battery_mid, f'{spot_battery_pct:.1f}%', 
                            ha='center', va='center', color='white', fontweight='bold', fontsize=9)
                
                if integrate_ppa and ppa_pct > 3:
                    ax3.text(i, ppa_mid, f'{ppa_pct:.1f}%', 
                            ha='center', va='center', color='white', fontweight='bold', fontsize=9)
        else:
            # Original logic without battery
            pv_val = df_plot_data.loc[month, 'PV']
            spot_val = df_plot_data.loc[month, 'Spot']
            ppa_val = df_plot_data.loc[month, 'PPA'] if integrate_ppa else 0
            
            total_plotted = pv_val + spot_val + ppa_val
            
            if total_plotted > 0:
                # Calculate percentages based on plotted total
                pv_pct = (pv_val / total_plotted) * 100
                spot_pct = (spot_val / total_plotted) * 100
                ppa_pct = (ppa_val / total_plotted) * 100 if integrate_ppa else 0
                
                # Position for text (middle of each bar segment)
                pv_mid = pv_val / 2
                spot_mid = pv_val + (spot_val / 2)
                ppa_mid = pv_val + spot_val + (ppa_val / 2)
                
                # Add percentage text if segment is large enough
                if pv_pct > 3:
                    ax3.text(i, pv_mid, f'{pv_pct:.1f}%', 
                            ha='center', va='center', color='white', fontweight='bold', fontsize=9)
                
                if spot_pct > 3:
                    ax3.text(i, spot_mid, f'{spot_pct:.1f}%', 
                            ha='center', va='center', color='white', fontweight='bold', fontsize=9)
                
                if integrate_ppa and ppa_pct > 3:
                    ax3.text(i, ppa_mid, f'{ppa_pct:.1f}%', 
                            ha='center', va='center', color='white', fontweight='bold', fontsize=9)
    
    # Set chart title based on battery inclusion
    if include_battery and battery_capacity_mwh > 0:
        chart_title = f'Monthly Energy Coverage (incl. {battery_capacity_mwh:.1f} MWh Daily Battery Storage)\nStacked: PV + Spot Energy + PPA Energy with Cumulative Totals'
    else:
        chart_title = 'Monthly Energy Coverage\nStacked: PV + Spot Energy + PPA Energy with Cumulative Totals'
    
    ax3.set_title(chart_title)
    ax3.set_xlabel('Month')
    ax3.set_ylabel('Energy (MWh)')
    ax3.tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    return fig2


def create_energy_distribution_pie_chart(df_plot_data, include_battery, battery_capacity_mwh, integrate_ppa):
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
    
    # Set pie chart title based on battery inclusion
    if include_battery and battery_capacity_mwh > 0:
        pie_title = f'Energy Distribution (with {battery_capacity_mwh:.1f} MWh Daily Battery Storage)'
    else:
        pie_title = 'Energy Distribution'
    
    ax4.set_title(pie_title, fontweight='bold', fontsize=12)
    plt.tight_layout()
    
    return fig3
