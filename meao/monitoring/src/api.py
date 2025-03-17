from main import app, meao

@app.route("/containerInfo", methods=["GET"])
def get_container_info():
    return jsonify(ContainerInfo=meao.get_container_ids())


@app.route("/nodeSpecs", methods=["GET"])
def get_node_specs():
    return jsonify(NodeSpecs=meao.get_node_specs())


@app.route("/nodeSpecs/<hostname>", methods=["GET"])
def get_node_specs_hostname(hostname):
    return jsonify(NodeSpecs=meao.get_node_specs(hostname))


@app.route("/nodeSpecs/update", methods=["GET"])
def update_node_specs():
    meao.update_node_specs()
    return jsonify(NodeSpecs=meao.get_node_specs())
