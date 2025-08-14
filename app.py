# app.py
import streamlit as st
import sqlite3
import pandas as pd
import io

DB_PATH = "local_food_wastage.db"

st.set_page_config(page_title="Local Food Wastage Management", layout="wide")

def get_conn():
    return sqlite3.connect(DB_PATH)

def db_exists():
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cur.fetchall()
        conn.close()
        return len(tables) > 0
    except Exception:
        return False

def to_csv_download(df, name="data.csv"):
    csv_bytes = df.to_csv(index=False).encode('utf-8')  # convert to bytes
    st.download_button(
        f"Download {name}",
        data=csv_bytes,
        file_name=name,
        mime="text/csv"
    )


st.title("Local Food Wastage Management System")

if not db_exists():
    st.error("Database not found. Run your pipeline to create local_food_wastage.db, then reload this app.")
    st.stop()

# ---------- Utility helpers ----------
def run_query(sql, params=None):
    conn = get_conn()
    df = pd.read_sql_query(sql, conn, params=params or ())
    conn.close()
    return df

def exec_sql(sql, params=None):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql, params or ())
    conn.commit()
    conn.close()

# ---------- Sidebar quick filters (used across app) ----------
with st.sidebar:
    st.header("Quick Filters")
    # populate dynamic filters
    conn = get_conn()
    cities = ["All"] + sorted([r[0] for r in conn.execute("SELECT DISTINCT Location FROM food_listings WHERE Location IS NOT NULL").fetchall() if r[0]])
    food_types = ["All"] + sorted([r[0] for r in conn.execute("SELECT DISTINCT Food_Type FROM food_listings WHERE Food_Type IS NOT NULL").fetchall() if r[0]])
    providers_list = ["All"] + sorted([r[0] for r in conn.execute("SELECT DISTINCT Name FROM providers WHERE Name IS NOT NULL").fetchall() if r[0]])
    conn.close()

    quick_city = st.selectbox("City filter (quick)", cities)
    quick_food_type = st.selectbox("Food Type (quick)", food_types)
    quick_provider = st.selectbox("Provider (quick)", providers_list)
    st.markdown("---")
    st.write("DB summary")
    conn = get_conn()
    counts = conn.execute("""
        SELECT
          (SELECT COUNT(*) FROM providers) as providers,
          (SELECT COUNT(*) FROM receivers) as receivers,
          (SELECT COUNT(*) FROM food_listings) as food_listings,
          (SELECT COUNT(*) FROM claims) as claims
    """).fetchone()
    conn.close()
    st.write(f"Providers: {counts[0]}  •  Receivers: {counts[1]}")
    st.write(f"Food Listings: {counts[2]}  •  Claims: {counts[3]}")

# ---------- Main layout: tabs ----------
tabs = st.tabs(["Dashboard", "Listings (Filters + CRUD)", "Providers / Receivers", "Claims", "Queries"])

# ---------------- DASHBOARD ----------------
with tabs[0]:
    st.header("Dashboard")
    # KPIs
    k1 = run_query("SELECT COUNT(*) AS total_providers FROM providers").iloc[0,0]
    k2 = run_query("SELECT COUNT(*) AS total_receivers FROM receivers").iloc[0,0]
    k3 = run_query("SELECT SUM(Quantity) AS total_quantity FROM food_listings").iloc[0,0] or 0
    k4 = run_query("SELECT COUNT(*) AS total_claims FROM claims").iloc[0,0]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Providers", int(k1))
    col2.metric("Receivers", int(k2))
    col3.metric("Total Quantity Available", int(k3))
    col4.metric("Total Claims", int(k4))

    st.markdown("### Most Common Food Types")
    df_common = run_query("""
        SELECT Food_Type, COUNT(*) as cnt
        FROM food_listings
        GROUP BY Food_Type
        ORDER BY cnt DESC
        LIMIT 10
    """)
    if not df_common.empty:
        st.bar_chart(df_common.set_index("Food_Type"))

    st.markdown("### Monthly Claims Trend")
    df_monthly = run_query("""
        SELECT substr(Timestamp, 1, 7) as month, COUNT(*) as claims_count
        FROM claims
        WHERE Timestamp IS NOT NULL
        GROUP BY month
        ORDER BY month;
    """)
    if not df_monthly.empty:
        st.line_chart(df_monthly.set_index("month"))

