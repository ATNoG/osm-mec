from flask import Flask, jsonify
from src.meao import MEAO

app = Flask(__name__)

@app.route("/NodeSpecs", methods=["GET"])
def get_node_specs():
    return jsonify(NodeSpecs=meao.get_node_specs())

@app.route("/ContainerIds", methods=["GET"])
def get_container_info():
    return jsonify(ContainerIds=meao.get_container_ids())

def run(meao_: MEAO, host="0.0.0.0", port=8001):
    global meao
    meao = meao_
    app.run(host=host, port=port)

if __name__ == "__main__":
    run()
