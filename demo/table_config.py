import sqlite3
import pathlib

# Connect with chatbot.db
db_conn = sqlite3.connect(pathlib.Path().cwd() / "chatbot.db")
db_cursor = db_conn.cursor()
print("SUCCESS: Connection to the database succeeded")

# Create table users
db_cursor.execute("""DROP TABLE IF EXISTS users;""")
sql = f"""CREATE TABLE users(
    id INTEGER PRIMARY KEY  AUTOINCREMENT,
    user TEXT UNIQUE,
    user_status VARCHAR(2),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )"""
db_cursor.execute(sql)
print("table users created successfully")

# Create table user_configs
db_cursor.execute("""DROP TABLE IF EXISTS user_configs;""")
sql = f"""CREATE TABLE user_configs(
    id INTEGER PRIMARY KEY   AUTOINCREMENT,
    user_id VARCHAR(50) UNIQUE,
    foreign_currency_id INTEGER,
    user_choose VARCHAR(3),
    setting_value REAL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(foreign_currency_id) REFERENCES foreign_currencies(id) ON DELETE SET NULL
    )"""
db_cursor.execute(sql)
sql = f"""CREATE  TRIGGER user_infos_trigger_updated_at AFTER UPDATE ON user_configs
    BEGIN
    UPDATE user_configs SET updated_at = DATETIME('now', 'localtime') WHERE rowid == NEW.rowid;
    END"""
db_cursor.execute(sql)
print("table user_infos created successfully")

# Create table trade_days
db_cursor.execute("""DROP TABLE IF EXISTS trade_days;""")
sql = f"""CREATE TABLE trade_days(
    id INTEGER PRIMARY KEY   AUTOINCREMENT,
    trade_day VARCHAR(10)
    )"""
db_cursor.execute(sql)
print("table trade_days created successfully")

# Create table foreign_currencies
db_cursor.execute("""DROP TABLE IF EXISTS foreign_currencies;""")
sql = f"""CREATE TABLE foreign_currencies(
    id INTEGER PRIMARY KEY   AUTOINCREMENT,
    foreign_currency VARCHAR(10) UNIQUE
    )"""
db_cursor.execute(sql)
print("table foreign_currencies created successfully")

# Initialize table
currency_list = [
    "USD", 
    "HKD", 
    "GBP", 
    "AUD", 
    "SGD", 
    "CHF", 
    "JPY", 
    "ZAR", 
    "SEK",
    "NZD", 
    "THB", 
    "PHP", 
    "IDR", 
    "EUR", 
    "KRW", 
    "VND", 
    "MYR", 
    "CNY"
    ]
for ele in currency_list:
    sql = f"""
        INSERT INTO foreign_currencies(foreign_currency)
        VALUES ('%s')"""%(ele)
    db_cursor.execute(sql)

# Create table exchanges
db_cursor.execute("""DROP TABLE IF EXISTS exchanges;""")
sql = f"""CREATE TABLE exchanges(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    foreign_currency_id INTEGER,
    trade_day_id INTEGER,
    cash_buy REAL NOT NULL,
    cash_sell REAL NOT NULL,
    spot_buy REAL NOT NULL,
    spot_sell REAL NOT NULL,
    updated_at DATETIME,
    FOREIGN KEY(foreign_currency_id) REFERENCES foreign_currencies(id) ON DELETE SET NULL,
    FOREIGN KEY(trade_day_id) REFERENCES trade_day(id) ON DELETE SET NULL,
    UNIQUE(foreign_currency_id, updated_at))
    """
db_cursor.execute(sql)
print("table exchanges created successfully")

db_conn.commit()
db_conn.close()