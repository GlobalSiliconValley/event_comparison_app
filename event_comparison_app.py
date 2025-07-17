import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import json

# Try to import Supabase, fall back to local storage if not available
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    st.warning("Supabase not installed. Using local storage. Run: pip install supabase")

# Page configuration
st.set_page_config(
    page_title="Event Registration Comparison",
    page_icon="📊",
    layout="wide"
)

# Title
st.title("📊 Event Registration Data Comparison")
st.markdown("Compare registration data between two years relative to Summit start dates")

# Initialize session state
if 'df1' not in st.session_state:
    st.session_state.df1 = None
if 'df2' not in st.session_state:
    st.session_state.df2 = None
if 'year1' not in st.session_state:
    st.session_state.year1 = None
if 'year2' not in st.session_state:
    st.session_state.year2 = None
if 'summit_date1' not in st.session_state:
    st.session_state.summit_date1 = None
if 'summit_date2' not in st.session_state:
    st.session_state.summit_date2 = None
if 'date_column1' not in st.session_state:
    st.session_state.date_column1 = None
if 'date_column2' not in st.session_state:
    st.session_state.date_column2 = None

# Initialize Supabase client if available
if SUPABASE_AVAILABLE and "supabase" in st.secrets:
    @st.cache_resource
    def init_supabase():
        try:
            url = st.secrets["supabase"]["url"]
            key = st.secrets["supabase"]["key"]

            # Debug: Show URL format without revealing full URL
            st.sidebar.write("URL check:")
            st.sidebar.write(f"- Starts with https://: {url.startswith('https://')}")
            st.sidebar.write(f"- Contains supabase.co: {'supabase.co' in url}")
            st.sidebar.write(f"- Length: {len(url)} chars")

            # Clean the URL - remove any trailing slashes or spaces
            url = url.strip().rstrip('/')
            key = key.strip()

            # Additional cleaning - remove any quotes that might have been accidentally included
            url = url.strip('"\'')
            key = key.strip('"\'')

            return create_client(url, key)
        except Exception as e:
            st.error(f"Error initializing Supabase: {str(e)}")
            return None

    try:
        supabase = init_supabase()
        SUPABASE_CONNECTED = supabase is not None
    except Exception as e:
        SUPABASE_CONNECTED = False
        st.error(f"Could not connect to Supabase: {str(e)}")
else:
    SUPABASE_CONNECTED = False

# Senior leader keywords
SENIOR_KEYWORDS = ["Chief", "VP", "President", "Director", "Head", "Founder", "Dean"]

# Community College patterns and known institutions
CC_PATTERNS = [
    "Community College",
    "CC",
    "Technical College",
    "Junior College",
    "Comm Coll",
    "Comm. College",
    "Tech College",
    "City College",
    "County College"
]

# A sample of well-known community colleges (we'll expand this)
KNOWN_COMMUNITY_COLLEGES = {
    # Major community college systems
    "Miami Dade College",
    "Houston Community College",
    "Austin Community College District",
    "Northern Virginia Community College",
    "City College of San Francisco",
    "Santa Monica College",
    "Lone Star College System",
    "Dallas County Community College District",
    "Maricopa County Community College District",
    "Los Angeles Community College District",

    # Individual community colleges by state
    # California
    "Pasadena City College",
    "Orange Coast College",
    "De Anza College",
    "Foothill College",
    "Santa Barbara City College",
    "Glendale Community College",
    "College of the Canyons",
    "Mt. San Antonio College",
    "Cerritos College",
    "Long Beach City College",

    # Texas
    "Tarrant County College",
    "San Jacinto College",
    "Collin College",
    "El Paso Community College",
    "San Antonio College",
    "Alamo Community College District",

    # Florida
    "Broward College",
    "Valencia College",
    "Hillsborough Community College",
    "Palm Beach State College",
    "Seminole State College of Florida",
    "St. Petersburg College",

    # New York
    "CUNY Borough of Manhattan Community College",
    "CUNY LaGuardia Community College",
    "Nassau Community College",
    "Suffolk County Community College",
    "Monroe Community College",

    # Illinois
    "College of DuPage",
    "Harper College",
    "Oakton Community College",
    "Joliet Junior College",
    "Triton College",

    # Other states
    "Community College of Philadelphia",
    "Montgomery College", # Maryland
    "Cuyahoga Community College", # Ohio
    "Wake Technical Community College", # North Carolina
    "Ivy Tech Community College", # Indiana
    "Portland Community College", # Oregon
    "Mesa Community College", # Arizona
    "Salt Lake Community College", # Utah
    "Front Range Community College", # Colorado
    "Kirkwood Community College", # Iowa
    "Johnson County Community College", # Kansas
}

