import aiohttp
import asyncio
import time
from bs4 import BeautifulSoup
import multiprocessing as mp
import sqlite3
import pathlib
import json
from linebot import LineBotApi
from linebot.models import TextSendMessage

# route initialize
root = pathlib.Path().cwd()
passwd = root / "json_file" / "passwd.json"
message = root / "json_file" / "message.json"

# connect with chatbot.db
db_conn = sqlite3.connect(root / "chatbot.db")
db_cursor = db_conn.cursor()

# wibsite url (18)
base_url = "https://rate.bot.com.tw/xrt/quote/day/"
currency_list = ["USD", "HKD", "GBP", "AUD", "SGD", "CHF", "JPY", "ZAR", "SEK","NZD", "THB", "PHP", "IDR", "EUR", "KRW", "VND", "MYR", "CNY"]
loop = asyncio.get_event_loop()

# linebotsdk token auth
with open (passwd, 'r') as f:
    token = json.load(f)
line_bot_api = LineBotApi(token['channel_access_token'])

def parse(html):
    soup = BeautifulSoup(html, 'html.parser')
    html_rows = iter(soup.find_all('tr')[-1])
    html_row = [ele.text for ele in html_rows]
    for i in range(len(html_row)):
        if '\n' not in html_row:
            break
        html_row.remove('\n')
    currency = html_row[1].split('(')[1].split(')')[0]

    # check trade day
    trade_day = html_row[0].split(' ')[0]
    db_cursor.execute(f"""
            SELECT id, trade_day FROM trade_days
            WHERE trade_day='{trade_day}'
        """)
    resp = db_cursor.fetchall()
    if resp!=[]:
        db_trade_day_id = resp[0][0]
    else:
        sql = f"""
            INSERT INTO trade_days(trade_day)
            VALUES('%s') 
        """%(trade_day)
        db_cursor.execute(sql) 
        db_trade_day_id = db_cursor.lastrowid
        db_conn.commit()
    db_updated = query_last_rows(currency)[0]
    db_currency_id = query_last_rows(currency)[1]
    html_row[0].replace('/','-')
    
    # Scrap fail continue next loop 
    if db_updated == html_row[0]:
        return

    # Scrap successful remove element from currency_list
    update_data(html_row, db_currency_id, db_trade_day_id)
    push_message(html_row, db_currency_id)
    global currency_list
    currency_list.remove(currency)
    return

# get last updated timestamp
def query_last_rows(foreign_currency):

    # get foreign currency id
    sql = f"""
            SELECT id FROM foreign_currencies
            WHERE foreign_currency='%s'
            """%(foreign_currency)
    db_cursor.execute(sql)
    db_currency_id = db_cursor.fetchall()[0][0]

    # get last updated timestamp
    sql = f"""
            SELECT updated_at FROM exchanges
            WHERE foreign_currency_id='%s'
            """%(db_currency_id)
    db_cursor.execute(sql)
    last_updated = db_cursor.fetchall()
    if last_updated == []:
        return None, db_currency_id
    else:
        return last_updated[0][0], db_currency_id

# insert the latest data
def update_data(html_row, currency_id, trade_day_id):
    sql = f"""
            INSERT INTO exchanges(foreign_currency_id, trade_day_id, cash_buy,cash_sell, spot_buy, spot_sell, updated_at)
            VALUES('%s', '%s', '%s', '%s', '%s', '%s', '%s')"""%(currency_id, trade_day_id, html_row[2], html_row[3], html_row[4], html_row[5], html_row[0])
    db_cursor.execute(sql)
    db_conn.commit()    

def push_message(html_row, db_currency_id=None):
    sql = f"""SELECT user_id, foreign_currency_id, user_choose, setting_value FROM user_configs"""
    db_cursor.execute(sql)
    notify_list = db_cursor.fetchall()
    for notify in notify_list:
        # check user track currency id
        if notify[1] != db_currency_id:
            continue

        # get user_id
        sql = f"""SELECT user FROM users WHERE id='%s'"""%(notify[0])
        db_cursor.execute(sql)
        user = db_cursor.fetchall()[0][0]
        
        # get user configs
        sql = f"""SELECT user_choose,setting_value FROM user_configs WHERE user_id='%s'"""%(notify[0])
        db_cursor.execute(sql)
        db_setting_value = db_cursor.fetchall()[0]
        print(db_setting_value)

        print(html_row[3],db_setting_value[1])
        # identify user_choose
        if db_setting_value[0] == "CB" and float(html_row[2]) > db_setting_value[1]:
            line_bot_api.push_message(user, 
                    TextSendMessage(text=f'目前"{html_row[1]}"現金買入匯率為{html_row[2]},已高於設定值({db_setting_value[1]})！'))
        elif db_setting_value[0] == "CS" and float(html_row[3]) < db_setting_value[1]:
            line_bot_api.push_message(user, 
                    TextSendMessage(text=f'目前"{html_row[1]}"現金賣出匯率為{html_row[3]},已低於設定值({db_setting_value[1]})！'))

        elif db_setting_value[0] == "SB" and float(html_row[4]) > db_setting_value[1]:
            line_bot_api.push_message(user, 
                    TextSendMessage(text=f'目前"{html_row[1]}"即期買入匯率為{html_row[4]},已高於設定值({db_setting_value[1]})！'))

        elif db_setting_value[0] == "SS" and float(html_row[5]) < db_setting_value[1]:
            line_bot_api.push_message(user, 
                    TextSendMessage(text=f'目前"{html_row[1]}"即期賣出匯率為{html_row[5]},已低於設定值({db_setting_value[1]})！'))

        else:
            pass



    print(notify_list)
    # sql_query = pd.read_sql_query(sql,db_conn)
    # notify_list = pd.DataFrame(sql_query, columns=['user_id', 'foreign_currency_id', 'user_choose', 'setting_value'])
    
async def crawl(url, session):
    r = await session.get(url)
    html = await r.text()
    await asyncio.sleep(0.1)        # slightly delay for downloading
    return html


async def main(loop):
    pool = mp.Pool(2)               # slightly affected
    async with aiohttp.ClientSession() as session:
        tasks = [loop.create_task(crawl(base_url + url, session)) for url in currency_list]
        finished, unfinished = await asyncio.wait(tasks)
        htmls = [f.result() for f in finished]
        parse_jobs = [pool.apply_async(parse, args=(html,)) for html in htmls]
        # results = [j.get() for j in parse_jobs]
        
def run():
    global currency_list, start_at
    localtime = time.strftime('%H:%M', time.localtime())

    # Empty list rest
    if currency_list == []:
        loop.close()
        db_conn.close()
        exit(1)
    
    # exceed trading time
    elif localtime == "02:03":
        loop.close()
        db_conn.close()
        exit(0)
    
    else:
        pass
    
    loop.run_until_complete(main(loop))
    print("Async total time: ", time.time() - start_at)
    if (time.time() - start_at) > 60:
        start_at = time.time()
        currency_list = ["USD", "HKD", "GBP", "AUD", "SGD", "CHF", "JPY", "ZAR", "SEK","NZD", "THB", "PHP", "IDR", "EUR", "KRW", "VND", "MYR", "CNY"]
    time.sleep(10)
    run()

if __name__ == "__main__":
    start_at = time.time()
    run()