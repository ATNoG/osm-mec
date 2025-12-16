from src.utils.exceptions import handle_exceptions
import threading
import re
from src.utils.general import bytes_to_mb, updateDict
import logging

@handle_exceptions
def callback(meao, message):
    """
    Processes raw metrics related to each node and container
    """

    # TODO: Redo this. Due to current Federator implementation, I do not have a direct mapping between the appi and the migrated appi. Since we are using a low quantity of appis, this is acceptable for now.
    appis = message.get("appis", {})
    corrected_appis = {}
    for appi_id, appi in appis.items():
        for all_appis_id, all_appis_appi in meao.appis.items():
            for domain, domain_instances in all_appis_appi.get("instances", {}).items():
                for instance_id, instance in domain_instances.items():
                    if instance.get("appi_id") == appi_id:
                        corrected_appis[all_appis_id] = appi
    updateDict(meao.federation_appis_metrics, corrected_appis)
    
    node_specs = message.get("nodeSpecs", {})
    updateDict(meao.federation_node_specs, node_specs)
