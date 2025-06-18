from flask import Flask, jsonify, request
from src.meao import MEAO
from src.utils.kafka.kafka_utils import KafkaUtils

app = Flask(__name__)

@app.route("/disable_kdu", methods=["POST"])
def disable_kdu():
    # Get the data from the request
    if request.is_json:
        data = request.get_json(silent=True)
    else:
        data = request.form.to_dict()
    
    mec_appd_id = data.get("mec_appd_id", None)
    kdu_id = data.get("kdu_id", None)
    ns_id = data.get("ns_id", None)

    try:
        KafkaUtils.send_message(
            producer=meao.producer,
            topic="disable_kdu",
            message={"mec_appd_id": mec_appd_id, "kdu_id": kdu_id, "ns_id": ns_id}
        )
    except Exception as e:
        return jsonify({"status": 500, "error": str(e)}), 500
    

@app.route("/enable_kdu", methods=["POST"])
def enable_kdu():
    # Get the data from the request
    if request.is_json:
        data = request.get_json(silent=True)
    else:
        data = request.form.to_dict()
    
    mec_appd_id = data.get("mec_appd_id", None)
    artifact_id = data.get("kdu_id", None)
    ns_id = data.get("ns_id", None)
    node = data.get("node", None)

    try:
        KafkaUtils.send_message(
            producer=meao.producer,
            topic="enable_kdu",
            message={"mec_appd_id": mec_appd_id, "kdu_id": artifact_id, "ns_id": ns_id, "node": node}
        )
    except Exception as e:
        return jsonify({"status": 500, "error": str(e)}), 500
    

@app.route("/appis/<appi_id>/artifacts/<artifact_id>/migrate", methods=["POST"])
def migrate_container(appi_id, artifact_id):
    try:
        
        # Get the data from the request
        if request.is_json:
            data = request.get_json(silent=True)
        else:
            data = request.form.to_dict()
        
        if not data:
            return {"error": "No data provided"}, 400
        
        domain = data.get("domain", None)
        if not domain:
            return {"error": "No domain provided"}, 400
        
        cluster_id = data.get("cluster", None)
        if not cluster_id:
            return {"error": "No cluster ID provided"}, 400

        finalTargetNode = data.get("finalTargetNode", None)
        if not finalTargetNode:
            return {"error": "No final target node provided"}, 400
        
        status= meao.migrate(appi_id, artifact_id, domain, cluster_id, finalTargetNode)

        if status:
            return {"message": "Migrating container", "appi_id": appi_id, "artifact_id": artifact_id, "domain": domain, "cluster": cluster_id, "node": finalTargetNode}, 200
        
        return {"error": "Artifact is already being migrated"}, 500
    
    except Exception as e:
        return {"Message": "Error: {}".format(e)}, 500

def run(meao_: MEAO, host="0.0.0.0", port=8002):
    global meao
    meao = meao_
    app.run(host=host, port=port)

if __name__ == "__main__":
    run()
