# optimizer.py

from typing import Dict, List, Tuple
from constraints.models import Fund, ConstraintType
from constraints.constraint_utils import initialize_constraint_caps, apply_exclusions
import pandas as pd

def allocate_systems_to_funds(
    df_systems: pd.DataFrame,
    df_backlog: pd.DataFrame,
    funds: Dict[str, Fund],
    fund_targets: Dict[str, float]
) -> Dict[str, Dict]:
    """
    Allocate systems to multiple funds.

    Args:
        df_systems: DataFrame of all systems, including those already allocated to funds.
        df_backlog: DataFrame of backlog systems to be allocated.
        funds: Dictionary of Fund objects.
        fund_targets: Dictionary of target capacities per fund.

    Returns:
        allocation_results: Dictionary with fund names as keys, each containing:
            - allocated_systems: DataFrame of systems allocated to the fund.
            - infeasible_constraints: List of constraints that were violated or prevented allocations.
            - constraint_analysis: DataFrame with constraint usage information.
    """
    allocation_results = {}

    # Step 1: Prepare Fund Data
    fund_data = {}
    for fund_name in funds:
        fund = funds[fund_name]
        target_capacity = fund_targets[fund_name]

        # Systems already allocated to the fund
        df_allocated = df_systems[df_systems['Asset Portfolio - Customer'] == fund_name]

        # Current allocation
        current_allocation = df_allocated['FMV'].sum()

        # Remaining capacity
        remaining_capacity = target_capacity - current_allocation

        if remaining_capacity <= 0:
            remaining_capacity = 0.0

        # Initialize constraints
        attribute_caps, constrained_values = initialize_constraint_caps(fund, target_capacity)

        # Calculate current attribute allocations
        attribute_allocations = {}
        for attribute in attribute_caps:
            allocations = df_allocated.groupby(attribute)['FMV'].sum()
            attribute_allocations[attribute] = allocations.to_dict()

            # Adjust remaining capacities per attribute value
            for value in attribute_caps[attribute]:
                current_usage = attribute_allocations[attribute].get(value, 0.0)
                attribute_caps[attribute][value] -= current_usage
                if attribute_caps[attribute][value] < 0:
                    attribute_caps[attribute][value] = 0.0

        # Store fund data
        fund_data[fund_name] = {
            'fund': fund,
            'remaining_capacity': remaining_capacity,
            'attribute_caps': attribute_caps,
            'constrained_values': constrained_values,
            'allocated_systems': df_allocated.copy(),
            'infeasible_constraints': set()
        }

    # Step 2: Build Candidate Allocations
    candidate_allocations = []

    # Exclude systems that are already allocated to any fund
    allocated_systems_ids = df_systems[df_systems['Asset Portfolio - Customer'].isin(fund_names)].index
    df_backlog = df_backlog.drop(index=allocated_systems_ids, errors='ignore')

    # Apply exclusion constraints upfront
    for fund_name in fund_data:
        fund_info = fund_data[fund_name]
        fund = fund_info['fund']
        df_backlog = apply_exclusions(df_backlog, fund)

    for idx, system in df_backlog.iterrows():
        system_fmv = system['FMV']
        system_id = idx  # Assuming index is unique identifier
        for fund_name, fund_info in fund_data.items():
            # Skip if fund has no remaining capacity
            if fund_info['remaining_capacity'] < system_fmv:
                continue

            feasible = True
            attribute_caps = fund_info['attribute_caps']
            for attribute in attribute_caps:
                value = system[attribute]
                cap = attribute_caps[attribute].get(value)
                if cap is not None:
                    if cap < system_fmv:
                        feasible = False
                        fund_info['infeasible_constraints'].add(f"Constraint '{attribute}={value}' exceeded capacity.")
                        break
                elif '__OTHERS__' in attribute_caps[attribute]:
                    if value not in fund_info['constrained_values'].get(attribute, set()):
                        cap = attribute_caps[attribute]['__OTHERS__']
                        if cap < system_fmv:
                            feasible = False
                            fund_info['infeasible_constraints'].add(f"Constraint '{attribute}=__OTHERS__' exceeded capacity.")
                            break
                else:
                    # No applicable constraint, assume unlimited capacity
                    continue

            if feasible:
                candidate_allocations.append({
                    'system_index': idx,
                    'fund_name': fund_name,
                    'system_fmv': system_fmv
                })

    # Step 3: Sort Candidate Allocations
    candidate_allocations.sort(key=lambda x: -x['system_fmv'])

    # Step 4: Allocation Loop
    unallocated_systems = set(df_backlog.index)
    for candidate in candidate_allocations:
        system_idx = candidate['system_index']
        fund_name = candidate['fund_name']
        system_fmv = candidate['system_fmv']

        if system_idx not in unallocated_systems:
            continue

        fund_info = fund_data[fund_name]
        if fund_info['remaining_capacity'] < system_fmv:
            continue

        system = df_backlog.loc[system_idx]
        feasible = True
        attribute_caps = fund_info['attribute_caps']
        for attribute in attribute_caps:
            value = system[attribute]
            cap = attribute_caps[attribute].get(value)
            if cap is not None:
                if cap < system_fmv:
                    feasible = False
                    break
            elif '__OTHERS__' in attribute_caps[attribute]:
                if value not in fund_info['constrained_values'].get(attribute, set()):
                    cap = attribute_caps[attribute]['__OTHERS__']
                    if cap < system_fmv:
                        feasible = False
                        break

        if feasible:
            # Allocate system to fund
            fund_info['allocated_systems'] = fund_info['allocated_systems'].append(system)
            fund_info['remaining_capacity'] -= system_fmv

            # Update attribute allocations
            for attribute in attribute_caps:
                value = system[attribute]
                if value in attribute_caps[attribute]:
                    attribute_caps[attribute][value] -= system_fmv
                elif '__OTHERS__' in attribute_caps[attribute]:
                    if value not in fund_info['constrained_values'].get(attribute, set()):
                        attribute_caps[attribute]['__OTHERS__'] -= system_fmv

            # Remove system from unallocated_systems
            unallocated_systems.remove(system_idx)

    # Step 5: Compile Results
    for fund_name, fund_info in fund_data.items():
        allocated_systems = fund_info['allocated_systems']
        infeasible_constraints = list(fund_info['infeasible_constraints'])

        # Prepare constraint analysis
        constraint_analysis = []
        attribute_caps = fund_info['attribute_caps']
        for attribute in attribute_caps:
            for value, remaining_cap in attribute_caps[attribute].items():
                original_cap = initialize_constraint_caps(fund_info['fund'], fund_targets[fund_name])[0][attribute][value]
                usage = original_cap - remaining_cap
                usage_percentage = usage / original_cap if original_cap > 0 else 0
                constraint_analysis.append({
                    'constraint_name': f"{attribute} = {value}",
                    'usage': usage,
                    'upper_bound': original_cap,
                    'remaining_capacity': remaining_cap,
                    'usage_percentage': usage_percentage
                })
        constraint_analysis_df = pd.DataFrame(constraint_analysis)

        allocation_results[fund_name] = {
            'allocated_systems': allocated_systems,
            'infeasible_constraints': infeasible_constraints,
            'constraint_analysis': constraint_analysis_df
        }

    return allocation_results

