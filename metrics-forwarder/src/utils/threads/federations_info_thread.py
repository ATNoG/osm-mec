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
                "bootstrap_servers": "10.255.41.143:31999",
                "security_protocol": "SASL_PLAINTEXT",
                "sasl_mechanism": "PLAIN",
                "sasl_plain_username": "user1",
                "sasl_plain_password": "K5nT4EAnhx"
            },
            "TEST_DOMAIN": {
                "bootstrap_servers": "10.255.41.81:31999",
                "security_protocol": "SASL_PLAINTEXT",
                "sasl_mechanism": "PLAIN",
                "sasl_plain_username": "user1",
                "sasl_plain_password": "nczChFRDn6"
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

            # TODO: The following code is purely a temporary solution to keep the work before integrating with the actual federation management system.
            # ======================================================================================
            for federation in federations:
                if federation.get("originOP", {}).get("origOPFederationId") == "federation-12345":
                    federation["originOP"]["origOPFederationId"] = "IT_AVEIRO"
                else:
                    federation["originOP"]["origOPFederationId"] = "TEST_DOMAIN"
                
                if federation.get("partnerOP", {}).get("partnerOPFederationId") == "federation-12345":
                    federation["partnerOP"]["partnerOPFederationId"] = "IT_AVEIRO"
                else:
                    federation["partnerOP"]["partnerOPFederationId"] = "TEST_DOMAIN"
            # ======================================================================================

            # Get credentials for the federation somehow
            for federation in federations:
                if federation.get("originOP", {}).get("origOPFederationId") == self.domain:
                    federation_partner = federation.get("partnerOP", {}).get("partnerOPFederationId")
                    current_partners.add(federation_partner)
                    if federation_partner not in self.producers:
                        # Create a producer for this federation
                        print("Creating producer for federation partner:", federation_partner)
                        print("Using config:", self.partners_config.get(federation_partner, {}))
                        producer = KafkaUtils.create_producer(
                            config=self.partners_config.get(federation_partner, {}),
                        )
                        self.producers[federation_partner] = producer
            
            # Remove producers not in current federations
            for partner in list(self.producers):
                if partner not in current_partners:
                    self.producers[partner].close()  # Properly close the Kafka producer
                    del self.producers[partner]

            print("Current Federations:", federations)
            print("Current Producers:", self.producers)
            time.sleep(self.sleep_time)
