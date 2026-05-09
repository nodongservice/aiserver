-- Indexes for /api/v1/score/map accessibility scoring queries.
-- Run on PostgreSQL/PostGIS outside a transaction block.

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pd_nationwide_bus_stop_lat_lng_not_null
    ON pd_nationwide_bus_stop (latitude, longitude)
    WHERE latitude IS NOT NULL AND longitude IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pd_nationwide_crosswalk_lat_lng_not_null
    ON pd_nationwide_crosswalk (latitude, longitude)
    WHERE latitude IS NOT NULL AND longitude IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pd_nationwide_traffic_light_lat_lng_not_null
    ON pd_nationwide_traffic_light (latitude, longitude)
    WHERE latitude IS NOT NULL AND longitude IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pd_transport_support_center_lat_lng_not_null
    ON pd_transport_support_center (latitude, longitude)
    WHERE latitude IS NOT NULL AND longitude IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_public_accessibility_gis_feature_active_source
    ON public_accessibility_gis_feature (source_type)
    WHERE is_active IS TRUE;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_public_accessibility_gis_feature_active_geog
    ON public_accessibility_gis_feature
    USING GIST (geog)
    WHERE is_active IS TRUE AND geog IS NOT NULL;
