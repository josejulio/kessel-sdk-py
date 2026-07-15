"""
RPC utilities for Kessel SDK.

Provides transport-agnostic abstractions for credentials, errors, and status codes
that work across different RPC implementations.
"""

from typing import TYPE_CHECKING
from connectrpc.errors import ConnectError
from enum import IntEnum

if TYPE_CHECKING:
    from kessel.auth import OAuth2ClientCredentials


# RPC status codes (standardized across implementations)
class StatusCode(IntEnum):
    """
    RPC status codes.

    Standard status codes used across RPC implementations (gRPC, Connect, etc).
    See: https://grpc.github.io/grpc/core/md_doc_statuscodes.html
    """

    OK = 0
    CANCELLED = 1
    UNKNOWN = 2
    INVALID_ARGUMENT = 3
    DEADLINE_EXCEEDED = 4
    NOT_FOUND = 5
    ALREADY_EXISTS = 6
    PERMISSION_DENIED = 7
    RESOURCE_EXHAUSTED = 8
    FAILED_PRECONDITION = 9
    ABORTED = 10
    OUT_OF_RANGE = 11
    UNIMPLEMENTED = 12
    INTERNAL = 13
    UNAVAILABLE = 14
    DATA_LOSS = 15
    UNAUTHENTICATED = 16


# Map Connect error codes to standard RPC status codes
_CONNECT_TO_GRPC_CODE = {
    "canceled": StatusCode.CANCELLED,
    "unknown": StatusCode.UNKNOWN,
    "invalid_argument": StatusCode.INVALID_ARGUMENT,
    "deadline_exceeded": StatusCode.DEADLINE_EXCEEDED,
    "not_found": StatusCode.NOT_FOUND,
    "already_exists": StatusCode.ALREADY_EXISTS,
    "permission_denied": StatusCode.PERMISSION_DENIED,
    "resource_exhausted": StatusCode.RESOURCE_EXHAUSTED,
    "failed_precondition": StatusCode.FAILED_PRECONDITION,
    "aborted": StatusCode.ABORTED,
    "out_of_range": StatusCode.OUT_OF_RANGE,
    "unimplemented": StatusCode.UNIMPLEMENTED,
    "internal": StatusCode.INTERNAL,
    "unavailable": StatusCode.UNAVAILABLE,
    "data_loss": StatusCode.DATA_LOSS,
    "unauthenticated": StatusCode.UNAUTHENTICATED,
}


class RpcError(Exception):
    """
    RPC error with status code and details.

    Standard exception type for RPC operations, providing access to error status
    codes and messages regardless of underlying transport.

    Example:
        try:
            response = client.check(request)
        except RpcError as e:
            print(f"Code: {e.code()}")
            print(f"Details: {e.details()}")
    """

    def __init__(self, connect_error: ConnectError):
        """
        Create an RPC error from a ConnectError.

        Args:
            connect_error: The underlying transport error
        """
        self._connect_error = connect_error
        super().__init__(connect_error.message)

    def code(self) -> StatusCode:
        """
        Get the RPC status code.

        Returns:
            StatusCode enum value indicating the error type

        Example:
            if error.code() == StatusCode.PERMISSION_DENIED:
                print("Access denied")
        """
        # Map Connect's code (string) to StatusCode (int)
        connect_code = self._connect_error.code
        return _CONNECT_TO_GRPC_CODE.get(connect_code, StatusCode.UNKNOWN)

    def details(self) -> str:
        """
        Get the error message details.

        Returns:
            Human-readable error message string

        Example:
            print(f"Error: {error.details()}")
        """
        return self._connect_error.message

    @property
    def connect_error(self) -> ConnectError:
        """
        Access the underlying ConnectError for advanced use cases.

        Returns:
            The wrapped ConnectError instance
        """
        return self._connect_error


def oauth2_call_credentials(credentials: "OAuth2ClientCredentials"):
    """
    Create OAuth2 call credentials for RPC authentication.

    Prepares OAuth2 credentials for use with authenticated RPC clients.
    The credentials will be used to automatically add authentication tokens
    to RPC requests.

    Args:
        credentials: OAuth2ClientCredentials instance

    Returns:
        Credentials object ready for use with ClientBuilder

    Example:
        from kessel.auth import OAuth2ClientCredentials, fetch_oidc_discovery
        from kessel.grpc import oauth2_call_credentials
        from kessel.inventory.v1beta2 import ClientBuilder

        # Discover token endpoint
        discovery = fetch_oidc_discovery(issuer_url)

        # Create credentials
        creds = OAuth2ClientCredentials(
            client_id="...",
            client_secret="...",
            token_endpoint=discovery.token_endpoint
        )

        # Create call credentials
        call_creds = oauth2_call_credentials(creds)

        # Build authenticated client
        client = (
            ClientBuilder(target)
            .oauth2_client_authenticated(call_creds)
            .build()
        )
    """
    # Return the OAuth2ClientCredentials directly.
    # ClientBuilder.oauth2_client_authenticated() will handle it appropriately
    # for the underlying transport (via interceptors in Connect-Python).
    return credentials


# Channel Credentials Abstraction
# ================================
# Transport-agnostic credential types for secure RPC connections.
# Works across different RPC implementations.


