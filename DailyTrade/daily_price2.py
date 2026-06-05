#%%
# -*- encoding:utf-8 -*-

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import requests
import io
import os.path
import time
from datetime import timedelta, date, datetime
import pandas as pd
import csv
from StockList.loader import StockListHolder

import global_func
import define
from define import DB_KEY as DB_KEY

mongo_mgr = None
LOG_ENABLE = True

def get_mongo_mgr():
    global mongo_mgr
    if mongo_mgr is None:
        from mongo import MongoManager
        mongo_mgr = MongoManager(os.environ.get("STOCK_MONGO_URL", "mongodb://stock:stock@192.168.1.14:27017/stock"))
    return mongo_mgr

def _clean_cell(value):
    value = str(value).strip().replace('\u3000', '')
    if value.startswith('="') and value.endswith('"'):
        value = value[2:-1]
    return value.replace('=', '')

def _get_daily_price_header(market_type):
    if market_type == define.MarketType.TPEX:
        return {
            "證券代號": "代號",
            "證券名稱": "名稱",
            "收盤價": "收盤",
            "開盤價": "開盤",
            "最高價": "最高",
            "最低價": "最低",
            "成交股數": "成交股數",
            "成交金額": "成交金額(元)",
            "成交筆數": "成交筆數",
        }

    return {
        "證券代號": "證券代號",
        "證券名稱": "證券名稱",
        "收盤價": "收盤價",
        "開盤價": "開盤價",
        "最高價": "最高價",
        "最低價": "最低價",
        "成交股數": "成交股數",
        "成交金額": "成交金額",
        "成交筆數": "成交筆數",
    }

def _to_roc_date(src_date):
    year, month, day = src_date.split("/")
    return "{0}/{1}/{2}".format(int(year) - 1911, month.zfill(2), day.zfill(2))

def _response_matches_date(market_type, text, src_date):
    if market_type != define.MarketType.TPEX:
        return True

    expected = "資料日期:{0}".format(_to_roc_date(src_date))
    return expected in text

