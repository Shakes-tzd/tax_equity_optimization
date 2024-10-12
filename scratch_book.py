# utils/data_processing.py
import json
import pandas as pd
from constraints.config import CONSTRAINTS_DIR, DEFAULT_CONSTRAINTS_FILE
import os
from typing import Dict, Union
from constraints.models import Fund, Constraint, Condition, ConstraintCategory, ConstraintType



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
        for constraint_data in fund_data['constraints']:
            conditions = []
            for condition_data in constraint_data['conditions']:
                condition = Condition(**condition_data)
                conditions.append(condition)
            constraint = Constraint(
                name=constraint_data['name'],
                category=ConstraintCategory(constraint_data['category']),
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
                active=True
            )
            constraints.append(constraint)
        fund = Fund(
            name=fund_name,
            capacity=fund_data['capacity'],
            constraints=constraints
        )
        funds[fund_name] = fund
    return funds

# optimization/runner.py
import streamlit as st
from typing import Dict, List
from constraints.models import Fund
from optimization.optimizer import allocate_systems_greedy
import pandas as pd
from utils.data_processing import load_constraints, execute_query
from utils.visualization import display_constraint_analysis
import duckdb
import io
import json


def run_optimization(
    con,
    funds: Dict[str, Fund],
    fund_targets: Dict[str, Dict[str, float]],
    selected_funds: List[str],
) -> Dict[str, Dict[str, float]]:
    allocation_results = {}

    for fund_name in selected_funds:
        fund = funds[fund_name]
        target_data = fund_targets[fund_name]

        allocated_amount = target_data["allocated_amount"]
        target_amount = target_data["target_amount"]
        fund_remaining_capacity = target_amount - allocated_amount

        if fund_remaining_capacity <= 0:
            allocation_results[fund_name] = {"allocated_fmv": 0.0}
            continue
        query = f"""
            SELECT * FROM backlog
            WHERE allocated_fund IS NULL"""


        # Filter systems eligible for the fund
        eligible_systems = con.execute(query).fetch_df()
        # Allocate systems
        allocated_systems_df = allocate_systems_greedy(
            eligible_systems, fund, fund_remaining_capacity
        )

        if not allocated_systems_df.empty:
            allocated_fmv = allocated_systems_df["FMV"].sum()
            allocation_results[fund_name] = {"allocated_fmv": allocated_fmv}
            # Update systems_df to mark allocated systems
            eligible_systems.loc[allocated_systems_df.index, "Allocated Fund"] = fund_name
        else:
            allocation_results[fund_name] = {"allocated_fmv": 0.0}

    return allocation_results


