# -*- coding: utf-8 -*-
"""
Enhanced operation strategies for electrolyzer based on price thresholds.
Implements Service Ratio-Based Strategy and Target Price-Based Strategy.
"""

import pandas as pd
import calendar
import numpy as np


def calculate_service_ratio_strategy(df, target_price=15, ppa_price=80, initial_service_ratio=0.98, pv_price=0, return_extended_info=False):
    """
    Service Ratio-Based Strategy:
    1. For each month, cumulate spot hours while average price < PPA price
    2. Use spot price when available, PPA price when spot > PPA
    3. Continue adding cheapest hours until average cost reaches PPA price
    4. No target price requirement - focus on maximizing hours below PPA price
    
    Parameters:
        df (pd.DataFrame): DataFrame containing electricity price data
        target_price (float): Not used in this strategy (kept for compatibility)
        ppa_price (float): PPA price (€/MWh) - maximum acceptable average cost
        initial_service_ratio (float): Not used in this strategy (kept for compatibility)
        pv_price (float): PV price (€/MWh)
        return_extended_info (bool): If True, returns additional info
    
    Returns:
        dict: Operation hours by month
        or tuple: (hours_dict, extended_info_dict) if return_extended_info=True
    """
    df = df.copy()
    
    # Handle datetime conversion
    if df['Date'].dtype == 'datetime64[ns]':
        df['timestamp'] = df['Date'].dt.strftime('%Y-%m-%d') + ' ' + df['Heure'].astype(str) + ':00:00'
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    else:
        df['timestamp'] = pd.to_datetime(df['Date'].astype(str) + ' ' + df['Heure'].astype(str) + ':00:00')
    
    df['year'] = df['timestamp'].dt.year
    df['month'] = df['timestamp'].dt.month
    df = df.rename(columns={'Prix': 'price'})

    result = {}
    extended_info = {}
    
    for (year, month), group in df.groupby(['year', 'month']):
        prices = group['price'].values
        total_hours_in_month = len(prices)
        
        # Sort prices in ascending order to get cheapest hours first
        sorted_prices = sorted(prices)
        
        # Cumulate hours while average price < PPA price
        total_cost = 0.0
        max_hours = 0
        spot_hours = 0
        ppa_hours = 0
        
        for i, price in enumerate(sorted_prices, 1):
            # Determine which price to use for this hour
            if price <= ppa_price:
                # Use spot price
                total_cost += price
                spot_hours += 1
            else:
                # Use PPA price (spot price > PPA price)
                total_cost += ppa_price
                ppa_hours += 1
            
            # Calculate current average cost
            current_avg_cost = total_cost / i
            
            # Continue as long as average cost < PPA price
            if current_avg_cost < ppa_price:
                max_hours = i
            else:
                # Stop when average cost reaches or exceeds PPA price
                break
        
        # If no hours meet the criteria, set to 0
        if max_hours == 0:
            max_hours = None
            final_avg_cost = 0
        else:
            final_avg_cost = total_cost / max_hours
        
        # Store results
        year_str = str(year)
        month_name = calendar.month_name[month]
        if year_str not in result:
            result[year_str] = {}
            extended_info[year_str] = {}
        
        result[year_str][month_name] = max_hours
        extended_info[year_str][month_name] = {
            'target_hours': max_hours,
            'total_hours_available': total_hours_in_month,
            'average_cost': final_avg_cost,
            'spot_hours': spot_hours,
            'ppa_hours': ppa_hours,
            'service_ratio': max_hours / total_hours_in_month if max_hours else 0,
            'ppa_price_threshold': ppa_price
        }
    
    if return_extended_info:
        return result, extended_info
    return result


