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

    # Filter for specific device ID
    json_request = json.dumps({
        "filter": {
            "deviceIds": {
                "values": ["9AAEE15EEB3A18FADDA20C1BACDB76F8"]
            }
        }
    })
    print(f"Subscription request: {json_request}")
    req = Parse(json_request, arista.changecontrol.v1.services.ChangeControlStreamRequest(), False)

    # Initialize connection and subscribe
    print(f"Connecting to server: {args.server}")
    with grpc.secure_channel(args.server, connCreds) as channel:
        tag_stub = arista.changecontrol.v1.services.ChangeControlServiceStub(channel)
        print("Starting subscription...")
        try:
            for response in tag_stub.Subscribe(req, timeout=RPC_TIMEOUT):
                print(f"Received event: {response}")
            print("Stream ended (no more events or timeout reached)")
        except grpc.RpcError as e:
            print(f"gRPC error: {e}")
        except KeyboardInterrupt:
            print("Subscription interrupted by user")

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
