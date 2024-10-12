# utils/data_processing.py

import json
import pandas as pd
from typing import Dict, Union
from constraints.models import Fund, Constraint, Condition, ConstraintCategory, ConstraintType
def filter_dict(original_dict, keys_to_keep):
    return {k: original_dict[k] for k in keys_to_keep if k in original_dict}
def load_constraints(json_data: Union[Dict, str]) -> Dict[str, Fund]:
    if isinstance(json_data, str):
        # If a string is provided, assume it's a file path
        with open(json_data, 'r') as f:
            data = json.load(f)
    else:
        # If a dict is provided, use it directly
        data = json_data

    funds = {}
    for fund_name, fund_data in data.items():
        constraints = []
        for constraint_data in fund_data.get('constraints', []):
            conditions = []
            for condition_data in constraint_data['conditions']:
                condition = Condition(
                    type=condition_data['type'],
                    condition=condition_data['condition'],
                    values=condition_data.get('values', []),
                    value=condition_data.get('value')
                )
                conditions.append(condition)
            constraint = Constraint(
                name=constraint_data['name'],
                category=constraint_data.get('category'),
                constraint_type=ConstraintType(constraint_data['constraint_type']),
                attribute=constraint_data['attribute'],
                measure=constraint_data.get('measure', 'FMV'),
                upper_bound=constraint_data.get('upper_bound'),
                aggregation=constraint_data.get('aggregation'),
                apply_per_value=constraint_data.get('apply_per_value', False),
                conditions=conditions,
                group_name=constraint_data.get('group_name'),
                current_allocation=constraint_data.get('current_allocation', 0.0),
                remaining_capacity=constraint_data.get('remaining_capacity', 0.0),
                active=constraint_data.get('active', True)
            )
            constraints.append(constraint)
        fund = Fund(
            name=fund_name,
            capacity=fund_data['capacity'],
            constraints=constraints
        )
        funds[fund_name] = fund
    return funds

def load_systems_data(file_path: str) -> pd.DataFrame:
    """
    Load systems data from a Parquet file.
    """
    df_systems = pd.read_parquet(file_path)
    df_systems = df_systems.rename(columns={"Project Purchase Price": "FMV"})
    return df_systems