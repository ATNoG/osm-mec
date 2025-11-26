from src.utils.exceptions import handle_exceptions
import re
import logging
from src.utils.kafka.kafka_utils import KafkaUtils

@handle_exceptions
def callback(forwarder, message):
    """
    !!! THREAD !!!
    
    update_current_metrics:
        thread for collecting and processing current metrics information received from the MEAO Monitoring Service
    """

    try:
        message.pop("msg_id", None)

        # Update the nodes with the available CPU and memory
        for cluster in message["nodeSpecs"]:
            for node, specs in message["nodeSpecs"][cluster]["nodeSpecs"].items():
                available_cpu = specs["num_cpu_cores"] - specs["allocated-cpu"] - (specs.get("cpuUsage", 0) - specs.get("appis-cpuUsage", 0))
                available_mem = specs["memory_size"] - specs["allocated-mem"] - (specs.get("memUsage", 0) - specs.get("appis-memUsage", 0))
                message["nodeSpecs"][cluster]["nodeSpecs"][node]["available-cpu"] = available_cpu
                message["nodeSpecs"][cluster]["nodeSpecs"][node]["available-mem"] = available_mem

        # For each federated domain, filter the appis metrics to only include those relevant to that domain
        filtered_appis_metrics = {}
        all_appis = message.pop("appis", {})
        for partner, producer in forwarder.producers.items():
            if not producer:
                logging.error(f"Producer for domain {partner} not found.")
                continue

            partner_appis = forwarder.federated_domains_appis.get(partner, {})
            for appi_id, kdus in partner_appis.items():
                for kdu_name in kdus:
                    if kdu_name in all_appis.get(appi_id, {}):
                        if forwarder.original_appi_ids.get(appi_id):
                            original_appi_id = forwarder.original_appi_ids.get(appi_id)
                            filtered_appis_metrics.setdefault(original_appi_id, {})[kdu_name] = all_appis[appi_id][kdu_name]
            
        # Send the current metrics information to the Domain's kafka for further processing
        message["appis"] = filtered_appis_metrics
        KafkaUtils.send_message(
            producer,
            "federation-meh-metrics",
            message
        )

    except RuntimeError as e:
        logging.error("Exception while processing kafka messages: ", e)

