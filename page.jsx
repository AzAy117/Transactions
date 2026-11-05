"use client";
import React, { useState, useEffect } from "react";
import { supabase } from "../lib/supabaseClient";

export default function MainComponent() {
  const [transactions, setTransactions] = useState([]);
  const [date, setDate] = useState("");
  const [amount, setAmount] = useState("");
  const [reason, setReason] = useState("");
  const [file, setFile] = useState(null);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchTransactions();
  }, []);

  const fetchTransactions = async () => {
    const { data, error } = await supabase
      .from("transactions")
      .select("*")
      .order("date", { ascending: false });

    if (error) {
      console.error("Error fetching transactions:", error);
      return;
    }

    setTransactions(data || []);
    const sum = (data || []).reduce((acc, t) => acc + Number(t.amount), 0);
    setTotal(sum);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    let screenshotUrl = "";
    if (file) {
      const fileExt = file.name.split(".").pop();
      const fileName = `${Math.random()}.${fileExt}`;
      const filePath = `${fileName}`;

      const { error: uploadError } = await supabase.storage
        .from("screenshots")
        .upload(filePath, file);

      if (uploadError) {
        setError(uploadError.message);
        setLoading(false);
        return;
      }

      const { data: publicURLData } = supabase.storage
        .from("screenshots")
        .getPublicUrl(filePath);

      screenshotUrl = publicURLData.publicUrl;
    }

    const numAmount = parseFloat(amount);

    const { error: insertError } = await supabase.from("transactions").insert([
      {
        date,
        amount: numAmount,
        reason,
        screenshot: screenshotUrl,
      },
    ]);

    if (insertError) {
      setError(insertError.message);
      setLoading(false);
      return;
    }

    setDate("");
    setAmount("");
    setReason("");
      setFile(null);
    setLoading(false);
    fetchTransactions();
  };

  const handleDelete = async (id, txAmount) => {
    const { error } = await supabase.from("transactions").delete().eq("id", id);
    if (error) {
      console.error("Error deleting transaction:", error);
      return;
    }
    fetchTransactions();
  };

  return (
    <div className="min-h-screen bg-gray-100 p-4">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-6">Len-Den Tracker</h1>

        {error && (
          <div className="bg-red-100 text-red-700 p-3 rounded mb-4">
            {error}
          </div>
        )}

        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">
            Total Balance:{" "}
            <span className={total >= 0 ? "text-green-600" : "text-red-600"}>
              ₹{total.toFixed(2)}
            </span>
          </h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <input
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                className="border rounded p-2 w-full"
                required
              />
              <input
                type="number"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder="Amount (use - for negative)"
                className="border rounded p-2 w-full"
                required
                step="0.01"
              />
              <input
                type="text"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Reason"
                className="border rounded p-2 w-full"
                required
              />
              <input
                type="file"
                onChange={(e) => setFile(e.target.files[0])}
                className="border rounded p-2 w-full"
                accept="image/*"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 w-full"
            >
              {loading ? "Adding..." : "Add Transaction"}
            </button>
          </form>
        </div>

        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left">Date</th>
                  <th className="px-6 py-3 text-left">Amount</th>
                  <th className="px-6 py-3 text-left">Reason</th>
                  <th className="px-6 py-3 text-left">Screenshot</th>
                  <th className="px-6 py-3 text-left">Actions</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((transaction) => (
                  <tr key={transaction.id} className="border-t">
                    <td className="px-6 py-4">{transaction.date}</td>
                    <td className="px-6 py-4">
                      <span
                        className={
                          Number(transaction.amount) >= 0
                            ? "text-green-600"
                            : "text-red-600"
                        }
                      >
                        ₹{Number(transaction.amount).toFixed(2)}
                      </span>
                    </td>
                    <td className="px-6 py-4">{transaction.reason}</td>
                    <td className="px-6 py-4">
                      {transaction.screenshot && (
                        <img
                          src={transaction.screenshot}
                          alt="Receipt"
                          className="w-16 h-16 object-cover rounded"
                        />
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <button
                        onClick={() =>
                          handleDelete(transaction.id, transaction.amount)
                        }
                        className="text-red-600 hover:text-red-800"
                      >
                        🗑️
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
