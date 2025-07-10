from src.utils.appd_validation import *
from src.utils.db import DB
from src.utils.kafka.kafka_utils import KafkaUtils
from src.utils.exceptions import handle_exceptions
from src.utils.file_management import *
from src.utils.osm import get_osm_client

@handle_exceptions
def callback(meao, message):
    appi_id = message.get("appi_id")
    wait = message.get("wait")
    msg_id = message.get("msg_id", None)

    if appi_id:
        appi = meao.appis.get(appi_id, None)
        if not appi:
            return {"status": 404, "error": "App instance not found"}
        
        network_services = get_all_ns(appi)
        released_resources = get_appi_resources(appi)
        for domain, instance in sorted(network_services, key=lambda x: (x[0] != meao.domain, x)):
            if domain == meao.domain:
                meao.nbi_k8s_connector.delete_network_service(instance[1], wait=wait)
                for resources in released_resources.get((domain, instance[1]), []):
                    DB._general_update_by("resources", {"cluster": resources["cluster"], "node": resources["node"]}, {"$inc": {"allocated-cpu": resources["allocated-cpu"], "allocated-mem": resources["allocated-mem"]}})
            else:
                msg_id = KafkaUtils.send_message(
                    meao.producer,
                    "federation_remove_appi",
                    {
                        "federation_context_id": meao.federations_context_id.get(domain),
                        "app_instance_id": instance[0],
                    }
                )
        
        DB._delete_by("appis", filter={"appi_id": appi_id})
        return {"status": 204, "msg_id": msg_id}
    
    return {"status": 404, "error": "Error terminating the app instance"}


def get_all_ns(appi: dict):
    """
    Join the data by domain and cluster to create the network services structure.
    """
    
    instances = set( (domain, (appi["instances"][domain][cluster].get("appi_id", None), appi["instances"][domain][cluster]["ns_id"])) for domain in appi["instances"] for cluster in appi["instances"][domain] )
    return instances

def get_appi_resources(appi: dict):
    """
    Get the resources of the app instance.
    """
    
    resources = {}
    for domain in appi["instances"]:
        for cluster in appi["instances"][domain]:
            ns_id = appi["instances"][domain][cluster]["ns_id"]
            resources[(domain, ns_id)] = []
            for kdu, node in appi["instances"][domain][cluster]["kdus"].items():
                if kdu in appi["migration_policy"]:
                    resources[(domain, ns_id)].append({
                        "cluster": cluster,
                        "node": node,
                        "allocated-cpu": -appi["migration_policy"].get(kdu, {}).get("cpu-criteria", {}).get("allocated-cpu", 0),
                        "allocated-mem": -appi["migration_policy"].get(kdu, {}).get("mem-criteria", {}).get("allocated-mem", 0),
                    })
    return resources
