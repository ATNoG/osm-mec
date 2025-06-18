from src.utils.exceptions import handle_exceptions
from src.utils.general import updateDict

@handle_exceptions
def callback(meao, message):
    """
    !!! THREAD !!! 
    
    update_appis:
        thread for collecting and processing MEC Application information received from the OSS
        updates the nodeSpecs and containerInfo
    """

    try:
        # TODO: The following code is purely a temporary solution to keep the work before integrating with the actual federation management system.
        # ======================================================================================
        message = {
            "appis":{
                "app1": {
                    "domain": "domain1",
                    "instances":{
                        '7ff4f465-da73-4f0d-9023-7ad1f7c87d60': {
                            "ns_id": '3122b1c3-660c-4005-9f54-b3ca6fe9614b',
                            "vnf_id": '9f563e38-f657-4247-98cc-6d21fb819452',
                            "kdus": {
                                'object-detection': 'k3s-ns-k3s-through-ansible-vnf-worker-0-79783e18',
                                'object-detection-2': 'k3s-ns-k3s-through-ansible-vnf-worker-0-79783e18',
                                'object-detection-4': 'k3s-ns-k3s-through-ansible-vnf-controller-0-f805b397',
                                'object-detection-5': 'k3s-ns-k3s-through-ansible-vnf-controller-0-f805b397'
                            }
                        },
                        '4135491a-b6c9-4c75-83f7-4379cff76a70': {
                            "ns_id": '6ef37f74-0016-4bf6-aaf9-b4984df32590',
                            "vnf_id": '8e5e18c6-31c0-4384-8162-bc97b249e475',
                            "kdus": {
                                'object-detection-3': 'osm-mec-node-0-03254c31'
                            }
                        }
                    }
                },
                "app2": {
                    "domain": "domain2",
                    "instances":{
                        '7ff4f465-da73-4f0d-9023-7ad1f7c8ssss': {
                            "ns_id": '3122b1c3-660c-4005-9f54-b3ca6fe9ssss',
                            "vnf_id": '9f563e38-f657-4247-98cc-6d21fb819452',
                            "kdus": {
                                'object-detection': 'k3s-ns-k3s-through-ansible-vnf-worker-0-79783e18',
                                'object-detection-2': 'k3s-ns-k3s-through-ansible-vnf-worker-0-79783e18',
                                'object-detection-4': 'k3s-ns-k3s-through-ansible-vnf-controller-0-f805b397',
                                'object-detection-5': 'k3s-ns-k3s-through-ansible-vnf-controller-0-f805b397'
                            }
                        },
                        '4135491a-b6c9-4c75-83f7-4379cffssss': {
                            "ns_id": '6ef37f74-0016-4bf6-aaf9-b4984df3ssss',
                            "vnf_id": '8e5e18c6-31c0-4384-8162-bc97b249e475',
                            "kdus": {
                                'object-detection-3': 'osm-mec-node-0-03254c31'
                            }
                        }
                    }
                },
            },
            "msg_id": "teste"
        }
        # ======================================================================================

        # Update the MEC Apps Instances
        message.pop("msg_id", None)
        meao.federation_appis.update(message.get("appis", {}))
        print("New Federation Appis:", meao.federation_appis)

        # Get the containers information to be able to monitor them
        container_to_app = meao.nbi_k8s_connector.get_federation_container_info(meao.federation_appis)
        print("Container to App mapping:", container_to_app)

        # Update the container to app mapping and the current metrics
        meao.federation_container_to_app = updateDict(meao.federation_container_to_app, container_to_app)

        print("New Federation Container to App mapping:", meao.federation_container_to_app)
        
    except RuntimeError as e:
        print("INFO: Exception while processing kafka messages: ", e)
