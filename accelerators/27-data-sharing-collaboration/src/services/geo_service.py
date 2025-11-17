"""Geospatial service."""
from sqlalchemy.orm import Session
from src.models.geospatial_data import GeospatialData

class GeoService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_location(self, lat: float, lon: float, properties: dict = None):
        location = GeospatialData(
            location_type='point',
            latitude=lat,
            longitude=lon,
            properties=properties or {}
        )
        self.db.add(location)
        self.db.commit()
        return location
