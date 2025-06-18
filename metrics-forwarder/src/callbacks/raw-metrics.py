from src.utils.exceptions import handle_exceptions
import re
from src.utils.kafka.kafka_utils import KafkaUtils

@handle_exceptions
def callback(forwarder, message):
    """
    Processes raw metrics related to each node and container
    """
    
    # process the message
    container_name = message["container_Name"]

    # if the received information is related to a node it needs to be the meao to deal with it
    if container_name == "/":
        return
    
    # Get the container ID from the container name
    match = re.search(r'cri-containerd-([a-f0-9]+)\.scope', container_name)
    if match:
        container_name = match.group(1)
        container = forwarder.federation_container_to_app.get(container_name, None)
    else:
        container = None
    
    # If the container is not found in the mapping, we do not need to process it
    if not container:
        return
    print("Container is part of a federation:", container)
    
    # Send the metrics information to the Domain's kafka for further processing
    producer = forwarder.producers.get(container["domain"], None)
    if not producer:
        print(f"Producer for domain {container['domain']} not found.")
        return
    
    print("Sending message to", container["domain"], ":", message)
    # KafkaUtils.send_message(
    #     producer,
    #     "raw-metrics",
    #     message
    # )
