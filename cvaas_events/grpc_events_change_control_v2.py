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
def subscribe_to_all_events():
    """
    Connects to CloudVision via gRPC and subscribes to
    ALL events.
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

            # 5. Define the event filter (removed to listen to all events)
            # To listen to all events, we simply create an empty EventStreamRequest.
            # No partial_eq_filter is needed.

            # 6. Create the stream request
            # An empty partial_eq_filter means all events will be streamed.
            request = services.EventStreamRequest()

            print("Subscribing to ALL events. Waiting for events...")
            # 7. Start the subscription and process incoming events
            for resp in event_stub.Subscribe(request):
                # 'resp' is an EventStreamResponse object.
                # The actual event data can be in 'resp.event' (for new events)
                # or directly in 'resp.value' (often for initial sync/catch-up events).
                print(f"DEBUG: Type of received stream response object: {type(resp)}")

                event = None
                if hasattr(resp, 'event') and resp.event is not None:
                    event = resp.event
                elif hasattr(resp, 'value') and resp.value is not None:
                    # If 'event' field is not present, check for 'value' field.
                    # This often happens with initial synchronization events.
                    event = resp.value

                if event is None:
                    print("WARNING: Received EventStreamResponse with no 'event' or 'value' field. Skipping.")
                    print(f"DEBUG: Full response object (when event is missing): {resp}")
                    continue # Skip to the next response

                print(f"DEBUG: Type of event object within response: {type(event)}")
                print("\n--- New Event Received ---")

                # Safely access timestamp
                timestamp_value = "N/A"
                try:
                    # EventKey might be nested, so check for key and timestamp attributes
                    if event.key and hasattr(event.key, 'timestamp') and isinstance(event.key.timestamp, Timestamp):
                        # Timestamp is a google.protobuf.timestamp_pb2.Timestamp object
                        # It has 'seconds' and 'nanos' attributes.
                        timestamp_seconds = event.key.timestamp.seconds
                        timestamp_nanos = event.key.timestamp.nanos
                        # Convert nanos to a string and pad with zeros to 9 digits
                        timestamp_value = f"{timestamp_seconds}.{str(timestamp_nanos).zfill(9)}"
                except Exception as ex:
                    print(f"Error accessing timestamp: {type(ex).__name__} - {ex}")
                    print(f"Debug: event.key type: {type(event.key)}, event.key value: {event.key}")
                print(f"Timestamp: {timestamp_value}")

                # Safely access title and description (assuming they are StringValue types)
                title_value = "N/A"
                try:
                    title_value = event.title.value if hasattr(event, 'title') and event.title else "N/A"
                except Exception as ex:
                    print(f"Error accessing title: {type(ex).__name__} - {ex}")
                    print(f"Debug: event.title type: {type(event.title)}, event.title value: {event.title}")
                print(f"Title: {title_value}")

                description_value = "N/A"
                try:
                    description_value = event.description.value if hasattr(event, 'description') and event.description else "N/A"
                except Exception as ex:
                    print(f"Error accessing description: {type(ex).__name__} - {ex}")
                    print(f"Debug: event.description type: {type(event.description)}, event.description value: {event.description}")
                print(f"Description: {description_value}")

                # Safely access severity mapping
                severity_value = "N/A"
                try:
                    if hasattr(event, 'severity') and event.severity is not None:
                        # Use Name() method for enum to string conversion
                        severity_value = models.EventSeverity.Name(event.severity)
                except Exception as ex:
                    print(f"Error accessing severity: {type(ex).__name__} - {ex}")
                    print(f"Debug: event.severity type: {type(event.severity)}, event.severity value: {event.severity}")
                print(f"Severity: {severity_value}")

                # Safely access event_type
                event_type_value = "N/A"
                try:
                    event_type_value = event.event_type.value if hasattr(event, 'event_type') and event.event_type else "N/A"
                except Exception as ex:
                    print(f"Error accessing event_type: {type(ex).__name__} - {ex}")
                    print(f"Debug: event.event_type type: {type(event.event_type)}, event.event_type value: {event.event_type}")
                print(f"Event Type: {event_type_value}")


                # Accessing other relevant fields if they exist for this event type:
                # These fields might not be present for all event types, so handle them gracefully.
                try:
                    if hasattr(event, 'change_control_id') and event.change_control_id and event.change_control_id.value:
                        print(f"Change Control ID: {event.change_control_id.value}")
                except Exception as ex:
                    print(f"Error accessing change_control_id: {type(ex).__name__} - {ex}")

                try:
                    if hasattr(event, 'executor') and event.executor and event.executor.value:
                        print(f"Executor: {event.executor.value}")
                except Exception as ex:
                    print(f"Error accessing executor: {type(ex).__name__} - {ex}")

                try:
                    if hasattr(event, 'impacted_devices') and event.impacted_devices:
                        print(f"Impacted Devices: {[d.value for d in event.impacted_devices if d.value]}")
                except Exception as ex:
                    print(f"Error accessing impacted_devices: {type(ex).__name__} - {ex}")

                # You can add more specific field checks based on the event type if needed.
                # For example, for "CVE Threat Exposure" events, you might want to parse 'data' or 'components'.
                if event_type_value == "BUGALERTS_CVE_EXPOSED" and hasattr(event, 'data') and event.data:
                    print("  --- CVE Details (from 'data' field) ---")
                    # The 'data' field itself is a repeated field of KeyValue pairs
                    for item in event.data.data:
                        try:
                            # Ensure 'item' has 'key' and 'value' attributes
                            if hasattr(item, 'key') and hasattr(item, 'value'):
                                print(f"    {item.key}: {item.value}")
                            else:
                                print(f"    WARNING: Data item has unexpected structure: {item}")
                        except Exception as ex:
                            print(f"    Error processing data item: {type(ex).__name__} - {ex}")
                            print(f"    Debug: Data item type: {type(item)}, value: {item}")

                if hasattr(event, 'components') and event.components:
                    print("  --- Components Details ---")
                    # The 'components' field is also a nested structure
                    for component_item in event.components.components:
                        try:
                            component_type = models.COMPONENT_TYPE_TO_STRING.get(component_item.type, "UNKNOWN")
                            print(f"    Component Type: {component_type}")
                            if hasattr(component_item, 'components'): # Nested components within component_item
                                for detail in component_item.components:
                                    if hasattr(detail, 'key') and hasattr(detail, 'value'):
                                        print(f"      {detail.key}: {detail.value}")
                                    else:
                                        print(f"      WARNING: Component detail has unexpected structure: {detail}")
                        except Exception as ex:
                            print(f"    Error processing component item: {type(ex).__name__} - {ex}")
                            print(f"    Debug: Component item type: {type(component_item)}, value: {component_item}")


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
        # This catch-all will now print the actual type of the exception
        print(f"An unexpected error occurred: {type(e).__name__} - {e}")

# --- Entry point of the script ---
if __name__ == "__main__":
    subscribe_to_all_events()
