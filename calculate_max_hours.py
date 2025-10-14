# -*- coding: utf-8 -*-
"""
Function to calculate maximum hours that can be purchased each month
while keeping the average price below or equal to the target price.
"""

import pandas as pd
import calendar


def calculate_max_hours(df, target_price=15, ppa_price=80, return_extended_info=False):
    """
    Calculate the maximum number of hours that can be purchased each month
    while keeping the average price below or equal to the target price.
    If target hours are reached, extend with spot prices until average < PPA price.

    Parameters:
        df (pd.DataFrame): DataFrame containing electricity price data with 'Date', 'Heure', and 'Prix' columns
        target_price (float): Target price (€/MWh), default is 15
        ppa_price (float): PPA price (€/MWh), default is 80
        return_extended_info (bool): If True, returns additional info about extended hours

    Returns:
        dict: Maximum purchasable hours organized by year and month with string keys (month as full name)
        or tuple: (hours_dict, extended_info_dict) if return_extended_info=True
    """
    # Create a copy to avoid modifying the original DataFrame
    df = df.copy()
    
    # Combine 'Date' and 'Heure' to create 'timestamp' and convert to datetime
    # Handle case where Date might already be datetime
    if df['Date'].dtype == 'datetime64[ns]':
        df['timestamp'] = df['Date'].dt.strftime('%Y-%m-%d') + ' ' + df['Heure'].astype(str) + ':00:00'
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    else:
        df['timestamp'] = pd.to_datetime(df['Date'].astype(str) + ' ' + df['Heure'].astype(str) + ':00:00')
    df['year'] = df['timestamp'].dt.year
    df['month'] = df['timestamp'].dt.month

    # Rename 'Prix' to 'price' for consistency with the original logic
    df = df.rename(columns={'Prix': 'price'})

    # Group by year and month
    result = {}
    extended_info = {}
    
    for (year, month), group in df.groupby(['year', 'month']):
        prices = group['price'].values
        sorted_prices = sorted(prices)  # Sort prices in ascending order

        total_price = 0.0
        max_hours = 0
        extended_hours = 0
        base_hours = 0

        # Phase 1: Calculate base hours up to target_price
        for i, price in enumerate(sorted_prices, 1):
            total_price += price
            avg_price = total_price / i
            if avg_price <= target_price:
                max_hours = i
                base_hours = i
            else:
                break  # Stop once target price is exceeded
        
        # Phase 2: Extend hours if we can still stay below PPA price
        # Even if no base hours were found, we can still extend with PPA price limit
        if max_hours < len(sorted_prices):
            extended_total_price = total_price
            extended_hours_count = max_hours
            
            # Continue adding hours while average stays below PPA price
            for i in range(max_hours, len(sorted_prices)):
                next_price = sorted_prices[i]
                new_total = extended_total_price + next_price
                new_avg = new_total / (i + 1)
                
                if new_avg < ppa_price:
                    extended_total_price = new_total
                    extended_hours_count = i + 1
                    extended_hours = extended_hours_count - base_hours
                else:
                    break
            
            max_hours = extended_hours_count
        
        if max_hours == 0:
            max_hours = None
            
        # Create nested dictionary structure with string keys (month as full name)
        year_str = str(year)
        month_name = calendar.month_name[month]
        if year_str not in result:
            result[year_str] = {}
            extended_info[year_str] = {}
        
        # Calculate the actual average price of selected hours
        actual_avg_price = 0
        if max_hours is not None and max_hours > 0:
            selected_prices = sorted_prices[:max_hours]
            actual_avg_price = sum(selected_prices) / len(selected_prices)
        
        result[year_str][month_name] = max_hours
        extended_info[year_str][month_name] = {
            'base_hours': base_hours,
            'extended_hours': extended_hours,
            'total_hours': max_hours,
            'actual_avg_price': actual_avg_price
        }

    if return_extended_info:
        return result, extended_info
    return result
