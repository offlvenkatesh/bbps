from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_live():
    response = client.get("/health/live")

    assert response.status_code == 200


def test_fetch():
    response = client.post("/v1/fetch", json={
        "fetch_reference": "fetch-10001",
        "biller_id": "biller-electricity-demo",
        "customer_params": {
            "consumer_number": "consumer-501"
        }
    })

    assert response.status_code == 200
    assert "transaction_id" in response.json()
    assert response.json()["transaction_id"]
    assert response.json()["fetch_reference"] == "fetch-10001"
    assert response.json()["bill"]["amount_due"] == 12500


def test_payment():
    fetch_response = client.post("/v1/fetch", json={
        "fetch_reference": "fetch-10002",
        "biller_id": "biller-electricity-demo",
        "customer_params": {
            "consumer_number": "consumer-501"
        }
    })

    assert fetch_response.status_code == 200

    transaction_id = fetch_response.json()["transaction_id"]

    payment_response = client.post("/v1/payment", json={
        "transaction_id": transaction_id,
        "client_reference": "fetch-10002",
        "payment": {
            "mode": "UPI",
            "amount": 12500,
            "currency": "INR"
        }
    })

    assert payment_response.status_code == 200
    assert "transaction_id" in payment_response.json()
    assert payment_response.json()["transaction_id"] == transaction_id
    assert "provider_reference" in payment_response.json()
    assert payment_response.json()["provider_reference"]
    assert payment_response.json()["status"] == "success"


def test_transaction_id():
    fetch_response = client.post("/v1/fetch", json={
        "fetch_reference": "fetch-10003",
        "biller_id": "biller-electricity-demo",
        "customer_params": {
            "consumer_number": "consumer-501"
        }
    })

    assert fetch_response.status_code == 200

    transaction_id = fetch_response.json()["transaction_id"]

    transaction_response = client.get(
        f"/v1/transactions/{transaction_id}"
    )

    assert transaction_response.status_code == 200
    assert transaction_response.json()["transaction_id"] == transaction_id


def test_invalid_transaction_id():
    response = client.get("/v1/transactions/99999")

    assert response.status_code == 404


def test_invalid_fetch():
    response = client.post("/v1/fetch", json={
        "fetch_reference": "fetch-invalid",
        "biller_id": "biller-electricity-demo",
        "customer_params": {
            "consumer_number": "wrong-consumer"
        }
    })

    assert response.status_code == 404


def test_invalid_payment_amount():
    fetch_response = client.post("/v1/fetch", json={
        "fetch_reference": "fetch-invalid-payment",
        "biller_id": "biller-electricity-demo",
        "customer_params": {
            "consumer_number": "consumer-501"
        }
    })

    assert fetch_response.status_code == 200

    transaction_id = fetch_response.json()["transaction_id"]

    payment_response = client.post("/v1/payment", json={
        "transaction_id": transaction_id,
        "client_reference": "fetch-invalid-payment",
        "payment": {
            "mode": "UPI",
            "amount": 10000,
            "currency": "INR"
        }
    })

    assert payment_response.status_code == 400


def test_payment_already_paid():
    fetch_response = client.post("/v1/fetch", json={
        "fetch_reference": "fetch-already-paid",
        "biller_id": "biller-electricity-demo",
        "customer_params": {
            "consumer_number": "consumer-501"
        }
    })

    assert fetch_response.status_code == 200

    transaction_id = fetch_response.json()["transaction_id"]

    payment_data = {
        "transaction_id": transaction_id,
        "client_reference": "fetch-already-paid",
        "payment": {
            "mode": "UPI",
            "amount": 12500,
            "currency": "INR"
        }
    }

    first_payment = client.post(
        "/v1/payment",
        json=payment_data
    )

    assert first_payment.status_code == 200

    second_payment = client.post(
        "/v1/payment",
        json=payment_data
    )

    assert second_payment.status_code == 400

