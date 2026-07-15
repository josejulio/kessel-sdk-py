"""
ClientBuilder for Kessel SDK.

Provides a fluent builder API for creating authenticated RPC clients
with support for OAuth2, custom TLS, and various connection modes.
"""

from typing import Self, TYPE_CHECKING

if TYPE_CHECKING:
    from kessel.auth import OAuth2ClientCredentials

from connectrpc.protocol import ProtocolType
from connectrpc.interceptor import (
    UnaryInterceptorSync,
    UnaryInterceptor,
)

from kessel.inventory.connect_wrapper import (
    StubWrapper,
    AsyncStubWrapper,
)
from kessel.inventory.v1beta2.inventory_service_connect import (
    KesselInventoryServiceClientSync,
    KesselInventoryServiceClient,
)


class OAuth2Interceptor(UnaryInterceptorSync):
    """
    Synchronous interceptor that adds OAuth2 Bearer token to request headers.
    """

    def __init__(self, credentials: "OAuth2ClientCredentials"):
        """
        Initialize interceptor with OAuth2 credentials.

        Args:
            credentials: OAuth2ClientCredentials instance
        """
        self._credentials = credentials

    def intercept_unary_sync(self, next_handler, request, ctx):
        """Add OAuth2 bearer token to unary request."""
        # Get fresh token
        token_response = self._credentials.get_token()

        ctx.request_headers()["authorization"] = f"Bearer {token_response.access_token}"
        return next_handler(request, ctx)


class AsyncOAuth2Interceptor(UnaryInterceptor):
    """
    Asynchronous interceptor that adds OAuth2 Bearer token to request headers.
    """

    def __init__(self, credentials: "OAuth2ClientCredentials"):
        """
        Initialize interceptor with OAuth2 credentials.

        Args:
            credentials: OAuth2ClientCredentials instance
        """
        self._credentials = credentials

    async def intercept_unary(self, next_handler, request, ctx):
        """Add OAuth2 bearer token to async unary request."""
        # Get fresh token
        token_response = (
            self._credentials.get_token()
        )  # TODO: Check if there is an async version of this

        # Add to headers
        ctx.request_headers()["authorization"] = f"Bearer {token_response.access_token}"

        return await next_handler(request, ctx)


