import pandas as pd
import os

# 1. Check if file exists
csv_path = "/home/sysadm/Music/My_Agentic_Ai/data/schedule_export.csv"

if not os.path.exists(csv_path):
    print(f"❌ ERROR: File not found at {csv_path}")
    print("   -> Did you rename 'events (1).csv' to 'schedule_export.csv'?")
    print("   -> Did you put it inside the 'data' folder?")
    exit()

print(f"✅ File found: {csv_path}")

# 2. Check content
try:
    df = pd.read_csv(csv_path, dtype=str).fillna("")
    print(f"✅ Loaded CSV with {len(df)} rows.")
    print(f"   Columns found: {list(df.columns)}")
    
    # 3. Search for DLCS specifically
    # We look in ALL columns just in case
    mask = df.apply(lambda x: x.astype(str).str.contains("ENG", case=False)).any(axis=1)
    dlcs_rows = df[mask]
    
    if not dlcs_rows.empty:
        print(f"\n🎉 SUCCESS! Found {len(dlcs_rows)} rows containing 'ENG':")
        print(dlcs_rows[["Name", "Title", "Day Of Week", "Published Start", "Location"]])
    else:
        print("\n❌ ERROR: CSV is readable, but contains NO 'DLCS' rows.")
        print("   -> Verify you didn't accidentally overwrite the file with an empty export.")

except Exception as e:
    print(f"❌ CRITICAL ERROR reading CSV: {e}")