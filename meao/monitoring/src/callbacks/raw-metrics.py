from src.utils.exceptions import handle_exceptions
import threading
import re

@handle_exceptions
def callback(meao, message):
    """
    Processes raw metrics related to each node and container
    """
    
    # process the message
    cName = message["container_Name"]

    # if the received information is related to a node
    if cName == "/":
        # obtain the name of the associated cadvisor pod
        machine_name = message["machine_name"]
        
        # ensure nodeSpecs contains information relating to this node
        node = next(((cluster_id, node_id) for cluster_id, cluster in meao.node_specs.items() for node_id, nodeInfo in cluster["nodeSpecs"].items() if machine_name == nodeInfo["cadvisor"]), None)

        # if the node is found, update the metrics information
        if node:
            threading.Thread(target=update_meh_metrics, args=(meao, node, message)).start()
        return
    
    container = re.search(r'cri-containerd-([a-f0-9]+)\.scope', cName)
    if container and container.group(1) in meao.container_to_app:
        threading.Thread(target=update_meh_metrics, args=(meao, container.group(1), message, meao.container_to_app[container.group(1)], True)).start()


def update_meh_metrics(meao, cName, values, container=None, silent=True):
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
        memory_size = (meao.node_specs[container["cluster_id"]]["nodeSpecs"][container["node"]]["memory_size"]*pow(1024,3))
        num_cpu_cores = meao.node_specs[container["cluster_id"]]["nodeSpecs"][container["node"]]["num_cpu_cores"]
    else:
        memory_size = (meao.node_specs[cName[0]]['nodeSpecs'][cName[1]]["memory_size"]*pow(1024,3))
        num_cpu_cores = meao.node_specs[cName[0]]['nodeSpecs'][cName[1]]["num_cpu_cores"]

    # CPU load corresponds to the amount of time that was spent executing tasks over a certain time period
    # this can be obtained by calculating the ratio of CPU time delta over the system time delta

    # the current timestamp corresponds to the current system time
    timestampParts = values["timestamp"].split(':')
    timestamp = (float(timestampParts[-3][-2:])*pow(60,2) + float(timestampParts[-2])*60 + float(timestampParts[-1][:-1])) * pow(10, 9)
    # the cpu usage value corresponds to the current CPU time
    current_cpu = values["container_stats"]["cpu"]["usage"]["total"]
    if cName not in meao.prev_cpu.keys():
        meao.prev_cpu[cName] = {}
        meao.prev_cpu[cName]["previousCPU"] = 0
        meao.prev_cpu[cName]["previousSystem"] = 0

    # Get the CPU usage and time
    cpu_usage = current_cpu - meao.prev_cpu[cName]["previousCPU"]
    elapsed_time = timestamp - meao.prev_cpu[cName]["previousSystem"]

    # calculate the ratio of the CPU time delta over the system time delta compared to the number of cores of the node
    cpuLoad = 0
    if elapsed_time > 0.0 and cpu_usage >= 0.0:
        cpuLoad = min(round(((cpu_usage / elapsed_time) / num_cpu_cores) * 100, 2), 100)

    # store the current times in the prev_cpu dictionary for future iterations of this function
    meao.prev_cpu[cName]["previousCPU"] = current_cpu
    meao.prev_cpu[cName]["previousSystem"] = timestamp

    # memory load corresponds to the amount of memory used compared to the total memory of the node
    memUsage = values["container_stats"]["memory"]["working_set"]
    memLoad = min(round((memUsage/memory_size) * 100, 2), 100)
    
    if container:
        meao.current_metrics[container["appi_id"]][container["kdu"]]["pods"][container["pod"]]["containers"][cName]["metrics"]["cpuUsage"] = min(round((cpu_usage / elapsed_time), 2), num_cpu_cores)
        meao.current_metrics[container["appi_id"]][container["kdu"]]["pods"][container["pod"]]["containers"][cName]["metrics"]["cpuLoad"] = cpuLoad
        meao.current_metrics[container["appi_id"]][container["kdu"]]["pods"][container["pod"]]["containers"][cName]["metrics"]["memUsage"] = round(memUsage / (1024 * 1024), 2)
        meao.current_metrics[container["appi_id"]][container["kdu"]]["pods"][container["pod"]]["containers"][cName]["metrics"]["memLoad"] = memLoad
    else:
        meao.node_specs[cName[0]]['nodeSpecs'][cName[1]]["cpuUsage"] = min(round((cpu_usage / elapsed_time), 2), num_cpu_cores)
        meao.node_specs[cName[0]]['nodeSpecs'][cName[1]]["cpuLoad"] = cpuLoad
        meao.node_specs[cName[0]]['nodeSpecs'][cName[1]]["memUsage"] = round(memUsage / (1024 * 1024), 2)
        meao.node_specs[cName[0]]['nodeSpecs'][cName[1]]["memLoad"] = memLoad
        
    
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
