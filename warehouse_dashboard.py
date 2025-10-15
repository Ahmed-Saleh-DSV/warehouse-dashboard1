import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io
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
        # Search and filter for basic UX
        search_query = st.text_input("Search by SKU or Description")
        if search_query:
            filtered_df = st.session_state.df[
                st.session_state.df.apply(lambda row: search_query.upper() in str(row).upper(), axis=1)
            ]
        else:
            filtered_df = st.session_state.df
        
        # Color-coded table using styled DataFrame
        def highlight_rows(row):
            color = 'red' if row['QTYAVAILABLE'] < 10 else 'yellow' if row['QTYAVAILABLE'] < 20 else 'green'
            return ['background-color: {}'.format(color)] * len(row)
        
        styled_df = filtered_df.style.apply(highlight_rows, axis=1)
        st.dataframe(styled_df, height=400)  # Scrollable table
        
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
        
        # Edit existing SKU
        selected_sku = st.selectbox("Select SKU to Edit", st.session_state.df['SKU'].unique())
        if st.button("Edit Selected SKU"):
            edit_row = st.session_state.df[st.session_state.df['SKU'] == selected_sku].iloc[0]
            with st.form("Edit Form"):
                form_data = generate_dynamic_form(st.session_state.df, is_edit=True, edit_row=edit_row)
                submitted_edit = st.form_submit_button()
                if submitted_edit:
                    for idx, row in st.session_state.df.iterrows():
                        if row['SKU'] == selected_sku:
                            st.session_state.df.loc[idx] = list(form_data.values())
                    st.session_state.log.append(f"Edited SKU: {selected_sku}")
                    st.success("SKU edited successfully!")
        
        # Delete SKU with confirmation
        if st.button("Delete Selected SKU"):
            selected_sku_delete = st.selectbox("Select SKU to Delete", st.session_state.df['SKU'].unique())
            if st.button("Confirm Delete"):
                if st.confirm("Are you sure?"):
                    st.session_state.df = st.session_state.df[st.session_state.df['SKU'] != selected_sku_delete]
                    st.session_state.log.append(f"Deleted SKU: {selected_sku_delete}")
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
