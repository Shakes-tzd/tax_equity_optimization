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
