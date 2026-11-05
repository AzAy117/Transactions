import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime
import io

# Page configuration
st.set_page_config(page_title="Transactions", page_icon="📊", layout="wide")

# Supabase Credentials initialization
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "https://ozstskgokzppbfbbubyp.supabase.co")
SUPABASE_KEY = st.secrets.get("SUPABASE_ANON_KEY", "sb_publishable_JDP0BufPA7MpgLSi8wffMg_i7_64gVO")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Please configure your Supabase URL and API Key in the Streamlit Secrets settings.")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("📊 Transactions")

# Fetch data from Supabase
def fetch_data():
    try:
        response = supabase.table("transactions").select("*").order("date", desc=True).execute()
        return response.data or []
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return []

data = fetch_data()

# Tabs structure
tab1, tab2 = st.tabs(["📝 Transactions", "📅 Yearly Summary"])

# --- TAB 1: TRANSACTIONS & ADD/EDIT ---
with tab1:
    # Total Balance Header
    total = sum([float(t["amount"]) for t in data]) if data else 0
    if total >= 0:
        st.subheader(f"Total Balance: ₹{total:.2f}")
    else:
        st.subheader(f"Total Balance: -₹{abs(total):.2f}")

    st.markdown("---")

    # Add / Edit Transaction Section
    st.write("### Add / Edit Transaction")
    
    # Check if we are in edit mode
    edit_id = st.session_state.get("edit_id", None)
    edit_item = next((t for t in data if t["id"] == edit_id), None) if edit_id else None

    default_date = datetime.strptime(edit_item["date"], "%Y-%m-%d").date() if edit_item else datetime.today()
    default_amount = float(edit_item["amount"]) if edit_item else 0.0
    default_reason = edit_item["reason"] if edit_item else ""

    with st.form("transaction_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            date_val = st.date_input("Date", value=default_date)
            amount_val = st.number_input("Amount (use negative for debit/expense)", value=default_amount, step=0.01)
        with col2:
            reason_val = st.text_input("Reason / Description", value=default_reason)
            uploaded_file = st.file_uploader("Screenshot / Receipt (Optional)", type=["png", "jpg", "jpeg"])

        btn_label = "Update Transaction" if edit_item else "Add Transaction"
        submitted = st.form_submit_button(btn_label)

        if submitted:
            if not reason_val:
                st.error("Please enter a reason.")
            else:
                image_url = edit_item["screenshot"] if edit_item else ""
                
                # Upload Image if selected
                if uploaded_file is not None:
                    try:
                        file_ext = uploaded_file.name.split(".")[-1]
                        file_path = f"{datetime.now().timestamp()}.{file_ext}"
                        
                        supabase.storage.from_("screenshots").upload(file_path, uploaded_file.getvalue())
                        image_url = supabase.storage.from_("screenshots").get_public_url(file_path)
                    except Exception as img_err:
                        st.warning(f"Failed to upload image: {img_err}")

                payload = {
                    "date": str(date_val),
                    "amount": amount_val,
                    "reason": reason_val,
                    "screenshot": image_url
                }

                if edit_item:
                    # Update existing record
                    supabase.table("transactions").update(payload).eq("id", edit_id).execute()
                    st.success("Transaction updated successfully!")
                    st.session_state["edit_id"] = None
                else:
                    # Insert new record
                    supabase.table("transactions").insert(payload).execute()
                    st.success("Transaction added successfully!")
                
                st.rerun()

    if edit_id:
        if st.button("Cancel Edit"):
            st.session_state["edit_id"] = None
            st.rerun()

    st.markdown("---")

    # Export to Excel & History Header
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.write("### Transaction History")
    with col_h2:
        if data:
            df_export = pd.DataFrame(data)[["date", "amount", "reason", "screenshot"]]
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_export.to_excel(writer, index=False, sheet_name='Transactions')
            st.download_button(
                label="📥 Export to Excel",
                data=buffer.getvalue(),
                file_name=f"Transactions_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    # Display list with monthly alternating colors
    if data:
        df = pd.DataFrame(data)
        df['dt'] = pd.to_datetime(df['date'])
        df['year_month'] = df['dt'].dt.to_period('M')

        # Get unique months to assign alternating colors
        unique_months = df['year_month'].unique()
        month_color_map = {}
        for idx, month in enumerate(unique_months):
            # Alternating light colors: light grey / light blue-grey
            month_color_map[month] = "#f9f9f9" if idx % 2 == 0 else "#ffffff"

        # Table Header
        h_col1, h_col2, h_col3, h_col4, h_col5 = st.columns([2, 2, 4, 2, 2])
        h_col1.markdown("**Date**")
        h_col2.markdown("**Amount**")
        h_col3.markdown("**Reason**")
        h_col4.markdown("**Screenshot**")
        h_col5.markdown("**Actions**")

        for _, row in df.iterrows():
            bg_color = month_color_map[row['year_month']]
            container = st.container()
            
            with container:
                st.markdown(
                    f"""
                    <div style="background-color: {bg_color}; padding: 8px; border-radius: 5px; margin-bottom: 4px;">
                    """,
                    unsafe_allow_html=True
                )
                c1, c2, c3, c4, c5 = st.columns([2, 2, 4, 2, 2])
                c1.write(str(row["date"]))
                
                amt = float(row["amount"])
                amt_str = f"₹{amt:.2f}"
                if amt >= 0:
                    c2.markdown(f"<span style='color:green; font-weight:bold;'>{amt_str}</span>", unsafe_allow_html=True)
                else:
                    c2.markdown(f"<span style='color:red; font-weight:bold;'>{amt_str}</span>", unsafe_allow_html=True)
                
                c3.write(row["reason"])
                
                if row["screenshot"]:
                    c4.markdown(f"[View Image]({row['screenshot']})", unsafe_allow_html=True)
                else:
                    c4.write("-")
                
                with c5:
                    col_e, col_d = st.columns(2)
                    if col_e.button("✏️", key=f"edit_{row['id']}"):
                        st.session_state["edit_id"] = row["id"]
                        st.rerun()
                    if col_d.button("🗑️", key=f"del_{row['id']}"):
                        supabase.table("transactions").delete().eq("id", row["id"]).execute()
                        st.success("Deleted!")
                        st.rerun()
                
                st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("No transactions found yet.")

# --- TAB 2: YEARLY & MONTHLY SUMMARY ---
with tab2:
    st.write("### Yearly & Monthly Overview")
    if data:
        df_summary = pd.DataFrame(data)
        df_summary['dt'] = pd.to_datetime(df_summary['date'])
        df_summary['year'] = df_summary['dt'].dt.year
        df_summary['month_name'] = df_summary['dt'].dt.strftime('%B')
        df_summary['month_num'] = df_summary['dt'].dt.month

        years = sorted(df_summary['year'].unique(), reverse=True)
        selected_year = st.selectbox("Select Year", years)

        if selected_year:
            year_data = df_summary[df_summary['year'] == selected_year]
            year_total = year_data['amount'].astype(float).sum()

            st.metric(label=f"Total Balance for {selected_year}", value=f"₹{year_total:.2f}")

            st.write("#### Monthly Breakdown (Scroll horizontally if needed)")
            
            # Monthly summary aggregation
            monthly_summary = (
                year_data.groupby(['month_num', 'month_name'])['amount']
                .sum()
                .reset_index()
                .sort_values('month_num')
            )

            # Horizontal Scroll Card Layout
            cards_html = "<div style='display: flex; overflow-x: auto; gap: 15px; padding: 10px 0;'>"
            for _, m_row in monthly_summary.iterrows():
                m_amt = float(m_row['amount'])
                color = "green" if m_amt >= 0 else "red"
                cards_html += f"""
                <div style='min-width: 160px; background: #ffffff; padding: 15px; border-radius: 8px; border: 1px solid #ddd; text-align: center; box-shadow: 2px 2px 5px rgba(0,0,0,0.05);'>
                    <h5 style='margin:0; color:#555;'>{m_row['month_name']}</h5>
                    <p style='font-size:18px; font-weight:bold; color:{color}; margin:10px 0 0 0;'>₹{m_amt:.2f}</p>
                </div>
                """
            cards_html += "</div>"
            
            st.markdown(cards_html, unsafe_allow_html=True)
    else:
        st.info("No data available for summary.")
