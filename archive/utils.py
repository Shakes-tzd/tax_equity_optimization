# utils.py
import streamlit as st
import duckdb
import pandas as pd
import yaml
from great_tables import GT, html
import re
from typing import List, Dict, Union, Optional
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
    measure: str
    upper_bound: float
    conditions: List[Condition]
    group_name: Optional[str] = None
    aggregation: Optional[str] = None
    apply_per_value: bool = False
    current_allocation: float = 0.0
    remaining_capacity: float = 0.0
    active: bool = True

class Fund(BaseModel):
    name: str
    capacity: float
    constraints: List[Constraint]

def load_constraints(json_data: Dict) -> Dict[str, Fund]:
    funds = {}
    for fund_name, fund_data in json_data.items():
        constraints = [Constraint(**constraint_data) for constraint_data in fund_data['constraints']]
        funds[fund_name] = Fund(name=fund_name, capacity=fund_data['capacity'], constraints=constraints)
    return funds

def save_constraints(funds: Dict[str, Fund]) -> Dict:
    return {fund_name: fund.dict() for fund_name, fund in funds.items()}

def render_constraint_editor(constraint: Constraint, key: str):
    st.subheader(f"Editing Constraint: {constraint.name}")

    constraint.active = st.checkbox("Active", value=constraint.active, key=f"active_{key}")
    constraint.name = st.text_input("Constraint Name", value=constraint.name, key=f"name_{key}")
    constraint.category = st.selectbox("Category", options=list(ConstraintCategory), index=list(ConstraintCategory).index(constraint.category), key=f"category_{key}")
    constraint.constraint_type = st.selectbox("Constraint Type", options=list(ConstraintType), index=list(ConstraintType).index(constraint.constraint_type), key=f"constraint_type_{key}")
    constraint.attribute = st.text_input("Attribute", value=constraint.attribute, key=f"attribute_{key}")
    constraint.measure = st.text_input("Measure", value=constraint.measure, key=f"measure_{key}")
    constraint.group_name = st.text_input("Group Name", value=constraint.group_name or "", key=f"group_name_{key}")
    constraint.aggregation = st.selectbox("Aggregation Method", options=['', 'sum', 'average', 'max', 'min'], index=['', 'sum', 'average', 'max', 'min'].index(constraint.aggregation or ''), key=f"aggregation_{key}")
    constraint.apply_per_value = st.checkbox("Apply Per Value", value=constraint.apply_per_value, key=f"apply_per_value_{key}")
    constraint.upper_bound = st.number_input("Upper Bound", min_value=0.0, max_value=1.0, value=constraint.upper_bound, step=0.01, key=f"upper_bound_{key}")

    st.markdown("### Conditions")
    for i, condition in enumerate(constraint.conditions):
        st.markdown(f"**Condition {i+1}**")
        condition.type = st.text_input("Type", value=condition.type, key=f"type_{key}_{i}")
        condition.condition = st.selectbox("Condition", options=['Equals', 'Not Equals', 'Contains', 'Not Contains', 'Greater Than', 'Less Than'], index=['Equals', 'Not Equals', 'Contains', 'Not Contains', 'Greater Than', 'Less Than'].index(condition.condition), key=f"condition_{key}_{i}")
        
        if isinstance(condition.values, list):
            values_input = st.text_area("Values (one per line or comma-separated)", value='\n'.join(condition.values), key=f"values_{key}_{i}")
            condition.values = [v.strip() for v in values_input.replace(',', '\n').split('\n') if v.strip()]
        elif isinstance(condition.values, dict):
            st.markdown("Value-specific upper bounds:")
            new_values = {}
            for value, bound in condition.values.items():
                new_bound = st.number_input(f"Upper bound for {value}", min_value=0.0, max_value=1.0, value=bound, step=0.01, key=f"value_bound_{key}_{i}_{value}")
                new_values[value] = new_bound
            condition.values = new_values
        else:
            condition.value = st.text_input("Value", value=condition.value or "", key=f"value_{key}_{i}")

        if st.button(f"Remove Condition {i+1}", key=f"remove_condition_{key}_{i}"):
            del constraint.conditions[i]
            st.experimental_rerun()

    if st.button("Add Condition", key=f"add_condition_{key}"):
        constraint.conditions.append(Condition(type="", condition="Equals"))
        st.experimental_rerun()

    return constraint

