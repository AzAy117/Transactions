import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime

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

# Handle query parameters for table-based actions
query_params = st.query_params
if "edit_id" in query_params:
    st.session_state["active_edit_id"] = query_params["edit_id"]
if "del_id" in query_params:
    st.session_state["active_del_id"] = query_params["del_id"]

# Fetch data from Supabase
def fetch_data():
    try:
        response = supabase.table("transactions").select("*").order("date", desc=False).execute()
        rows = response.data or []
        for r in rows:
            amt = float(r.get("amount", 0))
            r["type"] = "Sent" if amt >= 0 else "Received"
        return rows
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return []

data = fetch_data()

# Calculate Totals (Sent = Gives, Received = Takes)
total_gives = sum([abs(float(t["amount"])) for t in data if t.get("type") == "Sent"]) if data else 0
total_takes = sum([abs(float(t["amount"])) for t in data if t.get("type") == "Received"]) if data else 0

# Correct Balance Calculation: Received (Takes) - Sent (Gives)
total = total_takes - total_gives

# --- TOTAL BALANCE & SUMMARY (Centered Alignment) ---
st.markdown("<div style='text-align: center; width: 100%; margin-bottom: 20px;'>", unsafe_allow_html=True)
st.subheader("Total Balance")
if total >= 0:
    st.markdown(f"<h1 style='color: #2e7d32; margin-top: -5px; text-align: center;'>₹{total:.2f}</h1>", unsafe_allow_html=True)
