"""Tests for Geo Service."""
import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models.geospatial_data import Base, GeospatialData, TimeSeriesData
from src.services.geo_service import GeoService


@pytest.fixture
def db_session():
    """Create test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_create_geospatial_data(db_session):
    """Test creating geospatial data."""
    service = GeoService(db_session)
    data = service.create_geospatial_data(
        name="Store Location",
        geometry_type="point",
        coordinates={"lat": 37.7749, "lon": -122.4194},
        properties={"address": "123 Main St"}
    )

    assert data.data_id is not None
    assert data.name == "Store Location"
    assert data.geometry_type == "point"
    assert data.coordinates["lat"] == 37.7749


def test_record_timeseries(db_session):
    """Test recording time series data."""
    service = GeoService(db_session)
    data = service.record_timeseries(
        metric_name="temperature",
        value=25.5,
        tags={"location": "sensor1"}
    )

    assert data.series_id is not None
    assert data.metric_name == "temperature"
    assert data.value == 25.5
    assert data.timestamp is not None


def test_spatial_query(db_session):
    """Test spatial query."""
    service = GeoService(db_session)

    # Create some geospatial data
    service.create_geospatial_data("Location1", "point", {"lat": 37.7749, "lon": -122.4194}, {})
    service.create_geospatial_data("Location2", "point", {"lat": 37.7849, "lon": -122.4294}, {})

    # Query
    results = service.spatial_query(bbox={"min_lat": 37.7, "max_lat": 37.8, "min_lon": -122.5, "max_lon": -122.4})

    assert isinstance(results, list)
