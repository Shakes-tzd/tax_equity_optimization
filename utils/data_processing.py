import json
import pandas as pd
from constraints.config import CONSTRAINTS_DIR, DEFAULT_CONSTRAINTS_FILE
from constraints.models import Fund
import os
from typing import Dict

def load_constraints(file_name=None):
    if file_name is None:
        file_path = DEFAULT_CONSTRAINTS_FILE
    else:
        file_path = os.path.join(CONSTRAINTS_DIR, file_name)
    
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    return {name: Fund(**fund_data) for name, fund_data in data.items()}

def save_constraints(funds: Dict[str, Fund], file_name='updated_constraints.json'):
    file_path = os.path.join(CONSTRAINTS_DIR, file_name)
    data = {name: fund.dict() for name, fund in funds.items()}
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)

def execute_query(con, query: str) -> pd.DataFrame:
    return con.execute(query).fetch_df()

def update_allocations(con, df_allocated: pd.DataFrame, fund_name: str):
    allocated_ids = df_allocated['System Name'].tolist()
    placeholders = ','.join(['?'] * len(allocated_ids))
    query = f"UPDATE backlog SET allocated_fund = ? WHERE \"System Name\" IN ({placeholders})"
    con.execute(query, [fund_name] + allocated_ids)