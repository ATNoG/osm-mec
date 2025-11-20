from src.utils.exceptions import handle_exceptions
import logging

@handle_exceptions
def callback(meao, message):
    """
    !!! THREAD !!! 
    
    handle_response:
        thread for collecting and processing responses from the MEAO
    """
    
    try:
        msg_id = message.pop("msg_id", None)

        if msg_id not in meao.waiting_responses:
            return

        if meao.waiting_responses[msg_id].get("type", "") == "migration":
            # Get the waiting response data
            appi_id, kdu_id = meao.waiting_responses[msg_id]["app"]
            from_node = meao.waiting_responses[msg_id]["from"]

            # Remove from the response waiting list
            meao.migrating_apps.discard((appi_id, kdu_id))
            meao.waiting_responses.pop(msg_id)

            # Remove the appi from the expected resource gains as it already completed the migration
            meao.expected_resource_gains[(from_node["domain"], from_node["cluster"], from_node["node"])]["cpu"] -= meao.waiting_responses[msg_id]["expected_gain"]["cpu"]
            meao.expected_resource_gains[(from_node["domain"], from_node["cluster"], from_node["node"])]["mem"] -= meao.waiting_responses[msg_id]["expected_gain"]["mem"]

            # Handle the response
            if message["status"] == 200:
                logging.info(f"Migration completed successfully: {message['message']}")
            else:
                logging.error(f"Migration failed with error: {message['error']}")

    except RuntimeError as e:
        logging.error(f"Exception while processing kafka messages: {e}")
