import streamlit as st
import pandas as pd
import plotly.express as px
import io
from fpdf import FPDF  # pip install fpdf2 for PDF export

# Custom CSS for professional styling (gray/blue theme, rounded, shadows)
st.markdown("""
<style>
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 0rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }
    .stMetric > label {
        color: #2E86AB;  /* Blue text */
        font-weight: bold;
    }
    .stMetric > div > div {
        color: #5F6A6A;  /* Gray values */
        font-size: 1.5em;
    }
    .metric-card {
        background-color: #F8F9FA;  /* Light gray */
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        padding: 1rem;
        text-align: center;
        margin: 0.5rem 0;
    }
    .stExpander > div > div {
        border-radius: 10px;
        border: 1px solid #DEE2E6;  /* Light border */
    }
    .stButton > button {
        border-radius: 8px;
        background-color: #2E86AB;  /* Blue buttons */
        color: white;
    }
    .stButton > button:hover {
        background-color: #1B5E7A;
    }
    .warning-box {
        background-color: #FFF3CD;
        border: 1px solid #FFEAA7;
        border-radius: 5px;
        padding: 1rem;
    }
    .success-box {
        background-color: #D4EDDA;
        border: 1px solid #C3E6CB;
        border-radius: 5px;
        padding: 1rem;
    }
    .error-box {
        background-color: #F8D7DA;
        border: 1px solid #F5C6CB;
        border-radius: 5px;
        padding: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Page configuration
st.set_page_config(
    page_title="Warehouse Inventory Dashboard",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Title
st.title("🏭 Warehouse Inventory Control Center")
st.markdown("Professional dashboard for managing warehouse inventory. Upload, edit, analyze, and export data with real-time validation and alerts.")

# Initialize session state
if 'df' not in st.session_state:
    st.session_state.df = None
if 'original_df' not in st.session_state:
    st.session_state.original_df = None
if 'deleted_df' not in st.session_state:
    st.session_state.deleted_df = pd.DataFrame()

# File upload
uploaded_file = st.file_uploader("📁 Upload Excel File", type="xlsx")

if uploaded_file is not None and st.session_state.df is None:
    try:
        df = pd.read_excel(uploaded_file, engine="openpyxl")
        if df.empty:
            st.warning("⚠️ Uploaded file is empty.")
        else:
            # Clean data
            numeric_cols = ['QTYHOLD', 'STDCUBE', 'QTYAVAILABLE', 'QTY']
            fixed_cols = ['SKU', 'DESCR'] + numeric_cols
            # Dynamically detect location columns: between QTYAVAILABLE and QTY
            location_cols = []
            if 'QTYAVAILABLE' in df.columns and 'QTY' in df.columns:
                qty_avail_idx = list(df.columns).index('QTYAVAILABLE')
                qty_idx = list(df.columns).index('QTY')
                if qty_idx > qty_avail_idx + 1:
                    location_cols = list(df.columns)[qty_avail_idx + 1 : qty_idx]
                else:
                    st.warning("⚠️ No location columns detected between QTYAVAILABLE and QTY. Proceeding without them.")
            else:
                st.warning("⚠️ QTYAVAILABLE or QTY column missing. Skipping location detection.")
                location_cols = [col for col in df.columns if col not in fixed_cols]
            
            # Clean numeric columns (skip missing ones silently)
            all_numeric_cols = [col for col in numeric_cols + location_cols if col in df.columns]
            for col in all_numeric_cols:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            df = df.dropna(subset=['SKU'])
            if 'Status' not in df.columns:
                df['Status'] = 'Active'
            st.session_state.df = df
            st.session_state.original_df = df.copy()
            st.session_state.deleted_df = pd.DataFrame()
            st.success(f"✅ Loaded {len(df)} rows. Detected {len(location_cols)} location columns: {', '.join(location_cols) if location_cols else 'None'}.")
            st.rerun()
    except Exception as e:
        st.error(f"❌ Error loading file: {e}")

# Main dashboard logic
if st.session_state.df is not None and not st.session_state.df.empty:
    df = st.session_state.df.copy()
    
    # Re-detect location columns dynamically (in case of edits/changes)
    location_cols = []
    if 'QTYAVAILABLE' in df.columns and 'QTY' in df.columns:
        qty_avail_idx = list(df.columns).index('QTYAVAILABLE')
        qty_idx = list(df.columns).index('QTY')
        if qty_idx > qty_avail_idx + 1:
            location_cols = list(df.columns)[qty_avail_idx + 1 : qty_idx]
        else:
            st.warning("⚠️ No location columns detected between QTYAVAILABLE and QTY. Proceeding without them.")
    else:
        st.warning("⚠️ QTYAVAILABLE or QTY column missing. Skipping location detection.")
        # Fallback: any non-fixed columns
        fixed_cols = ['SKU', 'DESCR', 'QTYHOLD', 'STDCUBE', 'QTYAVAILABLE', 'QTY', 'Status']
        location_cols = [col for col in df.columns if col not in fixed_cols]
    
    # Enhanced Sidebar Filters
    st.sidebar.header("🔍 Enhanced Filters")
    status_filter = st.sidebar.selectbox(
        "Status Filter",
        options=['All', 'Active', 'Deleted'],
        index=0,
        help="Filter by item status"
    )
    location_filter = st.sidebar.multiselect(
        "Location Filter",
        options=location_cols,
        default=location_cols[:5] if len(location_cols) > 5 else location_cols,
        help="Filter data by specific locations"
    )
    sku_search = st.sidebar.text_input("SKU Search", placeholder="Enter SKU...")
    descr_search = st.sidebar.text_input("Description Search", placeholder="Enter description...")
    
    if st.sidebar.button("🔄 Reset Filters"):
        status_filter = 'All'
        location_filter = location_cols[:5] if len(location_cols) > 5 else location_cols
        sku_search = ""
        descr_search = ""
        st.rerun()
    
    # Apply filters
    filtered_df = df.copy()
    if status_filter != 'All':
        filtered_df = filtered_df[filtered_df['Status'] == status_filter]
    if sku_search:
        filtered_df = filtered_df[filtered_df['SKU'].astype(str).str.contains(sku_search, case=False, na=False)]
    if descr_search:
        filtered_df = filtered_df[filtered_df['DESCR'].astype(str).str.contains(descr_search, case=False, na=False)]
    if location_filter:
        # Filter rows where at least one selected location has quantity >0 (skip missing columns)
        loc_mask_cols = [col for col in location_filter if col in filtered_df.columns]
        if loc_mask_cols:
            loc_mask = filtered_df[loc_mask_cols].sum(axis=1) > 0
            filtered_df = filtered_df[loc_mask]
        else:
            st.warning("⚠️ No valid location columns selected for filtering. Showing all data.")
    
    # Display columns for table (exclude Status for main view, include in deleted; skip missing)
    display_cols = ['SKU', 'DESCR', 'QTYHOLD', 'STDCUBE', 'QTYAVAILABLE']
    display_cols += [col for col in location_filter if col in df.columns]
    display_cols += ['QTY', 'Status']
    
    # KPI Cards (Dashboard Overview)
    col1, col2, col3, col4 = st.columns(4)
    active_df = df[df['Status'] == 'Active']
    deleted_count = len(df[df['Status'] == 'Deleted'])
    total_skus = len(active_df['SKU'].unique())
    total_qty = active_df['QTY'].sum()
    active_locations = len([col for col in location_cols if col in active_df.columns and active_df[col].sum() > 0])
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Total SKUs", total_skus)
        st.markdown('📦', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Total Quantity", f"{total_qty:,.0f}")
        st.markdown('📦', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Active Locations", active_locations)
        st.markdown('🏭', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Deleted SKUs", deleted_count)
        st.markdown('🗑️', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # CRUD Buttons
    col_add, col_del, col_restore = st.columns(3)
    with col_add:
        if st.button("🆕 Add SKU"):
            with st.expander("Add New SKU", expanded=True):
                new_sku = st.text_input("SKU")
                new_descr = st.text_area("Description")
                new_qtyhold = st.number_input("QTYHOLD", min_value=0.0, value=0.0)
                new_stdcube = st.number_input("STDCUBE", min_value=0.0, value=1.0)
                new_qtyavailable = st.number_input("QTYAVAILABLE", min_value=0.0, value=0.0)
                new_qty = st.number_input("QTY", min_value=0.0, value=0.0)
                new_location_values = {}
                for loc in location_cols[:5]:  # Limit inputs to first 5 detected locations
                    if loc in df.columns:  # Skip if missing
                        new_location_values[loc] = st.number_input(f"Qty in {loc}", min_value=0.0, value=0.0)
                    else:
                        new_location_values[loc] = 0.0  # Default if missing
                
                if st.button("Add"):
                    # Validation (skip missing columns)
                    sum_locations = sum(new_location_values.get(loc, 0.0) for loc in location_cols if loc in df.columns)
                    if sum_locations > new_qtyavailable:
                        st.error("❌ Sum of location quantities exceeds QTYAVAILABLE. Please adjust.")
                    else:
                        new_row = pd.DataFrame({
                            'SKU': [new_sku],
                            'DESCR': [new_descr],
                            'QTYHOLD': [new_qtyhold],
                            'STDCUBE': [new_stdcube],
                            'QTYAVAILABLE': [new_qtyavailable],
                            'QTY': [new_qty],
                            'Status': ['Active']
                        })
                        # Add location columns (skip missing)
                        for loc in location_cols:
                            if loc in df.columns:
                                new_row[loc] = new_location_values.get(loc, 0.0)
                            else:
                                if loc not in new_row.columns:
                                    new_row[loc] = 0.0
                        
                        st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
                        st.success("✅ New SKU added!")
                        st.rerun()
    
    with col_del:
        if st.button("❌ Delete SKU"):
            with st.expander("Delete SKU", expanded=True):
                sku_to_delete = st.selectbox("Select SKU to Delete", options=df['SKU'].unique())
                if st.button("Confirm Delete"):
                    df.loc[df['SKU'] == sku_to_delete, 'Status'] = 'Deleted'
                    st.session_state.df = df
                    st.success("✅ SKU marked as deleted.")
                    st.rerun()
    
    with col_restore:
        if st.button("🔁 Restore SKU"):
            with st.expander("Restore SKU", expanded=True):
                deleted_skus = df[df['Status'] == 'Deleted']['SKU'].unique()
                if deleted_skus:
                    sku_to_restore = st.selectbox("Select Deleted SKU", options=deleted_skus)
                    if st.button("Confirm Restore"):
                        df.loc[df['SKU'] == sku_to_restore, 'Status'] = 'Active'
                        st.session_state.df = df
                        st.success("✅ SKU restored!")
                        st.rerun()
                else:
                    st.info("No deleted SKUs to restore.")
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📦 Inventory Table", "📈 Charts & Analytics", "🚨 Alerts & Notifications", "🗑️ Recycle Bin"])
    
    with tab1:
        st.header("📦 Inventory Table")
        st.markdown("Edit cells directly. Validation ensures location quantities ≤ QTYAVAILABLE.")
        
        # Editable table (skip missing columns in display)
        safe_display_cols = [col for col in display_cols if col in filtered_df.columns]
        edited_df = st.data_editor(
            filtered_df[safe_display_cols],
            num_rows="dynamic",
            use_container_width=True,
            height=400
        )
        
        # Validation on edit (simple check for demo; in production, use callbacks)
        if not edited_df.empty:
            for idx, row in edited_df.iterrows():
                # Sum only existing location columns
                existing_locs = [col for col in location_cols if col in edited_df.columns]
                sum_loc = row[existing_locs].sum() if existing_locs else 0
                if sum_loc > row.get('QTYAVAILABLE', 0):
                    st.error(f"Row {idx}: Location sum ({sum_loc}) > QTYAVAILABLE ({row.get('QTYAVAILABLE', 0)}). Adjust values.")
        
        # Export
        col_exp1, col_exp2 = st.columns(2)
        with col_exp1:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                edited_df.to_excel(writer, index=False)
            buffer.seek(0)
            st.download_button(
                label="📥 Export to Excel",
                data=buffer,
                file_name="inventory.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        with col_exp2:
            # PDF Export (skip missing columns)
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            for col in safe_display_cols:
                pdf.cell(40, 10, str(col), 1)
            pdf.ln()
            for _, row in edited_df.iterrows():
                for col in safe_display_cols:
                    val = row.get(col, '') if col in row else ''
                    pdf.cell(40, 10, str(val), 1)
                pdf.ln()
            pdf_output = pdf.output(dest='S').encode('latin1')
            pdf_buffer = io.BytesIO(pdf_output)
            st.download_button(
                label="🧾 Export to PDF",
                data=pdf_buffer,
                file_name="inventory.pdf",
                mime="application/pdf"
            )
    
    with tab2:
        st.header("📈 Charts & Analytics")
        
        # Pie Chart: Quantity distribution per location (skip missing)
        valid_location_cols = [col for col in location_cols if col in df.columns]
        if valid_location_cols:
            st.subheader("Quantity Distribution per Location")
            loc_sums = df[valid_location_cols].sum()
            fig_pie = px.pie(
                values=loc_sums.values,
                names=loc_sums.index,
                title="Total Quantity by Location",
                color_discrete_sequence=px.colors.sequential.Blues
            )
            fig_pie.update_traces(textinfo="label+percent+value")
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.warning("⚠️ No valid location columns for chart.")
        
        # Bar Chart: Top 10 SKUs by total quantity
        st.subheader("Top 10 SKUs by Total Quantity")
        sku_totals = df.groupby('SKU')['QTY'].sum().sort_values(ascending=False).head(10)
        fig_bar = px.bar(
            x=sku_totals.index,
            y=sku_totals.values,
            title="Top SKUs by Quantity",
            color=sku_totals.values,
            color_continuous_scale='Viridis'
        )
        fig_bar.update_layout(xaxis_tickangle=45)
        st.plotly_chart(fig_bar, use_container_width=True)
    
    with tab3:
        st.header("🚨 Alerts & Notifications")
        
        # Low stock alerts (skip missing columns)
        low_stock = filtered_df[filtered_df['QTYAVAILABLE'] < threshold]
        zero_stock = filtered_df[filtered_df['QTYAVAILABLE'] == 0]
        
        col_a1, col_a2 = st.columns(2)
        with col_a1:
            if len(zero_stock) > 0:
                st.error(f"🚨 {len(zero_stock)} Zero-Stock Items")
            else:
                st.success("✅ No Zero-Stock Items")
        with col_a2:
            st.info(f"⚠️ {len(low_stock)} Low-Stock Items (< {threshold})")
        
        if not low_stock.empty:
            st.subheader("Low Stock Items")
            alert_display_cols = ['SKU', 'DESCR', 'QTYAVAILABLE'] + [col for col in location_filter if col in low_stock.columns]
            st.dataframe(low_stock[alert_display_cols], use_container_width=True)
    
    with tab4:
        st.header("🗑️ Recycle Bin")
        deleted_items = df[df['Status'] == 'Deleted']
        if not deleted_items.empty:
            st.subheader("Deleted Items")
            st.dataframe(deleted_items, use_container_width=True)
            if st.button("🔁 Restore All"):
                df['Status'] = 'Active'
                st.session_state.df = df
                st.success("All items restored!")
                st.rerun()
            else:
                st.info("No deleted items in the recycle bin.")

    # Footer / Credits
                st.markdown("---")
                st.markdown(
                "<div style='text-align: center; color: #5F6A6A;'>"
                "Built with ❤️ Streamlit & Plotly | Warehouse Inventory Dashboard"
         "</div>",
            unsafe_allow_html=True
            )
                if 'QTY' in df.columns:
                    for idx, row in df.iterrows():
                        loc_cols_existing = [col for col in location_cols if col in df.columns]
                        df.at[idx, 'QTY'] = row.get('QTYAVAILABLE', 0)  # Or sum(row[loc_cols_existing])
                        st.session_state.df = df
                        buffer_all = io.BytesIO()
                with pd.ExcelWriter(buffer_all, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False)
                    buffer_all.seek(0)
                    st.download_button(
                    label="📥 Download Full Dataset",
                    data=buffer_all,
                     mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


