import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from io import BytesIO
import warnings
from datetime import datetime  # For timestamp in reports
import base64  # For downloading Excel

# Page configuration for a clean, wide, modern layout
st.set_page_config(
    page_title="Warehouse Inventory Management",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state for data persistence
if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame()  # Main DataFrame
if 'log' not in st.session_state:
    st.session_state.log = []  # Log of changes

# Sidebar for file upload
with st.sidebar:
    st.header("Upload Excel File")
    uploaded_file = st.file_uploader("Drag and drop your Excel file here", type=["xlsx", "xls"])
    
    if uploaded_file:
        st.session_state.df = pd.read_excel(uploaded_file)
        st.session_state.log.append("Uploaded new Excel file")
        st.success("Excel file uploaded and loaded successfully!")

# Tabs navigation
tab1, tab2, tab3 = st.tabs(["Dashboard Overview", "Inventory Management", "Logs"])

with tab1:
    st.header("Dashboard Overview")
    
    if not st.session_state.df.empty:
        total_skus = len(st.session_state.df)
        total_qty = st.session_state.df['QTYAVAILABLE'].sum()
        low_stock_threshold = 10  # Threshold for low stock alerts
        low_stock = st.session_state.df[st.session_state.df['QTYAVAILABLE'] < low_stock_threshold]
        
        # KPIs in cards with gradient colors (blue/purple theme)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("""
                <div style='background: linear-gradient(to right, #007bff, #6c5ce7); color: white; padding: 10px; border-radius: 5px; text-align: center;'>
                    <h4>Total SKUs</h4>
                    <h2>{}</h2>
                </div>
            """.format(total_skus), unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
                <div style='background: linear-gradient(to right, #007bff, #6c5ce7); color: white; padding: 10px; border-radius: 5px; text-align: center;'>
                    <h4>Total Quantity</h4>
                    <h2>{}</h2>
                </div>
            """.format(total_qty), unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
                <div style='background: linear-gradient(to right, #ff4d4d, #ff7675); color: white; padding: 10px; border-radius: 5px; text-align: center;'>
                    <h4>Low Stock Alerts</h4>
                    <h2>{}</h2>
                </div>
            """.format(len(low_stock)), unsafe_allow_html=True)
        
        if len(low_stock) > 0:
            st.warning(f"{len(low_stock)} items are below the low stock threshold of {low_stock_threshold}.")
        
        with st.expander("Low Stock Details"):
            st.dataframe(low_stock.style.highlight_min(axis=0, subset=['QTYAVAILABLE'], color='red'))

with tab2:
    st.header("Inventory Management")
    
    if not st.session_state.df.empty:
        # Search and filter
        search_query = st.text_input("Search by SKU, DESCR, or Location (e.g., 21KCH2)")
        if search_query:
            filtered_df = st.session_state.df[
                st.session_state.df.apply(lambda row: search_query.upper() in str(row).upper(), axis=1)
            ]
        else:
            filtered_df = st.session_state.df
        
        # Color coding based on QTYAVAILABLE
        def highlight_rows(row):
            color = 'red' if row['QTYAVAILABLE'] < 10 else 'yellow' if row['QTYAVAILABLE'] < 20 else 'green'
            return ['background-color: {}'.format(color)] * len(row)
        
        styled_df = filtered_df.style.apply(highlight_rows, axis=1)
        st.dataframe(styled_df, height=300)  # Display with minimal borders
        
        # Buttons for Add, Edit, Delete
        col_btn1, col_btn2, col_btn3 = st.columns(3)
        
        with col_btn1:
            if st.button("Add New SKU"):
               with st.form("Add Form"):
                   form_data = {}  # Dictionary to hold form inputs
                   for column in st.session_state.df.columns:
                       if st.session_state.df[column].dtype in ['int64', 'float64']:  # Check for numeric columns
                          form_data[column] = st.number_input(column, min_value=0 if column in ['QTYAVAILABLE', 'QTY'] else None)
                       else:
                           form_data[column] = st.text_input(column)
                   submitted = st.form_submit_button()
                   if submitted:
                      new_row = pd.DataFrame([form_data.values()], columns=form_data.keys())
                      st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
                      st.session_state.log.append(f"Added SKU: {form_data.get('SKU', 'Unknown')}")
                      st.success("SKU added successfully!")
        
        with col_btn2:
            if st.button("Edit Selected SKU"):
            selected_sku = st.selectbox("Select SKU to Edit", st.session_state.df['SKU'].unique())
            edit_row = st.session_state.df[st.session_state.df['SKU'] == selected_sku].iloc[0]
           with st.form("Edit Form"):
              form_data = {}
              for column in st.session_state.df.columns:
                  if st.session_state.df[column].dtype in ['int64', 'float64']:
                     form_data[column] = st.number_input(column, value=edit_row[column], min_value=0 if column in ['QTYAVAILABLE', 'QTY'] else None)
                  else:
                      form_data[column] = st.text_input(column, value=str(edit_row[column]))  # Convert to string for text input
               submitted_edit = st.form_submit_button()
               if submitted_edit:
              for column in st.session_state.df.columns:
                  st.session_state.df.loc[st.session_state.df['SKU'] == selected_sku, column] = form_data[column]
                  st.session_state.log.append(f"Edited SKU: {selected_sku}")
                  st.success("SKU edited successfully!")
        with col_btn3:
            selected_sku_delete = st.selectbox("Select SKU to Delete", st.session_state.df['SKU'].unique())
            if st.button("Delete Selected SKU"):
                st.session_state.df = st.session_state.df[st.session_state.df['SKU'] != selected_sku_delete]
                st.session_state.log.append(f"Deleted SKU: {selected_sku_delete}")
                st.success("SKU deleted successfully!")
        
        # Download current table as Excel
        def get_excel_download_link(df):
            output = df.to_excel(index=False)
            b64 = base64.b64encode(output.encode()).decode()
            return f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="inventory.xlsx">Download Excel</a>'
        
        st.markdown(get_excel_download_link(st.session_state.df), unsafe_allow_html=True)

with tab3:
    st.header("Logs")
    if st.session_state.log:
        log_df = pd.DataFrame(st.session_state.log, columns=["Log Entries"])
        st.dataframe(log_df)  # Simple log table
    else:
        st.info("No logs yet.")

      # Download current table as Excel using BytesIO
        
        def get_excel_download_link(df):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
            output.seek(0)
            b64 = base64.b64encode(output.getvalue()).decode()  # Still use base64 for the link, but with BytesIO
            href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="inventory.xlsx">Download Excel</a>'
            return href
        
        st.markdown(get_excel_download_link(st.session_state.df), unsafe_allow_html=True)
    
    # End of tab2 content

with tab3:
    st.header("Logs")
    if st.session_state.log:
        log_df = pd.DataFrame(st.session_state.log, columns=["Log Entries"])  # Dynamically show all logs
        st.dataframe(log_df, height=200)  # Make the log table scrollable for better readability
    else:
        st.info("No logs yet.")
    
    if st.button("Clear Log"):
        st.session_state.log = []  # Clear the log array
        st.success("Log cleared successfully!")  # Immediate feedback

    
    if st.button("Clear Log"):
        st.session_state.log = []
        st.success("Log cleared successfully!")



