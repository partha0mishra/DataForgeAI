"""Data Mesh Enablement - Production API."""
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from src.database import get_db, init_db
from src.services.data_product_service import DataProductService
from src.schemas.data_product import DataProductCreate, DataProductResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Data Mesh Enablement API",
    description="Production API for data mesh implementation",
    version="1.0.0"
)

@app.on_event("startup")
async def startup_event():
    try:
        init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.post("/api/v1/products", response_model=DataProductResponse)
async def create_data_product(product: DataProductCreate, db: Session = Depends(get_db)):
    """Create a new data product."""
    try:
        service = DataProductService(db)
        result = service.create_product(
            name=product.name,
            domain_id=product.domain_id,
            owner=product.owner,
            product_type=product.product_type,
            access_type=product.access_type,
            data_location=product.data_location,
            description=product.description
        )
        return DataProductResponse.from_orm(result)
    except Exception as e:
        logger.error(f"Error creating data product: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/products/{product_id}", response_model=DataProductResponse)
async def get_data_product(product_id: str, db: Session = Depends(get_db)):
    """Get data product by ID."""
    service = DataProductService(db)
    product = service.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Data product not found")
    return DataProductResponse.from_orm(product)

@app.get("/api/v1/products")
async def list_data_products(domain_id: Optional[str] = None, db: Session = Depends(get_db)):
    """List all data products."""
    service = DataProductService(db)
    products = service.list_products(domain_id)
    return [DataProductResponse.from_orm(p) for p in products]

@app.post("/api/v1/products/{product_id}/publish")
async def publish_data_product(product_id: str, db: Session = Depends(get_db)):
    """Publish a data product."""
    service = DataProductService(db)
    product = service.publish_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Data product not found")
    return {"message": "Data product published successfully", "product_id": product_id}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8025)
