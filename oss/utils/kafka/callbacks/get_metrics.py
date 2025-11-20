from ...threads.websocket_service_thread import metrics_queue
import logging

def callback(data):
    try:
        data.pop("msg_id", None)  # Remove msg_id if present

        apps_metrics = {}
        for appi, appi_data in data["appis"].items():
            apps_metrics.setdefault(appi, {"artifacts": {}, "metrics": {}})

            apps_metrics[appi]["metrics"] = {
                "cpu-load": appi_data.get("metrics", {}).get("cpuLoad", 0),
                "mem-load": appi_data.get("metrics", {}).get("memLoad", 0),
            }
            
            for artifact_name, artifact_data in appi_data.items():
                apps_metrics[appi]["artifacts"].setdefault(artifact_name, {"metrics": {}})

                apps_metrics[appi]["artifacts"][artifact_name]["metrics"] = {
                    "cpu-load": artifact_data.get("metrics", {}).get("cpuLoad", 0),
                    "mem-load": artifact_data.get("metrics", {}).get("memLoad", 0),
                }

        nodes_metrics = {}
        for cluster, cluster_data in data["nodeSpecs"].items():
            domain = cluster_data.get("domain", None)

            for node_name, node_data in cluster_data.get("nodeSpecs", {}).items():
                nodes_metrics.setdefault(f"{domain}-{cluster}-{node_name}", {
                    "domain": domain,
                    "cluster": cluster,
                    "node": node_name,
                    "metrics": {
                        "cpu-load": (node_data.get('cpuUsage', 0) + (max(node_data.get('allocated-cpu', 0) - node_data.get("appis-cpuLoad", 0), 0) ) / node_data.get('num_cpu_cores', 0)) * 100,
                        "mem-load": (node_data.get("memUsage", 0) + (max(node_data.get("allocated-mem", 0) - node_data.get("appis-memLoad", 0), 0)) / node_data.get("memory_size", 0)) * 100,
                    }
                })
            
        metrics_queue.put({
            "appis": apps_metrics,
            "nodes": nodes_metrics
        })
    except Exception as e:
        logging.error(f"Error in get_metrics callback: {e}")
