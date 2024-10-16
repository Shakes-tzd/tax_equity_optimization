# optimizer.py

import pandas as pd
from typing import Dict
from constraints.models import Fund, ConstraintType
from constraints.constraint_utils import initialize_constraint_caps, apply_exclusions
from collections import defaultdict

def allocate_systems_to_funds(
    df_systems: pd.DataFrame,
    df_backlog: pd.DataFrame,
    funds: Dict[str, Fund],
    fund_targets: Dict[str, float]
) -> Dict[str, Dict]:
    """
    Allocate systems to multiple funds using a Greedy Algorithm.
    """
    # Apply exclusion constraints
    for fund in funds.values():
        exclusion_constraints = [
            constraint for constraint in fund.constraints
            if constraint.constraint_type == ConstraintType.EXCLUSION and constraint.active
        ]
        if exclusion_constraints:
            df_backlog = apply_exclusions(df_backlog, exclusion_constraints)
    
    # Initialize fund data
    fund_data = {}
    for fund_name, fund in funds.items():
        # Existing allocations
        existing_systems = df_systems[df_systems['Asset Portfolio - Customer'] == fund_name]
        current_allocation = existing_systems['FMV'].sum()
        remaining_capacity = max(0.0, fund_targets[fund_name] - current_allocation)
        
        # Initialize constraints
        fund_model = initialize_constraint_caps(fund, fund_targets[fund_name])
        constraint_caps = {}
        for constraint in fund_model.constraints:
            cap = constraint.upper_bound
            # Adjust cap based on existing usage
            if constraint.is_group:
                usage = existing_systems[existing_systems[constraint.attribute].isin(constraint.values)]['FMV'].sum()
            else:
                usage = existing_systems[existing_systems[constraint.attribute] == constraint.values[0]]['FMV'].sum()
            remaining_cap = max(0.0, cap - usage)
            constraint_caps[constraint.name] = remaining_cap
        
        fund_data[fund_name] = {
            'fund': fund,
            'fund_model': fund_model,
            'remaining_capacity': remaining_capacity,
            'constraint_caps': constraint_caps,
            'allocated_systems': pd.DataFrame(),
            'existing_systems': existing_systems.copy(),
        }
    
    # Calculate priorities
    df_backlog['Priority'] = df_backlog['FMV']  # Simple priority based on FMV
    
    # Sort systems by priority
    df_backlog_sorted = df_backlog.sort_values(by='Priority', ascending=False)
    
    # Allocate systems
    allocated_systems_ids = set()
    for idx, system in df_backlog_sorted.iterrows():
        system_fmv = system['FMV']
        if idx in allocated_systems_ids:
            continue
        for fund_name, fund_info in fund_data.items():
            if fund_info['remaining_capacity'] < system_fmv:
                continue
            # Check constraints
            constraints_satisfied = True
            for constraint in fund_info['fund_model'].constraints:
                cap_remaining = fund_info['constraint_caps'][constraint.name]
                if constraint.is_group:
                    if system[constraint.attribute] in constraint.values:
                        if cap_remaining < system_fmv:
                            constraints_satisfied = False
                            break
                else:
                    if system[constraint.attribute] == constraint.values[0]:
                        if cap_remaining < system_fmv:
                            constraints_satisfied = False
                            break
            if constraints_satisfied:
                # Allocate system to fund
                fund_info['allocated_systems'] = pd.concat(
                    [fund_info['allocated_systems'], system.to_frame().T], ignore_index=True
                )
                fund_info['remaining_capacity'] -= system_fmv
                # Update constraint capacities
                for constraint in fund_info['fund_model'].constraints:
                    if constraint.is_group:
                        if system[constraint.attribute] in constraint.values:
                            fund_info['constraint_caps'][constraint.name] -= system_fmv
                    else:
                        if system[constraint.attribute] == constraint.values[0]:
                            fund_info['constraint_caps'][constraint.name] -= system_fmv
                allocated_systems_ids.add(idx)
                break  # Move to next system
    
    # Prepare results
    allocation_results = {}
    for fund_name, fund_info in fund_data.items():
        # Filter out empty DataFrames before concatenation
        dfs_to_concat = [df for df in [fund_info['existing_systems'], fund_info['allocated_systems']] if not df.empty]
        if dfs_to_concat:
            allocated_systems = pd.concat(dfs_to_concat, ignore_index=True)
        else:
            # Create an empty DataFrame with the desired columns
            allocated_systems = pd.DataFrame(columns=df_systems.columns)
        
        # Prepare constraint analysis
        constraint_analysis = []
        for constraint in fund_info['fund_model'].constraints:
            usage = constraint.upper_bound - fund_info['constraint_caps'][constraint.name]
            upper_bound = constraint.upper_bound
            remaining_capacity = fund_info['constraint_caps'][constraint.name]
            usage_percentage = (usage / upper_bound) if upper_bound > 0 else 0.0
            # Update constraint_name to show the value(s)
            constraint_values_str = ', '.join(constraint.values) if constraint.values else 'N/A'
            constraint_analysis.append({
                'constraint_name': constraint_values_str,
                'usage': usage,
                'upper_bound': upper_bound,
                'remaining_capacity': remaining_capacity,
                'usage_percentage': usage_percentage
            })
        constraint_analysis_df = pd.DataFrame(constraint_analysis)
        allocation_results[fund_name] = {
            'allocated_systems': allocated_systems,
            'infeasible_constraints': [],  # Greedy algorithm may not capture infeasibility
            'constraint_analysis': constraint_analysis_df
        }

    return allocation_results
