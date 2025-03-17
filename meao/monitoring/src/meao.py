import json
import asyncio
import time
import threading
import time
import dateutil.parser as dp
from confluent_kafka import Consumer, Producer, KafkaError

from src.utils.nbi_k8s_connector import NBIConnector
from src.utils.threads.kafka_consumer_thread import KafkaConsumerThread
from src.utils.kafka.kafka_utils import KafkaUtils

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
    def __init__(self, nbi_k8s_connector: NBIConnector, raw_metrics_topic: str, ue_latency_kafka_topic: str, meh_metrics_topic: str, send_cluster_metrics_freq: int, kafka_consumer_conf: dict, kafka_producer_conf: dict) -> None:
        # NBI Connector
        self.nbi_k8s_connector = nbi_k8s_connector

        # Kafka topics
        self.raw_metrics_topic = raw_metrics_topic
        self.ue_latency_kafka_topic = ue_latency_kafka_topic
        self.meh_metrics_topic = meh_metrics_topic

        # Frequency of sending container info to the OSS
        self.send_cluster_metrics_freq = send_cluster_metrics_freq

        # Kafka configurations
        self.kafka_consumer_conf = kafka_consumer_conf
        self.kafka_producer_conf = kafka_producer_conf
        self.producer = KafkaUtils.create_producer(self.kafka_producer_conf)

        # Initialize the dictionaries
        self.nodeSpecs = self.nbi_k8s_connector.getNodeSpecs()
        self.containerInfo = self.nbi_k8s_connector.getContainerInfo(self.nodeSpecs)
        self.prev_cpu = {}

        print("Node Specs: " + str(self.nodeSpecs))
        print("Container Info: " + str(self.containerInfo))


    def start(self):
        """
        Starts all threads:

            read_metrics_collector:
                thread for collecting and processing metrics relating to each node and container

            read_ue_latency:
                thread for collecting and processing latency information

            update_container_ids:
                thread for updating the nodeSpecs and containerInfos

            send_cluster_metrics:
                thread for sending the nodeSpecs and containerInfo dictionaries to the OSS
        """
        
        # Create threads
        KafkaConsumerThread(self.kafka_consumer_conf, "raw-metrics", self.process_metrics).start()
        KafkaConsumerThread(self.kafka_consumer_conf, "mec-apps", self.update_container_ids).start()
        # read_ue_latency = threading.Thread(target=self.read_ue_latency)
        send_cluster_metrics_thread = threading.Thread(target=self.send_cluster_metrics).start()


    def get_node_specs(self, hostname=None):
        """
        Returns information relating to the cluster's nodes

        Parameters
        ----------
        hostname : str, optional
            if specified, the function returns only the chosen node's information (default is None)
        """
        if hostname:
            if hostname in self.nodeSpecs.keys():
                return self.nodeSpecs[hostname]
            else:
                return None
        else:
            return self.nodeSpecs


    def get_container_ids(self):
        return self.containerInfo


    def update_node_specs(self):
        self.nodeSpecs = self.nbi_k8s_connector.getNodeSpecs()
    

    def processContainerLatencies(self, cName, values):
        """
        Processes latency information

        Parameters
        ----------
        cName : str
            the container's ID
        values: dict
            dictionary containing latency information
        """
        self.containerInfo[cName]["ue-lats"] = values
    

    def updateDict(self, oldDict, updatedDict):
        """
        Simple function to ensures the old dictionary is updated without altering the existing contents unnecessarily.

        Parameters
        ----------
        oldDict : dict
            dictionary to be updated
        values: dict
            dictionary with new content
        """
        keys_to_keep = set(oldDict.keys()).intersection(updatedDict.keys())
        keys_to_remove = set(oldDict.keys()) - keys_to_keep
        for key in keys_to_remove:
            oldDict.pop(key)
        
        keys_to_add = set(updatedDict.keys()) - set(oldDict.keys())
        for key in keys_to_add:
            oldDict[key] = updatedDict[key]

        return oldDict


    def read_ue_latency(self):
        """
        !!! THREAD !!! 
        
        read_ue_latency:
            thread for collecting and processing latency information
        """
        # create kafka consumer
        consumer = Consumer(self.kafka_consumer_conf)

        # subscribe to the topic
        consumer.subscribe([self.ue_latency_kafka_topic])

        try:
            print("Listening to Kafka on topic {}....".format(self.ue_latency_kafka_topic))
            while True:
                
                # poll for messages
                message = consumer.poll(1.0)

                if message is None:
                    continue
                if message.error():
                    if message.error().code() == KafkaError._PARTITION_EOF:
                        # end of partition
                        continue
                    else:
                        # error
                        print("Error: {}".format(message.error()))
                        break

                # process the message
                values = json.loads(message.value().decode('utf-8'))
                try:
                    # since information regarding every node is received, each container's latency information 
                    for containerName in self.containerInfo.keys():
                        t = threading.Thread(target=self.processContainerLatencies, args=(containerName, values,))
                        t.start()
                except RuntimeError as e:
                    print("INFO: Exception while processing kafka messages: ", e)

        except KeyboardInterrupt:
            # Stop consumer on keyboard interrupt
            consumer.close()


    def update_container_ids(self, data):
        """
        !!! THREAD !!! 
        
        update_container_ids:
            thread for collecting and processing MEC Application information received from the OSS
            updates the nodeSpecs and containerInfo
        """

        try:
            # update node specs
            newNodeSpecs = self.nbi_k8s_connector.getNodeSpecs()
            for nodeName in self.nodeSpecs.keys():
                if (
                    nodeName in newNodeSpecs
                    and "cadvisor" in self.nodeSpecs[nodeName].keys() 
                    and "cadvisor" in newNodeSpecs[nodeName].keys() 
                    and self.nodeSpecs[nodeName]["cadvisor"] != newNodeSpecs[nodeName]["cadvisor"]
                ):
                    self.nodeSpecs[nodeName]["cadvisor"] = newNodeSpecs[nodeName]["cadvisor"]
            self.nodeSpecs = self.updateDict(self.nodeSpecs, newNodeSpecs)

            # update container info
            self.containerInfo = self.updateDict(self.containerInfo, self.nbi_k8s_connector.getContainerInfo(self.nodeSpecs, data["mec_apps"]))
        except RuntimeError as e:
            print("INFO: Exception while processing kafka messages: ", e)
    

    def send_cluster_metrics(self):
        """
        !!! THREAD !!! 
        
        send_cluster_metrics:
            thread for sending the nodeSpecs and containerInfo dictionaries to the OSS
        """
        while True:
            try:
                message = {
                    "containerInfo": self.containerInfo,
                    "nodeSpecs": self.nodeSpecs,
                }
                KafkaUtils.send_message(self.producer, self.meh_metrics_topic, message)
                time.sleep(self.send_cluster_metrics_freq)
            except Exception as e:
                print("INFO: Exception while sending container info: ", e)
                continue
    

    def process_metrics(self, data):
        """
        Processes raw metrics related to each node and container
        """
        
        # process the message
        cName = data["container_Name"]

        # if the received information is related to a node
        if cName == "/":
            # obtain the name of the associated cadvisor pod
            machine_name = data["machine_name"]
            # ensure nodeSpecs contains information relating to this node
            if not any(machine_name in nodeInfo.values() for node, nodeInfo in self.nodeSpecs.items()):
                return
            # if so, process the metrics information received
            for node, nodeInfo in self.nodeSpecs.items():
                if nodeInfo["cadvisor"] == machine_name:
                    t = threading.Thread(target=self.update_meh_metrics, args=(node, data, False, False))
                    t.start()
                    break

        # if the received information is related to a container
        containers = self.containerInfo.items()
        for containerName, container in containers:
            # if it is a OSM-deployed container and containerInfo contains information
            # relating to it, process the metrics information received
            if containerName in cName:
                t = threading.Thread(target=self.update_meh_metrics, args=(containerName, data, container, False))
                t.start()

    def update_meh_metrics(self, cName, values, container=None, silent=True):
        """
        Calculates the cpu and memory load based on the metrics information relating to a node or container

        Parameters
        ----------
        cName : str
            the container's ID
        values: dict
            dictionary containing metrics information relating to a node or container
        container: dict, optional
            information relating to the container whose metrics are being processed, obtained from the containerInfo dictionary (default is None)
        silent: boolean, optional
            flag determining whether the information printing functionality is suppressed (default is True)
        """
        if container:
            memory_size = (self.nodeSpecs[container["node"]]["memory_size"]*pow(1024,3))
            num_cpu_cores = self.nodeSpecs[container["node"]]["num_cpu_cores"]
        else:
            memory_size = (self.nodeSpecs[cName]["memory_size"]*pow(1024,3))
            num_cpu_cores = self.nodeSpecs[cName]["num_cpu_cores"]

        # CPU load corresponds to the amount of time that was spent executing tasks over a certain time period
        # this can be obtained by calculating the ratio of CPU time delta over the system time delta

        # the current timestamp corresponds to the current system time
        timestampParts = values["timestamp"].split(':')
        timestamp = (float(timestampParts[-3][-2:])*pow(60,2) + float(timestampParts[-2])*60 + float(timestampParts[-1][:-1])) * pow(10, 9)
        # the cpu usage value corresponds to the current CPU time
        current_cpu = values["container_stats"]["cpu"]["usage"]["total"]
        if cName not in self.prev_cpu.keys():
            self.prev_cpu[cName] = {}
            self.prev_cpu[cName]["previousCPU"] = 0
            self.prev_cpu[cName]["previousSystem"] = 0

        # Get the CPU usage and time
        cpu_usage = current_cpu - self.prev_cpu[cName]["previousCPU"]
        elapsed_time = timestamp - self.prev_cpu[cName]["previousSystem"]

        # calculate the ratio of the CPU time delta over the system time delta compared to the number of cores of the node
        cpuLoad = 0
        if elapsed_time > 0.0 and cpu_usage >= 0.0:
            cpuLoad = min(round(((cpu_usage / elapsed_time) / num_cpu_cores) * 100, 2), 100)

        # store the current times in the prev_cpu dictionary for future iterations of this function
        self.prev_cpu[cName]["previousCPU"] = current_cpu
        self.prev_cpu[cName]["previousSystem"] = timestamp

        # memory load corresponds to the amount of memory used compared to the total memory of the node
        memUsage = values["container_stats"]["memory"]["usage"]
        memLoad = (memUsage/memory_size) * 100

        if not container:
            self.nodeSpecs[cName]["cpuLoad"] = cpuLoad
            self.nodeSpecs[cName]["memLoad"] = memLoad
        else:        
            self.containerInfo[cName]["cpuLoad"] = cpuLoad
            self.containerInfo[cName]["memLoad"] = memLoad
        
        if not silent:
            print("-------------------------------------------------------")
            print("Container ID:", cName)
            print("Machine Name:", values["machine_name"])
            print("Timestamp:", values["timestamp"])
            print("CPU Cores:", num_cpu_cores)
            print("CPU Load:", cpuLoad)
            print("Memory Size:", memory_size)
            print("Memory Load:", memLoad)
            print("-------------------------------------------------------")