class ChannelCredentials:
    """
    Channel credentials for secure RPC connections.

    Configures TLS/SSL settings including custom CA certificates and mutual TLS (mTLS).
    Use factory methods to create instances:
    - ssl_channel_credentials() for TLS with optional custom certificates
    - insecure_channel_credentials() for plaintext (testing only)
    - local_channel_credentials() for local connections
    """

    def __init__(
        self,
        root_certificates: bytes = None,
        private_key: bytes = None,
        certificate_chain: bytes = None,
        include_system_certs: bool = True,
    ):
        """
        Create channel credentials.

        Args:
            root_certificates: PEM-encoded CA certificate(s) for server verification
            private_key: PEM-encoded private key for mutual TLS
            certificate_chain: PEM-encoded client certificate chain for mutual TLS
            include_system_certs: Whether to include system CA bundle (default: True)

        Note:
            For mTLS, both private_key and certificate_chain must be provided together.
        """
        self.root_certificates = root_certificates
        self.private_key = private_key
        self.certificate_chain = certificate_chain
        self.include_system_certs = include_system_certs
        self._insecure = False

        # Validate mTLS configuration
        if (private_key is None) != (certificate_chain is None):
            raise ValueError(
                "Both private_key and certificate_chain must be provided together for mTLS"
            )

    def is_secure(self) -> bool:
        """
        Check if these credentials provide TLS security.

        Returns:
            True if TLS is enabled, False for insecure/plaintext
        """
        return not self._insecure

    def __repr__(self):
        parts = []
        if self._insecure:
            parts.append("insecure")
        else:
            parts.append("TLS")
            if self.root_certificates:
                parts.append("custom-CA")
            if self.private_key and self.certificate_chain:
                parts.append("mTLS")
        return f"<ChannelCredentials: {', '.join(parts)}>"


class InsecureChannelCredentials(ChannelCredentials):
    """
    Insecure channel credentials (plaintext, no TLS).

    For testing only. Production should use ssl_channel_credentials().
    """

    def __init__(self):
        super().__init__()
        self._insecure = True

    def is_secure(self) -> bool:
        return False


def ssl_channel_credentials(
    root_certificates: bytes = None,
    private_key: bytes = None,
    certificate_chain: bytes = None
) -> ChannelCredentials:
    """
    Create SSL/TLS channel credentials.

    Supports custom CA certificates and mutual TLS (mTLS) for secure RPC connections.

    Args:
        root_certificates: PEM-encoded root certificate(s) as bytes for custom CA.
            If None, uses system CA bundle. Can be a single cert or bundle.
        private_key: PEM-encoded private key as bytes for client authentication (mTLS).
            Must be provided with certificate_chain.
        certificate_chain: PEM-encoded client certificate chain as bytes for mTLS.
            Must be provided with private_key.

    Returns:
        ChannelCredentials object configured for TLS

    Raises:
        ValueError: If only one of private_key/certificate_chain is provided

    Examples:
        # Default TLS (system CA bundle)
        from kessel.grpc import ssl_channel_credentials
        creds = ssl_channel_credentials()

        # Custom CA certificate
        with open("ca.pem", "rb") as f:
            ca_cert = f.read()
        creds = ssl_channel_credentials(root_certificates=ca_cert)

        # Mutual TLS (client certificate authentication)
        with open("ca.pem", "rb") as f:
            ca_cert = f.read()
        with open("client-key.pem", "rb") as f:
            key = f.read()
        with open("client-cert.pem", "rb") as f:
            cert = f.read()
        creds = ssl_channel_credentials(
            root_certificates=ca_cert,
            private_key=key,
            certificate_chain=cert
        )

        # Use with ClientBuilder
        from kessel.inventory.v1beta2 import ClientBuilder
        stub, channel = (
            ClientBuilder(target)
            .oauth2_client_authenticated(auth_creds, creds)
            .build()
        )
    """
    return ChannelCredentials(
        root_certificates=root_certificates,
        private_key=private_key,
        certificate_chain=certificate_chain,
        include_system_certs=True,
    )


def local_channel_credentials(local_connect=None) -> ChannelCredentials:
    """
    Create credentials for local connections.

    Returns default TLS credentials suitable for local services.

    Args:
        local_connect: Reserved for future use

    Returns:
        ChannelCredentials configured for TLS

    Example:
        from kessel.grpc import local_channel_credentials
        creds = local_channel_credentials()
        client = (
            ClientBuilder("localhost:9000")
            .oauth2_client_authenticated(auth_creds, creds)
            .build()
        )
    """
    return ChannelCredentials()


def insecure_channel_credentials() -> InsecureChannelCredentials:
    """
    Create credentials for insecure (plaintext) connections.

    For testing only. Disables all TLS.

    Returns:
        InsecureChannelCredentials (plaintext)

    Note:
        Using ClientBuilder.insecure() is preferred over this function:

        # Preferred:
        ClientBuilder(target).insecure().build()

        # Also works:
        ClientBuilder(target).unauthenticated(insecure_channel_credentials()).build()

    Example:
        from kessel.grpc import insecure_channel_credentials

        # Testing only - plaintext connection
        creds = insecure_channel_credentials()
        client = (
            ClientBuilder("localhost:9000")
            .unauthenticated(creds)
            .build()
        )
    """
    return InsecureChannelCredentials()
