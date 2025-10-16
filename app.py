Okay, this is an ambitious request for a full, copy-pastable code, as it involves a multi-file structure and several advanced features. I will provide a comprehensive, single-file `app.py` (and a `styles.css`) that integrates:

1.  **Streamlit Framework**
2.  **Multi-User Authentication** (`streamlit-authenticator` with SQLite)
3.  **Persistent Storage** (SQLite via SQLAlchemy for Users, Inventory, Logs, Transactions)
4.  **Dashboard Overview** (KPIs, Low Stock Alerts, Interactive Charts)
5.  **Inventory Management** (CRUD, Search/Filter, Excel Upload/Export)
6.  **Activity Logs** (User actions)
7.  **Basic Analytics** (Inflow/Outflow, Stock Trend - *simplified forecasting*)
8.  **Responsive & Professional Styling** (Custom CSS)
9.  **Error Handling & UX** (`st.spinner`, `st.error`, `st.success`)

**Important Considerations for Replit:**

*   **Database:** SQLite is file-based (`inventory_dashboard.db`). Replit's default behavior saves this file, so data will persist across sessions/restarts.
*   **Performance:** For very large datasets (thousands of SKUs, millions of transactions), SQLite might become slow. For production, consider PostgreSQL/MySQL.
*   **Forecasting:** A full-blown ML forecasting model (like ARIMA, Prophet) is complex and beyond a simple, copy-pastable example due to model training, serialization, and dependencies. I'll implement a *basic trend visualization* based on historical transaction data as a placeholder for where a more advanced model would integrate.
*   **Email/SMS Alerts:** Requires external services (e.g., SendGrid, Twilio) and background tasks, which are out of scope for this self-contained example.
*   **Admin User:** The code will automatically create an `admin` user if the database is empty.

---

### **Step 1: Create `requirements.txt`**

Create a file named `requirements.txt` in your Replit project and paste the following:

```
streamlit
pandas
plotly
sqlalchemy
bcrypt
streamlit-authenticator
openpyxl
```

---

### **Step 2: Create `styles.css`**

Create a file named `styles.css` in your Replit project and paste the following:

```css
/* General Body and Font Styling */
body {
    font-family: 'Inter', sans-serif;
    color: #333;
    background-color: #f0f2f6; /* Light gray background */
}

/* Streamlit Header Overrides */
h1 {
    color: #2c3e50; /* Dark blue-gray */
    font-weight: 700;
    margin-bottom: 20px;
}

h2 {
    color: #34495e;
    font-weight: 600;
    margin-top: 30px;
    margin-bottom: 15px;
    border-bottom: 1px solid #eee;
    padding-bottom: 5px;
}

h3 {
    color: #555;
    font-weight: 500;
    margin-top: 20px;
    margin-bottom: 10px;
}

/* Custom KPI Card Styling */
.kpi-card {
    background: linear-gradient(135deg, #ffffff, #f9f9f9); /* Subtle gradient */
    border-radius: 12px;
    padding: 20px 25px;
    margin-bottom: 20px;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08); /* Soft shadow */
    border: 1px solid #e0e0e0;
    transition: transform 0.2s ease-in-out;
}

.kpi-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.12);
}

.kpi-card .stMetric {
    padding: 0;
}

.kpi-card .stMetric label {
    font-size: 1.1em;
    color: #666;
    margin-bottom: 5px;
    display: block;
}

.kpi-card .stMetric div[data-testid="stMetricValue"] {
    font-size: 2.2em;
    font-weight: 700;
    color: #2980b9; /* A professional blue */
}

/* Streamlit specific elements */
.stTabs [data-testid="stTabItem"] {
    font-size: 1.1em;
    font-weight: 500;
    color: #555;
}

.stTabs [data-testid="stTabItem"][aria-selected="true"] {
    color: #2980b9;
    border-bottom: 3px solid #2980b9;
}

/* Sidebar styling */
[data-testid="stSidebar"] {
    background-color: #ffffff;
    box-shadow: 2px 0 10px rgba(0,0,0,0.05);
}

[data-testid="stSidebar"] .stButton button {
    background-color: #e74c3c; /* Red for logout */
    color: white;
    border-radius: 8px;
    border: none;
    padding: 8px 15px;
    font-weight: 500;
}

[data-testid="stSidebar"] .stButton button:hover {
    background-color: #c0392b;
}

/* General Button Styling */
.stButton button {
    background-color: #3498db; /* Blue for primary actions */
    color: white;
    border-radius: 8px;
    border: none;
    padding: 10px 20px;
    font-weight: 600;
    transition: background-color 0.2s ease-in-out;
}

.stButton button:hover {
    background-color: #2980b9;
}

/* Specific buttons for clarity */
.stButton button[title="Add Item"],
.stButton button[title="Update Item"],
.stButton button[title="Delete Item"] {
    background-color: #2ecc71; /* Green for Add/Update */
}

.stButton button[title="Add Item"]:hover,
.stButton button[title="Update Item"]:hover {
    background-color: #27ae60;
}

.stButton button[title="Delete Item"] {
    background-color: #e74c3c; /* Red for Delete */
}

.stButton button[title="Delete Item"]:hover {
    background-color: #c0392b;
}

/* Expander Styling */
.stExpander {
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    background-color: #ffffff;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
    margin-bottom: 15px;
}

.stExpander div[data-testid="stExpanderHeader"] {
    padding: 15px 20px;
    font-weight: 600;
    color: #34495e;
    background-color: #fdfdfd;
    border-bottom: 1px solid #eee;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}

/* Dataframe styling - limited by Streamlit, but can influence container */
[data-testid="stDataFrame"] {
    border-radius: 8px;
    overflow: hidden; /* Ensures border radius applies to corners */
}

/* File uploader styling */
.stFileUploader {
    border: 2px dashed #bdc3c7;
    border-radius: 10px;
    padding: 20px;
    text-align: center;
    background-color: #ecf0f1;
    transition: background-color 0.2s ease-in-out, border-color 0.2s ease-in-out;
}

.stFileUploader:hover {
    background-color: #e0e5e7;
    border-color: #95a5a6;
}

/* Custom classes for low stock items */
.low-stock-row {
    background-color: #ffe0e0 !important; /* Light red */
}
.low-stock-text {
    color: #e74c3c;
    font-weight: bold;
}

/* General containers */
.stContainer {
    padding: 0 !important;
}

/* Remove default Streamlit padding from main content area */
.main .block-container {
    padding-top: 2rem;
    padding-right: 2rem;
    padding-left: 2rem;
    padding-bottom: 2rem;
}

/* Custom styles for the analytics charts */
.chart-container {
    background: #ffffff;
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
    margin-bottom: 20px;
}
```

