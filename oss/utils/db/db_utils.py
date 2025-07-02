import os

from bson import ObjectId
from pymongo import MongoClient

client = MongoClient(
    "mongodb://mongo:27017/",
    username=os.getenv("MONGO_USER"),
    password=os.getenv("MONGO_PASSWORD"),
)

db = client["db"]
db_federation = client["federation"]


class DB:
    @staticmethod
    def _get(id, collection, db=db):
        return db[collection].find_one({"_id": ObjectId(id)})

    @staticmethod
    def _find(collection, filter=None, db=db):
        return db[collection].find_one(filter)

    @staticmethod
    def _list(collection, filter=None, db=db):
        return list(db[collection].find(filter))

    @staticmethod
    def _add(collection, data, db=db):
        id = db[collection].insert_one(data).inserted_id
        return str(id)

    @staticmethod
    def _update(id, collection, data, db=db):
        db[collection].update_one({"_id": ObjectId(id)}, {"$set": data})

    @staticmethod
    def _delete(id, collection, db=db):
        db[collection].delete_one({"_id": ObjectId(id)})

    @staticmethod
    def _exists(id, collection, db=db):
        return db[collection].find_one({"_id": ObjectId(id)}) is not None
    
    @staticmethod
    def _exists_by(collection, filter, db=db):
        return db[collection].find_one(filter) is not None
