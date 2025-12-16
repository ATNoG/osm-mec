import copy
import threading
import time
import logging
from src.utils.kafka.kafka_utils import KafkaUtils

class SendClusterMetricsThread:
    """Background thread that sends MEC Apps information"""

    def __init__(self, producer, appis: dict, current_metrics: dict, federation_appis_metrics: dict, container_to_app: dict, node_specs: dict, federation_node_specs: dict, meh_metrics_topic: str, send_cluster_metrics_freq: int):
        self.producer = producer

        self.appis = appis
        self.current_metrics = current_metrics
        self.federation_appis_metrics = federation_appis_metrics
        self.container_to_app = container_to_app
        self.node_specs = node_specs
        self.federation_node_specs = federation_node_specs

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
                # Reset nodeSpecs appis metrics aggregation
                nodes_specs = copy.deepcopy(self.node_specs)
                for cluster_id, cluster_data in nodes_specs.items():
                    for node_id in cluster_data["nodeSpecs"]:
                        nodes_specs[cluster_id]["nodeSpecs"][node_id]["appis-cpuUsage"] = 0
                        nodes_specs[cluster_id]["nodeSpecs"][node_id]["appis-cpuLoad"] = 0
                        nodes_specs[cluster_id]["nodeSpecs"][node_id]["appis-memUsage"] = 0
                        nodes_specs[cluster_id]["nodeSpecs"][node_id]["appis-memLoad"] = 0
                        nodes_specs[cluster_id]["nodeSpecs"][node_id]["appis-count"] = 0

                app_metrics = copy.deepcopy(self.current_metrics)
                for _, app_data in app_metrics.items():
                    for _, kdu_data in app_data.items():
                        kdu_cpu_usage, kdu_cpu_load, kdu_mem_usage, kdu_mem_load = 0, 0, 0, 0
                        for _, pod_data in kdu_data["pods"].items():
                            pod_cpu_usage, pod_cpu_load, pod_mem_usage, pod_mem_load = 0, 0, 0, 0
                            for container_name, container_data in pod_data["containers"].items():
                                if container_name not in self.container_to_app:
                                    continue
                                metrics = container_data["metrics"]
                                    

                                # Add to pod-level aggregation
                                pod_cpu_usage += metrics.get("cpuUsage", 0)
                                pod_cpu_load += metrics.get("cpuLoad", 0)
                                pod_mem_usage += metrics.get("memUsage", 0)
                                pod_mem_load += metrics.get("memLoad", 0)

                            # Add to KDU-level aggregation
                            kdu_cpu_usage += pod_cpu_usage
                            kdu_cpu_load += pod_cpu_load
                            kdu_mem_usage += pod_mem_usage
                            kdu_mem_load += pod_mem_load

                            # Update pod-level metrics
                            pod_data["metrics"] = {
                                "cpuUsage": round(pod_cpu_usage, 2),
                                "cpuLoad": round(pod_cpu_load, 2),
                                "memUsage": round(pod_mem_usage, 2),
                                "memLoad": round(pod_mem_load, 2),
                            }

                        # Update KDU-level metrics
                        kdu_data["metrics"] = {
                            "cpuUsage": round(kdu_cpu_usage, 2),
                            "cpuLoad": round(kdu_cpu_load, 2),
                            "memUsage": round(kdu_mem_usage, 2),
                            "memLoad": round(kdu_mem_load, 2),
                        }

                        # Update node-level aggregation
                        nodes_specs[kdu_data["cluster"]]["nodeSpecs"][kdu_data["node"]]["appis-cpuUsage"] += kdu_cpu_usage
                        nodes_specs[kdu_data["cluster"]]["nodeSpecs"][kdu_data["node"]]["appis-cpuLoad"] += kdu_cpu_load
                        nodes_specs[kdu_data["cluster"]]["nodeSpecs"][kdu_data["node"]]["appis-memUsage"] += kdu_mem_usage
                        nodes_specs[kdu_data["cluster"]]["nodeSpecs"][kdu_data["node"]]["appis-memLoad"] += kdu_mem_load
                

                # Merge local and federation appis metrics
                federation_appis_metrics = copy.deepcopy(self.federation_appis_metrics)
                for appi_id, appi in federation_appis_metrics.items():
                    for kdu_id, kdu in appi.items():
                        app_metrics.setdefault(appi_id, {})[kdu_id] = kdu

                message = {
                    "appis": app_metrics,
                    "nodeSpecs": {**nodes_specs, **self.federation_node_specs}, # Merge local and federation node specs
                }

                # Send metrics to Kafka
                KafkaUtils.send_message(self.producer, self.meh_metrics_topic, message)
                logging.info(f"Sent message to Kafka topic {self.meh_metrics_topic}: {message}")

                time.sleep(self.send_cluster_metrics_freq)

            except Exception as e:
                logging.info(f"INFO: Exception while sending cluster metrics: {e}")
                continue
