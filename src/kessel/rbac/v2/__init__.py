from typing import Optional, AsyncIterator, Iterable, TYPE_CHECKING
from requests.auth import AuthBase
import requests

from kessel.inventory.v1beta2.representation_type_pb2 import RepresentationType
from kessel.inventory.v1beta2.resource_reference_pb2 import ResourceReference
from kessel.inventory.v1beta2.subject_reference_pb2 import SubjectReference
from kessel.inventory.v1beta2.reporter_reference_pb2 import ReporterReference
from kessel.inventory.v1beta2.streamed_list_objects_request_pb2 import StreamedListObjectsRequest
from kessel.inventory.v1beta2.streamed_list_objects_response_pb2 import StreamedListObjectsResponse
from kessel.inventory.v1beta2.request_pagination_pb2 import RequestPagination

if TYPE_CHECKING:
    from kessel.inventory.connect_wrapper import StubWrapper, AsyncStubWrapper


class Workspace:
    def __init__(self, id: str, name: str, type: str, description: str):
        """
        Initialize a Workspace instance.

        Args:
            id: Workspace identifier
            name: Workspace name
            type: Workspace type ("root", "default")
            description: Workspace description
        """
        self.id = id
        self.name = name
        self.type = type
        self.description = description


def _fetch_workspace_by_type(
    rbac_base_endpoint: str,
    org_id: str,
    workspace_type: str,
    auth: Optional[AuthBase] = None,
    http_client: Optional[requests] = None,
) -> Workspace:
    """
    Internal helper to fetch a workspace by type ("root", "default").

    Args:
        auth: Authentication object compatible with requests.
        rbac_base_endpoint: The RBAC service endpoint URL.
        org_id: Organization ID to use for the request.
        workspace_type: The workspace type to query for.
        http_client: Optional requests-like client. Defaults to requests.

    Returns:
        A Workspace instance of the requested type.
    """
    client = http_client if http_client is not None else requests

    url = f"{rbac_base_endpoint.rstrip('/')}/api/rbac/v2/workspaces/"
    headers = {
        "x-rh-rbac-org-id": org_id,
        "Content-Type": "application/json",
    }

    response = client.get(url, params={"type": workspace_type}, headers=headers, auth=auth)
    response.raise_for_status()

    data = response.json()

    if "data" in data and data["data"]:
        workspace_data = data["data"][0]
    else:
        raise ValueError(f"No {workspace_type} workspace found in response")

    return Workspace(
        workspace_data["id"],
        workspace_data["name"],
        workspace_data["type"],
        workspace_data["description"],
    )


def fetch_root_workspace(
    rbac_base_endpoint: str,
    org_id: str,
    auth: Optional[AuthBase] = None,
    http_client: Optional[requests] = None,
) -> Workspace:
    """
    Fetches the root workspace for the specified organization.
    This function queries RBAC v2 to find the root workspace for the given org_id.

    GET /api/rbac/v2/workspaces/?type=root

    Args:
        auth: Authentication object compatible with requests (e.g. oauth2_auth(credentials)).
        rbac_base_endpoint: The RBAC service endpoint URL (stage/prod/ephemeral)
        org_id: Organization ID to use for the request.
        http_client: Optional requests module.
                    If not provided, uses the default requests module.

    Returns:
        A Workspace object representing the root workspace for the organization.
    """
    return _fetch_workspace_by_type(
        rbac_base_endpoint=rbac_base_endpoint,
        org_id=org_id,
        workspace_type="root",
        auth=auth,
        http_client=http_client,
    )


def fetch_default_workspace(
    rbac_base_endpoint: str,
    org_id: str,
    auth: Optional[AuthBase] = None,
    http_client: Optional[requests] = None,
) -> Workspace:
    """
    Fetches the default workspace for the specified organization.
    This function queries RBAC v2 to find the default workspace for the given org_id.

    GET /api/rbac/v2/workspaces/?type=default

    Args:
        auth: Authentication object compatible with requests (e.g. oauth2_auth(credentials)).
        rbac_base_endpoint: The RBAC service endpoint URL (stage/prod/ephemeral)
        org_id: Organization ID to use for the request.
        http_client: Optional requests module.
                    If not provided, uses the default requests module.

    Returns:
        A Workspace object representing the default workspace for the organization.
    """
    return _fetch_workspace_by_type(
        rbac_base_endpoint=rbac_base_endpoint,
        org_id=org_id,
        workspace_type="default",
        auth=auth,
        http_client=http_client,
    )


def workspace_type() -> RepresentationType:
    """
    Function to create a RepresentationType for workspace resources.
    Returns a protobuf RepresentationType configured for RBAC workspace objects.

    Returns:
        RepresentationType: A RepresentationType for workspace resources
    """
    return RepresentationType(resource_type="workspace", reporter_type="rbac")


