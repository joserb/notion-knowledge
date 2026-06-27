"""Rate-limited Notion API client with automatic pagination.

Uses notion-client v3 SDK. Since v3 removed databases.query(), we use
client.request() for raw API calls with Notion-Version 2022-06-28 to
ensure full property schemas are returned.
"""

from __future__ import annotations

import threading
import time

from notion_client import Client


# Use older API version that returns full properties in database responses
NOTION_VERSION = "2022-06-28"

# Notion's documented average is ~3 requests per second. 0.34s between
# request *starts* keeps us safely under that ceiling even with
# concurrent workers sharing this client.
DEFAULT_MIN_INTERVAL = 0.34


class RateLimitedNotionClient:
    """Wrapper around the Notion SDK with rate limiting and pagination.

    The rate limiter is **thread-safe**: multiple workers can share a
    single client instance and the limiter will serialize the *start* of
    each request to the configured minimum interval, while the actual
    HTTP requests still run concurrently.
    """

    def __init__(self, token: str, min_interval: float = DEFAULT_MIN_INTERVAL):
        self._client = Client(auth=token, notion_version=NOTION_VERSION)
        self._min_interval = min_interval
        self._last_request_time = 0.0
        self._wait_lock = threading.Lock()

    def _wait(self) -> None:
        """Enforce minimum interval between API requests (thread-safe)."""
        with self._wait_lock:
            now = time.monotonic()
            elapsed = now - self._last_request_time
            if elapsed < self._min_interval:
                time.sleep(self._min_interval - elapsed)
            self._last_request_time = time.monotonic()

    def get_me(self) -> dict:
        self._wait()
        return self._client.users.me()

    def get_database(self, database_id: str) -> dict:
        self._wait()
        return self._client.databases.retrieve(database_id=database_id)

    def query_database(
        self,
        database_id: str,
        *,
        paginate: bool = True,
        **kwargs,
    ) -> list[dict]:
        """Query a database. Auto-paginates by default; pass ``paginate=False``
        to fetch only the first page (useful for connectivity checks or for
        small databases where one page is enough)."""
        all_results: list[dict] = []
        start_cursor = None

        while True:
            self._wait()
            body = {**kwargs}
            if start_cursor:
                body["start_cursor"] = start_cursor

            response = self._client.request(
                path=f"databases/{database_id}/query",
                method="POST",
                body=body,
            )
            all_results.extend(response.get("results", []))

            if not paginate or not response.get("has_more"):
                break
            start_cursor = response.get("next_cursor")

        return all_results

    def get_block_children(self, block_id: str) -> list[dict]:
        """Get all children of a block with automatic pagination."""
        all_blocks: list[dict] = []
        start_cursor = None

        while True:
            self._wait()
            kwargs = {}
            if start_cursor:
                kwargs["start_cursor"] = start_cursor

            response = self._client.blocks.children.list(
                block_id=block_id,
                **kwargs,
            )
            all_blocks.extend(response.get("results", []))

            if not response.get("has_more"):
                break
            start_cursor = response.get("next_cursor")

        return all_blocks

    def get_all_blocks_recursive(self, block_id: str) -> list[dict]:
        """Get all blocks for a page recursively, expanding children."""
        blocks = self.get_block_children(block_id)

        for block in blocks:
            if block.get("has_children"):
                block["_children"] = self.get_all_blocks_recursive(block["id"])

        return blocks
