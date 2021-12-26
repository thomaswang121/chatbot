from flask import Flask, request, abort
import json
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,FlexSendMessage
)
from linebot.models.flex_message import (
    BubbleContainer, ImageComponent
)
from linebot.models.actions import URIAction
import sqlite3
import pathlib
import pandas as pd

# 輸入幣種
# with open(message_currency, 'r', encoding='utf-8') as f:
#     FlexMessage = json.load(f)
# line_bot_api.reply_message(event.reply_token, FlexSendMessage('profile',FlexMessage))

# route initialize
root = pathlib.Path().cwd()
passwd = root / "json_file" / "passwd.json"
message_currency = root / "json_file" / "message_currency.json"
message_track = root / "json_file" / "message_track.json"
message_function = root / "json_file" / "message_function.json"
message_setting_value = root / "json_file" / "message_setting_value.json"
message_query = root / "json_file" / "message_query.json"


app = Flask(__name__)

# webhook
with open (passwd, 'r') as f:
    token = json.load(f)
line_bot_api = LineBotApi(token['channel_access_token'])
handler = WebhookHandler(token['channel_secret'])

# connect with chatbot.db
db_conn=sqlite3.connect(root / "chatbot.db", check_same_thread=False)
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
    if str=='NaN':
      return False
    float(str)
    return True
  except ValueError:
    return False


# parse json file
def parse_json(data_route):
    with open(data_route, 'r', encoding='utf-8')as f:
        data = json.load(f)
    return data

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

    # List of function
    if user_text == "外幣服務":
        FlexMessage = parse_json(message_function)
        line_bot_api.reply_message(event.reply_token, FlexSendMessage('profile',FlexMessage))

    # reset status
    if not create_result[1]:
        if user_text == "R":
            # reset user status
            sql = f"""UPDATE users SET user_status=null WHERE user='%s'"""%(user_id)
            db_cursor.execute(sql)
            db_conn.commit()

            # delete user config
            sql = f"""DELETE FROM user_configs WHERE user_id='%s'"""%(db_uid)
            db_cursor.execute(sql)
            db_conn.commit()

            # reply message
            FlexMessage = parse_json(message_function)
            line_bot_api.reply_message(event.reply_token, FlexSendMessage('profile',FlexMessage))
            return


    # select user status
    sql = f"""
        SELECT user_status FROM users
        WHERE user='%s'
    """%(user_id)
    db_cursor.execute(sql)
    user_status = db_cursor.fetchall()


    if user_text == "查詢匯率":
        sql = f"""UPDATE users SET user_status='Q' WHERE user='%s'"""%(user_id)
        db_cursor.execute(sql)
        db_conn.commit()
        line_bot_api.reply_message(event.reply_token,TextSendMessage(f"請依照下列格式輸入「美金-2021/12/24」"))
        return


    if user_status[0][0] is None:
        # user input in default list
        if user_text in currency:

            # get db_cid
            sql = f"""SELECT id FROM foreign_currencies
                    WHERE foreign_currency='%s'"""%(currency[user_text])
            db_cursor.execute(sql)
            db_cid = db_cursor.fetchall()[0][0]

            # setting user config
            sql = f"""INSERT INTO user_configs(foreign_currency_id, user_id) VALUES('%s', '%s')"""%(db_cid, db_uid)
            db_cursor.execute(sql)
            db_conn.commit()


            FlexMessage = parse_json(message_track)
            line_bot_api.reply_message(event.reply_token, FlexSendMessage('profile',FlexMessage))
            # line_bot_api.reply_message(event.reply_token,TextSendMessage(f"請輸入欲追蹤種類，例如:現金買入、即期賣出"))

            # Update user status C (choose)
            sql = f"""UPDATE users SET user_status='C' WHERE user='%s'"""%(user_id)
            db_cursor.execute(sql)
            db_conn.commit()


        # Update user status P (puah)
        elif user_text == "匯率推播":
            # reset user status
            sql = f"""UPDATE users SET user_status=null WHERE user='%s'"""%(user_id)
            db_cursor.execute(sql)

            # delete user config
            sql = f"""DELETE FROM user_configs WHERE user_id='%s'"""%(db_uid)
            db_cursor.execute(sql)
            db_conn.commit()
            FlexMessage = parse_json(message_currency)
            line_bot_api.reply_message(event.reply_token, FlexSendMessage('profile',FlexMessage))

        # user input not in default list
        else:
            input_list = [ele for ele in currency.items()]
            line_bot_api.reply_message(event.reply_token,TextSendMessage(f"抱歉！輸入格式有誤"))
    
    elif user_status[0][0] == "Q":
        # get trade day id
        trade_day = user_text.split('-')[1]
        sql = f"""SELECT id FROM trade_days WHERE trade_day='%s'"""%(trade_day)
        db_cursor.execute(sql)
        db_tid = db_cursor.fetchall()[0][0]

        # get currency id
        sql = f"""SELECT id FROM foreign_currencies
                WHERE foreign_currency='%s'"""%(currency[user_text.split('-')[0]])
        db_cursor.execute(sql)
        db_cid = db_cursor.fetchall()[0][0]
        
        # retrieve
        sql = f"""SELECT cash_buy,cash_sell,spot_buy,spot_sell
                FROM exchanges 
                WHERE foreign_currency_id='%s' 
                AND trade_day_id='%s'"""%(db_cid, db_tid)
        db_cursor.execute(sql)
        db_row = db_cursor.fetchall()[0]

        # reply to user
        FlexMessage = parse_json(message_query)
        FlexMessage['contents'][0]['body']['contents'][0]['text'] = f"現金買入:{db_row[0]}"
        FlexMessage['contents'][0]['body']['contents'][1]['text'] = f"現金買入:{db_row[1]}"
        FlexMessage['contents'][0]['body']['contents'][2]['text'] = f"現金買入:{db_row[2]}"
        FlexMessage['contents'][0]['body']['contents'][3]['text'] = f"現金買入:{db_row[3]}"
        FlexMessage['contents'][0]['hero']['contents'][0]['text'] = f"日期：{trade_day}"
        line_bot_api.reply_message(event.reply_token, FlexSendMessage('profile',FlexMessage))
        
        # reset user status
        sql = f"""UPDATE users SET user_status=null WHERE user='%s'"""%(user_id)
        db_cursor.execute(sql)
        db_conn.commit()


    elif user_status[0][0] == "C":
        if user_text in ["現金買入", "現金賣出", "即期買入", "即期賣出"]:
            
            # Update user track category
            sql = f"""UPDATE user_configs SET user_choose='%s' WHERE user_id='%s'"""%(option[option.chn == user_text].code.values[0], db_uid)
            db_cursor.execute(sql)

            # Update user status S (setting)
            sql = f"""UPDATE users SET user_status='S' WHERE user='%s'"""%(user_id)
            db_cursor.execute(sql)
            db_conn.commit()
            FlexMessage = parse_json(message_setting_value)
            line_bot_api.reply_message(event.reply_token, FlexSendMessage('profile',FlexMessage))
            # line_bot_api.reply_message(event.reply_token,TextSendMessage(f"請輸入門檻值"))
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
            
            # Update user status null
            sql = f"""UPDATE users SET user_status=null WHERE user='%s'"""%(user_id)
            db_cursor.execute(sql)
            db_conn.commit()
        else:
            line_bot_api.reply_message(event.reply_token,TextSendMessage(f"請輸入數字 例如:27.3"))
    
    return
    
    
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5050)
    db_conn.close()

