import threading
import time
from src.utils.kafka.kafka_utils import KafkaUtils
from src.utils.db import DB, db_federation

class FederationsInfoThread:
    """Background thread that consumes messages from Kafka"""

    def __init__(self, domain, federations_context_id: dict, sleep_time: int = 10):
        self.domain = domain
        self.federations_context_id = federations_context_id
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
            federations = DB._list("federations", db=db_federation)
            current_federations = {}

            # Create the producers for the current federations
            for federation in federations:
                if federation.get("originOP", {}).get("origOPFederationId") == self.domain:
                    federation_partner = federation.get("partnerOP", {}).get("partnerOPFederationId")
                    federation_context_id = federation.get("partnerOP", {}).get("federationContextId")
                    current_federations[federation_partner] = federation_context_id
            
            # Update the current federations
            self.federations_context_id.clear()
            self.federations_context_id.update(current_federations)

            time.sleep(self.sleep_time)
