from ...threads.mec_apps_thread import containers
from ...threads.websocket_service_thread import lat_queue


def callback(data):
    for container_id in containers.keys():
        temp_data = {
            "k3s-worker1-pedrocjdpereira": data["k3s-worker1-pedrocjdpereira"],
            "k3s-worker2-pedrocjdpereira": data["k3s-worker2-pedrocjdpereira"],
        }
        temp_data["node"] = containers[container_id]["node"]
        temp_data["appi_id"] = containers[container_id]["ns"]
        lat_queue.put(temp_data)