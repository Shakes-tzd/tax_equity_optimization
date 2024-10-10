from typing import Dict, List
import pandas as pd
from constraints.models import Fund, Constraint
from utils.constraint_processing import build_where_clause
from utils.data_processing import execute_query, update_allocations

def run_optimization(con, funds: Dict[str, Fund], fund_targets: Dict[str, Dict[str, float]]):
    allocation_results = {}

    for fund_name, fund in funds.items():
        if fund_name not in fund_targets:
            continue

        remaining_capacity = fund_targets[fund_name]['target_amount'] - fund_targets[fund_name]['allocated_amount']

        if remaining_capacity <= 0:
            allocation_results[fund_name] = {'allocated_fmv': 0.0}
            continue

        where_clause = build_where_clause(fund.constraints)
        query = f"SELECT * FROM backlog WHERE allocated_fund IS NULL AND {where_clause}"
        df_fund = execute_query(con, query)

        if df_fund.empty:
            allocation_results[fund_name] = {'allocated_fmv': 0.0}
            continue

        df_allocated = allocate_systems(df_fund, remaining_capacity, fund.constraints)
        
        if not df_allocated.empty:
            update_allocations(con, df_allocated, fund_name)
            allocated_fmv = df_allocated['FMV'].sum()
            allocation_results[fund_name] = {'allocated_fmv': allocated_fmv}
        else:
            allocation_results[fund_name] = {'allocated_fmv': 0.0}

    return allocation_results

def allocate_systems(df_fund: pd.DataFrame, remaining_capacity: float, constraints: List[Constraint]) -> pd.DataFrame:
    # Implementation of system allocation logic
    # This is a placeholder and should be replaced with your actual allocation algorithm
    df_fund = df_fund.sort_values(by='FMV', ascending=False)
    allocated_systems = []
    total_allocated = 0

    for _, system in df_fund.iterrows():
        if total_allocated + system['FMV'] > remaining_capacity:
            break
        allocated_systems.append(system)
        total_allocated += system['FMV']

    return pd.DataFrame(allocated_systems)