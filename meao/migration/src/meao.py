import json
import asyncio
import time
import threading
import time
import uuid
import dateutil.parser as dp
import logging

from src.callbacks import load_callback_functions

from src.utils.nbi_k8s_connector import NBIConnector
from src.utils.threads.migration_decision_thread import MigrationDecisionThread
from src.utils.kafka.kafka_utils import KafkaUtils

logging.basicConfig(level=logging.INFO)

class MEAO:
    """
    This class represents the MEAO monitoring and migration agent

    ...

    Attributes
    ----------
    nbi_k8s_connector : NBIConnector
        instance of NBIConnector which simplifies interactions with OSM's NBI and the Kubernetes API
    raw_metrics_topic : str
        kafka topic for the MEAO to subscribe to consume metrics information relating to the containers
    ue_latency_kafka_topic : str
        kafka topic for the MEAO to subscribe to consume latency information relating to the containers
    meh_metrics_topic : str
        kafka topic for the MEAO to communicate with the OSS
    send_container_info_freq : int
        length of time (in seconds) that the send_container_info thread must wait between each message it sends to the OSS
    kafka_consumer_conf: str
        kafka consumer configuration (IP, offset, etc.)
    kafka_producer_conf: str
        kafka producer configuration (IP, etc.)
    migratingContainers: dict
        dictionary to monitor which containers are currently being migrated,
        mapping the container's ID to the corresponding OSM migration operation ID
    cpu_history: dict
        dictionary utilized for cpuLoad calculations
    nodeSpecs: dict
        dictionary storing information relating to the cluster's nodes,
        mapping the node's name to the corresponding node information:
            - num_cpu_cores: int
                the number of CPU cores of the node
            - memory_size: float
                the amount of RAM of the node in GBs
            - cadvisor: str
                name of the cadvisor pod that is collecting metrics in the node
            - cpuLoad: float
                the node's CPU load as calculated based on the collected metrics
            - memLoad: float
                the node's memory load as calculated based on the collected metrics
    containerInfo: dict
        dictionary storing information relating to OSM-deployed containers,
        mapping the container's ID to the corresponding container information:
            - ns_id: str
                the ID of the associated Network Service (NS)
            - vnf_id: str
                the ID of the associated Virtual Network Function (VNF)
            - kdu_id: str
                the ID of the associated Kubernetes Deployment Unit (KDU)
            - node: str
                the node in which the container is deployed
            - cpuLoad: float
                the container's CPU load on the node as calculated based on the collected metrics
            - memLoad: float
                the container's memory load on the node as calculated based on the collected metrics
            - ue-lats: dict
                dictionary storing latency information
            - migration_policy: dict
                dictionary containing the container's migration policy, if stipulated:
                    - mem_load_thresh: float
                        the memory load of the container on the node that corresponds to the "allocated-mem" value
                    - mem_surge_capacity: float
                        the memory load of the container on the node that corresponds to the "mem-surge-capacity" value
                    - cpu_load_thresh: float
                        the cpu load of the container on the node that corresponds to the "allocated-cpu" value
                    - cpu_surge_capacity: float
                        the cpu load of the container on the node that corresponds to the "cpu-surge-capacity" value
                    - mobility-migration-factor: float
                        used for determining migration based on latency information
    """

    def __init__(self, domain, nbi_k8s_connector: NBIConnector, raw_metrics_topic: str, ue_latency_kafka_topic: str, meh_metrics_topic: str, send_container_info_freq: int, kafka_consumer_conf: dict, kafka_producer_conf: dict) -> None:
        self.domain = domain
        self.nbi_k8s_connector = nbi_k8s_connector

        # Configs
        self.raw_metrics_topic = raw_metrics_topic
        self.ue_latency_kafka_topic = ue_latency_kafka_topic
        self.meh_metrics_topic = meh_metrics_topic
        self.send_container_info_freq = send_container_info_freq

        # Load topics
        self.callbacks = load_callback_functions()
        self.topics = list(self.callbacks.keys())

        # Kafka configurations
        self.kafka_consumer_conf = kafka_consumer_conf
        self.kafka_producer_conf = kafka_producer_conf
        self.producer = KafkaUtils.create_producer(config=self.kafka_producer_conf)
        self.consumer = KafkaUtils.create_consumer(config=self.kafka_consumer_conf, topics=self.topics)

        # Data tracking
        self.mec_apps = {}
        self.appis = {}
        self.current_metrics = {}
        self.nodeSpecs = {}
        self.federation_meh_metrics = {}

        # Logic tracking
        self.possible_migrations = {}
        self.migrating_apps = set()
        self.expected_resource_gains = {}
        self.waiting_responses = {}

        # Tests
        self.log = {}
        with open("results.csv", "w") as log_file:
            log_file.write("Metrics Collection,Metrics Reception,Migration Decision,Target Pod Initialization,Target Pod Ready,Source Pod Termination,Migration Completion in OSM\n")

    def run(self):
        """
        Starts all threads:

            update_container_ids:
                thread for updating the nodeSpecs and containerInfos
        """
        logging.info(f"Listening for messages on topics: {self.topics}")

        # Start the threads
        MigrationDecisionThread(self).start()

        # Start receiving and processing the messages
        try:
            for response in KafkaUtils.consume_messages(self.consumer, self, self.callbacks, max_workers=10):
                if response:
                    logging.info(f"Sending response: {response}")
                    KafkaUtils.send_message(self.producer, "responses", response)
        except Exception as e:
            logging.error(f"An error occurred: {e}")

        finally:
            self.producer.close()
            logging.info(f"Restarting Kafka...")
    

    def migrate(self, appi_id, kdu_id, domain, cluster_id, finalTargetNode):
        """
        Starts a migration operation for the specified artifact.

        Parameters
        ----------
        appi_id : str
            the ID of the application instance
        kdu_id : str
            the ID of the Kubernetes Deployment Unit (KDU) to be migrated
        domain : str
            the domain in which the application instance is going to be migrated into
        cluster_id : str
            the ID of the cluster in which the application instance is going to be migrated into
        finalTargetNode : str
            the name of the node to which the KDU will be migrated into
        """

        if (appi_id, kdu_id) in self.migrating_apps:
            return False
        
        kdu_current_node = next({"domain": domain, "cluster": cluster, "node": node} for domain in self.appis[appi_id]["instances"] for cluster in self.appis[appi_id]["instances"][domain] for kdu, node in self.appis[appi_id]["instances"][domain][cluster]["kdus"].items() if kdu == kdu_id)

        logging.info(f"Migrating kdu {kdu_id} from appi {appi_id} to node {finalTargetNode} at cluster {cluster_id} and domain {domain}")

        # Trigger a migration in the MEAO
        message = {"appi_id": appi_id, "kdu_id": kdu_id, "domain": domain, "cluster_id": cluster_id, "node": finalTargetNode}
        msg_id = KafkaUtils.send_message(self.producer, "migrate_app", message)

        # Calculate the expected resources gain
        expected_cpu_gain =  max(self.appis.get(appi_id, {}).get("migration_policy", {}).get(kdu_id, {}).get("cpu-criteria", {}).get("allocated-cpu", 0) - self.current_metrics.get(appi_id, {}).get(kdu_id, {}).get("metrics", {}).get("cpuUsage", 0), 0)
        expected_mem_gain = max(self.appis.get(appi_id, {}).get("migration_policy", {}).get(kdu_id, {}).get("mem-criteria", {}).get("allocated-mem", 0) - self.current_metrics.get(appi_id, {}).get(kdu_id, {}).get("metrics", {}).get("memUsage", 0), 0)

        # Add the expected resource gains so that the MEAO starts detecting the migration discrepancies
        key = (domain, cluster_id, finalTargetNode)
        if key not in self.expected_resource_gains:
            self.expected_resource_gains[key] = {"cpu": 0, "mem": 0}
        self.expected_resource_gains[key]["cpu"] += expected_cpu_gain
        self.expected_resource_gains[key]["mem"] += expected_mem_gain

        # Add the app and the kdu to the currently migrating apps
        self.migrating_apps.add((appi_id, kdu_id))
        self.waiting_responses[msg_id] = {"type": "migration", "app": (appi_id, kdu_id), "from": kdu_current_node, "to": {"domain": domain, "cluster": cluster_id, "node": finalTargetNode}, "expected_gain": {"cpu": expected_cpu_gain, "mem": expected_mem_gain}}

        logging.info(f"Expected gain: {self.waiting_responses[msg_id]['expected_gain']}")

        return True
