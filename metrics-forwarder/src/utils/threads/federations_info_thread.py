import json
import logging
import threading
import time
from src.utils.kafka.kafka_utils import KafkaUtils
from src.utils.db import DB, db_federation

class FederationsInfoThread:
    """Background thread that consumes messages from Kafka"""

    def __init__(self, domain, producers: dict, sleep_time: int = 10):
        self.domain = domain
        self.producers = producers
        self.sleep_time = sleep_time
        self.t = None

        # TODO: The following code is a temporary solution. This should come from the federation creation process.
        # ======================================================================================
        self.partners_config = self._load_partners_config()
        # ======================================================================================

    def _load_partners_config(self):
        """Load partners configuration from a JSON file"""
        try:
            with open('/etc/partners/partners.json', 'r') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error loading partners config: {e}")
            # Return empty dict as fallback
            return {}

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
            try:
                federations = DB._list("federations", db=db_federation)
                current_partners = set()

                # Create the producers for the current federations
                for federation in federations:
                    if federation.get("partnerOP", {}).get("partnerOPFederationId") == self.domain:
                        federation_partner = federation.get("originOP", {}).get("origOPFederationId")
                        current_partners.add(federation_partner)
                        if federation_partner not in self.producers and federation_partner in self.partners_config:
                            # Create a producer for this federation
                            producer = KafkaUtils.create_producer(
                                config=self.partners_config.get(federation_partner, {}),
                            )
                            self.producers[federation_partner] = producer
                
                # Remove producers not in current federations
                for partner in list(self.producers):
                    if partner not in current_partners:
                        self.producers[partner].close()  # Properly close the Kafka producer
                        del self.producers[partner]

                time.sleep(self.sleep_time)
            except Exception as e:
                logging.error(f"Exception in FederationsInfoThread: {e}")
                continue
