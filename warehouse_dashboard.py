
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import io
import streamlit_authenticator as stauth
from utils.data_handler import DataHandler
from utils.chart_generator import ChartGenerator
from utils.excel_handler import ExcelHandler
from utils.db_handler import DatabaseHandler

# Page configuration
st.set_page_config(
    page_title="Warehouse Inventory Dashboard",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize handlers
data_handler = DataHandler()
chart_generator = ChartGenerator()
excel_handler = ExcelHandler()
db_handler = DatabaseHandler()

# Initialize session state
if 'inventory_data' not in st.session_state:
    # Try to load from database first
    if db_handler.is_connected():
        st.session_state.inventory_data = db_handler.load_inventory()
    else:
        st.session_state.inventory_data = pd.DataFrame()

if 'activity_logs' not in st.session_state:
    # Try to load from database first
    if db_handler.is_connected():
        st.session_state.activity_logs = db_handler.load_logs()
    else:
        st.session_state.activity_logs = []

if 'low_stock_threshold' not in st.session_state:
    st.session_state.low_stock_threshold = 10

if 'db_initialized' not in st.session_state:
    st.session_state.db_initialized = db_handler.is_connected()

# Authentication configuration
# NOTE: These are DEMO credentials for development/testing only.
# In production, replace with environment variables or database-backed user management.
# Passwords will be auto-hashed by streamlit-authenticator.
if 'auth_config' not in st.session_state:
    st.session_state.auth_config = {
        'credentials': {
            'usernames': {
                'admin': {
                    'name': 'Admin User',
                    'email': 'admin@warehouse.com',
                    'password': 'admin123'  # Demo password - will be hashed
                },
                'manager': {
                    'name': 'Manager User',
                    'email': 'manager@warehouse.com',
                    'password': 'manager123'  # Demo password - will be hashed
                },
                'viewer': {
                    'name': 'Viewer User',
                    'email': 'viewer@warehouse.com',
                    'password': 'viewer123'  # Demo password - will be hashed
                }
            }
        },
        'cookie': {
            'expiry_days': 30,
            'key': 'warehouse_dashboard_key_2025',
            'name': 'warehouse_auth'
        },
        'preauthorized': {
            'emails': []
        }
    }

# Create authenticator
authenticator = stauth.Authenticate(
    st.session_state.auth_config['credentials'],
    st.session_state.auth_config['cookie']['name'],
    st.session_state.auth_config['cookie']['key'],
    st.session_state.auth_config['cookie']['expiry_days']
)

def main():
    # Authentication
    name, authentication_status, username = authenticator.login("Login", location="main")
    
    if authentication_status == False:
        st.error('Username/password is incorrect')
        st.info("Demo credentials: admin/admin123, manager/manager123, viewer/viewer123")
        return
    
    if authentication_status == None:
        st.warning('Please enter your username and password')
        st.info("Demo credentials: admin/admin123, manager/manager123, viewer/viewer123")
        return
    
    # User is authenticated
    st.title("📦 Warehouse Inventory Dashboard")
    
    # Sidebar with user info and logout
    with st.sidebar:
        st.write(f'Welcome **{name}**')
        st.write(f'Username: *{username}*')
        authenticator.logout('Logout', 'sidebar')
        st.markdown("---")
        st.info(f"Database: {'✅ Connected' if db_handler.is_connected() else '❌ Not Connected'}")
    
    st.markdown("---")
    
    # File upload section with drag-and-drop styling
    st.markdown(
        """
        <style>
        .upload-container {
            background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
            border: 2px dashed #667eea;
            border-radius: 15px;
            padding: 2rem;
            text-align: center;
            margin: 1rem 0;
            transition: all 0.3s ease;
        }
        .upload-container:hover {
            border-color: #764ba2;
            background: linear-gradient(135deg, #667eea25 0%, #764ba225 100%);
        }
        .upload-text {
            color: #667eea;
            font-size: 1.2rem;
            font-weight: 500;
            margin-bottom: 0.5rem;
        }
        .upload-subtext {
            color: #666;
            font-size: 0.9rem;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    with st.container():
        st.markdown(
            """
            <div class="upload-container">
                <div class="upload-text">📁 Drag & Drop Your Excel File Here</div>
                <div class="upload-subtext">or click to browse (Supports .xlsx and .xls files)</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        uploaded_file = st.file_uploader(
            "Upload Excel file with inventory data",
            type=['xlsx', 'xls'],
            help="Upload an Excel file containing SKU, Description, QTYAVAILABLE, and location columns",
            label_visibility="collapsed"
        )
        
        if uploaded_file is not None:
            try:
                with st.spinner("Processing file..."):
                    df = pd.read_excel(uploaded_file)
                    if data_handler.validate_data(df):
                        st.session_state.inventory_data = df
                        
                        # Save to database
                        if db_handler.is_connected():
                            db_handler.save_inventory(df)
                            db_handler.save_log("Upload", f"Loaded {len(df)} items from {uploaded_file.name}")
                        
                        data_handler.log_activity("Upload", f"Loaded {len(df)} items from {uploaded_file.name}")
                        st.success(f"✅ Successfully loaded {len(df)} items from {uploaded_file.name}")
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
        # Create location summary - extract only totals for chart
        location_summary = {}
        for col in location_columns:
            if df[col].dtype in ['int64', 'float64']:
                location_summary[col] = df[col].sum()
        
        if location_summary:
            col1, col2 = st.columns([1, 1])
            
            with col1:
                # Pass the simple {location: total} dict to chart generator
                fig_locations = chart_generator.create_location_summary_chart(location_summary)
                st.plotly_chart(fig_locations, use_container_width=True)
            
            with col2:
                # Add heatmap visualization
                fig_heatmap = chart_generator.create_inventory_heatmap(df)
                if fig_heatmap:
                    st.plotly_chart(fig_heatmap, use_container_width=True)
                else:
                    st.info("Heatmap requires at least 2 location columns with numeric data.")
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
    
    # Apply conditional formatting based on quantity
    def highlight_quantity(row):
        if 'QTYAVAILABLE' in row.index:
            qty = row['QTYAVAILABLE']
            if qty <= st.session_state.low_stock_threshold:
                color = '#ffcdd2'  # Light red
            elif qty <= st.session_state.low_stock_threshold * 2:
                color = '#fff9c4'  # Light yellow
            else:
                color = '#c8e6c9'  # Light green
            return [f'background-color: {color}'] * len(row)
        return [''] * len(row)
    
    # Apply styling and display
    if not filtered_df.empty:
        styled_df = filtered_df.style.apply(highlight_quantity, axis=1)
        st.dataframe(
            styled_df,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No data to display. Try adjusting your search filters.")
    
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
                            
                            # Save to database
                            if db_handler.is_connected():
                                db_handler.save_inventory(st.session_state.inventory_data)
                                db_handler.save_log("Add", f"Added SKU: {new_sku}")
                            
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
    
    # Edit form
    if st.session_state.get('show_edit_form', False):
        with st.expander("✏️ Edit SKU", expanded=True):
            # SKU selection
            if not df.empty and 'SKU' in df.columns:
                selected_sku = st.selectbox(
                    "Select SKU to Edit:",
                    options=df['SKU'].tolist(),
                    key="edit_sku_selector"
                )
                
                if selected_sku:
                    # Get the row data
                    row_index = df[df['SKU'] == selected_sku].index[0]
                    row_data = df.loc[row_index]
                    
                    with st.form("edit_sku_form"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            edit_sku = st.text_input("SKU*", value=str(row_data.get('SKU', '')))
                            edit_qty = st.number_input(
                                "Quantity Available*", 
                                min_value=0, 
                                value=int(row_data.get('QTYAVAILABLE', 0))
                            )
                        
                        with col2:
                            edit_description = st.text_input(
                                "Description", 
                                value=str(row_data.get('Description', ''))
                            )
                        
                        # Dynamic location fields
                        location_columns = [col for col in df.columns if col not in ['SKU', 'Description', 'QTYAVAILABLE']]
                        location_values = {}
                        
                        if location_columns:
                            st.subheader("Location Details")
                            for col in location_columns:
                                location_values[col] = st.number_input(
                                    f"{col}", 
                                    min_value=0, 
                                    value=int(row_data.get(col, 0)),
                                    key=f"edit_{col}"
                                )
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.form_submit_button("Update SKU"):
                                if edit_sku:
                                    # Update the row
                                    st.session_state.inventory_data.at[row_index, 'SKU'] = edit_sku
                                    st.session_state.inventory_data.at[row_index, 'Description'] = edit_description
                                    st.session_state.inventory_data.at[row_index, 'QTYAVAILABLE'] = edit_qty
                                    
                                    for col, val in location_values.items():
                                        st.session_state.inventory_data.at[row_index, col] = val
                                    
                                    # Save to database
                                    if db_handler.is_connected():
                                        db_handler.save_inventory(st.session_state.inventory_data)
                                        db_handler.save_log("Edit", f"Updated SKU: {edit_sku}")
                                    
                                    data_handler.log_activity("Edit", f"Updated SKU: {edit_sku}")
                                    st.success(f"✅ Updated SKU: {edit_sku}")
                                    st.session_state.show_edit_form = False
                                    st.rerun()
                                else:
                                    st.error("SKU is required!")
                        
                        with col2:
                            if st.form_submit_button("Cancel"):
                                st.session_state.show_edit_form = False
                                st.rerun()
            else:
                st.warning("No SKUs available to edit.")
                if st.button("Close"):
                    st.session_state.show_edit_form = False
                    st.rerun()
    
    # Delete form
    if st.session_state.get('show_delete_confirm', False):
        with st.expander("🗑️ Delete SKU", expanded=True):
            if not df.empty and 'SKU' in df.columns:
                selected_sku_delete = st.selectbox(
                    "Select SKU to Delete:",
                    options=df['SKU'].tolist(),
                    key="delete_sku_selector"
                )
                
                if selected_sku_delete:
                    st.warning(f"⚠️ Are you sure you want to delete SKU: {selected_sku_delete}?")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("🗑️ Confirm Delete", type="primary"):
                            # Delete the row
                            row_index = df[df['SKU'] == selected_sku_delete].index[0]
                            st.session_state.inventory_data = st.session_state.inventory_data.drop(row_index).reset_index(drop=True)
                            
                            # Save to database
                            if db_handler.is_connected():
                                db_handler.save_inventory(st.session_state.inventory_data)
                                db_handler.save_log("Delete", f"Deleted SKU: {selected_sku_delete}")
                            
                            data_handler.log_activity("Delete", f"Deleted SKU: {selected_sku_delete}")
                            st.success(f"✅ Deleted SKU: {selected_sku_delete}")
                            st.session_state.show_delete_confirm = False
                            st.rerun()
                    
                    with col2:
                        if st.button("Cancel"):
                            st.session_state.show_delete_confirm = False
                            st.rerun()
            else:
                st.warning("No SKUs available to delete.")
                if st.button("Close"):
                    st.session_state.show_delete_confirm = False
                    st.rerun()

def render_logs_tab():
    """Render the Logs tab"""
    st.subheader("📝 Activity Logs")
    
    col1, col2 = st.columns([8, 2])
    
    with col2:
        if st.button("🗑️ Clear Logs", use_container_width=True):
            st.session_state.activity_logs = []
            
            # Clear logs in database
            if db_handler.is_connected():
                db_handler.clear_logs()
            
            st.success("Logs cleared!")
            st.rerun()
    
    if st.session_state.activity_logs:
        logs_df = pd.DataFrame(st.session_state.activity_logs)
        st.dataframe(logs_df, use_container_width=True, hide_index=True)
    else:
        st.info("No activity logs available.")

if __name__ == "__main__":
    main()
