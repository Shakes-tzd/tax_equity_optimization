# main.py

import streamlit as st
from utils.data_processing import load_constraints
from optimization.optimizer import allocate_systems_to_fund
from utils.visualization import display_constraint_analysis
from constraints.models import Fund
from typing import Dict, List
import pandas as pd
import json
import io

def main():
    st.set_page_config(page_title="Solar System Allocation", layout="wide")

    st.title("Solar System Allocation")

    # Upload Parquet file
    st.header("Upload Systems Data")
    uploaded_parquet = st.file_uploader("Upload Parquet File", type="parquet")
    if uploaded_parquet is not None:
        # Read the Parquet file into a Pandas DataFrame
        try:
            parquet_bytes = uploaded_parquet.read()
            parquet_buffer = io.BytesIO(parquet_bytes)
            df_systems = pd.read_parquet(parquet_buffer)
            df_systems = df_systems.rename(columns={"Project Purchase Price": "FMV"})
            st.success("Systems data loaded successfully!")
        except Exception as e:
            st.error(f"Failed to read Parquet file: {e}")
            return
    else:
        st.info("Please upload the Parquet file to proceed.")
        return

    # Upload Constraints JSON
    st.header("Upload Constraints")
    uploaded_json = st.file_uploader("Upload Constraints JSON", type="json")
    if uploaded_json is not None:
        try:
            json_bytes = uploaded_json.read()
            json_str = json_bytes.decode('utf-8')
            json_data = json.loads(json_str)
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

    # Select funds to allocate
    st.header("Select Funds to Allocate")
    fund_names = list(funds.keys())
    selected_funds = st.multiselect("Select Funds", fund_names)

    if not selected_funds:
        st.warning("Please select at least one fund.")
        return

    # Set target FMV amounts for selected funds
    st.header("Set Target FMV Amounts for Selected Funds")
    fund_targets = {}
    for fund_name in selected_funds:
        fund = funds[fund_name]
        st.subheader(f"Fund: {fund_name}")
        capacity = fund.capacity
        target_fmv = st.number_input(f"Set target FMV for {fund_name} (Max: {capacity})", min_value=0.0, max_value=capacity, value=capacity)
        fund_targets[fund_name] = target_fmv

    # Run allocation
    if st.button("Run Allocation"):
        allocation_results = {}
        for fund_name in selected_funds:
            fund = funds[fund_name]
            target_fmv = fund_targets[fund_name]
            fund.capacity = target_fmv  # Update fund capacity with target FMV
            allocated_systems, infeasible_constraints, constraint_analysis_df = allocate_systems_to_fund(df_systems.copy(), fund)
            allocation_results[fund_name] = {
                'allocated_systems': allocated_systems,
                'infeasible_constraints': infeasible_constraints,
                'constraint_analysis': constraint_analysis_df
            }

        # Display results
        for fund_name, result in allocation_results.items():
            allocated_df = result['allocated_systems']
            infeasible_constraints = result['infeasible_constraints']
            constraint_analysis_df = result['constraint_analysis']
            total_allocated_fmv = allocated_df['FMV'].sum()
            st.subheader(f"Fund: {fund_name}")
            st.write(f"**Total Allocated FMV:** ${total_allocated_fmv:,.2f}")
            st.write(f"**Number of Systems Allocated:** {len(allocated_df)}")
            if infeasible_constraints:
                st.warning("Infeasible Constraints Detected:")
                for constraint in infeasible_constraints:
                    st.write(f"- {constraint}")
                # Optionally, allow user to relax constraints
                if st.button(f"Relax Constraints for {fund_name}"):
                    st.info("Constraint relaxation not implemented yet.")
            else:
                st.success("All constraints satisfied.")
            # Display allocated systems
            with st.expander("View Allocated Systems"):
                st.dataframe(allocated_df)
            # Display constraint analysis
            st.subheader("Constraint Analysis")
            display_constraint_analysis(constraint_analysis_df)

if __name__ == "__main__":
    main()