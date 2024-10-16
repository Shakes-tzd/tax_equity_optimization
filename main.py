# main.py

import streamlit as st
from optimization.optimizer import allocate_systems_to_funds
from utils.visualization import display_constraint_analysis
from utils.data_processing import load_constraints
from constraints.models import Fund
import json
import pandas as pd
import io

def main_page():
    st.title("Solar System Allocation")

    # Check if constraints are loaded in session state
    if 'funds' not in st.session_state:
        st.session_state['funds'] = None

    # Check if systems data is loaded in session state
    if 'df_systems' not in st.session_state:
        st.session_state['df_systems'] = None

    # Data Upload
    with st.expander("### Data Upload"):
        # Upload Parquet file
        uploaded_parquet = st.file_uploader("Upload Parquet File", type="parquet")
        if uploaded_parquet is not None:
            try:
                parquet_bytes = uploaded_parquet.read()
                parquet_buffer = io.BytesIO(parquet_bytes)
                df_systems = pd.read_parquet(parquet_buffer)
                if 'Project Purchase Price' in df_systems.columns:
                    df_systems = df_systems.rename(columns={"Project Purchase Price": "FMV"})
                elif 'FMV' not in df_systems.columns:
                    st.error("The systems data must contain a column named 'FMV' or 'Project Purchase Price'.")
                    return
                st.session_state['df_systems'] = df_systems
                st.success("Systems data loaded successfully!")
            except Exception as e:
                st.error(f"Failed to read Parquet file: {e}")
                return
        elif st.session_state['df_systems'] is not None:
            df_systems = st.session_state['df_systems']
            st.info("Using previously uploaded systems data.")
        else:
            st.info("Please upload the Parquet file to proceed.")
            return

        # Upload Constraints JSON
        uploaded_json = st.file_uploader("Upload Constraints JSON", type="json")
        if uploaded_json is not None:
            try:
                json_bytes = uploaded_json.read()
                json_str = json_bytes.decode('utf-8')
                json_data = json.loads(json_str)
                funds = load_constraints(json_data)
                if funds:
                    st.session_state['funds'] = funds
                    st.success("Constraints file uploaded successfully!")
                else:
                    st.error("Failed to parse JSON constraints file.")
                    return
            except json.JSONDecodeError:
                st.error("Invalid JSON file. Please upload a valid JSON file.")
                return
        elif st.session_state['funds'] is not None:
            funds = st.session_state['funds']
            st.info("Using previously uploaded constraints.")
        else:
            st.info("Please upload the JSON constraints file to proceed.")
            return

    # Option to proceed to constraint editor
    st.write("If you wish to edit the constraints, please select 'Constraint Editor' from the navigation sidebar.")

    # Proceed with the rest of the optimization code
    # Filter systems that are in the backlog
    df_backlog = df_systems[
        (df_systems['Asset Portfolio - Customer'] == 'Sunnova TEP Developer LLC') &
        (df_systems['Stage'] == 'Substantial')
    ].copy()

    if df_backlog.empty:
        st.error("No systems in the backlog after filtering. Please check your data.")
        return

    # Select funds to allocate
    fund_names = list(funds.keys())
    selected_funds = st.multiselect("Select Funds to Allocate", fund_names)

    if not selected_funds:
        st.warning("Please select at least one fund.")
        return

    # Set target FMV amounts for selected funds
    st.header("Set Target FMV Amounts for Selected Funds")
    fund_targets = {}

    # Pre-calculate current allocations for all funds
    current_allocations = df_systems.groupby('Asset Portfolio - Customer')['FMV'].sum()

    for fund_name in selected_funds:
        fund = funds[fund_name]
        capacity = fund.capacity
        current_allocation = current_allocations.get(fund_name, 0.0)
        current_percentage = (current_allocation / capacity) * 100 if capacity > 0 else 0

        st.subheader(f"Fund: {fund_name}")
        st.write(f"Current Allocation: ${current_allocation:,.2f} ({current_percentage:.2f}%)")
        st.write(f"Original Capacity: ${capacity:,.2f}")

        target_percentage = st.slider(
            f"Set target FMV for {fund_name} as percentage of capacity",
            min_value=0.0,
            max_value=150.0,
            value=min(115.0, 150.0),  # Default to 115% or max_percentage
            step=1.0,
            format="%.1f%%"
        )

        target_fmv = (target_percentage / 100.0) * capacity
        st.write(f"Target FMV: ${target_fmv:,.2f}")
        fund_targets[fund_name] = target_fmv

    if st.button("Run Allocation"):
        # Allocate systems to funds
        allocation_results = allocate_systems_to_funds(
            df_systems=df_systems,
            df_backlog=df_backlog,
            funds={k: funds[k] for k in selected_funds},
            fund_targets=fund_targets
        )

        for fund_name, result in allocation_results.items():
            allocated_df = result['allocated_systems']
            infeasible_constraints = result['infeasible_constraints']
            constraint_analysis_df = result['constraint_analysis']

            st.subheader(f"Fund: {fund_name}")

            if allocated_df.empty:
                st.warning("No systems were allocated to this fund.")
                total_allocated_fmv = 0.0
            else:
                total_allocated_fmv = allocated_df['FMV'].sum()
                st.write(f"**Total Allocated FMV:** ${total_allocated_fmv:,.2f}")
                st.write(f"**Number of Systems Allocated:** {len(allocated_df)}")
                # Display allocated systems
                with st.expander("View Allocated Systems"):
                    st.dataframe(allocated_df)

            if infeasible_constraints:
                st.warning("Infeasible Constraints Detected:")
                for constraint in infeasible_constraints:
                    st.write(f"- {constraint}")
            else:
                st.success("All constraints satisfied.")

            # Display constraint analysis
            if not constraint_analysis_df.empty:
                st.subheader("Constraint Analysis")
                display_constraint_analysis(constraint_analysis_df)
            else:
                st.info("No constraint analysis available.")

if __name__ == "__main__":
    main_page()
