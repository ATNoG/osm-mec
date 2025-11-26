import logging
from src.callbacks import load_callback_functions

from src.utils.nbi_k8s_connector import NBIConnector
from src.utils.kafka.kafka_utils import KafkaUtils
from src.utils.threads.send_cluster_metrics_thread import SendClusterMetricsThread
from src.utils.threads.send_federation_containers_thread import SendFederationContainersThread

logging.basicConfig(level=logging.INFO)

class MEAO:
    """
    This class represents the MEAO monitoring service

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
        kafka topic for the MEAO to publish information related with the monitored containers
    send_cluster_metrics_freq : int
        length of time (in seconds) that the send_cluster_metrics thread must wait between each message it sends to the OSS
    kafka_consumer_conf: str
        kafka consumer configuration (IP, offset, etc.)
    kafka_producer_conf: str
        kafka producer configuration (IP, etc.)
    prev_cpu: dict
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
    """
    def __init__(self, domain: str, nbi_k8s_connector: NBIConnector, raw_metrics_topic: str, ue_latency_kafka_topic: str, meh_metrics_topic: str, send_cluster_metrics_freq: int, kafka_consumer_conf: dict, kafka_producer_conf: dict) -> None:
        self.domain = domain
        # NBI Connector
        self.nbi_k8s_connector = nbi_k8s_connector

        # Kafka topics
        self.raw_metrics_topic = raw_metrics_topic
        self.ue_latency_kafka_topic = ue_latency_kafka_topic
        self.meh_metrics_topic = meh_metrics_topic

        # Frequency of sending container info to the OSS
        self.send_cluster_metrics_freq = send_cluster_metrics_freq

        self.callbacks = load_callback_functions()
        self.topics = list(self.callbacks.keys())

        # Kafka configurations
        self.kafka_producer_conf = kafka_producer_conf
        self.kafka_consumer_conf = kafka_consumer_conf
        self.producer = KafkaUtils.create_producer(config=self.kafka_producer_conf)
        self.consumer = KafkaUtils.create_consumer(config=self.kafka_consumer_conf, topics=self.topics)

        # Initialize the dictionaries
        self.node_specs = {}
        self.appis = {}
        self.federation_appis = {}  # App_id: "instances" -> {}
        self.federation_appis_metrics = {}
        self.container_to_app = {}
        self.federation_container_to_app = {}
        self.current_metrics = {}
        self.prev_cpu = {}

    def run(self):
        """
        Starts all threads:

            read_metrics_collector:
                thread for collecting and processing metrics relating to each node and container

            read_ue_latency:
                thread for collecting and processing latency information

            update_appis:
                thread for updating the nodeSpecs and containerInfos

            send_cluster_metrics:
                thread for sending the nodeSpecs and containerInfo dictionaries to the OSS
        """
        
        logging.info(f"Listening for messages on topics: {self.topics}")

        # Create threads
        # read_ue_latency = threading.Thread(target=self.read_ue_latency)
        SendClusterMetricsThread(self.producer, self.appis, self.current_metrics, self.federation_appis_metrics, self.container_to_app, self.node_specs, self.meh_metrics_topic, self.send_cluster_metrics_freq).start()
        SendFederationContainersThread(self.producer, self.federation_container_to_app, "federation-containers", self.send_cluster_metrics_freq).start()
        # SendContainerToAppThread(self.producer, self.container_to_app, "container_to_app", self.send_cluster_metrics_freq).start()
    
        try:
            for response in KafkaUtils.consume_messages(self.consumer, self, self.callbacks, max_workers=10):
                if response:
                    logging.info(f"Sending response: {response}")
                    KafkaUtils.send_message(self.producer, "responses", response)
        except Exception as e:
            logging.error(f"An error occurred: {e}")

        finally:
            self.producer.close()
            self.consumer.close()
            logging.info(f"Restarting Kafka...")



    def get_node_specs(self, hostname=None):
        """
        Returns information relating to the cluster's nodes

        Parameters
        ----------
        hostname : str, optional
            if specified, the function returns only the chosen node's information (default is None)
        """
        if hostname:
            if hostname in self.node_specs.keys():
                return self.node_specs[hostname]
            else:
                return None
        else:
            return self.node_specs


    def get_container_ids(self):
        return self.container_to_app
