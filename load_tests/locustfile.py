"""Locust load test for the production ML service.

Headless run:
    locust -f load_tests/locustfile.py ^
      --headless -u 50 -r 5 -t 60s ^
      --host http://localhost:8000 ^
      --csv=results/load_test ^
      --html=results/load_test.html
"""

from locust import HttpUser, between, task


class MLServiceUser(HttpUser):
    """Simulates a user hitting the ML service endpoints."""

    wait_time = between(0.1, 0.5)

    @task(5)
    def recommendations(self):
        self.client.get("/api/recommendations?query=running+shoes&top_k=5")

    @task(3)
    def conversation(self):
        self.client.post(
            "/api/conversation",
            json={"message": "recommend shoes under 1000"},
        )

    @task(2)
    def description(self):
        self.client.get("/api/description?product_id=prod001")

    @task(1)
    def health(self):
        self.client.get("/health")

    @task(1)
    def ready(self):
        self.client.get("/ready")
