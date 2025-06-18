from src.utils.appd_validation import *
from src.utils.db import DB
from src.utils.exceptions import handle_exceptions
from src.utils.file_management import *
from src.utils.osm import get_osm_client

@handle_exceptions
def callback(meao, message):
    appi_id = message.get("appi_id")
    wait = message.get("wait")

    if appi_id:
        appi = meao.appis.get(appi_id, None)
        if not appi:
            return {"status": 404, "error": "App instance not found"}
        
        network_services = get_all_ns(appi)
        released_resources = get_appi_resources(appi)
        for domain, ns_id in sorted(network_services, key=lambda x: (x[0] != meao.domain, x)):
            if domain == meao.domain:
                meao.nbi_k8s_connector.delete_network_service(ns_id, wait=wait)
            # else:
            #     print(f"TODO: Cannot delete network service {ns_id} in domain {domain}. Multiple Domain deletion Not Implemented yet.")

        # Update the nodes allocated resources in the database
        for (cluster, node), resources in released_resources.items():
            DB._general_update_by("resources", {"cluster": cluster, "node": node}, {"$inc": resources})
        
        DB._delete_by("appis", filter={"appi_id": appi_id})
        return {"status": 204}
    
    return {"status": 404, "error": "Error terminating the app instance"}


def get_all_ns(appi: dict):
    """
    Join the data by domain and cluster to create the network services structure.
    """
    instances = set( (domain, appi["instances"][domain][cluster]["ns_id"]) for domain in appi["instances"] for cluster in appi["instances"][domain] )
    return instances            

def get_appi_resources(appi: dict):
    """
    Get the resources of the app instance.
    """
    resources = {}
    for domain in appi["instances"]:
        if domain == appi["domain"]:
            for cluster in appi["instances"][domain]:
                for kdu, node in appi["instances"][domain][cluster]["kdus"].items():
                    if kdu in appi["migration_policy"]:
                        resources[(cluster, node)] = {
                            "allocated-cpu": -appi["migration_policy"].get(kdu, {}).get("cpu-criteria", {}).get("allocated-cpu", 0),
                            "allocated-mem": -appi["migration_policy"].get(kdu, {}).get("mem-criteria", {}).get("allocated-mem", 0),
                        }
    return resources
