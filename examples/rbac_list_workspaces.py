import asyncio
import os

from kessel.auth import fetch_oidc_discovery, OAuth2ClientCredentials
from kessel.grpc import RpcError
from kessel.inventory.v1beta2 import (
    ClientBuilder,
)
from kessel.rbac.v2 import list_workspaces, list_workspaces_async, principal_subject


KESSEL_ENDPOINT = os.environ.get("KESSEL_ENDPOINT", "localhost:9000")
ISSUER_URL = os.environ.get("AUTH_DISCOVERY_ISSUER_URL", "")
CLIENT_ID = os.environ.get("AUTH_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("AUTH_CLIENT_SECRET", "")

SUBJECT_ID = os.environ.get("RBAC_SUBJECT_ID", "alice")
SUBJECT_DOMAIN = os.environ.get("RBAC_SUBJECT_DOMAIN", "redhat")
RELATION = os.environ.get("RBAC_RELATION", "view_document")


def run_sync():
    try:
        discovery = fetch_oidc_discovery(ISSUER_URL)
        token_endpoint = discovery.token_endpoint

        auth_credentials = OAuth2ClientCredentials(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            token_endpoint=token_endpoint,
        )

        client = (
            ClientBuilder(KESSEL_ENDPOINT).oauth2_client_authenticated(auth_credentials).build()
        )

        with client:
            subject = principal_subject(SUBJECT_ID, SUBJECT_DOMAIN)
            print(f"Listing workspaces (sync) for subject='{SUBJECT_ID}' relation='{RELATION}'")
            for obj in list_workspaces(client, subject=subject, relation=RELATION):
                print(f"{obj}")
                print(f"{obj.pagination.continuation_token}")

    except RpcError as e:
        print("gRPC error occurred during list_workspaces (sync):")
        print(f"Code: {e.code()}")
        print(f"Details: {e.details()}")


async def run_async():
    try:
        discovery = fetch_oidc_discovery(ISSUER_URL)
        token_endpoint = discovery.token_endpoint

        auth_credentials = OAuth2ClientCredentials(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            token_endpoint=token_endpoint,
        )

        client = (
            ClientBuilder(KESSEL_ENDPOINT)
            .oauth2_client_authenticated(auth_credentials)
            .build_async()
        )

        async with client:
            subject = principal_subject(SUBJECT_ID, SUBJECT_DOMAIN)
            print(f"Listing workspaces (async) for subject='{SUBJECT_ID}' relation='{RELATION}'")
            async for obj in list_workspaces_async(client, subject=subject, relation=RELATION):
                print(f"{obj}")
                print(f"{obj.pagination.continuation_token}")

    except RpcError as e:
        print("gRPC error occurred during list_workspaces (async):")
        print(f"Code: {e.code()}")
        print(f"Details: {e.details()}")


if __name__ == "__main__":
    run_sync()
    asyncio.run(run_async())
