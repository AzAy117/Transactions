import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime

# Page configuration
st.set_page_config(page_title="Transactions Tracker", page_icon="📊", layout="wide")

# --- CUSTOM CSS FOR MOBILE HORIZONTAL SCROLL ---
st.markdown("""
<style>
    /* Mobile par columns ko vertical stack hone se rokne ke liye */
    @media (max-width: 768px) {
        [data-testid="stHorizontalBlock"] {
            flex-wrap: nowrap !important;
        }
        [data-testid="column"] {
            min-width: 90px !important;
            flex: 1 1 auto !important;
        }
    }
    
    /* Spreadsheet grid ke liye horizontal scroll wrapper */
    .scrollable-grid {
        width: 100%;
        overflow-x: auto;
        display: block;
    }
</style>
""", unsafe_allow_html=True)

# Supabase Credentials initialization from st.secrets
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "https://ozstskgokzppbfbbubyp.supabase.co")
SUPABASE_KEY = st.secrets.get("SUPABASE_ANON_KEY", "sb_publishable_JDP0BufPA7MpgLSi8wffMg_i7_64gVO")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Please configure your SUPABASE_URL and SUPABASE_ANON_KEY in Streamlit Secrets.")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("📊 Transactions Tracker")

# Initialize Session State for seamless inline editing & deleting
if "active_edit_id" not in st.session_state:
    st.session_state.active_edit_id = None
if "active_del_id" not in st.session_state:
    st.session_state.active_del_id = None

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

# --- ADD TRANSACTION SECTION ---
st.write("### Add New Transaction")

with st.form("transaction_form", clear_on_submit=True):
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        date_val = st.date_input("Date", value=datetime.today())
    with col_f2:
        amount_val = st.number_input(
            "Amount",
            value=None,
            step=0.01,
            format="%.2f",
            placeholder="Enter the amount"
        )
    with col_f3:
        reason_val = st.text_input("Reason", value="")
    with col_f4:
        auto_type = "Sent" if (amount_val is not None and amount_val >= 0) else "Received"
        st.write(f"**Type:** {auto_type} (auto)")

    uploaded_file = st.file_uploader("Screenshot / Receipt (Optional)", type=["png", "jpg", "jpeg"])

    submitted = st.form_submit_button("Add Transaction", use_container_width=True)

    if submitted:
        if amount_val is None:
            st.error("Please enter a valid amount.")
        else:
            image_url = ""
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
                "screenshot": image_url
            }

            supabase.table("transactions").insert(payload).execute()
            st.success("Transaction added successfully!")
            st.rerun()

st.markdown("---")

# --- ACTIVE EDIT / DELETE FORMS (POPUP SECTIONS) ---
if st.session_state.active_edit_id:
    edit_item = next((t for t in data if str(t["id"]) == str(st.session_state.active_edit_id)), None)
    if edit_item:
        st.info(f"✏️ Editing transaction: {edit_item.get('reason', '')} (₹{edit_item.get('amount')})")
        with st.form("inline_edit_form"):
            try:
                def_date = datetime.strptime(edit_item["date"], "%Y-%m-%d").date()
            except:
                def_date = datetime.today()
            def_amount = float(edit_item["amount"])
            def_reason = edit_item["reason"] or ""

            ie_col1, ie_col2, ie_col3, ie_col4 = st.columns(4)
            with ie_col1:
                new_date = st.date_input("Date", value=def_date)
            with ie_col2:
                new_amount = st.number_input(
                    "Amount",
                    value=def_amount,
                    step=0.01,
                    format="%.2f",
                    placeholder="Enter the amount"
                )
            with ie_col3:
                new_reason = st.text_input("Reason", value=def_reason)
            with ie_col4:
                auto_type = "Sent" if (new_amount is not None and new_amount >= 0) else "Received"
                st.write(f"**Type:** {auto_type} (auto)")

            new_file = st.file_uploader("Replace Receipt (Optional)", type=["png", "jpg", "jpeg"])
            
            sub_c1, sub_c2 = st.columns(2)
            with sub_c1:
                save_update = st.form_submit_button("💾 Save Changes", use_container_width=True)
            with sub_c2:
                cancel_update = st.form_submit_button("❌ Cancel", use_container_width=True)

            if cancel_update:
                st.session_state.active_edit_id = None
                st.rerun()

            if save_update:
                if new_amount is None:
                    st.error("Please enter a valid amount.")
                else:
                    image_url = edit_item.get("screenshot", "")
                    if new_file is not None:
                        try:
                            file_ext = new_file.name.split(".")[-1]
                            file_path = f"{int(datetime.now().timestamp())}.{file_ext}"
                            supabase.storage.from_("screenshots").upload(file_path, new_file.getvalue())
                            image_url = supabase.storage.from_("screenshots").get_public_url(file_path)
                        except Exception as img_err:
                            st.warning(f"Failed to upload image: {img_err}")

                    payload = {
                        "date": str(new_date),
                        "amount": new_amount,
                        "reason": new_reason,
                        "screenshot": image_url
                    }

                    supabase.table("transactions").update(payload).eq("id", st.session_state.active_edit_id).execute()
                    st.success("Transaction updated successfully on Cloud!")
                    st.session_state.active_edit_id = None
                    st.rerun()

