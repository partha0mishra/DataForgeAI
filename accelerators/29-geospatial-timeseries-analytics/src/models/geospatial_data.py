"""Geospatial data model."""
from sqlalchemy import Column, String, DateTime, JSON, Float
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()

class GeospatialData(Base):
    __tablename__ = "geospatial_data"

    data_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), nullable=False)
    geometry_type = Column(String(50), nullable=False)  # point, linestring, polygon
    coordinates = Column(JSON, nullable=False)  # GeoJSON coordinates
    properties = Column(JSON)
    srid = Column(String(20), default='EPSG:4326')  # Spatial reference system
    bbox = Column(JSON)  # Bounding box
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class TimeSeriesData(Base):
    __tablename__ = "timeseries_data"

    series_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    metric_name = Column(String(100), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    value = Column(Float, nullable=False)
    tags = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
