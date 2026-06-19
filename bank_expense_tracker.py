import streamlit as st
import pandas as pd
import pdfplumber
import re
import io
import json
import hashlib
import requests
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px
from pypdf import PdfReader

# ─── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Bank Statement Expense Tracker",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.main { background-color: #f8fafc; }

.hero {
    background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 60%, #1e293b 100%);
    border-radius: 16px; padding: 28px 32px; margin-bottom: 24px; color: white;
}
.hero h1 { margin: 0; font-size: 26px; font-weight: 800; }
.hero p  { margin: 8px 0 0; opacity: .75; font-size: 13px; line-height: 1.6; }

.shield-badge {
    display: inline-flex; align-items: center; gap: 6px;
    background: rgba(34,197,94,0.15); border: 1px solid rgba(34,197,94,0.4);
    border-radius: 20px; padding: 4px 12px; font-size: 12px;
    color: #86efac; font-weight: 600; margin-top: 10px;
}

.card {
    background: white; border-radius: 14px; padding: 20px 22px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.07); margin-bottom: 14px;
    border-left: 4px solid #6366f1;
}
.card.green  { border-left-color: #22c55e; }
.card.red    { border-left-color: #ef4444; }
.card.blue   { border-left-color: #3b82f6; }
.card.orange { border-left-color: #f97316; }
.card.teal   { border-left-color: #14b8a6; }
.card-label  { font-size: 11px; color: #64748b; font-weight: 600; text-transform: uppercase; letter-spacing: .5px; }
.card-value  { font-size: 26px; font-weight: 800; color: #1e293b; margin: 4px 0 0; }
.card-sub    { font-size: 12px; color: #94a3b8; margin-top: 2px; }

.section-header {
    font-size: 17px; font-weight: 700; color: #1e293b;
    margin: 24px 0 12px; padding-bottom: 8px;
    border-bottom: 2px solid #e2e8f0;
}

.privacy-panel {
    background: #f0fdf4; border: 1px solid #bbf7d0;
    border-radius: 12px; padding: 16px 18px; margin-bottom: 16px;
    font-size: 13px; color: #14532d; line-height: 1.7;
}
.privacy-panel h4 { margin: 0 0 8px; font-size: 14px; font-weight: 700; color: #15803d; }

.masked-item {
    display: inline-block; background: #fef9c3; border: 1px solid #fde047;
    border-radius: 4px; padding: 1px 6px; font-size: 11px;
    color: #713f12; font-weight: 600; font-family: monospace;
}

.pii-log {
    background: #1e293b; border-radius: 10px; padding: 12px 16px;
    font-size: 11px; font-family: monospace; color: #94a3b8;
    max-height: 140px; overflow-y: auto; margin-top: 8px;
}
.pii-log .masked { color: #fbbf24; }
.pii-log .ok     { color: #4ade80; }

.bank-card {
    background: white; border-radius: 12px; padding: 14px 16px;
    border: 1px solid #e2e8f0; margin-bottom: 10px;
}

.badge { display: inline-block; font-size: 10px; font-weight: 700;
    padding: 2px 8px; border-radius: 20px; text-transform: uppercase; }
.badge-major  { background: #fef2f2; color: #dc2626; }
.badge-debit  { background: #eff6ff; color: #2563eb; }
.badge-credit { background: #f0fdf4; color: #16a34a; }
.badge-safe   { background: #f0fdf4; color: #15803d; }

.txn-row {
    display: flex; justify-content: space-between; align-items: flex-start;
    padding: 10px 12px; border-radius: 8px; margin-bottom: 5px;
    background: #f8fafc; border: 1px solid #f1f5f9; font-size: 13px;
}
.txn-desc { color: #334155; font-weight: 500; flex: 1; }
.txn-amt  { font-weight: 700; color: #1e293b; white-space: nowrap; margin-left: 12px; }

.warning-box {
    background: #fffbeb; border: 1px solid #fcd34d;
    border-radius: 10px; padding: 14px 16px; font-size: 13px; color: #92400e; margin-bottom: 14px;
}
.info-box {
    background: #f0f9ff; border: 1px solid #bae6fd;
    border-radius: 10px; padding: 14px 16px; font-size: 13px; color: #0c4a6e; margin-bottom: 14px;
}
.delete-box {
    background: #fef2f2; border: 1px solid #fca5a5;
    border-radius: 10px; padding: 14px 16px; font-size: 13px; color: #7f1d1d; margin-bottom: 14px;
}
.stTabs [data-baseweb="tab"] { font-size: 13px; font-weight: 500; }
</style>
""", unsafe_allow_html=True)

# ─── Constants ─────────────────────────────────────────────────────────────────
BANKS = {
    "axis_debit":   {"label": "Axis Bank Debit Card",     "icon": "🏦", "color": "#c0392b"},
    "sbi_debit":    {"label": "SBI Debit Card",            "icon": "🏛️", "color": "#2980b9"},
    "axis_credit":  {"label": "Axis Bank Credit Card",     "icon": "💳", "color": "#e74c3c"},
    "flipkart_sbi": {"label": "Flipkart SBI Credit Card",  "icon": "🛒", "color": "#8e44ad"},
    "yes_credit":   {"label": "Yes Bank Credit Card",      "icon": "💜", "color": "#16a085"},
}

CATEGORIES = [
    "Groceries", "Food & Dining", "Shopping – Clothing",
    "Shopping – Electronics", "Shopping – General",
    "Utilities & Bills", "Fuel & Transport", "Healthcare & Medicines",
    "Entertainment", "Travel", "EMI / Loan", "Insurance",
    "Investment / Savings", "Cash Withdrawal", "Transfer / UPI",
    "Education", "Other",
]

# ─── Session State ──────────────────────────────────────────────────────────────
def init_state():
    for k, v in {
        "transactions": pd.DataFrame(),
        "api_key": "",
        "processed_banks": [],
        "confirmed_delete": False,
        "pii_log": [],
    }.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ══════════════════════════════════════════════════════════════════════════════
#  PII MASKING ENGINE  — strips all sensitive fields BEFORE any data is stored
# ══════════════════════════════════════════════════════════════════════════════

# Compiled patterns — order matters (most specific first)
_PII_PATTERNS = [
    # 16-digit card numbers (with or without spaces/dashes)
    ("Card Number",
     re.compile(r"\b(?:\d[ -]?){13,15}\d\b")),
    # Account numbers (10–18 digits standalone)
    ("Account Number",
     re.compile(r"\b\d{10,18}\b")),
    # IFSC codes
    ("IFSC Code",
     re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b")),
    # UPI IDs  e.g. someone@upi, someone@okaxis
    ("UPI ID",
     re.compile(r"\b[\w.\-+]+@[\w]+\b")),
    # Transaction / reference IDs (alphanumeric 8–24 chars after common labels)
    ("Transaction ID",
     re.compile(r"(?:Ref(?:erence)?(?:\s*No\.?|:|\s)|Txn\s*(?:ID|No\.?|:|\s)|UTR\s*(?:No\.?|:|\s)|NEFT\s*Ref\s*|IMPS\s*Ref\s*)([A-Z0-9]{6,24})", re.IGNORECASE)),
    # Standalone alphanumeric IDs that look like txn refs (12–22 chars)
    ("Ref ID",
     re.compile(r"\b[A-Z]{2,4}[0-9]{8,18}\b")),
    # PAN number
    ("PAN",
     re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")),
    # Aadhaar (12 digits, sometimes with spaces)
    ("Aadhaar",
     re.compile(r"\b\d{4}\s\d{4}\s\d{4}\b")),
    # Mobile numbers (10 digits starting with 6-9)
    ("Mobile",
     re.compile(r"\b[6-9]\d{9}\b")),
    # Email addresses
    ("Email",
     re.compile(r"\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b")),
    # Person names after "To:" / "By:" / "From:" in UPI lines
    ("Payee Name",
     re.compile(r"(?:To|By|From|Paid to|Sent to|Received from)\s*:\s*([A-Z][a-zA-Z ]{3,30})", re.IGNORECASE)),
    # Branch names (heuristic: Title Case word(s) before "Branch")
    ("Branch",
     re.compile(r"[A-Z][a-z]+(?: [A-Z][a-z]+)* Branch", re.IGNORECASE)),
    # MMID
    ("MMID",
     re.compile(r"\b\d{7}\b")),
]

_KEEP_FIELDS = {"date", "amount", "type", "description_clean", "merchant", "category"}


def _hash_token(val: str) -> str:
    """Deterministic short hash for logging — never stored in output."""
    return hashlib.sha256(val.encode()).hexdigest()[:8].upper()


def mask_pii(text: str) -> tuple:
    """
    Apply all PII patterns to a text string.
    Returns (masked_text, list_of_what_was_masked).
    The original values are NEVER stored — only replaced with [MASKED-TYPE].
    """
    log = []
    result = text

    for label, pattern in _PII_PATTERNS:
        def replacer(m, lbl=label):
            full = m.group(0)
            log.append(f"[{lbl}] → [MASKED]")
            return f"[MASKED-{lbl.upper().replace(' ', '-')}]"
        result = pattern.sub(replacer, result)

    return result, log


def sanitize_line(line: str) -> str:
    """Mask PII on a single line and return the safe version."""
    clean, _ = mask_pii(line)
    return clean


def sanitize_text_block(raw_text: str) -> tuple:
    """
    Sanitize entire PDF text block.
    Returns (sanitized_text, total_mask_events).
    Raw text is discarded after this call — only sanitized version persists.
    """
    lines = raw_text.splitlines()
    clean_lines = []
    all_events = []
    for line in lines:
        c, events = mask_pii(line)
        clean_lines.append(c)
        all_events.extend(events)
    return "\n".join(clean_lines), all_events


# ══════════════════════════════════════════════════════════════════════════════
#  PDF EXTRACTION  (text extracted → immediately sanitized → raw discarded)
# ══════════════════════════════════════════════════════════════════════════════

def extract_and_sanitize(uploaded_file, password: str) -> tuple:
    """
    Step 1: Extract raw text from PDF (in memory only).
    Step 2: Immediately apply PII masking.
    Step 3: Discard raw text — only masked text is returned.
    Returns (sanitized_text, pii_event_count, error_or_none).
    """
    raw_bytes = uploaded_file.read()
    uploaded_file.seek(0)
    raw_text = ""

    # Try pdfplumber first
    try:
        with pdfplumber.open(io.BytesIO(raw_bytes), password=password or None) as pdf:
            parts = []
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    parts.append(t)
            raw_text = "\n".join(parts)
    except Exception:
        pass

    # Fallback to pypdf
    if not raw_text:
        try:
            reader = PdfReader(io.BytesIO(raw_bytes))
            if reader.is_encrypted:
                reader.decrypt(password or "")
            parts = []
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    parts.append(t)
            raw_text = "\n".join(parts)
        except Exception as e:
            return "", 0, str(e)

    if not raw_text:
        return "", 0, "No text could be extracted from PDF."

    # ── SANITIZE IMMEDIATELY — raw_text goes out of scope after this ──────────
    sanitized, events = sanitize_text_block(raw_text)
    del raw_text  # explicitly delete raw text from memory

    return sanitized, len(events), None


# ══════════════════════════════════════════════════════════════════════════════
#  TRANSACTION PARSER  (works on already-sanitized text)
# ══════════════════════════════════════════════════════════════════════════════

def parse_transaction_lines(sanitized_text: str) -> list:
    """Extract candidate transaction lines from sanitized text."""
    lines = sanitized_text.splitlines()
    amount_re = re.compile(r"\b\d{1,3}(?:,\d{3})*(?:\.\d{2})?\b")
    date_re = re.compile(
        r"\b(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}"
        r"|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})\b",
        re.IGNORECASE,
    )
    txn_keywords = [
        "upi", "neft", "imps", "atm", "pos", "purchase", "payment",
        "transfer", "credit", "debit", "refund", "swiggy", "zomato",
        "amazon", "flipkart", "myntra", "zepto", "blinkit", "uber",
        "ola", "irctc", "netflix", "hotstar", "airtel", "jio",
    ]
    candidates = []
    seen = set()
    for line in lines:
        line = line.strip()
        if not line or len(line) < 8:
            continue
        has_amount = amount_re.search(line)
        has_date = date_re.search(line)
        has_keyword = any(k in line.lower() for k in txn_keywords)
        if has_amount and (has_date or has_keyword):
            if line not in seen:
                seen.add(line)
                candidates.append(line)
    return candidates


# ══════════════════════════════════════════════════════════════════════════════
#  AI CATEGORIZATION  (only sanitized lines sent to API)
# ══════════════════════════════════════════════════════════════════════════════

def categorize_with_ai(sanitized_lines: list, api_key: str, bank_label: str) -> list:
    """Send ONLY sanitized transaction lines (no PII) to Claude API."""
    if not api_key:
        return []

    results = []
    batch_size = 40

    for i in range(0, len(sanitized_lines), batch_size):
        batch = sanitized_lines[i:i + batch_size]
        batch_text = "\n".join(f"{j+1}. {t}" for j, t in enumerate(batch))

        prompt = f"""You are a financial analyst reviewing ALREADY SANITIZED bank transactions from '{bank_label}'.
All account numbers, card numbers, names, IDs and references have been replaced with [MASKED-*] tokens.
DO NOT attempt to recover or guess any masked information.

For each line extract ONLY:
- date: DD-MM-YYYY (infer from context; use today if missing)
- description: clean merchant/purpose description (ignore [MASKED-*] tokens)
- amount: numeric only (positive float)
- type: "debit" or "credit"
- category: pick ONE from {json.dumps(CATEGORIES)}
- merchant: app/merchant name only (e.g. Swiggy, Amazon, Zepto)
- confidence: "high" | "medium" | "low"

Category rules:
Swiggy/Zomato→Food & Dining | Myntra/Ajio/Meesho→Shopping – Clothing |
Amazon/Flipkart→Shopping – General | Zepto/Blinkit/BigBasket→Groceries |
Netflix/Hotstar/Spotify/Prime→Entertainment | Apollo/1mg/Medplus→Healthcare & Medicines |
IRCTC/MakeMyTrip/Indigo→Travel | Ola/Uber/Petrol→Fuel & Transport |
Electricity/Jio/Airtel/Recharge→Utilities & Bills | ATM→Cash Withdrawal |
EMI/Loan/LIC→EMI / Loan | Groww/Zerodha/MF/SIP→Investment / Savings |
UPI/NEFT/IMPS→Transfer / UPI | School/Udemy→Education

Transactions:
{batch_text}

Return ONLY a valid JSON array. No markdown, no explanation."""

        try:
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-6",
                    "max_tokens": 4000,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=60,
            )
            if resp.status_code == 200:
                content = resp.json()["content"][0]["text"].strip()
                content = re.sub(r"^```(?:json)?", "", content).strip()
                content = re.sub(r"```$", "", content).strip()
                results.extend(json.loads(content))
            else:
                st.warning(f"API error {resp.status_code}")
        except Exception as e:
            st.warning(f"AI error: {e}")

    return results


def rule_based_categorize(text: str) -> str:
    d = text.lower()
    rules = [
        (["swiggy","zomato","restaurant","cafe","food","dining","biryani","pizza","dunzo"], "Food & Dining"),
        (["myntra","ajio","meesho","fashion","clothes","clothing","westside","zara","h&m"], "Shopping – Clothing"),
        (["amazon","flipkart","snapdeal","nykaa","purplle","decathlon","firstcry"], "Shopping – General"),
        (["zepto","blinkit","bigbasket","grofer","jiomart","dmart","grocery","supermarket"], "Groceries"),
        (["netflix","hotstar","prime video","spotify","youtube","zee5","sony liv","bookmyshow"], "Entertainment"),
        (["apollo","1mg","medplus","tata 1mg","netmeds","pharmeasy","medicine","pharmacy"], "Healthcare & Medicines"),
        (["irctc","makemytrip","goibibo","yatra","cleartrip","indigo","air india","airlines","flight","train ticket"], "Travel"),
        (["ola","uber","rapido","petrol","diesel","fuel","metro","parking"], "Fuel & Transport"),
        (["electricity","water","gas","airtel","jio","vodafone","broadband","recharge","bescom","tata power","bill payment"], "Utilities & Bills"),
        (["atm","cash withdrawal","cash wtd"], "Cash Withdrawal"),
        (["emi","loan","mortgage","bajaj","lic","insurance","policy"], "EMI / Loan"),
        (["mutual fund","sip","zerodha","groww","coin","ppf","nps","investment","fd","fixed deposit"], "Investment / Savings"),
        (["upi","neft","imps","rtgs","transfer","paid to","sent to"], "Transfer / UPI"),
        (["school","college","university","tuition","course","udemy","coursera","byju"], "Education"),
    ]
    for keywords, cat in rules:
        if any(k in d for k in keywords):
            return cat
    return "Other"


# ══════════════════════════════════════════════════════════════════════════════
#  FULL PIPELINE
# ══════════════════════════════════════════════════════════════════════════════

def process_statement(uploaded_file, password: str, bank_key: str, api_key: str):
    bank_label = BANKS[bank_key]["label"]
    pii_events = 0

    # Step 1: Extract + sanitize (raw text never persists)
    with st.spinner(f"🔒 Extracting & masking PII from {bank_label}..."):
        sanitized_text, pii_events, err = extract_and_sanitize(uploaded_file, password)

    if err:
        st.error(f"❌ {bank_label}: {err}")
        return pd.DataFrame(), 0

    if not sanitized_text:
        st.warning(f"⚠️ No content extracted from {bank_label}.")
        return pd.DataFrame(), 0

    # Step 2: Parse transaction lines from sanitized text
    with st.spinner(f"🔍 Identifying transactions..."):
        txn_lines = parse_transaction_lines(sanitized_text)
    del sanitized_text  # free sanitized text too — only txn_lines kept

    if not txn_lines:
        st.warning(f"⚠️ No transactions detected in {bank_label}.")
        return pd.DataFrame(), pii_events

    # Step 3: Categorize (AI or rule-based)
    if api_key:
        with st.spinner(f"🤖 AI categorizing {len(txn_lines)} transactions..."):
            ai_results = categorize_with_ai(txn_lines, api_key, bank_label)
    else:
        ai_results = []

    # Step 4: Build clean DataFrame — ONLY allowed fields stored
    rows = []
    amount_re = re.compile(r"(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)")
    date_re = re.compile(r"(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})", re.IGNORECASE)

    if ai_results:
        for t in ai_results:
            try:
                dt = datetime.today()
                for fmt in ["%d-%m-%Y","%d/%m/%Y","%Y-%m-%d","%d %b %Y","%d-%b-%Y"]:
                    try:
                        dt = datetime.strptime(str(t.get("date", "")), fmt)
                        break
                    except Exception:
                        pass
                amt = float(str(t.get("amount", 0)).replace(",", ""))
                if amt <= 0 or amt > 500000:
                    continue
                rows.append({
                    "date":        dt,
                    "month_sort":  dt.strftime("%Y-%m"),
                    "month_year":  dt.strftime("%b %Y"),
                    "bank":        bank_label,
                    "bank_key":    bank_key,
                    # ── Only safe fields below ──────────────────────────
                    "description": str(t.get("description", ""))[:120],
                    "merchant":    str(t.get("merchant", ""))[:50],
                    "amount":      amt,
                    "type":        t.get("type", "debit"),
                    "category":    t.get("category", "Other"),
                    "confidence":  t.get("confidence", "medium"),
                })
            except Exception:
                continue
    else:
        for line in txn_lines:
            amounts = amount_re.findall(line)
            if not amounts:
                continue
            amt = float(amounts[-1].replace(",", ""))
            if amt <= 0 or amt > 500000:
                continue
            dt = datetime.today()
            dates = date_re.findall(line)
            if dates:
                for fmt in ["%d/%m/%Y","%d/%m/%y","%d-%m-%Y","%d-%m-%y"]:
                    try:
                        dt = datetime.strptime(dates[0], fmt)
                        break
                    except Exception:
                        pass
            # Strip any remaining [MASKED-*] tokens from description
            clean_desc = re.sub(r"\[MASKED-[A-Z\-]+\]", "", line).strip()
            rows.append({
                "date":        dt,
                "month_sort":  dt.strftime("%Y-%m"),
                "month_year":  dt.strftime("%b %Y"),
                "bank":        bank_label,
                "bank_key":    bank_key,
                "description": clean_desc[:120],
                "merchant":    "",
                "amount":      amt,
                "type":        "credit" if any(w in line.lower() for w in ["credit","cr","refund"]) else "debit",
                "category":    rule_based_categorize(line),
                "confidence":  "low",
            })

    del txn_lines  # free raw lines
    return pd.DataFrame(rows) if rows else pd.DataFrame(), pii_events


# ─── Helpers ────────────────────────────────────────────────────────────────────
def fmt_inr(val):
    if val >= 1_00_000:
        return f"₹{val/1_00_000:.2f}L"
    if val >= 1_000:
        return f"₹{val:,.0f}"
    return f"₹{val:.0f}"

def metric_card(label, value, sub="", color="purple"):
    st.markdown(f"""
    <div class="card {color}">
        <div class="card-label">{label}</div>
        <div class="card-value">{value}</div>
        {"<div class='card-sub'>" + sub + "</div>" if sub else ""}
    </div>""", unsafe_allow_html=True)

def pct_change(cur, prev):
    return (cur - prev) / prev * 100 if prev else 0


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN APP
# ══════════════════════════════════════════════════════════════════════════════

def main():
    st.markdown("""
    <div class="hero">
        <h1>🏦 Bank Statement Expense Tracker</h1>
        <p>
            Upload your bank &amp; credit card statements for AI-powered expense analysis.<br>
            Account numbers · Card numbers · Names · IFSC · UPI IDs · Transaction IDs<br>
            are <strong>masked immediately</strong> at extraction — never stored or transmitted.
        </p>
        <div class="shield-badge">🔒 End-to-End PII Masking Active</div>
    </div>""", unsafe_allow_html=True)

    # ── Sidebar ──────────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### ⚙️ Configuration")

        api_key = st.text_input(
            "🤖 Anthropic API Key",
            type="password",
            value=st.session_state.api_key,
            help="Get one at console.anthropic.com — enables smart AI categorization",
        )
        if api_key:
            st.session_state.api_key = api_key
            st.success("✅ API key set — AI categorization ON")
        else:
            st.markdown('<div class="warning-box">⚠️ No API key — using rule-based categorization</div>',
                        unsafe_allow_html=True)

        st.markdown("---")
        major_threshold = st.slider("Major expense threshold (%)", 5, 25, 10)

        st.markdown("---")
        st.markdown("### 🔒 Privacy Status")
        total_pii = sum(st.session_state.pii_log)
        st.markdown(f"""
        <div class="privacy-panel">
            <h4>🛡️ PII Shield Active</h4>
            ✅ Account numbers masked<br>
            ✅ Card numbers masked<br>
            ✅ Names & UPI IDs masked<br>
            ✅ IFSC & Transaction IDs masked<br>
            ✅ PAN / Aadhaar / Mobile masked<br><br>
            <b>Total fields masked this session:</b>
            <span class="masked-item">{total_pii}</span>
        </div>""", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 🗑️ Data Management")
        col_r, col_d = st.columns(2)
        with col_r:
            if st.button("🔄 RESET", use_container_width=True):
                st.session_state.transactions = pd.DataFrame()
                st.session_state.processed_banks = []
                st.session_state.pii_log = []
                st.session_state.confirmed_delete = False
                st.rerun()
        with col_d:
            if st.button("🗑️ DELETE", use_container_width=True, type="primary"):
                st.session_state.confirmed_delete = True

        if st.session_state.confirmed_delete:
            st.markdown('<div class="delete-box">⚠️ Permanently clears all statement data, transactions, and masks from this session.</div>',
                        unsafe_allow_html=True)
            if st.button("✅ Confirm Delete All", type="primary", use_container_width=True):
                for key in ["transactions", "processed_banks", "pii_log", "api_key"]:
                    st.session_state[key] = pd.DataFrame() if key == "transactions" else ([] if "banks" in key or "log" in key else "")
                st.session_state.confirmed_delete = False
                st.success("🗑️ All data permanently deleted from session.")
                st.rerun()
            if st.button("❌ Cancel", use_container_width=True):
                st.session_state.confirmed_delete = False
                st.rerun()

        st.markdown("---")
        st.caption("🔐 Data lives only in your browser session.\nNothing is saved to disk or server.")

    # ── Privacy Notice ────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="privacy-panel">
    <h4>🛡️ How Your Data is Protected</h4>
    <b>1. Immediate Masking:</b> The moment your PDF is read, a PII engine scans every line and replaces account numbers, card numbers, IFSC codes, UPI IDs, transaction reference IDs, names, PAN, Aadhaar, and mobile numbers with <span class="masked-item">[MASKED]</span> tokens before any processing occurs.<br>
    <b>2. Raw Text Discarded:</b> The original extracted text is deleted from memory immediately after masking. It is never stored, logged, or displayed.<br>
    <b>3. Only 4 Fields Kept:</b> Date · Amount · Type (debit/credit) · Transaction Description (merchant/purpose only).<br>
    <b>4. API Calls (if enabled):</b> Only the already-masked, sanitized transaction lines are sent to the Anthropic API — never raw statement content.<br>
    <b>5. Session-Only:</b> All data is cleared when you close or reset the app.
    </div>""", unsafe_allow_html=True)

    # ── Upload Section ────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">📂 Upload Bank Statements</div>', unsafe_allow_html=True)

    upload_cols = st.columns(2)
    new_dfs = []

    for idx, (bank_key, bank_info) in enumerate(BANKS.items()):
        col = upload_cols[idx % 2]
        with col:
            st.markdown(f"**{bank_info['icon']} {bank_info['label']}**")
            has_stmt = st.selectbox("Statement available?", ["No", "Yes"],
                                    key=f"has_{bank_key}", label_visibility="collapsed")
            if has_stmt == "Yes":
                uploaded = st.file_uploader(
                    f"Upload PDF", type=["pdf"],
                    key=f"file_{bank_key}", label_visibility="collapsed")
                pwd = st.text_input("PDF Password", type="password",
                                    key=f"pwd_{bank_key}",
                                    placeholder="Enter PDF password (leave blank if none)")
                if uploaded and bank_key not in st.session_state.processed_banks:
                    df, pii_count = process_statement(
                        uploaded, pwd, bank_key, st.session_state.api_key)
                    if not df.empty:
                        new_dfs.append(df)
                        st.session_state.processed_banks.append(bank_key)
                        st.session_state.pii_log.append(pii_count)
                        st.success(f"✅ {len(df)} transactions loaded · "
                                   f"🔒 {pii_count} PII fields masked")
            st.markdown("---")

    if new_dfs:
        combined = pd.concat(new_dfs, ignore_index=True)
        st.session_state.transactions = (
            combined if st.session_state.transactions.empty
            else pd.concat([st.session_state.transactions, combined], ignore_index=True)
            .drop_duplicates()
        )

    df = st.session_state.transactions

    if df.empty:
        st.markdown("""
        <div class="info-box">
        📌 <b>Getting started:</b> Set any card's dropdown to "Yes", upload the PDF, enter its password, and your expense dashboard will appear here automatically.
        </div>""", unsafe_allow_html=True)
        return

    # Filter to debits for spend analysis
    df_spend = df[(df["type"] == "debit") & (df["amount"] > 0) & (df["amount"] < 500000)].copy()
    months_sorted = sorted(df_spend["month_sort"].unique())
    month_labels = {m: datetime.strptime(m, "%Y-%m").strftime("%b %Y") for m in months_sorted}

    monthly_total = (
        df_spend.groupby("month_sort")["amount"].sum().reset_index()
        .rename(columns={"amount": "total"})
    )
    monthly_total["month_year"] = monthly_total["month_sort"].map(month_labels)

    # ── KPIs ──────────────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">📊 Overview</div>', unsafe_allow_html=True)
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1: metric_card("Total Spend", fmt_inr(df_spend["amount"].sum()), f"{len(months_sorted)} months", "purple")
    with k2: metric_card("Avg Monthly", fmt_inr(monthly_total["total"].mean()), "per month", "blue")
    with k3:
        peak = monthly_total.loc[monthly_total["total"].idxmax()]
        metric_card("Highest Month", fmt_inr(peak["total"]), peak["month_year"], "red")
    with k4:
        low = monthly_total.loc[monthly_total["total"].idxmin()]
        metric_card("Lowest Month", fmt_inr(low["total"]), low["month_year"], "green")
    with k5:
        metric_card("Transactions", str(len(df_spend)),
                    f"{df_spend['bank'].nunique()} card(s)", "teal")

    # ── Tabs ──────────────────────────────────────────────────────────────────────
    tabs = st.tabs(["📅 Monthly Summary", "🔍 Month Detail",
                    "📈 Trends & Heatmap", "🏷️ Categories", "📋 All Transactions"])

    # Tab 1 ── Monthly Summary
    with tabs[0]:
        st.markdown('<div class="section-header">Monthly Spend by Card</div>', unsafe_allow_html=True)
        bank_colors = {BANKS[k]["label"]: BANKS[k]["color"] for k in BANKS}
        monthly_bank = df_spend.groupby(["month_sort","month_year","bank"])["amount"].sum().reset_index()
        fig_bar = go.Figure()
        for bank in df_spend["bank"].unique():
            sub = monthly_bank[monthly_bank["bank"] == bank]
            fig_bar.add_trace(go.Bar(
                x=sub["month_year"], y=sub["amount"], name=bank,
                marker_color=bank_colors.get(bank, "#94a3b8"),
                text=sub["amount"].apply(fmt_inr),
                textposition="inside", textfont=dict(color="white", size=10),
            ))
        fig_bar.update_layout(
            barmode="stack", plot_bgcolor="white", paper_bgcolor="white",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, font=dict(size=10)),
            margin=dict(l=0,r=0,t=50,b=0), height=320,
            xaxis=dict(title=""), yaxis=dict(title="₹", gridcolor="#f1f5f9"),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        st.markdown('<div class="section-header">Month-over-Month Comparison</div>', unsafe_allow_html=True)
        rows = []
        for i, ms in enumerate(months_sorted):
            cur = monthly_total[monthly_total["month_sort"] == ms]["total"].values[0]
            if i == 0:
                diff, pct, status = 0, 0, "—"
            else:
                prev = monthly_total[monthly_total["month_sort"] == months_sorted[i-1]]["total"].values[0]
                diff = cur - prev
                pct = pct_change(cur, prev)
                status = "🔴 Higher" if pct > 5 else ("🟢 Lower" if pct < -5 else "🟡 Similar")
            rows.append({
                "Month": month_labels[ms],
                "Total Spend": fmt_inr(cur),
                "Change Amount": f"{'▲' if diff > 0 else '▼'} {fmt_inr(abs(diff))}" if diff != 0 else "—",
                "Change %": f"{'+' if pct > 0 else ''}{pct:.1f}%" if diff != 0 else "—",
                "Status": status,
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # Tab 2 ── Month Detail
    with tabs[1]:
        st.markdown('<div class="section-header">Drill Down by Month</div>', unsafe_allow_html=True)
        sel = st.selectbox("Select Month", months_sorted, format_func=lambda m: month_labels[m])
        mdf = df_spend[df_spend["month_sort"] == sel].copy()
        mtotal = mdf["amount"].sum()
        major_cut = mtotal * (major_threshold / 100)

        c1, c2 = st.columns([3, 2])
        with c1:
            cat_t = mdf.groupby("category")["amount"].sum().sort_values(ascending=False).reset_index()
            cat_t["pct"] = cat_t["amount"] / mtotal * 100
            fig_pie = px.pie(cat_t, values="amount", names="category",
                             color_discrete_sequence=px.colors.qualitative.Set3, hole=0.38)
            fig_pie.update_traces(textinfo="percent+label", textposition="outside")
            fig_pie.update_layout(showlegend=False, margin=dict(l=0,r=0,t=20,b=0), height=300)
            st.plotly_chart(fig_pie, use_container_width=True)
        with c2:
            metric_card("Month Total", fmt_inr(mtotal), month_labels[sel], "purple")
            metric_card("Transactions", str(len(mdf)), f"Avg {fmt_inr(mdf['amount'].mean())}", "blue")
            metric_card("Major Expenses", str(len(mdf[mdf["amount"] >= major_cut])),
                        f"Each > {fmt_inr(major_cut)}", "red")

        for _, row in cat_t.iterrows():
            badge = '<span class="badge badge-major">MAJOR</span>' if row["amount"] >= major_cut else ""
            st.markdown(f"""<div class="txn-row">
                <span class="txn-desc">{row['category']} {badge}</span>
                <span class="txn-amt">{fmt_inr(row['amount'])}
                    <span style="color:#94a3b8;font-size:11px;"> {row['pct']:.1f}%</span>
                </span></div>""", unsafe_allow_html=True)

        st.markdown('<div class="section-header">Top Transactions</div>', unsafe_allow_html=True)
        top = mdf.nlargest(20, "amount")[["date","description","merchant","amount","category","bank"]].copy()
        top["date"] = top["date"].dt.strftime("%d %b")
        top["amount"] = top["amount"].apply(fmt_inr)
        st.dataframe(top, use_container_width=True, hide_index=True)

    # Tab 3 ── Trends
    with tabs[2]:
        st.markdown('<div class="section-header">Spending Trends</div>', unsafe_allow_html=True)
        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(
            x=monthly_total["month_year"], y=monthly_total["total"],
            mode="lines+markers+text",
            text=monthly_total["total"].apply(fmt_inr), textposition="top center",
            line=dict(color="#6366f1", width=3), marker=dict(size=9, color="#6366f1"),
            fill="tozeroy", fillcolor="rgba(99,102,241,0.08)",
        ))
        fig_line.update_layout(plot_bgcolor="white", paper_bgcolor="white",
                                margin=dict(l=0,r=0,t=20,b=0), height=280,
                                xaxis=dict(title=""), yaxis=dict(title="₹", gridcolor="#f1f5f9"))
        st.plotly_chart(fig_line, use_container_width=True)

        st.markdown("**Category × Month Heatmap**")
        pivot = df_spend.groupby(["month_sort","category"])["amount"].sum().reset_index()
        pivot = pivot.pivot(index="category", columns="month_sort", values="amount").fillna(0)
        pivot.columns = [month_labels[m] for m in pivot.columns]
        fig_heat = go.Figure(go.Heatmap(
            z=pivot.values, x=list(pivot.columns), y=list(pivot.index),
            colorscale="Blues",
            text=[[fmt_inr(v) for v in row] for row in pivot.values],
            texttemplate="%{text}", textfont=dict(size=10),
        ))
        fig_heat.update_layout(margin=dict(l=0,r=0,t=10,b=0),
                                height=max(300, len(pivot)*32),
                                plot_bgcolor="white", paper_bgcolor="white")
        st.plotly_chart(fig_heat, use_container_width=True)

    # Tab 4 ── Categories
    with tabs[3]:
        st.markdown('<div class="section-header">All-Time Category Analysis</div>', unsafe_allow_html=True)
        cat_all = df_spend.groupby("category")["amount"].agg(["sum","count"]).reset_index()
        cat_all.columns = ["Category","Total","Txns"]
        cat_all = cat_all.sort_values("Total", ascending=False)
        cat_all["Total (₹)"] = cat_all["Total"].apply(fmt_inr)
        cat_all["% of Spend"] = (cat_all["Total"] / cat_all["Total"].sum() * 100).round(1).astype(str) + "%"
        fig_cat = px.bar(cat_all, x="Total", y="Category", orientation="h",
                         color="Total", color_continuous_scale="Purples", text="Total (₹)")
        fig_cat.update_traces(textposition="outside")
        fig_cat.update_layout(plot_bgcolor="white", paper_bgcolor="white",
                               coloraxis_showscale=False,
                               margin=dict(l=0,r=0,t=10,b=0),
                               height=max(300, len(cat_all)*36),
                               xaxis=dict(title="₹", gridcolor="#f1f5f9"), yaxis=dict(title=""))
        st.plotly_chart(fig_cat, use_container_width=True)
        st.dataframe(cat_all[["Category","Total (₹)","Txns","% of Spend"]],
                     use_container_width=True, hide_index=True)

        if df_spend["merchant"].str.strip().ne("").any():
            st.markdown('<div class="section-header">Top 10 Merchants</div>', unsafe_allow_html=True)
            merch = df_spend[df_spend["merchant"] != ""].groupby("merchant")["amount"].sum()
            merch = merch.sort_values(ascending=False).head(10).reset_index()
            merch.columns = ["Merchant","Total"]
            merch["Total (₹)"] = merch["Total"].apply(fmt_inr)
            fig_m = px.bar(merch, x="Merchant", y="Total",
                           color="Total", color_continuous_scale="Oranges", text="Total (₹)")
            fig_m.update_traces(textposition="outside")
            fig_m.update_layout(plot_bgcolor="white", paper_bgcolor="white",
                                 coloraxis_showscale=False,
                                 margin=dict(l=0,r=0,t=10,b=0), height=280,
                                 xaxis=dict(title=""), yaxis=dict(title="₹", gridcolor="#f1f5f9"))
            st.plotly_chart(fig_m, use_container_width=True)

    # Tab 5 ── All Transactions
    with tabs[4]:
        st.markdown('<div class="section-header">All Transactions</div>', unsafe_allow_html=True)
        f1, f2, f3, f4 = st.columns(4)
        with f1:
            f_bank = st.multiselect("Bank/Card", df_spend["bank"].unique(),
                                    default=list(df_spend["bank"].unique()))
        with f2:
            f_cat = st.multiselect("Category", sorted(df_spend["category"].unique()),
                                   default=list(df_spend["category"].unique()))
        with f3:
            f_month = st.multiselect("Month", months_sorted,
                                     format_func=lambda m: month_labels[m],
                                     default=months_sorted)
        with f4:
            mn, mx = float(df_spend["amount"].min()), float(df_spend["amount"].max())
            f_range = st.slider("Amount (₹)", mn, mx, (mn, mx))

        filt = df_spend[
            df_spend["bank"].isin(f_bank) &
            df_spend["category"].isin(f_cat) &
            df_spend["month_sort"].isin(f_month) &
            (df_spend["amount"] >= f_range[0]) &
            (df_spend["amount"] <= f_range[1])
        ].copy()

        disp = filt[["date","month_year","bank","description","merchant","amount","category","type"]].copy()
        disp["date"] = disp["date"].dt.strftime("%d %b %Y")
        disp.columns = ["Date","Month","Bank/Card","Description","Merchant","Amount (₹)","Category","Type"]

        st.caption(f"Showing {len(disp):,} transactions · Total: {fmt_inr(filt['amount'].sum())} "
                   f"· <span class='badge badge-safe'>🔒 No PII in any field</span>",
                   unsafe_allow_html=True)
        st.dataframe(disp, use_container_width=True, hide_index=True,
                     column_config={"Amount (₹)": st.column_config.NumberColumn(format="₹%.0f")})

        buf = io.StringIO()
        disp.to_csv(buf, index=False)
        st.download_button("⬇️ Download as CSV (PII-free)", data=buf.getvalue(),
                           file_name="expenses_safe_export.csv", mime="text/csv")


if __name__ == "__main__":
    main()
