import os
from kessel.grpc import RpcError

from kessel.inventory.v1beta2 import (
    representation_type_pb2,
    reporter_reference_pb2,
    resource_reference_pb2,
    streamed_list_objects_request_pb2,
    subject_reference_pb2,
    ClientBuilder,
)


KESSEL_ENDPOINT = os.environ.get("KESSEL_ENDPOINT", "localhost:9000")


def run():
    client = ClientBuilder(KESSEL_ENDPOINT).insecure().build()

    with client:
        object_type = representation_type_pb2.RepresentationType(
            resource_type="host",
            reporter_type="hbi",
        )
        subject = subject_reference_pb2.SubjectReference(
            resource=resource_reference_pb2.ResourceReference(
                reporter=reporter_reference_pb2.ReporterReference(type="rbac"),
                resource_id="1",
                resource_type="principal",
            )
        )
        request = streamed_list_objects_request_pb2.StreamedListObjectsRequest(
            object_type=object_type,
            relation="view",
            subject=subject,
        )

        try:
            responses = client.streamed_list_objects(request)
            print("Received streamed responses:")
            for response in responses:
                print(response)

        except RpcError as e:
            print("gRPC error occurred:")
            print(f"Code: {e.code()}")
            print(f"Message: {e.details()}")


if __name__ == "__main__":
    run()