def role_type() -> RepresentationType:
    """
    Function to create a RepresentationType for role resources.
    Returns a protobuf RepresentationType configured for RBAC role objects.

    Returns:
        RepresentationType: A RepresentationType for role resources
    """
    return RepresentationType(resource_type="role", reporter_type="rbac")


def principal_resource(id: str, domain: str) -> ResourceReference:
    """
    Creates a ResourceReference for a user principal based on user ID and domain.
    This function standardizes the creation of principal resources.

    Args:
        id: The user identifier
        domain: The domain or organization the user belongs to

    Returns:
        ResourceReference: A ResourceReference pointing to the user's principal resource
    """
    return ResourceReference(
        resource_type="principal",
        resource_id=f"{domain}/{id}",
        reporter=ReporterReference(type="rbac"),
    )


def role_resource(resource_id: str) -> ResourceReference:
    """
    Function to create a ResourceReference for a role.
    Returns a protobuf ResourceReference configured for RBAC role resources.

    Args:
        resource_id: The role identifier

    Returns:
        ResourceReference: A ResourceReference for the role
    """
    return ResourceReference(
        resource_type="role", resource_id=resource_id, reporter=ReporterReference(type="rbac")
    )


def workspace_resource(resource_id: str) -> ResourceReference:
    """
    Function to create a ResourceReference for a workspace.
    Returns a protobuf ResourceReference configured for RBAC workspace resources.

    Args:
        resource_id: The workspace identifier

    Returns:
        ResourceReference: A ResourceReference for the workspace
    """
    return ResourceReference(
        resource_type="workspace", resource_id=resource_id, reporter=ReporterReference(type="rbac")
    )


def principal_subject(id: str, domain: str) -> SubjectReference:
    """
    Creates a SubjectReference for a user principal based on user ID and domain.
    This is a convenience function that wraps principal_resource to create a subject reference.

    Args:
        id: The user identifier
        domain: The domain or organization the user belongs to

    Returns:
        SubjectReference: A SubjectReference for the user's principal
    """
    return SubjectReference(resource=principal_resource(id, domain))


def subject(resource_ref: ResourceReference, relation: Optional[str] = None) -> SubjectReference:
    """
    Creates a SubjectReference from a ResourceReference and an optional relation.
    This function allows you to easily create a subject reference.

    Args:
        resource_ref: The resource reference that identifies the subject
        relation: Optional relation that points to a set of subjects (e.g., "members", "owners")

    Returns:
        SubjectReference: A reference to a Subject or, if a relation is provided, a Subject Set.
    """
    if relation is not None:
        return SubjectReference(resource=resource_ref, relation=relation)
    else:
        return SubjectReference(resource=resource_ref)


def list_workspaces(
    inventory: "StubWrapper",
    subject: SubjectReference,
    relation: str,
    continuation_token: Optional[str] = None,
) -> Iterable[StreamedListObjectsResponse]:
    """
    Lists all workspaces that a subject has a specific relation to.
    This function queries the inventory service to find workspaces
    based on the subject's permissions.

    Args:
        subject: The subject to check permissions for
        relation: The relationship type to check "member", "admin", "viewer")
        inventory: The inventory service client stub for making the request
        continuation_token: Optional token to resume listing from a previous page

    Returns:
        An iterator of StreamedListObjectsResponse messages
    """
    while True:
        pagination = None
        if continuation_token is not None:
            pagination = RequestPagination(
                limit=1000,
                continuation_token=continuation_token if continuation_token is not None else "",
            )

        request = StreamedListObjectsRequest(
            object_type=workspace_type(),
            relation=relation,
            subject=subject,
            pagination=pagination,
        )

        last_token = None
        for response in inventory.streamed_list_objects(request):
            yield response
            if response.pagination is not None:
                last_token = response.pagination.continuation_token

        if not last_token:
            break

        continuation_token = last_token


async def list_workspaces_async(
    inventory: "AsyncStubWrapper",
    subject: SubjectReference,
    relation: str,
    continuation_token: Optional[str] = None,
) -> AsyncIterator[StreamedListObjectsResponse]:
    """
    Lists all workspaces that a subject has a specific relation to.
    This function queries the inventory service to find workspaces
     based on the subject's permissions.

    Args:
        inventory: The inventory service client stub for making the request (async channel).
        subject: The subject to check permissions for.
        relation: The relationship type to check (e.g. "member", "admin", "viewer").
        continuation_token: Optional token to resume listing from a previous page

    Returns:
        An async iterator of StreamedListObjectsResponse messages
    """
    while True:
        pagination = None
        if continuation_token is not None:
            pagination = RequestPagination(
                limit=1000,
                continuation_token=continuation_token if continuation_token is not None else "",
            )

        request = StreamedListObjectsRequest(
            object_type=workspace_type(),
            relation=relation,
            subject=subject,
            pagination=pagination,
        )

        last_token = None
        async for response in inventory.streamed_list_objects(request):
            yield response
            if response.pagination is not None:
                last_token = response.pagination.continuation_token

        if not last_token:
            break

        continuation_token = last_token
