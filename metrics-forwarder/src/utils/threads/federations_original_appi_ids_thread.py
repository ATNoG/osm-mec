import threading
import time
from src.utils.kafka.kafka_utils import KafkaUtils
from src.utils.db import DB, db_federation

class FederationsOriginalAppiIdsThread:
    """Background thread that consumes messages from Kafka"""

    def __init__(self, original_appi_ids, sleep_time: int = 10):
        self.original_appi_ids = original_appi_ids
        self.sleep_time = sleep_time
        self.t = None

    def start(self):
        """Plugin entrypoint"""

        self.t = threading.Thread(
            target=self.executor, args=()
        )
        self.t.daemon = True
        self.t.start()


    def executor(self):
        """Background worker thread"""
        while True:
            federation_appis = DB._list("appInstances", db=db_federation)
            
            for appi in federation_appis:
                local_appi_id = appi.get("appiId")
                original_appi_id = appi.get("appInstanceId")
                self.original_appi_ids[local_appi_id] = original_appi_id

            time.sleep(self.sleep_time)