def is_community_college(institution_name):
    """
    Check if an institution is a community college using:
    1. Exact match against known community colleges
    2. Pattern matching for common CC naming conventions
    """
    if not institution_name:
        return False

    # Normalize the name for comparison
    name_upper = institution_name.upper().strip()

    # Check exact match first (case-insensitive)
    for known_cc in KNOWN_COMMUNITY_COLLEGES:
        if known_cc.upper() == name_upper:
            return True

    # Check if any pattern exists in the name
    for pattern in CC_PATTERNS:
        if pattern.upper() in name_upper:
            # Exclude false positives like "College Community" (reversed)
            if pattern.upper() == "CC" and "CC" in name_upper:
                # Make sure it's actually a CC abbreviation, not part of another word
                words = name_upper.split()
                if "CC" in words or name_upper.endswith(" CC") or name_upper.endswith("CC"):
                    return True
            else:
                return True

    return False

def save_data_to_database():
    """Save current session data to Supabase"""
    if not SUPABASE_CONNECTED:
        st.error("Database not connected. Please check your configuration.")
        return False

    try:
        # Debug: Check what we're trying to save
        st.write("Preparing data for save...")

        # Convert DataFrames to JSON-serializable format
        data = {
            'df1': st.session_state.df1.to_json(date_format='iso') if st.session_state.df1 is not None else None,
            'df2': st.session_state.df2.to_json(date_format='iso') if st.session_state.df2 is not None else None,
            'year1': st.session_state.year1,
            'year2': st.session_state.year2,
            'summit_date1': st.session_state.summit_date1.isoformat() if st.session_state.summit_date1 else None,
            'summit_date2': st.session_state.summit_date2.isoformat() if st.session_state.summit_date2 else None,
            'date_column1': st.session_state.date_column1,
            'date_column2': st.session_state.date_column2
        }

        # Debug: Show data size
        data_str = json.dumps(data)
        data_size_mb = len(data_str) / (1024 * 1024)
        st.write(f"Data size: {data_size_mb:.2f} MB ({len(data_str):,} characters)")

        if data_size_mb > 50:  # Supabase has limits
            st.warning("Data might be too large. Consider filtering or sampling.")

        # Update or insert data
        # First, try to update existing record
        response = supabase.table('event_data').update({
            'data_value': data
        }).eq('data_key', 'event_comparison_data').execute()

        # If no rows were updated, insert new record
        if len(response.data) == 0:
            response = supabase.table('event_data').insert({
                'data_key': 'event_comparison_data',
                'data_value': data
            }).execute()

        # Debug: Check response
        st.write("Save response:", response)

        st.success("✅ Data saved to database successfully!")
        return True
    except Exception as e:
        st.error(f"Error saving to database: {str(e)}")
        st.write("Error type:", type(e).__name__)
        import traceback
        st.text(traceback.format_exc())
        return False

def load_data_from_database():
    """Load saved data from Supabase"""
    if not SUPABASE_CONNECTED:
        st.error("Database not connected. Please check your configuration.")
        return False

    try:
        # Fetch data
        response = supabase.table('event_data').select("*").eq('data_key', 'event_comparison_data').single().execute()

        if response.data:
            data = response.data['data_value']

            # Restore DataFrames
            if data.get('df1'):
                st.session_state.df1 = pd.read_json(data['df1'])
            if data.get('df2'):
                st.session_state.df2 = pd.read_json(data['df2'])

            # Restore other values
            st.session_state.year1 = data.get('year1')
            st.session_state.year2 = data.get('year2')

            # Restore dates
            if data.get('summit_date1'):
                st.session_state.summit_date1 = pd.to_datetime(data['summit_date1']).date()
            if data.get('summit_date2'):
                st.session_state.summit_date2 = pd.to_datetime(data['summit_date2']).date()

            st.session_state.date_column1 = data.get('date_column1')
            st.session_state.date_column2 = data.get('date_column2')

            st.success("✅ Data loaded from database successfully!")
            return True
        else:
            st.info("No saved data found in database")
            return False

    except Exception as e:
        st.error(f"Error loading from database: {str(e)}")
        return False

