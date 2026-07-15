"""
Connect-Python client wrapper for exception compatibility.

Wraps ConnectError exceptions as RpcError to maintain API compatibility
across transport implementations.
"""

import functools
from connectrpc.errors import ConnectError
from kessel.grpc import RpcError


class StubWrapper:
    """
    Minimal wrapper to convert ConnectError to RpcError.

    This wrapper exists to maintain API compatibility by:
    1. Wrapping ConnectError exceptions as RpcError
    2. Proxying context manager support from underlying Connect client
    3. Proxying all method calls directly to Connect client (snake_case per Python conventions)

    Example:
        client = ClientBuilder(...).build()
        with client:  # Context manager support
            response = client.check(request)  # snake_case per Python/spec conventions

        try:
            client.check(request)
        except RpcError as e:  # Wrapped ConnectError
            print(e.code(), e.details())
    """

    def __init__(self, connect_client):
        """
        Initialize wrapper with Connect client.

        Args:
            connect_client: Connect-Python client instance with context manager support
        """
        self._client = connect_client

    def __enter__(self):
        """Enter context manager - delegates to Connect client."""
        self._client.__enter__()
        return self

    def __exit__(self, *args):
        """Exit context manager - delegates to Connect client."""
        return self._client.__exit__(*args)

    def __getattr__(self, name: str):
        """
        Proxy method calls to underlying Connect client with exception wrapping.

        Args:
            name: Method name (snake_case per Python conventions)

        Returns:
            Wrapped method that converts ConnectError to RpcError

        Raises:
            AttributeError: If the method doesn't exist on Connect client
        """
        # Check if Connect client has this method
        if not hasattr(self._client, name):
            raise AttributeError(
                f"'{type(self._client).__name__}' has no method '{name}'"
            )

        # Get the method and wrap it to convert exceptions
        method = getattr(self._client, name)
        return self._wrap_method(method)

    @staticmethod
    def _wrap_method(method):
        """
        Wrap a Connect client method to convert ConnectError to RpcError.

        Args:
            method: Connect client method (sync)

        Returns:
            Wrapped method that raises RpcError instead of ConnectError
        """

        @functools.wraps(method)
        def wrapped(*args, **kwargs):
            try:
                return method(*args, **kwargs)
            except ConnectError as e:
                raise RpcError(e) from e

        return wrapped


class AsyncStubWrapper:
    """
    Minimal async wrapper to convert ConnectError to RpcError.

    Same as StubWrapper but for async clients. Wraps ConnectError as RpcError
    and proxies async context manager support.

    Example:
        client = ClientBuilder(...).build_async()
        async with client:  # Async context manager support
            response = await client.check(request)  # snake_case per Python/spec conventions
    """

    def __init__(self, connect_client):
        """
        Initialize wrapper with Connect async client.

        Args:
            connect_client: Connect-Python async client instance with async context manager support
        """
        self._client = connect_client

    async def __aenter__(self):
        """Enter async context manager - delegates to Connect client."""
        await self._client.__aenter__()
        return self

    async def __aexit__(self, *args):
        """Exit async context manager - delegates to Connect client."""
        return await self._client.__aexit__(*args)

    def __getattr__(self, name: str):
        """
        Proxy async method calls to underlying Connect client with exception wrapping.

        Args:
            name: Method name (snake_case per Python conventions)

        Returns:
            Wrapped async method that converts ConnectError to RpcError

        Raises:
            AttributeError: If the method doesn't exist on Connect client
        """
        if not hasattr(self._client, name):
            raise AttributeError(
                f"'{type(self._client).__name__}' has no method '{name}'"
            )

        # Get the method and wrap it to convert exceptions
        method = getattr(self._client, name)
        return self._wrap_async_method(method)

    @staticmethod
    def _wrap_async_method(method):
        """
        Wrap an async Connect client method to convert ConnectError to RpcError.

        Args:
            method: Connect client method (async)

        Returns:
            Wrapped async method that raises RpcError instead of ConnectError
        """

        @functools.wraps(method)
        async def wrapped(*args, **kwargs):
            try:
                return await method(*args, **kwargs)
            except ConnectError as e:
                raise RpcError(e) from e

        return wrapped