if st.session_state.active_del_id:
    del_item = next((t for t in data if str(t["id"]) == str(st.session_state.active_del_id)), None)
    if del_item:
        st.warning(f"⚠️ Do you want to delete this transaction for '{del_item.get('reason', '')}' (₹{del_item.get('amount')})?")
        dc_1, dc_2 = st.columns(2)
        with dc_1:
            if st.button("Yes, Delete", use_container_width=True, key="confirm_delete_action"):
                supabase.table("transactions").delete().eq("id", st.session_state.active_del_id).execute()
                st.success("Transaction deleted successfully from Cloud!")
                st.session_state.active_del_id = None
                st.rerun()
        with dc_2:
            if st.button("Cancel", use_container_width=True, key="cancel_delete_action"):
                st.session_state.active_del_id = None
                st.rerun()

# --- UNIFIED SPREADSHEET GRID WITH EMBEDDED ROW ACTIONS ---
st.write("### Transactions Spreadsheet")

if data:
    df_table = pd.DataFrame(data)
    bg_colors = ["#e6f2ff", "#f3e8ff"] # 2 alternating colors: light blue & pinkish/purple

    # Spreadsheet Header using Native Columns
    h_cols = st.columns([2, 2, 3, 1.5, 1.5, 1, 1])
    h_cols[0].markdown("**Date**")
    h_cols[1].markdown("**Amount**")
    h_cols[2].markdown("**Reason**")
    h_cols[3].markdown("**Type**")
    h_cols[4].markdown("**Receipt**")
    h_cols[5].markdown("**Edit**")
    h_cols[6].markdown("**Delete**")

    st.markdown("<hr style='margin: 5px 0 10px 0;'>", unsafe_allow_html=True)

    for idx, row in df_table.iterrows():
        amount_val = float(row['amount'])
        t_type = "Sent" if amount_val >= 0 else "Received"
        badge_bg = "#2e7d32" if t_type == "Sent" else "#c62828"
        
        amount_color = "#2e7d32" if amount_val < 0 else "#c62828"
        row_bg = bg_colors[idx % len(bg_colors)]
        
        # Row Columns matching header exactly
        r_cols = st.columns([2, 2, 3, 1.5, 1.5, 1, 1], vertical_alignment="center")

        with r_cols[0]:
            st.markdown(f"<div style='background-color: {row_bg}; padding: 8px; border-radius: 4px; color: #000;'>{row['date']}</div>", unsafe_allow_html=True)
        with r_cols[1]:
            st.markdown(f"<div style='background-color: {row_bg}; padding: 8px; border-radius: 4px;'><b style='color: {amount_color};'>₹{amount_val:.2f}</b></div>", unsafe_allow_html=True)
        with r_cols[2]:
            st.markdown(f"<div style='background-color: {row_bg}; padding: 8px; border-radius: 4px; color: #000;'>{row['reason'] or '-'}</div>", unsafe_allow_html=True)
        with r_cols[3]:
            st.markdown(f"<div style='background-color: {row_bg}; padding: 8px; border-radius: 4px;'><span style='background-color: {badge_bg}; color: white; padding: 3px 10px; border-radius: 10px; font-weight: bold; font-size: 11px;'>{t_type}</span></div>", unsafe_allow_html=True)
        with r_cols[4]:
            if row.get("screenshot"):
                st.markdown(f"<div style='background-color: {row_bg}; padding: 8px; border-radius: 4px;'><a href='{row['screenshot']}' target='_blank'>View</a></div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='background-color: {row_bg}; padding: 8px; border-radius: 4px; color: #000;'>-</div>", unsafe_allow_html=True)
        with r_cols[5]:
            if st.button("✏️", key=f"grid_edit_{row['id']}"):
                st.session_state.active_edit_id = row['id']
                st.session_state.active_del_id = None
                st.rerun()
        with r_cols[6]:
            if st.button("🗑️", key=f"grid_del_{row['id']}"):
                st.session_state.active_del_id = row['id']
                st.session_state.active_edit_id = None
                st.rerun()
else:
    st.info("No transactions found yet.")
