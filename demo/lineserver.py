from flask import Flask, request, abort
import json
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
)
import sqlite3
import pathlib
import pandas as pd
app = Flask(__name__)
db_conn=sqlite3.connect(pathlib.Path().cwd()/"user.db")
db_cursor=db_conn.cursor()
with open ("passwd.json", 'r') as f:
    token = json.load(f)
line_bot_api = LineBotApi(token['channel_access_token'])
handler = WebhookHandler(token['channel_secret'])

db_conn=sqlite3.connect(pathlib.Path().cwd() / "chatbot.db",check_same_thread=False)
db_cursor = db_conn.cursor()
currency = {
    "美金":"USD",
    "港幣":"HKD",
    "英鎊":"GBP",
    "澳幣":"AUD",
    "新加坡幣":"SGD",
    "瑞士法郎":"CHF",
    "日圓":"JPY",
    "南非幣":"ZAR",
    "瑞典幣":"SEK",
    "紐元":"NZD",
    "泰幣":"THB",
    "菲國比索":"PHP",
    "印尼幣":"IDR",
    "歐元":"EUR",
    "韓元":"KRW",
    "越南盾":"VND",
    "馬來幣":"MYR",
    "人民幣":"CNY",
}
option_dict = {
    "現金買入":"CB",
    "現金賣出":"CS",
    "即期買入":"SB",
    "即期賣出":"SS"
}
option = pd.DataFrame(list(option_dict.items()), columns=['chn', 'code'])


@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    try:
        handler.handle(body, signature)
        
    except InvalidSignatureError:
        abort(400)

    return 'OK'

# check user text
def is_number(str):
  try:
    # 因為使用float有一個例外是'NaN'
    if str=='NaN':
      return False
    float(str)
    return True
  except ValueError:
    return False

# reset user status
def reset_status(user_id):
    sql = f"""UPDATE users SET user_status=null WHERE user='%s'"""%(user_id)
    db_cursor.execute(sql)
    db_conn.commit()

# get user id 
def create_new_user(user_id):
    try:
        sql = f"""INSERT INTO users(user) VALUES('%s')"""%(user_id)
        db_cursor.execute(sql)
        db_uid = db_cursor.lastrowid
        db_conn.commit()
        print(f"Create user : {user_id}")
        return (db_uid, True)

    except:
        sql = f"""SELECT id FROM users
                    WHERE user='%s'"""%(user_id)
        db_cursor.execute(sql)
        db_uid = db_cursor.fetchall()[0][0]
        print(f"{user_id} Data Exists")
        return (db_uid, False)


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    # get user id when reply
    user_id = event.source.user_id
    user_text = event.message.text
    print("user_id =", user_id)
    create_result = create_new_user(user_id)
    db_uid = create_result[0]

    # reset status
    if not create_result[1]:
        if user_text == "R":
            reset_status(user_id)
            line_bot_api.reply_message(event.reply_token,TextSendMessage(f"已清除設定，請輸入幣種，例如:美金"))
            return

    # select user status
    sql = f"""
        SELECT user_status FROM users
        WHERE user='%s'
    """%(user_id)
    db_cursor.execute(sql)
    user_status = db_cursor.fetchall()


    if user_status[0][0] is None:
        # user input in default list
        if user_text in currency:

            # get db_cid
            sql = f"""SELECT id FROM foreign_currencies
                    WHERE foreign_currency='%s'"""%(currency[user_text])
            db_cursor.execute(sql)
            db_cid = db_cursor.fetchall()[0][0]

            # New user
            if create_result[1]:
                sql = f"""INSERT INTO user_configs(foreign_currency_id, user_id) VALUES('%s', '%s')"""%(db_cid, db_uid)
                db_cursor.execute(sql)
                db_conn.commit()

            # Old user
            else:
                sql = f"""UPDATE user_configs SET foreign_currency_id='%s' WHERE user_id='%s'"""%(db_cid, db_uid)
                db_cursor.execute(sql)
                db_conn.commit()
                
            line_bot_api.reply_message(event.reply_token,TextSendMessage(f"請輸入欲追蹤種類，例如:現金買入、即期賣出"))

            # Update user status C (choose)
            sql = f"""UPDATE users SET user_status='C' WHERE user='%s'"""%(user_id)
            db_cursor.execute(sql)
            db_conn.commit()

        # Update user status Q (query)
        elif user_text == "查詢":
            sql = f"""UPDATE users SET user_status='Q' WHERE user='%s'"""%(user_id)
            db_cursor.execute(sql)
            db_conn.commit()
            line_bot_api.reply_message(event.reply_token,TextSendMessage(f"請依照下列格式輸入您想查詢內容"))

        # user input not in default list
        else:
            input_list = [ele for ele in currency.items()]
            print(input_list)
            line_bot_api.reply_message(event.reply_token,TextSendMessage(f"請輸入正確幣種，例如:美金"))
    
    elif user_status[0][0] == "C":
        if user_text in ["現金買入", "現金賣出", "即期買入", "即期賣出"]:
            
            # Update user track category
            sql = f"""UPDATE user_configs SET user_choose='%s' WHERE user_id='%s'"""%(option[option.chn == user_text].code.values[0], db_uid)
            db_cursor.execute(sql)

            # Update user status S (setting)
            sql = f"""UPDATE users SET user_status='S' WHERE user='%s'"""%(user_id)
            db_cursor.execute(sql)
            db_conn.commit()
            line_bot_api.reply_message(event.reply_token,TextSendMessage(f"請輸入門檻值"))
        else:
            line_bot_api.reply_message(event.reply_token,TextSendMessage(f"請輸入正確選項，例如:現金買入、現金賣出、即期買入、即期賣出"))

    # Setting track value
    elif user_status[0][0] == "S":
        if is_number(user_text):
            # Setting track value
            sql = f"""UPDATE user_configs SET setting_value='%s' WHERE user_id='%s'"""%(user_text, db_uid)
            db_cursor.execute(sql)
            db_conn.commit()

            # get user track category
            sql = f"""SELECT user_choose FROM user_configs WHERE user_id='%s'"""%(db_uid)
            db_cursor.execute(sql)
            setting_value = db_cursor.fetchall()[0][0]
            setting_value = option[option.code == setting_value].chn.values[0]
            line_bot_api.reply_message(event.reply_token,TextSendMessage(f"完成設定，{setting_value} {user_text}，若欲清除或重新設定請輸入「R」"))
            
            # Update user status F (Finish)
            sql = f"""UPDATE users SET user_status='F' WHERE user='%s'"""%(user_id)
            db_cursor.execute(sql)
            db_conn.commit()
        else:
            line_bot_api.reply_message(event.reply_token,TextSendMessage(f"請輸入數字 例如:27.3"))
    
    return
    
    
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5050)
    db_conn.close()