def render_fund_editor(funds: Dict[str, Fund]):
    selected_fund = st.selectbox("Select Fund to Edit", list(funds.keys()))
    fund = funds[selected_fund]

    st.header(f"Editing Fund: {selected_fund}")

    fund.capacity = st.number_input("Fund Capacity", min_value=0.0, value=fund.capacity, step=1000000.0, format="%.2f")

    if st.button(f"Add Constraint to {selected_fund}", key=f"add_constraint_{selected_fund}"):
        new_constraint = Constraint(
            name="New Constraint",
            category=ConstraintCategory.GEOGRAPHIC,
            constraint_type=ConstraintType.UPPER_BOUND,
            attribute="",
            measure="FMV",
            upper_bound=0.0,
            conditions=[Condition(type="", condition="Equals")]
        )
        fund.constraints.append(new_constraint)
        st.experimental_rerun()

    for i, constraint in enumerate(fund.constraints):
        with st.expander(f"Constraint: {constraint.name}"):
            fund.constraints[i] = render_constraint_editor(constraint, f"{selected_fund}_{i}")

            if st.button(f"Remove Constraint", key=f"remove_constraint_{selected_fund}_{i}"):
                del fund.constraints[i]
                st.experimental_rerun()

    return funds


def load_constraints(json_data: Dict) -> Dict[str, Fund]:
    funds = {}
    for fund_name, fund_data in json_data.items():
        constraints = [Constraint(**constraint_data) for constraint_data in fund_data['constraints']]
        funds[fund_name] = Fund(name=fund_name, capacity=fund_data['capacity'], constraints=constraints)
    return funds

def save_constraints(funds: Dict[str, Fund]) -> Dict:
    return {fund_name: fund.dict() for fund_name, fund in funds.items()}




def parse_yaml(yaml_string):
    """Parse a YAML string into a Python object."""
    try:
        return yaml.safe_load(yaml_string)
    except yaml.YAMLError as e:
        st.error(f"Error parsing YAML: {e}")
        return None

def stringify_yaml(yaml_data):
    """Convert a Python object into a YAML string."""
    try:
        return yaml.dump(yaml_data, default_flow_style=False, sort_keys=False)
    except yaml.YAMLError as e:
        st.error(f"Error converting to YAML: {e}")
        return None

def run_optimization(con, yaml_data, fund_targets):
    """Run the optimization process using DuckDB and the constraints."""
    st.write("Running optimization...")

    allocation_results = {}

    try:
        # Allocate systems to funds
        allocate_systems(con, yaml_data, fund_targets, allocation_results)

        # Retrieve final allocations
        final_allocations = con.execute("SELECT * FROM backlog WHERE allocated_fund IS NOT NULL").fetch_df()

        if not final_allocations.empty:
            st.write("Allocations:")
            st.dataframe(final_allocations.head())
            # Download the allocations as CSV
            csv_data = final_allocations.to_csv(index=False)
            st.download_button(
                label="Download Allocations CSV",
                data=csv_data,
                file_name="allocations.csv",
                mime="text/csv"
            )
        else:
            st.warning("No allocations were made.")

        st.success("Optimization completed successfully!")

    except Exception as e:
        st.error(f"Optimization failed: {e}")

    return allocation_results
# utils.py

# import streamlit as st
# import duckdb
# import pandas as pd
# import yaml