# # optimizer.py

# from typing import Dict, List, Tuple
# from constraints.models import Fund, ConstraintType
# from constraints.constraint_utils import initialize_constraint_caps, apply_exclusions
# import pandas as pd

# def allocate_systems_to_fund(
#     systems_df: pd.DataFrame,
#     fund: Fund,
#     fund_capacity: float
# ) -> Tuple[pd.DataFrame, List[str], pd.DataFrame]:
#     """
#     Allocate systems to a fund based on constraints, maximizing total FMV.
#     Returns allocated systems, a list of infeasible constraints if any, and constraint usage data.
#     """
#     infeasible_constraints = []

#     # Apply exclusion constraints
#     systems_df = apply_exclusions(systems_df, fund)
    
#     # Initialize constraint capacities
#     attribute_caps, constrained_values = initialize_constraint_caps(fund, fund_capacity)
    
#     # Initialize allocations
#     remaining_fund_capacity = fund_capacity
    
#     # Track allocated FMV per attribute value
#     attribute_allocations = {attr: {val: 0.0 for val in vals.keys()} for attr, vals in attribute_caps.items()}
    
#     # Prepare systems data
#     systems_df = systems_df.copy()
    
#     # Determine applicable constraints per attribute using vectorized operations
#     for attribute in attribute_caps:
#         attribute_caps_values = set(attribute_caps[attribute].keys())
#         constrained_values_set = constrained_values.get(attribute, set())
        