def calculate_target_price_strategy(df, target_spot_price=15, return_extended_info=False):
    """
    Target Price-Based Strategy:
    1. User defines a target spot price threshold
    2. Electrolyzer operates by cumulating hours while average price <= target
    3. Sort prices in ascending order and add hours until cumulative average exceeds target
    4. This ensures the average cost of all operating hours stays at or below target price
    
    Parameters:
        df (pd.DataFrame): DataFrame containing electricity price data
        target_spot_price (float): Target spot price threshold (€/MWh) - cumulative average limit
        return_extended_info (bool): If True, returns additional info
    
    Returns:
        dict: Operation hours by month
        or tuple: (hours_dict, extended_info_dict) if return_extended_info=True
    """
    df = df.copy()
    
    # Handle datetime conversion
    if df['Date'].dtype == 'datetime64[ns]':
        df['timestamp'] = df['Date'].dt.strftime('%Y-%m-%d') + ' ' + df['Heure'].astype(str) + ':00:00'
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    else:
        df['timestamp'] = pd.to_datetime(df['Date'].astype(str) + ' ' + df['Heure'].astype(str) + ':00:00')
    
    df['year'] = df['timestamp'].dt.year
    df['month'] = df['timestamp'].dt.month
    df = df.rename(columns={'Prix': 'price'})

    result = {}
    extended_info = {}
    
    for (year, month), group in df.groupby(['year', 'month']):
        prices = group['price'].values
        total_hours_in_month = len(prices)
        
        # Sort prices in ascending order to get cheapest hours first
        sorted_prices = sorted(prices)
        
        # Cumulate hours while average price <= target_spot_price
        total_cost = 0.0
        max_hours = 0
        
        for i, price in enumerate(sorted_prices, 1):
            total_cost += price
            current_avg_cost = total_cost / i
            
            # Continue as long as cumulative average <= target price
            if current_avg_cost <= target_spot_price:
                max_hours = i
            else:
                # Stop when cumulative average exceeds target price
                break
        
        # Calculate final statistics
        if max_hours > 0:
            # Recalculate final average cost from the selected hours
            selected_prices = sorted_prices[:max_hours]
            final_avg_cost = sum(selected_prices) / len(selected_prices)
            # Calculate actual hours used (spot hours only, no PPA mixing)
            spot_hours = max_hours
            ppa_hours = 0
        else:
            final_avg_cost = 0
            spot_hours = 0
            ppa_hours = 0
        
        # Store results
        year_str = str(year)
        month_name = calendar.month_name[month]
        if year_str not in result:
            result[year_str] = {}
            extended_info[year_str] = {}
        
        result[year_str][month_name] = max_hours if max_hours > 0 else None
        extended_info[year_str][month_name] = {
            'target_spot_price': target_spot_price,
            'spot_hours': spot_hours,
            'ppa_hours': ppa_hours,
            'total_hours': total_hours_in_month,
            'final_avg_cost': final_avg_cost,
            'service_ratio': max_hours / total_hours_in_month if total_hours_in_month > 0 else 0
        }
    
    if return_extended_info:
        return result, extended_info
    return result


def get_selected_hours_details_target_price(df, target_spot_price=15):
    """
    Get detailed information about which specific hours are selected by Target Price-Based strategy.
    Returns the actual hour values (0-23) and day of week for each selected hour.
    
    Parameters:
        df (pd.DataFrame): DataFrame containing electricity price data
        target_spot_price (float): Target spot price threshold (€/MWh)
    
    Returns:
        list: List of dicts with 'hour', 'day_of_week', 'date', 'price' for each selected hour
    """
    df = df.copy()
    
    # Ensure Date column is datetime
    if df['Date'].dtype != 'datetime64[ns]':
        df['Date'] = pd.to_datetime(df['Date'])
    
    # Add day of week
    df['DayOfWeek'] = df['Date'].dt.day_name()
    df['DateOnly'] = df['Date'].dt.date
    
    selected_hours_details = []
    
    # Process each day separately (simulating daily purchase decision)
    for date, day_group in df.groupby('DateOnly'):
        if len(day_group) < 24:  # Skip incomplete days
            continue
        
        # Sort by price to select cheapest hours first
        day_group = day_group.sort_values('Prix').reset_index(drop=True)
        
        # Apply Target Price-Based strategy logic
        total_cost = 0.0
        selected_hours_for_day = []
        
        for idx, row in day_group.iterrows():
            total_cost += row['Prix']
            num_selected = len(selected_hours_for_day) + 1
            current_avg = total_cost / num_selected
            
            if current_avg <= target_spot_price:
                selected_hours_for_day.append({
                    'hour': row['Heure'],
                    'day_of_week': row['DayOfWeek'],
                    'date': row['DateOnly'],
                    'price': row['Prix']
                })
            else:
                break
        
        selected_hours_details.extend(selected_hours_for_day)
    
    return selected_hours_details


