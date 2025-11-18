"""
Battery Energy Management System Optimizer
Hourly simulation of PV-Battery-Electrolyser system with arbitrage
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from battery_config import (
    DEFAULT_BATTERY_PARAMS, DEFAULT_TIME_WINDOWS, DEFAULT_ELECTROLYSER_PARAMS,
    NIGHT_CHARGE_STRATEGY, PENALTY_PARAMS, is_hour_in_window, get_window_duration
)


class BatteryOptimizer:
    """
    Battery Energy Management System with time-windowed operations:
    - PV priority charging (10:00-16:00)
    - Evening arbitrage discharge (16:00-23:00)
    - Spot grid charging (23:00-05:00)
    - Morning electrolyser supply (05:00-10:00)
    """
    
    def __init__(self, battery_params=None, time_windows=None, electrolyser_params=None,
                 night_charge_strategy=None, penalty_params=None):
        """
        Initialize the battery optimizer
        
        Args:
            battery_params: Dictionary of battery technical parameters
            time_windows: Dictionary of operational time windows (hours)
            electrolyser_params: Dictionary of electrolyser parameters
            night_charge_strategy: Dictionary with charging strategy
            penalty_params: Dictionary with penalty parameters
        """
        self.battery_params = battery_params or DEFAULT_BATTERY_PARAMS.copy()
        self.time_windows = time_windows or DEFAULT_TIME_WINDOWS.copy()
        self.electrolyser_params = electrolyser_params or DEFAULT_ELECTROLYSER_PARAMS.copy()
        self.night_charge_strategy = night_charge_strategy or NIGHT_CHARGE_STRATEGY.copy()
        self.penalty_params = penalty_params or PENALTY_PARAMS.copy()
        
        # Calculate effective energy limits based on DoD
        self.E_min = self.battery_params["E_bat_max"] * self.battery_params["SoC_min"]
        self.E_max = self.battery_params["E_bat_max"] * self.battery_params["SoC_max"]
        
    def simulate_year(self, pv_profile_mw, spot_prices_eur_mwh, hours_of_day):
        """
        Simulate a full year of battery operation with hourly resolution
        
        Args:
            pv_profile_mw: Array of PV production [MW] for each hour
            spot_prices_eur_mwh: Array of spot market prices [€/MWh] for each hour
            hours_of_day: Array of hours (0-23) for each timestep
        
        Returns:
            DataFrame with hourly results and summary statistics
        """
        n_hours = len(hours_of_day)
        
        # Initialize results arrays
        results = {
            'hour_of_day': hours_of_day,
            'pv_available_mw': pv_profile_mw,
            'spot_price_eur_mwh': spot_prices_eur_mwh,
            
            # Battery state
            'soc': np.zeros(n_hours),
            'energy_stored_mwh': np.zeros(n_hours),
            
            # Power flows [MW] (positive = charging, negative = discharging)
            'pv_to_battery_mw': np.zeros(n_hours),
            'grid_to_battery_mw': np.zeros(n_hours),
            'battery_to_grid_mw': np.zeros(n_hours),
            'battery_to_ely_mw': np.zeros(n_hours),
            'pv_curtailed_mw': np.zeros(n_hours),
            
            # Electrolyser
            'ely_power_mw': np.zeros(n_hours),
            'ely_h2_production_kg': np.zeros(n_hours),
            'ely_shortage_mw': np.zeros(n_hours),
            
            # Economics [€]
            'revenue_arbitrage': np.zeros(n_hours),
            'cost_charging': np.zeros(n_hours),
            'cost_penalties': np.zeros(n_hours),
            'net_cashflow': np.zeros(n_hours),
            
            # Operational windows (for debugging/visualization)
            'window_type': [''] * n_hours,
        }
        
        # Initialize battery state
        E_bat = self.battery_params["E_bat_max"] * self.battery_params["SoC_initial"]
        
        # Simulation loop
        for t in range(n_hours):
            hour_of_day = int(hours_of_day[t])
            results['hour_of_day'][t] = hour_of_day
            
            pv_available = pv_profile_mw[t]
            spot_price = spot_prices_eur_mwh[t]
            
            # Apply self-discharge
            E_bat *= (1 - self.battery_params["self_discharge_rate"])
            
            # Determine operational window
            window_type = self._get_window_type(hour_of_day)
            results['window_type'][t] = window_type
            
            # Apply operational rules based on window
            if window_type == "pv_charge":
                E_bat, flows = self._pv_charge_window(E_bat, pv_available, spot_price)
                
            elif window_type == "arbitrage_discharge":
                E_bat, flows = self._arbitrage_discharge_window(E_bat, pv_available, spot_price)
                
            elif window_type == "night_charge":
                E_bat, flows = self._night_charge_window(E_bat, pv_available, spot_price)
                
            elif window_type == "electrolyser":
                E_bat, flows = self._electrolyser_window(E_bat, pv_available, spot_price)
            
            else:
                # No specific window - idle
                flows = self._idle_state(pv_available)
            
            # Store results
            E_bat = np.clip(E_bat, self.E_min, self.E_max)
            results['energy_stored_mwh'][t] = E_bat
            results['soc'][t] = E_bat / self.battery_params["E_bat_max"]
            
            results['pv_to_battery_mw'][t] = flows['pv_to_battery']
            results['grid_to_battery_mw'][t] = flows['grid_to_battery']
            results['battery_to_grid_mw'][t] = flows['battery_to_grid']
            results['battery_to_ely_mw'][t] = flows['battery_to_ely']
            results['pv_curtailed_mw'][t] = flows['pv_curtailed']
            results['ely_power_mw'][t] = flows['ely_power']
            results['ely_shortage_mw'][t] = flows['ely_shortage']
            
            # Calculate economics
            # Revenue from selling to grid (arbitrage)
            revenue = flows['battery_to_grid'] * spot_price
            results['revenue_arbitrage'][t] = revenue
            
            # Cost of buying from grid
            cost_grid = flows['grid_to_battery'] * spot_price
            results['cost_charging'][t] = cost_grid
            
            # Penalties
            penalty_cost = flows['ely_shortage'] * self.penalty_params['electrolyser_shortage_penalty']
            results['cost_penalties'][t] = penalty_cost
            
            # Net cashflow
            results['net_cashflow'][t] = revenue - cost_grid - penalty_cost
            
            # Hydrogen production
            if flows['ely_power'] > 0:
                h2_kg = (flows['ely_power'] * 1000) / self.electrolyser_params['specific_consumption']
                results['ely_h2_production_kg'][t] = h2_kg
        
        # Convert to DataFrame
        df_results = pd.DataFrame(results)
        
        # Calculate summary statistics
        summary = self._calculate_summary(df_results)
        
        return df_results, summary
    
    def _get_window_type(self, hour):
        """Determine which operational window the current hour belongs to"""
        tw = self.time_windows
        
        if is_hour_in_window(hour, tw["electrolyser_start"], tw["electrolyser_end"]):
            return "electrolyser"
        elif is_hour_in_window(hour, tw["pv_charge_start"], tw["pv_charge_end"]):
            return "pv_charge"
        elif is_hour_in_window(hour, tw["arbitrage_discharge_start"], tw["arbitrage_discharge_end"]):
            return "arbitrage_discharge"
        elif is_hour_in_window(hour, tw["night_charge_start"], tw["night_charge_end"]):
            return "night_charge"
        else:
            return "idle"
    
    def _pv_charge_window(self, E_bat, pv_available, spot_price):
        """
        PV-priority charging window (default 10:00-16:00)
        - All PV production charges the battery (up to limits)
        - Excess PV is curtailed
        - No grid interaction
        """
        flows = self._init_flows()
        
        # Calculate how much battery can accept
        E_available = self.E_max - E_bat
        P_charge_limit = self.battery_params["P_charge_max"]
        eta_charge = self.battery_params["eta_charge"]
        
        # Maximum energy that can be charged this hour
        E_charge_max = min(P_charge_limit * 1.0, E_available)  # 1.0 hour timestep
        
        # PV to battery (limited by charge power and available capacity)
        P_pv_to_bat = min(pv_available, P_charge_limit)
        E_pv_to_bat = min(P_pv_to_bat * 1.0, E_charge_max)
        
        # Apply charging efficiency
        E_bat_new = E_bat + E_pv_to_bat * eta_charge
        
        # Curtail excess PV
        pv_curtailed = max(0, pv_available - P_pv_to_bat)
        
        flows['pv_to_battery'] = P_pv_to_bat
        flows['pv_curtailed'] = pv_curtailed
        
        return E_bat_new, flows
    
    def _arbitrage_discharge_window(self, E_bat, pv_available, spot_price):
        """
        Evening arbitrage discharge window (default 16:00-23:00)
        - Discharge battery to grid at maximum power to sell energy
        - Goal: empty battery to prepare for spot charging
        - PV is curtailed (not sold in this implementation, could be modified)
        """
        flows = self._init_flows()
        
        # Calculate maximum discharge
        E_available = E_bat - self.E_min
        P_discharge_limit = self.battery_params["P_discharge_max"]
        eta_discharge = self.battery_params["eta_discharge"]
        
        # Discharge at maximum rate
        P_discharge = min(P_discharge_limit, E_available / 1.0)  # 1.0 hour timestep
        E_discharge = P_discharge * 1.0
        
        # Apply discharge efficiency (energy loss in battery)
        E_bat_new = E_bat - E_discharge / eta_discharge
        
        # Curtail PV during this window (rule: only arbitrage in evening)
        pv_curtailed = pv_available
        
        flows['battery_to_grid'] = P_discharge
        flows['pv_curtailed'] = pv_curtailed
        
        return E_bat_new, flows
    
    def _night_charge_window(self, E_bat, pv_available, spot_price):
        """
        Spot grid charging window (default 23:00-05:00)
        - Charge from grid at spot market prices to prepare for electrolyser
        - Can use price threshold strategy or always charge
        """
        flows = self._init_flows()
        
        # Check charging strategy
        should_charge = True
        if self.night_charge_strategy['mode'] == 'price_threshold':
            should_charge = spot_price <= self.night_charge_strategy['price_threshold']
        
        if should_charge:
            # Calculate how much battery can accept
            E_available = self.E_max - E_bat
            P_charge_limit = self.battery_params["P_charge_max"]
            eta_charge = self.battery_params["eta_charge"]
            
            # Charge at maximum rate
            P_charge = min(P_charge_limit, E_available / eta_charge / 1.0)
            E_charge = P_charge * 1.0 * eta_charge
            
            E_bat_new = E_bat + E_charge
            
            flows['grid_to_battery'] = P_charge
        else:
            E_bat_new = E_bat
        
        # No PV during this window typically, but handle it
        flows['pv_curtailed'] = pv_available
        
        return E_bat_new, flows
    
    def _electrolyser_window(self, E_bat, pv_available, spot_price):
        """
        Morning electrolyser supply window (default 05:00-10:00)
        - Battery exclusively powers electrolyser
        - No grid purchase allowed
        - If insufficient battery energy, electrolyser runs at reduced power or shuts down
        """
        flows = self._init_flows()
        
        # Required power for electrolyser
        P_ely_rated = self.electrolyser_params["P_ely"]
        min_load_ratio = self.electrolyser_params["min_load_ratio"]
        P_ely_min = P_ely_rated * min_load_ratio
        
        # Available battery energy for discharge
        E_available = E_bat - self.E_min
        eta_discharge = self.battery_params["eta_discharge"]
        
        # Maximum power we can supply from battery this hour
        P_max_from_battery = min(
            self.battery_params["P_discharge_max"],
            E_available / 1.0 * eta_discharge
        )
        
        # Determine electrolyser operation
        if P_max_from_battery >= P_ely_rated:
            # Full power operation
            P_ely_actual = P_ely_rated
            P_shortage = 0
        elif P_max_from_battery >= P_ely_min:
            # Reduced power operation
            P_ely_actual = P_max_from_battery
            P_shortage = P_ely_rated - P_ely_actual
        else:
            # Shutdown - cannot meet minimum load
            P_ely_actual = 0
            P_shortage = P_ely_rated
        
        # Discharge battery to supply electrolyser
        if P_ely_actual > 0:
            E_discharge = P_ely_actual * 1.0
            E_bat_new = E_bat - E_discharge / eta_discharge
        else:
            E_bat_new = E_bat
        
        flows['battery_to_ely'] = P_ely_actual
        flows['ely_power'] = P_ely_actual
        flows['ely_shortage'] = P_shortage
        
        # Curtail any PV during electrolyser window (could be modified to charge battery)
        flows['pv_curtailed'] = pv_available
        
        return E_bat_new, flows
    
    def _idle_state(self, pv_available):
        """Idle state - no operations, curtail any PV"""
        flows = self._init_flows()
        flows['pv_curtailed'] = pv_available
        return flows
    
    def _init_flows(self):
        """Initialize power flow dictionary"""
        return {
            'pv_to_battery': 0.0,
            'grid_to_battery': 0.0,
            'battery_to_grid': 0.0,
            'battery_to_ely': 0.0,
            'pv_curtailed': 0.0,
            'ely_power': 0.0,
            'ely_shortage': 0.0,
        }
    
    def _calculate_summary(self, df):
        """Calculate summary statistics from simulation results"""
        
        # Energy flows (MWh)
        total_pv_available = df['pv_available_mw'].sum()
        total_pv_to_battery = df['pv_to_battery_mw'].sum()
        total_pv_curtailed = df['pv_curtailed_mw'].sum()
        total_grid_to_battery = df['grid_to_battery_mw'].sum()
        total_battery_to_grid = df['battery_to_grid_mw'].sum()
        total_battery_to_ely = df['battery_to_ely_mw'].sum()
        
        # Economics
        total_revenue = df['revenue_arbitrage'].sum()
        total_cost = df['cost_charging'].sum()
        total_penalties = df['cost_penalties'].sum()
        net_profit = total_revenue - total_cost - total_penalties
        
        # Hydrogen production
        total_h2_kg = df['ely_h2_production_kg'].sum()
        total_h2_tonnes = total_h2_kg / 1000
        
        # Battery statistics
        avg_soc = df['soc'].mean()
        min_soc = df['soc'].min()
        max_soc = df['soc'].max()
        
        # Estimate battery cycles (full equivalent cycles)
        # Sum of absolute energy throughput / (2 * capacity)
        energy_throughput = df['battery_to_grid_mw'].sum() + df['battery_to_ely_mw'].sum()
        equivalent_cycles = energy_throughput / self.battery_params["E_bat_max"]
        
        # Electrolyser statistics
        ely_hours = (df['ely_power_mw'] > 0).sum()
        ely_shortage_hours = (df['ely_shortage_mw'] > 0).sum()
        ely_capacity_factor = df['ely_power_mw'].sum() / (self.electrolyser_params["P_ely"] * len(df))
        
        # Window statistics
        window_counts = df['window_type'].value_counts().to_dict()
        
        summary = {
            # Energy flows
            'total_pv_available_mwh': total_pv_available,
            'total_pv_to_battery_mwh': total_pv_to_battery,
            'total_pv_curtailed_mwh': total_pv_curtailed,
            'pv_utilization_rate': total_pv_to_battery / total_pv_available if total_pv_available > 0 else 0,
            'total_grid_to_battery_mwh': total_grid_to_battery,
            'total_battery_to_grid_mwh': total_battery_to_grid,
            'total_battery_to_ely_mwh': total_battery_to_ely,
            
            # Economics
            'total_revenue_eur': total_revenue,
            'total_cost_eur': total_cost,
            'total_penalties_eur': total_penalties,
            'net_profit_eur': net_profit,
            'avg_arbitrage_price_eur_mwh': df[df['battery_to_grid_mw'] > 0]['spot_price_eur_mwh'].mean() if (df['battery_to_grid_mw'] > 0).any() else 0,
            'avg_charging_price_eur_mwh': df[df['grid_to_battery_mw'] > 0]['spot_price_eur_mwh'].mean() if (df['grid_to_battery_mw'] > 0).any() else 0,
            
            # Hydrogen production
            'total_h2_production_kg': total_h2_kg,
            'total_h2_production_tonnes': total_h2_tonnes,
            
            # Battery statistics
            'avg_soc': avg_soc,
            'min_soc': min_soc,
            'max_soc': max_soc,
            'equivalent_cycles': equivalent_cycles,
            
            # Electrolyser statistics
            'ely_operating_hours': ely_hours,
            'ely_shortage_hours': ely_shortage_hours,
            'ely_capacity_factor': ely_capacity_factor,
            
            # Window statistics
            'window_counts': window_counts,
            
            # Per unit metrics
            'revenue_per_mwh_discharged': total_revenue / total_battery_to_grid if total_battery_to_grid > 0 else 0,
            'cost_per_mwh_charged': total_cost / total_grid_to_battery if total_grid_to_battery > 0 else 0,
            'net_profit_per_cycle': net_profit / equivalent_cycles if equivalent_cycles > 0 else 0,
            'h2_cost_eur_per_kg': (total_cost - total_revenue + total_penalties) / total_h2_kg if total_h2_kg > 0 else 0,
        }
        
        return summary


def load_pv_profile(pv_data, timestamps):
    """
    Load or generate PV production profile
    
    Args:
        pv_data: Can be:
            - DataFrame with 'timestamp' and 'pv_mw' columns
            - Dict with monthly energy values (will be distributed hourly)
            - None (will generate typical profile)
        timestamps: Hourly timestamps for the simulation
    
    Returns:
        Array of PV production [MW] for each timestamp
    """
    if pv_data is None:
        # Generate typical PV profile (simplified)
        return generate_typical_pv_profile(timestamps)
    elif isinstance(pv_data, pd.DataFrame):
        # Use provided hourly data
        return pv_data['pv_mw'].values
    elif isinstance(pv_data, dict):
        # Distribute monthly energy across hours
        return distribute_monthly_pv_to_hourly(pv_data, timestamps)
    else:
        raise ValueError("Invalid pv_data format")


def generate_typical_pv_profile(timestamps, peak_power_mw=10.0):
    """
    Generate a typical PV production profile with seasonal variation
    
    Simple model: PV follows sine curve during daylight hours
    """
    pv_profile = np.zeros(len(timestamps))
    
    for i, ts in enumerate(timestamps):
        hour = ts.hour
        month = ts.month
        
        # Seasonal capacity factor (higher in summer)
        seasonal_factor = 0.7 + 0.3 * np.sin((month - 3) * np.pi / 6)
        
        # Daily production curve (sine between sunrise and sunset)
        if 6 <= hour <= 20:
            hour_angle = (hour - 13) * np.pi / 14  # Peak at 13:00
            pv_profile[i] = peak_power_mw * seasonal_factor * np.cos(hour_angle) ** 2
        else:
            pv_profile[i] = 0
    
    return pv_profile


def distribute_monthly_pv_to_hourly(monthly_pv_mwh, timestamps):
    """
    Distribute monthly PV energy values to hourly profile
    using typical daily production curve
    
    Args:
        monthly_pv_mwh: Dict with month names as keys and energy (MWh) as values
        timestamps: Array-like of datetime objects
    """
    pv_profile = np.zeros(len(timestamps))
    
    # Month name mapping
    month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                   'July', 'August', 'September', 'October', 'November', 'December']
    
    # Create daily production curve (normalized)
    daily_curve = np.zeros(24)
    for hour in range(6, 21):  # 6am to 9pm
        hour_angle = (hour - 13) * np.pi / 14
        daily_curve[hour] = np.cos(hour_angle) ** 2
    
    daily_curve = daily_curve / daily_curve.sum()  # Normalize
    
    for i, ts in enumerate(timestamps):
        # Convert numpy.datetime64 to pandas Timestamp if needed
        if isinstance(ts, np.datetime64):
            ts = pd.Timestamp(ts)
        
        month_name = month_names[ts.month - 1]
        if month_name in monthly_pv_mwh:
            # Get monthly energy
            monthly_energy = monthly_pv_mwh[month_name]
            
            # Days in this month
            if ts.month == 2:
                days_in_month = 28  # Simplified
            elif ts.month in [4, 6, 9, 11]:
                days_in_month = 30
            else:
                days_in_month = 31
            
            # Daily average energy
            daily_energy = monthly_energy / days_in_month
            
            # Hourly power
            pv_profile[i] = daily_energy * daily_curve[ts.hour]
    
    return pv_profile


def distribute_monthly_pv_to_hourly_from_dataframe(monthly_pv_mwh, data_df):
    """
    Distribute monthly PV energy values to hourly profile using DataFrame with Mois and Heure columns
    
    Args:
        monthly_pv_mwh: Dict with month names as keys and energy (MWh) as values
        data_df: DataFrame with 'Mois' (month name) and 'Heure' (hour) columns
    
    Returns:
        Array of PV power [MW] for each hour in the dataframe
    """
    n_hours = len(data_df)
    pv_profile = np.zeros(n_hours)
    
    # Days in each month (simplified, not accounting for leap years)
    days_in_month = {
        'January': 31, 'February': 28, 'March': 31, 'April': 30,
        'May': 31, 'June': 30, 'July': 31, 'August': 31,
        'September': 30, 'October': 31, 'November': 30, 'December': 31
    }
    
    # Create daily production curve (normalized)
    daily_curve = np.zeros(24)
    for hour in range(6, 21):  # 6am to 9pm
        hour_angle = (hour - 13) * np.pi / 14
        daily_curve[hour] = np.cos(hour_angle) ** 2
    
    daily_curve = daily_curve / daily_curve.sum()  # Normalize
    
    # Process each row
    for i in range(n_hours):
        month_name = data_df.iloc[i]['Mois']
        hour = int(data_df.iloc[i]['Heure'])
        
        if month_name in monthly_pv_mwh:
            # Get monthly energy
            monthly_energy = monthly_pv_mwh[month_name]
            
            # Days in this month
            days = days_in_month.get(month_name, 30)
            
            # Daily average energy
            daily_energy = monthly_energy / days
            
            # Hourly power
            pv_profile[i] = daily_energy * daily_curve[hour]
    
    return pv_profile