def parse_dates(df, date_column='Registration Date'):
    """Parse dates handling both ISO and MM/DD/YY formats"""
    # Show available columns to help debug
    st.info(f"Available columns: {', '.join(df.columns.tolist())}")

    # Try to find date column with various possible names
    possible_date_columns = ['Last Registration Date (GMT)',
                             'Last Registration Date (GMT-05:00) Eastern [US & Canada]',
                             'Original Response Date (GMT)',
                             'Original Response Date (GMT-05:00) Eastern [US & Canada]',
                             'Registration Date', 'Date', 'Created Date', 'Registered Date',
                             'Registration_Date', 'registration_date', 'Created', 'Timestamp']

    date_col_found = None
    for col in possible_date_columns:
        if col in df.columns:
            date_col_found = col
            st.success(f"Found date column: '{col}'")
            break

    if date_col_found is None:
        st.error(f"No date column found. Please ensure your CSV has one of these columns: {', '.join(possible_date_columns)}")
        return None, None

    # Use the found column
    date_column = date_col_found

    # Try multiple date formats
    date_formats = ['%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y', '%d/%m/%Y', '%d/%m/%y']

    for fmt in date_formats:
        try:
            df[date_column] = pd.to_datetime(df[date_column], format=fmt)
            # Remove timezone information to avoid comparison issues
            if df[date_column].dt.tz is not None:
                df[date_column] = df[date_column].dt.tz_localize(None)
            return df, date_column
        except:
            continue

    # If all formats fail, try pandas automatic parsing
    try:
        df[date_column] = pd.to_datetime(df[date_column], format='mixed', dayfirst=False)
        # Remove timezone information to avoid comparison issues
        if df[date_column].dt.tz is not None:
            df[date_column] = df[date_column].dt.tz_localize(None)
        return df, date_column
    except:
        st.error("Unable to parse dates. Please check date format.")
        return None, None

def get_job_classifications(df):
    """Get unique job classifications from the dataframe"""
    if 'Job Classification' in df.columns:
        classifications = df['Job Classification'].dropna().unique()
        return sorted(classifications)
    return []

