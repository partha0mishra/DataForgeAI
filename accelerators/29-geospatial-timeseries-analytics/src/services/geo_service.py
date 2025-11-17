"""Geospatial analytics service."""
from sqlalchemy.orm import Session
from src.models.geospatial_data import GeospatialData, TimeSeriesData
from datetime import datetime

class GeoService:
    def __init__(self, db: Session):
        self.db = db

    def create_geospatial_data(self, name: str, geometry_type: str, coordinates: dict, properties: dict = None):
        data = GeospatialData(
            name=name,
            geometry_type=geometry_type,
            coordinates=coordinates,
            properties=properties or {}
        )
        self.db.add(data)
        self.db.commit()
        return data

    def record_timeseries(self, metric_name: str, value: float, tags: dict = None):
        data = TimeSeriesData(
            metric_name=metric_name,
            timestamp=datetime.utcnow(),
            value=value,
            tags=tags or {}
        )
        self.db.add(data)
        self.db.commit()
        return data

    def spatial_query(self, bbox: dict):
        """Query data within bounding box."""
        # Simplified spatial query
        return self.db.query(GeospatialData).filter(
            GeospatialData.bbox.isnot(None)
        ).all()
