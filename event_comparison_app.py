import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import numpy as np

# Page configuration
st.set_page_config(
    page_title="Event Registration Comparison",
    page_icon="📊",
    layout="wide"
)

# Title
st.title("📊 Event Registration Data Comparison")
st.markdown("Compare registration data between two years")

# Initialize session state
if 'df1' not in st.session_state:
    st.session_state.df1 = None
if 'df2' not in st.session_state:
    st.session_state.df2 = None
if 'year1' not in st.session_state:
    st.session_state.year1 = None
if 'year2' not in st.session_state:
    st.session_state.year2 = None
if 'date_column1' not in st.session_state:
    st.session_state.date_column1 = None
if 'date_column2' not in st.session_state:
    st.session_state.date_column2 = None

# Senior leader keywords
SENIOR_KEYWORDS = ["Chief", "VP", "President", "Director", "Head", "Founder", "Dean"]

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
        df[date_column] = pd.to_datetime(df[date_column])
        # Remove timezone information to avoid comparison issues
        if df[date_column].dt.tz is not None:
            df[date_column] = df[date_column].dt.tz_localize(None)
        return df, date_column
    except:
        st.error("Unable to parse dates. Please check date format.")
        return None, None

def calculate_kpis(df, selected_date, date_column):
    """Calculate KPIs for data up to and including selected date"""
    # Convert selected_date to pandas datetime without timezone
    selected_date_pd = pd.to_datetime(selected_date).tz_localize(None)
    
    # Filter data up to selected date
    filtered_df = df[df[date_column] <= selected_date_pd]
    
    # 1. Number of Attendees (non-empty registrations)
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
    
    # 4. Number of Institutions
    if 'Company Name' in filtered_df.columns:
        num_institutions = filtered_df['Company Name'].dropna().nunique()
    else:
        num_institutions = 0
    
    # 5. Number of Community Colleges
    if 'Company Name' in filtered_df.columns:
        cc_mask = filtered_df['Company Name'].fillna('').str.contains('Community College|CC', case=False, na=False)
        num_community_colleges = filtered_df[cc_mask]['Company Name'].nunique()
    else:
        num_community_colleges = 0
    
    # 6. Number of U.S. States Represented
    if 'Primary State/Prov. Code' in filtered_df.columns:
        # Get all unique state/province codes
        all_codes = filtered_df['Primary State/Prov. Code'].dropna().unique()
        num_all_regions = len(all_codes)
        
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
        
        # For backwards compatibility, use total regions count
        num_states = num_all_regions
    else:
        num_states = 0
        num_us_states = 0
        num_all_regions = 0
    
    return {
        'Attendees': num_attendees,
        'Senior Leaders': num_senior_leaders,
        'Women Leaders': num_women_leaders,
        'Institutions': num_institutions,
        'Community Colleges': num_community_colleges,
        'Regions (States/Provinces)': num_states,
        'U.S. States Only': num_us_states if 'num_us_states' in locals() else 0
    }

def create_daily_registration_chart(df1, df2, year1, year2, selected_date1, selected_date2, date_column1, date_column2):
    """Create line chart showing daily cumulative registrations"""
    # Convert selected_dates to pandas datetime without timezone
    selected_date1_pd = pd.to_datetime(selected_date1).tz_localize(None)
    selected_date2_pd = pd.to_datetime(selected_date2).tz_localize(None)
    
    # Filter data up to selected date
    df1_filtered = df1[df1[date_column1] <= selected_date1_pd].copy()
    df2_filtered = df2[df2[date_column2] <= selected_date2_pd].copy()
    
    # Group by date and count
    daily1 = df1_filtered.groupby(df1_filtered[date_column1].dt.date).size().reset_index(name='count')
    daily2 = df2_filtered.groupby(df2_filtered[date_column2].dt.date).size().reset_index(name='count')
    
    # Rename date columns for consistency
    daily1.rename(columns={date_column1: 'Registration Date'}, inplace=True)
    daily2.rename(columns={date_column2: 'Registration Date'}, inplace=True)
    
    # Calculate cumulative sum
    daily1['cumulative'] = daily1['count'].cumsum()
    daily2['cumulative'] = daily2['count'].cumsum()
    
    # Create figure
    fig = go.Figure()
    
    # Add traces
    fig.add_trace(go.Scatter(
        x=daily1['Registration Date'],
        y=daily1['cumulative'],
        mode='lines+markers',
        name=str(year1),
        line=dict(width=3)
    ))
    
    fig.add_trace(go.Scatter(
        x=daily2['Registration Date'],
        y=daily2['cumulative'],
        mode='lines+markers',
        name=str(year2),
        line=dict(width=3)
    ))
    
    # Update layout
    fig.update_layout(
        title='Daily Cumulative Registrations',
        xaxis_title='Date',
        yaxis_title='Cumulative Registrations',
        hovermode='x unified',
        height=400
    )
    
    return fig

# File upload section
col1, col2 = st.columns(2)

with col1:
    st.subheader("📁 Upload First Year Data")
    file1 = st.file_uploader("Choose CSV file", type="csv", key="file1")
    if file1 is not None:
        try:
            df1 = pd.read_csv(file1)
            df1, date_col1 = parse_dates(df1)
            if df1 is not None:
                st.session_state.df1 = df1
                st.session_state.date_column1 = date_col1
                year1 = st.number_input("Enter year for this data:", min_value=2000, max_value=2030, value=2023, key="year1_input")
                st.session_state.year1 = year1
                st.success(f"✅ Loaded {len(df1)} records for year {year1}")
        except Exception as e:
            st.error(f"Error reading file: {str(e)}")

