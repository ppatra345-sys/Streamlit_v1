import streamlit as st
import pandas as pd
import re
from datetime import datetime
from collections import defaultdict
import plotly.graph_objects as go
import plotly.express as px
import io

# ─── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="WhatsApp Expense Tracker",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.main { background-color: #f8fafc; }

.metric-card {
    background: white;
    border-radius: 14px;
    padding: 20px 24px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.07);
    border-left: 4px solid #6366f1;
    margin-bottom: 12px;
}
.metric-card.green  { border-left-color: #22c55e; }
.metric-card.red    { border-left-color: #ef4444; }
.metric-card.blue   { border-left-color: #3b82f6; }
.metric-card.purple { border-left-color: #8b5cf6; }
.metric-card.orange { border-left-color: #f97316; }

.metric-label { font-size: 12px; color: #64748b; font-weight: 500; text-transform: uppercase; letter-spacing: .5px; }
.metric-value { font-size: 28px; font-weight: 700; color: #1e293b; margin: 4px 0 0; }
.metric-sub   { font-size: 13px; color: #94a3b8; margin-top: 2px; }

.section-header {
    font-size: 18px; font-weight: 700; color: #1e293b;
    margin: 28px 0 14px; padding-bottom: 8px;
    border-bottom: 2px solid #e2e8f0;
}

.expense-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 10px 14px; border-radius: 8px; margin-bottom: 6px;
    background: white; border: 1px solid #f1f5f9;
    font-size: 14px;
}
.expense-row:hover { background: #f8fafc; }
.expense-item { font-weight: 500; color: #334155; }
.expense-amount { font-weight: 700; color: #1e293b; }

.badge-major {
    background: #fef2f2; color: #dc2626;
    font-size: 10px; font-weight: 600; padding: 2px 8px;
    border-radius: 20px; text-transform: uppercase;
}

.compare-up   { color: #ef4444; font-weight: 600; }
.compare-down { color: #22c55e; font-weight: 600; }
.compare-same { color: #94a3b8; font-weight: 600; }

.upload-hint {
    background: #f0f9ff; border: 1px dashed #93c5fd;
    border-radius: 10px; padding: 16px; font-size: 13px;
    color: #1e40af; margin-bottom: 20px; line-height: 1.6;
}

.stTabs [data-baseweb="tab"] { font-size: 14px; font-weight: 500; }
</style>
""", unsafe_allow_html=True)


# ─── Parsing Logic ─────────────────────────────────────────────────────────────

# WhatsApp date patterns (covers Android & iOS exports)
DATE_PATTERNS = [
    # DD/MM/YYYY, HH:MM - am/pm  (iOS)
    r"(\d{1,2}/\d{1,2}/\d{2,4}),\s*\d{1,2}:\d{2}(?::\d{2})?\s*(?:am|pm|AM|PM)?\s*[-–]\s*",
    # DD/MM/YYYY, HH:MM            (Android)
    r"(\d{1,2}/\d{1,2}/\d{2,4}),\s*\d{1,2}:\d{2}(?::\d{2})?\s*[-–]\s*",
    # [DD/MM/YYYY, HH:MM:SS]        (some exports)
    r"\[(\d{1,2}/\d{1,2}/\d{2,4}),\s*\d{1,2}:\d{2}(?::\d{2})?(?:\s*(?:am|pm|AM|PM))?\]\s*",
    # M/D/YY format
    r"(\d{1,2}/\d{1,2}/\d{2}),\s*\d{1,2}:\d{2}\s*(?:AM|PM)?\s*[-–]\s*",
]

AMOUNT_PATTERNS = [
    r"₹\s*([\d,]+(?:\.\d{1,2})?)",
    r"Rs\.?\s*([\d,]+(?:\.\d{1,2})?)",
    r"INR\s*([\d,]+(?:\.\d{1,2})?)",
    r"\b([\d,]+(?:\.\d{1,2})?)\s*(?:rupees?|/-)",
    # plain number that looks like a price (100–99999)
    r"\b([\d]{3,5}(?:\.\d{1,2})?)\b",
]

SKIP_PHRASES = [
    "messages and calls", "end-to-end encrypted", "joined using",
    "added", "removed", "left", "changed the subject",
    "changed this group", "you were added", "security code",
    "image omitted", "video omitted", "audio omitted",
    "document omitted", "sticker omitted", "contact card omitted",
    "deleted this message", "this message was deleted",
    "<media omitted>",
]

CATEGORY_KEYWORDS = {
    "Groceries":    ["grocery", "groceries", "sabji", "vegetable", "fruit", "dal", "rice", "atta", "oil", "salt", "sugar", "masala", "spice", "paneer", "milk", "curd", "dahi", "egg", "onion", "potato", "tomato", "garlic", "ginger"],
    "Food & Dining":["food", "lunch", "dinner", "breakfast", "snack", "restaurant", "swiggy", "zomato", "dine", "eat", "biryani", "pizza", "burger", "chai", "coffee", "tea", "biscuit", "cake", "sweet", "mithai"],
    "Medicines":    ["medicine", "tablet", "capsule", "syrup", "pharmacy", "chemist", "apollo", "1mg", "netmeds", "pharma", "strip", "injection", "ointment", "cream", "drops"],
    "Clothing":     ["shirt", "pant", "trouser", "saree", "dress", "top", "kurta", "jeans", "cloth", "clothing", "garment", "fabric", "blouse", "skirt", "jacket", "coat", "shoes", "footwear", "sandal", "slipper", "chappal"],
    "Utilities":    ["electricity", "bill", "water", "gas", "recharge", "mobile", "internet", "wifi", "broadband", "dth", "cable", "maintenance", "society", "rent", "emi"],
    "Household":    ["household", "utensil", "vessel", "bucket", "mop", "broom", "soap", "detergent", "shampoo", "toothpaste", "brush", "toilet", "cleanser", "surface", "floor", "napkin", "tissue"],
    "Transport":    ["auto", "rickshaw", "cab", "uber", "ola", "taxi", "bus", "train", "metro", "petrol", "diesel", "fuel", "parking"],
    "Shopping":     ["amazon", "flipkart", "myntra", "meesho", "nykaa", "zepto", "blinkit", "bigbasket", "jiomart", "grofers"],
}


def parse_date(date_str: str):
    date_str = date_str.strip().rstrip("/- ")
    fmts = [
        "%d/%m/%Y", "%d/%m/%y",
        "%m/%d/%Y", "%m/%d/%y",
        "%d-%m-%Y", "%d-%m-%y",
    ]
    for fmt in fmts:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def extract_date_from_line(line: str):
    for pat in DATE_PATTERNS:
        m = re.match(pat, line, re.IGNORECASE)
        if m:
            return m.group(1), m.end()
    return None, -1


def clean_amount(raw: str) -> float:
    return float(raw.replace(",", ""))


def extract_amounts(text: str):
    amounts = []
    for pat in AMOUNT_PATTERNS[:-1]:   # prefer explicit currency patterns first
        for m in re.finditer(pat, text, re.IGNORECASE):
            try:
                amounts.append(clean_amount(m.group(1)))
            except Exception:
                pass
    if amounts:
        return amounts
    # fall back to plain numbers
    for m in re.finditer(AMOUNT_PATTERNS[-1], text):
        val = clean_amount(m.group(1))
        if 10 <= val <= 200000:        # sanity range
            amounts.append(val)
    return amounts


def guess_category(text: str) -> str:
    lower = text.lower()
    for cat, kws in CATEGORY_KEYWORDS.items():
        if any(kw in lower for kw in kws):
            return cat
    return "Other"


def should_skip(text: str) -> bool:
    lower = text.lower()
    return any(phrase in lower for phrase in SKIP_PHRASES)


def parse_whatsapp_chat(content: str, group_label: str) -> pd.DataFrame:
    """Parse raw WhatsApp export text into a DataFrame of expense rows."""
    records = []
    lines = content.splitlines()
    current_date = None
    current_sender = None
    current_msg_parts = []

    def flush():
        nonlocal current_msg_parts
        if not current_msg_parts or current_date is None:
            return
        msg = " ".join(current_msg_parts).strip()
        if should_skip(msg):
            current_msg_parts = []
            return
        amounts = extract_amounts(msg)
        for amt in amounts:
            records.append({
                "date": current_date,
                "month_year": current_date.strftime("%b %Y"),
                "month_sort": current_date.strftime("%Y-%m"),
                "sender": current_sender or "Unknown",
                "description": msg[:120],
                "amount": amt,
                "category": guess_category(msg),
                "group": group_label,
            })
        current_msg_parts = []

    for line in lines:
        date_str, msg_start = extract_date_from_line(line)
        if date_str and msg_start > 0:
            flush()
            dt = parse_date(date_str)
            if dt:
                current_date = dt
                rest = line[msg_start:].strip()
                # split "Sender: message"
                if ":" in rest:
                    parts = rest.split(":", 1)
                    current_sender = parts[0].strip()
                    current_msg_parts = [parts[1].strip()] if len(parts) > 1 else []
                else:
                    current_msg_parts = [rest]
        else:
            # continuation line
            current_msg_parts.append(line.strip())

    flush()
    return pd.DataFrame(records)


# ─── Helper UI components ───────────────────────────────────────────────────────

def metric_card(label, value, sub="", color="purple"):
    st.markdown(f"""
    <div class="metric-card {color}">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        {"<div class='metric-sub'>" + sub + "</div>" if sub else ""}
    </div>""", unsafe_allow_html=True)


def fmt_inr(val: float) -> str:
    if val >= 1_00_000:
        return f"₹{val/1_00_000:.2f}L"
    if val >= 1_000:
        return f"₹{val:,.0f}"
    return f"₹{val:.0f}"


def pct_arrow(pct):
    if pct > 0:
        return f'<span class="compare-up">▲ {abs(pct):.1f}%</span>'
    if pct < 0:
        return f'<span class="compare-down">▼ {abs(pct):.1f}%</span>'
    return '<span class="compare-same">— 0%</span>'


# ─── Main App ───────────────────────────────────────────────────────────────────

def main():
    # Header
    st.markdown("""
    <div style="background:linear-gradient(135deg,#6366f1,#8b5cf6);
         border-radius:16px;padding:28px 32px;margin-bottom:28px;color:white;">
        <h1 style="margin:0;font-size:28px;font-weight:800;">💰 WhatsApp Expense Tracker</h1>
        <p style="margin:6px 0 0;opacity:.85;font-size:15px;">
            Upload your WhatsApp group chats to get consolidated monthly expense reports
        </p>
    </div>""", unsafe_allow_html=True)

    # ── Sidebar upload ──────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### 📂 Upload Chat Exports")

        st.markdown("""
        <div class="upload-hint">
        <b>How to export WhatsApp chat:</b><br>
        Open group → ⋮ Menu → More → Export Chat → Without Media<br><br>
        Upload the <code>.txt</code> file below.
        </div>""", unsafe_allow_html=True)

        grocery_file = st.file_uploader(
            "🛒 Grocery / Food / Medicines Chat",
            type=["txt"], key="grocery"
        )
        shopping_file = st.file_uploader(
            "🛍️ Shopping / Utilities Chat",
            type=["txt"], key="shopping"
        )

        st.markdown("---")
        major_threshold_pct = st.slider(
            "Major expense threshold (%)",
            min_value=5, max_value=30, value=10,
            help="Expenses > this % of monthly total are flagged as major"
        )
        st.markdown("---")
        st.caption("Built with ❤️ using Streamlit + Plotly")

    # ── Parse uploaded files ────────────────────────────────────────────────────
    dfs = []
    if grocery_file:
        try:
            text = grocery_file.read().decode("utf-8", errors="ignore")
            df = parse_whatsapp_chat(text, "Grocery/Food/Medicines")
            dfs.append(df)
        except Exception as e:
            st.error(f"Error parsing grocery file: {e}")

    if shopping_file:
        try:
            text = shopping_file.read().decode("utf-8", errors="ignore")
            df = parse_whatsapp_chat(text, "Shopping/Utilities")
            dfs.append(df)
        except Exception as e:
            st.error(f"Error parsing shopping file: {e}")

    if not dfs:
        # Welcome / demo state
        st.markdown("""
        <div style="text-align:center;padding:60px 20px;color:#94a3b8;">
            <div style="font-size:64px;margin-bottom:16px;">📤</div>
            <h3 style="color:#64748b;">Upload your WhatsApp chat exports to get started</h3>
            <p style="font-size:14px;">Use the sidebar on the left to upload one or both chat files.<br>
            Amounts in ₹, Rs, INR or plain numbers will be auto-detected.</p>
        </div>""", unsafe_allow_html=True)
        return

    df_all = pd.concat(dfs, ignore_index=True)

    if df_all.empty:
        st.warning("No expense entries could be detected in the uploaded files. "
                   "Make sure the chat contains amounts (₹ / Rs / INR or plain numbers).")
        return

    df_all = df_all.sort_values(["month_sort", "date"])
    months_sorted = sorted(df_all["month_sort"].unique())
    month_labels = {m: datetime.strptime(m, "%Y-%m").strftime("%b %Y") for m in months_sorted}

    # ── Monthly aggregate ───────────────────────────────────────────────────────
    monthly = (
        df_all.groupby(["month_sort", "month_year", "group"])["amount"]
        .sum().reset_index()
    )
    monthly_total = (
        df_all.groupby("month_sort")["amount"].sum().reset_index()
        .rename(columns={"amount": "total"})
    )
    monthly_total["month_year"] = monthly_total["month_sort"].map(month_labels)

    # ── Top-level KPIs ──────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">📊 Overview</div>', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_card("Total Expenses", fmt_inr(df_all["amount"].sum()),
                    f"{len(months_sorted)} months tracked", "purple")
    with col2:
        avg = monthly_total["total"].mean()
        metric_card("Avg Monthly Spend", fmt_inr(avg), "per month", "blue")
    with col3:
        peak_row = monthly_total.loc[monthly_total["total"].idxmax()]
        metric_card("Highest Month", fmt_inr(peak_row["total"]),
                    peak_row["month_year"], "red")
    with col4:
        low_row = monthly_total.loc[monthly_total["total"].idxmin()]
        metric_card("Lowest Month", fmt_inr(low_row["total"]),
                    low_row["month_year"], "green")

    # ── Tabs ────────────────────────────────────────────────────────────────────
    tabs = st.tabs(["📅 Monthly Summary", "🔍 Month Detail", "📈 Trends", "📋 All Transactions"])

    # ── Tab 1: Monthly Summary ──────────────────────────────────────────────────
    with tabs[0]:
        st.markdown('<div class="section-header">Monthly Consolidated Expenses</div>',
                    unsafe_allow_html=True)

        # Stacked bar: grocery vs shopping
        fig_bar = go.Figure()
        groups = df_all["group"].unique()
        colors = {"Grocery/Food/Medicines": "#6366f1", "Shopping/Utilities": "#f97316"}
        for grp in groups:
            sub = monthly[monthly["group"] == grp]
            fig_bar.add_trace(go.Bar(
                x=sub["month_year"], y=sub["amount"],
                name=grp, marker_color=colors.get(grp, "#94a3b8"),
                text=sub["amount"].apply(fmt_inr), textposition="inside",
                textfont=dict(color="white", size=11),
            ))
        fig_bar.update_layout(
            barmode="stack", plot_bgcolor="white", paper_bgcolor="white",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            margin=dict(l=0, r=0, t=40, b=0), height=320,
            xaxis=dict(title=""), yaxis=dict(title="Amount (₹)", gridcolor="#f1f5f9"),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        # Month-over-month comparison table
        st.markdown('<div class="section-header">Month-over-Month Comparison</div>',
                    unsafe_allow_html=True)

        rows = []
        for i, ms in enumerate(months_sorted):
            cur = monthly_total[monthly_total["month_sort"] == ms]["total"].values[0]
            if i == 0:
                diff, pct, arrow = 0, 0, "—"
            else:
                prev_ms = months_sorted[i - 1]
                prev = monthly_total[monthly_total["month_sort"] == prev_ms]["total"].values[0]
                diff = cur - prev
                pct = (diff / prev * 100) if prev else 0
                arrow = ("▲" if diff > 0 else "▼") if diff != 0 else "—"
            rows.append({
                "Month": month_labels[ms],
                "Total": fmt_inr(cur),
                "vs Prev Month": f"{arrow} {fmt_inr(abs(diff))}" if diff != 0 else "—",
                "Change %": f"{'+' if pct > 0 else ''}{pct:.1f}%" if diff != 0 else "—",
                "Status": "🔴 Higher" if pct > 5 else ("🟢 Lower" if pct < -5 else "🟡 Similar"),
            })

        cmp_df = pd.DataFrame(rows)
        st.dataframe(cmp_df, use_container_width=True, hide_index=True)

    # ── Tab 2: Month Detail ─────────────────────────────────────────────────────
    with tabs[1]:
        st.markdown('<div class="section-header">Drill Down by Month</div>',
                    unsafe_allow_html=True)

        selected_month = st.selectbox(
            "Select Month",
            options=months_sorted,
            format_func=lambda m: month_labels[m],
        )

        month_df = df_all[df_all["month_sort"] == selected_month].copy()
        month_total = month_df["amount"].sum()
        major_cutoff = month_total * (major_threshold_pct / 100)

        col_a, col_b = st.columns([2, 1])

        with col_a:
            # Category breakdown
            cat_totals = (
                month_df.groupby("category")["amount"].sum()
                .sort_values(ascending=False).reset_index()
            )
            cat_totals["pct"] = cat_totals["amount"] / month_total * 100
            cat_totals["is_major"] = cat_totals["amount"] >= major_cutoff

            fig_pie = px.pie(
                cat_totals, values="amount", names="category",
                color_discrete_sequence=px.colors.qualitative.Pastel,
                hole=0.4,
            )
            fig_pie.update_traces(textposition="outside", textinfo="percent+label")
            fig_pie.update_layout(
                showlegend=False, margin=dict(l=0, r=0, t=30, b=0), height=300
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_b:
            metric_card("Month Total", fmt_inr(month_total),
                        month_labels[selected_month], "purple")
            metric_card("# Transactions",
                        str(len(month_df)),
                        f"Avg {fmt_inr(month_df['amount'].mean())}/entry", "blue")
            n_major = len(month_df[month_df["amount"] >= major_cutoff])
            metric_card("Major Expenses", str(n_major),
                        f"Each > {fmt_inr(major_cutoff)}", "red")

        # Category table
        st.markdown("**Category Breakdown**")
        for _, row in cat_totals.iterrows():
            badge = '<span class="badge-major">MAJOR</span>' if row["is_major"] else ""
            st.markdown(f"""
            <div class="expense-row">
                <span class="expense-item">{row["category"]} {badge}</span>
                <span class="expense-amount">{fmt_inr(row["amount"])}
                    <span style="color:#94a3b8;font-size:12px;font-weight:400;">
                        ({row['pct']:.1f}%)
                    </span>
                </span>
            </div>""", unsafe_allow_html=True)

        # Individual transactions
        st.markdown('<div class="section-header">Individual Entries</div>',
                    unsafe_allow_html=True)
        display_df = month_df[["date", "sender", "description", "amount", "category", "group"]].copy()
        display_df["date"] = display_df["date"].dt.strftime("%d %b")
        display_df["amount"] = display_df["amount"].apply(fmt_inr)
        display_df.columns = ["Date", "Sender", "Description", "Amount", "Category", "Group"]
        st.dataframe(display_df, use_container_width=True, hide_index=True)

    # ── Tab 3: Trends ───────────────────────────────────────────────────────────
    with tabs[2]:
        st.markdown('<div class="section-header">Expense Trends</div>',
                    unsafe_allow_html=True)

        # Line chart total
        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(
            x=monthly_total["month_year"], y=monthly_total["total"],
            mode="lines+markers+text",
            text=monthly_total["total"].apply(fmt_inr),
            textposition="top center",
            line=dict(color="#6366f1", width=2.5),
            marker=dict(size=8, color="#6366f1"),
            fill="tozeroy", fillcolor="rgba(99,102,241,0.08)",
        ))
        fig_line.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=0, r=0, t=20, b=0), height=280,
            xaxis=dict(title=""), yaxis=dict(title="₹", gridcolor="#f1f5f9"),
        )
        st.plotly_chart(fig_line, use_container_width=True)

        # Category heatmap across months
        st.markdown("**Category Spend Heatmap (₹)**")
        cat_month = (
            df_all.groupby(["month_sort", "category"])["amount"]
            .sum().reset_index()
        )
        pivot = cat_month.pivot(index="category", columns="month_sort", values="amount").fillna(0)
        pivot.columns = [month_labels[m] for m in pivot.columns]

        fig_heat = go.Figure(go.Heatmap(
            z=pivot.values,
            x=list(pivot.columns), y=list(pivot.index),
            colorscale="Purples",
            text=[[fmt_inr(v) for v in row] for row in pivot.values],
            texttemplate="%{text}",
            textfont=dict(size=10),
        ))
        fig_heat.update_layout(
            margin=dict(l=0, r=0, t=10, b=0), height=320,
            plot_bgcolor="white", paper_bgcolor="white",
        )
        st.plotly_chart(fig_heat, use_container_width=True)

    # ── Tab 4: All Transactions ─────────────────────────────────────────────────
    with tabs[3]:
        st.markdown('<div class="section-header">All Transactions</div>',
                    unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)
        with c1:
            filter_group = st.multiselect("Group", df_all["group"].unique(),
                                          default=list(df_all["group"].unique()))
        with c2:
            filter_cat = st.multiselect("Category", sorted(df_all["category"].unique()),
                                        default=list(df_all["category"].unique()))
        with c3:
            min_amt, max_amt = float(df_all["amount"].min()), float(df_all["amount"].max())
            amt_range = st.slider("Amount range (₹)", min_amt, max_amt,
                                  (min_amt, max_amt))

        filtered = df_all[
            (df_all["group"].isin(filter_group)) &
            (df_all["category"].isin(filter_cat)) &
            (df_all["amount"] >= amt_range[0]) &
            (df_all["amount"] <= amt_range[1])
        ].copy()

        filtered_display = filtered[["date", "month_year", "sender", "description",
                                     "amount", "category", "group"]].copy()
        filtered_display["date"] = filtered_display["date"].dt.strftime("%d %b %Y")
        filtered_display.columns = ["Date", "Month", "Sender", "Description",
                                    "Amount (₹)", "Category", "Group"]

        st.caption(f"Showing {len(filtered_display):,} transactions | "
                   f"Total: {fmt_inr(filtered['amount'].sum())}")

        st.dataframe(filtered_display, use_container_width=True, hide_index=True,
                     column_config={"Amount (₹)": st.column_config.NumberColumn(format="₹%.0f")})

        # Download
        csv_buf = io.StringIO()
        filtered_display.to_csv(csv_buf, index=False)
        st.download_button(
            "⬇️ Download as CSV",
            data=csv_buf.getvalue(),
            file_name="expenses_export.csv",
            mime="text/csv",
        )


if __name__ == "__main__":
    main()
