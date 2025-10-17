import time
import sys
import json
import os
import argparse

# The gRPC library is required for this script
import grpc
# You will need to install the Arista CloudVision gRPC client libraries for events.
# These libraries need to be generated or installed based on your CloudVision version.
import arista.event.v1.services as event_services
import arista.event.v1 as event_pb2
from google.protobuf.json_format import MessageToDict

# --- Configuration ---
# IMPORTANT: Use environment variables or a secure vault to store sensitive information
# These are placeholder values.

CVP_SERVER = os.environ.get("CVP_SERVER") # e.g., "my-cvaas-instance.arista.io:443"
CVP_TOKEN = os.environ.get("CVP_TOKEN")
TARGET_DEVICE_IDS = os.environ.get("TARGET_DEVICE_IDS", "").split(',')  # Comma-separated list of device IDs
EVENT_RULE_LABEL = "ci_cd_config_applied"
RPC_TIMEOUT = 600 # in seconds (e.g., 10 minutes for subscription)

# Ensure all required environment variables are set and that TARGET_DEVICE_IDS is not an empty list
if not CVP_SERVER or not CVP_TOKEN or not TARGET_DEVICE_IDS or TARGET_DEVICE_IDS == ['']:
    print("Error: Required environment variables CVP_SERVER, CVP_TOKEN, and TARGET_DEVICE_IDS are not set or are empty.")
    sys.exit(1)

# --- API Interaction Functions ---
def get_event_stub():
    """
    Creates a gRPC channel and returns an EventService stub.
    """
    # Create the header object for the token
    call_creds = grpc.access_token_call_credentials(CVP_TOKEN)
    
    # Use standard TLS credentials
    channel_creds = grpc.ssl_channel_credentials()
    
    # Composite the credentials
    conn_creds = grpc.composite_channel_credentials(channel_creds, call_creds)

    # Initialize a secure connection to the server
    channel = grpc.secure_channel(CVP_SERVER, conn_creds)
    stub = event_services.EventServiceStub(channel)
    return stub

def subscribe_to_events(stub):
    """
    Subscribes to a real-time stream of CloudVision events and yields them.
    """
    # The subscription request. We are not filtering by time here as the stream gives new events.
    req = event_services.EventStreamRequest()
    req.partial_eq_filter.append(
        event_services.Event(rule_id=EVENT_RULE_LABEL)
    )

    try:
        # Iterate over the stream of responses from the Subscribe RPC
        for response in stub.Subscribe(req, timeout=RPC_TIMEOUT):
            # The response is a stream of Event messages
            yield response
    except grpc.RpcError as e:
        print(f"Error during subscription: {e}")
        # Exit with a non-zero code to fail the CI/CD job
        sys.exit(1)

# --- Main Script Execution ---
if __name__ == "__main__":
    
    # Initialize the gRPC stub
    try:
        cvp_stub = get_event_stub()
    except grpc.RpcError as e:
        print(f"Failed to connect to CloudVision: {e}")
        sys.exit(1)

    print("Starting CI/CD job. Subscribing to real-time events.")
    print(f"Looking for event with rule label '{EVENT_RULE_LABEL}' on devices: {', '.join(TARGET_DEVICE_IDS)}")

    event_found = False
    
    # The subscription will block and receive events as they happen
    for event_response in subscribe_to_events(cvp_stub):
        # Convert the protobuf message to a dictionary for easier access
        event_dict = MessageToDict(event_response, preserving_proto_field_name=True)
        event_device_id = event_dict.get("deviceId", "N/A")

        if event_device_id in TARGET_DEVICE_IDS:
            print(f"\nSuccess! Found event for device {event_device_id}.")
            print("Event details:")
            print(json.dumps(event_dict, indent=2))
            
            # Found the event, so we can exit the loop and the script
            event_found = True
            break
        else:
            print(f"Received event for device {event_device_id}. Waiting for a match...")

    if event_found:
        print("\nPipeline can proceed to the next stage.")
        sys.exit(0)
    else:
        # This part of the code would only be reached if the gRPC stream timed out
        print("\nTimeout reached. The event was not found. Exiting with failure.")
        sys.exit(1)

