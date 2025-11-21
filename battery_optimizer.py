"""
Battery Energy Management System Optimizer
Hourly simulation of PV-Battery-Electrolyser system with arbitrage
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from battery_config import (
    DEFAULT_BATTERY_PARAMS, DEFAULT_TIME_WINDOWS, DEFAULT_ELECTROLYSER_PARAMS,
    PENALTY_PARAMS, is_hour_in_window, get_window_duration
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
                 penalty_params=None, pv_price=0.0):
        """
        Initialize the battery optimizer
        
        Args:
            battery_params: Dictionary of battery technical parameters
            time_windows: Dictionary of operational time windows (hours)
            electrolyser_params: Dictionary of electrolyser parameters
            penalty_params: Dictionary with penalty parameters
            pv_price: Price of PV electricity [€/MWh]
        """
        self.battery_params = battery_params or DEFAULT_BATTERY_PARAMS.copy()
        self.time_windows = time_windows or DEFAULT_TIME_WINDOWS.copy()
        self.electrolyser_params = electrolyser_params or DEFAULT_ELECTROLYSER_PARAMS.copy()
        self.penalty_params = penalty_params or PENALTY_PARAMS.copy()
        self.pv_price = pv_price
        
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
            'battery_available_mwh': np.zeros(n_hours),  # Replaces pv_available_mw
            'pv_profile_mw': pv_profile_mw.copy(),       # Keep raw PV data
            'spot_price_eur_mwh': spot_prices_eur_mwh,
            
            # Battery state
            'soc': np.zeros(n_hours),
            'energy_stored_mwh': np.zeros(n_hours),
            
            # Power flows [MW] (positive = charging, negative = discharging)
            'battery_charge_mw': np.zeros(n_hours),
            'battery_discharge_mw': np.zeros(n_hours),
            'pv_curtailed_mw': np.zeros(n_hours),
            
            # Electrolyser
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
            #E_bat *= (1 - self.battery_params["self_discharge_rate"])
            
            # Determine operational window
            window_type = self._get_window_type(hour_of_day)
            results['window_type'][t] = window_type
            
            # Apply operational rules based on window
            if window_type == "pv_charge":
                # Check if this is the last hour of the PV charging window
                is_last_hour = (hour_of_day == self.time_windows["pv_charge_end"])
                E_bat, flows = self._pv_charge_window(E_bat, pv_available, spot_price, is_last_hour)
                
            elif window_type == "sell_to_grid":
                E_bat, flows = self._sell_to_grid_window(E_bat, pv_available, spot_price)
                
            elif window_type == "grid_charging":
                E_bat, flows = self._grid_charging_window(E_bat, pv_available, spot_price)
                
            elif window_type == "electrolyser":
                E_bat, flows = self._electrolyser_window(E_bat, pv_available, spot_price)
            
            else:
                # Should not happen if windows cover 24 hours
                # Default to idle behavior (no flows)
                flows = self._init_flows()
                flows['pv_curtailed'] = pv_available
            
            # Store results
            E_bat = np.clip(E_bat, self.E_min, self.E_max)
            results['energy_stored_mwh'][t] = E_bat
            results['battery_available_mwh'][t] = E_bat  # Track battery energy state
            results['soc'][t] = E_bat / self.battery_params["E_bat_max"]
            
            results['battery_charge_mw'][t] = flows['battery_charge']
            results['battery_discharge_mw'][t] = flows['battery_discharge']
            results['pv_curtailed_mw'][t] = flows['pv_curtailed']
            results['ely_shortage_mw'][t] = flows['ely_shortage']
            
            # Calculate economics
            # Revenue from selling to grid (arbitrage)
            # Only applies if window is sell_to_grid
            if window_type == 'sell_to_grid':
                revenue = flows['battery_discharge'] * spot_price
            elif window_type == 'electrolyser':
                # Revenue from supplying electrolyser (avoided cost at spot price)
                revenue = flows['battery_discharge'] * spot_price
            else:
                revenue = 0.0
            results['revenue_arbitrage'][t] = revenue
            
            # Cost of buying from grid
            # Only applies if window is grid_charging
            if window_type == 'grid_charging':
                cost_grid = flows['battery_charge'] * spot_price
            else:
                cost_grid = 0.0
            results['cost_charging'][t] = cost_grid
            
            # Penalties
            penalty_cost = flows['ely_shortage'] * self.penalty_params['electrolyser_shortage_penalty']
            results['cost_penalties'][t] = penalty_cost
            
            # Net cashflow
            results['net_cashflow'][t] = revenue - cost_grid - penalty_cost
            
            # Hydrogen production
            # If electrolyser window, power comes from battery discharge
            if window_type == 'electrolyser' and flows['battery_discharge'] > 0:
                # Power supplied to electrolyser = battery discharge
                P_ely_actual = flows['battery_discharge']
                h2_kg = (P_ely_actual * 1000) / self.electrolyser_params['specific_consumption']
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
        elif is_hour_in_window(hour, tw["sell_to_grid_start"], tw["sell_to_grid_end"]):
            return "sell_to_grid"
        elif is_hour_in_window(hour, tw["grid_charging_start"], tw["grid_charging_end"]):
            return "grid_charging"
        else:
            return "idle"
    
    def _pv_charge_window(self, E_bat, pv_available, spot_price, is_last_hour=False):
        """
        PV-priority charging window (default 10:00-16:00)
        - Simplified: Charge at constant power (P_charge_max) each hour
        - PV charge = charge power (constant charging)
        - No curtailment calculation (simplified)
        """
        flows = self._init_flows()
        
        # Calculate how much battery can accept
        E_available = self.E_max - E_bat
        P_charge_limit = self.battery_params["P_charge_max"]
        eta_charge = self.battery_params["eta_charge"]
        
        # Simplified: Constant charge power each hour (not dependent on actual PV)
        # Charge at maximum power or remaining capacity
        P_charge = min(P_charge_limit, E_available / 1.0)  # 1.0 hour timestep
        E_charge = P_charge * 1.0
        
        # Apply charging efficiency
        E_bat_new = E_bat + E_charge * eta_charge
        
        # Simplified: No curtailment tracking
        flows['battery_charge'] = P_charge
        flows['pv_curtailed'] = 0.0
        
        # Force fully charged state if this is the last hour of the window
        if is_last_hour and E_bat_new < self.E_max:
            # Calculate energy needed to reach full charge
            E_needed = self.E_max - E_bat_new
            
            # We assume this energy is supplied (e.g., from grid or just assumed)
            # To keep energy balance somewhat consistent in reports, we add it to charge flow
            # even if it exceeds power limits
            # Note: We divide by eta_charge to get the input energy required
            additional_charge_mw = E_needed / eta_charge
            flows['battery_charge'] += additional_charge_mw
            
            E_bat_new = self.E_max
        
        return E_bat_new, flows
    
    def _sell_to_grid_window(self, E_bat, pv_available, spot_price):
        """
        Evening sell to grid window (default 16:00-23:00)
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
        
        flows['battery_discharge'] = P_discharge
        flows['pv_curtailed'] = pv_curtailed
        
        return E_bat_new, flows
    
    def _grid_charging_window(self, E_bat, pv_available, spot_price):
        """
        Spot grid charging window (default 23:00-05:00)
        - Charge from grid at spot market prices to prepare for electrolyser
        - Always charge when in this window
        """
        flows = self._init_flows()
        
        # Calculate how much battery can accept
        E_available = self.E_max - E_bat
        P_charge_limit = self.battery_params["P_charge_max"]
        eta_charge = self.battery_params["eta_charge"]
        
        # Charge at maximum rate
        P_charge = min(P_charge_limit, E_available / eta_charge / 1.0)
        E_charge = P_charge * 1.0 * eta_charge
        
        E_bat_new = E_bat + E_charge
        
        flows['battery_charge'] = P_charge
        
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
        
        flows['battery_discharge'] = P_ely_actual
        flows['ely_shortage'] = P_shortage
        
        # Curtail any PV during electrolyser window (could be modified to charge battery)
        flows['pv_curtailed'] = pv_available
        
        return E_bat_new, flows
    
    def _init_flows(self):
        """Initialize power flow dictionary"""
        return {
            'battery_charge': 0.0,
            'battery_discharge': 0.0,
            'pv_curtailed': 0.0,
            'ely_shortage': 0.0,
        }
    
    def _calculate_summary(self, df):
        """Calculate summary statistics from simulation results"""
        
        # Energy flows (MWh)
        total_pv_available = df['pv_profile_mw'].sum()
        
        # PV Charging: only when window is 'pv_charge'
        df_pv_charge = df[df['window_type'] == 'pv_charge']
        total_pv_to_battery = df_pv_charge['battery_charge_mw'].sum()
        
        # Grid Charging: only when window is 'grid_charging'
        df_grid_charge = df[df['window_type'] == 'grid_charging']
        total_grid_to_battery = df_grid_charge['battery_charge_mw'].sum()
        
        # Grid Discharge: only when window is 'sell_to_grid'
        df_grid_discharge = df[df['window_type'] == 'sell_to_grid']
        total_battery_to_grid = df_grid_discharge['battery_discharge_mw'].sum()
        
        # Ely Discharge: only when window is 'electrolyser'
        df_ely_discharge = df[df['window_type'] == 'electrolyser']
        total_battery_to_ely = df_ely_discharge['battery_discharge_mw'].sum()
        
        total_pv_curtailed = df['pv_curtailed_mw'].sum()
        
        # Economics
        # Arbitrage revenue from selling to grid
        total_revenue_arbitrage = df['revenue_arbitrage'].sum()
        # Grid charging cost (battery charged from grid)
        total_cost_charging = df['cost_charging'].sum()
        
        # Penalties (e.g. electrolyser shortages)
        total_penalties = df['cost_penalties'].sum()

        # Additional simplified economics to match dashboard "Financial Flows":
        # - Treat PV charging as having a cost equal to PV Price (€/MWh)
        # - Treat battery supply to electrolyser as an avoided grid cost (value)
        total_pv_cost = (df_pv_charge['battery_charge_mw'] * self.pv_price).sum()
        total_ely_value = (df_ely_discharge['battery_discharge_mw'] * df_ely_discharge['spot_price_eur_mwh']).sum()

        # Aggregated revenue and cost consistent with Operational Windows analysis
        total_revenue = total_revenue_arbitrage + total_ely_value
        total_cost = total_cost_charging + total_pv_cost

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
        energy_throughput = total_battery_to_grid + total_battery_to_ely
        equivalent_cycles = energy_throughput / self.battery_params["E_bat_max"]
        
        # Electrolyser statistics
        # Re-derive ely_power from discharge
        ely_power_series = df.apply(
            lambda row: row['battery_discharge_mw'] if row['window_type'] == 'electrolyser' else 0, axis=1
        )
        ely_hours = (ely_power_series > 0).sum()
        ely_shortage_hours = (df['ely_shortage_mw'] > 0).sum()
        ely_capacity_factor = ely_power_series.sum() / (self.electrolyser_params["P_ely"] * len(df))
        
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
            'total_revenue_arbitrage_eur': total_revenue_arbitrage,
            'total_cost_charging_eur': total_cost_charging,
            'total_pv_cost_eur': total_pv_cost,
            'total_ely_value_eur': total_ely_value,
            'total_penalties_eur': total_penalties,
            'net_profit_eur': net_profit,
            'avg_arbitrage_price_eur_mwh': df_grid_discharge[df_grid_discharge['battery_discharge_mw'] > 0]['spot_price_eur_mwh'].mean() if (df_grid_discharge['battery_discharge_mw'] > 0).any() else 0,
            'avg_charging_price_eur_mwh': df_grid_charge[df_grid_charge['battery_charge_mw'] > 0]['spot_price_eur_mwh'].mean() if (df_grid_charge['battery_charge_mw'] > 0).any() else 0,
            
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
            # Define H2 cost as pure production cost (charging costs only), not net of arbitrage revenue
            'h2_cost_eur_per_kg': (total_cost / total_h2_kg) if total_h2_kg > 0 else 0,
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
            if days_in_month.get(month_name):
                days = days_in_month.get(month_name)
            else:
                days = 30
            
            # Daily average energy
            daily_energy = monthly_energy / days
            
            # Hourly power
            pv_profile[i] = daily_energy * daily_curve[hour]
    
    return pv_profile

