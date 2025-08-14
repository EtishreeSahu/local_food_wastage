import pandas as pd
import sqlite3
from datetime import datetime
import re
import os

# ---------- Helper cleaning functions ----------
def clean_phone(phone):
    if pd.isna(phone):
        return None
    s = str(phone)
    digits = re.sub(r'\D', '', s)  # keep digits only
    return digits if digits else None

def parse_date(val):
    if pd.isna(val):
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(str(val).strip(), fmt).date().isoformat()
        except:
            continue
    try:
        return pd.to_datetime(val).date().isoformat()
    except:
        return None

# ---------- 1. Load CSVs ----------
providers = pd.read_csv("data/providers_data.csv")
receivers = pd.read_csv("data/receivers_data.csv")
food = pd.read_csv("data/food_listings_data.csv")
claims = pd.read_csv("data/claims_data.csv")

print("providers shape:", providers.shape)
print("receivers shape:", receivers.shape)
print("food shape:", food.shape)
print("claims shape:", claims.shape)

# ---------- 2. Clean Providers ----------
providers.columns = [c.strip() for c in providers.columns]
receivers.columns = [c.strip() for c in receivers.columns]
food.columns = [c.strip() for c in food.columns]
claims.columns = [c.strip() for c in claims.columns]

providers['Provider_ID'] = pd.to_numeric(providers['Provider_ID'], errors='coerce').astype('Int64')
providers['Name'] = providers['Name'].astype(str).str.strip()
providers['Type'] = providers['Type'].astype(str).str.strip()
providers['City'] = providers['City'].astype(str).str.strip()
providers['Contact'] = providers['Contact'].apply(clean_phone)
providers['Address'] = providers.get('Address', '').fillna('').astype(str).str.strip()

# ---------- 3. Clean Receivers ----------
receivers['Receiver_ID'] = pd.to_numeric(receivers['Receiver_ID'], errors='coerce').astype('Int64')
receivers['Name'] = receivers['Name'].astype(str).str.strip()
receivers['Type'] = receivers['Type'].astype(str).str.strip()
receivers['City'] = receivers['City'].astype(str).str.strip()
receivers['Contact'] = receivers['Contact'].apply(clean_phone)

# ---------- 4. Clean Food Listings ----------
food['Food_ID'] = pd.to_numeric(food['Food_ID'], errors='coerce').astype('Int64')
food['Food_Name'] = food['Food_Name'].astype(str).str.strip()
food['Quantity'] = pd.to_numeric(food['Quantity'], errors='coerce').fillna(0).astype(int)
food['Expiry_Date'] = food.get('Expiry_Date', None).apply(parse_date)
food['Provider_ID'] = pd.to_numeric(food['Provider_ID'], errors='coerce').astype('Int64')
food['Provider_Type'] = food.get('Provider_Type', '').astype(str).str.strip()
food['Location'] = food.get('Location', '').astype(str).str.strip()
food['Food_Type'] = food.get('Food_Type', '').astype(str).str.strip()
food['Meal_Type'] = food.get('Meal_Type', '').astype(str).str.strip()

# ---------- 5. Clean Claims ----------
claims['Claim_ID'] = pd.to_numeric(claims['Claim_ID'], errors='coerce').astype('Int64')
claims['Food_ID'] = pd.to_numeric(claims['Food_ID'], errors='coerce').astype('Int64')
claims['Receiver_ID'] = pd.to_numeric(claims['Receiver_ID'], errors='coerce').astype('Int64')
claims['Status'] = claims['Status'].astype(str).str.strip().fillna('Pending')
claims['Timestamp'] = claims.get('Timestamp', None).apply(parse_date)

# ---------- 6. Create SQLite DB ----------
if os.path.exists("local_food_wastage.db"):
    os.remove("local_food_wastage.db")  # start fresh

conn = sqlite3.connect('local_food_wastage.db')
c = conn.cursor()
c.execute("PRAGMA foreign_keys = ON;")

# Create tables
c.execute("""
CREATE TABLE providers (
    Provider_ID INTEGER PRIMARY KEY,
    Name TEXT NOT NULL,
    Type TEXT,
    Address TEXT,
    City TEXT,
    Contact TEXT
);
""")
c.execute("""
CREATE TABLE receivers (
    Receiver_ID INTEGER PRIMARY KEY,
    Name TEXT NOT NULL,
    Type TEXT,
    City TEXT,
    Contact TEXT
);
""")
c.execute("""
CREATE TABLE food_listings (
    Food_ID INTEGER PRIMARY KEY,
    Food_Name TEXT,
    Quantity INTEGER,
    Expiry_Date DATE,
    Provider_ID INTEGER,
    Provider_Type TEXT,
    Location TEXT,
    Food_Type TEXT,
    Meal_Type TEXT,
    FOREIGN KEY(Provider_ID) REFERENCES providers(Provider_ID) ON DELETE SET NULL
);
""")
c.execute("""
CREATE TABLE claims (
    Claim_ID INTEGER PRIMARY KEY,
    Food_ID INTEGER,
    Receiver_ID INTEGER,
    Status TEXT,
    Timestamp DATETIME,
    FOREIGN KEY(Food_ID) REFERENCES food_listings(Food_ID) ON DELETE CASCADE,
    FOREIGN KEY(Receiver_ID) REFERENCES receivers(Receiver_ID) ON DELETE SET NULL
);
""")
conn.commit()

# ---------- 7. Insert data (no foreign key issues) ----------
conn.execute("PRAGMA foreign_keys = OFF;")  # disable temporarily

providers.to_sql('providers', conn, if_exists='append', index=False)
receivers.to_sql('receivers', conn, if_exists='append', index=False)
food.to_sql('food_listings', conn, if_exists='append', index=False)
claims.to_sql('claims', conn, if_exists='append', index=False)

conn.execute("PRAGMA foreign_keys = ON;")  # re-enable

print("Database created & data inserted successfully ✅")

conn.close()
