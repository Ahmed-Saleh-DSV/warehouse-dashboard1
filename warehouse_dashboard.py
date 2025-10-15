import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from st_aggrid import AgGrid, GridOptionsBuilder  # For high-performance tables
import io
import base64
import time  # For loading indicators

# Page configuration for a professional, wide, and modern layout
st.set_page_config(
    layout="wide",
    page_title="Professional Warehouse Inventory Dashboard",
    page_icon="📦"
)

# Initialize session state for persistence and performance
if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame()  # Main inventory DataFrame
if 'log' not in st.session_state:
    st.session_state.log = []  # Log of changes

# Sidebar for file upload with a modern design
with st.sidebar:
    st.header("File Upload and Controls")
    uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx", "xls"])
    if uploaded_file:
        with st.spinner("Loading data..."):
            time.sleep(1)  # Simulate loading for UX
            st.session_state.df = pd.read_excel(uploaded_file)
            st.session_state.log.append("Uploaded new Excel file")
        st.success("Excel file uploaded and loaded successfully!")

# Tabs navigation for a clean, responsive interface
tab1, tab2, tab3 = st.tabs(["Dashboard Overview", "Inventory Management", "Logs"])

# Function for dynamic form generation with type handling
def generate_dynamic_form(df, is_edit=False, edit_row=None):
    form_data = {}
    for column in df.columns:
        if df[column].dtype in ['int64', 'float64']:  # Numeric columns
            if is_edit:
                # Use float to handle mixed types, then convert back
                form_data[column] = st.number_input(column, value=float(edit_row[column]), format="%.2f")
            else:
                form_data[column] = st.number_input(column, value=0.0, format="%.2f")  # Default to float
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
        
        # Modern KPIs with tooltips and professional styling
        col1, col2, col3 = st.columns(3)
        with col1: st.metric(label="Total SKUs", value=total_skus, help="Total unique SKUs in inventory", label_color="#1E90FF")
        with col2: st.metric(label="Total Quantity", value=total_qty, help="Sum of available quantity", label_color="#32CD32")
        with col3: st.metric(label="Low Stock Alerts", value=len(low_stock), help=f"Items below {low_stock_threshold}", label_color="#FF4500")
        
        # Interactive and optimized Plotly charts
        if not low_stock.empty:
            with st.spinner("Generating charts..."):
                fig_bar = px.bar(low_stock, x='SKU', y='QTYAVAILABLE', title="Low Stock Items",
                                 labels={'QTYAVAILABLE': 'Quantity Available'},
                                 color='QTYAVAILABLE', color_continuous_scale='reds')
                st.plotly_chart(fig_bar, use_container_width=True)
                
                location_cols = [col for col in st.session_state.df.columns if col in ['21KCH2', '21KCH5', '3K-M45', '6KMZ-2', 'YARD']]
                if location_cols and len(location_cols) >= 2:
                    try:
                        pivot_data = st.session_state.df.pivot_table(
                            values='QTYAVAILABLE',
                            index=location_cols[0],
                            columns=location_cols[1],
                            aggfunc='sum'
                        ).fillna(0)
                        fig_heatmap = go.Figure(data=go.Heatmap(
                            z=pivot_data.values,
                            x=pivot_data.columns,
                            y=pivot_data.index,
                            colorscale='Greens'
                        ))
                        fig_heatmap.update_layout(title="Quantity Distribution Across Locations")
                        st.plotly_chart(fig_heatmap, use_container_width=True)
                    except Exception as e:
                        st.error(f"Error generating heatmap: {e}")
        
        with st.expander("Low Stock Details"):
            st.dataframe(low_stock.style.format(precision=2))

with tab2:
    st.header("Inventory Management")
    
    if not st.session_state.df.empty:
        # Use AgGrid for high-performance, editable table
        try:
            gb = GridOptionsBuilder.from_dataframe(st.session_state.df)
            gb.configure_pagination(paginationAutoPageSize=True)
            gb.configure_side_bar()
            gb.configure_selection(selection_mode="single", use_checkbox=True)
            gb.configure_grid_options(editable=True)  # Inline editing
            gb.configure_columns([{"field": "QTYAVAILABLE", "cellStyle": {"backgroundColor": lambda params: "red" if params['value'] < 10 else "yellow" if params['value'] < 20 else "green"}}])
            grid_options = gb.build()
            
            grid_response = AgGrid(st.session_state.df, gridOptions=grid_options, height=400, update_mode='GRID_CHANGED')
            updated_df = pd.DataFrame(grid_response['data'])
            st.session_state.df = updated_df  # Update immediately
            st.session_state.log.append("Updated inventory via AgGrid")
            
            # Add new SKU with form
            if st.button("Add New SKU"):
                with st.form("Add Form"):
                    form_data = generate_dynamic_form(st.session_state.df)
                    submitted = st.form_submit_button()
                    if submitted:
                        new_row = pd.DataFrame([form_data], columns=st.session_state.df.columns)  # Match columns exactly
                        st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
                        st.session_state.log.append(f"Added SKU: {form_data.get('SKU', 'Unknown')}")
                        st.success("SKU added successfully!")
            
            # Edit and Delete are handled via AgGrid inline editing
            if st.button("Delete Selected SKU"):
                selected_rows = grid_response['selected_rows']
                if selected_rows and st.confirm("Are you sure?"):
                    sku_to_delete = selected_rows[0]['SKU']
                    st.session_state.df = st.session_state.df[st.session_state.df['SKU'] != sku_to_delete]
                    st.session_state.log.append(f"Deleted SKU: {sku_to_delete}")
                    st.success("SKU deleted successfully!")
            
        except ImportError:
            # Fallback to st.dataframe if AgGrid is not installed
            st.warning("AgGrid not installed. Falling back to basic table for performance.")
            search_query = st.text_input("Search by SKU or Description")
            filtered_df = st.session_state.df if not search_query else st.session_state.df[st.session_state.df.apply(lambda row: search_query.upper() in str(row).upper(), axis=1)]
            styled_df = filtered_df.style.apply(lambda row: ['background-color: red' if row['QTYAVAILABLE'] < 10 else 'background-color: yellow' if row['QTYAVAILABLE'] < 20 else 'background-color: green' for _ in row], axis=1)
            st.dataframe(styled_df, height=400)
            # Add/Edit/Delete forms as before
            if st.button("Add New SKU"):
                with st.form("Add Form"):
                    form_data = generate_dynamic_form(st.session_state.df)
                    submitted = st.form_submit_button()
                    if submitted:
                        new_row = pd.DataFrame([form_data], columns=st.session_state.df.columns)
                        st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
                        st.success("SKU added successfully!")
            # Similar for Edit and Delete...

        # Reliable Excel export
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
        st.dataframe(log_df.style.format(precision=2), height=300)
    else:
        st.info("No logs yet.")
    
    if st.button("Clear Log"):
        st.session_state.log = []
        st.success("Log cleared successfully!")
