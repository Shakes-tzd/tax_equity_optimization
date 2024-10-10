import streamlit as st
import pandas as pd
from utils.data_processing import load_constraints, execute_query
from optimization.optimizer import run_optimization
from utils.visualization import display_constraint_analysis
from constraints.config import DB_CONNECTION_STRING
import duckdb

def optimization_runner():
    st.title("Run Optimization")

    # Load constraints
    funds = load_constraints()

    # Connect to the database
    con = duckdb.connect(DB_CONNECTION_STRING)

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
        target_percentage = st.slider(f"Target Percentage for {fund_name}", 
                                      min_value=float(current_percentage), 
                                      max_value=100.0, 
                                      value=float(current_percentage),
                                      step=0.1)
        
        target_amount = (target_percentage / 100) * fund.capacity
        
        fund_targets[fund_name] = {
            'capacity': fund.capacity,
            'allocated_amount': current_allocation,
            'target_percentage': target_percentage,
            'target_amount': target_amount
        }

    if st.button("Run Optimization"):
        results = run_optimization(con, funds, fund_targets)
        
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