#         def get_applicable_constraint(value):
#             if value in attribute_caps_values:
#                 return value
#             elif '__OTHERS__' in attribute_caps_values and value not in constrained_values_set:
#                 return '__OTHERS__'
#             else:
#                 return None  # No applicable constraint
        
#         systems_df[attribute + '_constraint'] = systems_df[attribute].apply(get_applicable_constraint)
    
#     # Exclude systems exceeding fund capacity
#     systems_df = systems_df[systems_df['FMV'] <= remaining_fund_capacity]
#     if systems_df.empty:
#         infeasible_constraints.append("No systems can be allocated within the fund capacity.")
#         constraint_analysis_df = pd.DataFrame()
#         allocated_systems = pd.DataFrame()
#         return allocated_systems, infeasible_constraints, constraint_analysis_df
    
#     # Sort systems by FMV ascending (can be adjusted based on strategy)
#     systems_df = systems_df.sort_values(by='FMV')
    
#     # Reset index for efficient access
#     systems_df.reset_index(drop=True, inplace=True)
    
#     # Convert attribute allocations to DataFrames for efficient updates
#     attribute_allocations_df = {}
#     for attribute in attribute_caps:
#         attribute_allocations_df[attribute] = pd.Series(attribute_allocations[attribute])
    
#     # Initialize allocation mask
#     allocation_mask = [False] * len(systems_df)
    
#     # Allocate systems
#     for idx, system in systems_df.iterrows():
#         system_fmv = system['FMV']
#         feasible = True
        
#         # Check fund capacity
#         if remaining_fund_capacity < system_fmv:
#             break  # Fund capacity exhausted
        
#         # Check constraints
#         for attribute in attribute_caps:
#             value = system[attribute + '_constraint']
#             if value is not None:
#                 current_allocation = attribute_allocations_df[attribute][value]
#                 cap = attribute_caps[attribute][value]
#                 if (current_allocation + system_fmv) > cap:
#                     feasible = False
#                     break
#         if feasible:
#             # Allocate system
#             allocation_mask[idx] = True
#             remaining_fund_capacity -= system_fmv
#             # Update allocations
#             for attribute in attribute_caps:
#                 value = system[attribute + '_constraint']
#                 if value is not None:
#                     attribute_allocations_df[attribute][value] += system_fmv
#         else:
#             continue  # System cannot be allocated due to constraints
    
#     # Get allocated systems
#     allocated_systems = systems_df[allocation_mask]
    
#     # Prepare constraint usage DataFrame
#     constraint_analysis = []
#     for attribute in attribute_caps:
#         allocations = attribute_allocations_df[attribute]
#         for value in attribute_caps[attribute]:
#             usage = allocations[value]
#             upper_bound = attribute_caps[attribute][value]
#             remaining_capacity = upper_bound - usage
#             usage_percentage = usage / upper_bound if upper_bound > 0 else 0
#             constraint_analysis.append({
#                 'constraint_name': f"{attribute} = {value}",
#                 'usage': usage,
#                 'upper_bound': upper_bound,
#                 'remaining_capacity': remaining_capacity,
#                 'usage_percentage': usage_percentage
#             })
#     constraint_analysis_df = pd.DataFrame(constraint_analysis)
    
#     # Identify globally infeasible constraints using groupby
#     infeasible_constraints_set = set()
#     for attribute in attribute_caps:
#         total_fmv_per_value = systems_df.groupby(attribute + '_constraint')['FMV'].sum()
#         for value in attribute_caps[attribute]:
#             total_available = total_fmv_per_value.get(value, 0)
#             cap = attribute_caps[attribute][value]
#             if total_available > cap:
#                 infeasible_constraints_set.add(f"Constraint '{attribute}={value}' is globally infeasible.")
#     infeasible_constraints.extend(infeasible_constraints_set)
    
#     return allocated_systems, infeasible_constraints, constraint_analysis_df