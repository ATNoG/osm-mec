from src.utils.exceptions import handle_exceptions

@handle_exceptions
def callback(forwarder, message):
    """
    Processes the container to app mapping information received from the Kafka topic.
    """
    forwarder.federation_container_to_app = message.get("containers", {})
    print("New Federation Container to App mapping:", forwarder.federation_container_to_app)
    