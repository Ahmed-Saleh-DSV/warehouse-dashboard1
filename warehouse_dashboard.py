import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from io import BytesIO
import warnings
import base64

# Page configuration for wide, modern layout
st.set_page_config(layout="wide", page_title="Warehouse Inventory Management Dashboard")

# Initialize session state for persistence
if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame()  # Main inventory DataFrame
if 'log' not in st.session_state:
    st.session_state.log = []  # Log of changes

# Sidebar for file upload
with st.sidebar:
    st.header("File Upload")
    uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx", "xls"])
    if uploaded_file:
        st.session_state.df = pd.read_excel(uploaded_file)
        st.session_state.log.append("Uploaded new Excel file")
        st.success("Excel file uploaded and loaded successfully!")

# Tabs navigation
tab1, tab2, tab3 = st.tabs(["Dashboard Overview", "Inventory Management", "Logs"])

# Function for dynamic form generation
def generate_dynamic_form(df, is_edit=False, edit_row=None):
    form_data = {}
    for column in df.columns:
        if df[column].dtype in ['int64', 'float64']:  # Numeric columns
            if is_edit:
                form_data[column] = st.number_input(column, value=edit_row[column], min_value=0 if column in ['QTYAVAILABLE', 'QTY'] else None)
            else:
                form_data[column] = st.number_input(column, min_value=0 if column in ['QTYAVAILABLE', 'QTY'] else None)
        else:  # String or other columns
            if is_edit:
                form_data[column] = st.text_input(column, value=str(edit_row[column]))
            else:
                form_data[column] = st.text_input(column)
    return form_data

with tab1:
    st.header("Dashboard Overview")
    
    if not st.session_state.df.empty:
        total_skus = len(st.session_state.df)
        total_qty = st.session_state.df['QTYAVAILABLE'].sum()
        low_stock_threshold = 10
        low_stock = st.session_state.df[st.session_state.df['QTYAVAILABLE'] < low_stock_threshold]
        
        # KPIs with modern color themes
        col1, col2, col3 = st.columns(3)
        with col1: st.metric(label="Total SKUs", value=total_skus, delta=None, help="Total unique SKUs", label_color="blue")
        with col2: st.metric(label="Total Quantity", value=total_qty, delta=None, help="Sum of QTYAVAILABLE", label_color="green")
        with col3: st.metric(label="Low Stock Alerts", value=len(low_stock), delta=None, help=f"Items below {low_stock_threshold}", label_color="red")
        
        # Interactive Plotly charts
        if not low_stock.empty:
            # Bar chart for low stock items
            fig_bar = px.bar(low_stock, x='SKU', y='QTYAVAILABLE', title="Low Stock Items",
                             labels={'QTYAVAILABLE': 'Quantity Available'},
                             color='QTYAVAILABLE', color_continuous_scale='reds')
            fig_bar.update_layout(showlegend=True)
            st.plotly_chart(fig_bar, use_container_width=True)
            
            # Heatmap for quantity distribution across locations
            location_cols = [col for col in st.session_state.df.columns if col in ['21KCH2', '21KCH5', '3K-M45', '6KMZ-2', 'YARD']]
            if location_cols:
                heatmap_data = st.session_state.df.groupby(location_cols[0])['QTYAVAILABLE'].sum().reset_index()
                for col in location_cols[1:]:
                    heatmap_data = heatmap_data.groupby(col)['QTYAVAILABLE'].sum().reset_index()
                fig_heatmap = go.Figure(data=go.Heatmap(
                    z=heatmap_data['QTYAVAILABLE'],
                    x=heatmap_data.columns[1:],
                    y=heatmap_data[heatmap_data.columns[0]],
                    colorscale='Greens'
                ))
                fig_heatmap.update_layout(title="Quantity Distribution Across Locations")
                st.plotly_chart(fig_heatmap, use_container_width=True)
        
        with st.expander("Low Stock Details"):
            st.dataframe(low_stock)

with tab2:
    st.header("Inventory Management")
    
    if not st.session_state.df.empty:
        # AgGrid for high-performance table with editing, filtering, sorting, and pagination
        gb = GridOptionsBuilder.from_dataframe(st.session_state.df)
        gb.configure_pagination(paginationAutoPageSize=True)  # Pagination for large datasets
        gb.configure_side_bar()  # Enable filtering and sorting
        gb.configure_selection(selection_mode="single", use_checkbox=True)
        gb.configure_grid_options(editable=True)  # Inline editing
        # Conditional formatting for QTYAVAILABLE
        gb.configure_columns([{ "field": "QTYAVAILABLE", "cellStyle": {"color": "white", "backgroundColor": lambda params: "red" if params['value'] < 10 else "yellow" if params['value'] < 20 else "green"} }])
        grid_options = gb.build()
        
        grid_response = AgGrid(st.session_state.df, gridOptions=grid_options, height=400, width='100%', data_return_mode='AS_INPUT', update_mode='GRID_CHANGED')
        
        updated_df = grid_response['data']  # Get updated data from AgGrid
        st.session_state.df = pd.DataFrame(updated_df)  # Update session state immediately
        st.session_state.log.append("Edited inventory via AgGrid")  # Log changes
        
        # Add new SKU
        if st.button("Add New SKU"):
            with st.form("Add Form"):
                form_data = generate_dynamic_form(st.session_state.df)
                submitted = st.form_submit_button()
                if submitted:
                    new_row = pd.DataFrame([form_data])
                    st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
                    st.session_state.log.append(f"Added SKU: {form_data.get('SKU', 'Unknown')}")
                    st.success("SKU added successfully!")
        
        # Edit existing SKU (using AgGrid's inline edit, but fallback form)
        if st.button("Edit Selected SKU"):
            selected_rows = grid_response['selected_rows']
            if selected_rows:
                edit_row = selected_rows[0]
                with st.form("Edit Form"):
                    form_data = generate_dynamic_form(st.session_state.df, is_edit=True, edit_row=edit_row)
                    submitted_edit = st.form_submit_button()
                    if submitted_edit:
                        # Update the row in the DataFrame
                        for idx, row in st.session_state.df.iterrows():
                            if row['SKU'] == edit_row['SKU']:
                                st.session_state.df.loc[idx] = list(form_data.values())
                        st.session_state.log.append(f"Edited SKU: {edit_row['SKU']}")
                        st.success("SKU edited successfully!")
        
        # Delete SKU with confirmation
        if st.button("Delete Selected SKU"):
            selected_rows = grid_response['selected_rows']
            if selected_rows:
                if st.confirm("Are you sure you want to delete this SKU?"):
                    sku_to_delete = selected_rows[0]['SKU']
                    st.session_state.df = st.session_state.df[st.session_state.df['SKU'] != sku_to_delete]
                    st.session_state.log.append(f"Deleted SKU: {sku_to_delete}")
                    st.success("SKU deleted successfully!")
        
        # Download as Excel
        def get_excel_download_link(df):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            output.seek(0)
            b64 = base64.b64encode(output.getvalue()).decode()
            return f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="inventory.xlsx">Download Excel</a>'
        
        st.markdown(get_excel_download_link(st.session_state.df), unsafe_allow_html=True)

with tab3:
    st.header("Logs")
    if st.session_state.log:
        log_df = pd.DataFrame(st.session_state.log, columns=["Log Entries"])
        st.dataframe(log_df, height=300)  # Scrollable table
    else:
        st.info("No logs yet.")
    
    if st.button("Clear Log"):
        st.session_state.log = []
        st.success("Log cleared successfully!")