def allocate_systems(con, yaml_data, fund_targets, allocation_results):
    """Allocate systems to funds based on constraints and analyze constraint impacts."""
    for fund, fund_data in yaml_data.items():
        if fund not in fund_targets:
            continue  # Skip funds not selected

        st.write(f"Allocating systems to fund: {fund}")
        constraints = fund_data.get('constraints', [])

        fund_capacity = fund_targets[fund]['capacity']
        allocated_amount = fund_targets[fund]['allocated_amount']
        target_percentage = fund_targets[fund]['target_percentage']
        target_amount = fund_targets[fund]['target_amount']
        remaining_capacity = target_amount - allocated_amount

        if remaining_capacity <= 0:
            st.warning(f"Fund {fund} has already reached the target capacity.")
            # Record zero allocation
            allocation_results[fund] = {
                'allocated_fmv': 0.0
            }
            continue

        # Build the WHERE clause and analyze constraints
        where_clause, constraint_analysis_df = build_where_clause(constraints, con, fund, fund_capacity)

        # Display constraint analysis with progress bars
        st.subheader(f"Constraint Analysis for {fund}")
        display_constraint_analysis(constraint_analysis_df)

        # Select systems satisfying the constraints from backlog
        query = f"""
            SELECT * FROM backlog
            WHERE allocated_fund IS NULL
            AND {where_clause}
        """
        df_fund = con.execute(query).fetch_df()

        if df_fund.empty:
            st.warning(f"No systems satisfy the constraints for fund {fund}.")
            st.code(query, language='sql')
            # Record zero allocation
            allocation_results[fund] = {
                'allocated_fmv': 0.0
            }
            continue

        # Allocate systems up to remaining capacity and constraint capacities
        df_allocated = allocate_up_to_capacity(df_fund, remaining_capacity, constraint_analysis_df, fund_capacity)

        # Update the allocations in the database
        if not df_allocated.empty:
            allocated_ids = df_allocated['System Name'].tolist()
            con.execute(f"""
                UPDATE backlog
                SET allocated_fund = ?
                WHERE "System Name" IN ({','.join(['?'] * len(allocated_ids))})
            """, [fund] + allocated_ids)

            # Record allocated FMV
            allocated_fmv = df_allocated['FMV'].sum()
            allocation_results[fund] = {
                'allocated_fmv': allocated_fmv
            }
        else:
            st.warning(f"No systems were allocated to fund {fund} due to capacity constraints.")
            # Record zero allocation
            allocation_results[fund] = {
                'allocated_fmv': 0.0
            }

