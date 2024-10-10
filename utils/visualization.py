# visualization/visualization.py

import pandas as pd
import re
import streamlit as st

def create_bar(prop_fill: float, max_width: int, height: int) -> str:
    """Create divs to represent prop_fill as a bar with color gradient."""
    width = round(max_width * prop_fill, 2)
    px_width = f"{width}px"
    
    # Calculate color (green to red gradient)
    r = int(255 * (1 - prop_fill))
    g = int(255 * prop_fill)
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
    """Display constraint analysis using Streamlit components."""
    
    # Ensure we're working with a pandas DataFrame
    if not isinstance(constraint_analysis_df, pd.DataFrame):
        constraint_analysis_df = pd.DataFrame(constraint_analysis_df)
    
    # Convert column names to snake_case
    constraint_analysis_df.columns = [to_snake_case(col) for col in constraint_analysis_df.columns]
    
    # Add the progress bar column
    constraint_analysis_df['usage_bar'] = constraint_analysis_df['usage_percentage'].apply(
        lambda x: create_bar(x, max_width=100, height=20)
    )
    cols_to_keep = ["constraint_name", "usage_bar", "usage_percentage", "upper_bound", "remaining_capacity", "usage"]
    data = constraint_analysis_df[cols_to_keep]
    data = data.sort_values(by="usage_percentage", ascending=False)
    data['usage_percentage'] = data['usage_percentage'].apply(lambda x: f"{x:.2%}")
    
    # Display the DataFrame
    st.write(data.to_html(escape=False, index=False), unsafe_allow_html=True)