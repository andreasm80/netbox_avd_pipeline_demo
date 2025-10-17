# The gRPC library is required for this script
import time
import sys
import json
import os
import argparse
import logging
from datetime import datetime
from google.protobuf.json_format import ParseDict, MessageToDict

# You will need to install the Arista CloudVision gRPC client libraries.
# pip install cloudvision-python
import arista.changecontrol.v1.services as change_control_services
import grpc

# Configure logging for better visibility
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration ---
# IMPORTANT: Use environment variables to pass these values
CVP_SERVER = os.environ.get("CVP_SERVER")
CVP_TOKEN = os.environ.get("CVP_TOKEN")
CHANGE_CONTROL_ID = os.environ.get("CHANGE_CONTROL_ID")
POLLING_INTERVAL = 30 # in seconds
TIMEOUT = 600 # in seconds (e.g., 10 minutes)

# Ensure all required environment variables are set
if not CVP_SERVER or not CVP_TOKEN or not CHANGE_CONTROL_ID:
    logging.error("Required environment variables CVP_SERVER, CVP_TOKEN, and CHANGE_CONTROL_ID are not set.")
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

def poll_for_completion(stub, change_control_id):
    """
    Polls the ChangeControl service for a specific job completion.
    """
    start_time = time.time()

    while True:
        try:
            # Construct the request as a dictionary, which is safer
            request_dict = {
                "key": {
                    "id": change_control_id
                }
            }
            # Parse the dictionary into the correct protobuf message object
            req = ParseDict(request_dict, change_control_services.ChangeControlRequest())

            logging.info(f"Polling Change Control ID: {change_control_id}...")
            response = stub.GetOne(req)
            change_control_info = MessageToDict(response, preserving_proto_field_name=True)

            status = change_control_info.get("status", "N/A")

            if status == "STATUS_COMPLETED":
                logging.info(f"Change Control job '{change_control_id}' completed successfully.")
                return True

            if status in ["STATUS_FAILED", "STATUS_TERMINATED"]:
                logging.error(f"Change Control job '{change_control_id}' ended with a failure status: {status}.")
                return False

            if time.time() - start_time > TIMEOUT:
                logging.error(f"Timeout reached. Change Control job '{change_control_id}' did not complete in time. Current status: {status}.")
                return False

            logging.info(f"Change Control job status is '{status}'. Waiting {POLLING_INTERVAL} seconds before next poll.")
            time.sleep(POLLING_INTERVAL)

        except grpc.RpcError as e:
            logging.error(f"gRPC Error while polling: {e}")
            return False
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")
            return False

# --- Main Script Execution ---
if __name__ == "__main__":

    # In a real CI/CD pipeline, the CHANGE_CONTROL_ID would be passed from a previous
    # stage that initiates the Change Control job.
    logging.info("Starting CI/CD change control polling job.")
    
    try:
        cvp_stub = get_change_control_stub()
    except Exception as e:
        logging.error(f"Failed to connect to CloudVision: {e}")
        sys.exit(1)

    job_completed = poll_for_completion(cvp_stub, CHANGE_CONTROL_ID)

    if job_completed:
        logging.info("Pipeline can proceed to the next stage.")
        sys.exit(0)
    else:
        logging.info("Exiting with failure.")
        sys.exit(1)
