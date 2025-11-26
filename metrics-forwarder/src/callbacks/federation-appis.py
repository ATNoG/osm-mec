from src.utils.exceptions import handle_exceptions

@handle_exceptions
def callback(forwarder, message):
    """
    Processes the container to app mapping information received from the Kafka topic.
    """

    message.pop("msg_id", None)

    # Make a Domain-Appi mapping
    federated_domains_appis = {}
    appis = message.get("appis", {})
    for appi_id, appi in appis.items():
        federated_domains_appis.setdefault(appi["domain"], {})[appi_id] = []
        for cluster in appi["instances"].values():
            federated_domains_appis[appi["domain"]][appi_id].extend(cluster["kdus"].keys())
    
    forwarder.federated_domains_appis = federated_domains_appis
    