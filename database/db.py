import config
from database import sheets, mongo


class Database:
    def __init__(self, update=None):
        if config.DB_TYPE == "mongo":
            self.service = mongo.MongoService(update)
        else:
            self.service = sheets.SheetsService(update)