# ---------------- LISTINGS ----------------
with tabs[1]:
    st.header("Available Food Listings")
    # Filters (more advanced)
    city_filter = st.selectbox("City (all)", ["All"] + sorted([v for v in run_query("SELECT DISTINCT Location FROM food_listings")["Location"].dropna()]))
    food_type_filter = st.selectbox("Food Type (all)", ["All"] + sorted([v for v in run_query("SELECT DISTINCT Food_Type FROM food_listings")["Food_Type"].dropna()]))
    food_name_filter = st.selectbox("Food Name (all)", ["All"] + sorted([v for v in run_query("SELECT DISTINCT Food_Name FROM food_listings")["Food_Name"].dropna()]))
    provider_filter = st.selectbox("Provider (all)", ["All"] + sorted([v for v in run_query("SELECT DISTINCT Name FROM providers")["Name"].dropna()]))

    q = "SELECT * FROM food_listings WHERE 1=1"
    params = []
    if city_filter != "All":
        q += " AND Location = ?"
        params.append(city_filter)
    if food_type_filter != "All":
        q += " AND Food_Type = ?"
        params.append(food_type_filter)
    if food_name_filter != "All":
        q += " AND Food_Name = ?"
        params.append(food_name_filter)
    if provider_filter != "All":
        # translate provider name to provider_id(s)
        provider_ids = run_query("SELECT Provider_ID FROM providers WHERE Name = ?", (provider_filter,))
        if not provider_ids.empty:
            pid = int(provider_ids.iloc[0,0])
            q += " AND Provider_ID = ?"
            params.append(pid)

    df_food = pd.read_sql_query(q, get_conn(), params=params)
    st.dataframe(df_food)

    # Download CSV of current view
    to_csv_download(df_food, name="filtered_food_listings.csv")

    st.markdown("---")
    st.subheader("Create / Update / Delete Food Listing")
    with st.form("food_form"):
        st.write("Fill details (leave Food_ID blank to create new)")
        fid = st.text_input("Food_ID (for update/delete)")
        fname = st.text_input("Food_Name")
        qty = st.number_input("Quantity", min_value=0, value=1)
        expiry = st.text_input("Expiry_Date (YYYY-MM-DD or blank)")
        provider_id_input = st.text_input("Provider_ID (integer)")
        ptype = st.text_input("Provider_Type")
        location = st.text_input("Location / City")
        ftype = st.text_input("Food_Type")
        mtype = st.text_input("Meal_Type")
        submitted = st.form_submit_button("Submit")
        if submitted:
            conn = get_conn()
            cur = conn.cursor()
            try:
                if fid.strip() == "":
                    # create new (auto primary key if not provided)
                    cur.execute("""
                        INSERT INTO food_listings
                        (Food_Name, Quantity, Expiry_Date, Provider_ID, Provider_Type, Location, Food_Type, Meal_Type)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (fname, int(qty), expiry or None, int(provider_id_input) if provider_id_input else None, ptype, location, ftype, mtype))
                    conn.commit()
                    st.success("New food listing added.")
                else:
                    # update existing
                    cur.execute("""
                        UPDATE food_listings
                        SET Food_Name=?, Quantity=?, Expiry_Date=?, Provider_ID=?, Provider_Type=?, Location=?, Food_Type=?, Meal_Type=?
                        WHERE Food_ID=?
                    """, (fname, int(qty), expiry or None, int(provider_id_input) if provider_id_input else None, ptype, location, ftype, mtype, int(fid)))
                    conn.commit()
                    st.success("Food listing updated.")
            except Exception as e:
                st.error(f"DB error: {e}")
            finally:
                conn.close()

    st.markdown("### Delete a food listing")
    with st.form("delete_food"):
        del_id = st.text_input("Food_ID to delete")
        del_submit = st.form_submit_button("Delete")
        if del_submit:
            if del_id.strip() == "":
                st.error("Provide Food_ID to delete.")
            else:
                try:
                    exec_sql("DELETE FROM food_listings WHERE Food_ID = ?", (int(del_id),))
                    st.success("Deleted food listing.")
                except Exception as e:
                    st.error(f"Error: {e}")

# ---------------- PROVIDERS / RECEIVERS ----------------
with tabs[2]:
    st.header("Providers & Receivers Management")

    left, right = st.columns(2)

    with left:
        st.subheader("Providers")
        df_prov = run_query("SELECT * FROM providers")
        st.dataframe(df_prov)
        to_csv_download(df_prov, name="providers.csv")

        with st.form("provider_form"):
            pid = st.text_input("Provider_ID (leave blank to create)")
            pname = st.text_input("Name")
            ptype = st.text_input("Type")
            paddr = st.text_input("Address")
            pcity = st.text_input("City")
            pcontact = st.text_input("Contact")
            subp = st.form_submit_button("Submit Provider")
            if subp:
                try:
                    conn = get_conn()
                    cur = conn.cursor()
                    if pid.strip() == "":
                        cur.execute("INSERT INTO providers (Name, Type, Address, City, Contact) VALUES (?, ?, ?, ?, ?)",
                                    (pname, ptype, paddr, pcity, pcontact))
                        conn.commit()
                        st.success("Provider added.")
                    else:
                        cur.execute("UPDATE providers SET Name=?, Type=?, Address=?, City=?, Contact=? WHERE Provider_ID=?",
                                    (pname, ptype, paddr, pcity, pcontact, int(pid)))
                        conn.commit()
                        st.success("Provider updated.")
                except Exception as e:
                    st.error(f"Error: {e}")
                finally:
                    conn.close()

        with st.form("delete_provider"):
            dpid = st.text_input("Provider_ID to delete")
            dps = st.form_submit_button("Delete Provider")
            if dps:
                if dpid.strip() == "":
                    st.error("Provide Provider_ID")
                else:
                    try:
                        exec_sql("DELETE FROM providers WHERE Provider_ID = ?", (int(dpid),))
                        st.success("Provider deleted.")
                    except Exception as e:
                        st.error(f"Error: {e}")

    with right:
        st.subheader("Receivers")
        df_recv = run_query("SELECT * FROM receivers")
        st.dataframe(df_recv)
        to_csv_download(df_recv, name="receivers.csv")

        with st.form("receiver_form"):
            rid = st.text_input("Receiver_ID (leave blank to create)")
            rname = st.text_input("Name (receiver)")
            rtype = st.text_input("Type")
            rcity = st.text_input("City")
            rcontact = st.text_input("Contact")
            subr = st.form_submit_button("Submit Receiver")
            if subr:
                try:
                    conn = get_conn()
                    cur = conn.cursor()
                    if rid.strip() == "":
                        cur.execute("INSERT INTO receivers (Name, Type, City, Contact) VALUES (?, ?, ?, ?)",
                                    (rname, rtype, rcity, rcontact))
                        conn.commit()
                        st.success("Receiver added.")
                    else:
                        cur.execute("UPDATE receivers SET Name=?, Type=?, City=?, Contact=? WHERE Receiver_ID=?",
                                    (rname, rtype, rcity, rcontact, int(rid)))
                        conn.commit()
                        st.success("Receiver updated.")
                except Exception as e:
                    st.error(f"Error: {e}")
                finally:
                    conn.close()

        with st.form("delete_receiver"):
            drid = st.text_input("Receiver_ID to delete")
            drs = st.form_submit_button("Delete Receiver")
            if drs:
                if drid.strip() == "":
                    st.error("Provide Receiver_ID")
                else:
                    try:
                        exec_sql("DELETE FROM receivers WHERE Receiver_ID = ?", (int(drid),))
                        st.success("Receiver deleted.")
                    except Exception as e:
                        st.error(f"Error: {e}")

# ---------------- CLAIMS ----------------
with tabs[3]:
    st.header("Claims Management")

    st.subheader("View Claims")
    df_claims = run_query("""
        SELECT c.Claim_ID, c.Food_ID, f.Food_Name, c.Receiver_ID, r.Name as Receiver_Name, c.Status, c.Timestamp
        FROM claims c
        LEFT JOIN food_listings f ON c.Food_ID = f.Food_ID
        LEFT JOIN receivers r ON c.Receiver_ID = r.Receiver_ID
        ORDER BY c.Timestamp DESC
    """)
    st.dataframe(df_claims)
    to_csv_download(df_claims, name="claims.csv")

    st.markdown("### Create a Claim")
    with st.form("create_claim"):
        cf_food_id = st.text_input("Food_ID")
        cf_receiver_id = st.text_input("Receiver_ID")
        cf_status = st.selectbox("Status", ["Pending", "Completed", "Cancelled"])
        cf_ts = st.text_input("Timestamp (YYYY-MM-DD) or leave blank")
        cs = st.form_submit_button("Create Claim")
        if cs:
            if cf_food_id.strip() == "" or cf_receiver_id.strip() == "":
                st.error("Food_ID and Receiver_ID required")
            else:
                try:
                    exec_sql("INSERT INTO claims (Food_ID, Receiver_ID, Status, Timestamp) VALUES (?, ?, ?, ?)",
                             (int(cf_food_id), int(cf_receiver_id), cf_status, cf_ts or None))
                    st.success("Claim created.")
                except Exception as e:
                    st.error(f"Error: {e}")

    st.markdown("### Update Claim Status / Delete")
    with st.form("update_claim"):
        ucid = st.text_input("Claim_ID to update")
        new_status = st.selectbox("New Status", ["Pending", "Completed", "Cancelled"])
        upd = st.form_submit_button("Update Claim")
        if upd:
            if ucid.strip() == "":
                st.error("Provide Claim_ID")
            else:
                try:
                    exec_sql("UPDATE claims SET Status = ? WHERE Claim_ID = ?", (new_status, int(ucid)))
                    st.success("Claim updated.")
                except Exception as e:
                    st.error(f"Error: {e}")

    with st.form("delete_claim"):
        dcid = st.text_input("Claim_ID to delete")
        dsubmit = st.form_submit_button("Delete Claim")
        if dsubmit:
            if dcid.strip() == "":
                st.error("Provide Claim_ID")
            else:
                try:
                    exec_sql("DELETE FROM claims WHERE Claim_ID = ?", (int(dcid),))
                    st.success("Claim deleted.")
                except Exception as e:
                    st.error(f"Error: {e}")

# ---------------- QUERIES ----------------
with tabs[4]:
    st.header("SQL Queries & Analysis")

    predefined = {
        "1 Providers & receivers per city": """
            SELECT City,
                   (SELECT COUNT(*) FROM providers p WHERE p.City = r.City) as providers_count,
                   (SELECT COUNT(*) FROM receivers r2 WHERE r2.City = r.City) as receivers_count
            FROM (
                SELECT City FROM providers
                UNION
                SELECT City FROM receivers
            ) r
            GROUP BY City;
        """,
        "2 Top provider type by count": """
            SELECT Type, COUNT(*) as cnt
            FROM providers
            GROUP BY Type
            ORDER BY cnt DESC;
        """,
        "3 Provider contacts by city (parameterized)": "SELECT Name, Contact, Address, City FROM providers WHERE City = ?;",
        "4 Receivers who claimed the most": """
            SELECT r.Receiver_ID, r.Name, COUNT(c.Claim_ID) as claims_count
            FROM receivers r
            LEFT JOIN claims c ON r.Receiver_ID = c.Receiver_ID
            GROUP BY r.Receiver_ID
            ORDER BY claims_count DESC;
        """,
        "5 Total quantity available": "SELECT SUM(Quantity) as total_quantity FROM food_listings;",
        "6 City with highest listings": """
            SELECT Location as City, COUNT(*) as listings_count
            FROM food_listings
            GROUP BY Location
            ORDER BY listings_count DESC;
        """,
        "7 Most common food types": """
            SELECT Food_Type, COUNT(*) as cnt
            FROM food_listings
            GROUP BY Food_Type
            ORDER BY cnt DESC;
        """,
        "8 Claims per food item": """
            SELECT f.Food_ID, f.Food_Name, COUNT(c.Claim_ID) as claim_count
            FROM food_listings f
            LEFT JOIN claims c ON f.Food_ID = c.Food_ID
            GROUP BY f.Food_ID
            ORDER BY claim_count DESC;
        """,
        "9 Provider with most successful claims": """
            SELECT p.Provider_ID, p.Name,
                   SUM(CASE WHEN c.Status = 'Completed' THEN 1 ELSE 0 END) as completed_claims
            FROM providers p
            LEFT JOIN food_listings f ON p.Provider_ID = f.Provider_ID
            LEFT JOIN claims c ON f.Food_ID = c.Food_ID
            GROUP BY p.Provider_ID
            ORDER BY completed_claims DESC;
        """,
        "10 Claims status percentage": """
            SELECT Status, COUNT(*) * 1.0 / (SELECT COUNT(*) FROM claims) * 100 as pct
            FROM claims
            GROUP BY Status;
        """,
        "11 Avg quantity claimed per receiver": """
            SELECT r.Receiver_ID, r.Name, 
                   AVG(f.Quantity) as avg_quantity_claimed
            FROM receivers r
            JOIN claims c ON r.Receiver_ID = c.Receiver_ID
            JOIN food_listings f ON c.Food_ID = f.Food_ID
            GROUP BY r.Receiver_ID
            ORDER BY avg_quantity_claimed DESC;
        """,
        "12 Most claimed meal type": """
            SELECT f.Meal_Type, COUNT(c.Claim_ID) as claim_count
            FROM food_listings f
            JOIN claims c ON f.Food_ID = c.Food_ID
            GROUP BY f.Meal_Type
            ORDER BY claim_count DESC;
        """,
        "13 Total quantity donated per provider": """
            SELECT p.Provider_ID, p.Name, SUM(f.Quantity) as total_donated
            FROM providers p
            LEFT JOIN food_listings f ON p.Provider_ID = f.Provider_ID
            GROUP BY p.Provider_ID
            ORDER BY total_donated DESC;
        """,
        "14 Monthly claims trend": """
            SELECT substr(Timestamp, 1, 7) as month, COUNT(*) as claims_count
            FROM claims
            WHERE Timestamp IS NOT NULL
            GROUP BY month
            ORDER BY month;
        """,
        "15 Expired items still available": """
            SELECT Food_ID, Food_Name, Quantity, Expiry_Date, Location
            FROM food_listings
            WHERE Expiry_Date IS NOT NULL AND DATE(Expiry_Date) < DATE('now') AND Quantity > 0;
        """
    }

    q_choice = st.selectbox("Choose query to run", list(predefined.keys()))
    sql = predefined[q_choice]
    if "parameterized" in q_choice:
        param = st.text_input("Enter city name (for query parameter)")
        if st.button("Run query"):
            if param.strip() == "":
                st.error("Provide the city name parameter")
            else:
                df_q = run_query(sql, params=(param,))
                st.dataframe(df_q)
                to_csv_download(df_q, name=f"query_{q_choice}.csv")
    else:
        if st.button("Run query"):
            df_q = run_query(sql)
            st.dataframe(df_q)
            to_csv_download(df_q, name=f"query_{q_choice}.csv")