def optimization_runner():
    st.title("Run Optimization")
        # Upload Parquet file
    with st.expander("Upload Required Files:"):
        uploaded_parquet = st.file_uploader("Upload Parquet File", type="parquet")
        if uploaded_parquet is not None:
            st.success("Parquet file uploaded successfully!")
            # Read the Parquet file into a Pandas DataFrame
            try:
                parquet_bytes = uploaded_parquet.read()
                parquet_buffer = io.BytesIO(parquet_bytes)
                df_systems = pd.read_parquet(parquet_buffer)
                df_systems = df_systems.rename(columns={"Project Purchase Price": "FMV"})
                st.write("Systems data loaded successfully!")
            except Exception as e:
                st.error(f"Failed to read Parquet file: {e}")
                return
        else:
            st.info("Please upload the Parquet file to proceed.")
            return
        uploaded_json = st.file_uploader("Upload Constraints JSON", type="json", key="json_upload_opt")
        if uploaded_json is not None:
            try:
                json_data = json.load(uploaded_json)
                funds = load_constraints(json_data)
                if funds:
                    st.success("Constraints file uploaded successfully!")
                else:
                    st.error("Failed to parse JSON constraints file.")
                    return
            except json.JSONDecodeError:
                st.error("Invalid JSON file. Please upload a valid JSON file.")
                return
        else:
            st.info("Please upload the JSON constraints file to proceed.")
            return
        

        

    with st.expander("Preview Data"):
        st.dataframe(df_systems.head(), use_container_width=True)

    # Connect to DuckDB in-memory database
    con = duckdb.connect(database=':memory:', read_only=False)

    # Register the DataFrame as a DuckDB table
    con.register('systems', df_systems)

    # Create the backlog table
    con.execute("""
        CREATE TABLE backlog AS
        SELECT *, CAST(NULL AS VARCHAR) AS allocated_fund
        FROM systems
        WHERE "Asset Portfolio - Customer" = 'Sunnova TEP Developer LLC'
          AND "Stage" != 'Substantial'
    """)



    # Select funds to optimize
    selected_funds = st.multiselect("Select Funds to Optimize", list(funds.keys()))

    if not selected_funds:
        st.warning("Please select at least one fund to optimize.")
        return

    # Set target percentages for selected funds
    fund_targets = {}
    for fund_name in selected_funds:
        fund = funds[fund_name]
        st.subheader(f"Fund: {fund_name}")

        # Display current allocation
        current_allocation = execute_query(con, f"SELECT SUM(FMV) FROM systems WHERE \"Asset Portfolio - Customer\" = '{fund_name}'")
        current_allocation = current_allocation.iloc[0, 0] if not current_allocation.empty else 0
        current_percentage = (current_allocation / fund.capacity) * 100 if fund.capacity > 0 else 0

        st.write(f"Current Allocation: ${current_allocation:,.2f} ({current_percentage:.2f}%)")

        # Set target percentage
        # Slider for target percentage
        max_percentage = min(current_percentage * 2 if current_percentage > 0 else 100.0, 200.0)
        target_percentage = st.slider(
                f"Set Target Percentage for {fund_name}",
                min_value=current_percentage,
                max_value=max_percentage,
                value=current_percentage,
                step=1.0,
                help="Select the target percentage of the fund capacity."
            )

            # Calculate and display the target FMV amount
        target_amount = (target_percentage / 100.0) * fund.capacity
        # st.write(f"**Target FMV Amount:** ${target_amount:,.2f}")
        fund_targets[fund_name] = {
            'capacity': fund.capacity,
            'allocated_amount': current_allocation,
            'target_percentage': target_percentage,
            'target_amount': target_amount
        }

    if st.button("Run Optimization"):
        results = run_optimization(con, funds, fund_targets,selected_funds)

        st.subheader("Optimization Results")
        for fund_name, result in results.items():
            st.write(f"**{fund_name}**")
            allocated_fmv = result['allocated_fmv']
            target_amount = fund_targets[fund_name]['target_amount']
            percentage_of_target = (allocated_fmv / target_amount) * 100 if target_amount > 0 else 0

            st.write(f"Allocated FMV: ${allocated_fmv:,.2f}")
            st.write(f"Target FMV: ${target_amount:,.2f}")
            st.write(f"Percentage of Target Met: {percentage_of_target:.2f}%")
            st.progress(min(percentage_of_target / 100, 1.0))

        # Display constraint analysis
        st.subheader("Constraint Analysis")
        for fund_name in selected_funds:
            constraint_analysis = execute_query(con, f"SELECT * FROM constraint_analysis WHERE fund = '{fund_name}'")
            if not constraint_analysis.empty:
                st.write(f"**{fund_name}**")
                display_constraint_analysis(constraint_analysis)

    con.close()

# optimization/optimizer.py
from typing import Dict, List
import pandas as pd
from constraints.models import Fund, Constraint
# from utils.constraint_processing import build_where_clause
from utils.data_processing import execute_query, update_allocations

# optimization/optimizer.py
from typing import List, Dict, Tuple
from constraints.models import Fund, Constraint, ConstraintType

PER_CUSTOMER_FMV_LIMIT = 125000

