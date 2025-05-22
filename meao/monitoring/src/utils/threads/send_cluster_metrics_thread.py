import copy
import threading
import time
import logging
from src.utils.kafka.kafka_utils import KafkaUtils

class SendClusterMetricsThread:
    """Background thread that sends MEC Apps information"""

    def __init__(self, producer, appis: dict, current_metrics: dict, container_to_app: dict, node_specs: dict, meh_metrics_topic: str, send_cluster_metrics_freq: int):
        self.producer = producer

        self.appis = appis
        self.current_metrics = current_metrics
        self.container_to_app = container_to_app
        self.node_specs = node_specs

        self.meh_metrics_topic = meh_metrics_topic
        self.send_cluster_metrics_freq = send_cluster_metrics_freq

        self.t = None

    def start(self):
        """Plugin entrypoint"""
        self.t = threading.Thread(target=self.send_cluster_metrics, args=())
        self.t.daemon = True
        self.t.start()
    
    def send_cluster_metrics(self):
        while True:
            try:
                nodes_specs = copy.deepcopy(self.node_specs)
                for cluster_id, cluster_data in nodes_specs.items():
                    for node_id in cluster_data["nodeSpecs"]:
                        # Reset node appis metrics aggregation
                        nodes_specs[cluster_id]["nodeSpecs"][node_id]["appis-cpuUsage"] = 0
                        nodes_specs[cluster_id]["nodeSpecs"][node_id]["appis-cpuLoad"] = 0
                        nodes_specs[cluster_id]["nodeSpecs"][node_id]["appis-memUsage"] = 0
                        nodes_specs[cluster_id]["nodeSpecs"][node_id]["appis-memLoad"] = 0
                        nodes_specs[cluster_id]["nodeSpecs"][node_id]["appis-count"] = 0

                app_metrics = copy.deepcopy(self.current_metrics)
                for _, app_data in app_metrics.items():
                    for _, kdu_data in app_data.items():
                        # Reset KDU metrics aggregation
                        kdu_cpu_usage, kdu_cpu_load, kdu_mem_usage, kdu_mem_load, kdu_pod_count = 0, 0, 0, 0, 0

                        for _, pod_data in kdu_data["pods"].items():
                            pod_cpu_usage, pod_cpu_load, pod_mem_usage, pod_mem_load, pod_container_count = 0, 0, 0, 0, 0

                            for container_name, container_data in pod_data["containers"].items():
                                metrics = container_data["metrics"]
                                pod_cpu_usage += metrics.get("cpuUsage", 0)
                                pod_cpu_load += metrics.get("cpuLoad", 0)
                                pod_mem_usage += metrics.get("memUsage", 0)
                                pod_mem_load += metrics.get("memLoad", 0)

                                container_metrics = {
                                    "cpuUsage": metrics.get("cpuUsage", 0),
                                    "cpuLoad": metrics.get("cpuLoad", 0),
                                    "memUsage": metrics.get("memUsage", 0),
                                    "memLoad": metrics.get("memLoad", 0),
                                }
                                container_data["metrics"] = container_metrics

                                if "cpuUsage" in metrics:
                                    pod_container_count += 1
                                
                            nodes_specs[self.container_to_app[container_name]["cluster_id"]]["nodeSpecs"][self.container_to_app[container_name]["node"]]["appis-cpuUsage"] += pod_cpu_usage
                            nodes_specs[self.container_to_app[container_name]["cluster_id"]]["nodeSpecs"][self.container_to_app[container_name]["node"]]["appis-cpuLoad"] += pod_cpu_load
                            nodes_specs[self.container_to_app[container_name]["cluster_id"]]["nodeSpecs"][self.container_to_app[container_name]["node"]]["appis-memUsage"] += pod_mem_usage
                            nodes_specs[self.container_to_app[container_name]["cluster_id"]]["nodeSpecs"][self.container_to_app[container_name]["node"]]["appis-memLoad"] += pod_mem_load

                            if pod_container_count > 0:
                                pod_metrics = {
                                    "cpuUsage": pod_cpu_usage / pod_container_count,
                                    "cpuLoad": pod_cpu_load,
                                    "memUsage": pod_mem_usage / pod_container_count,
                                    "memLoad": pod_mem_load,
                                }
                                pod_data["metrics"] = pod_metrics
                            else:
                                pod_data["metrics"] = {
                                    "cpuUsage": 0,
                                    "cpuLoad": 0,
                                    "memUsage": 0,
                                    "memLoad": 0,
                                }

                            # Add to KDU-level aggregation
                            kdu_cpu_usage += pod_data["metrics"].get("cpuUsage", 0)
                            kdu_cpu_load += pod_data["metrics"].get("cpuLoad", 0)
                            kdu_mem_usage += pod_data["metrics"].get("memUsage", 0)
                            kdu_mem_load += pod_data["metrics"].get("memLoad", 0)

                            if "cpuUsage" in pod_data["metrics"]:
                                kdu_pod_count += 1

                        if kdu_pod_count > 0:
                            kdu_data["metrics"] = {
                                "cpuUsage": kdu_cpu_usage / kdu_pod_count,
                                "cpuLoad": kdu_cpu_load,
                                "memUsage": kdu_mem_usage / kdu_pod_count,
                                "memLoad": kdu_mem_load,
                            }
                        else:
                            kdu_data["metrics"] = {
                                "cpuUsage": 0,
                                "cpuLoad": 0,
                                "memUsage": 0,
                                "memLoad": 0,
                            }

                message = {
                    "appis": app_metrics,
                    "nodeSpecs": nodes_specs,
                }

                # Kafka sending placeholder
                KafkaUtils.send_message(self.producer, self.meh_metrics_topic, message)
                logging.info("Sent message to Kafka topic {}: {}".format(self.meh_metrics_topic, message))

                time.sleep(self.send_cluster_metrics_freq)

            except Exception as e:
                print("INFO: Exception while sending container info: ", e)
                continue
