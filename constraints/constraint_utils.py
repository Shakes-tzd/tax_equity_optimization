# constraints/constraint_utils.py

from typing import Dict, List, Tuple
from constraints.models import Fund, Constraint, ConstraintType
import pandas as pd

def initialize_constraint_caps(fund: Fund, fund_capacity: float) -> Tuple[Dict[str, Dict], Dict[str, set]]:
    """
    Initialize constraint capacities and track constrained values.
    """
    attribute_caps = {}
    constrained_values = {}

    for constraint in fund.constraints:
        if not constraint.active:
            continue

        if constraint.constraint_type == ConstraintType.EXCLUSION:
            continue  # Exclusions are handled separately

        fund_capacity = fund.capacity
        upper_bound = constraint.upper_bound

        for condition in constraint.conditions:
            attribute = condition.type
            if attribute not in attribute_caps:
                attribute_caps[attribute] = {}
                constrained_values[attribute] = set()

            if constraint.apply_per_value:
                values = condition.values
                if isinstance(values, dict):
                    for value, ub in values.items():
                        cap = ub * fund_capacity if ub <= 1 else ub
                        attribute_caps[attribute][value] = cap
                        if value != "__OTHERS__":
                            constrained_values[attribute].add(value)
                else:
                    ub = upper_bound
                    cap = ub * fund_capacity if ub <= 1 else ub
                    for value in values:
                        attribute_caps[attribute][value] = cap
                        constrained_values[attribute].add(value)
            else:
                # Group constraint
                values = condition.values
                cap = upper_bound * fund_capacity if upper_bound <= 1 else upper_bound
                for value in values:
                    attribute_caps[attribute][value] = cap
                    constrained_values[attribute].add(value)

    return attribute_caps, constrained_values

def apply_exclusions(systems_df: pd.DataFrame, fund: Fund) -> pd.DataFrame:
    """
    Apply exclusion constraints to filter out ineligible systems.
    """
    for constraint in fund.constraints:
        if not constraint.active:
            continue
        if constraint.constraint_type != ConstraintType.EXCLUSION:
            continue
        for condition in constraint.conditions:
            attribute = condition.type
            values = condition.values
            if isinstance(values, list):
                systems_df = systems_df[~systems_df[attribute].isin(values)]
    return systems_df