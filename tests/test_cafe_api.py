import pytest

from cafe_api import create_app


@pytest.fixture()
def client(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "cafes.sqlite"), "API_KEY": "test-key"})
    return app.test_client()


def headers():
    return {"X-API-Key": "test-key"}


def sample_cafe():
    return {"name": "Desk & Bean", "location": "London", "has_wifi": True, "has_sockets": True, "coffee_price": 3.4}


def test_mutation_needs_api_key(client):
    response = client.post("/api/cafes", json=sample_cafe())
    assert response.status_code == 401


def test_create_list_and_search(client):
    created = client.post("/api/cafes", headers=headers(), json=sample_cafe())
    assert created.status_code == 201
    assert created.get_json()["cafe"]["has_wifi"] is True
    assert len(client.get("/api/cafes").get_json()["cafes"]) == 1
    assert len(client.get("/api/cafes/search?location=lond").get_json()["cafes"]) == 1


def test_create_validates_price(client):
    cafe = sample_cafe()
    cafe["coffee_price"] = "expensive"
    response = client.post("/api/cafes", headers=headers(), json=cafe)
    assert response.status_code == 400


def test_update_and_delete(client):
    cafe_id = client.post("/api/cafes", headers=headers(), json=sample_cafe()).get_json()["cafe"]["id"]
    updated = client.patch(f"/api/cafes/{cafe_id}", headers=headers(), json={"coffee_price": 2.9})
    assert updated.get_json()["cafe"]["coffee_price"] == 2.9
    assert client.delete(f"/api/cafes/{cafe_id}", headers=headers()).status_code == 200
    assert client.delete(f"/api/cafes/{cafe_id}", headers=headers()).status_code == 404


def test_search_needs_location(client):
    assert client.get("/api/cafes/search").status_code == 400
