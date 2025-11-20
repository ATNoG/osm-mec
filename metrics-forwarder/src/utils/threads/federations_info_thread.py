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

        # TODO: The following code is purely a temporary solution to keep the work before integrating with the actual federation management system.
        # ======================================================================================
        self.partners_config = {
            "IT_AVEIRO": {
                "bootstrap_servers": "10.255.41.4:31999",
                "security_protocol": "SASL_PLAINTEXT",
                "sasl_mechanism": "PLAIN",
                "sasl_plain_username": "user1",
                "sasl_plain_password": "IvndH8Si21"
            },
            "PARTNER": {
                "bootstrap_servers": "10.255.41.8:31999",
                "security_protocol": "SASL_PLAINTEXT",
                "sasl_mechanism": "PLAIN",
                "sasl_plain_username": "user1",
                "sasl_plain_password": "2jQd7t0Hfm"
            },
        }
        # ======================================================================================

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
