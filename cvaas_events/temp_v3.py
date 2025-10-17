import argparse
import grpc
import json
import arista.changecontrol.v1
from google.protobuf.json_format import Parse

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

    # List of device IDs to filter for
    device_ids = [
        "2E85018A64223A538DF7998034B03EDC",
        "4F29E152080FCEFB29DB756B4F2C3577",
        "9AAEE15EEB3A18FADDA20C1BACDB76F8",
        "9CDD2323393E14468FC22C4AF1F1D99B",
        "B52C1D9B0CA30A90F2A9E7046D573EE6",
        "CEEEDE54D6FC6582BC75FF7E2B8FCE2D",
        "D264759BAB01E3100E3A85704B65CBA1",
        "F61379FA1B345E2FFDD5FB1B156FB329",
        "2AB9BDD18A71C07B6A8A953AD88601E1",
        "BBF97A93C142AB9A11F2C3358FAA6A8C"
    ]

    # Create a JSON request with a filter for the specified device IDs
    json_request = {
        "filter": {
            "deviceIds": {
                "values": device_ids
            }
        }
    }
    req = Parse(json.dumps(json_request), arista.changecontrol.v1.services.ChangeControlStreamRequest(), False)

    # initialize a connection to the server using our connection settings (auth + TLS)
    with grpc.secure_channel(args.server, connCreds) as channel:
        tag_stub = arista.changecontrol.v1.services.ChangeControlServiceStub(channel)

        try:
            print("Attempting to subscribe to Change Control events for specified device IDs...")
            # Iterate directly over the stream instead of converting to a list
            for event in tag_stub.Subscribe(req, timeout=RPC_TIMEOUT):
                print("Received event:")
                print(event)  # This will print the protobuf message object
                # You can add more specific processing of the 'event' object here
        except grpc.RpcError as e:
            # gRPC specific errors
            print(f"gRPC Error: {e.code()} - {e.details()}")
            if e.code() == grpc.StatusCode.UNAUTHENTICATED:
                print("Authentication failed. Check your token's validity and permissions.")
            elif e.code() == grpc.StatusCode.UNAVAILABLE:
                print("Server unavailable. Check the server address and connectivity.")
            elif e.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
                print("RPC Deadline Exceeded. The server did not respond within the timeout.")
            elif e.code() == grpc.StatusCode.CANCELLED:
                print("The RPC was cancelled (e.g., by the client closing the connection).")
            else:
                print("An unexpected gRPC error occurred.")
        except Exception as e:
            # Catch any other unexpected Python errors
            print(f"An unexpected Python error occurred: {e}")

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