def calculate_kpis(df, days_before_summit, date_column, summit_date, job_filter=None, institution_filter=None):
    """Calculate KPIs for data up to specified days before summit"""
    # Calculate the cutoff date
    cutoff_date = summit_date - timedelta(days=days_before_summit)

    # Filter data up to cutoff date
    filtered_df = df[df[date_column] <= cutoff_date]

    # Apply job classification filter if specified
    if job_filter and job_filter != "All" and 'Job Classification' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Job Classification'] == job_filter]

    # Create a separate dataframe for institution-based metrics
    inst_filtered_df = filtered_df.copy()

    # Apply institution type filter for specific metrics
    if institution_filter and institution_filter != "All" and 'Job Classification' in inst_filtered_df.columns:
        if institution_filter == "Higher Education":
            # Filter for HE institutions
            inst_filtered_df = inst_filtered_df[inst_filtered_df['Job Classification'].str.contains('HE|Higher Ed|Higher Education', case=False, na=False)]
        elif institution_filter == "K-12":
            # Filter for K-12 institutions
            inst_filtered_df = inst_filtered_df[inst_filtered_df['Job Classification'].str.contains('K-12|K12', case=False, na=False)]

    # 1. Number of Attendees (non-empty email addresses)
    if 'Email Address' in filtered_df.columns:
        num_attendees = len(filtered_df[filtered_df['Email Address'].notna()])
    else:
        num_attendees = len(filtered_df[filtered_df[date_column].notna()])

    # 2. Number of Senior Leaders
    if 'Title' in filtered_df.columns:
        senior_mask = filtered_df['Title'].fillna('').str.contains('|'.join(SENIOR_KEYWORDS), case=False, na=False)
        num_senior_leaders = senior_mask.sum()
        senior_df = filtered_df[senior_mask]
    else:
        num_senior_leaders = 0
        senior_df = pd.DataFrame()

    # 3. Number of Women Leaders
    if 'My Gender is:' in filtered_df.columns and len(senior_df) > 0:
        gender_col = filtered_df['My Gender is:'].fillna('').str.lower()
        num_women_leaders = len(senior_df[senior_df['My Gender is:'].fillna('').str.lower().isin(['female', 'woman', 'f'])])
    elif 'Gender' in filtered_df.columns and len(senior_df) > 0:
        num_women_leaders = len(senior_df[senior_df['Gender'].fillna('').str.lower().isin(['female', 'woman', 'f'])])
    else:
        num_women_leaders = 0

    # 4. Number of Institutions (use institution-filtered data)
    if 'Company Name' in inst_filtered_df.columns:
        num_institutions = inst_filtered_df['Company Name'].dropna().nunique()
    else:
        num_institutions = 0

    # 5. Number of Community Colleges (use institution-filtered data)
    if 'Company Name' in inst_filtered_df.columns:
        # Get unique institutions
        unique_institutions = inst_filtered_df['Company Name'].dropna().unique()

        # Count community colleges using our comprehensive check
        cc_count = 0
        cc_list = []
        for inst in unique_institutions:
            if is_community_college(inst):
                cc_count += 1
                cc_list.append(inst)

        num_community_colleges = cc_count

        # Also count all institutions with "College" in the name
        college_mask = inst_filtered_df['Company Name'].fillna('').str.contains('College', case=False, na=False)
        num_colleges = inst_filtered_df[college_mask]['Company Name'].nunique()
    else:
        num_community_colleges = 0
        num_colleges = 0

    # 6. Number of U.S. States Only (use institution-filtered data)
    if 'Primary State/Prov. Code' in inst_filtered_df.columns:
        # Get all unique state/province codes
        all_codes = inst_filtered_df['Primary State/Prov. Code'].dropna().unique()

        # Define valid U.S. state codes (50 states + DC)
        us_state_codes = {
            'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
            'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
            'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
            'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
            'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY', 'DC'
        }

        # Count only valid U.S. states
        us_states_in_data = [code for code in all_codes if code.upper() in us_state_codes]
        num_us_states = len(us_states_in_data)
    else:
        num_us_states = 0

    # 7. Number of Startups (attendees from startups or corporate enterprises)
    if 'Job Classification' in filtered_df.columns:
        # Count attendees with startup/growth or corporate enterprise classification
        startup_mask = filtered_df['Job Classification'].fillna('').str.contains(
            'Start Up/Growth Stage Company|Corporate Enterprise',
            case=False,
            na=False
        )
        num_startups = startup_mask.sum()
    else:
        num_startups = 0

    return {
        'Attendees': num_attendees,
        'Senior Leaders': num_senior_leaders,
        'Women Leaders': num_women_leaders,
        'Institutions': num_institutions,
        'Community Colleges': num_community_colleges,
        'All Colleges': num_colleges,
        'U.S. States': num_us_states,
        'Startups': num_startups
    }

def create_daily_registration_chart(df1, df2, year1, year2, days_before_summit, date_column1, date_column2, summit_date1, summit_date2, job_filter=None):
    """Create line chart showing daily cumulative registrations relative to summit dates"""
    # Calculate cutoff dates
    cutoff_date1 = summit_date1 - timedelta(days=days_before_summit)
    cutoff_date2 = summit_date2 - timedelta(days=days_before_summit)

    # Filter data
    df1_filtered = df1[df1[date_column1] <= cutoff_date1].copy()
    df2_filtered = df2[df2[date_column2] <= cutoff_date2].copy()

    # Apply job classification filter if specified
    if job_filter and job_filter != "All":
        if 'Job Classification' in df1_filtered.columns:
            df1_filtered = df1_filtered[df1_filtered['Job Classification'] == job_filter]
        if 'Job Classification' in df2_filtered.columns:
            df2_filtered = df2_filtered[df2_filtered['Job Classification'] == job_filter]

    # Calculate days before summit for each registration
    df1_filtered['days_before_summit'] = (summit_date1 - df1_filtered[date_column1]).dt.days
    df2_filtered['days_before_summit'] = (summit_date2 - df2_filtered[date_column2]).dt.days

    # Group by days before summit and count
    daily1 = df1_filtered.groupby('days_before_summit').size().reset_index(name='count')
    daily2 = df2_filtered.groupby('days_before_summit').size().reset_index(name='count')

    # Sort by days before summit (descending) and calculate cumulative
    daily1 = daily1.sort_values('days_before_summit', ascending=False)
    daily2 = daily2.sort_values('days_before_summit', ascending=False)

    daily1['cumulative'] = daily1['count'].cumsum()
    daily2['cumulative'] = daily2['count'].cumsum()

    # Create figure
    fig = go.Figure()

    # Add traces
    fig.add_trace(go.Scatter(
        x=daily1['days_before_summit'],
        y=daily1['cumulative'],
        mode='lines+markers',
        name=str(year1),
        line=dict(width=3)
    ))

    fig.add_trace(go.Scatter(
        x=daily2['days_before_summit'],
        y=daily2['cumulative'],
        mode='lines+markers',
        name=str(year2),
        line=dict(width=3)
    ))

    # Update layout
    fig.update_layout(
        title=f'Daily Cumulative Registrations (Days Before Summit){" - " + job_filter if job_filter and job_filter != "All" else ""}',
        xaxis_title='Days Before Summit',
        yaxis_title='Cumulative Registrations',
        hovermode='x unified',
        height=400,
        xaxis=dict(autorange='reversed')  # Show countdown to summit
    )

    return fig

