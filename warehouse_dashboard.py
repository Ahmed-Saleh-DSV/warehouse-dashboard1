import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import io
from utils.data_handler import DataHandler
from utils.chart_generator import ChartGenerator
from utils.excel_handler import ExcelHandler

# Page configuration
st.set_page_config(
    page_title="Warehouse Inventory Dashboard",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize session state
if 'inventory_data' not in st.session_state:
    st.session_state.inventory_data = pd.DataFrame()
if 'activity_logs' not in st.session_state:
    st.session_state.activity_logs = []
if 'low_stock_threshold' not in st.session_state:
    st.session_state.low_stock_threshold = 10

# Initialize handlers
data_handler = DataHandler()
chart_generator = ChartGenerator()
excel_handler = ExcelHandler()

def main():
    st.title("📦 Warehouse Inventory Dashboard")
    st.markdown("---")
    
    # File upload section
    with st.container():
        st.subheader("📁 Data Upload")
        uploaded_file = st.file_uploader(
            "Upload Excel file with inventory data",
            type=['xlsx', 'xls'],
            help="Upload an Excel file containing SKU, Description, QTYAVAILABLE, and location columns"
        )
        
        if uploaded_file is not None:
            try:
                with st.spinner("Processing file..."):
                    df = pd.read_excel(uploaded_file)
                    if data_handler.validate_data(df):
                        st.session_state.inventory_data = df
                        st.success(f"✅ Successfully loaded {len(df)} items from {uploaded_file.name}")
                        data_handler.log_activity("Upload", f"Loaded {len(df)} items from {uploaded_file.name}")
                    else:
                        st.error("❌ Invalid file format. Please ensure your Excel file contains the required columns.")
            except Exception as e:
                st.error(f"❌ Error reading file: {str(e)}")
    
    st.markdown("---")
    
    # Main tabs
    tab1, tab2, tab3 = st.tabs(["📊 Overview", "📋 Inventory Management", "📝 Logs"])
    
    with tab1:
        render_overview_tab()
    
    with tab2:
        render_inventory_management_tab()
    
    with tab3:
        render_logs_tab()

def render_overview_tab():
    """Render the Overview tab with KPIs and charts"""
    if st.session_state.inventory_data.empty:
        st.info("📋 Please upload an Excel file to view the dashboard.")
        return
    
    df = st.session_state.inventory_data
    
    # KPI Cards
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_skus = len(df)
        st.markdown(
            f"""
            <div style="
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 1.5rem;
                border-radius: 10px;
                color: white;
                text-align: center;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            ">
                <h2 style="margin: 0; font-size: 2.5rem;">{total_skus}</h2>
                <p style="margin: 0.5rem 0 0 0; font-size: 1.1rem;">Total SKUs</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    with col2:
        total_quantity = df['QTYAVAILABLE'].sum() if 'QTYAVAILABLE' in df.columns else 0
        st.markdown(
            f"""
            <div style="
                background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                padding: 1.5rem;
                border-radius: 10px;
                color: white;
                text-align: center;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            ">
                <h2 style="margin: 0; font-size: 2.5rem;">{total_quantity:,}</h2>
                <p style="margin: 0.5rem 0 0 0; font-size: 1.1rem;">Total Quantity</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    with col3:
        low_stock_count = len(df[df['QTYAVAILABLE'] <= st.session_state.low_stock_threshold]) if 'QTYAVAILABLE' in df.columns else 0
        st.markdown(
            f"""
            <div style="
                background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
                padding: 1.5rem;
                border-radius: 10px;
                color: #333;
                text-align: center;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            ">
                <h2 style="margin: 0; font-size: 2.5rem; color: #d63384;">{low_stock_count}</h2>
                <p style="margin: 0.5rem 0 0 0; font-size: 1.1rem;">Low Stock Alerts</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Low Stock Alerts
    if low_stock_count > 0:
        st.warning(f"⚠️ {low_stock_count} items are below the low stock threshold of {st.session_state.low_stock_threshold} units!")
        
        # Low Stock Items Table
        st.subheader("🔻 Low Stock Items")
        low_stock_items = df[df['QTYAVAILABLE'] <= st.session_state.low_stock_threshold]
        
        # Display columns that exist in the dataframe
        display_columns = ['SKU', 'Description', 'QTYAVAILABLE']
        location_columns = [col for col in df.columns if col not in display_columns and col != '']
        display_columns.extend(location_columns)
        
        # Filter to only include columns that exist
        available_columns = [col for col in display_columns if col in low_stock_items.columns]
        
        st.dataframe(
            low_stock_items[available_columns],
            use_container_width=True,
            hide_index=True
        )
        
        # Low Stock Bar Chart
        if 'SKU' in low_stock_items.columns:
            fig_bar = chart_generator.create_low_stock_chart(low_stock_items)
            st.plotly_chart(fig_bar, use_container_width=True)
    
    # Location Summary Charts
    st.subheader("📍 Location Summary")
    location_columns = [col for col in df.columns if col not in ['SKU', 'Description', 'QTYAVAILABLE'] and col != '']
    
    if location_columns:
        # Create location summary
        location_summary = {}
        for col in location_columns:
            if df[col].dtype in ['int64', 'float64']:
                location_summary[col] = df[col].sum()
        
        if location_summary:
            fig_locations = chart_generator.create_location_summary_chart(location_summary)
            st.plotly_chart(fig_locations, use_container_width=True)
        else:
            st.info("No numeric location data found for summary charts.")
    else:
        st.info("No location columns detected in the data.")

def render_inventory_management_tab():
    """Render the Inventory Management tab"""
    if st.session_state.inventory_data.empty:
        st.info("📋 Please upload an Excel file to manage inventory.")
        return
    
    df = st.session_state.inventory_data
    
    # Action buttons
    col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 2])
    
    with col1:
        if st.button("➕ Add New SKU", use_container_width=True):
            st.session_state.show_add_form = True
    
    with col2:
        if st.button("✏️ Edit Selected", use_container_width=True):
            st.session_state.show_edit_form = True
    
    with col3:
        if st.button("🗑️ Delete Selected", use_container_width=True):
            st.session_state.show_delete_confirm = True
    
    with col4:
        if st.button("📥 Export Excel", use_container_width=True):
            excel_buffer = excel_handler.export_to_excel(df)
            st.download_button(
                label="Download Excel File",
                data=excel_buffer.getvalue(),
                file_name=f"inventory_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    
    with col5:
        threshold = st.number_input(
            "Low Stock Threshold",
            min_value=1,
            max_value=100,
            value=st.session_state.low_stock_threshold,
            key="threshold_input"
        )
        if threshold != st.session_state.low_stock_threshold:
            st.session_state.low_stock_threshold = threshold
            st.rerun()
    
    # Search and Filter
    st.subheader("🔍 Search & Filter")
    col1, col2 = st.columns(2)
    
    with col1:
        search_term = st.text_input("Search SKU or Description:", key="search_input")
    
    with col2:
        location_filter = st.selectbox(
            "Filter by Location:",
            ["All"] + [col for col in df.columns if col not in ['SKU', 'Description', 'QTYAVAILABLE']],
            key="location_filter"
        )
    
    # Filter data
    filtered_df = df.copy()
    
    if search_term:
        mask = False
        if 'SKU' in filtered_df.columns:
            mask |= filtered_df['SKU'].astype(str).str.contains(search_term, case=False, na=False)
        if 'Description' in filtered_df.columns:
            mask |= filtered_df['Description'].astype(str).str.contains(search_term, case=False, na=False)
        filtered_df = filtered_df[mask]
    
    # Display inventory table with conditional coloring
    st.subheader("📋 Inventory Table")
    
    # Apply conditional formatting
    def color_rows(row):
        if 'QTYAVAILABLE' in row:
            qty = row['QTYAVAILABLE']
            if qty <= st.session_state.low_stock_threshold:
                return ['background-color: #ffebee'] * len(row)  # Light red
            elif qty <= st.session_state.low_stock_threshold * 2:
                return ['background-color: #fff3e0'] * len(row)  # Light orange
            else:
                return ['background-color: #e8f5e8'] * len(row)  # Light green
        return [''] * len(row)
    
    # Display dataframe
    st.dataframe(
        filtered_df,
        use_container_width=True,
        hide_index=True
    )
    
    # Handle forms
    handle_inventory_forms(df)

def handle_inventory_forms(df):
    """Handle add/edit/delete forms"""
    
    # Add form
    if st.session_state.get('show_add_form', False):
        with st.expander("➕ Add New SKU", expanded=True):
            with st.form("add_sku_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    new_sku = st.text_input("SKU*")
                    new_qty = st.number_input("Quantity Available*", min_value=0, value=0)
                
                with col2:
                    new_description = st.text_input("Description")
                
                # Dynamic location fields
                location_columns = [col for col in df.columns if col not in ['SKU', 'Description', 'QTYAVAILABLE']]
                location_values = {}
                
                if location_columns:
                    st.subheader("Location Details")
                    for col in location_columns:
                        location_values[col] = st.number_input(f"{col}", min_value=0, value=0, key=f"add_{col}")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("Add SKU"):
                        if new_sku:
                            new_row = {
                                'SKU': new_sku,
                                'Description': new_description,
                                'QTYAVAILABLE': new_qty
                            }
                            new_row.update(location_values)
                            
                            st.session_state.inventory_data = pd.concat([
                                st.session_state.inventory_data,
                                pd.DataFrame([new_row])
                            ], ignore_index=True)
                            
                            data_handler.log_activity("Add", f"Added SKU: {new_sku}")
                            st.success(f"✅ Added SKU: {new_sku}")
                            st.session_state.show_add_form = False
                            st.rerun()
                        else:
                            st.error("SKU is required!")
                
                with col2:
                    if st.form_submit_button("Cancel"):
                        st.session_state.show_add_form = False
                        st.rerun()

def render_logs_tab():
    """Render the Logs tab"""
    st.subheader("📝 Activity Logs")
    
    col1, col2 = st.columns([8, 2])
    
    with col2:
        if st.button("🗑️ Clear Logs", use_container_width=True):
            st.session_state.activity_logs = []
            st.success("Logs cleared!")
            st.rerun()
    
    if st.session_state.activity_logs:
        logs_df = pd.DataFrame(st.session_state.activity_logs)
        st.dataframe(logs_df, use_container_width=True, hide_index=True)
    else:
        st.info("No activity logs available.")

if __name__ == "__main__":
    main()
