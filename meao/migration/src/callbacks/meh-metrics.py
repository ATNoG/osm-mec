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
                # if cpuUsage (or mem) is present, it will have the total sum, so it will be selected. If not, appis-*usage is used
                available_cpu = max(0, specs["num_cpu_cores"] - max(specs.get("appis-cpuUsage", 0), specs.get("allocated-cpu", 0), specs.get("cpuUsage", 0)))
                available_mem = max(0, specs["memory_size"] - max(specs.get("appis-memUsage", 0), specs.get("allocated-mem", 0), specs.get("memUsage", 0)))
                message["nodeSpecs"][cluster]["nodeSpecs"][node]["available-cpu"] = available_cpu
                message["nodeSpecs"][cluster]["nodeSpecs"][node]["available-mem"] = available_mem
        meao.nodeSpecs = message["nodeSpecs"]

    except RuntimeError as e:
        logging.info(f"Exception while processing kafka messages: {e}")