def calculate_hybrid_strategy(df, target_price=15, ppa_price=80, pv_price=0, strategy_type='service_ratio', **kwargs):
    """
    Hybrid function that chooses between Service Ratio-Based and Target Price-Based strategies.
    
    Parameters:
        df (pd.DataFrame): DataFrame containing electricity price data
        target_price (float): Target price (€/MWh)
        ppa_price (float): PPA price (€/MWh)
        pv_price (float): PV price (€/MWh)
        strategy_type (str): 'service_ratio' or 'target_price'
        **kwargs: Additional parameters for specific strategies
    
    Returns:
        dict: Operation hours by month
        or tuple: (hours_dict, extended_info_dict) if return_extended_info=True
    """
    if strategy_type == 'service_ratio':
        return calculate_service_ratio_strategy(
            df, target_price, ppa_price, 
            kwargs.get('initial_service_ratio', 0.98),
            pv_price, kwargs.get('return_extended_info', False)
        )
    elif strategy_type == 'target_price':
        return calculate_target_price_strategy(
            df, target_price, kwargs.get('return_extended_info', False)
        )
    else:
        raise ValueError("strategy_type must be 'service_ratio' or 'target_price'")


def calculate_optimal_monthly_ratios(df, annual_service_ratio=0.98, return_extended_info=False):
    """
    Optimize Monthly Ratios for a Target Annual Service Ratio:
    1. Sorts ALL hours of the year by price.
    2. Selects the top (annual_service_ratio * total_hours) cheapest hours.
    3. Aggregates the selected hours back into monthly service ratios.
    
    Parameters:
        df (pd.DataFrame): DataFrame containing electricity price data (needs 'year' and 'month')
        annual_service_ratio (float): Target annual service ratio (0.0 to 1.0)
        return_extended_info (bool): If True, returns additional info
    
    Returns:
        dict: Operation hours by month {year: {month: hours}}
        or tuple: (hours_dict, extended_info_dict) if return_extended_info=True
    """
    df = df.copy()
    
    # Handle datetime conversion if needed (similar to other strategies)
    if 'timestamp' not in df.columns:
        if df['Date'].dtype == 'datetime64[ns]':
            df['timestamp'] = df['Date'].dt.strftime('%Y-%m-%d') + ' ' + df['Heure'].astype(str) + ':00:00'
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        else:
            df['timestamp'] = pd.to_datetime(df['Date'].astype(str) + ' ' + df['Heure'].astype(str) + ':00:00')
            
    df['year'] = df['timestamp'].dt.year
    df['month'] = df['timestamp'].dt.month
    if 'price' not in df.columns:
        df = df.rename(columns={'Prix': 'price'})

    result = {}
    extended_info = {}
    
    # Process per year to ensure annual ratio is respected per year
    for year, group in df.groupby('year'):
        year_str = str(year)
        result[year_str] = {}
        extended_info[year_str] = {}
        
        # Sort all hours in the year by price
        sorted_group = group.sort_values('price')
        total_hours_year = len(group)
        target_hours_year = int(total_hours_year * annual_service_ratio)
        
        # Select cheap hours
        selected_hours = sorted_group.head(target_hours_year)
        
        # Aggregate by month to get monthly hours
        monthly_counts = selected_hours.groupby('month').size()
        
        # Iterate over all months in this year to ensure we populate even months with 0 hours
        months_in_year = group['month'].unique()
        
        for month in months_in_year:
            month_name = calendar.month_name[month]
            
            hours_in_month = len(group[group['month'] == month])
            selected_hours_month = monthly_counts.get(month, 0)
            
            result[year_str][month_name] = int(selected_hours_month)
            
            # Calculate avg cost for this month (of selected hours)
            if selected_hours_month > 0:
                # Filter selected_hours for this month
                month_selection = selected_hours[selected_hours['month'] == month]
                avg_cost_month = month_selection['price'].mean()
            else:
                avg_cost_month = 0.0
                
            extended_info[year_str][month_name] = {
                'target_hours': int(selected_hours_month),
                'total_hours_available': hours_in_month,
                'average_cost': avg_cost_month,
                'spot_hours': int(selected_hours_month), # Pure spot strategy assumed
                'ppa_hours': 0,
                'service_ratio': selected_hours_month / hours_in_month if hours_in_month > 0 else 0,
                'annual_service_ratio_target': annual_service_ratio
            }
            
    if return_extended_info:
        return result, extended_info
    return result
