import threading
import time
from src.utils.nbi_k8s_connector import NBIConnector
from src.utils.kafka.kafka_utils import KafkaUtils
from src.utils.db import DB

class InfrastructureInfoThread:
    """Background thread that consumes messages from Kafka"""

    def __init__(self, domain, producer, nbi_k8s_connector: NBIConnector, infrastructure_info: dict, sleep_time: int = 10):
        self.domain = domain
        self.producer = producer
        self.nbi_k8s_connector = nbi_k8s_connector
        self.infrastructure_info = infrastructure_info
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
            # Get the clusters from the own infrastructure
            self.infrastructure_info.clear()
            clusters = self.nbi_k8s_connector.get_clusters()
            
            # If we cannot get the clusters, wait and retry
            if clusters is None:
                time.sleep(self.sleep_time)
                continue

            # Get each node in the cluster
            for cluster in clusters:
                self.infrastructure_info[cluster["_id"]] = {
                    "domain": self.domain,
                    "name": cluster["name"],
                    "k8s-version": cluster["k8s_version"],
                    "vim-account": cluster["vim_account"],
                    "description": cluster["description"],
                    "nets": cluster["nets"],
                }
                
                # Save credentials to the database
                self.nbi_k8s_connector.save_credentials(cluster["_id"], cluster["credentials"])

                # Get each node in the cluster
                nodeSpecs = self.nbi_k8s_connector.getNodeSpecs(cluster["_id"])

                for node in nodeSpecs:
                    current_allocated_resources = DB._get_by("resources", {"cluster": cluster["_id"], "node": node})
                    if not current_allocated_resources:
                        DB._add("resources", {
                            "cluster": cluster["_id"],
                            "node": node,
                            "allocated-cpu": 0,
                            "allocated-mem": 0
                        })
                        nodeSpecs[node]["allocated-cpu"] = 0
                        nodeSpecs[node]["allocated-mem"] = 0
                    else:
                        nodeSpecs[node]["allocated-cpu"] = current_allocated_resources["allocated-cpu"]
                        nodeSpecs[node]["allocated-mem"] = current_allocated_resources["allocated-mem"]
                        
                self.infrastructure_info[cluster["_id"]]["nodeSpecs"] = nodeSpecs

            # Publish the infrastructure information to Kafka
            KafkaUtils.send_message(
                self.producer,
                "infrastructure-info",
                self.infrastructure_info
            )

            time.sleep(self.sleep_time)
