from flask import Flask, jsonify, request
from src.meao import MEAO

app = Flask(__name__)

@app.route("/appis/<appi_id>/disable", methods=["POST"])
def disable_kdu(appi_id):
    data = request.get_json()

    ns_id = "230e6007-0780-497c-9ba1-fee825c4af1a"  # TODO: For now this is manually set as I do not expect to use this endpoint in the future and is only for testing purposes

    try:
        result = meao.disable_kdu(appi_id, ns_id, data)
    except Exception as e:
        return jsonify({"status": 500, "error": str(e)}), 500
    
    if "error" in result:
        return jsonify(result), 404
    else:
        return jsonify(result), 200

@app.route("/appis/<appi_id>/enable", methods=["POST"])
def enable_kdu(appi_id):
    data = request.get_json()

    ns_id = "230e6007-0780-497c-9ba1-fee825c4af1a"  # TODO: For now this is manually set as I do not expect to use this endpoint in the future and is only for testing purposes

    try:
        result = meao.enable_kdu(appi_id, data)
    except Exception as e:
        return jsonify({"status": 500, "error": str(e)}), 500
    
    if "error" in result:
        return jsonify(result), 404
    else:
        return jsonify(result), 200

@app.route("/appis/<appi_id>/artifacts/<artifact_id>/migrate/", methods=["POST"])
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
