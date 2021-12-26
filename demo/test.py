import pathlib
import sqlite3
# connect with chatbot.db
root = pathlib.Path().cwd()

db_conn=sqlite3.connect(root / "chatbot.db", check_same_thread=False)
db_cursor = db_conn.cursor()
sql = f"""UPDATE users SET user_status=null"""
db_cursor.execute(sql)
db_conn.commit()
db_conn.close()