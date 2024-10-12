# main.py

import streamlit as st
from utils.data_processing import load_constraints,filter_dict
from optimization.optimizer import allocate_systems_to_funds
from utils.visualization import display_constraint_analysis
from constraints.models import Fund
from typing import Dict, List
import pandas as pd
import json
import io

def main():
    st.set_page_config(page_title="Solar System Allocation", layout="wide")

    st.title("Solar System Allocation")
    with st.expander("### Data Upload"):
        # Upload Parquet file
        st.header("Upload Systems Data")
        uploaded_parquet = st.file_uploader("Upload Parquet File", type="parquet")
        if uploaded_parquet is not None:
            # Read the Parquet file into a Pandas DataFrame
            try:
                parquet_bytes = uploaded_parquet.read()
                parquet_buffer = io.BytesIO(parquet_bytes)
                df_systems = pd.read_parquet(parquet_buffer)
                # Ensure 'FMV' column exists
                if 'Project Purchase Price' in df_systems.columns:
                    df_systems = df_systems.rename(columns={"Project Purchase Price": "FMV"})
                elif 'FMV' not in df_systems.columns:
                    st.error("The systems data must contain a column named 'FMV' or 'Project Purchase Price'.")
                    return
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

    # Filter systems that are in the backlog
    df_systems_filtered = df_systems[
        (df_systems['Asset Portfolio - Customer'] == 'Sunnova TEP Developer LLC') &
        (df_systems['Stage'] == 'Substantial')
    ].copy()

    if df_systems_filtered.empty:
        st.error("No systems in the backlog after filtering. Please check your data.")
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
        capacity = fund.capacity  # Original capacity in dollars

        # Display current allocation
        current_allocation = df_systems.loc[df_systems["Asset Portfolio - Customer"] == fund_name, "FMV"].sum()
        current_percentage = (current_allocation / capacity) * 100 if capacity > 0 else 0

        st.write(f"Current Allocation: ${current_allocation:,.2f} ({current_percentage:.2f}%)")
        st.write(f"Original Capacity: ${capacity:,.2f}")

        # Allow up to 150% of the original capacity
        max_percentage = 150.0

        # Create a slider for setting the target FMV percentage
        target_percentage = st.slider(
            f"Set target FMV for {fund_name} as percentage of capacity",
            min_value=0.0,
            max_value=max_percentage,
            value=min(115.0, max_percentage),  # Default to 115% or max_percentage
            step=1.0,
            format="%.1f%%"
        )

        # Convert percentage to dollar amount
        target_fmv = (target_percentage / 100.0) * capacity
        st.write(f"Target FMV: ${target_fmv:,.2f}")

        # Update the fund_targets dictionary with the calculated dollar amount
        fund_targets[fund_name] = target_fmv
        
        # Run allocation
    if st.button("Run Allocation"):
        # Call the new allocation function
        allocation_results = allocate_systems_to_funds(
            df_systems=df_systems[df_systems['Stage'] == 'Cancelled'],
            df_backlog=df_systems_filtered,
            funds=filter_dict(funds,selected_funds),
            fund_targets=fund_targets
        )

        # Display results
        for fund_name, result in allocation_results.items():
            allocated_df = result['allocated_systems']
            infeasible_constraints = result['infeasible_constraints']
            constraint_analysis_df = result['constraint_analysis']
            st.subheader(f"Fund: {fund_name}")

            total_allocated_fmv = allocated_df['FMV'].sum()
            st.write(f"**Total Allocated FMV:** ${total_allocated_fmv:,.2f}")
            st.write(f"**Number of Systems Allocated:** {len(allocated_df)}")

            if infeasible_constraints:
                st.warning("Infeasible Constraints Detected:")
                for constraint in infeasible_constraints:
                    st.write(f"- {constraint}")
            else:
                st.success("All constraints satisfied.")

            # Display allocated systems
            with st.expander("View Allocated Systems"):
                st.dataframe(allocated_df)

            # Display constraint analysis
            if not constraint_analysis_df.empty:
                st.subheader("Constraint Analysis")
                display_constraint_analysis(constraint_analysis_df)
            else:
                st.info("No constraint analysis available.")

    # # Run allocation
    # if st.button("Run Allocation"):
    #     allocation_results = {}
    #     for fund_name in selected_funds:
    #         fund = funds[fund_name]
    #         target_fmv = fund_targets[fund_name]
    #         # Ensure the fund capacity used in allocation is updated
    #         allocated_systems, infeasible_constraints, constraint_analysis_df = allocate_systems_to_fund(
    #             df_systems_filtered.copy(), fund, target_fmv
    #         )
    #         allocation_results[fund_name] = {
    #             'allocated_systems': allocated_systems,
    #             'infeasible_constraints': infeasible_constraints,
    #             'constraint_analysis': constraint_analysis_df
    #         }

    #     # Display results
    #     for fund_name, result in allocation_results.items():
    #         allocated_df = result['allocated_systems']
    #         infeasible_constraints = result['infeasible_constraints']
    #         constraint_analysis_df = result['constraint_analysis']
    #         st.subheader(f"Fund: {fund_name}")

    #         try:
    #             if allocated_df.empty:
    #                 st.warning("No systems were allocated to this fund.")
    #                 total_allocated_fmv = 0.0
    #             else:
    #                 total_allocated_fmv = allocated_df['FMV'].sum()
    #                 st.write(f"**Total Allocated FMV:** ${total_allocated_fmv:,.2f}")
    #                 st.write(f"**Number of Systems Allocated:** {len(allocated_df)}")
    #                 # Display allocated systems
    #                 with st.expander("View Allocated Systems"):
    #                     st.dataframe(allocated_df)

    #             if infeasible_constraints:
    #                 st.warning("Infeasible Constraints Detected:")
    #                 for constraint in infeasible_constraints:
    #                     st.write(f"- {constraint}")
    #             else:
    #                 st.success("All constraints satisfied.")

    #             # Display constraint analysis
    #             if not constraint_analysis_df.empty:
    #                 st.subheader("Constraint Analysis")
    #                 display_constraint_analysis(constraint_analysis_df)
    #             else:
    #                 st.info("No constraint analysis available.")
    #         except Exception as e:
    #             st.error(f"An error occurred while displaying results for {fund_name}: {e}")

if __name__ == "__main__":
    main()