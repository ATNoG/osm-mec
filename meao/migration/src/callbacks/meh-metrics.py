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
                available_cpu = max(0, specs["num_cpu_cores"] - max(specs["allocated-cpu"], specs.get("cpuUsage", 0)))
                available_mem = max(0, specs["memory_size"] - max(specs["allocated-mem"], specs.get("memUsage", 0)))
                message["nodeSpecs"][cluster]["nodeSpecs"][node]["available-cpu"] = available_cpu
                message["nodeSpecs"][cluster]["nodeSpecs"][node]["available-mem"] = available_mem
        meao.nodeSpecs = message["nodeSpecs"]

    except RuntimeError as e:
        logging.info(f"Exception while processing kafka messages: {e}")
