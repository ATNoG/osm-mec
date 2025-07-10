from src.utils.exceptions import handle_exceptions
from src.utils.db import DB

# This callback should only be called by the federator
@handle_exceptions
def callback(meao, message):
    # Get the data from the message
    mec_appd_id = message.get("mec_appd_id", None)
    kdu_id = message.get("kdu_id", None)
    ns_id = message.get("ns_id", None)

    # Validate the required fields
    if not mec_appd_id or not kdu_id or not ns_id:
        raise ValueError("Missing required fields in the message: mec_appd_id, kdu_id, ns_id")

    # Get the resources for the kdu
    mec_app = next((mec_app for mec_app in meao.mec_apps.values() if mec_app["appd_id"] == mec_appd_id), None)
    kdu_resources = mec_app.get("migration_policy", {}).get(kdu_id, {})

    # Get the kdu instance details
    ns_instance = meao.nbi_k8s_connector.callNBI(
        meao.nbi_k8s_connector.nbi_client.ns.get,
        ns_id
    )
    kdu_instance = next(kdu for kdu in ns_instance["_admin"]["deployed"]["K8s"] if kdu["kdu-name"] == kdu_id)
    cluster = kdu_instance["k8scluster-uuid"]
    node = kdu_instance["node-selector"]["kubernetes.io/hostname"]

    # Update the resources in the database
    DB._general_update_by("resources", {"cluster": cluster, "node": node}, {"$inc": {"allocated-cpu": -kdu_resources.get("cpu-criteria", {}).get("allocated-cpu", 0), "allocated-mem": -kdu_resources.get("mem-criteria", {}).get("allocated-mem", 0)}})

    # Enable the kdu in the expected node
    meao.nbi_k8s_connector.disable_kdu(mec_appd_id, ns_id, [kdu_id])

    return {
        "status": 200,
        "message": f"KDU {kdu_id} disabled successfully in MEC AppD {mec_appd_id} for NS {ns_id}"
    }
