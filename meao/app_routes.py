import cherrypy
from controllers import load_controllers

controllers = load_controllers()

# {prefix: [(name, route, action, controller, method),...]}
endpoints = {
    "/api/v1": [
        ("index_test", "/dummy", "index", "DummyController", "GET"),
        ("hello", "/dummy/hello/{name}", "hello", "DummyController", "GET"),
    ],
}


def set_routes():
    dispatcher = cherrypy.dispatch.RoutesDispatcher()

    for prefix, routes_info in endpoints.items():
        for route_info in routes_info:
            dispatcher.connect(
                name=route_info[0],
                route=prefix + route_info[1],
                action=route_info[2],
                controller=controllers[route_info[3]](),
                conditions={"method": [route_info[4]]},
            )

    return dispatcher
