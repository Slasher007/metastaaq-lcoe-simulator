def calculate_lcoe(pv_energy_mwh, spot_energy_dict, ppa_energy_dict, pv_price, spot_price, ppa_price, go_enabled=False, go_cost_per_mwh=0.0):
    """Calculate the Levelized Cost of Energy based on energy mix and prices"""
    total_cost = 0
    total_energy = 0
    
    # Calculate effective spot price including GO cost if enabled
    effective_spot_price = spot_price + (go_cost_per_mwh if go_enabled else 0.0)
    
    for month in pv_energy_mwh.keys():
        # Get energy amounts for each source
        pv_energy = pv_energy_mwh[month]
        spot_energy = spot_energy_dict.get(month, 0)
        ppa_energy = ppa_energy_dict.get(month, 0)
        
        # Calculate costs (use effective spot price including GO)
        pv_cost = pv_energy * pv_price
        spot_cost = spot_energy * effective_spot_price
        ppa_cost = ppa_energy * ppa_price
        
        # Add to totals
        total_cost += pv_cost + spot_cost + ppa_cost
        total_energy += pv_energy + spot_energy + ppa_energy
    
    return total_cost / total_energy if total_energy > 0 else 0
