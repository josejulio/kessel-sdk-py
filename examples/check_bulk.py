import os
from kessel.grpc import RpcError

from kessel.inventory.v1beta2 import (
    check_bulk_request_pb2,
    resource_reference_pb2,
    reporter_reference_pb2,
    ClientBuilder,
)
from kessel.rbac.v2 import principal_subject, workspace_resource

KESSEL_ENDPOINT = os.environ.get("KESSEL_ENDPOINT", "localhost:9000")


def run():
    client = ClientBuilder(KESSEL_ENDPOINT).insecure().build()

    with client:
        # Item 1: Check if bob can view widgets in workspace_123
        item1 = check_bulk_request_pb2.CheckBulkRequestItem(
            object=workspace_resource("workspace_123"),
            relation="view_widget",
            subject=principal_subject(id="bob", domain="redhat"),
        )

        # Item 2: Check if bob can use widgets in workspace_456
        item2 = check_bulk_request_pb2.CheckBulkRequestItem(
            object=workspace_resource("workspace_456"),
            relation="use_widget",
            subject=principal_subject(id="bob", domain="redhat"),
        )

        # Item 3: Check with invalid resource type to demonstrate error handling
        item3 = check_bulk_request_pb2.CheckBulkRequestItem(
            object=resource_reference_pb2.ResourceReference(
                resource_type="not_a_valid_type",
                resource_id="invalid_resource",
                reporter=reporter_reference_pb2.ReporterReference(type="rbac"),
            ),
            relation="view_widget",
            subject=principal_subject(id="alice", domain="redhat"),
        )

        check_bulk_request = check_bulk_request_pb2.CheckBulkRequest(items=[item1, item2, item3])

        try:
            check_bulk_response = client.check_bulk(check_bulk_request)
            print("CheckBulk response received successfully")
            print(f"Total pairs in response: {len(check_bulk_response.pairs)}\n")

            for idx, pair in enumerate(check_bulk_response.pairs):
                print(f"--- Result {idx + 1} ---")

                req = pair.request
                print(
                    f"Request: subject={req.subject.resource.resource_id} "
                    f"relation={req.relation} "
                    f"object={req.object.resource_id}"
                )

                if pair.HasField("item"):
                    print(pair.item)
                elif pair.HasField("error"):
                    print(f"Error: Code={pair.error.code}, Message={pair.error.message}")

        except RpcError as e:
            print("gRPC error occurred during CheckBulk:")
            print(f"Code: {e.code()}")
            print(f"Message: {e.details()}")


if __name__ == "__main__":
    run()
