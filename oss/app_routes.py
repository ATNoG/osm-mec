import cherrypy
from controllers import load_controllers

controllers = load_controllers()

# {prefix: [(function_name, route, controller, method),...]}
endpoints = {
    "/oss/v1": [
        # APP PACKAGES
        (
            "list_app_pkgs",
            "/app_pkgs",
            "AppPkgController",
            "GET",
        ),
        (
            "get_app_pkg",
            "/app_pkgs/{app_pkg_id}",
            "AppPkgController",
            "GET",
        ),
        (
            "new_app_pkg",
            "/app_pkgs",
            "AppPkgController",
            "POST",
        ),
        (
            "update_app_pkg",
            "/app_pkgs/{app_pkg_id}",
            "AppPkgController",
            "PATCH",
        ),
        (
            "delete_app_pkg",
            "/app_pkgs/{app_pkg_id}",
            "AppPkgController",
            "POST",
        ),
        (
            "instantiate_app_pkg",
            "/app_pkgs/{app_pkg_id}/instantiate",
            "AppPkgController",
            "POST",
        ),
        # APP INSTANCES
        (
            "list_appis",
            "/appis",
            "AppiController",
            "GET",
        ),
        (
            "get_appi",
            "/appis/{appi_id}",
            "AppiController",
            "GET",
        ),
        (
            "list_mec_appis",
            "/mec-appis",
            "AppiController",
            "GET",
        ),
        (
            "get_mec_appi",
            "/mec-appis/{appi_id}",
            "AppiController",
            "GET",
        ),
        (
            "terminate_appi",
            "/appis/{appi_id}",
            "AppiController",
            "POST",
        ),
        # VIM
        (
            "list_vims",
            "/vims",
            "VimController",
            "GET",
        ),
        # FEDERATION
        (
            "new_federation",
            "/federations",
            "FederationController",
            "POST",
        ),
        (
            "get_federation",
            "/federations/{federation_id}",
            "FederationController",
            "GET",
        ),
        (
            "list_federations",
            "/federations",
            "FederationController",
            "GET",
        ),
        (
            "delete_federation",
            "/federations/{federation_id}",
            "FederationController",
            "DELETE",
        ),
    ],
}


def set_routes():
    dispatcher = cherrypy.dispatch.RoutesDispatcher()

    for prefix, routes_info in endpoints.items():
        for route_info in routes_info:
            dispatcher.connect(
                name=route_info[0],
                route=prefix + route_info[1],
                action=route_info[0],
                controller=controllers[route_info[2]](),
                conditions={"method": [route_info[3]]},
            )

    return dispatcher