def build_where_clause(constraints, con, fund, fund_capacity):
    """Build a SQL WHERE clause from a list of constraints and analyze their impact including allocated systems."""
    conditions_by_type = {}
    constrained_values = {}  # For tracking constrained values per attribute within this fund
    constraint_analysis = []  # List to hold analysis data

    # First pass: collect constrained values
    for constraint in constraints:
        if not constraint.get('active', True):
            continue  # Skip inactive constraints
        constraint_name = constraint.get('name', 'Unnamed Constraint')
        measure = constraint.get('measure', 'FMV')
        upper_bound_ratio = constraint.get('upper_bound', 1.0)
        upper_bound_absolute = upper_bound_ratio * fund_capacity  # Convert ratio to absolute value
        apply_per_value = constraint.get('apply_per_value', False)
        condition_list= constraint.get('conditions', [])

        for condition in constraint.get('conditions', []):
            col_type = condition['type']
            cond = condition['condition']
            values = condition.get('values', [])
            value = condition.get('value')

            if value == '__OTHERS__':
                continue  # Skip for now
            else:
                if col_type not in constrained_values:
                    constrained_values[col_type] = set()
                if values:
                    constrained_values[col_type].update(values)
                elif value is not None:
                    constrained_values[col_type].add(value)

    # Second pass: build expressions and analyze constraints
    for constraint in constraints:
        if not constraint.get('active', True):
            continue  # Skip inactive constraints
        constraint_name = constraint.get('name', 'Unnamed Constraint')
        measure = constraint.get('measure', 'FMV')
        upper_bound_ratio = constraint.get('upper_bound', 1.0)
        upper_bound_absolute = upper_bound_ratio * fund_capacity  # Convert ratio to absolute value
        apply_per_value = constraint.get('apply_per_value', False)
        conditions = constraint.get('conditions', [])

        # Handle apply_per_value
        if apply_per_value:
            for condition in conditions:
                col_type = condition['type']
                cond = condition['condition']
                values = condition.get('values', [])
                value = condition.get('value')

                # Get list of values to apply constraints individually
                if values:
                    value_list = values
                elif value is not None:
                    value_list = [value]
                else:
                    value_list = []

                for val in value_list:
                    expr = ''
                    if val == '__OTHERS__':
                        constrained_vals = constrained_values.get(col_type, set())
                        if constrained_vals:
                            values_list = ', '.join(f"'{v}'" for v in constrained_vals)
                            expr = f'"{col_type}" NOT IN ({values_list})'
                        else:
                            expr = '1=1'  # Select all
                    else:
                        if cond in ['Equals', 'In']:
                            expr = f'"{col_type}" = \'{val}\''
                        elif cond in ['Not Equals', 'Not In']:
                            expr = f'"{col_type}" != \'{val}\''
                        else:
                            continue  # Skip unsupported conditions for apply_per_value

                    # Analyze the constraint for this value
                    analyze_constraint_component(
                        con, fund, measure, upper_bound_absolute, constraint_name, val, expr, constraint_analysis, conditions
                    )
        else:
            # Handle as a single constraint
            condition_expressions = []
            for condition in conditions:
                col_type = condition['type']
                cond = condition['condition']
                values = condition.get('values', [])
                value = condition.get('value')

                expr = ''
                if value == '__OTHERS__':
                    # Handle '__OTHERS__' placeholder
                    constrained_vals = constrained_values.get(col_type, set())
                    if constrained_vals:
                        values_list = ', '.join(f"'{v}'" for v in constrained_vals)
                        expr = f'"{col_type}" NOT IN ({values_list})'
                    else:
                        expr = '1=1'  # Select all
                else:
                    if values:
                        values_list = ', '.join(f"'{v}'" for v in values)
                        if cond in ['Equals', 'In']:
                            expr = f'"{col_type}" IN ({values_list})'
                        elif cond in ['Not Equals', 'Not In']:
                            expr = f'"{col_type}" NOT IN ({values_list})'
                    elif value is not None:
                        if cond == 'Equals':
                            expr = f'"{col_type}" = \'{value}\''
                        elif cond == 'Not Equals':
                            expr = f'"{col_type}" != \'{value}\''
                        elif cond == 'Contains':
                            expr = f'"{col_type}" LIKE \'%{value}%\''
                        elif cond == 'Not Contains':
                            expr = f'"{col_type}" NOT LIKE \'%{value}%\''
                        elif cond == 'Greater Than':
                            expr = f'"{col_type}" > {value}'
                        elif cond == 'Less Than':
                            expr = f'"{col_type}" < {value}'
                        else:
                            expr = '1=1'  # Default condition (always true)
                    else:
                        expr = '1=1'  # Default condition (always true)

                condition_expressions.append(expr)

                if col_type not in conditions_by_type:
                    conditions_by_type[col_type] = []
                conditions_by_type[col_type].append(expr)

            # Combine condition expressions for this constraint
            if condition_expressions:
                constraint_expr = ' AND '.join(condition_expressions)
            else:
                constraint_expr = '1=1'

            # Analyze the constraint as a whole
            analyze_constraint_component(
                con, fund, measure, upper_bound_absolute, constraint_name, None, constraint_expr, constraint_analysis, conditions
            )

    # Combine conditions of the same type with 'OR'
    combined_conditions = []
    for col_type, expressions in conditions_by_type.items():
        if len(expressions) > 1:
            combined_group = f"({' OR '.join(expressions)})"
        else:
            combined_group = expressions[0]
        combined_conditions.append(combined_group)

    # Combine all groups with 'AND'
    if combined_conditions:
        where_clause = ' AND '.join(combined_conditions)
    else:
        where_clause = '1=1'  # Default to true if no conditions

    # Convert constraint analysis to DataFrame
    constraint_analysis_df = pd.DataFrame(constraint_analysis)

    return where_clause, constraint_analysis_df

