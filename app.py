import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime
import io

# Page configuration
st.set_page_config(page_title="Transactions Tracker", page_icon="📊", layout="wide")

# Supabase Credentials initialization from st.secrets
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "https://ozstskgokzppbfbbubyp.supabase.co")
SUPABASE_KEY = st.secrets.get("SUPABASE_ANON_KEY", "sb_publishable_JDP0BufPA7MpgLSi8wffMg_i7_64gVO")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Please configure your SUPABASE_URL and SUPABASE_ANON_KEY in Streamlit Secrets.")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("📊 Transactions Tracker")

# Fetch data from Supabase
def fetch_data():
    try:
        response = supabase.table("transactions").select("*").order("date", desc=False).execute()
        rows = response.data or []
        for r in rows:
            if "type" not in r or not r["type"]:
                r["type"] = "Sent"
        return rows
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return []

data = fetch_data()

# Calculate Totals strictly based on 'type'
total_takes = sum([float(t["amount"]) for t in data if t.get("type") == "Received"]) if data else 0
total_gives = sum([float(t["amount"]) for t in data if t.get("type") == "Sent"]) if data else 0
total = total_takes - total_gives

# --- TOTAL BALANCE & SUMMARY ---
st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
st.subheader("Total Balance")
if total >= 0:
    st.markdown(f"<h1 style='color: #2e7d32; margin-top: -10px;'>₹{total:.2f}</h1>", unsafe_allow_html=True)
