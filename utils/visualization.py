# visualization/visualization.py

import pandas as pd
import streamlit as st
import re
from great_tables import GT

def create_bar(prop_fill: float, max_width: int, height: int) -> str:
    if pd.isna(prop_fill) or prop_fill < 0:
        prop_fill = 0
    elif prop_fill > 1:
        prop_fill = 1
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
    """Display constraint analysis using Great Tables and Streamlit."""
    
    # Ensure we're working with a pandas DataFrame
    if not isinstance(constraint_analysis_df, pd.DataFrame):
        constraint_analysis_df = pd.DataFrame(constraint_analysis_df)
    
    # Simplify column names
    constraint_analysis_df.columns = [col.lower().replace(" ", "_") for col in constraint_analysis_df.columns]
    
    # Add the progress bar column
    constraint_analysis_df['usage_bar'] = constraint_analysis_df['usage_percentage'].apply(
        lambda x: create_bar(x, max_width=100, height=20)
    )
    
    cols_to_keep = ["constraint_name", "usage_bar", "usage_percentage", "upper_bound", "remaining_capacity", "usage"]
    data = constraint_analysis_df[cols_to_keep]
    data = data.sort_values(by="usage_percentage", ascending=False)
    
    # Create a Great Tables object
    gt_tbl = GT(data)
    
    # Apply formatting and styling
    gt_tbl = (
        gt_tbl.fmt_percent("usage_percentage", decimals=2)
        .fmt_currency(["upper_bound", "remaining_capacity", "usage"], decimals=2)
        .cols_width(
            usage_bar="100px",
            usage_percentage="80px",
            upper_bound="100px",
            remaining_capacity="120px",
            usage="80px"
        )
        .cols_align(
            align="left",
            columns="constraint_name"
        )
        .cols_align(
            align="center",
            columns=["usage_bar", "usage_percentage", "upper_bound", "remaining_capacity", "usage"]
        )
        .tab_spanner(
            label="Usage Statistics",
            columns=["usage_bar", "usage_percentage", "usage"]
        )
        .tab_spanner(
            label="Capacity Information",
            columns=["upper_bound", "remaining_capacity"]
        )
        .cols_move_to_start(columns=["constraint_name"])
        .cols_label(
            constraint_name="Constraint Name",
            usage_bar="Usage Bar",
            usage_percentage="Usage %",
            upper_bound="Upper Bound",
            remaining_capacity="Remaining Capacity",
            usage="Actual Usage"
        )
        .tab_options(
            column_labels_font_weight="bold",
            table_font_size="14px",
            heading_background_color="white",
            column_labels_background_color="white",
            table_background_color="white"
        )
    )
    
    # Convert the Great Tables object to HTML and display it using Streamlit
    st.write(gt_tbl.as_raw_html(), unsafe_allow_html=True)