with col2:
    st.subheader("📁 Upload Second Year Data")
    file2 = st.file_uploader("Choose CSV file", type="csv", key="file2")
    if file2 is not None:
        try:
            df2 = pd.read_csv(file2)
            df2, date_col2 = parse_dates(df2)
            if df2 is not None:
                st.session_state.df2 = df2
                st.session_state.date_column2 = date_col2
                year2 = st.number_input("Enter year for this data:", min_value=2000, max_value=2030, value=2025, key="year2_input")
                st.session_state.year2 = year2
                st.success(f"✅ Loaded {len(df2)} records for year {year2}")
        except Exception as e:
            st.error(f"Error reading file: {str(e)}")

# Date selector and analysis
if (st.session_state.df1 is not None and st.session_state.df2 is not None and 
    st.session_state.date_column1 is not None and st.session_state.date_column2 is not None):
    
    st.markdown("---")
    st.subheader("📅 Select Analysis Date")
    
    date_col1 = st.session_state.date_column1
    date_col2 = st.session_state.date_column2
    
    # Find date range
    min_date1 = st.session_state.df1[date_col1].min()
    max_date1 = st.session_state.df1[date_col1].max()
    min_date2 = st.session_state.df2[date_col2].min()
    max_date2 = st.session_state.df2[date_col2].max()
    
    # Display date ranges for each file
    st.info(f"**{st.session_state.year1} data range**: {min_date1.strftime('%Y-%m-%d')} to {max_date1.strftime('%Y-%m-%d')}")
    st.info(f"**{st.session_state.year2} data range**: {min_date2.strftime('%Y-%m-%d')} to {max_date2.strftime('%Y-%m-%d')}")
    
    # Check if date ranges overlap
    if max_date1 < min_date2 or max_date2 < min_date1:
        st.warning("⚠️ The date ranges in your files don't overlap. Showing comparison for the same relative dates.")
        
        # For non-overlapping ranges, allow selection within each file's range
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"**Select date for {st.session_state.year1}:**")
            selected_date1 = st.date_input(
                f"{st.session_state.year1} comparison date:",
                value=max_date1,
                min_value=min_date1,
                max_value=max_date1,
                key="date1"
            )
        
        with col2:
            st.markdown(f"**Select date for {st.session_state.year2}:**")
            selected_date2 = st.date_input(
                f"{st.session_state.year2} comparison date:",
                value=max_date2,
                min_value=min_date2,
                max_value=max_date2,
                key="date2"
            )
        
        # Calculate days from start for each
        days_from_start1 = (selected_date1 - min_date1.date()).days
        days_from_start2 = (selected_date2 - min_date2.date()).days
        
        st.info(f"Comparing day {days_from_start1} of {st.session_state.year1} with day {days_from_start2} of {st.session_state.year2}")
        
    else:
        # Use the latest min date and earliest max date for the selector
        min_date = max(min_date1, min_date2)
        max_date = min(max_date1, max_date2)
        
        selected_date = st.date_input(
            "Select date for comparison:",
            value=max_date,
            min_value=min_date,
            max_value=max_date
        )
        
        selected_date1 = selected_date
        selected_date2 = selected_date
    
    # Calculate KPIs
    kpis1 = calculate_kpis(st.session_state.df1, selected_date1, date_col1)
    kpis2 = calculate_kpis(st.session_state.df2, selected_date2, date_col2)
    
    # Display KPIs
    st.markdown("---")
    st.subheader("📊 KPI Comparison")
    if 'selected_date' in locals():
        st.markdown(f"**Data as of {selected_date}**")
    else:
        st.markdown(f"**{st.session_state.year1}** as of {selected_date1} | **{st.session_state.year2}** as of {selected_date2}")
    
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
        selected_date1,
        selected_date2,
        date_col1,
        date_col2
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Summary statistics
    st.markdown("---")
    st.subheader("📋 Summary Statistics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"**{st.session_state.year1} Summary**")
        summary_df1 = pd.DataFrame(list(kpis1.items()), columns=['KPI', 'Value'])
        st.dataframe(summary_df1, use_container_width=True)
    
    with col2:
        st.markdown(f"**{st.session_state.year2} Summary**")
        summary_df2 = pd.DataFrame(list(kpis2.items()), columns=['KPI', 'Value'])
        st.dataframe(summary_df2, use_container_width=True)

else:
    st.info("👆 Please upload both CSV files to begin the comparison")

# Instructions
with st.expander("ℹ️ How to use this app"):
    st.markdown("""
    1. **Upload Files**: Upload two CSV files containing registration data
    2. **Label Years**: Specify which year each file represents
    3. **Select Date**: Choose a date to compare registrations up to that point
    4. **View Results**: Examine KPIs, percentage changes, and trend charts
    
    **Expected CSV Columns:**
    - Date column: `Last Registration Date (GMT)` or similar variations
    - `Title`: Job title (for senior leader identification)
    - `My Gender is:`: Gender information
    - `Company Name`: Organization name
    - `Primary State/Prov. Code`: State/Province code
    - `Job Classification`: Job role classification
    - `Registration Type`: Type of registration
    
    **KPI Definitions:**
    - **Attendees**: Total registrations with valid dates
    - **Senior Leaders**: Titles containing Chief, VP, President, Director, Head, Founder, or Dean
    - **Women Leaders**: Senior leaders with gender marked as Female
    - **Institutions**: Unique organizations
    - **Community Colleges**: Organizations with "Community College" or "CC" in name
    - **Regions (States/Provinces)**: All unique state/province codes (includes international)
    - **U.S. States Only**: Count of valid U.S. state codes (50 states + DC)
    
    **Note**: The app will automatically detect your date column from common naming conventions.
    """)