else:
    st.markdown(f"<h1 style='color: #c62828; margin-top: -10px;'>-₹{abs(total):.2f}</h1>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

col_t1, col_t2 = st.columns(2)
with col_t1:
    st.markdown(
        f"""
        <div style='background-color: #ffebee; padding: 12px; border-radius: 8px; text-align: center; border: 1px solid #ffcdd2;'>
            <p style='margin: 0; color: #c62828; font-weight: bold; font-size: 13px;'>Total Gives (Sent)</p>
            <p style='margin: 3px 0 0 0; color: #c62828; font-size: 18px; font-weight: bold;'>₹{total_gives:.2f}</p>
        </div>
        """,
        unsafe_allow_html=True
    )
with col_t2:
    st.markdown(
        f"""
        <div style='background-color: #e8f5e9; padding: 12px; border-radius: 8px; text-align: center; border: 1px solid #c8e6c9;'>
            <p style='margin: 0; color: #2e7d32; font-weight: bold; font-size: 13px;'>Total Takes (Received)</p>
            <p style='margin: 3px 0 0 0; color: #2e7d32; font-size: 18px; font-weight: bold;'>₹{total_takes:.2f}</p>
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown("---")

# --- MONTHLY SUMMARY SECTION ---
st.write("### 📅 Monthly Summary")
if data:
    df_sum = pd.DataFrame(data)
    df_sum['dt'] = pd.to_datetime(df_sum['date'])
    df_sum['year'] = df_sum['dt'].dt.year
    df_sum['month_name'] = df_sum['dt'].dt.strftime('%B %Y')
    df_sum['month_num'] = df_sum['dt'].dt.to_period('M').astype(str)

    years = sorted(df_sum['year'].unique(), reverse=True)
    sel_year = st.selectbox("Select Year", years, label_visibility="collapsed")

    if sel_year:
        y_data = df_sum[df_sum['year'] == sel_year]
        
        # Calculate net monthly amount (Received - Sent)
        def calc_net(group):
            received = group[group['type'] == 'Received']['amount'].sum()
            sent = group[group['type'] == 'Sent']['amount'].sum()
            return received - sent

        monthly_summary = []
        for (m_num, m_name), group in y_data.groupby(['month_num', 'month_name']):
            net_amt = calc_net(group)
            monthly_summary.append({'month_num': m_num, 'month_name': m_name, 'amount': net_amt})
        
        monthly_summary = pd.DataFrame(monthly_summary).sort_values('month_num')

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
default_type = edit_item.get("type", "Sent") if edit_item else "Sent"

with st.form("transaction_form", clear_on_submit=True):
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        date_val = st.date_input("Date", value=default_date)
    with col_f2:
        amount_val = st.number_input("Amount", value=default_amount, step=0.01, min_value=0.0)
    with col_f3:
        reason_val = st.text_input("Reason", value=default_reason)
    with col_f4:
        type_val = st.selectbox("Type", ["Sent", "Received"], index=0 if default_type == "Sent" else 1)

    uploaded_file = st.file_uploader("Screenshot / Receipt (Optional)", type=["png", "jpg", "jpeg"])

    btn_label = "Update Transaction" if edit_item else "Add Transaction"
    submitted = st.form_submit_button(btn_label, use_container_width=True)

    if submitted:
        image_url = edit_item.get("screenshot", "") if edit_item else ""
        
        if uploaded_file is not None:
            try:
                file_ext = uploaded_file.name.split(".")[-1]
                file_path = f"{int(datetime.now().timestamp())}.{file_ext}"
                supabase.storage.from_("screenshots").upload(file_path, uploaded_file.getvalue())
                image_url = supabase.storage.from_("screenshots").get_public_url(file_path)
            except Exception as img_err:
                st.warning(f"Failed to upload image: {img_err}")

        payload = {
            "date": str(date_val),
            "amount": amount_val,
            "reason": reason_val,
            "type": type_val,
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

if data:
    df_table = pd.DataFrame(data)
    df_table['dt'] = pd.to_datetime(df_table['date'])
    df_table['year_month'] = df_table['dt'].dt.to_period('M').astype(str)

    unique_months = df_table['year_month'].unique()
    month_bg_map = {}
    for idx, m in enumerate(unique_months):
        # Alternate background colors for months/entries distinction
        month_bg_map[m] = "#f9f9f9" if idx % 2 == 0 else "#f0f4f8"

    st.write("### Transactions History")
    st.markdown("<hr style='margin: 5px 0 10px 0;'>", unsafe_allow_html=True)

    for idx, row in df_table.iterrows():
        t_type = row.get("type", "Sent")
        type_color = "#c62828" if t_type == "Sent" else "#2e7d32"
        bg_col = month_bg_map.get(row['year_month'], "#ffffff")
        
        # Clean mobile-friendly card design
        st.markdown(
            f"""
            <div style="background-color: {bg_col}; padding: 12px; border-radius: 8px; margin-bottom: 10px; border: 1px solid #d3d3d3; color: #000;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                    <span style="font-size: 13px; color: #555; font-weight: bold;">📅 {row['date']}</span>
                    <span style="background-color: {type_color}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: bold;">{t_type}</span>
                </div>
                <div style="font-size: 18px; font-weight: bold; color: #000; margin-bottom: 4px;">₹{float(row['amount']):.2f}</div>
                <div style="font-size: 14px; color: #333; margin-bottom: 8px;"><b>Reason:</b> {row['reason'] or '-'}</div>
            """,
            unsafe_allow_html=True
        )
        
        # Receipt link if available
        if row.get("screenshot"):
            st.markdown(f"📎 [View Receipt]({row['screenshot']})")

        # Action buttons inside columns for edit/delete
        col_act1, col_act2 = st.columns(2)
        with col_act1:
            if st.button("✏️ Edit", key=f"edit_{row['id']}", use_container_width=True):
                st.session_state["edit_id"] = row["id"]
                st.rerun()
        with col_act2:
            if st.button("🗑️ Delete", key=f"del_btn_{row['id']}", use_container_width=True):
                st.session_state[f"confirm_del_{row['id']}"] = True
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

        if st.session_state.get(f"confirm_del_{row['id']}", False):
            st.warning(f"Delete transaction for '{row.get('reason', '')}'?")
            d1, d2 = st.columns(2)
            if d1.button("Yes, Delete", key=f"yes_del_{row['id']}"):
                supabase.table("transactions").delete().eq("id", row["id"]).execute()
                st.session_state[f"confirm_del_{row['id']}"] = False
                st.rerun()
            if d2.button("Cancel", key=f"cancel_del_{row['id']}"):
                st.session_state[f"confirm_del_{row['id']}"] = False
                st.rerun()
else:
    st.info("No transactions found yet.")