---

### **Step 3: Create `app.py`**

Create a file named `app.py` in your Replit project and paste the following:

```python
import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.exc import IntegrityError
import datetime
import io
import bcrypt
import streamlit_authenticator as stauth
from pathlib import Path

# --- Configuration ---
DATABASE_URL = "sqlite:///inventory_dashboard.db"
LOW_STOCK_THRESHOLD = 10
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin" # Change this in a real application!
DEFAULT_LOCATIONS = ["Warehouse A", "Warehouse B", "Shelf 1", "Shelf 2"]

# --- Page Config ---
st.set_page_config(
    page_title="Warehouse Inventory Dashboard",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Load Custom CSS ---
try:
    with open("styles.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    st.warning("`styles.css` not found. Dashboard styling might be basic. Please create `styles.css`.")

# --- Database Setup (SQLAlchemy) ---
Base = declarative_base()
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- Database Models ---
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    name = Column(String)
    email = Column(String)
    role = Column(String, default='staff') # admin, manager, staff
    inventories = relationship('Inventory', back_populates='user', cascade="all, delete-orphan")
    logs = relationship('Log', back_populates='user', cascade="all, delete-orphan")
    transactions = relationship('Transaction', back_populates='user', cascade="all, delete-orphan")

class Inventory(Base):
    __tablename__ = 'inventory'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    sku = Column(String, nullable=False, index=True)
    description = Column(String)
    qty_available = Column(Float, default=0)
    location = Column(String)
    last_updated = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)

    user = relationship('User', back_populates='inventories')
    __table_args__ = (
        st.UniqueConstraint('user_id', 'sku', name='_user_sku_uc'), # Ensure SKU is unique per user
    )

class Log(Base):
    __tablename__ = 'logs'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.now)
    action = Column(String, nullable=False) # e.g., 'ADD', 'EDIT', 'DELETE', 'UPLOAD'
    sku = Column(String) # SKU affected
    details = Column(Text) # JSON string of old/new values or other relevant info

    user = relationship('User', back_populates='logs')

class Transaction(Base):
    __tablename__ = 'transactions'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    sku = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.now)
    type = Column(String, nullable=False) # 'IN' (increase), 'OUT' (decrease)
    quantity_change = Column(Float, nullable=False) # Absolute change
    current_qty = Column(Float, nullable=False) # Quantity after transaction

    user = relationship('User', back_populates='transactions')

# --- Database Initialization and CRUD ---
def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Create default admin user if not exists
        if not db.query(User).filter_by(username=ADMIN_USERNAME).first():
            hashed_password = bcrypt.hashpw(ADMIN_PASSWORD.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            admin_user = User(
                username=ADMIN_USERNAME,
                password_hash=hashed_password,
                name="Admin User",
                email="admin@example.com",
                role="admin"
            )
            db.add(admin_user)
            db.commit()
            st.success(f"Default admin user '{ADMIN_USERNAME}' created. Password: '{ADMIN_PASSWORD}'")
    except IntegrityError:
        db.rollback()
        st.error("Error creating default admin user (username might already exist).")
    finally:
        db.close()

@st.cache_data(ttl=60) # Cache for 60 seconds
def get_all_users_for_auth():
    db = SessionLocal()
    users = db.query(User).all()
    db.close()
    credentials = {"usernames": {}}
    for user in users:
        credentials["usernames"][user.username] = {
            "email": user.email,
            "name": user.name,
            "password": user.password_hash # This is the hashed password
        }
    return credentials

def get_user_details(username):
    db = SessionLocal()
    user = db.query(User).filter_by(username=username).first()
    db.close()
    return user

def register_new_user(username, name, password, email, role='staff'):
    db = SessionLocal()
    try:
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        new_user = User(username=username, name=name, password_hash=hashed_password, email=email, role=role)
        db.add(new_user)
        db.commit()
        return True
    except IntegrityError:
        db.rollback()
        return False # Username already exists
    finally:
        db.close()

def get_current_user_id():
    user = get_user_details(st.session_state.get('username'))
    return user.id if user else None

@st.cache_data(ttl=5) # Cache inventory data for 5 seconds
def load_inventory_data(user_id):
    if not user_id: return pd.DataFrame()
    db = SessionLocal()
    inventory_items = db.query(Inventory).filter_by(user_id=user_id).all()
    db.close()
    if not inventory_items:
        return pd.DataFrame(columns=['id', 'sku', 'description', 'qty_available', 'location', 'last_updated'])
    data = [{
        'id': item.id,
        'sku': item.sku,
        'description': item.description,
        'qty_available': item.qty_available,
        'location': item.location,
        'last_updated': item.last_updated
    } for item in inventory_items]
    df = pd.DataFrame(data)
    df['last_updated'] = pd.to_datetime(df['last_updated'])
    return df

def add_inventory_item(user_id, sku, description, qty_available, location):
    db = SessionLocal()
    try:
        new_item = Inventory(user_id=user_id, sku=sku, description=description,
                             qty_available=qty_available, location=location)
        db.add(new_item)
        db.commit()
        add_log_entry(user_id, 'ADD', sku, f"Added new item: Qty {qty_available}, Loc {location}")
        record_transaction(user_id, sku, 'IN', qty_available, qty_available)
        st.cache_data.clear() # Clear cache to refresh data
        return True
    except IntegrityError:
        db.rollback()
        return False # SKU already exists for this user
    finally:
        db.close()

def update_inventory_item(user_id, item_id, sku, description, qty_available, location):
    db = SessionLocal()
    try:
        item = db.query(Inventory).filter_by(id=item_id, user_id=user_id).first()
        if item:
            old_qty = item.qty_available
            old_sku = item.sku
            item.sku = sku
            item.description = description
            item.qty_available = qty_available
            item.location = location
            db.commit()

            log_details = f"Updated item. Old SKU: {old_sku}, New SKU: {sku}, Old Qty: {old_qty}, New Qty: {qty_available}"
            add_log_entry(user_id, 'EDIT', sku, log_details)

            # Record transaction if quantity changed
            if qty_available != old_qty:
                trans_type = 'IN' if qty_available > old_qty else 'OUT'
                change = abs(qty_available - old_qty)
                record_transaction(user_id, sku, trans_type, change, qty_available)

            st.cache_data.clear() # Clear cache to refresh data
            return True
        return False
    except IntegrityError:
        db.rollback()
        return False # SKU already exists for this user
    finally:
        db.close()

def delete_inventory_item(user_id, item_id):
    db = SessionLocal()
    try:
        item = db.query(Inventory).filter_by(id=item_id, user_id=user_id).first()
        if item:
            sku_deleted = item.sku
            db.delete(item)
            db.commit()
            add_log_entry(user_id, 'DELETE', sku_deleted, f"Deleted item: {sku_deleted}")
            st.cache_data.clear() # Clear cache to refresh data
            return True
        return False
    finally:
        db.close()

@st.cache_data(ttl=10) # Cache logs for 10 seconds
def load_logs_data(user_id):
    if not user_id: return pd.DataFrame()
    db = SessionLocal()
    logs = db.query(Log).filter_by(user_id=user_id).order_by(Log.timestamp.desc()).all()
    db.close()
    if not logs:
        return pd.DataFrame(columns=['timestamp', 'user', 'action', 'sku', 'details'])
    data = [{
        'timestamp': log.timestamp,
        'user': log.user.username if log.user else 'N/A',
        'action': log.action,
        'sku': log.sku,
        'details': log.details
    } for log in logs]
    df = pd.DataFrame(data)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

def add_log_entry(user_id, action, sku=None, details=None):
    db = SessionLocal()
    try:
        new_log = Log(user_id=user_id, action=action, sku=sku, details=details)
        db.add(new_log)
        db.commit()
        st.cache_data.clear() # Clear cache for logs
    finally:
        db.close()

def clear_all_logs(user_id):
    db = SessionLocal()
    try:
        db.query(Log).filter_by(user_id=user_id).delete()
        db.commit()
        st.cache_data.clear() # Clear cache for logs
        return True
    except Exception as e:
        db.rollback()
        st.error(f"Error clearing logs: {e}")
        return False
    finally:
        db.close()

@st.cache_data(ttl=10)
def load_transactions_data(user_id):
    if not user_id: return pd.DataFrame()
    db = SessionLocal()
    transactions = db.query(Transaction).filter_by(user_id=user_id).order_by(Transaction.timestamp.asc()).all()
    db.close()
    if not transactions:
        return pd.DataFrame(columns=['timestamp', 'sku', 'type', 'quantity_change', 'current_qty'])
    data = [{
        'timestamp': t.timestamp,
        'sku': t.sku,
        'type': t.type,
        'quantity_change': t.quantity_change,
        'current_qty': t.current_qty
    } for t in transactions]
    df = pd.DataFrame(data)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

def record_transaction(user_id, sku, trans_type, quantity_change, current_qty):
    db = SessionLocal()
    try:
        new_transaction = Transaction(
            user_id=user_id,
            sku=sku,
            type=trans_type,
            quantity_change=quantity_change,
            current_qty=current_qty
        )
        db.add(new_transaction)
        db.commit()
        st.cache_data.clear() # Clear cache for transactions
    finally:
        db.close()

# --- Initialize DB on app start ---
init_db()

# --- Authentication ---
names = []
usernames = []
hashed_passwords = []

db_users = get_all_users_for_auth()["usernames"]
for username, details in db_users.items():
    usernames.append(username)
    names.append(details["name"])
    hashed_passwords.append(details["password"])

authenticator = stauth.Authenticate(
    names,
    usernames,
    hashed_passwords,
    'inventory_dashboard_cookie',
    'abcdef', # A random string for cookie signature
    cookie_expiry_days=30
)

st.sidebar.image("https://www.flaticon.com/svg/static/icons/svg/2932/2932525.svg", width=100)
st.sidebar.title("📦 Inventory Dashboard")

name, authentication_status, username = authenticator.login('Login', 'sidebar')

if st.session_state["authentication_status"] == False:
    st.sidebar.error('Username/password is incorrect')
elif st.session_state["authentication_status"] == None:
    st.sidebar.warning('Please enter your username and password')
    if st.sidebar.button("Register New User"):
        with st.form("register_form"):
            st.subheader("Register New User")
            new_username = st.text_input("Username")
            new_name = st.text_input("Full Name")
            new_email = st.text_input("Email")
            new_password = st.text_input("Password", type='password')
            new_password_confirm = st.text_input("Confirm Password", type='password')
            if st.form_submit_button("Register"):
                if new_password != new_password_confirm:
                    st.error("Passwords do not match!")
                elif not new_username or not new_name or not new_password:
                    st.error("All fields are required!")
                else:
                    if register_new_user(new_username, new_name, new_password, new_email):
                        st.success("User registered successfully! Please login.")
                        st.experimental_rerun() # Rerun to refresh authenticator
                    else:
                        st.error("Username already exists or registration failed.")

# --- Main Application Logic (if authenticated) ---
if st.session_state["authentication_status"]:
    # Get current user details
    current_user = get_user_details(st.session_state["username"])
    st.session_state['user_id'] = current_user.id
    st.session_state['user_role'] = current_user.role
    st.session_state['name'] = current_user.name

    with st.sidebar:
        st.write(f'Welcome, *{st.session_state["name"]}*!')
        st.write(f'Role: *{st.session_state["user_role"].capitalize()}*')
        authenticator.logout('Logout', 'main')

    st.title("📦 Warehouse Inventory Dashboard")

    tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Inventory Management", "Logs", "Analytics"])

    # --- Load Data for current user ---
    current_user_id = st.session_state['user_id']
    inventory_df = load_inventory_data(current_user_id)
    logs_df = load_logs_data(current_user_id)
    transactions_df = load_transactions_data(current_user_id)

    with tab1: # --- Overview Tab ---
        st.header("Dashboard Overview")

        # KPIs
        col1, col2, col3, col4 = st.columns(4)

        total_skus = inventory_df['sku'].nunique() if not inventory_df.empty else 0
        total_quantity = inventory_df['qty_available'].sum() if not inventory_df.empty else 0
        low_stock_items_count = inventory_df[inventory_df['qty_available'] < LOW_STOCK_THRESHOLD]['sku'].nunique() if not inventory_df.empty else 0
        unique_locations = inventory_df['location'].nunique() if not inventory_df.empty else 0

        with col1:
            st.markdown(f'<div class="kpi-card"><h3>Total SKUs</h3><p style="font-size: 2.2em; font-weight: 700; color: #2980b9;">{total_skus}</p></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="kpi-card"><h3>Total Quantity</h3><p style="font-size: 2.2em; font-weight: 700; color: #2980b9;">{total_quantity:,.0f}</p></div>', unsafe_allow_html=True)
        with col3:
            st.markdown(f'<div class="kpi-card"><h3>Low Stock Items</h3><p style="font-size: 2.2em; font-weight: 700; color: #e74c3c;">{low_stock_items_count}</p></div>', unsafe_allow_html=True)
        with col4:
            st.markdown(f'<div class="kpi-card"><h3>Unique Locations</h3><p style="font-size: 2.2em; font-weight: 700; color: #2980b9;">{unique_locations}</p></div>', unsafe_allow_html=True)

        st.markdown("---")

        # Low Stock Alerts
        if low_stock_items_count > 0:
            st.warning(f"⚠️ **{low_stock_items_count}** items are critically low in stock!")
            low_stock_df = inventory_df[inventory_df['qty_available'] < LOW_STOCK_THRESHOLD].sort_values('qty_available')
            with st.expander("🚨 View Low Stock Items"):
                st.dataframe(low_stock_df[['sku', 'description', 'qty_available', 'location']], use_container_width=True)

            # Chart for Low Stock Items
            fig_low_stock = px.bar(low_stock_df, x='sku', y='qty_available',
                                    color='qty_available', color_continuous_scale='Reds',
                                    title='Top Low Stock Items',
                                    labels={'qty_available': 'Quantity Available', 'sku': 'SKU'})
            st.plotly_chart(fig_low_stock, use_container_width=True)

        st.markdown("---")

        # Inventory Distribution Charts
        if not inventory_df.empty:
            col_chart1, col_chart2 = st.columns(2)

            with col_chart1:
                st.subheader("Quantity Distribution by Location")
                location_summary = inventory_df.groupby('location')['qty_available'].sum().reset_index()
                fig_location = px.pie(location_summary, values='qty_available', names='location',
                                      title='Total Quantity by Location',
                                      hole=0.3)
                st.plotly_chart(fig_location, use_container_width=True)

            with col_chart2:
                st.subheader("Top 10 Most Stocked Items")
                top_items = inventory_df.sort_values('qty_available', ascending=False).head(10)
                fig_top_items = px.bar(top_items, x='sku', y='qty_available',
                                       color='qty_available', color_continuous_scale='Viridis',
                                       title='Top 10 Items by Quantity')
                st.plotly_chart(fig_top_items, use_container_width=True)
        else:
            st.info("No inventory data to display charts. Add some items!")

    with tab2: # --- Inventory Management Tab ---
        st.header("Inventory Management")

        # Search and Filter
        col_filter1, col_filter2 = st.columns([3, 1])
        with col_filter1:
            search_term = st.text_input("Search by SKU or Description", "").lower()
        with col_filter2:
            all_locations = inventory_df['location'].unique().tolist() if not inventory_df.empty else DEFAULT_LOCATIONS
            selected_locations = st.multiselect("Filter by Location", options=all_locations, default=all_locations)

        filtered_df = inventory_df
        if search_term:
            filtered_df = filtered_df[
                filtered_df['sku'].str.lower().str.contains(search_term) |
                filtered_df['description'].str.lower().str.contains(search_term)
            ]
        if selected_locations:
            filtered_df = filtered_df[filtered_df['location'].isin(selected_locations)]

        # Display Inventory Table
        st.subheader("Current Inventory")
        if not filtered_df.empty:
            # Add a 'Status' column for conditional formatting (visual only)
            display_df = filtered_df.copy()
            display_df['Status'] = display_df['qty_available'].apply(
                lambda x: "🚨 Low" if x < LOW_STOCK_THRESHOLD else "✅ OK"
            )
            # Custom styling for dataframe rows (limited in st.dataframe)
            # A more advanced table like st_aggrid would be needed for true row styling.
            # For now, we'll just display the status.
            st.dataframe(
                display_df[['sku', 'description', 'qty_available', 'location', 'last_updated', 'Status']],
                use_container_width=True,
                hide_index=True,
                height=400,
                selection_mode='single-row'
            )
            selected_rows = st.session_state.get('st_dataframe_selection', {'rows': []})
            selected_item_id = selected_rows['rows'][0] if selected_rows['rows'] else None
        else:
            st.info("No inventory items found matching your criteria.")
            selected_item_id = None

        st.markdown("---")

        # Add/Edit/Delete Forms
        col_crud1, col_crud2, col_crud3 = st.columns(3)
        with col_crud1:
            if st.button("➕ Add New Item", key="add_item_btn"):
                st.session_state['show_add_form'] = True
                st.session_state['show_edit_form'] = False
        with col_crud2:
            if st.button("✏️ Edit Selected Item", key="edit_item_btn", disabled=selected_item_id is None):
                st.session_state['show_edit_form'] = True
                st.session_state['show_add_form'] = False
        with col_crud3:
            if st.button("🗑️ Delete Selected Item", key="delete_item_btn", disabled=selected_item_id is None):
                if st.session_state.get('confirm_delete', False):
                    with st.spinner("Deleting item..."):
                        if delete_inventory_item(current_user_id, selected_item_id):
                            st.success("Item deleted successfully!")
                            st.session_state['confirm_delete'] = False
                            st.session_state['st_dataframe_selection'] = {'rows': []} # Clear selection
                            st.experimental_rerun()
                        else:
                            st.error("Failed to delete item.")
                else:
                    st.warning("Are you sure you want to delete this item? Click again to confirm.")
                    st.session_state['confirm_delete'] = True
            else:
                st.session_state['confirm_delete'] = False


        # Add Item Form
        if st.session_state.get('show_add_form'):
            with st.form("add_item_form", clear_on_submit=True):
                st.subheader("Add New Inventory Item")
                new_sku = st.text_input("SKU", key="new_sku")
                new_description = st.text_area("Description", key="new_desc")
                new_qty = st.number_input("Quantity Available", min_value=0.0, step=1.0, key="new_qty")
                new_location = st.selectbox("Location", options=all_locations + ["Add New Location"], key="new_loc_select")

                if new_location == "Add New Location":
                    new_location_text = st.text_input("Enter New Location", key="new_loc_text")
                    if new_location_text:
                        new_location = new_location_text
                    else:
                        st.warning("Please enter a new location name.")
                        new_location = None # Prevent adding if new location not typed

                submitted = st.form_submit_button("Add Item")
                if submitted and new_location:
                    if not new_sku:
                        st.error("SKU cannot be empty!")
                    elif add_inventory_item(current_user_id, new_sku, new_description, new_qty, new_location):
                        st.success(f"Item '{new_sku}' added successfully!")
                        st.session_state['show_add_form'] = False
                        st.experimental_rerun()
                    else:
                        st.error(f"Failed to add item. SKU '{new_sku}' might already exist.")

        # Edit Item Form
        if st.session_state.get('show_edit_form') and selected_item_id is not None:
            item_to_edit = inventory_df[inventory_df['id'] == selected_item_id].iloc[0]
            with st.form("edit_item_form"):
                st.subheader(f"Edit Item: {item_to_edit['sku']}")
                edit_sku = st.text_input("SKU", value=item_to_edit['sku'], key="edit_sku")
                edit_description = st.text_area("Description", value=item_to_edit['description'], key="edit_desc")
                edit_qty = st.number_input("Quantity Available", min_value=0.0, step=1.0, value=float(item_to_edit['qty_available']), key="edit_qty")
                edit_location = st.selectbox("Location", options=all_locations + ["Add New Location"], index=all_locations.index(item_to_edit['location']) if item_to_edit['location'] in all_locations else 0, key="edit_loc_select")

                if edit_location == "Add New Location":
                    edit_location_text = st.text_input("Enter New Location", key="edit_loc_text")
                    if edit_location_text:
                        edit_location = edit_location_text
                    else:
                        st.warning("Please enter a new location name.")
                        edit_location = None

                submitted = st.form_submit_button("Update Item")
                if submitted and edit_location:
                    if not edit_sku:
                        st.error("SKU cannot be empty!")
                    elif update_inventory_item(current_user_id, selected_item_id, edit_sku, edit_description, edit_qty, edit_location):
                        st.success(f"Item '{edit_sku}' updated successfully!")
                        st.session_state['show_edit_form'] = False
                        st.session_state['st_dataframe_selection'] = {'rows': []} # Clear selection
                        st.experimental_rerun()
                    else:
                        st.error(f"Failed to update item. SKU '{edit_sku}' might already exist or item not found.")

        st.markdown("---")

        # Excel Upload/Export
        col_excel1, col_excel2 = st.columns(2)
        with col_excel1:
            st.subheader("Upload Inventory (Excel)")
            uploaded_file = st.file_uploader("Upload .xlsx file", type=['xlsx'], key="excel_uploader")
            if uploaded_file:
                if st.button("Process Uploaded File"):
                    with st.spinner("Processing file..."):
                        try:
                            df_uploaded = pd.read_excel(uploaded_file)
                            required_cols = ['SKU', 'Description', 'QTYAVAILABLE', 'Location']
                            if not all(col in df_uploaded.columns for col in required_cols):
                                st.error(f"Missing required columns in Excel. Ensure you have: {', '.join(required_cols)}")
                            else:
                                # Clear existing inventory for the user before adding new
                                db = SessionLocal()
                                db.query(Inventory).filter_by(user_id=current_user_id).delete()
                                db.commit()
                                success_count = 0
                                for index, row in df_uploaded.iterrows():
                                    if add_inventory_item(current_user_id, str(row['SKU']), str(row['Description']), float(row['QTYAVAILABLE']), str(row['Location'])):
                                        success_count += 1
                                st.success(f"Successfully uploaded {success_count} items. Existing inventory was cleared.")
                                add_log_entry(current_user_id, 'UPLOAD', details=f"Uploaded {success_count} items from Excel.")
                                st.cache_data.clear() # Clear all caches
                                st.experimental_rerun()
                        except Exception as e:
                            st.error(f"Error processing file: {e}")
        with col_excel2:
            st.subheader("Export Inventory (Excel)")
            if not inventory_df.empty:
                excel_buffer = io.BytesIO()
                inventory_df.to_excel(excel_buffer, index=False, sheet_name='Inventory')
                excel_buffer.seek(0)
                st.download_button(
                    label="Download Inventory as Excel",
                    data=excel_buffer,
                    file_name="inventory_export.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.info("No inventory data to export.")

    with tab3: # --- Logs Tab ---
        st.header("Activity Logs")
        st.subheader(f"Recent Activities for {st.session_state['name']}")

        if not logs_df.empty:
            st.dataframe(logs_df[['timestamp', 'action', 'sku', 'details']], use_container_width=True, height=500, hide_index=True)
        else:
            st.info("No activity logs yet.")

        st.markdown("---")
        if st.session_state['user_role'] == 'admin':
            if st.button("🗑️ Clear All Logs (Admin Only)", key="clear_logs_btn"):
                if st.warning("Are you sure you want to clear all logs for this user? This action cannot be undone."):
                    if clear_all_logs(current_user_id):
                        st.success("All logs cleared successfully.")
                        st.experimental_rerun()
                    else:
                        st.error("Failed to clear logs.")
        else:
            st.info("Only admin users can clear logs.")

    with tab4: # --- Analytics & Forecasting Tab ---
        st.header("Advanced Analytics & Forecasting")
        st.info("This section provides basic analytics. For true advanced forecasting, a dedicated ML model (e.g., ARIMA, Prophet) would be integrated with more historical data points.")

        if not transactions_df.empty:
            st.subheader("Historical Stock Movement")

            # Aggregate transactions for daily net change
            transactions_df['date'] = transactions_df['timestamp'].dt.date
            daily_changes = transactions_df.groupby(['date', 'sku', 'type'])['quantity_change'].sum().unstack(fill_value=0)
            daily_net_change = daily_changes.apply(lambda x: x.get('IN', 0) - x.get('OUT', 0), axis=1).reset_index(name='net_change')

            # Calculate cumulative stock over time
            # This is a simplification; a more robust approach would reconstruct stock from initial inventory + all transactions.
            # For this example, we'll use the 'current_qty' from transactions as a proxy for stock level at that time.
            stock_over_time = transactions_df.sort_values('timestamp').groupby(['timestamp', 'sku'])['current_qty'].last().reset_index()

            # Plot stock trend for a selected SKU
            selected_sku_for_trend = st.selectbox("Select SKU for Trend Analysis", options=transactions_df['sku'].unique().tolist())
            if selected_sku_for_trend:
                sku_trend_df = stock_over_time[stock_over_time['sku'] == selected_sku_for_trend]
                if not sku_trend_df.empty:
                    fig_trend = px.line(sku_trend_df, x='timestamp', y='current_qty',
                                        title=f'Stock Level Trend for SKU: {selected_sku_for_trend}',
                                        labels={'current_qty': 'Quantity', 'timestamp': 'Date'})
                    st.plotly_chart(fig_trend, use_container_width=True)
                else:
                    st.info(f"No transaction data for SKU: {selected_sku_for_trend}")

            st.markdown("---")

            st.subheader("Inflow and Outflow Analysis")
            # Group by date and transaction type
            daily_in_out = transactions_df.groupby([transactions_df['timestamp'].dt.to_period('M'), 'type'])['quantity_change'].sum().unstack(fill_value=0)
            daily_in_out.index = daily_in_out.index.astype(str) # Convert PeriodIndex to string for Plotly
            daily_in_out = daily_in_out.reset_index().rename(columns={'timestamp': 'Month'})

            if 'IN' not in daily_in_out.columns: daily_in_out['IN'] = 0
            if 'OUT' not in daily_in_out.columns: daily_in_out['OUT'] = 0

            fig_in_out = px.bar(daily_in_out, x='Month', y=['IN', 'OUT'],
                                 title='Monthly Stock Inflow vs. Outflow',
                                 labels={'value': 'Quantity', 'variable': 'Type'},
                                 barmode='group')
            st.plotly_chart(fig_in_out, use_container_width=True)

            st.markdown("---")

            st.subheader("Forecasting (Basic Trend)")
            st.info("This is a simple linear trend projection. For more accurate forecasting, consider integrating time series models like ARIMA or Prophet, which require more data and complexity.")

            if selected_sku_for_trend and not sku_trend_df.empty:
                # Simple linear regression for future projection (very basic)
                from sklearn.linear_model import LinearRegression
                import numpy as np

                # Prepare data for regression: convert datetime to numerical (e.g., days since epoch)
                sku_trend_df['days_since_epoch'] = (sku_trend_df['timestamp'] - sku_trend_df['timestamp'].min()).dt.days
                X = sku_trend_df['days_since_epoch'].values.reshape(-1, 1)
                y = sku_trend_df['current_qty'].values

                if len(X) > 1: # Need at least 2 points for linear regression
                    model = LinearRegression()
                    model.fit(X, y)

                    # Project 30 days into the future
                    last_day = sku_trend_df['days_since_epoch'].max()
                    future_days = np.array(range(last_day + 1, last_day + 31)).reshape(-1, 1)
                    future_predictions = model.predict(future_days)

                    # Create a DataFrame for future predictions
                    future_dates = [sku_trend_df['timestamp'].min() + datetime.timedelta(days=int(d)) for d in future_days]
                    future_df = pd.DataFrame({'timestamp': future_dates, 'current_qty': future_predictions, 'type': 'Predicted'})
                    sku_trend_df['type'] = 'Actual' # Add type for plotting

                    combined_df = pd.concat([sku_trend_df[['timestamp', 'current_qty', 'type']], future_df])

                    fig_forecast = px.line(combined_df, x='timestamp', y='current_qty', color='type',
                                           title=f'Stock Level Forecast for SKU: {selected_sku_for_trend}',
                                           labels={'current_qty': 'Quantity', 'timestamp': 'Date'},
                                           color_discrete_map={'Actual': 'blue', 'Predicted': 'red'})
                    st.plotly_chart(fig_forecast, use_container_width=True)
                else:
                    st.info("Not enough data points for forecasting. Need at least two transactions for this SKU.")
            else:
                st.info("Select an SKU with transaction data to view basic forecasting.")

        else:
            st.info("No transaction data available for analytics. Add/edit items in Inventory Management to generate transactions.")
