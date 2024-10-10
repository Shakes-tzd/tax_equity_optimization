# constraint_editor.py
import streamlit as st
import json
from archive.utils import load_constraints, save_constraints, render_fund_editor


def constraint_editor():
    st.title("Constraint Editor")

    st.sidebar.header("Instructions")
    st.sidebar.markdown("""
    - Upload a JSON file containing the fund constraints.
    - Select a fund from the dropdown to edit its constraints and capacity.
    - Add, edit, or remove constraints and conditions as needed.
    - Download the edited JSON file when done.
    """)

    # File upload
    uploaded_file = st.file_uploader(
        "Choose a JSON file", type="json", key="json_upload"
    )
    if uploaded_file is not None:
        try:
            json_content = json.load(uploaded_file)
            funds = load_constraints(json_content)
            if funds:
                st.success("JSON file uploaded successfully!")
                # Render the fund editor
                updated_funds = render_fund_editor(funds)
                # Download button
                json_string = json.dumps(save_constraints(updated_funds), indent=2)
                st.download_button(
                    label="Download Edited JSON",
                    data=json_string,
                    file_name="edited_constraints.json",
                    mime="application/json",
                )
            else:
                st.error("Failed to parse JSON file.")
        except json.JSONDecodeError:
            st.error("Invalid JSON file. Please upload a valid JSON file.")
    else:
        st.info("Please upload a JSON file to begin.")
