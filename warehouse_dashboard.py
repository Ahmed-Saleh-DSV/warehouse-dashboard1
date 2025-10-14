import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from io import BytesIO
import warnings
from datetime import datetime  # For timestamp in reports

# For PDF export with reportlab (supports basic Unicode; for full Arabic/Hebrew, add custom fonts)
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont  # For custom Unicode fonts if needed
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# Page configuration for responsive layout
st.set_page_config(
    page_title="Enhanced Warehouse Inventory Management",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional, responsive styling
st.markdown("""
<style>
    /* Main header styling */
    .main-header {
        font-size: 2.5rem;
        color: #2c3e50;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: bold;
    }
    
    /* Metric cards with colors */
    .metric-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .metric-container label {
        color: white !important;
        font-size: 0.9rem;
    }
    .metric-container div {
        color: white !important;
        font-size: 2rem;
        font-weight: bold;
    }
    
    /* Warning, Success, Error boxes */
    .warning-box {
        background-color: #fff3cd;
        border-left: 5px solid #ffc107;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .success-box {
        background-color: #d4edda;
        border-left: 5px solid #28a745;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #f8d7da;
        border-left: 5px solid #dc3545;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    /* Buttons */
    .stButton > button {
        border-radius: 10px;
        background: linear-gradient(135deg, #007bff 0%, #0056b3 100%);
        color: white;
        border: none;
        padding: 0.75rem 1.5rem;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 123, 255, 0.3);
    }
    
    /* Data editor styling */
    .stDataEditor {
        border-radius: 10px;
        border: 2px solid #dee2e6;
        overflow: hidden;
    }
    .stDataEditor .dataframe {
        border-radius: 10px;
    }
    
    /* Chart card styling */
    .chart-card {
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        padding: 1rem;
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        margin-bottom: 1rem;
    }
    
    /* Responsive adjustments */
    @media (max-width: 768px) {
        .main-header { font-size: 2rem; }
        .metric-container { padding: 1rem; }
    }
</style>
""", unsafe_allow_html=True)

# =====================================
# HELPER FUNCTIONS
# =====================================

def process_uploaded_df(uploaded_file):
    """
    Process the uploaded Excel file:
    - Read columns: SKU, DESCR, QTYHOLD, STDCUBE, QTYAVAILABLE, locations (21KCH2, etc.), DELETED, NA, YARD, QTY
    - Convert numerics, fill NaN with 0
    - Calculate QTY as sum of location columns if missing/NaN
    - Handle DELETED as status (1/True -> 'Deleted', else 'Active')
    - Drop rows with missing SKU
    - Detect duplicates and return warning
    - Error handling for missing required columns
    """
    try:
        full_inventory = pd.read_excel(uploaded_file)
        
        # Required columns check
        required_cols = ['SKU', 'DESCR', 'QTYHOLD', 'STDCUBE', 'QTYAVAILABLE']
        missing = [col for col in required_cols if col not in full_inventory.columns]
        if missing:
            return None, f"Missing required columns: {', '.join(missing)}"
        
        # Define location columns (based on input spec, excluding DELETED)
        loc_cols = ['21KCH2', '21KCH5', '3K-M45', '6KMZ-2', 'NA', 'YARD']
        loc_cols = [col for col in loc_cols if col in full_inventory.columns]
        
        # Convert numeric columns (including DELETED as int for status)
        numeric_cols = ['QTYHOLD', 'STDCUBE', 'QTYAVAILABLE', 'QTY', 'DELETED'] + loc_cols
        for col in numeric_cols:
            if col in full_inventory.columns:
                full_inventory[col] = pd.to_numeric(full_inventory[col], errors='coerce').fillna(0)
        
        # Drop rows with missing SKU
        initial_rows = len(full_inventory)
        full_inventory = full_inventory.dropna(subset=['SKU']).reset_index(drop=True)
        if len(full_inventory) < initial_rows:
            st.warning(f"Dropped {initial_rows - len(full_inventory)} rows with missing SKUs.")
        
        # Calculate QTY as sum of locations if not present or NaN
        if 'QTY' not in full_inventory.columns:
            full_inventory['QTY'] = full_inventory[loc_cols].sum(axis=1).fillna(0)
        else:
            mask = full_inventory['QTY'].isna()
            full_inventory.loc[mask, 'QTY'] = full_inventory.loc[mask, loc_cols].sum(axis=1).fillna(0)
        
        # Ensure QTY is at least 0
        full_inventory['QTY'] = full_inventory['QTY'].clip(lower=0)
        
        # Handle DELETED column as status (ensure it's 0 or 1)
        if 'DELETED' not in full_inventory.columns:
            full_inventory['DELETED'] = 0
        full_inventory['DELETED'] = full_inventory['DELETED'].astype(int).clip(0, 1)
        full_inventory['Status'] = np.where(full_inventory['DELETED'] == 1, 'Deleted', 'Active')
        
        # Auto-mark QTY=0 as Deleted if Active
        mask_zero = (full_inventory['QTY'] == 0) & (full_inventory['Status'] == 'Active')
        if mask_zero.any():
            full_inventory.loc[mask_zero, 'Status'] = 'Deleted'
            full_inventory.loc[mask_zero, 'DELETED'] = 1
            st.info(f"Auto-marked {mask_zero.sum()} zero-quantity SKUs as Deleted.")
        
        # Check for duplicates
        dups = full_inventory['SKU'].duplicated().sum()
        duplicate_warning = f"Found {dups} duplicate SKUs. Please review." if dups > 0 else None
        
        return full_inventory, duplicate_warning, loc_cols
    
    except Exception as e:
        return None, f"Error processing file: {str(e)}", []

def process_edited_df(full_inventory, loc_cols):
    """
    Process edited DataFrame: Recalculate QTY, sync status, handle numerics.
    - Drop rows with empty/NaN SKU
    - Sync Status and DELETED, set Deleted if QTY=0
    - Warn on duplicates
    """
    # Convert numerics
    numeric_cols = ['QTYHOLD', 'STDCUBE', 'QTYAVAILABLE', 'QTY', 'DELETED'] + loc_cols
    for col in numeric_cols:
        if col in full_inventory.columns:
            full_inventory[col] = pd.to_numeric(full_inventory[col], errors='coerce').fillna(0)
    
    # Recalculate QTY as sum of locations
    full_inventory['QTY'] = full_inventory['QTY'].clip(lower=0)
    
    # Sync DELETED and Status
    if 'DELETED' not in full_inventory.columns:
        full_inventory['DELETED'] = 0
    full_inventory['DELETED'] = full_inventory['DELETED'].astype(int).clip(0, 1)
    full_inventory['Status'] = np.where(full_inventory['DELETED'] == 1, 'Deleted', 'Active')
    
    # Auto-mark zero QTY as Deleted if Active
    mask_zero = (full_inventory['QTY'] == 0) & (full_inventory['Status'] == 'Active')
    if mask_zero.any():
        full_inventory.loc[mask_zero, 'Status'] = 'Deleted'
        full_inventory.loc[mask_zero, 'DELETED'] = 1
    
    # Drop rows with empty/NaN SKU
    initial_rows = len(full_inventory)
    full_inventory = full_inventory.dropna(subset=['SKU']).reset_index(drop=True)
    full_inventory['SKU'] = full_inventory['SKU'].astype(str).str.strip()
    full_inventory = full_inventory[full_inventory['SKU'] != '']
    if len(full_inventory) < initial_rows:
        st.info(f"Removed {initial_rows - len(full_inventory)} rows with empty SKUs.")
    
    # Check for duplicates and warn
    dups = full_inventory['SKU'].duplicated().sum()
    duplicate_warning = f"Found {dups} duplicate SKUs. Please review." if dups > 0 else None
    
    return full_inventory, duplicate_warning, loc_cols

def process_edited_df(full_inventory, loc_cols):
    """
    Process edited DataFrame: Recalculate QTY, sync status, handle numerics.
    - Drop rows with empty/NaN SKU
    - Sync Status and DELETED, set Deleted if QTY=0
    - Warn on duplicates
    """
    # Convert numerics
    numeric_cols = ['QTYHOLD', 'STDCUBE', 'QTYAVAILABLE', 'QTY', 'DELETED'] + loc_cols
    for col in numeric_cols:
        if col in full_inventory.columns:
            full_inventory[col] = pd.to_numeric(full_inventory[col], errors='coerce').fillna(0)
    
    # Recalculate QTY as sum of locations
    full_inventory['QTY'] = full_inventory[loc_cols].sum(axis=1).fillna(0)
    full_inventory['QTY'] = full_inventory['QTY'].clip(lower=0)
    
    # Sync DELETED and Status
    if 'DELETED' not in full_inventory.columns:
        full_inventory['DELETED'] = 0
    full_inventory['DELETED'] = full_inventory['DELETED'].astype(int).clip(0, 1)
    full_inventory['Status'] = np.where(full_inventory['DELETED'] == 1, 'Deleted', 'Active')
    
    # Auto-mark zero QTY as Deleted if Active
    mask_zero = (full_inventory['QTY'] == 0) & (full_inventory['Status'] == 'Active')
    if mask_zero.any():
        full_inventory.loc[mask_zero, 'Status'] = 'Deleted'
        full_inventory.loc[mask_zero, 'DELETED'] = 1
    
    # Drop rows with empty/NaN SKU
    initial_rows = len(full_inventory)
    full_inventory = full_inventory.dropna(subset=['SKU']).reset_index(drop=True)
    full_inventory['SKU'] = full_inventory['SKU'].astype(str).str.strip()
    full_inventory = full_inventory[full_inventory['SKU'] != '']
    if len(full_inventory) < initial_rows:
        st.info(f"Removed {initial_rows - len(full_inventory)} rows with empty SKUs.")
    
    # Check for duplicates and warn
    dups = full_inventory['SKU'].duplicated().sum()
    if dups > 0:
        st.warning(f"Found {dups} duplicate SKUs. Please review.")
    
    return full_inventory

def validate_data(full_inventory, loc_cols, qty_available_col='QTYAVAILABLE'):
    """
    Validate:
    - Sum of locations <= QTYAVAILABLE
    - Return violations count and affected SKUs
    - Handle empty loc_cols edge case
    """
    if not loc_cols or full_inventory.empty:
        return 0, []
    sum_loc = full_inventory[loc_cols].sum(axis=1)
    violations = full_inventory[sum_loc > full_inventory[qty_available_col]]
    return len(violations), violations['SKU'].tolist()

def get_low_stock_df(full_inventory, threshold):
    """
    Get SKUs with QTY < threshold
    """
    return full_inventory[full_inventory['QTY'] < threshold]

@st.cache_data
def calculate_kpis(full_inventory, loc_cols):
    """
    Calculate KPIs (cached for performance):
    - Total SKUs: len(full_inventory)
    - Total Quantity: sum(QTY)
    - Active Locations: count of loc_cols with sum > 0
    - Deleted SKUs: count where Status == 'Deleted'
    - Handle empty loc_cols edge case
    """
    total_skus = len(full_inventory)
    total_qty = full_inventory['QTY'].sum()
    active_locs = sum(1 for col in loc_cols if full_inventory[col].sum() > 0) if loc_cols else 0
    deleted_skus = len(full_inventory[full_inventory['Status'] == 'Deleted'])
    return total_skus, total_qty, active_locs, deleted_skus

def create_location_heatmap(full_inventory, loc_cols, top_n_skus=20):
    """
    Create a heatmap for top N SKUs vs locations (quantities)
    - Handle empty loc_cols edge case
    """
    if not loc_cols or full_inventory.empty:
        return None
    # Sample top N by QTY for heatmap feasibility
    top_df = full_inventory.nlargest(top_n_skus, 'QTY')[['SKU'] + loc_cols].set_index('SKU')
    fig = px.imshow(
        top_df.values,
        x=loc_cols,
        y=top_df.index,
        labels=dict(x="Locations", y="Top SKUs", color="Quantity"),
        title=f"Heatmap: Quantity Distribution (Top {top_n_skus} SKUs)",
        color_continuous_scale='YlOrRd'
    )
    fig.update_layout(width=800, height=600)
    return fig

def render_charts(display_inventory, loc_cols, low_threshold, top_n=10):
    """
    Render all charts with low stock highlighting in card style.
    - Handle empty loc_cols edge case
    """
    if not loc_cols or display_inventory.empty:
        st.info("No location data available for charts.")
        return

    # Location summary
    loc_summary = pd.DataFrame({
        'Location': loc_cols,
        'Total_Qty': [display_inventory[col].sum() for col in loc_cols]
    }).query('Total_Qty > 0')

    if not loc_summary.empty:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown('<div class="chart-card"><h4>Total Qty per Location (Linear)</h4>', unsafe_allow_html=True)
            fig_bar = px.bar(loc_summary, x='Location', y='Total_Qty', title='')
            st.plotly_chart(fig_bar, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        with col2:
            st.markdown('<div class="chart-card"><h4>Total Qty per Location (Log)</h4>', unsafe_allow_html=True)
            fig_log = px.bar(loc_summary, x='Location', y='Total_Qty', title='', log_y=True)
            st.plotly_chart(fig_log, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        with col3:
            st.markdown('<div class="chart-card"><h4>Qty Distribution by Location</h4>', unsafe_allow_html=True)
            fig_pie = px.pie(loc_summary, values='Total_Qty', names='Location', title='')
            st.plotly_chart(fig_pie, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # Top N SKUs
    if not display_inventory.empty:
        top_df = display_inventory.nlargest(top_n, 'QTY')[['SKU', 'QTY', 'DESCR']]
        st.markdown('<div class="chart-card"><h4>Top {} SKUs by Quantity</h4>'.format(top_n), unsafe_allow_html=True)
        fig_top = px.bar(top_df, x='SKU', y='QTY', hover_data=['DESCR'], title='')
        low_in_top = top_df[top_df['QTY'] < low_threshold]
        if not low_in_top.empty:
            fig_top.add_hline(y=low_threshold, line_dash="dash", line_color="red", annotation_text="Low Stock Threshold")
        st.plotly_chart(fig_top, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Box plot with low stock highlight
    st.markdown('<div class="chart-card"><h4>Quantity Distribution per SKU</h4>', unsafe_allow_html=True)
    fig_box = px.box(display_inventory, y='QTY', title='')
    fig_box.add_hline(y=low_threshold, line_dash="dash", line_color="red", annotation_text="Low Stock Threshold")
    st.plotly_chart(fig_box, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Heatmap
    heatmap_fig = create_location_heatmap(display_inventory, loc_cols)
    if heatmap_fig:
        st.markdown('<div class="chart-card"><h4>Location Heatmap (Top SKUs)</h4>', unsafe_allow_html=True)
        st.plotly_chart(heatmap_fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

def apply_filters(full_inventory, status_filter, sku_search, desc_search, location_filter, loc_cols):
    """
    Apply all filters to the inventory DataFrame.
    - Handles NaN in SKU/DESCR explicitly.
    """
    display_inventory = full_inventory.copy()
    
    # Handle NaN in text columns
    display_inventory['SKU'] = display_inventory['SKU'].fillna('').astype(str)
    display_inventory['DESCR'] = display_inventory['DESCR'].fillna('').astype(str)
    
    if status_filter != 'All':
        display_inventory = display_inventory[display_inventory['Status'] == status_filter]
    if sku_search:
        display_inventory = display_inventory[display_inventory['SKU'].str.contains(sku_search, case=False, na=False)]
    if desc_search:
        display_inventory = display_inventory[display_inventory['DESCR'].str.contains(desc_search, case=False, na=False)]
    if location_filter != loc_cols and location_filter:
        loc_mask = display_inventory[location_filter].gt(0).any(axis=1)
        display_inventory = display_inventory[loc_mask]
    
    return display_inventory

def export_to_excel(full_inventory, filename="inventory_export.xlsx"):
    """
    Export DataFrame to Excel bytes
    """
    if full_inventory is None or full_inventory.empty:
        st.warning("❌ No data to export!")
        return None, None
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        full_inventory.to_excel(writer, index=False, sheet_name='Inventory')
    output.seek(0)
    return output.getvalue(), filename

def export_to_pdf(full_inventory, filename="inventory_export.pdf", is_low_stock_report=False):
    """
    Export DataFrame to PDF with reportlab. Basic Unicode support.
    """
    if full_inventory is None or full_inventory.empty:
        st.warning("❌ No data to export!")
        return None, None
    
    if not PDF_AVAILABLE:
        st.warning("PDF export requires reportlab: pip install reportlab")
        return None, None
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle', 
        parent=styles['Heading1'], 
        fontSize=18, 
        spaceAfter=30, 
        alignment=1
    )
    title = Paragraph("Warehouse Inventory Report" if not is_low_stock_report else "Low Stock Report", title_style)
    story = [title, Spacer(1, 12)]
    
    if is_low_stock_report:
        # Add low stock summary
        summary_para = Paragraph(f"Low Stock SKUs (QTY < threshold): {len(full_inventory)} items", styles['Normal'])
        story.append(summary_para)
        story.append(Spacer(1, 12))
    
    # Table data (handle mixed dtypes by converting to str for display)
    data = [list(full_inventory.columns)] + full_inventory.astype(str).values.tolist()
    num_cols = len(full_inventory.columns)
    col_widths = [6*inch / num_cols for _ in range(num_cols)]
    table = Table(data, colWidths=col_widths, rowHeights=20)
    
    # Table style
    style_list = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
    ]
    if is_low_stock_report:
        style_list.append(('BACKGROUND', (0, 1), (-1, -1), colors.lightcoral))
    
    table.setStyle(TableStyle(style_list))
    
    story.append(table)
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue(), filename

def generate_daily_report(low_stock_df, threshold, export_type='excel'):
    """
    Generate daily low stock report as Excel or PDF
    """
    timestamp = datetime.now().strftime('%Y%m%d')
    if export_type == 'excel':
        data, fname = export_to_excel(low_stock_df, f"low_stock_report_{timestamp}.xlsx")
        return data, fname, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        data, fname = export_to_pdf(low_stock_df, f"low_stock_report_{timestamp}.pdf", is_low_stock_report=True)
        return data, fname, "application/pdf"

# =====================================
# MAIN APPLICATION
# =====================================

def main():
    st.markdown('<h1 class="main-header">📦 Enhanced Warehouse Inventory Management</h1>', unsafe_allow_html=True)
    
    # Tooltips/Help
    with st.expander("📋 Column Guide"):
        st.markdown("""
        - **SKU**: Unique product identifier (required, text)
        - **DESCR**: Product description (text)
        - **QTYHOLD**: Quantity on hold (numeric)
        - **STDCUBE**: Standard cube/volume (numeric)
        - **QTYAVAILABLE**: Available quantity (numeric)
        - **Location Columns** (e.g., 21KCH2, 21KCH5, etc.): Quantities at specific locations (numeric)
        - **DELETED**: Status flag (1=Deleted, 0=Active; auto-synced with Status)
        - **QTY**: Total quantity (auto-calculated as sum of locations)
        """)

    # Initialize session state
    if 'full_inventory' not in st.session_state:
        st.session_state.full_inventory = pd.DataFrame()
    if 'loc_cols' not in st.session_state:
        st.session_state.loc_cols = []
    if 'duplicate_warning' not in st.session_state:
        st.session_state.duplicate_warning = None
    if 'display_inventory' not in st.session_state:
        st.session_state.display_inventory = pd.DataFrame()
    if 'status_filter' not in st.session_state:
        st.session_state.status_filter = 'All'
    if 'sku_search' not in st.session_state:
        st.session_state.sku_search = ''
    if 'desc_search' not in st.session_state:
        st.session_state.desc_search = ''
    if 'location_filter' not in st.session_state:
        st.session_state.location_filter = []
    if 'low_threshold' not in st.session_state:
        st.session_state.low_threshold = 10
    if 'top_n' not in st.session_state:
        st.session_state.top_n = 10
    if 'change_log' not in st.session_state:
        st.session_state.change_log = pd.DataFrame(columns=['timestamp', 'action', 'SKU', 'description'])
    if 'deleted_skus' not in st.session_state:
        st.session_state.deleted_skus = pd.DataFrame()

    # 1. File Upload - Clear on new upload
    uploaded_file = st.file_uploader(
        "Upload Inventory Excel (.xlsx)",
        type=['xlsx', 'xls'],
        help="Upload file with columns: SKU, DESCR, QTYHOLD, STDCUBE, QTYAVAILABLE, locations (21KCH2 etc.), DELETED, QTY"
    )
    
    if uploaded_file is not None:
        with st.spinner("Processing file..."):
            new_inventory, dup_warn, locs = process_uploaded_df(uploaded_file)
            if new_inventory is not None:
                st.session_state.full_inventory = new_inventory
                st.session_state.loc_cols = locs
                st.session_state.duplicate_warning = dup_warn
                # Clear deleted and log on new upload
                st.session_state.deleted_skus = pd.DataFrame()
                log_entry = pd.DataFrame({
                    'timestamp': [datetime.now()],
                    'action': ['Upload'],
                    'SKU': ['N/A'],
                    'description': [f"Uploaded {len(new_inventory)} SKUs"]
                })
                st.session_state.change_log = pd.concat([st.session_state.change_log, log_entry], ignore_index=True)
                st.session_state.display_inventory = apply_filters(new_inventory, st.session_state.status_filter, st.session_state.sku_search, st.session_state.desc_search, st.session_state.location_filter, locs)
                st.success("✅ File uploaded and processed!")
                st.rerun()
            else:
                st.error(dup_warn or "Failed to process file.")
                st.stop()

    if st.session_state.full_inventory.empty:
        st.info("👆 Please upload an Excel file to start.")
        st.stop()

    full_inventory = st.session_state.full_inventory.copy()
    loc_cols = st.session_state.loc_cols

    # Sidebar: Filters & Settings
    st.sidebar.header("🔍 Filters & Settings")
    status_filter = st.sidebar.selectbox("Status", ['All', 'Active', 'Deleted'], index=['All', 'Active', 'Deleted'].index(st.session_state.status_filter))
    st.session_state.status_filter = status_filter
    sku_search = st.sidebar.text_input("SKU Search", value=st.session_state.sku_search)
    st.session_state.sku_search = sku_search
    desc_search = st.sidebar.text_input("Description Search", value=st.session_state.desc_search)
    st.session_state.desc_search = desc_search
    location_filter = st.sidebar.multiselect("Filter by Locations (qty>0)", loc_cols, default=st.session_state.location_filter)
    st.session_state.location_filter = location_filter
    low_threshold = st.sidebar.number_input("Low Stock Threshold", min_value=0, value=st.session_state.low_threshold)
    st.session_state.low_threshold = low_threshold
    top_n = st.sidebar.number_input("Top N SKUs for charts", min_value=5, max_value=50, value=st.session_state.top_n)
    st.session_state.top_n = top_n
    if st.sidebar.button("Reset Filters"):
        st.session_state.status_filter = 'All'
        st.session_state.sku_search = ''
        st.session_state.desc_search = ''
        st.session_state.location_filter = loc_cols
        st.session_state.low_threshold = 10
        st.session_state.top_n = 10

    # Apply filters to update display_inventory
    display_inventory = apply_filters(full_inventory, st.session_state.status_filter, st.session_state.sku_search, st.session_state.desc_search, st.session_state.location_filter, loc_cols)
    st.session_state.display_inventory = display_inventory

    # Duplicate warning display (clear after showing)
    if st.session_state.duplicate_warning:
        st.warning(st.session_state.duplicate_warning)
        st.session_state.duplicate_warning = None

    # Header & KPI Cards Section (after upload check)
    if not st.session_state.full_inventory.empty:
        # Calculate KPIs dynamically using display_inventory
        total_skus, total_qty, active_locs, deleted_skus = calculate_kpis(st.session_state.display_inventory, loc_cols)
        
        # KPI Cards in responsive columns
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown("""
            <div class="metric-container">
                <label>Total SKUs</label>
                <div>{}</div>
            </div>
            """.format(total_skus), unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class="metric-container">
                <label>Total Quantity</label>
                <div>{:,.0f}</div>
            </div>
            """.format(total_qty), unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
            <div class="metric-container">
                <label>Active Locations</label>
                <div>{}</div>
            </div>
            """.format(active_locs), unsafe_allow_html=True)
        
        with col4:
            st.markdown("""
            <div class="metric-container">
                <label>Deleted SKUs</label>
                <div>{}</div>
            </div>
            """.format(deleted_skus), unsafe_allow_html=True)
    else:
        st.info("Upload data to view KPIs.")

    # Data Table Section - Dynamic Editor for Add/Edit/Delete
    st.subheader("📊 Inventory Management (Add/Edit/Delete SKUs)")

    if not st.session_state.full_inventory.empty:
        # Use full_inventory for editing (dynamic rows for add/delete)
        edit_inventory = st.session_state.full_inventory.copy()
        loc_cols = st.session_state.loc_cols
        
        # Debug info after upload (toggle via expander for production)
        with st.expander("🔍 Debug: Columns & Sample Data (Post-Upload)"):
            st.write("**Columns:**", list(edit_inventory.columns))
            st.write("**First 10 Rows:**")
            st.dataframe(edit_inventory.head(10), use_container_width=True)
        
        # Data Editor: Dynamic rows (allow add/delete), all columns editable except auto-calculated
        edited_inventory = st.data_editor(
            edit_inventory,
            num_rows="dynamic",  # Allows adding/deleting rows
            use_container_width=True,
            column_config={
                "SKU": st.column_config.TextColumn("SKU", help="Unique ID (editable)"),
                "DESCR": st.column_config.TextColumn("Description", help="Product description"),
                "Status": st.column_config.SelectboxColumn(
                    "Status", options=["Active", "Deleted"], 
                    help="Status (auto-syncs with DELETED and QTY=0)"
                ),
                "QTY": st.column_config.NumberColumn(
                    "Total Quantity", format="%.0f", 
                    help="Auto-calculated as sum of locations",
                    disabled=True  # Read-only, auto-updates
                ),
                **{col: st.column_config.NumberColumn(
                    col, format="%.0f", 
                    help=f"Quantity at {col} (edits auto-update QTY)"
                ) for col in loc_cols + ['QTYHOLD', 'STDCUBE', 'QTYAVAILABLE']},
                "DELETED": st.column_config.NumberColumn("DELETED Flag", help="Auto-synced with Status (1=Deleted)", disabled=True)
            },
            key="inventory_editor_dynamic"
        )
        
        # Process edits: Detect adds, edits, deletes; update deleted_skus; log changes; recalculate
        if not edit_inventory.equals(edited_inventory):
            # Get previous SKUs for comparison
            previous_skus = set(edit_inventory['SKU'].dropna().unique())
            current_skus = set(edited_inventory['SKU'].dropna().unique())
            
            # Detect deleted SKUs (in previous but not current)
            deleted_skus_set = previous_skus - current_skus
            if deleted_skus_set:
                # Extract deleted rows from previous inventory
                deleted_rows_data = edit_inventory[edit_inventory['SKU'].isin(deleted_skus_set)].copy()
                deleted_rows_data['deleted_timestamp'] = datetime.now()
                if 'deleted_skus' not in st.session_state:
                    st.session_state.deleted_skus = pd.DataFrame()
                # Append to deleted_skus
                st.session_state.deleted_skus = pd.concat([st.session_state.deleted_skus, deleted_rows_data], ignore_index=True)
                # Log deletion
                for sku in deleted_skus_set:
                    log_entry = pd.DataFrame({
                        'timestamp': [datetime.now()],
                        'action': ['Delete'],
                        'SKU': [sku],
                        'description': [f"SKU {sku} deleted"]
                    })
                    st.session_state.change_log = pd.concat([st.session_state.change_log, log_entry], ignore_index=True)
                st.info(f"📝 {len(deleted_skus_set)} SKUs moved to Deleted SKUs section. You can restore them below.")
            
            # Detect added SKUs (in current but not previous)
            added_skus_set = current_skus - previous_skus
            if added_skus_set:
                for sku in added_skus_set:
                    log_entry = pd.DataFrame({
                        'timestamp': [datetime.now()],
                        'action': ['Add'],
                        'SKU': [sku],
                        'description': [f"New SKU {sku} added"]
                    })
                    st.session_state.change_log = pd.concat([st.session_state.change_log, log_entry], ignore_index=True)
                st.success(f"➕ {len(added_skus_set)} new SKUs added.")
            
            # Detect edits (simple: any change in non-SKU columns)
            edited_mask = ~edited_inventory.equals(edit_inventory)
            if edited_mask.any().any():
                edited_skus = edited_inventory[edited_mask.any(axis=1)]['SKU'].dropna().unique()
                for sku in edited_skus:
                    log_entry = pd.DataFrame({
                        'timestamp': [datetime.now()],
                        'action': ['Edit'],
                        'SKU': [sku],
                        'description': [f"SKU {sku} edited"]
                    })
                    st.session_state.change_log = pd.concat([st.session_state.change_log, log_entry], ignore_index=True)
                st.info(f"✏️ {len(edited_skus)} SKUs edited.")
            
            # Update full_inventory with edited data and process (recalculates QTY, syncs Status/DELETED, removes empty SKUs)
            processed_inventory = process_edited_df(edited_inventory, loc_cols)
            st.session_state.full_inventory = processed_inventory
            
            # Re-apply filters to update display_inventory
            st.session_state.display_inventory = apply_filters(processed_inventory, st.session_state.status_filter, st.session_state.sku_search, st.session_state.desc_search, st.session_state.location_filter, loc_cols)
            
            st.rerun()  # Dynamic update: Propagates to all sections

    # Version Tracking / Change Log Section
    st.subheader("📝 Change Log (Version Tracking)")
    if 'change_log' in st.session_state and not st.session_state.change_log.empty:
        # Display recent changes (last 20 for lightweight)
        recent_changes = st.session_state.change_log.tail(20).copy()
        recent_changes['timestamp'] = recent_changes['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
        st.dataframe(recent_changes, use_container_width=True)
        if len(st.session_state.change_log) > 20:
            st.info(f"... and {len(st.session_state.change_log) - 20} more changes.")
    else:
        st.info("No changes yet. Upload or edit inventory to start tracking.")

    # Deleted SKUs Section
    st.subheader("🗑️ Deleted SKUs (Restore or Permanent Delete)")
    if 'deleted_skus' in st.session_state and not st.session_state.deleted_skus.empty:
        deleted_df = st.session_state.deleted_skus.copy()
        deleted_df = deleted_df.drop(columns=['deleted_timestamp'], errors='ignore')  # Hide timestamp for display
        
        # Show deleted table with options to restore or permanent delete
        col_restore, col_delete = st.columns(2)
        
        with col_restore:
            st.markdown("**Restore SKUs:** Select rows to restore back to inventory.")
            selected_to_restore = st.multiselect(
                "Select SKUs to restore",
                options=deleted_df['SKU'].tolist(),
                default=[],
                help="Restored SKUs will be added back; duplicates will be merged by summing quantities."
            )
        
        with col_delete:
            st.markdown("**Permanent Delete:** Select rows to remove forever.")
            selected_to_delete = st.multiselect(
                "Select SKUs to permanent delete",
                options=deleted_df['SKU'].tolist(),
                default=[],
                help="These will be removed from deleted list and cannot be recovered."
            )
        
        # Restore action
        if st.button("Restore Selected SKUs") and selected_to_restore:
            restore_rows = deleted_df[deleted_df['SKU'].isin(selected_to_restore)]
            # Check for conflicts (existing SKUs)
            conflicting_skus = set(restore_rows['SKU']) & set(st.session_state.full_inventory['SKU'])
            if conflicting_skus:
                st.warning(f"⚠️ Conflicts with existing SKUs: {list(conflicting_skus)}. Quantities will be summed.")
                # Merge: sum quantities for locations, QTY, etc.
                for sku in conflicting_skus:
                    existing_mask = st.session_state.full_inventory['SKU'] == sku
                    existing_row = st.session_state.full_inventory[existing_mask].iloc[0]
                    restore_row = restore_rows[restore_rows['SKU'] == sku].iloc[0]
                    # Sum numeric columns
                    numeric_cols_to_merge = ['QTY', 'QTYHOLD', 'STDCUBE', 'QTYAVAILABLE'] + st.session_state.loc_cols
                    for col in numeric_cols_to_merge:
                        if col in existing_row and col in restore_row:
                            st.session_state.full_inventory.loc[existing_mask, col] += restore_row[col]
                    # Update Status/DELETED if needed
                    if restore_row['DELETED'] == 1:
                        st.session_state.full_inventory.loc[existing_mask, 'DELETED'] = 1
                        st.session_state.full_inventory.loc[existing_mask, 'Status'] = 'Deleted'
            
            # Remove restored from deleted_skus and add non-conflicting to inventory
            non_conflicting_restore = restore_rows[~restore_rows['SKU'].isin(conflicting_skus)]
            st.session_state.full_inventory = pd.concat([st.session_state.full_inventory, non_conflicting_restore], ignore_index=True)
            st.session_state.deleted_skus = st.session_state.deleted_skus[~st.session_state.deleted_skus['SKU'].isin(selected_to_restore)]
            # Re-process full_inventory
            st.session_state.full_inventory = process_edited_df(st.session_state.full_inventory, st.session_state.loc_cols)
            # Log restore
            for sku in selected_to_restore:
                log_entry = pd.DataFrame({
                    'timestamp': [datetime.now()],
                    'action': ['Restore'],
                    'SKU': [sku],
                    'description': [f"SKU {sku} restored"]
                })
                st.session_state.change_log = pd.concat([st.session_state.change_log, log_entry], ignore_index=True)
            # Update display_inventory
            st.session_state.display_inventory = apply_filters(st.session_state.full_inventory, st.session_state.status_filter, st.session_state.sku_search, st.session_state.desc_search, st.session_state.location_filter, st.session_state.loc_cols)
            st.success(f"✅ Restored {len(selected_to_restore)} SKUs.")
            st.rerun()
        
        # Permanent delete action
        if st.button("Permanent Delete Selected SKUs") and selected_to_delete:
            num_deleted = len(selected_to_delete)
            st.session_state.deleted_skus = st.session_state.deleted_skus[~st.session_state.deleted_skus['SKU'].isin(selected_to_delete)]
            # Log permanent delete
            for sku in selected_to_delete:
                log_entry = pd.DataFrame({
                    'timestamp': [datetime.now()],
                    'action': ['Permanent Delete'],
                    'SKU': [sku],
                    'description': [f"SKU {sku} permanently deleted"]
                })
                st.session_state.change_log = pd.concat([st.session_state.change_log, log_entry], ignore_index=True)
            st.warning(f"🗑️ Permanently deleted {num_deleted} SKUs.")
            st.rerun()
        
        # Display deleted table
        if not deleted_df.empty:
            styled_deleted = deleted_df.style.apply(
                lambda row: ['background-color: lightgray' for _ in row], axis=1
            )
            st.dataframe(styled_deleted, use_container_width=True, hide_index=True)
        else:
            st.info("No deleted SKUs.")
    else:
        st.info("No deleted SKUs. Deletions from the editor will appear here.")

    # Clear deleted SKUs button (edge case: clear all)
    if st.button("Clear All Deleted SKUs (Permanent)"):
        if 'deleted_skus' in st.session_state:
            num_cleared = len(st.session_state.deleted_skus)
            st.session_state.deleted_skus = pd.DataFrame()
            # Log clear
            log_entry = pd.DataFrame({
                'timestamp': [datetime.now()],
                'action': ['Clear Deleted'],
                'SKU': ['N/A'],
                'description': [f"Cleared {num_cleared} deleted SKUs"]
            })
            st.session_state.change_log = pd.concat([st.session_state.change_log, log_entry], ignore_index=True)
        st.warning("🗑️ All deleted SKUs permanently removed.")
        st.rerun()

    # Post-processing for highlighting (display filtered view with colors)
    # Zero QTY rows in red, Deleted in gray (via styled dataframe)
    if not st.session_state.display_inventory.empty:
        styled_display = st.session_state.display_inventory.style.apply(
            lambda row: ['background-color: lightcoral' if row['QTY'] == 0 else 
                         'background-color: lightgray' if row['Status'] == 'Deleted' else '' 
                         for _ in row], axis=1
        )
        st.subheader("📊 Filtered Inventory View")
        st.dataframe(styled_display, use_container_width=True, hide_index=True)

    # Alerts Section
    st.subheader("🚨 Alerts & Alarms")

    if not st.session_state.full_inventory.empty:
        display_inventory = st.session_state.display_inventory
        low_threshold = st.session_state.low_threshold
        low_stock_df = get_low_stock_df(display_inventory, low_threshold)
        
        st.markdown("""
        <div style="border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); padding: 1.5rem; background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%); border-left: 5px solid #ffc107;">
            <h4 style="color: #856404; margin-bottom: 1rem;">Low Stock Alerts</h4>
        </div>
        """, unsafe_allow_html=True)
        
        if not low_stock_df.empty:
            critical = low_stock_df[low_stock_df['QTY'] == 0]
            warnings = low_stock_df[low_stock_df['QTY'] > 0]
            
            if not critical.empty:
                st.error(f"🔴 Critical: {len(critical)} SKUs with QTY=0")
                st.dataframe(critical[['SKU', 'DESCR', 'QTY']], use_container_width=True)
            
            if not warnings.empty:
                st.warning(f"🟡 Warnings: {len(warnings)} SKUs below threshold ({low_threshold})")
                st.dataframe(warnings[['SKU', 'DESCR', 'QTY']], use_container_width=True)
        else:
            st.success("✅ No low stock alerts.")
        
        # Validation alerts (from validate_data)
        violations, viol_skus = validate_data(display_inventory, loc_cols)
        if violations > 0:
            st.error(f"⚠️ {violations} SKUs exceed QTYAVAILABLE: {viol_skus[:5]}...")
    else:
        st.info("Upload data to view alerts.")

    # Data Visualizations Section
    st.subheader("📈 Data Visualizations")

    if not st.session_state.full_inventory.empty:
        display_inventory = st.session_state.display_inventory
        loc_cols = st.session_state.loc_cols
        low_threshold = st.session_state.low_threshold
        top_n = st.session_state.top_n
        
        render_charts(display_inventory, loc_cols, low_threshold, top_n)
    else:
        st.info("Upload data to view charts.")
    
    # Export Options Section
    st.subheader("💾 Export Options")

    if not st.session_state.full_inventory.empty:
        export_inventory = st.session_state.display_inventory
        low_stock_export = get_low_stock_df(export_inventory, st.session_state.low_threshold)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            with st.spinner("Preparing Excel export..."):
                excel_data, excel_fname = export_to_excel(export_inventory)
            if excel_data:
                st.download_button(
                    label="📊 Export Inventory (Excel)",
                    data=excel_data,
                    file_name=excel_fname,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
        
        with col2:
            with st.spinner("Preparing PDF export..."):
              if PDF_AVAILABLE:
                  pdf_data, pdf_fname = export_to_pdf(export_inventory)
                  if pdf_data:
                      st.download_button(
                      label="📄 Export Inventory (PDF)",
                      data=pdf_data,
                      file_name=pdf_fname,
                      mime="application/pdf",
                      use_container_width=True
                      )
                else:
                    st.info("PDF export requires reportlab: pip install reportlab")
        
        with col3:
            with st.spinner("Preparing Low Stock Excel..."):
                low_stock_excel_data, low_stock_excel_fname = export_to_excel(low_stock_export)
              if low_stock_excel_data:
                  st.download_button(
                     label="📊 Low Stock Report (Excel)",
                     data=low_stock_excel_data,
                     file_name=low_stock_excel_fname,
                     mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                     use_container_width=True)
        
        with col4:
            with st.spinner("Preparing Low Stock PDF..."):
                if PDF_AVAILABLE:
                    low_stock_pdf_data, low_stock_pdf_fname = export_to_pdf(low_stock_export, is_low_stock_report=True)
                    if low_stock_pdf_data:
                        st.download_button(
                            label="📄 Low Stock Report (PDF)",
                            data=low_stock_pdf_data,
                            file_name=low_stock_pdf_fname,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                else:
                    st.info("PDF export requires reportlab: pip install reportlab")

if __name__ == "__main__":
    main()






