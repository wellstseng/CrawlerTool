from pymongo import MongoClient
import uuid



class MongoManager:
    def __init__(self, url:str):
        self.__client = MongoClient(url)

    def __get_collection(self, db_name, collection_name):
        db = self.__client[db_name]
        if not collection_name in db.list_collection_names(): 
            db.create_collection(collection_name)
        collection = db.get_collection(collection_name)
        return collection

    def upsert(self, db_name, collection_name, condition, query):
        collection = self.__get_collection(db_name, collection_name)
        result = collection.update_one(condition, query, upsert=True)
        return {
            "ok": 1.0,
            "matched_count": result.matched_count,
            "modified_count": result.modified_count,
            "upserted_id": result.upserted_id,
        }
    
    def find_one(self, db_name, collection_name, condition):
        collection = self.__get_collection(db_name, collection_name)
        result = collection.find_one(condition)
        return result
    def get_collection_names(self, db_name):
        db = self.__client[db_name]
        return db.list_collection_names()
    def drop_collection(self, db_name, collection_name):
        db = self.__client[db_name]
        db.drop_collection(collection_name)
