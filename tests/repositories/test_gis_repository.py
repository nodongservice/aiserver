from app.repositories.gis_repository import get_accessibility_gis_feature
from app.schemas.analysis import JobCandidate
from app.schemas.gis import GisFeature


def test_get_accessibility_gis_feature_returns_dummy_without_db():
    """
    db 세션 없이 호출하면 기존 더미 GIS feature를 반환해야 한다.

    이 테스트는 scoring_service.py의 기존 동작이 깨지지 않는지 확인한다.
    """
    job = JobCandidate(
        job_post_id=101,
        company_id=55,
        company_name="ABC복지센터",
        job_title="사무보조",
        work_lat=37.5701,
        work_lng=126.9823,
        is_standard_workplace=True,
        is_disability_friendly_post=True,
        work_environment_tags=["computer_based"],
    )

    result = get_accessibility_gis_feature(job)

    assert isinstance(result, GisFeature)
    assert result.nearby_bus_stop_count >= 0
    assert result.nearby_subway_station_count >= 0
    assert result.nearby_crosswalk_count >= 0
