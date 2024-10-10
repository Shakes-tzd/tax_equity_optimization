# optimization/optimizer.py

from typing import Dict, List, Tuple
from constraints.models import Fund, ConstraintType
from constraints.constraint_utils import initialize_constraint_caps, apply_exclusions
import pandas as pd

def allocate_systems_to_fund(systems_df: pd.DataFrame, fund: Fund) -> Tuple[pd.DataFrame, List[str], pd.DataFrame]:
    """
    Allocate systems to a fund based on constraints, maximizing total FMV.
    Returns allocated systems, a list of infeasible constraints if any, and constraint usage data.
    """
    infeasible_constraints = []
    # Apply exclusion constraints
    systems_df = apply_exclusions(systems_df, fund)

    # Initialize constraint capacities
    attribute_caps, constrained_values = initialize_constraint_caps(fund)

    # Initialize allocations
    allocated_systems = pd.DataFrame()
    remaining_fund_capacity = fund.capacity

    # Keep track of allocated FMV per constraint
    constraint_usage = {}  # constraint -> allocated FMV
    constraint_upper_bounds = {}  # constraint -> upper bound

    # Prepare constraints data
    for attribute, caps in attribute_caps.items():
        for value, cap in caps.items():
            constraint = (attribute, value)
            constraint_usage[constraint] = 0.0
            constraint_upper_bounds[constraint] = cap

    # Prepare systems data
    systems_df = systems_df.copy()
    systems_df['Applicable Constraints'] = [[] for _ in range(len(systems_df))]
    systems_df['System Index'] = systems_df.index

    # For each system, determine applicable constraints
    for idx, system in systems_df.iterrows():
        applicable_constraints = []
        for attribute, caps in attribute_caps.items():
            value = system[attribute]
            if value in caps:
                applicable_constraints.append((attribute, value))
            elif '__OTHERS__' in caps and value not in constrained_values.get(attribute, set()):
                applicable_constraints.append((attribute, '__OTHERS__'))
        systems_df.at[idx, 'Applicable Constraints'] = applicable_constraints

    # Sort systems by FMV descending
    systems_df = systems_df.sort_values(by='FMV', ascending=False)

    # Initialize capacities
    constraint_capacities = constraint_upper_bounds.copy()

    # Allocate systems
    allocated_indices = []
    for idx, system in systems_df.iterrows():
        system_fmv = system['FMV']
        applicable_constraints = system['Applicable Constraints']
        feasible = True
        # Check fund capacity
        if remaining_fund_capacity < system_fmv:
            feasible = False
        else:
            # Check constraints
            for constraint in applicable_constraints:
                cap = constraint_capacities.get(constraint, 0)
                if cap < system_fmv:
                    feasible = False
                    break
        if feasible:
            # Allocate system
            allocated_indices.append(idx)
            remaining_fund_capacity -= system_fmv
            # Update constraints
            for constraint in applicable_constraints:
                constraint_capacities[constraint] -= system_fmv
                constraint_usage[constraint] += system_fmv
        else:
            # Could not allocate due to constraints
            for constraint in applicable_constraints:
                cap = constraint_capacities.get(constraint, 0)
                if cap < system_fmv:
                    infeasible_constraints.append(f"Constraint on {constraint[0]}='{constraint[1]}' exceeded capacity.")
            if remaining_fund_capacity < system_fmv:
                infeasible_constraints.append(f"Fund capacity exceeded.")
    allocated_systems = systems_df.loc[allocated_indices]

    # Prepare constraint usage DataFrame
    constraint_analysis = []
    for constraint, usage in constraint_usage.items():
        upper_bound = constraint_upper_bounds[constraint]
        remaining_capacity = upper_bound - usage
        usage_percentage = usage / upper_bound if upper_bound > 0 else 0
        constraint_analysis.append({
            'constraint_name': f"{constraint[0]} = {constraint[1]}",
            'usage': usage,
            'upper_bound': upper_bound,
            'remaining_capacity': remaining_capacity,
            'usage_percentage': usage_percentage
        })
    constraint_analysis_df = pd.DataFrame(constraint_analysis)

    return allocated_systems, list(set(infeasible_constraints)), constraint_analysis_df