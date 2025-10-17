import time
import sys
import json
import os
import argparse
import logging
import grpc
from google.protobuf.json_format import ParseDict, MessageToDict
import arista.changecontrol.v1.services as change_control_services

# Configure logging for better visibility
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration ---
CVP_SERVER = os.environ.get("CVP_SERVER")
CVP_TOKEN = os.environ.get("CVP_TOKEN")
CHANGE_CONTROL_NAME = os.environ.get("CHANGE_CONTROL_NAME")
POLLING_INTERVAL = 30 # in seconds
TIMEOUT = 600 # in seconds (e.g., 10 minutes)

if not CVP_SERVER or not CVP_TOKEN or not CHANGE_CONTROL_NAME:
    logging.error("Required environment variables CVP_SERVER, CVP_TOKEN, and CHANGE_CONTROL_NAME are not set.")
    sys.exit(1)

# --- API Interaction Functions ---
def get_change_control_stub():
    """
    Creates a gRPC channel and returns a ChangeControlService stub.
    """
    call_creds = grpc.access_token_call_credentials(CVP_TOKEN)
    channel_creds = grpc.ssl_channel_credentials()
    conn_creds = grpc.composite_channel_credentials(channel_creds, call_creds)

    channel = grpc.secure_channel(CVP_SERVER, conn_creds)
    stub = change_control_services.ChangeControlServiceStub(channel)
    return stub

def find_change_control_by_name(stub, cc_name):
    """Searches for a Change Control by its name and returns its ID."""
    try:
        logging.info(f"Searching for Change Control with name '{cc_name}'...")
        # Make the request to get all change controls
        resp = stub.GetAll(change_control_services.ChangeControlRequest())

        # Iterate over the response directly
        for change_control in resp:
            # THIS IS THE CORRECTED LINE
            if change_control.value.change.name.value == cc_name:
                logging.info(f"Found Change Control ID: {change_control.value.key.id.value}")
                return change_control.value.key.id.value
        logging.error("Change Control not found.")
        return None
    except grpc.RpcError as e:
        logging.error(f"gRPC Error while searching for Change Control: {e.details()}")
        sys.exit(1)

def poll_for_completion(stub, change_control_id):
    """
    Polls the ChangeControl service for a specific job completion.
    """
    start_time = time.time()
    while True:
        try:
            request_dict = {"key": {"id": change_control_id}}
            req = ParseDict(request_dict, change_control_services.ChangeControlRequest())

            logging.info(f"Polling Change Control ID: {change_control_id}...")
            response = stub.GetOne(req)
            change_control_info = MessageToDict(response, preserving_proto_field_name=True)
            status = change_control_info.get("status", "N/A")

            logging.info(f"Change Control job status: {status}")

            if status == "STATUS_COMPLETED":
                logging.info(f"Change Control job '{change_control_id}' completed successfully.")
                return True
            if status in ["STATUS_FAILED", "STATUS_TERMINATED", "STATUS_ABANDONED"]:
                logging.error(f"Change Control job '{change_control_id}' ended with a failure status: {status}.")
                return False
            if time.time() - start_time > TIMEOUT:
                logging.error(f"Timeout reached. Change Control job '{change_control_id}' did not complete in time. Current status: {status}.")
                return False

            logging.info(f"Waiting {POLLING_INTERVAL} seconds before next poll.")
            time.sleep(POLLING_INTERVAL)

        except grpc.RpcError as e:
            logging.error(f"gRPC Error while polling: {e.details()}")
            return False
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")
            return False

# --- Main Script Execution ---
if __name__ == "__main__":
    logging.info("Starting CI/CD change control polling job.")
    
    try:
        cvp_stub = get_change_control_stub()
    except Exception as e:
        logging.error(f"Failed to connect to CloudVision: {e}")
        sys.exit(1)

    # 1. Find the CC ID from the name
    cc_id = find_change_control_by_name(cvp_stub, CHANGE_CONTROL_NAME)
    if not cc_id:
        sys.exit(1)

    # 2. Poll for completion
    job_completed = poll_for_completion(cvp_stub, cc_id)

    if job_completed:
        logging.info("Pipeline can proceed to the next stage.")
        sys.exit(0)
    else:
        logging.info("Exiting with failure.")
        sys.exit(1)
