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