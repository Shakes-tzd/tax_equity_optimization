# app.py

import streamlit as st

# Import your pages
from main import main_page
from constraints.editor import constraint_editor_page

# Create a navigation menu
pages = [
    st.Page(main_page, title="Optimization", icon="📊", default=True),
    st.Page(constraint_editor_page, title="Constraint Editor", icon="✏️")
]

# Initialize navigation
pg = st.navigation(pages)

# Run the selected page
pg.run()
