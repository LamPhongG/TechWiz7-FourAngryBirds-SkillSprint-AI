def test_ping(client):
    assert client.get("/api/ping").json() == {"status": "ok"}


def test_health_checks_database(client):
    res = client.get("/api/health")

    assert res.status_code == 200
    assert res.json() == {"status": "ok", "database": "ok"}


def test_departments_match_frontend_keys(client, hr_headers):
    res = client.get("/api/departments", headers=hr_headers)

    assert res.status_code == 200
    by_code = {d["code"]: d for d in res.json()}
    assert len(by_code) == 10
    assert by_code["Company-wide"]["name"] == "Company-wide"
    assert by_code["Engineering"]["name_en"] == "Engineering"


def test_job_positions_belong_to_departments(client, employee_headers):
    res = client.get("/api/job-positions", headers=employee_headers)

    assert res.status_code == 200
    positions = {p["id"]: p for p in res.json()}
    assert len(positions) == 10
    assert positions["support-engineer"]["department_code"] == "Engineering"
    assert positions["team-leader"]["name_en"] == "Team Leader / Tech Lead"


def test_catalog_requires_login(client):
    assert client.get("/api/departments").status_code == 401
    assert client.get("/api/job-positions").status_code == 401


def test_cors_allows_vite_dev_server(client):
    res = client.options(
        "/api/auth/login",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST"},
    )

    assert res.headers["access-control-allow-origin"] == "http://localhost:3000"