def analyze_constraint_component(con, fund, measure, upper_bound_absolute, constraint_name, value, expr, constraint_analysis, conditions):
    """Analyze a single constraint component and append the results to constraint_analysis."""
    # Build the component name
    if value is not None:
        component_name = f"{value}"
    else:
        try: 
            component_name = " ,".join(conditions[0]['values'])
        except:
            component_name = conditions#[0]['value']

    # Total measure from systems already allocated to the fund
    allocated_query = f"""
        SELECT COUNT(*) as system_count, SUM("{measure}") as total_measure
        FROM systems
        WHERE "Asset Portfolio - Customer" = '{fund}'
        AND {expr}
    """
    allocated_result = con.execute(allocated_query).fetchone()
    allocated_system_count = allocated_result[0] or 0
    allocated_total_measure = allocated_result[1] or 0.0

    # Remaining capacity under the constraint
    remaining_constraint_capacity = max(upper_bound_absolute - allocated_total_measure, 0)

    # Total measure from backlog systems satisfying the constraint
    backlog_query = f"""
        SELECT COUNT(*) as system_count, SUM("{measure}") as total_measure
        FROM backlog
        WHERE allocated_fund IS NULL AND {expr}
    """
    backlog_result = con.execute(backlog_query).fetchone()
    backlog_system_count = backlog_result[0] or 0
    backlog_total_measure = backlog_result[1] or 0.0

    # Calculate usage percentage
    usage_percentage = (allocated_total_measure / upper_bound_absolute) * 100 if upper_bound_absolute > 0 else 0.0

    # Record analysis data
    constraint_analysis.append({
        'Constraint Name': component_name,
        'Allocated Measure': allocated_total_measure,
        'Upper Bound': upper_bound_absolute,
        'Remaining Capacity': remaining_constraint_capacity,
        'Usage': allocated_total_measure,  # For progress bar
        'Max Value': upper_bound_absolute,  # For progress bar max_value
        'Usage Percentage': usage_percentage,
        'Backlog Systems Satisfying Constraint': backlog_system_count,
        'Backlog Measure Satisfying Constraint': backlog_total_measure
    })




def create_bar(prop_fill: float, max_width: int, height: int) -> str:
    """Create divs to represent prop_fill as a bar with color gradient."""
    width = round(max_width * prop_fill, 2)
    px_width = f"{width}px"
    
    # Calculate color (green to red gradient)
    r = int(255 * prop_fill)
    g = int(255 * (1 - prop_fill))
    color = f"rgb({r},{g},0)"
    
    return f"""\
    <div style="width: {max_width}px; background-color: #e0e0e0;">
        <div style="height:{height}px;width:{px_width};background-color:{color};"></div>
    </div>
    """
def to_snake_case(name):
    """Convert a string to snake_case."""
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower().replace(" ", "_")