class ClientBuilder:
    """
    Fluent builder for creating authenticated RPC clients.

    Provides a simple API for configuring authentication, TLS, and connection options
    for Kessel service clients.

    Example:
        # Insecure connection
        client = ClientBuilder("localhost:9000").insecure().build()

        # OAuth2 authenticated
        client = ClientBuilder("localhost:9000")
            .oauth2_client_authenticated(credentials)
            .build()

        # Async client
        stub, channel = ClientBuilder("localhost:9000").insecure().build_async()
    """

    def __init__(self, target: str):
        """
        Initialize ClientBuilder with target endpoint.

        Args:
            target: Server address (e.g., "localhost:9000")

        Raises:
            TypeError: If target is not a string
        """
        self._target = target
        self._oauth2_credentials = None
        self._insecure = False
        self._call_credentials = None
        self._channel_credentials = None

        if not self._target or type(self._target) is not str:
            raise TypeError("Invalid target type")

    def oauth2_client_authenticated(
        self,
        oauth2_client_credentials: "OAuth2ClientCredentials",
        channel_credentials=None,
    ) -> Self:
        """
        Configure OAuth2 client credentials authentication.

        Args:
            oauth2_client_credentials: OAuth2 credentials instance
            channel_credentials: Optional TLS/channel credentials. If provided (even as
                a sentinel value), TLS will be used. Pass None to use default TLS behavior
                (secure by default). Use .insecure() for plaintext connections.

        Returns:
            Self for method chaining

        Example:
            # Default TLS (secure)
            .oauth2_client_authenticated(creds)

            # Explicit TLS with ChannelCredentials (cross-compatible)
            import grpc
            .oauth2_client_authenticated(creds, grpc.ssl_channel_credentials())

            # For plaintext (testing only)
            .oauth2_client_authenticated(creds).insecure()
        """
        self._oauth2_credentials = oauth2_client_credentials
        self._channel_credentials = channel_credentials
        self._insecure = False
        return self

    def authenticated(self, call_credentials=None, channel_credentials=None) -> Self:
        """
        Configure generic authentication.

        Note: With Connect-Python (v3.0+), call_credentials must be OAuth2ClientCredentials
        returned from kessel.grpc.oauth2_call_credentials(). For other credential types,
        use the transport-specific authentication mechanisms.

        Args:
            call_credentials: OAuth2ClientCredentials from oauth2_call_credentials()
            channel_credentials: Optional TLS/channel credentials. If provided (even as
                a sentinel value), TLS will be used. Accepts ChannelCredentials objects
                for cross-SDK compatibility.

        Returns:
            Self for method chaining

        Raises:
            TypeError: If call_credentials is not None and not OAuth2ClientCredentials

        Example:
            from kessel.auth import OAuth2ClientCredentials
            from kessel.grpc import oauth2_call_credentials
            import grpc  # Optional, for explicit TLS

            creds = OAuth2ClientCredentials(...)
            call_creds = oauth2_call_credentials(creds)

            # With default TLS
            client = (
                ClientBuilder(target)
                .authenticated(call_credentials=call_creds)
                .build()
            )

            # With explicit TLS (transport-agnostic)
            client = (
                ClientBuilder(target)
                .authenticated(
                    call_credentials=call_creds,
                    channel_credentials=grpc.ssl_channel_credentials()
                )
                .build()
            )
        """
        if call_credentials is not None:
            # Check if it's OAuth2ClientCredentials (which oauth2_call_credentials returns)
            from kessel.auth.auth import OAuth2ClientCredentials

            if not isinstance(call_credentials, OAuth2ClientCredentials):
                raise TypeError(
                    "call_credentials must be OAuth2ClientCredentials from "
                    "kessel.grpc.oauth2_call_credentials(). "
                    f"Got: {type(call_credentials).__name__}"
                )
            # Store as OAuth2 credentials for interceptor creation
            self._oauth2_credentials = call_credentials
            self._call_credentials = None  # Not using call credentials
        else:
            self._call_credentials = None
            self._oauth2_credentials = None

        self._channel_credentials = channel_credentials
        self._insecure = False
        return self

    def unauthenticated(self, channel_credentials=None) -> Self:
        """
        Configure unauthenticated connection (server auth only, no client credentials).

        Args:
            channel_credentials: Optional TLS/channel credentials. If provided, TLS will
                be used for the connection. Accepts ChannelCredentials objects for
                cross-SDK compatibility. Pass None to use default TLS behavior.

        Returns:
            Self for method chaining

        Example:
            # Default TLS, no client auth
            .unauthenticated()

            # Explicit TLS with ChannelCredentials
            import grpc
            .unauthenticated(grpc.ssl_channel_credentials())

            # Plaintext (testing only)
            .unauthenticated().insecure()
        """
        self._call_credentials = None
        self._oauth2_credentials = None
        self._channel_credentials = channel_credentials
        return self

    def insecure(self) -> Self:
        """
        Configure insecure (HTTP) connection.

        Returns:
            Self for method chaining
        """
        self._insecure = True
        self._call_credentials = None
        self._oauth2_credentials = None
        self._channel_credentials = None
        return self

    def _should_use_tls(self) -> bool:
        """
        Determine whether to use TLS based on configuration.

        Returns True (use HTTPS/TLS) if:
        - Not explicitly insecure, AND
        - channel_credentials is secure (or None, which defaults to secure)

        This matches SDK spec behavior where channel_credentials control TLS.
        """
        if self._insecure:
            return False

        # Check if credentials explicitly mark insecure
        if self._channel_credentials is not None:
            # If it's a ChannelCredentials object, check is_secure()
            if hasattr(self._channel_credentials, "is_secure"):
                return self._channel_credentials.is_secure()
            # If it's another credential object, assume secure
            return True

        # Default to TLS (secure by default)
        return True

    def _configure_tls(self, http_transport_class, http_version):
        """
        Configure TLS for pyqwest HTTPTransport.

        Args:
            http_transport_class: SyncHTTPTransport or HTTPTransport class
            http_version: HTTPVersion to use

        Returns:
            Configured transport instance with TLS settings
        """
        from kessel.grpc import ChannelCredentials

        # Extract TLS config from channel_credentials if it's a ChannelCredentials object
        tls_config = {}
        if isinstance(self._channel_credentials, ChannelCredentials):
            if self._channel_credentials.root_certificates:
                tls_config["tls_ca_cert"] = self._channel_credentials.root_certificates
            if self._channel_credentials.private_key:
                tls_config["tls_key"] = self._channel_credentials.private_key
            if self._channel_credentials.certificate_chain:
                tls_config["tls_cert"] = self._channel_credentials.certificate_chain
            tls_config["tls_include_system_certs"] = self._channel_credentials.include_system_certs

        # Create transport with TLS config
        return http_transport_class(http_version=http_version, **tls_config)

    def build(self):
        """
        Build synchronous client.

        Returns:
            StubWrapper providing transport-agnostic API with context manager support.
            The client supports `with` statement for automatic resource cleanup.

        Example:
            client = ClientBuilder("localhost:9000").insecure().build()
            with client:
                response = client.Check(request)
        """
        # Determine address with protocol based on TLS configuration
        use_tls = self._should_use_tls()
        protocol_scheme = "https" if use_tls else "http"
        address = f"{protocol_scheme}://{self._target}"

        # Build interceptors list
        interceptors = []
        if self._oauth2_credentials:
            interceptors.append(OAuth2Interceptor(self._oauth2_credentials))

        # Create Connect client using gRPC protocol
        # Configure HTTP/2 transport for gRPC compatibility with TLS settings
        # See: https://connectrpc.com/docs/python/grpc-compatibility
        from pyqwest import SyncClient, SyncHTTPTransport, HTTPVersion

        http2_transport = self._configure_tls(SyncHTTPTransport, HTTPVersion.HTTP2)
        http_client = SyncClient(transport=http2_transport)

        connect_client = KesselInventoryServiceClientSync(
            address=address,
            protocol=ProtocolType.GRPC,  # Use gRPC protocol
            http_client=http_client,
            send_compression=None,  # Send uncompressed (server will indicate support via headers)
            interceptors=tuple(interceptors) if interceptors else (),
        )

        # Wrap for exception handling API
        # Connect clients support context managers natively, so we only wrap
        # for exception conversion and method name compatibility
        stub = StubWrapper(connect_client)

        return stub

    def build_async(self):
        """
        Build asynchronous client.

        Returns:
            AsyncStubWrapper providing async API with async context manager support.
            The client supports `async with` statement for automatic resource cleanup.

        Example:
            client = ClientBuilder("localhost:9000").insecure().build_async()
            async with client:
                response = await client.Check(request)
        """
        # Determine address with protocol based on TLS configuration
        use_tls = self._should_use_tls()
        protocol_scheme = "https" if use_tls else "http"
        address = f"{protocol_scheme}://{self._target}"

        # Build interceptors list
        interceptors = []
        if self._oauth2_credentials:
            interceptors.append(AsyncOAuth2Interceptor(self._oauth2_credentials))

        # Create Connect async client using gRPC protocol
        # Configure HTTP/2 transport for gRPC compatibility with TLS settings
        # See: https://connectrpc.com/docs/python/grpc-compatibility
        from pyqwest import Client, HTTPTransport, HTTPVersion

        http2_transport = self._configure_tls(HTTPTransport, HTTPVersion.HTTP2)
        http_client = Client(transport=http2_transport)

        connect_client = KesselInventoryServiceClient(
            address=address,
            protocol=ProtocolType.GRPC,  # Use gRPC protocol
            http_client=http_client,
            send_compression=None,  # Send uncompressed (server will indicate support via headers)
            interceptors=tuple(interceptors) if interceptors else (),
        )

        # Wrap for exception handling.aio API
        # Connect clients support async context managers natively, so we only wrap
        # for exception conversion and method name compatibility
        stub = AsyncStubWrapper(connect_client)

        return stub
