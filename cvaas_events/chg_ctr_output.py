import argparse
import grpc
import json
import arista.changecontrol.v1
from google.protobuf.json_format import Parse, MessageToJson
import os # Import the os module for path manipulation

RPC_TIMEOUT = 300  # in seconds

def main(args):
    # read the file containing a session token to authenticate with
    token = args.token_file.read().strip()
    # create the header object for the token
    callCreds = grpc.access_token_call_credentials(token)

    # if using a self-signed certificate (should be provided as arg)
    if args.cert_file:
        # create the channel using the self-signed cert
        cert = args.cert_file.read()
        channelCreds = grpc.ssl_channel_credentials(root_certificates=cert)
    else:
        # otherwise default to checking against CAs
        channelCreds = grpc.ssl_channel_credentials()
    connCreds = grpc.composite_channel_credentials(channelCreds, callCreds)

    # Create an empty ChangeControlStreamRequest.
    # This will subscribe to all *new* change control events.
    json_request = json.dumps({})
    req = Parse(json_request, arista.changecontrol.v1.services.ChangeControlStreamRequest(), False)

    # Define the target device IDs
    # Make sure these are strings, as they appear in the JSON output
    TARGET_DEVICE_IDS = [
        "9AAEE15EEB3A18FADDA20C1BACDB76F8"
    ]
    TARGET_STATUS = "CHANGE_CONTROL_STATUS_COMPLETED"

    output_file_path = "completed_change_controls.txt"

    # initialize a connection to the server using our connection settings (auth + TLS)
    with grpc.secure_channel(args.server, connCreds) as channel:
        tag_stub = arista.changecontrol.v1.services.ChangeControlServiceStub(channel)
        print("Subscribed to ChangeControl events. Waiting for real-time updates...")
        print(f"Filtered events will be written to: {output_file_path}")

        try:
            # Open the file in append mode. It will be created if it doesn't exist.
            with open(output_file_path, 'a') as f:
                # Iterate over the stream of responses
                for response in tag_stub.Subscribe(req, timeout=RPC_TIMEOUT):
                    # Convert the protobuf message to JSON for easier processing
                    response_json_str = MessageToJson(response, preserving_proto_field_name=True, indent=2)
                    response_data = json.loads(response_json_str)

                    # Check for the desired status
                    event_status = response_data.get('value', {}).get('status')
                    if event_status == TARGET_STATUS:
                        # Check for the desired device IDs
                        device_ids_in_event = response_data.get('value', {}).get('device_ids', {}).get('values', [])
                        
                        # Check if any of the target device IDs are present in the event's device_ids
                        if any(device_id in TARGET_DEVICE_IDS for device_id in device_ids_in_event):
                            print(f"Found a matching event for status '{TARGET_STATUS}' and device_ids: {device_ids_in_event}")
                            f.write(response_json_str)
                            f.write("\n---\n") # Add a separator for readability in the file
                    # Optionally, print all events to console for debugging or general monitoring
                    # print(response_json_str)

        except grpc.RpcError as e:
            print(f"Error during subscription: {e}")
        except KeyboardInterrupt:
            print("Subscription interrupted by user.")
        finally:
            print(f"Script finished. Check '{output_file_path}' for recorded events.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        '--server',
        required=True,
        help="CloudVision server to connect to in <host>:<port> format")
    parser.add_argument("--token-file", required=True,
                            type=argparse.FileType('r'), help="file with access token")
    parser.add_argument("--cert-file", type=argparse.FileType('rb'),
                            help="certificate to use as root CA")
    args = parser.parse_args()
    main(args)
