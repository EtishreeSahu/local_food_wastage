
# 🍽️ Local Food Wastage Management System

## 📌 Project Overview

The **Local Food Wastage Management System** is designed to reduce food wastage by connecting **food providers** (restaurants, hotels, individuals) with **receivers** (NGOs, shelters, food banks).

The system uses **data pipelines, SQL analytics, and a Streamlit web app** to manage surplus food donations and analyze wastage patterns.

🔗 **Deployed App**: [Click here](https://localfoodwastage-zr8tqrclyf8avf9pspb2aw.streamlit.app/)
🔗 **GitHub Repo**: [Click here](https://github.com/etishreesahu/local_food_wastage)

---

## 📂 Dataset Overview

The project uses four datasets:

* `providers_data.csv` → Food providers (1000 rows)
* `receivers_data.csv` → Food receivers (1000 rows)
* `food_listings_data.csv` → Food items listed (1000 rows)
* `claims_data.csv` → Records of food claims (1000 rows)

---

## ⚙️ Features

✅ Data cleaning & preprocessing pipeline (`pipeline.py`)
✅ SQLite database with **4 interrelated tables**
✅ **15+ SQL queries** for insights
✅ Interactive **Streamlit dashboard**
✅ Filtering, CRUD operations, CSV download
✅ Deployed on **Streamlit Cloud**

---

## 🛠️ Tech Stack

* **Python** (pandas, sqlite3, re, datetime)
* **Streamlit** (for UI & deployment)
* **SQLite** (database management)
* **Matplotlib/Altair** (visualizations)

---

## 🚀 How to Run Locally

1. Clone the repo:

   ```bash
   git clone https://github.com/etishreesahu/local_food_wastage.git
   cd local_food_wastage
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run the pipeline (to create database & queries):

   ```bash
   python pipeline.py
   ```

4. Start the Streamlit app:

   ```bash
   streamlit run app.py
   ```

---

## 📊 Example SQL Queries Implemented

* Providers & Receivers per City
* Most Common Food Types
* Claims per Food Item
* Expired Items Still Available
* Monthly Claims Trend

---

## 📌 Internship Details

* **Name**: Etishree Sahu
* **Branch**: AI/ML
* **Project**: Local Food Wastage Management System
* **Internship**: 15 June Batch



