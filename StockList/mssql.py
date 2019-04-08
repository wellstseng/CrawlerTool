import os, sys, pymssql, csv

def load_csv(market_type):
    file_path = os.path.abspath(os.path.dirname(__file__)).replace('\\','/')
    file_path=file_path + "/list_{}.csv".format(market_type)
    rlist = None
    with open (file_path, 'r', encoding='utf8', newline='') as f:
        rows = csv.reader(f)
        rList = list(rows)
    return rList

def insert_to_sql(data):
   
    industry_types = {}


    query = 'if not exists (select * from dbo.StockInfos where Id = %s) begin \
                insert into dbo.StockInfo values (%s, %s, %s, %s, %s) end'
    print('insert query: ' + query)
    conn = pymssql.connect(
               server='192.168.1.28', 
               user='xstocker2', 
               password='L2IZ0xEcOXbH8jL25T1o!', 
               database='xstocker2')  
    cursor = conn.cursor(as_dict=True)
    cursor.execute('select * from dbo.IndustryType')
    for row in cursor:
        industry_types[row['IndustryName']] = row['IndustryId']
    print('industry_types:' + str(industry_types))
    length = len(data)
    for i in range(1, length):
        if data[i][4] not in industry_types:
            print('insert {} into sql'.format(data[i][4]))
            cursor.execute("""insert into dbo.IndustryType (IndustryName) values (%d)""", data[i][4])
            print("result: " + str(cursor.rowcount) )
            if cursor.rowcount >= 1:
                cursor.execute('select IndustryId from dbo.IndustryType where IndustryName=%s', data[i][4])
                industry_types[data[i][4]] = cursor.fetchone()['IndustryId']
        

        data[i][3] = 0 if '上市' in data[i][3] else 1
        data[i][4] = industry_types[data[i][4]]
        data[i] = [data[i][0]] + data[i]
        print('data:' + str(data[i]))
        cursor.execute(query, tuple(data[i]))
    conn.commit()


if __name__ == '__main__':
    marketType = sys.argv[1]
    data = load_csv(4) 
    insert_to_sql(data)