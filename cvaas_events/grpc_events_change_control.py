import grpc
import os
import ssl
from arista.event.v1 import models, services
from google.protobuf.wrappers_pb2 import StringValue # Used for string fields in Protobuf messages

# --- Configuration ---
# Replace with your CloudVision server's IP address or hostname and gRPC port
CVP_SERVER_ADDRESS = "www.cv-staging.corp.arista.io:443"

# Path to your API token file
# It's highly recommended to use environment variables or a secure secret management system
# in production environments instead of a plain file.
TOKEN_FILE_PATH = "/home/andreasm/cvaas_token/cvaas.token"

# --- Function to load the API token ---
def load_api_token(file_path):
    """Loads the API token from a specified file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"API token file not found at: {file_path}")
    with open(file_path, 'r') as f:
        token = f.read().strip()
    if not token:
        raise ValueError(f"API token file '{file_path}' is empty.")
    return token

# --- Main subscription logic ---
def subscribe_to_change_control_succeeded_events():
    """
    Connects to CloudVision via gRPC and subscribes to
    'Change Control Succeeded' events.
    """
    try:
        # 1. Load the API token
        api_token = load_api_token(TOKEN_FILE_PATH)
        print(f"Successfully loaded API token from {TOKEN_FILE_PATH}")

        # 2. Create gRPC credentials
        # SSL/TLS credentials for secure communication
        ssl_credentials = grpc.ssl_channel_credentials()
        # Call credentials for token-based authentication
        call_credentials = grpc.access_token_call_credentials(api_token)
        # Combine both for a secure, authenticated channel
        composite_credentials = grpc.composite_channel_credentials(
            ssl_credentials, call_credentials
        )

        # 3. Establish a secure gRPC channel to CloudVision
        print(f"Connecting to CloudVision at {CVP_SERVER_ADDRESS}...")
        with grpc.secure_channel(CVP_SERVER_ADDRESS, composite_credentials) as channel:
            # 4. Create an Event Service stub
            event_stub = services.EventServiceStub(channel)
            print("gRPC channel established and EventServiceStub created.")

            # 5. Define the event filter for 'Change Control Succeeded'
            # We filter by the 'title' field of the Event model.
            # The exact string "Change Control Succeeded" is based on CloudVision's
            # documented event types. You can verify this in the CVP GUI under Events.
            change_control_succeeded_filter = models.Event(
                title=StringValue(value="Change Control Succeeded")
            )

            # You could also add a severity filter if needed, e.g.:
            # severity=models.EVENT_SEVERITY_INFO

            # 6. Create the stream request
            # partial_eq_filter means that events matching these partial attributes will be streamed.
            request = services.EventStreamRequest(
                partial_eq_filter=[change_control_succeeded_filter]
            )

            print("Subscribing to 'Change Control Succeeded' events. Waiting for events...")
            # 7. Start the subscription and process incoming events
            for resp in event_stub.Subscribe(request):
                # 'resp' is an Event object containing the details of the event
                print("\n--- New Change Control Succeeded Event Received ---")
                print(f"Timestamp: {resp.key.timestamp}") # Event timestamp in milliseconds since epoch
                print(f"Title: {resp.title.value}")
                print(f"Description: {resp.description.value}")
                print(f"Severity: {models.EVENT_SEVERITY_TO_STRING[resp.severity]}")

                # Accessing other relevant fields if they exist for this event type:
                if resp.change_control_id.value:
                    print(f"Change Control ID: {resp.change_control_id.value}")
                if resp.executor.value:
                    print(f"Executor: {resp.executor.value}")
                if resp.impacted_devices:
                    print(f"Impacted Devices: {[d.value for d in resp.impacted_devices]}")
                # You might need to inspect the 'resp' object structure for other fields
                # relevant to Change Control events (e.g., task IDs, status).
                # The exact fields available depend on the Protobuf definition for the event.

    except FileNotFoundError as e:
        print(f"Error: {e}. Please create the '{TOKEN_FILE_PATH}' file with your API token.")
    except ValueError as e:
        print(f"Error: {e}")
    except grpc.RpcError as e:
        print(f"gRPC Error: {e.code()} - {e.details()}")
        if e.code() == grpc.StatusCode.UNAUTHENTICATED:
            print("Authentication failed. Please check your API token and its permissions.")
        elif e.code() == grpc.StatusCode.UNAVAILABLE:
            print(f"Could not connect to CVP at {CVP_SERVER_ADDRESS}. Is the server running and reachable?")
        elif e.code() == grpc.StatusCode.PERMISSION_DENIED:
            print("Permission denied. The token might not have sufficient privileges to subscribe to events.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

# --- Entry point of the script ---
if __name__ == "__main__":
    subscribe_to_change_control_succeeded_events()

