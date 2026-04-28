from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_public_data_records_returns_valid_response():
    """
    공공데이터 조회 API가 기본 응답 구조를 반환하는지 확인한다.

    현재는 데이터가 없어도 count=0, records=[] 형태로 응답하면 정상이다.
    """
    response = client.get(
        "/api/v1/public-data/records",
        params={
            "source_type": "KEPAD_RECRUITMENT",
            "limit": 10,
            "offset": 0,
        },
    )

    assert response.status_code == 200, response.json()

    data = response.json()

    assert data["source_type"] == "KEPAD_RECRUITMENT"
    assert "count" in data
    assert "records" in data
    assert isinstance(data["records"], list)
