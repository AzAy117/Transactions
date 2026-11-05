import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime
import io

# Page configuration for mobile responsiveness
st.set_page_config(page_title="Transactions", page_icon="📊", layout="centered")

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

# Calculate Totals
total = sum([float(t["amount"]) for t in data]) if data else 0
total_takes = sum([float(t["amount"]) for t in data if float(t["amount"]) > 0]) if data else 0
total_gives = sum([float(t["amount"]) for t in data if float(t["amount"]) < 0]) if data else 0

# --- TOTAL BALANCE & GIVES/TAKES CARDS (CENTERED) ---
st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
st.subheader("Total Balance")
if total >= 0:
    st.markdown(f"<h1 style='color: #2e7d32; margin-top: -10px;'>₹{total:.2f}</h1>", unsafe_allow_html=True)
else:
    st.markdown(f"<h1 style='color: #c62828; margin-top: -10px;'>-₹{abs(total):.2f}</h1>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# Gives and Takes Summary Boxes
col_t1, col_t2 = st.columns(2)
with col_t1:
    st.markdown(
        f"""
        <div style='background-color: #ffebee; padding: 10px; border-radius: 8px; text-align: center; border: 1px solid #ffcdd2;'>
            <p style='margin: 0; color: #c62828; font-weight: bold; font-size: 13px;'>Total Gives</p>
            <p style='margin: 3px 0 0 0; color: #c62828; font-size: 18px; font-weight: bold;'>₹{abs(total_gives):.2f}</p>
        </div>
        """,
        unsafe_allow_html=True
    )
with col_t2:
    st.markdown(
        f"""
        <div style='background-color: #e8f5e9; padding: 10px; border-radius: 8px; text-align: center; border: 1px solid #c8e6c9;'>
            <p style='margin: 0; color: #2e7d32; font-weight: bold; font-size: 13px;'>Total Takes</p>
            <p style='margin: 3px 0 0 0; color: #2e7d32; font-size: 18px; font-weight: bold;'>₹{total_takes:.2f}</p>
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown("---")

# --- MONTHLY SUMMARY SECTION UNDER BALANCE ---
st.write("### 📅 Monthly Summary")
if data:
    df_sum = pd.DataFrame(data)
    df_sum['dt'] = pd.to_datetime(df_sum['date'])
    df_sum['year'] = df_sum['dt'].dt.year
    df_sum['month_name'] = df_sum['dt'].dt.strftime('%B %Y')
    df_sum['month_num'] = df_sum['dt'].dt.to_period('M')

    years = sorted(df_sum['year'].unique(), reverse=True)
    sel_year = st.selectbox("Select Year", years, label_visibility="collapsed")

    if sel_year:
        y_data = df_sum[df_sum['year'] == sel_year]
        monthly_summary = (
            y_data.groupby(['month_num', 'month_name'])['amount']
            .sum()
            .reset_index()
            .sort_values('month_num')
        )

        cards_html = "<div style='display: flex; overflow-x: auto; gap: 10px; padding: 5px 0;'>"
        for _, m_row in monthly_summary.iterrows():
            m_amt = float(m_row['amount'])
            color = "#2e7d32" if m_amt >= 0 else "#c62828"
            cards_html += f"""
            <div style='min-width: 130px; background: #ffffff; padding: 10px; border-radius: 6px; border: 1px solid #ddd; text-align: center; color: #000;'>
                <p style='margin:0; font-size:12px; color:#555;'>{m_row['month_name']}</p>
                <p style='font-size:15px; font-weight:bold; color:{color}; margin:5px 0 0 0;'>₹{m_amt:.2f}</p>
            </div>
            """
        cards_html += "</div>"
        st.markdown(cards_html, unsafe_allow_html=True)

st.markdown("---")

# --- ADD / EDIT TRANSACTION SECTION ---
st.write("### Add / Edit Transaction")

edit_id = st.session_state.get("edit_id", None)
edit_item = next((t for t in data if t["id"] == edit_id), None) if edit_id else None

default_date = datetime.strptime(edit_item["date"], "%Y-%m-%d").date() if edit_item else datetime.today()
default_amount = float(edit_item["amount"]) if edit_item else 0.0
default_reason = edit_item["reason"] if edit_item else ""

with st.form("transaction_form", clear_on_submit=True):
    date_val = st.date_input("Date", value=default_date)
    amount_val = st.number_input("Amount (use negative for give/expense)", value=default_amount, step=0.01)
    reason_val = st.text_input("Reason / Description", value=default_reason)
    uploaded_file = st.file_uploader("Screenshot / Receipt (Optional)", type=["png", "jpg", "jpeg"])

    btn_label = "Update Transaction" if edit_item else "Add Transaction"
    submitted = st.form_submit_button(btn_label, use_container_width=True)

    if submitted:
        if not reason_val:
            st.error("Please enter a reason.")
        else:
            image_url = edit_item["screenshot"] if edit_item else ""
            
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
                supabase.table("transactions").update(payload).eq("id", edit_id).execute()
                st.success("Transaction updated successfully!")
                st.session_state["edit_id"] = None
            else:
                supabase.table("transactions").insert(payload).execute()
                st.success("Transaction added successfully!")
            
            st.rerun()

if edit_id:
    if st.button("Cancel Edit", use_container_width=True):
        st.session_state["edit_id"] = None
        st.rerun()

st.markdown("---")

# --- TRANSACTION HISTORY & EXPORT ---
col_h1, col_h2 = st.columns([2, 1])
with col_h1:
    st.write("### History")
with col_h2:
    if data:
        df_export = pd.DataFrame(data)[["date", "amount", "reason", "screenshot"]]
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_export.to_excel(writer, index=False, sheet_name='Transactions')
        st.download_button(
            label="📥 Export Excel",
            data=buffer.getvalue(),
            file_name=f"Transactions_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

if data:
    df_hist = pd.DataFrame(data)
    df_hist['dt'] = pd.to_datetime(df_hist['date'])
    df_hist['year_month'] = df_hist['dt'].dt.to_period('M')
    
    # Alternating monthly background colors
    unique_months = df_hist['year_month'].unique()
    month_bg_map = {}
    for idx, m in enumerate(unique_months):
        month_bg_map[m] = "#ffffff" if idx % 2 == 0 else "#f1f3f5"

    for _, row in df_hist.iterrows():
        m_key = row['year_month']
        row_bg = month_bg_map.get(m_key, "#ffffff")
        
        amt = float(row["amount"])
        amt_str = f"₹{amt:.2f}"
        amt_color = "green" if amt >= 0 else "red"

        # Mobile friendly container card
        st.markdown(
            f"""
            <div style="background-color: {row_bg}; border: 1px solid #dcdcdc; padding: 12px; border-radius: 8px; margin-bottom: 8px; color: #000000;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                    <span style="font-size: 13px; color: #555;">📅 {row["date"]}</span>
                    <span style="font-size: 16px; font-weight: bold; color: {amt_color};">{amt_str}</span>
                </div>
                <div style="font-size: 15px; font-weight: 500; margin-bottom: 6px;">{row["reason"]}</div>
            """,
            unsafe_allow_html=True
        )

        if row["screenshot"]:
            st.markdown(f"<a href='{row['screenshot']}' target='_blank' style='font-size: 12px;'>🔗 View Receipt</a>", unsafe_allow_html=True)

        col_b1, col_b2 = st.columns(2)
        with col_b1:
            if st.button("✏️ Edit", key=f"edit_{row['id']}", use_container_width=True):
                st.session_state["edit_id"] = row["id"]
                st.rerun()
        with col_b2:
            if st.button("🗑️ Delete", key=f"del_btn_{row['id']}", use_container_width=True):
                st.session_state[f"confirm_del_{row['id']}"] = True
                st.rerun()

        # Delete Confirmation Prompt inside card
        if st.session_state.get(f"confirm_del_{row['id']}", False):
            st.warning("Are you sure you want to delete?")
            d_col1, d_col2 = st.columns(2)
            if d_col1.button("Yes", key=f"yes_del_{row['id']}", use_container_width=True):
                supabase.table("transactions").delete().eq("id", row["id"]).execute()
                st.session_state[f"confirm_del_{row['id']}"] = False
                st.rerun()
            if d_col2.button("No", key=f"cancel_del_{row['id']}", use_container_width=True):
                st.session_state[f"confirm_del_{row['id']}"] = False
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)
else:
    st.info("No transactions found yet.")
