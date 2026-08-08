"""Base class for singleton client managers with a unified async lifecycle."""

import asyncio
from typing import Any, ClassVar, Self, cast


class ClientManager[T]:
    """Base singleton with async initialize() / close() lifecycle.

    Subclasses must override ``_create_client`` and, if the underlying
    resource needs explicit teardown, ``_close_client``.
    """

    _instance: ClassVar[Any] = None
    _client: T | None
    _lock: asyncio.Lock

    def __new__(cls) -> Self:
        # Check cls.__dict__ (not cls._instance) so each subclass gets its
        # own singleton instead of inheriting one from a parent class.
        if cls.__dict__.get("_instance") is None:
            instance = super().__new__(cls)
            instance._client = None
            instance._lock = asyncio.Lock()
            cls._instance = instance
        return cast(Self, cls._instance)

    @property
    def name(self) -> str:
        return self.__class__.__name__

    @property
    def client(self) -> T:
        if self._client is None:
            raise RuntimeError(
                f"{self.name} not initialized. Call 'await manager.initialize()' first."
            )
        return self._client

    async def initialize(self) -> None:
        async with self._lock:
            if self._client is None:
                self._client = await self._create_client()

    async def _create_client(self) -> T:
        raise NotImplementedError

    async def close(self) -> None:
        async with self._lock:
            if self._client is None:
                return
            try:
                await self._close_client()
            finally:
                self._client = None

    async def _close_client(self) -> None:
        """Override to perform cleanup. Default is a no-op."""
