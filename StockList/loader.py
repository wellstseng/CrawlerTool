
#%%
# -*- encoding: utf8-*-

import requests
import sys, os
from bs4 import BeautifulSoup
import json
import csv
import pandas as pd

class MarketType:
    TWSE = 2
    TPEX = 4

class StockListHolder:
    FILE_PATH = os.path.abspath(os.path.dirname(__file__)).replace('\\','/')
    FILE_PATH_FMT=FILE_PATH + "/list_{}.csv"
    TEST = False
    @staticmethod
    def __load_data(marketType):        
        if StockListHolder.TEST == False:
            url = "http://isin.twse.com.tw/isin/C_public.jsp?strMode={}".format(marketType)
            print('load list from url {}'.format(url))
            headers = {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
                "Accept-Encoding": "gzip, deflate",
                "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
                "Cache-Control": "max-age=0",            
                "Host": "isin.twse.com.tw",
                "Coolie":"JSESSIONID=F13C7761B22C9768E52BEB2B2C90ED44",
                "Upgrade-Insecure-Requests": "1",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36",
                "Connection": 'keep-alive',
            }
            res = requests.get(url, headers=headers, timeout=60, verify=False)
            return res.text
        else:
            print('load list from test')
            f = open(StockListHolder.FILE_PATH+"/test.txt", 'r', encoding='utf8')
            text = f.read()
            f.close()
            return text

    @staticmethod
    def __save_data(marketType, data):   
        print("save list...")
        json_str = str(data).replace('\u3000','').replace('\'','"').replace(' ','')
        data_parsed = json.loads(json_str)
        file_path = StockListHolder.FILE_PATH_FMT.format(marketType)
        if os.path.isfile(file_path):
            os.remove(file_path)

        f = open(file_path, "a+", encoding='utf-8', newline='')
        csv_writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        csv_writer.writerow(['Id','Name','PublishDate','MarketId','IndustryId'])

        for key, value in data_parsed.items():            
            csv_writer.writerow(["{}".format(key)] + value)

        f.close()
    
    @staticmethod
    def __parse_data(src):
        print("parse data...")
        soup = BeautifulSoup(src, 'html.parser')    
        table = soup.find("table", {"class" : "h4"})
        datas = {}
        do_parse = False
        for row in table.find_all("tr"):
            cols = row.find_all('td')

            if len(cols) == 1 :
                if "股票" in cols[0].text or "ETF" in cols[0].text:
                    do_parse = True
                else:
                    do_parse = False
            

            if do_parse:
                split_r = cols[0].text.split('\u3000')
                if len(split_r) >= 2:
                    datas[split_r[0]] = [split_r[1].strip('\u3000'),cols[2].text, cols[3].text,cols[4].text ]
        return datas

    @staticmethod
    def get_list(marketType):
        src = StockListHolder.__load_data(marketType)      
        datas = StockListHolder.__parse_data(src)
        StockListHolder.__save_data(marketType, datas)

    @staticmethod
    def read_stock_ids(marketType):
        if type(marketType) is str:
            marketType=2 if marketType == "twse" else 4
                
        file_path = StockListHolder.FILE_PATH_FMT.format(marketType)
        df = pd.read_csv(file_path, header=0, dtype={"Id":str})
        df.set_index('Id', inplace=True)
        return df.index.values

if __name__ == '__main__':
    if StockListHolder.TEST == False:
        #marketType = sys.argv[1]
        #StockListHolder.get_list(marketType)   
        StockListHolder.get_list(4)   
    else:
        StockListHolder.get_list(4)     

    # print(StockListHolder.read_stock_ids(2))

