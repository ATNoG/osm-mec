from flask import Flask, jsonify, request
from src.meao import MEAO

app = Flask(__name__)

@app.route("/mecApps", methods=["GET"])
def get_mec_apps():
    return jsonify(MecApps=meao.get_mec_apps())

@app.route("/appis", methods=["GET"])
def get_mec_apps_instances():
    return jsonify(Appis=meao.get_mec_apps_instances())

@app.route("/InfrastructureInfo", methods=["GET"])
def get_infrastructure_info():
    return jsonify(ClusterInfo=meao.get_infrastructure_info())

def run(meao_: MEAO, host="0.0.0.0", port=8000):
    global meao
    meao = meao_
    app.run(host=host, port=port)

if __name__ == "__main__":
    run()
