import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
import numpy as np

# ---------------------------
# Functions
# ---------------------------

def load_excel(file):
    df = pd.read_excel(file)
    return df

def download_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    processed_data = output.getvalue()
    return processed_data

def moving_average(series, window=3):
    return series.rolling(window, min_periods=1).mean()

def forecast(series, periods=5):
    # Simple forecast using last value
    last_value = series.iloc[-1]
    return pd.Series([last_value]*periods)

def dynamic_color(val, low, high):
    if val < low:
        return 'background-color: red; color: white'
    elif val < high:
        return 'background-color: yellow; color: black'
    else:
        return 'background-color: green; color: white'

def show_notification(message, level='info'):
    if level == 'info':
        st.info(message)
    elif level == 'warning':
        st.warning(message)
    elif level == 'error':
        st.error(message)
    elif level == 'success':
        st.success(message)

# ---------------------------
# App
# ---------------------------

st.set_page_config(page_title="Inventory Dashboard", layout="wide")
st.title("Inventory Management Dashboard 🚀")

# ---------------------------
# Excel Upload
# ---------------------------
uploaded_file = st.file_uploader("Drag & Drop or Select Excel file", type=['xlsx'])
if uploaded_file:
    df = load_excel(uploaded_file)
else:
    # Default demo data
    df = pd.DataFrame({
        "SKU": ["A101","A102","A103","B201","B202"],
        "Description": ["Item A","Item B","Item C","Item D","Item E"],
        "Location": ["WH1","WH2","WH1","WH2","WH3"],
        "Quantity": [50, 20, 0, 70, 15]
    })

# ---------------------------
# Filters
# ---------------------------
st.subheader("Filters 🔍")
sku_filter = st.text_input("Filter by SKU")
desc_filter = st.text_input("Filter by Description")
loc_filter = st.text_input("Filter by Location")

filtered_df = df.copy()
if sku_filter:
    filtered_df = filtered_df[filtered_df['SKU'].str.contains(sku_filter, case=False)]
if desc_filter:
    filtered_df = filtered_df[filtered_df['Description'].str.contains(desc_filter, case=False)]
if loc_filter:
    filtered_df = filtered_df[filtered_df['Location'].str.contains(loc_filter, case=False)]

# ---------------------------
# Editable Table
# ---------------------------
st.subheader("Inventory Table ✏️")
edited_df = st.data_editor(
    filtered_df,
    num_rows="dynamic",
    use_container_width=True
)

# ---------------------------
# Dynamic Color Coding
# ---------------------------
st.subheader("Dynamic Stock Levels 🎨")
styled_df = edited_df.style.applymap(
    lambda x: dynamic_color(x, low=20, high=50) if isinstance(x, (int,float)) else ""
)
st.dataframe(styled_df, use_container_width=True)

# ---------------------------
# Notifications
# ---------------------------
for idx, row in edited_df.iterrows():
    if row['Quantity'] < 10:
        show_notification(f"SKU {row['SKU']} is critically low!", level='error')
    elif row['Quantity'] < 30:
        show_notification(f"SKU {row['SKU']} stock is low.", level='warning')

# ---------------------------
# Analytics & Forecast
# ---------------------------
st.subheader("Analytics & Forecast 📈")

numeric_cols = edited_df.select_dtypes(include=np.number).columns
for col in numeric_cols:
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=edited_df['SKU'], y=edited_df[col],
        name='Actual', marker_color='blue'
    ))
    ma = moving_average(edited_df[col])
    fig.add_trace(go.Scatter(
        x=edited_df['SKU'], y=ma, mode='lines+markers',
        name='Moving Average', marker_color='orange'
    ))
    fc = forecast(edited_df[col])
    fig.add_trace(go.Scatter(
        x=edited_df['SKU'], y=fc, mode='lines+markers',
        name='Forecast', marker_color='green'
    ))
    fig.update_layout(title=f"{col} Analysis", xaxis_title="SKU", yaxis_title=col)
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------
# Download Updated Excel
# ---------------------------
st.subheader("Download Updated Data 💾")
if st.button("Download Excel"):
    to_download = download_excel(edited_df)
    st.download_button(label="Download Excel File", data=to_download, file_name="updated_inventory.xlsx")
