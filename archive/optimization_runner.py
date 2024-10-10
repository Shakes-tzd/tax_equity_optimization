# optimization_runner.py

import streamlit as st
import duckdb
import pandas as pd
from archive.utils import parse_yaml, run_optimization, build_where_clause, display_constraint_analysis
import io
import yaml

def optimization_runner():
    st.title("Run Optimization")

    st.sidebar.header("Instructions")
    st.sidebar.markdown("""
    - Upload the Parquet file containing the systems data.
    - Upload the YAML constraints file.
    - Select the funds to allocate systems into.
    - Adjust the target percentage for each fund.
    - Run the optimization to allocate systems to funds.
    """)

    # Upload Parquet file
    with st.expander("Upload Required Files:"):
        uploaded_parquet = st.file_uploader("Upload Parquet File", type="parquet")
        if uploaded_parquet is not None:
            st.success("Parquet file uploaded successfully!")
        else:
            st.info("Please upload the Parquet file to proceed.")
            return

        # Upload YAML constraints file
        uploaded_yaml = st.file_uploader("Upload Constraints YAML", type="yaml", key="yaml_upload_opt")
        if uploaded_yaml is not None:
            yaml_content = uploaded_yaml.read().decode("utf-8")
            yaml_data = parse_yaml(yaml_content)
            if yaml_data:
                st.success("Constraints file uploaded successfully!")
            else:
                st.error("Failed to parse YAML constraints file.")
                return
        else:
            st.info("Please upload the YAML constraints file to proceed.")
            return

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

    # Get list of funds from yaml_data
    fund_names = list(yaml_data.keys())

    # Select funds to allocate into
    selected_funds = st.multiselect("Select Funds to Allocate Into", fund_names)

    if not selected_funds:
        st.info("Please select at least one fund to proceed.")
        return

    # For each selected fund, compute allocated percentages and provide slider for target percentage
    fund_targets = {}
    tabs = st.tabs(selected_funds)

    for tab, fund in zip(tabs, selected_funds):
        with tab:
            # st.subheader(f"Fund: {fund}")

            # Display YAML definition of the constraints

            fund_constraints_yaml = yaml_data[fund]
            with st.expander(f"**{fund} Constraints**"):
                st.code(yaml.dump(fund_constraints_yaml, sort_keys=False), language="yaml")

            # Get fund capacity
            fund_capacity = yaml_data[fund].get('capacity', 0.0)
            if fund_capacity <= 0:
                st.warning(f"Fund {fund} has no capacity defined. Please define the capacity in the YAML file.")
                continue

            # Compute allocated amount
            allocated_amount = con.execute(f"""
                SELECT SUM("FMV") as total_allocated
                FROM systems
                WHERE "Asset Portfolio - Customer" = '{fund}'
                  AND "Stage" != 'Cancelled'
            """).fetchone()[0] or 0.0

            allocated_percentage = (allocated_amount / fund_capacity) * 100 if fund_capacity > 0 else 0.0

            st.write(f"**Allocated Amount:** ${allocated_amount:,.2f}")
            st.write(f"**Allocated Percentage:** {allocated_percentage:.2f}%")

            # Slider for target percentage
            max_percentage = min(allocated_percentage * 2 if allocated_percentage > 0 else 100.0, 200.0)
            target_percentage = st.slider(
                f"Set Target Percentage for {fund}",
                min_value=allocated_percentage,
                max_value=max_percentage,
                value=allocated_percentage,
                step=1.0,
                help="Select the target percentage of the fund capacity."
            )

            # Calculate and display the target FMV amount
            target_amount = (target_percentage / 100.0) * fund_capacity
            st.write(f"**Target FMV Amount:** ${target_amount:,.2f}")

            fund_targets[fund] = {
                'capacity': fund_capacity,
                'allocated_amount': allocated_amount,
                'allocated_percentage': allocated_percentage,
                'target_percentage': target_percentage,
                'target_amount': target_amount
            }

            # Build the WHERE clause
            where_clause, constraint_analysis_df = build_where_clause(fund_constraints_yaml.get('constraints', []), con,fund ,target_amount)

            # Show the generated SQL query
            # with st.expander("**Generated SQL WHERE Clause:**"):
            #     st.code(where_clause, language='sql')
            with st.expander("**Constraint Status**"):
                # st.write((constraint_analysis_df.columns).tolist())
                display_constraint_analysis(constraint_analysis_df)
                # st.dataframe(constraint_analysis_df)

    # Run optimization button
    if st.button("Run Optimization"):
        allocation_results = run_optimization(con, yaml_data, fund_targets)
        # Display how much of the target was met after optimization
        st.header("Optimization Results")
        for fund, result in allocation_results.items():
            st.subheader(f"Fund: {fund}")
            allocated_fmv = result['allocated_fmv']
            target_amount = fund_targets[fund]['target_amount']
            percentage_of_target = (allocated_fmv / target_amount) * 100 if target_amount > 0 else 0.0

            st.write(f"Allocated FMV Amount: ${allocated_fmv:,.2f}")
            st.write(f"Target FMV Amount: ${target_amount:,.2f}")
            st.write(f"Percentage of Target Met: {percentage_of_target:.2f}%")

            st.progress(min(percentage_of_target / 100.0, 1.0))

        # Close the DuckDB connection
        con.close()

    else:
        # Close the DuckDB connection if not running optimization
        con.close()


# def build_where_clause(constraints):
#     """Build a SQL WHERE clause from a list of constraints."""
#     # Group conditions by 'type' (column name)
#     conditions_by_type = {}

#     for constraint in constraints:
#         if not constraint.get('active', True):
#             continue  # Skip inactive constraints
#         for condition in constraint.get('conditions', []):
#             col_type = condition['type']
#             cond = condition['condition']
#             values = condition.get('values', [])
#             value = condition.get('value')

#             expr = ''
#             if values:
#                 values_list = ', '.join(f"'{v}'" for v in values)
#                 if cond in ['Equals', 'In']:
#                     expr = f'"{col_type}" IN ({values_list})'
#                 elif cond in ['Not Equals', 'Not In']:
#                     expr = f'"{col_type}" NOT IN ({values_list})'
#             elif value is not None:
#                 if cond == 'Equals':
#                     expr = f'"{col_type}" = \'{value}\''
#                 elif cond == 'Not Equals':
#                     expr = f'"{col_type}" != \'{value}\''
#                 elif cond == 'Contains':
#                     expr = f'"{col_type}" LIKE \'%{value}%\''
#                 elif cond == 'Not Contains':
#                     expr = f'"{col_type}" NOT LIKE \'%{value}%\''
#                 elif cond == 'Greater Than':
#                     expr = f'"{col_type}" > {value}'
#                 elif cond == 'Less Than':
#                     expr = f'"{col_type}" < {value}'
#                 else:
#                     expr = '1=1'  # Default condition (always true)
#             else:
#                 expr = '1=1'  # Default condition (always true)

#             if col_type not in conditions_by_type:
#                 conditions_by_type[col_type] = []
#             conditions_by_type[col_type].append(expr)

#     # Combine conditions of the same type with 'OR'
#     combined_conditions = []
#     for col_type, expressions in conditions_by_type.items():
#         if len(expressions) > 1:
#             combined_group = f"({' OR '.join(expressions)})"
#         else:
#             combined_group = expressions[0]
#         combined_conditions.append(combined_group)

#     # Combine all groups with 'AND'
#     if combined_conditions:
#         where_clause = ' AND '.join(combined_conditions)
#     else:
#         where_clause = '1=1'  # Default to true if no conditions

#     return where_clause



if __name__ == "__main__":
    optimization_runner()