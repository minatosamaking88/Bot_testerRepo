import httpx
from fastapi.testclient import TestClient

from order_service.main import create_app


def make_customer_transport(
    status_code: int = 200,
    customer: dict[str, object] | None = None,
) -> httpx.MockTransport:
    response_body = customer or {
        "id": 1,
        "name": "Ava Patel",
        "status": "active",
    }

    def handle_request(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/customers/1"
        return httpx.Response(status_code, json=response_body)

    return httpx.MockTransport(handle_request)


def test_create_and_get_order_calls_customer_service_over_http() -> None:
    requested_paths: list[str] = []

    def handle_request(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        return httpx.Response(
            200,
            json={
                "id": 1,
                "name": "Ava Patel",
                "status": "active",
            },
        )

    app = create_app(
        customer_service_url="http://customer-service",
        customer_transport=httpx.MockTransport(handle_request),
    )

    with TestClient(app) as client:
        created = client.post("/orders", json={"customer_id": 1})
        order_id = created.json()["id"]
        fetched = client.get(f"/orders/{order_id}")

    assert created.status_code == 201
    assert created.json() == {
        "id": order_id,
        "customer_id": 1,
        "customer_name": "Ava Patel",
    }
    assert fetched.status_code == 200
    assert fetched.json() == created.json()
    assert requested_paths == ["/customers/1", "/customers/1"]


def test_suspended_customer_cannot_create_order() -> None:
    app = create_app(
        customer_transport=make_customer_transport(
            customer={
                "id": 1,
                "name": "Ava Patel",
                "status": "suspended",
            }
        )
    )

    with TestClient(app) as client:
        response = client.post("/orders", json={"customer_id": 1})

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Orders cannot be created for suspended customers"
    }
    assert app.state.orders == {}


def test_missing_customer_cannot_create_order() -> None:
    app = create_app(customer_transport=make_customer_transport(status_code=404))

    with TestClient(app) as client:
        response = client.post("/orders", json={"customer_id": 1})

    assert response.status_code == 404
    assert response.json() == {"detail": "Customer not found"}
    assert app.state.orders == {}


def test_legacy_customer_without_status_can_create_and_fetch_order() -> None:
    app = create_app(
        customer_transport=make_customer_transport(
            customer={"id": 1, "name": "Ava Patel"}
        )
    )

    with TestClient(app) as client:
        created = client.post("/orders", json={"customer_id": 1})
        fetched = client.get(f"/orders/{created.json()['id']}")

    assert created.status_code == 201
    assert created.json()["customer_name"] == "Ava Patel"
    assert fetched.status_code == 200
    assert fetched.json()["customer_name"] == "Ava Patel"


def test_customer_service_failure_returns_503_without_storing_order() -> None:
    app = create_app(customer_transport=make_customer_transport(status_code=500))

    with TestClient(app) as client:
        response = client.post("/orders", json={"customer_id": 1})

    assert response.status_code == 503
    assert response.json() == {"detail": "Customer service unavailable"}
    assert app.state.orders == {}


def test_invalid_customer_id_is_rejected() -> None:
    with TestClient(create_app()) as client:
        response = client.post("/orders", json={"customer_id": 0})

    assert response.status_code == 422


def test_get_unknown_order_returns_404() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/orders/unknown")

    assert response.status_code == 404
    assert response.json() == {"detail": "Order not found"}
