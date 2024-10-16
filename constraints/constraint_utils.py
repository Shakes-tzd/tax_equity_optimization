# constraints/constraint_utils.py

from constraints.models import Fund, ConstraintType, FundModel, ConstraintModel, Condition
from typing import List
import pandas as pd

def initialize_constraint_caps(fund: Fund, fund_capacity: float) -> FundModel:
    """
    Initialize constraint capacities and track constrained values.
    """
    constraints = []

    for constraint in fund.constraints:
        if not constraint.active or constraint.constraint_type == ConstraintType.EXCLUSION:
            continue

        upper_bound = constraint.upper_bound
        if upper_bound is None:
            continue

        if not isinstance(fund_capacity, (int, float)) or fund_capacity <= 0:
            raise ValueError(f"Invalid fund capacity: {fund_capacity}")

        cap = upper_bound * fund_capacity if upper_bound <= 1 else upper_bound

        for condition in constraint.conditions:
            attribute = condition.type
            values = condition.values

            if constraint.apply_per_value:
                if isinstance(values, dict):
                    for value, ub in values.items():
                        if ub is not None:
                            value_cap = ub * fund_capacity if ub <= 1 else ub
                            constraints.append(ConstraintModel(
                                name=f"{constraint.name}_{value}",
                                attribute=attribute,
                                upper_bound=value_cap,
                                values=[value],
                                is_group=False
                            ))
                else:
                    for value in values:
                        constraints.append(ConstraintModel(
                            name=f"{constraint.name}_{value}",
                            attribute=attribute,
                            upper_bound=cap,
                            values=[value],
                            is_group=False
                        ))
            else:
                constraints.append(ConstraintModel(
                    name=constraint.name,
                    attribute=attribute,
                    upper_bound=cap,
                    values=values,
                    is_group=True
                ))

    return FundModel(
        name=fund.name,
        target_capacity=fund_capacity,
        constraints=constraints
    )

def apply_exclusions(df: pd.DataFrame, exclusion_constraints: List[Condition]) -> pd.DataFrame:
    """
    Apply exclusion constraints to the DataFrame.
    """
    for condition in exclusion_constraints:
        attribute = condition.type
        values = condition.values
        df = df[~df[attribute].isin(values)]
    return df
