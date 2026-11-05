import streamlit as st
from supabase import create_client
import pandas as pd

# Page configuration
st.set_page_config(page_title="Transactions", page_icon="💰", layout="centered")

# Supabase Credentials initialization
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "https://ozstskgokzppbfbbubyp.supabase.co")
SUPABASE_KEY = st.secrets.get("SUPABASE_ANON_KEY", "sb_publishable_JDP0BufPA7MpgLSi8wffMg_i7_64gVO")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Please configure your Supabase URL and API Key in the Streamlit Secrets settings.")
else:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    st.title("📊 Transactions")

    # Fetch data from Supabase
    try:
        response = supabase.table("transactions").select("*").order("date", desc=True).execute()
        data = response.data
    except Exception as e:
        data = []
        st.error(f"Error fetching data: {e}")

    # Calculate Total Balance
    total = sum([float(t["amount"]) for t in data]) if data else 0

    if total >= 0:
        st.subheader(f"Total Balance: ₹{total:.2f}")
    else:
        st.subheader(f"Total Balance: -₹{abs(total):.2f}")

    st.markdown("---")

    # Input Form to Add Transaction
    with st.form("transaction_form", clear_on_submit=True):
        st.write("### Add New Transaction")
        date = st.date_input("Date")
        amount = st.number_input("Amount (use negative for expense/debit)", step=0.01)
        reason = st.text_input("Reason / Description")
        
        submitted = st.form_submit_button("Add Transaction")
        
        if submitted:
            if reason:
                try:
                    supabase.table("transactions").insert({
                        "date": str(date),
                        "amount": amount,
                        "reason": reason,
                        "screenshot": ""
                    }).execute()
                    st.success("Transaction added successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error inserting transaction: {e}")
            else:
                st.error("Please enter a reason.")

    st.markdown("---")
    st.write("### Transaction History")

    if data:
        df = pd.DataFrame(data)
        # Display table with clean formatting
        st.dataframe(df[["date", "amount", "reason"]], use_container_width=True)
    else:
        st.info("No transactions found yet.")
