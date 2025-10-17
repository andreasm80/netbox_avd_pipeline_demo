import grpc
import logging
import os
import time
from google.protobuf import wrappers_pb2 as wrappers

from arista.changecontrol.v1 import models as cc_models, services as cc_services

# Set your CloudVision details from your playbook as environment variables
CV_SERVER = os.environ.get("CVP_SERVER")
CV_TOKEN = os.environ.get("CVP_TOKEN")
CHANGE_CONTROL_NAME = os.environ.get("CHANGE_CONTROL_NAME")

logging.basicConfig(
    format='%(asctime)s - %(levelname)-8s - %(message)s',
    level=logging.INFO
)

def create_grpc_channel(server, token) -> grpc.Channel:
    """Creates a secure gRPC channel with token authentication."""
    call_creds = grpc.access_token_call_credentials(token)
    channel_creds = grpc.ssl_channel_credentials()
    conn_creds = grpc.composite_channel_credentials(channel_creds, call_creds)
    return grpc.secure_channel(server, conn_creds)

def find_change_control_by_name(channel: grpc.Channel, cc_name):
    """Searches for a Change Control by its name and returns its ID."""
    logging.info(f"Searching for Change Control with name '{cc_name}'")
    cc_stub = cc_services.ChangeControlServiceStub(channel)
    try:
        # We subscribe to the stream and wait for the CC with the matching name
        # This is a reliable way to get the latest state
        for resp in cc_stub.Subscribe(cc_services.ChangeControlStreamRequest()):
            if resp.value.change.name.value == cc_name:
                cc_id = resp.value.key.id.value
                logging.info(f"Found Change Control: {resp.value.change.name.value} with ID {cc_id}")
                return cc_id
    except grpc.RpcError as e:
        logging.error(f"gRPC Error while searching for CC by name: {e.details()}")
        return None
    
    return None

def subscribe_to_cc_status(channel: grpc.Channel, cc_id: str):
    """Subscribes to a Change Control and monitors it until completion."""
    logging.info(f"Subscribing to CC with ID {cc_id} to monitor for completion")
    key = cc_models.ChangeControlKey(id=wrappers.StringValue(value=cc_id))
    sub_req = cc_services.ChangeControlStreamRequest()
    sub_req.partial_eq_filter.append(cc_models.ChangeControl(key=key))

    max_retries = 5
    retry_delay = 5  # Initial delay in seconds

    for attempt in range(max_retries):
        try:
            cc_stub = cc_services.ChangeControlServiceStub(channel)
            for resp in cc_stub.Subscribe(sub_req):
                current_status = resp.value.status
                if current_status == cc_models.CHANGE_CONTROL_STATUS_UNSPECIFIED:
                    continue

                logging.info(f"Current status: {cc_models.ChangeControlStatus.Name(current_status)}")
                
                if current_status == cc_models.CHANGE_CONTROL_STATUS_COMPLETED:
                    if resp.value.error and resp.value.error.value:
                        err = resp.value.error.value
                        logging.info(f"Change Control completed with error: {err}")
                        return
                    else:
                        logging.info("Change Control completed successfully.")
                        return
                if current_status == cc_models.CHANGE_CONTROL_STATUS_FAILED:
                    logging.error(f"Change Control failed: {cc_models.ChangeControlStatus.Name(current_status)}")
                    return
                if current_status == cc_models.CHANGE_CONTROL_STATUS_ABANDONED:
                    logging.error(f"Change Control was abandoned: {cc_models.ChangeControlStatus.Name(current_status)}")
                    return
        except grpc.RpcError as e:
            if attempt < max_retries - 1:
                logging.warning(f"Stream error occurred. Attempt {attempt + 1} failed. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logging.error(f"Failed to subscribe after {max_retries} attempts.")
                logging.error(f"gRPC Error: {e.details()}")
                return

def main():
    """Main function to run the script."""
    if not all([CV_SERVER, CV_TOKEN, CHANGE_CONTROL_NAME]):
        logging.error("Required environment variables CVP_SERVER, CVP_TOKEN, and CHANGE_CONTROL_NAME are not set.")
        return

    # Backoff-and-retry logic for connection failures
    max_retries = 5
    retry_delay = 5  # Initial delay in seconds

    for attempt in range(max_retries):
        try:
            with create_grpc_channel(CV_SERVER, CV_TOKEN) as channel:
                cc_id = find_change_control_by_name(channel, CHANGE_CONTROL_NAME)
                if cc_id:
                    subscribe_to_cc_status(channel, cc_id)
                else:
                    logging.error("Could not find the Change Control to monitor.")
                return # Exit the function on success
        except grpc.RpcError as e:
            if attempt < max_retries - 1:
                logging.warning(f"Connection attempt {attempt + 1} failed. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logging.error(f"All {max_retries} connection attempts failed. Exiting.")
                logging.error(f"gRPC Error: {e.details()}")
                return

if __name__ == "__main__":
    main()
