from fastapi.testclient import TestClient

from customer_service.main import create_app
from customer_service.models import Customer


def test_list_customers_includes_status_values() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/customers")

    assert response.status_code == 200
    customers = response.json()
    assert len(customers) == 3
    assert customers[0] == {"id": 1, "name": "Ava Patel", "status": "active"}
    assert customers[1]["status"] == "suspended"


def test_get_customer_returns_customer_with_default_active_status() -> None:
    app = create_app(customers=[Customer(id=8, name="Jordan Lee")])

    with TestClient(app) as client:
        response = client.get("/customers/8")

    assert response.status_code == 200
    assert response.json() == {
        "id": 8,
        "name": "Jordan Lee",
        "status": "active",
    }


def test_get_customer_returns_explicit_suspended_status() -> None:
    app = create_app(customers=[Customer(id=9, name="Morgan Diaz", status="suspended")])

    with TestClient(app) as client:
        response = client.get("/customers/9")

    assert response.status_code == 200
    assert response.json()["status"] == "suspended"


def test_get_unknown_customer_returns_404() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/customers/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Customer not found"}