def initialize_constraint_caps(constraints: List[Constraint], fund_capacity: float) -> Tuple[Dict[str, float], Dict[str, Dict]]:
    constraint_caps = {}
    constraint_details = {}
    for constraint in constraints:
        if not constraint.active:
            continue
        measure = constraint.measure
        constraint_name = constraint.name
        upper_bound = constraint.upper_bound
        conditions = constraint.conditions
        apply_per_value = constraint.apply_per_value
        if apply_per_value:
            for condition in conditions:
                values = condition.values
                if isinstance(values, dict):
                    for value, ub in values.items():
                        cname = f"{constraint_name} - {value}"
                        ub_absolute = ub * fund_capacity if ub < 1 else ub
                        constraint_caps[cname] = ub_absolute
                        constraint_details[cname] = {
                            'attribute': condition.type,
                            'value': value,
                        }
                else:
                    ub_absolute = upper_bound * fund_capacity if upper_bound and upper_bound < 1 else upper_bound
                    for value in values:
                        cname = f"{constraint_name} - {value}"
                        constraint_caps[cname] = ub_absolute
                        constraint_details[cname] = {
                            'attribute': condition.type,
                            'value': value,
                        }
        else:
            ub_absolute = upper_bound * fund_capacity if upper_bound and upper_bound < 1 else upper_bound
            cname = constraint_name
            constraint_caps[cname] = ub_absolute
            constraint_details[cname] = {
                'attribute': None,
                'values': [],
            }
    return constraint_caps, constraint_details

def apply_constraints(systems_df: pd.DataFrame, constraints: List[Constraint], constraint_caps: Dict[str, float], constraint_details: Dict[str, Dict]) -> pd.DataFrame:
    # Precompute constraint masks
    for cname, details in constraint_details.items():
        attribute = details.get('attribute')
        value = details.get('value')
        if attribute and value:
            mask = systems_df[attribute] == value
            systems_df.loc[mask, 'Applicable Constraints'] = systems_df.loc[mask, 'Applicable Constraints'].apply(lambda x: x + [cname])
    return systems_df

def allocate_systems(systems_df: pd.DataFrame, fund: Fund, fund_remaining_capacity: float, constraint_caps: Dict[str, float]) -> pd.DataFrame:
    allocated_systems = []
    total_allocated_fmv = 0.0

    # Sort systems by FMV descending
    systems_df = systems_df.sort_values(by='FMV', ascending=False).reset_index(drop=True)

    # Iterate over systems
    for idx, system in systems_df.iterrows():
        system_fmv = system['FMV']
        customer = system['Customer Account']
        applicable_constraints = system.get('Applicable Constraints', [])

        if total_allocated_fmv + system_fmv > fund_remaining_capacity:
            continue

        # Check per-customer FMV limit
        customer_fmv = system.get('Customer FMV', 0.0)
        if customer_fmv + system_fmv > PER_CUSTOMER_FMV_LIMIT:
            continue

        # Check constraint capacities
        can_allocate = True
        for cname in applicable_constraints:
            if constraint_caps[cname] < system_fmv:
                can_allocate = False
                break

        if not can_allocate:
            continue

        # Allocate system
        allocated_systems.append(system)
        total_allocated_fmv += system_fmv

        # Update constraint capacities
        for cname in applicable_constraints:
            constraint_caps[cname] -= system_fmv

        # Update customer's allocated FMV
        systems_df.at[idx, 'Customer FMV'] = customer_fmv + system_fmv

        if total_allocated_fmv >= fund_remaining_capacity:
            break

    return pd.DataFrame(allocated_systems)

def allocate_systems_greedy(systems_df: pd.DataFrame, fund: Fund, fund_remaining_capacity: float) -> pd.DataFrame:
    # Initialize constraint capacities and details
    constraint_caps, constraint_details = initialize_constraint_caps(fund.constraints, fund.capacity)

    # Add columns to systems_df for constraints and customer FMV
    systems_df['Applicable Constraints'] = [[] for _ in range(len(systems_df))]
    systems_df['Customer FMV'] = 0.0

    # Apply constraints to systems
    systems_df = apply_constraints(systems_df, fund.constraints, constraint_caps, constraint_details)

    # Allocate systems
    allocated_systems_df = allocate_systems(systems_df, fund, fund_remaining_capacity, constraint_caps)

    return allocated_systems_df


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

