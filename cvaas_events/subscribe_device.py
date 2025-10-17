import argparse

import grpc

import json
import arista.event.v1
from google.protobuf.json_format import Parse

debug = False


def main(apiserverAddr, token=None, certs=None, key=None, ca=None, device=None):

    path_elts = ["Smash", "routing", "status", "route"]
    query = [
        create_query([(path_elts, [])], args.device)
    ]
    with GRPCClient(apiserverAddr, token=token, key=key,
                    ca=ca, certs=certs) as client:
        for batch in client.subscribe(query):
            for notif in batch["notifications"]:
                 pretty_print(notif["updates"])

    return 0


if __name__ == "__main__":
    base.add_argument(
        "--device", type=str, required=True, help="device (by SerialNumber) to subscribe to"
    )
    args = base.parse_args()
    exit(
        main(
            args.apiserver,
            certs=args.certFile,
            key=args.keyFile,
            ca=args.caFile,
            token=args.tokenFile,
        )
    )