# Sidebar for data management
with st.sidebar:
    st.header("📁 Data Management")

    # Debug info
    with st.expander("Debug Info"):
        st.write("df1 loaded:", st.session_state.df1 is not None)
        st.write("df2 loaded:", st.session_state.df2 is not None)
        if st.session_state.df1 is not None:
            st.write("df1 shape:", st.session_state.df1.shape)
        if st.session_state.df2 is not None:
            st.write("df2 shape:", st.session_state.df2.shape)

        # Force reload button
        if st.button("🔄 Force Reload Files"):
            # Check if file uploaders have files
            if 'file2' in st.session_state and st.session_state.file2 is not None:
                try:
                    df2 = pd.read_csv(st.session_state.file2)
                    df2, date_col2 = parse_dates(df2)
                    if df2 is not None:
                        st.session_state.df2 = df2
                        st.session_state.date_column2 = date_col2
                        st.success("Force reloaded file 2!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Force reload error: {str(e)}")

    if SUPABASE_CONNECTED:
        st.success("✅ Database connected")

        # Load saved data button
        if st.button("Load Data from Database", type="primary"):
            if load_data_from_database():
                st.rerun()

        # Save current data button - show when both files are loaded
        if st.session_state.df1 is not None and st.session_state.df2 is not None:
            st.markdown("---")
            if st.button("💾 Save Data to Database", type="secondary", key="save_btn", help="Save current data to Supabase"):
                with st.spinner("Saving to database..."):
                    if save_data_to_database():
                        st.balloons()
        else:
            st.info("Upload both CSV files to enable saving to database")

        # Connection test button
        if st.button("🔌 Test Connection"):
            try:
                import socket
                url = st.secrets["supabase"]["url"]
                # Extract hostname
                hostname = url.replace("https://", "").replace("http://", "").split("/")[0]
                st.write(f"Testing connection to: {hostname}")

                # Try DNS lookup
                ip = socket.gethostbyname(hostname)
                st.success(f"✅ DNS resolved! IP: {ip}")

                # Try a simple HTTP request
                import requests
                response = requests.get(f"{url}/rest/v1/", headers={"apikey": "test"}, timeout=5)
                st.write(f"HTTP Status: {response.status_code}")

            except socket.gaierror as e:
                st.error(f"❌ DNS Error: Cannot resolve hostname")
                st.write("Make sure your URL is correct in .streamlit/secrets.toml")
            except Exception as e:
                st.error(f"Connection test failed: {str(e)}")
                st.write(f"Error type: {type(e).__name__}")
    else:
        st.warning("Database not connected")
        with st.expander("Setup Instructions"):
            st.markdown("""
            To enable database storage:
            1. Install Supabase: `pip install supabase`
            2. Create a Supabase project at supabase.com
            3. Add your credentials to `.streamlit/secrets.toml`:
            ```toml
            [supabase]
            url = "your-project-url"
            key = "your-anon-key"
            ```
            """)

    st.markdown("---")
    st.markdown("**Note**: Database storage allows your team to access the same data without re-uploading CSVs.")

# File upload section
col1, col2 = st.columns(2)

