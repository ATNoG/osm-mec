from src.utils.exceptions import handle_exceptions
from src.utils.db import DB
import time

# This callback should only be called by the federator
@handle_exceptions
def callback(meao, message):
    # Get the data from the message
    mec_appd_id = message.get("mec_appd_id", None)
    ns_id = message.get("ns_id", None)
    vnf_id = message.get("vnf_id", None)
    kdu_id = message.get("kdu_id", None)
    node = message.get("node", None)

    # Validate the required fields
    if not ns_id or not vnf_id or not kdu_id or not node:
        raise ValueError("Missing required fields in the message: ns_id, vnf_id, kdu_id, node")

    # Get the mec_app instance from the meao
    mec_app = next((mec_app for mec_app in meao.mec_apps.values() if mec_app["appd_id"] == mec_appd_id), None)

    # Get the kdu instance of the kdu_id from the ns instance
    ns_instance = meao.nbi_k8s_connector.callNBI(meao.nbi_k8s_connector.nbi_client.ns.get, ns_id)
    kdu_instance_index, kdu_instance = next((index, kdu) for index, kdu in enumerate(ns_instance["_admin"]["deployed"]["K8s"]) if kdu["kdu-name"] == kdu_id and kdu["member-vnf-index"] == str(mec_app["appd_id"] + "-vnf"))

    if not kdu_instance:
        return {"status": 404, "error": "KDU Instance {} not found".format(kdu_id)}
    
    # Get info about the nodes and resources
    cluster = kdu_instance["k8scluster-uuid"]
    old_node = kdu_instance["node-selector"]["kubernetes.io/hostname"]

    # Get the resources for the kdu
    kdu_resources = mec_app.get("migration_policy", {}).get(kdu_id, {})

    # increment the resources in the database for the new node
    DB._general_update_by("resources", {"cluster": cluster, "node": node}, {"$inc": {"allocated-cpu": kdu_resources.get("cpu-criteria", {}).get("allocated-cpu", 0), "allocated-mem": kdu_resources.get("mem-criteria", {}).get("allocated-mem", 0)}})

    # Enable the kdu in the expected node
    meao.nbi_k8s_connector.migrate(ns_id, vnf_id, kdu_instance["kdu-instance"], kdu_instance_index, node)

    # Wait for the kdu to be migrated
    while True:
        ns_instance = meao.nbi_k8s_connector.callNBI(meao.nbi_k8s_connector.nbi_client.ns.get, ns_id)
        kdu_instance = next(kdu for kdu in ns_instance["_admin"]["deployed"]["K8s"] if kdu["kdu-name"] == kdu_id)
        if kdu_instance["enable"] and kdu_instance["operation"] == "upgrade" and kdu_instance["status"] == "Upgrade complete" and kdu_instance["node-selector"]["kubernetes.io/hostname"] == node:
            break
        time.sleep(0.01)  # Sleep for 0.01 seconds to avoid busy waiting
    
    # Update the resources in the database for the old node
    DB._general_update_by("resources", {"cluster": cluster, "node": old_node}, {"$inc": {"allocated-cpu": -kdu_resources.get("cpu-criteria", {}).get("allocated-cpu", 0), "allocated-mem": -kdu_resources.get("mem-criteria", {}).get("allocated-mem", 0)}})

    return {
        "status": 200,
        "message": f"Network Service with ID {ns_id} migrated successfully."
    }