def display_constraint_analysis(constraint_analysis_df):
    """Display constraint analysis using Great Tables with progress bars."""
    
    # Ensure we're working with a pandas DataFrame
    if not isinstance(constraint_analysis_df, pd.DataFrame):
        constraint_analysis_df = pd.DataFrame(constraint_analysis_df)
    
    # Convert column names to snake_case
    constraint_analysis_df.columns = [to_snake_case(col) for col in constraint_analysis_df.columns]
    # st.write(list(constraint_analysis_df.columns))
    
    # Add the progress bar column
    constraint_analysis_df['usage_ratio'] = constraint_analysis_df['usage'] / constraint_analysis_df["max__value"]
    constraint_analysis_df['usage_bar'] = constraint_analysis_df['usage_ratio'].apply(
        lambda x: create_bar(x, max_width=100, height=20)

    )
    cols_to_keep=["constraint__name","usage_bar","usage__percentage",
                                    "upper__bound", "remaining__capacity", "backlog__systems__satisfying__constraint",
                                    "usage", "backlog__measure__satisfying__constraint"]
    number_cols=[#"usage__percentage",
                                    "upper__bound", "remaining__capacity", 
                                    "usage", "backlog__measure__satisfying__constraint"]
    data=constraint_analysis_df[cols_to_keep]
    data["usage__percentage"]=data["usage__percentage"]/100
    # st.write(data)

    # Create and customize the GT table
    gt_table = (
        GT(data).cols_width(
        cases={
           "constraint__name": "150px",
    
        }
    )
        .cols_move_to_start(columns=["constraint__name"])
        .tab_spanner(
        label="Allocated",
        columns=["usage_bar","usage__percentage","usage"]
    )
        .cols_label(
            constraint__name="Constraint Name",
            usage=html(" "),
            usage__percentage=html(" "),
            usage_bar=html(" "),
            upper__bound=html("Upper<br>Bound ($)"),
            # allocated__measure=html("FMV<br>Allocated ($)"),
            remaining__capacity=html("Remaining<br>Capacity ($)"),
            
            backlog__systems__satisfying__constraint=html("Systems in<br>Backlog"),
            backlog__measure__satisfying__constraint=html("FMV<br>in Backlog ($)")
        )
        .fmt_number(
            columns=number_cols,
            compact=True,
        pattern="${x}",
        n_sigfig=3,
        )
        .fmt_integer("backlog_systems_satisfying_constraint")
        .fmt_percent("usage__percentage", decimals=1)
        # .tab_header(title="Constraint Analysis")
        .tab_source_note(source_note="Note: Usage bars show percentage relative to each constraints upper bound.")
    )

    # Display the GT table in Streamlit
    st.write(gt_table.as_raw_html(), unsafe_allow_html=True)

def allocate_up_to_capacity(df_fund, remaining_capacity, constraint_analysis_df, fund_capacity):
    """Allocate systems up to the remaining capacity and considering constraint capacities."""
    # Sort systems (you can customize this sorting)
    df_fund = df_fund.sort_values(by='FMV', ascending=False)

    # Initialize allocation
    allocated_systems = []
    total_allocated_measure = 0.0

    # Convert constraint analysis to a dictionary for quick lookup
    constraint_caps = {}
    for idx, row in constraint_analysis_df.iterrows():
        constraint_name = row['Constraint Name']
        remaining_cap = row['Remaining Capacity']
        constraint_caps[constraint_name] = remaining_cap

    # Iterate over systems and allocate while respecting constraints
    for _, system in df_fund.iterrows():
        system_measure = system['FMV']
        if total_allocated_measure + system_measure > remaining_capacity:
            break  # Exceeds fund remaining capacity

        # Check if allocating this system exceeds any constraint's remaining capacity
        violates_constraint = False
        for constraint_name, remaining_cap in constraint_caps.items():
            if remaining_cap <= 0:
                violates_constraint = True
                break  # Cannot allocate due to constraint capacity being zero

            if system_measure > remaining_cap:
                violates_constraint = True
                break  # Cannot allocate due to constraint capacity exceeded

        if not violates_constraint:
            allocated_systems.append(system)
            total_allocated_measure += system_measure

            # Update remaining capacities for constraints affected by this system
            for constraint_name in constraint_caps.keys():
                constraint_caps[constraint_name] -= system_measure

    if allocated_systems:
        df_allocated = pd.DataFrame(allocated_systems)
    else:
        df_allocated = pd.DataFrame()

    return df_allocated