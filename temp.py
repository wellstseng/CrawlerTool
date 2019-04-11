from mongo import MongoManager
mongo_mgr = MongoManager("mongodb://stock:stock@192.168.1.14:27017/stock")

l = mongo_mgr.get_collection_names('stock')
for collection_name in l:
    if "DailyInfo_" in collection_name:
        print(collection_name)
        #mongo_mgr.drop_collection('stock', collection_name)