with col1:
    st.subheader("📁 First Year Data")
    if st.session_state.df1 is None:
        file1 = st.file_uploader("Choose CSV file", type="csv", key="file1")
        if file1 is not None:
            try:
                df1 = pd.read_csv(file1)
                df1, date_col1 = parse_dates(df1)
                if df1 is not None:
                    st.session_state.df1 = df1
                    st.session_state.date_column1 = date_col1
            except Exception as e:
                st.error(f"Error reading file: {str(e)}")

    if st.session_state.df1 is not None:
        col1a, col1b = st.columns(2)
        with col1a:
            year1 = st.number_input("Year:", min_value=2000, max_value=2030,
                                    value=st.session_state.year1 or 2024, key="year1_input")
            st.session_state.year1 = year1
        with col1b:
            summit_date1 = st.date_input("Summit Start Date:",
                                         value=st.session_state.summit_date1 or datetime(2024, 4, 14).date(),
                                         key="summit1_date")
            st.session_state.summit_date1 = summit_date1
        st.success(f"✅ Loaded {len(st.session_state.df1)} records for year {year1}")

with col2:
    st.subheader("📁 Second Year Data")
    if st.session_state.df2 is None:
        file2 = st.file_uploader("Choose CSV file", type="csv", key="file2")
        if file2 is not None:
            try:
                df2 = pd.read_csv(file2)
                df2, date_col2 = parse_dates(df2)
                if df2 is not None:
                    st.session_state.df2 = df2
                    st.session_state.date_column2 = date_col2
                    st.success(f"✅ Successfully loaded file into session state")
            except Exception as e:
                st.error(f"Error reading file: {str(e)}")

    if st.session_state.df2 is not None:
        col2a, col2b = st.columns(2)
        with col2a:
            year2 = st.number_input("Year:", min_value=2000, max_value=2030,
                                    value=st.session_state.year2 or 2025, key="year2_input")
            st.session_state.year2 = year2
        with col2b:
            summit_date2 = st.date_input("Summit Start Date:",
                                         value=st.session_state.summit_date2 or datetime(2025, 4, 6).date(),
                                         key="summit2_date")
            st.session_state.summit_date2 = summit_date2
        st.success(f"✅ Loaded {len(st.session_state.df2)} records for year {year2}")