else:
    st.markdown(f"<h1 style='color: #c62828; margin-top: -5px; text-align: center;'>-₹{abs(total):.2f}</h1>", unsafe_allow_html=True)
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
        
        def calc_net(group):
            received = group[group['type'] == 'Received']['amount'].apply(lambda x: abs(float(x))).sum()
            sent = group[group['type'] == 'Sent']['amount'].apply(lambda x: abs(float(x))).sum()
            return received - sent

        monthly_summary = []
        for (m_num, m_name), group in y_data.groupby(['month_num', 'month_name']):
            net_amt = calc_net(group)
            monthly_summary.append({'month_num': m_num, 'month_name': m_name, 'amount': net_amt})
        
        monthly_summary = pd.DataFrame(monthly_summary).sort_values('month_num')

        if not monthly_summary.empty:
            m_cols = st.columns(len(monthly_summary))
            for i, (_, m_row) in enumerate(monthly_summary.iterrows()):
                m_amt = float(m_row['amount'])
                color = "#2e7d32" if m_amt >= 0 else "#c62828"
                with m_cols[i]:
                    st.markdown(
                        f"""
                        <div style='background: #ffffff; padding: 10px; border-radius: 6px; border: 1px solid #ddd; text-align: center; color: #000;'>
                            <p style='margin:0; font-size:12px; color:#555;'>{m_row['month_name']}</p>
                            <p style='font-size:15px; font-weight:bold; color:{color}; margin:5px 0 0 0;'>₹{m_amt:.2f}</p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

st.markdown("---")

# --- ACTIVE EDIT OR DELETE POPUP SECTION AT THE TOP ---
active_edit_id = st.session_state.get("active_edit_id")
active_del_id = st.session_state.get("active_del_id")

if active_edit_id:
    edit_item = next((t for t in data if str(t["id"]) == str(active_edit_id)), None)
    if edit_item:
        st.info(f"✏️ Editing transaction: {edit_item.get('reason', '')} (₹{edit_item.get('amount')})")
        with st.form("edit_transaction_form"):
            try:
                def_date = datetime.strptime(edit_item["date"], "%Y-%m-%d").date()
            except:
                def_date = datetime.today()
            def_amount = float(edit_item["amount"])
            def_reason = edit_item["reason"] or ""

            e_col1, e_col2, e_col3, e_col4 = st.columns(4)
            with e_col1:
                new_date = st.date_input("Date", value=def_date)
            with e_col2:
                new_amount = st.number_input("Amount", value=def_amount, step=0.01)
            with e_col3:
                new_reason = st.text_input("Reason", value=def_reason)
            with e_col4:
                auto_type = "Sent" if new_amount >= 0 else "Received"
                st.write(f"**Type:** {auto_type} (auto)")

            new_file = st.file_uploader("Replace Receipt (Optional)", type=["png", "jpg", "jpeg"])
            
            sub_col1, sub_col2 = st.columns(2)
            with sub_col1:
                update_submitted = st.form_submit_button("Update Transaction", use_container_width=True)
            with sub_col2:
                cancel_edit = st.form_submit_button("Cancel", use_container_width=True)

            if cancel_edit:
                st.session_state["active_edit_id"] = None
                st.query_params.clear()
                st.rerun()

            if update_submitted:
                image_url = edit_item.get("screenshot", "")
                if new_file is not None:
                    try:
                        file_ext = new_file.name.split(".")[-1]
                        file_path = f"{int(datetime.now().timestamp())}.{file_ext}"
                        supabase.storage.from_("screenshots").upload(file_path, new_file.getvalue())
                        image_url = supabase.storage.from_("screenshots").get_public_url(file_path)
                    except Exception as img_err:
                        st.warning(f"Failed to upload image: {img_err}")

                final_type = "Sent" if new_amount >= 0 else "Received"
                payload = {
                    "date": str(new_date),
                    "amount": new_amount,
                    "reason": new_reason,
                    "type": final_type,
                    "screenshot": image_url
                }

                supabase.table("transactions").update(payload).eq("id", active_edit_id).execute()
                st.success("Transaction updated successfully!")
                st.session_state["active_edit_id"] = None
                st.query_params.clear()
                st.rerun()

if active_del_id:
    del_item = next((t for t in data if str(t["id"]) == str(active_del_id)), None)
    if del_item:
        st.warning(f"Do you want to delete this transaction for '{del_item.get('reason', '')}' (₹{del_item.get('amount')})?")
        d_col1, d_col2 = st.columns(2)
        with d_col1:
            if st.button("Yes, Delete", use_container_width=True, key="confirm_del_btn"):
                supabase.table("transactions").delete().eq("id", active_del_id).execute()
                st.success("Transaction deleted successfully!")
                st.session_state["active_del_id"] = None
                st.query_params.clear()
                st.rerun()
        with d_col2:
            if st.button("Cancel", use_container_width=True, key="cancel_del_btn"):
                st.session_state["active_del_id"] = None
                st.query_params.clear()
                st.rerun()

# --- ADD TRANSACTION SECTION ---
st.write("### Add New Transaction")

with st.form("transaction_form", clear_on_submit=True):
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        date_val = st.date_input("Date", value=datetime.today())
    with col_f2:
        amount_val = st.number_input("Amount", value=0.0, step=0.01)
    with col_f3:
        reason_val = st.text_input("Reason", value="")
    with col_f4:
        auto_type = "Sent" if amount_val >= 0 else "Received"
        st.write(f"**Type:** {auto_type} (auto)")

    uploaded_file = st.file_uploader("Screenshot / Receipt (Optional)", type=["png", "jpg", "jpeg"])

    submitted = st.form_submit_button("Add Transaction", use_container_width=True)

    if submitted:
        image_url = ""
        if uploaded_file is not None:
            try:
                file_ext = uploaded_file.name.split(".")[-1]
                file_path = f"{int(datetime.now().timestamp())}.{file_ext}"
                supabase.storage.from_("screenshots").upload(file_path, uploaded_file.getvalue())
                image_url = supabase.storage.from_("screenshots").get_public_url(file_path)
            except Exception as img_err:
                st.warning(f"Failed to upload image: {img_err}")

        final_type = "Sent" if amount_val >= 0 else "Received"
        payload = {
            "date": str(date_val),
            "amount": amount_val,
            "reason": reason_val,
            "type": final_type,
            "screenshot": image_url
        }

        supabase.table("transactions").insert(payload).execute()
        st.success("Transaction added successfully!")
        st.rerun()

st.markdown("---")

# --- HORIZONTAL SCROLLABLE SPREADSHEET TABLE WITH EMBEDDED EDIT/DELETE/RECEIPT ---
st.write("### Transactions Spreadsheet")

if data:
    df_table = pd.DataFrame(data)
    bg_colors = ["#e6f2ff", "#f3e8ff"] # 2 alternating colors: light blue & pinkish/purple

    table_html = """<div style="overflow-x: auto; width: 100%;">
<table style="width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 14px; color: #000; min-width: 600px;">
    <thead>
        <tr style="background-color: #262730; color: white; text-align: left;">
            <th style="padding: 10px; border: 1px solid #d3d3d3;">Date</th>
            <th style="padding: 10px; border: 1px solid #d3d3d3;">Amount</th>
            <th style="padding: 10px; border: 1px solid #d3d3d3;">Reason</th>
            <th style="padding: 10px; border: 1px solid #d3d3d3;">Type</th>
            <th style="padding: 10px; border: 1px solid #d3d3d3; text-align: center;">Receipt</th>
            <th style="padding: 10px; border: 1px solid #d3d3d3; text-align: center;">Edit</th>
            <th style="padding: 10px; border: 1px solid #d3d3d3; text-align: center;">Delete</th>
        </tr>
    </thead>
    <tbody>"""

    for idx, row in df_table.iterrows():
        amount_val = float(row['amount'])
        t_type = "Sent" if amount_val >= 0 else "Received"
        badge_bg = "#2e7d32" if t_type == "Sent" else "#c62828"
        
        amount_color = "#2e7d32" if amount_val < 0 else "#c62828"
        row_bg = bg_colors[idx % len(bg_colors)]
        
        receipt_link = f"<a href='{row['screenshot']}' target='_blank'>View</a>" if row.get("screenshot") else "-"
        
        table_html += f"""<tr style="background-color: {row_bg};">
    <td style="padding: 9px 10px; border: 1px solid #d3d3d3; color: #000;">{row['date']}</td>
    <td style="padding: 9px 10px; border: 1px solid #d3d3d3;"><b style="color: {amount_color};">₹{amount_val:.2f}</b></td>
    <td style="padding: 9px 10px; border: 1px solid #d3d3d3; color: #000;">{row['reason'] or '-'}</td>
    <td style="padding: 9px 10px; border: 1px solid #d3d3d3;"><span style="background-color: {badge_bg}; color: white; padding: 3px 10px; border-radius: 10px; font-weight: bold; font-size: 11px;">{t_type}</span></td>
    <td style="padding: 9px 10px; border: 1px solid #d3d3d3; text-align: center;">{receipt_link}</td>
    <td style="padding: 9px 10px; border: 1px solid #d3d3d3; text-align: center;"><a href="?edit_id={row['id']}" target="_self" style="text-decoration: none;">✏️ Edit</a></td>
    <td style="padding: 9px 10px; border: 1px solid #d3d3d3; text-align: center;"><a href="?del_id={row['id']}" target="_self" style="text-decoration: none;">🗑️ Delete</a></td>
</tr>"""

    table_html += """</tbody>
</table>
</div>"""

    st.markdown(table_html, unsafe_allow_html=True)
else:
    st.info("No transactions found yet.")
