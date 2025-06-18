from src.utils.exceptions import handle_exceptions

@handle_exceptions
def callback(meao, message):
    print("Callback for enabling KDU called with message:", message)
    # Get the data from the message
    mec_appd_id = message.get("mec_appd_id", None)
    kdu_id = message.get("kdu_id", None)
    ns_id = message.get("ns_id", None)
    node = message.get("node", None)

    # Validate the required fields
    if not mec_appd_id or not kdu_id or not ns_id or not node:
        raise ValueError("Missing required fields in the message: mec_appd_id, kdu_id, ns_id, node")

    # Enable the kdu in the expected node
    meao.nbi_k8s_connector.enable_kdu(mec_appd_id, ns_id, [kdu_id], node)

    # wait for the new kdu to be running
    meao.nbi_k8s_connector.wait_for_kdu_enable(ns_id, kdu_id)

    return {
        "status": "success",
        "message": f"KDU {kdu_id} enabled successfully in MEC AppD {mec_appd_id} for NS {ns_id} on node {node}"
    }
