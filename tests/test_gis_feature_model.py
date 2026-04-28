from app.db.models import AccessibilityGisFeature


def test_accessibility_gis_feature_model_table_name():
    """
    AccessibilityGisFeature 모델이 올바른 테이블명을 사용하는지 확인한다.
    """
    assert AccessibilityGisFeature.__tablename__ == "public_accessibility_gis_feature"


def test_accessibility_gis_feature_model_has_required_columns():
    """
    GIS feature 모델에 공간 검색에 필요한 핵심 컬럼이 있는지 확인한다.
    """
    columns = AccessibilityGisFeature.__table__.columns.keys()

    assert "id" in columns
    assert "public_data_record_id" in columns
    assert "source_type" in columns
    assert "feature_type" in columns
    assert "latitude" in columns
    assert "longitude" in columns
    assert "geom" in columns
    assert "geog" in columns
    assert "properties" in columns
    assert "is_active" in columns
