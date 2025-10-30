import pandas as pd

# Load the uploaded CSV
input_file = "fixed_dates.csv"
output_file = "fixed_dates_cleaned.csv"

# Read the CSV safely
df = pd.read_csv(input_file)

# --- Preserve 'Ticker' column if it exists ---
ticker_col = None
for c in df.columns:
    if 'ticker' in c.lower():
        ticker_col = c
        break

# --- Identify and format the Date column ---
date_col = None
for c in df.columns:
    if 'date' in c.lower():
        date_col = c
        break
if not date_col:
    # Choose column with most parseable dates
    parse_counts = {c: pd.to_datetime(df[c], errors='coerce').notna().sum() for c in df.columns}
    date_col = max(parse_counts, key=parse_counts.get)

df[date_col] = pd.to_datetime(df[date_col], errors='coerce', dayfirst=True)
df = df.dropna(subset=[date_col])
df[date_col] = df[date_col].dt.strftime('%Y-%m-%d')

# --- Format numeric columns (CHLO, Change, etc.) ---
for c in df.columns:
    if c not in [ticker_col, date_col]:
        df[c] = (
            df[c].astype(str)
            .str.replace(r'[^0-9.\-]', '', regex=True)
            .replace('', None)
        )
        df[c] = pd.to_numeric(df[c], errors='coerce').round(2)

# --- Reorder columns: Ticker first (if exists), then Date ---
if ticker_col:
    cols = [ticker_col, date_col] + [c for c in df.columns if c not in [ticker_col, date_col]]
else:
    cols = [date_col] + [c for c in df.columns if c != date_col]

df = df[cols]

# --- Save cleaned CSV ---
df.to_csv(output_file, index=False)

print(f"✅ Cleaned file saved as: {output_file}")
