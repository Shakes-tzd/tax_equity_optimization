import streamlit as st
from utils.data_processing import load_constraints #, save_constraints
from constraints.models import Fund, Constraint, Condition, ConstraintCategory, ConstraintType
from typing import Dict

def constraint_editor_page():
    st.title("Constraint Editor")

    # Access constraints from session state
    if 'funds' not in st.session_state or st.session_state['funds'] is None:
        st.error("No constraints data found. Please upload constraints in the 'Optimization' page.")
        return
    else:
        funds = st.session_state['funds']

    # Rest of your constraint editor code
    edited_funds = render_fund_editor(funds)

    # Save Changes
    if st.button("Save Changes"):
        st.session_state['funds'] = edited_funds
        st.success("Changes saved successfully!")

def constraint_editor():
    st.title("Constraint Editor")

    uploaded_file = st.file_uploader("Choose a JSON file", type="json")
    if uploaded_file is not None:
        funds = load_constraints(uploaded_file)
        if funds:
            st.success("JSON file uploaded successfully!")
            edited_funds = render_fund_editor(funds)
            if st.button("Save Changes"):
                save_constraints(edited_funds)
                st.success("Changes saved successfully!")
        else:
            st.error("Failed to parse JSON file.")
    else:
        st.info("Please upload a JSON file to begin.")

def render_fund_editor(funds: Dict[str, Fund]):
    selected_fund = st.selectbox("Select Fund to Edit", list(funds.keys()))
    fund = funds[selected_fund]

    st.header(f"Editing Fund: {selected_fund}")

    fund.capacity = st.number_input("Fund Capacity", min_value=0.0, value=fund.capacity, step=1000000.0, format="%.2f")

    if st.button(f"Add Constraint to {selected_fund}"):
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

    for i, constraint in enumerate(fund.constraints):
        with st.expander(f"Constraint: {constraint.name}"):
            render_constraint_editor(constraint, f"{selected_fund}_{i}")

            if st.button(f"Remove Constraint", key=f"remove_constraint_{selected_fund}_{i}"):
                fund.constraints.pop(i)
                st.experimental_rerun()

    return funds

def render_constraint_editor(constraint: Constraint, key: str):
    constraint.name = st.text_input("Constraint Name", value=constraint.name, key=f"name_{key}")
    constraint.category = st.selectbox("Category", options=list(ConstraintCategory), index=list(ConstraintCategory).index(constraint.category), key=f"category_{key}")
    constraint.constraint_type = st.selectbox("Constraint Type", options=list(ConstraintType), index=list(ConstraintType).index(constraint.constraint_type), key=f"constraint_type_{key}")
    constraint.attribute = st.text_input("Attribute", value=constraint.attribute, key=f"attribute_{key}")
    constraint.measure = st.text_input("Measure", value=constraint.measure, key=f"measure_{key}")
    constraint.upper_bound = st.number_input("Upper Bound", min_value=0.0, max_value=1.0, value=constraint.upper_bound, step=0.01, key=f"upper_bound_{key}")
    constraint.group_name = st.text_input("Group Name", value=constraint.group_name or "", key=f"group_name_{key}")
    constraint.aggregation = st.selectbox("Aggregation Method", options=['', 'sum', 'average', 'max', 'min'], index=['', 'sum', 'average', 'max', 'min'].index(constraint.aggregation or ''), key=f"aggregation_{key}")
    constraint.apply_per_value = st.checkbox("Apply Per Value", value=constraint.apply_per_value, key=f"apply_per_value_{key}")
    constraint.active = st.checkbox("Active", value=constraint.active, key=f"active_{key}")

    st.subheader("Conditions")
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
            constraint.conditions.pop(i)
            st.experimental_rerun()

    if st.button("Add Condition", key=f"add_condition_{key}"):
        constraint.conditions.append(Condition(type="", condition="Equals"))
        st.experimental_rerun()