from ...threads.websocket_service_thread import metrics_queue

def callback(data):
    apps_metrics = {}
    for container_id, container in data["containerInfo"].items():
        app_id = container["ns_id"]
        if app_id not in apps_metrics:
            apps_metrics[app_id] = {}
        apps_metrics[app_id][container_id] = {
            "mem_load": container.get("memLoad", None),
            "cpu_load": container.get("cpuLoad", None),
            "node": container.get("node", None),
            "latency": container.get("lat", None),
            "kdu_id": container.get("kdu_id", None),
            "warning": container.get("warning", None),
        }
        
    metrics_queue.put(apps_metrics)
