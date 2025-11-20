from src.utils.exceptions import handle_exceptions
import logging

@handle_exceptions
def callback(meao, message):
    """
    !!! THREAD !!!
    
    update_current_metrics:
        thread for collecting and processing current metrics information received from the MEAO Monitoring Service
    """

    try:
        meao.current_metrics = message["appis"]
        # Update the nodes with the available CPU and memory
        for cluster in message["nodeSpecs"]:
            for node, specs in message["nodeSpecs"][cluster]["nodeSpecs"].items():
                available_cpu = specs["num_cpu_cores"] - specs["allocated-cpu"] - (specs.get("cpuUsage", 0) - specs.get("appis-cpuUsage", 0))
                available_mem = specs["memory_size"] - specs["allocated-mem"] - (specs.get("memUsage", 0) - specs.get("appis-memUsage", 0))
                message["nodeSpecs"][cluster]["nodeSpecs"][node]["available-cpu"] = available_cpu
                message["nodeSpecs"][cluster]["nodeSpecs"][node]["available-mem"] = available_mem
        meao.nodeSpecs = message["nodeSpecs"]

    except RuntimeError as e:
        logging.info(f"Exception while processing kafka messages: {e}")
