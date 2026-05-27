"""Unit tests for shared/redis helpers (no DB)."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from src.shared.redis import dispose_redis, get_redis


class TestRedis:
    def test_get_redis_singleton(self):
        with patch("src.shared.redis._redis_client", None):
            with patch("src.shared.redis.Redis") as mock_redis:
                with patch("src.shared.redis.get_settings") as mock_settings:
                    mock_settings.return_value = type("S", (), {"redis_url": "redis://localhost"})()
                    r1 = get_redis()
                    r2 = get_redis()
                    assert r1 is r2
                    mock_redis.from_url.assert_called_once()

    async def test_dispose_redis(self):
        with patch("src.shared.redis._redis_client") as mock_client:
            mock_client.aclose = AsyncMock()
            await dispose_redis()
            mock_client.aclose.assert_awaited_once()