# constraints/models.py

from typing import List, Optional, Union, Dict
from pydantic import BaseModel, Field
from enum import Enum

class ConstraintCategory(str, Enum):
    GEOGRAPHIC = "Geographic"
    EQUIPMENT = "Equipment"
    PARTNER = "Partner"

class ConstraintType(str, Enum):
    UPPER_BOUND = "Upper Bound"
    EXCLUSION = "Exclusion"

class Condition(BaseModel):
    type: str
    condition: str
    values: Union[List[str], Dict[str, float]] = Field(default_factory=list)
    value: Optional[str] = None

class Constraint(BaseModel):
    name: str
    category: ConstraintCategory
    constraint_type: ConstraintType
    attribute: str
    measure: str = "FMV"
    upper_bound: Optional[float] = None
    aggregation: Optional[str] = None
    apply_per_value: bool = False
    conditions: List[Condition]
    group_name: Optional[str] = None
    current_allocation: float = 0.0
    remaining_capacity: float = 0.0
    active: bool = True

class Fund(BaseModel):
    name: str
    capacity: float
    constraints: List[Constraint]

#main.py
import streamlit as st
from constraints.editor import constraint_editor
from optimization.runner import optimization_runner

def display_fund_summary(fund_name: str, capacity: float, allocated_amount: float, target_amount: float):
    """Display a summary of a fund's allocation status."""
    st.subheader(f"Fund: {fund_name}")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Capacity", f"${capacity:,.2f}")
    
    with col2:
        allocated_percentage = (allocated_amount / capacity) * 100 if capacity > 0 else 0
        st.metric("Allocated", f"${allocated_amount:,.2f}", f"{allocated_percentage:.2f}%")
    
    with col3:
        target_percentage = (target_amount / capacity) * 100 if capacity > 0 else 0
        st.metric("Target", f"${target_amount:,.2f}", f"{target_percentage:.2f}%")

def constraint_input(constraint, key):
    """Render inputs for a single constraint."""
    st.text_input("Name", value=constraint.name, key=f"name_{key}")
    st.selectbox("Category", options=list(constraint.category), key=f"category_{key}")
    st.selectbox("Type", options=list(constraint.constraint_type), key=f"type_{key}")
    st.text_input("Attribute", value=constraint.attribute, key=f"attribute_{key}")
    st.number_input("Upper Bound", value=constraint.upper_bound, min_value=0.0, max_value=1.0, step=0.01, key=f"upper_bound_{key}")
    st.checkbox("Apply Per Value", value=constraint.apply_per_value, key=f"apply_per_value_{key}")

def condition_input(condition, key):
    """Render inputs for a single condition."""
    st.text_input("Type", value=condition.type, key=f"condition_type_{key}")
    st.selectbox("Condition", options=['Equals', 'Not Equals', 'Contains', 'Not Contains', 'Greater Than', 'Less Than'], key=f"condition_{key}")
    
    if isinstance(condition.values, list):
        st.text_area("Values", value="\n".join(condition.values), key=f"values_{key}")
    elif isinstance(condition.values, dict):
        for value, bound in condition.values.items():
            st.number_input(f"Bound for {value}", value=bound, min_value=0.0, max_value=1.0, step=0.01, key=f"bound_{value}_{key}")
    else:
        st.text_input("Value", value=condition.value, key=f"value_{key}")

def main():
    st.set_page_config(page_title="Solar System Allocation", layout="wide")
    
    st.sidebar.title("Solar System Allocation")
    page = st.sidebar.radio("Choose a page", ["Constraint Editor", "Run Optimization"])

    if page == "Constraint Editor":
        constraint_editor()
    elif page == "Run Optimization":
        optimization_runner()

if __name__ == "__main__":
    main()