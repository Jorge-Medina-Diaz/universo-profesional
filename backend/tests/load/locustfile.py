"""Load tests: Locust scenarios for production readiness validation.

Run locally:
    cd backend && uv run locust -f tests/load/locustfile.py --host http://localhost:8000

Required env:
    LOAD_TEST_EMAIL_PREFIX  # e.g. loadtest
    LOAD_TEST_PASSWORD      # e.g. SecurePass123!
"""
from __future__ import annotations

import os
from typing import ClassVar

from locust import HttpUser, TaskSet, between, task


class AuthFlowTasks(TaskSet):
    def on_start(self) -> None:
        self.email = f"{os.getenv('LOAD_TEST_EMAIL_PREFIX', 'loadtest')}_{self.user.id}@test.local"
        self.password = os.getenv("LOAD_TEST_PASSWORD", "S3cur3-Passw0rd!")
        self.access_token: str | None = None
        self._register_and_login()

    def _register_and_login(self) -> None:
        # Register
        with self.client.post(
            "/api/v1/auth/register",
            json={
                "email": self.email,
                "password": self.password,
                "display_name": "Load Tester",
                "locale": "es-ES",
            },
            catch_response=True,
        ) as resp:
            if resp.status_code == 201:
                data = resp.json()
                self.verification_link = data.get("verification_link", "")
            else:
                resp.failure(f"register failed: {resp.text}")
                return

        # Verify (extract token from link)
        import re

        m = re.search(r"token=([\w-]+)", self.verification_link)
        token = m.group(1) if m else ""
        with self.client.post("/api/v1/auth/verify", json={"token": token}, catch_response=True) as resp:
            if resp.status_code != 200:
                resp.failure(f"verify failed: {resp.text}")

        # Login
        with self.client.post(
            "/api/v1/auth/login",
            json={"email": self.email, "password": self.password},
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                self.access_token = resp.json()["access_token"]
            else:
                resp.failure(f"login failed: {resp.text}")

    @task(3)
    def fetch_universe(self) -> None:
        if not self.access_token:
            return
        self.client.get(
            "/api/v1/universe/summary",
            headers={"Authorization": f"Bearer {self.access_token}"},
        )

    @task(1)
    def generate_cv(self) -> None:
        if not self.access_token:
            return
        self.client.post(
            "/api/v1/documents/generate-cv",
            json={
                "job_description": "Senior Python developer with FastAPI experience",
                "template": "ats-classic",
                "language": "es",
            },
            headers={"Authorization": f"Bearer {self.access_token}"},
        )


class NormalUser(HttpUser):
    tasks: ClassVar[list] = [AuthFlowTasks]
    wait_time = between(1, 3)


class SpikeUser(HttpUser):
    """Higher throughput variant for stress testing."""

    tasks: ClassVar[list] = [AuthFlowTasks]
    wait_time = between(0.1, 0.5)