def normalize_file(market_type:str, file_path:str):
    rows = []
    with open(file_path, "r", encoding='utf8', newline='') as f:
        rows = list(csv.reader(f))

    header_index = None
    for i, row in enumerate(rows):
        if len(row) > 0 and row[0] in ("證券代號", "代號"):
            header_index = i
            break

    if header_index is None:
        os.remove(file_path)
        return

    src_header = [_clean_cell(i) for i in rows[header_index]]
    output_header = list(_get_daily_price_header(market_type).keys())
    if all(i in src_header for i in output_header):
        column_map = {i: i for i in output_header}
    else:
        column_map = _get_daily_price_header(market_type)
    output_rows = []
    for row in rows[header_index + 1:]:
        if len(row) < len(src_header):
            continue

        row_map = {src_header[i]: _clean_cell(row[i]) for i in range(len(src_header))}
        stock_id = row_map.get(column_map["證券代號"], "")
        if stock_id == "" or stock_id in ("證券代號", "代號"):
            continue

        output_rows.append([row_map.get(column_map[col], "") for col in output_header])

    if len(output_rows) <= 0:
        os.remove(file_path)
        return

    with open(file_path, "w", encoding='utf8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(output_header)
        writer.writerows(output_rows)


def parse_file_to_db(market_type:str, file_path:str):
    
    if not os.path.isfile(file_path):
        print("File:{} not exist do not parse to db".format(file_path))
        return
    normalize_file(market_type, file_path)        
    df = pd.read_csv(file_path, header=0, dtype={"證券代號":str})
    df.set_index('證券代號', inplace=True)
    file_date = os.path.basename(file_path).split('.')[0]    
    year_month = file_date[:6]
    total = len(df.index)
    cnt = 0
    id_list = StockListHolder.read_stock_ids(market_type).tolist()
    for index, series in df.iterrows():
        cnt += 1
        if str(index) in id_list:                
            series = df.loc[index]
            suspend = "--" in str(series["開盤價"])
            o = float((str(series["開盤價"]).replace(',',''))) if not suspend else -1
            h = float((str(series["最高價"]).replace(',',''))) if not suspend else -1
            l = float((str(series["最低價"]).replace(',',''))) if not suspend else -1
            c = float((str(series["收盤價"]).replace(',',''))) if not suspend else -1
            name =  series["證券名稱"]
            volume = int(round(int(series["成交股數"].replace(',',''))*0.001, 0)) if not suspend else 0
            turnover = round(int(series["成交金額"].replace(',',''))*0.00000001, 3)  if not suspend else 0
            transaction = int(series["成交筆數"].replace(',',''))  if not suspend else 0
            query = {
                "$set":
                    {
                        DB_KEY.DATE: year_month,
                        "items.{0}.{1}".format(file_date, DB_KEY.OPEN):o,
                        "items.{0}.{1}".format(file_date,DB_KEY.HIGH):h,
                        "items.{0}.{1}".format(file_date,DB_KEY.LOW):l,
                        "items.{0}.{1}".format(file_date,DB_KEY.CLOSE):c,
                        "items.{0}.{1}".format(file_date,DB_KEY.VOLUME):volume,
                        "items.{0}.{1}".format(file_date,DB_KEY.TURNOVER):turnover,
                        "items.{0}.{1}".format(file_date,DB_KEY.TRANSACTION):transaction,                    
                    }
            }
            result = get_mongo_mgr().upsert("stock", "Stock_{}".format(index), {DB_KEY.DATE:year_month}, query)
            if result['ok'] != 1.0:
                raise Exception("mongo db upsert fail date:{0}, stock_id:{1}, query:{2}".format(file_date, index, query) )
            
            
            if LOG_ENABLE:
                sys.stdout.flush()     
                print("{0:10} {1:8} => {2:6}/{3:6}\r".format(file_date, index, cnt, total ),end='')

    print("", end="\n")
    print("done")
    

def check_update_latest_day(latest_date):
    #寫入最新股價日期
    if latest_date is not None :        
        from bson.objectid import ObjectId
        result = get_mongo_mgr().find_one("stock", "Outline", {DB_KEY.OBJECT_ID:ObjectId("5b940a041e6fe6eb0d8a53b2")}) or {}
        curr_d = result[DB_KEY.LATEST_DAY] if DB_KEY.LATEST_DAY in result else None
        if curr_d is None or int(latest_date) > int(curr_d):
           result = get_mongo_mgr().upsert("stock", "Outline", {DB_KEY.OBJECT_ID:ObjectId("5b940a041e6fe6eb0d8a53b2")}, 
           {"$set":
                {
                    DB_KEY.LATEST_DAY:latest_date,                 
                }
            }) 
        print("upsert latest date: " , str(result))

def load_range(market_type:str, url_fmt:str, headers:str, start_date:str=None, end_date:str=None, parse_to_db:bool=False, try_load:bool=True):
    if start_date == None:
        start_date = datetime.now().strftime("%Y/%m/%d")
    if end_date == None:
        end_date = global_func.get_latest_file_date(define.Define.SRC_DATA_PATH_FMT.format(define.DataType.PRICE,market_type))
 
    print("start:{0}  end:{1},  try load:{2}".format(start_date, end_date, try_load))
    s = start_date.split("/")
    e= end_date.split("/")
    start_date = date(int(s[0]), int(s[1]), int(s[2]))
    end_date = date(int(e[0]), int(e[1]), int(e[2]))
    latest_date = None
    for single_date in global_func.daterange(start_date, end_date):
        
        file_path = global_func.get_abs_path(define.Define.DAILY_PRICE_FMT.format(market_type, single_date.strftime("%Y%m%d")))
        
        src_date = single_date.strftime("%Y/%m/%d") if market_type == define.MarketType.TPEX else single_date.strftime("%Y%m%d")

        if os.path.isfile(file_path):
            print("Exist file. Do not load again: " + file_path)
        else:
            if try_load == True :
                print('Load csv date:{}  to {}'.format(src_date, file_path), end="\n")
                url = url_fmt.format(src_date)           
                req = requests.get(url, headers=headers, timeout=60)
                req.raise_for_status()
                req.encoding = 'ms950'
                text = req.text
                if not _response_matches_date(market_type, text, src_date):
                    print('No data')
                    continue
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, 'w', encoding='utf8', newline='') as f:
                    f.write(text)
                normalize_file(market_type, file_path)

                if os.path.isfile(file_path):
                    latest_date = single_date.strftime("%Y%m%d")
                    print("latest date: ", latest_date)
                    print('Load Done')
                else:
                    print('No data')
                #print("Sleep 10")
                #time.sleep(10)

        if parse_to_db:
            print("Parse file {0} to db".format(file_path))
            parse_file_to_db(market_type, file_path)           
    if parse_to_db:
        check_update_latest_day(latest_date)

if __name__=="__main__":
    load_range("twse", define.Define.TWSE_DAILY_PRICE_URL_FMT, define.Define.TWSE_DAILY_PRICE_HEADERS, parse_to_db=True)
    load_range("tpex", define.Define.TPEX_DAILY_PRICE_URL_FMT, define.Define.TPEX_DAILY_PRICE_HEADERS, parse_to_db=True)
    # print(define.Define.FILE_PATH)
    '''
    if sys.argv[1] == 'twse':
        url = define.Define.TWSE_DAILY_PRICE_URL_FMT
        header = define.Define.TWSE_DAILY_PRICE_HEADERS
    else:
        url = define.Define.TPEX_DAILY_PRICE_URL_FMT
        header = define.Define.TPEX_DAILY_PRICE_HEADERS

    load_range(sys.argv[1], url, header, start_date=sys.argv[2], end_date=sys.argv[3], parse_to_db=sys.argv[4], try_load=sys.argv[5])
    '''