# Analysis section
if (st.session_state.df1 is not None and st.session_state.df2 is not None and
        st.session_state.date_column1 is not None and st.session_state.date_column2 is not None):

    st.markdown("---")
    st.subheader("📅 Analysis Settings")

    # Get job classifications
    classifications1 = get_job_classifications(st.session_state.df1)
    classifications2 = get_job_classifications(st.session_state.df2)
    all_classifications = sorted(list(set(classifications1 + classifications2)))

    col_settings1, col_settings2 = st.columns(2)

    with col_settings1:
        # Days before summit selector
        days_before = st.slider(
            "Days before summit to analyze:",
            min_value=1,
            max_value=365,
            value=120,
            help="Compare registrations at the same number of days before each summit"
        )

    with col_settings2:
        # Job classification filter
        job_filter = st.selectbox(
            "Filter by Job Classification:",
            options=["All"] + all_classifications,
            help="Filter all metrics by specific job classification"
        )

    # Advanced filters section - Now job_filter is defined
    institution_filter = "All"
    if True:  # Always show institution filter
        st.markdown("---")
        st.subheader("🔧 Advanced Filters")
        st.markdown("Apply institution-type filtering to specific metrics:")

        # Institution type filter for metrics
        institution_filter = st.selectbox(
            "Filter institution-based metrics by type:",
            options=["All", "Higher Education", "K-12"],
            help="This filter applies to: Institutions, Community Colleges, All Colleges, and U.S. States counts",
            key="inst_filter"
        )

        if institution_filter != "All":
            st.info(f"📊 Institution-based metrics will only count {institution_filter} institutions")

    # Convert summit dates to datetime
    summit_date1_dt = pd.to_datetime(st.session_state.summit_date1)
    summit_date2_dt = pd.to_datetime(st.session_state.summit_date2)

    # Calculate KPIs with institution filter
    kpis1 = calculate_kpis(st.session_state.df1, days_before, st.session_state.date_column1,
                           summit_date1_dt, job_filter if job_filter != "All" else None,
                           institution_filter if institution_filter != "All" else None)
    kpis2 = calculate_kpis(st.session_state.df2, days_before, st.session_state.date_column2,
                           summit_date2_dt, job_filter if job_filter != "All" else None,
                           institution_filter if institution_filter != "All" else None)

    # Display KPIs
    st.markdown("---")
    st.subheader("📊 KPI Comparison")

    filter_text = f"**{days_before} days before summit**"
    if job_filter != "All":
        filter_text += f" | **Job Classification: {job_filter}**"
    if institution_filter != "All":
        filter_text += f" | **Institution Type: {institution_filter}**"

    st.markdown(filter_text)

    # Create KPI cards
    cols = st.columns(4)  # Changed to 4 columns to accommodate new metric
    kpi_names = list(kpis1.keys())

    for i, kpi in enumerate(kpi_names):
        with cols[i % 4]:  # Changed to 4 columns
            val1 = kpis1[kpi]
            val2 = kpis2[kpi]

            # Calculate percentage change
            if val1 > 0:
                pct_change = ((val2 - val1) / val1) * 100
            else:
                pct_change = 0 if val2 == 0 else 100

            # Display metric
            st.metric(
                label=kpi,
                value=f"{val2:,}",
                delta=f"{pct_change:+.1f}% vs {st.session_state.year1}",
                delta_color="normal"
            )

            # Show comparison details
            st.caption(f"{st.session_state.year1}: {val1:,} | {st.session_state.year2}: {val2:,}")

    # Display line chart
    st.markdown("---")
    st.subheader("📈 Registration Trends")

    fig = create_daily_registration_chart(
        st.session_state.df1,
        st.session_state.df2,
        st.session_state.year1,
        st.session_state.year2,
        days_before,
        st.session_state.date_column1,
        st.session_state.date_column2,
        summit_date1_dt,
        summit_date2_dt,
        job_filter if job_filter != "All" else None
    )
    st.plotly_chart(fig, use_container_width=True)

    # Summary statistics
    st.markdown("---")
    st.subheader("📋 Summary Statistics")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"**{st.session_state.year1} Summary** ({days_before} days before summit)")
        summary_df1 = pd.DataFrame(list(kpis1.items()), columns=['KPI', 'Value'])
        st.dataframe(summary_df1, use_container_width=True)

    with col2:
        st.markdown(f"**{st.session_state.year2} Summary** ({days_before} days before summit)")
        summary_df2 = pd.DataFrame(list(kpis2.items()), columns=['KPI', 'Value'])
        st.dataframe(summary_df2, use_container_width=True)

else:
    st.info("👆 Please upload both CSV files or load saved data to begin the comparison")

# Instructions
with st.expander("ℹ️ How to use this app"):
    st.markdown("""
    1. **Upload Files**: Upload two CSV files containing registration data OR load previously saved data
    2. **Set Summit Dates**: Specify the year and summit start date for each dataset
    3. **Choose Analysis Period**: Select how many days before the summit to analyze
    4. **Filter by Job Classification**: Optionally filter all metrics by K-12, HE, Workforce, etc.
    5. **Apply Institution Filters**: Filter institution-based metrics by Higher Education or K-12
    6. **View Results**: Examine KPIs, percentage changes, and trend charts
    
    **Expected CSV Columns:**
    - Date column: `Last Registration Date (GMT)` or similar variations
    - `Email Address`: Used to count attendees
    - `Title`: Job title (for senior leader identification)
    - `My Gender is:`: Gender information
    - `Company Name`: Organization name
    - `Primary State/Prov. Code`: State/Province code
    - `Job Classification`: K-12, HE, Workforce, etc.
    
    **KPI Definitions:**
    - **Attendees**: Total records with valid email addresses
    - **Senior Leaders**: Titles containing Chief, VP, President, Director, Head, Founder, or Dean
    - **Women Leaders**: Senior leaders with gender marked as Female
    - **Institutions**: Unique organizations
    - **Community Colleges**: Identified using comprehensive list + pattern matching
    - **All Colleges**: Any institution with "College" in the name
    - **U.S. States**: Valid U.S. state codes only (50 states + DC)
    - **Startups**: Attendees with "Start Up/Growth Stage Company" or "Corporate Enterprise" job classification
    
    **Institution Filtering:**
    - Institution-based metrics can be filtered by Higher Education or K-12
    - This affects: Institutions, Community Colleges, All Colleges, and U.S. States counts
    
    **Data Persistence:**
    - If database is connected, use the sidebar to save/load your data
    - Your team can access the same data without re-uploading CSVs
    """)