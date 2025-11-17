"""Cross-Platform Analytics Portability - Production API."""
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from src.database import get_db, init_db
from src.services.model_conversion_service import ModelConversionService
from src.services.sql_translation_service import SQLTranslationService
from src.services.platform_compatibility_service import PlatformCompatibilityService
from src.services.table_conversion_service import TableConversionService
from src.schemas.model_conversion import ModelConversionRequest, ModelConversionResponse
from src.schemas.sql_translation import SQLTranslationRequest, SQLTranslationResponse
from src.schemas.platform_compatibility import PlatformCompatibilityRequest, PlatformCompatibilityResponse
from src.schemas.table_conversion import TableConversionRequest, TableConversionResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Cross-Platform Analytics Portability API",
    description="Production API for model conversion, SQL translation, and platform compatibility",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

# Model Conversion Endpoints
@app.post("/api/v1/models/convert", response_model=ModelConversionResponse)
async def convert_model(request: ModelConversionRequest, db: Session = Depends(get_db)):
    """Convert ML model between formats."""
    try:
        service = ModelConversionService(db)
        conversion = service.convert_model(
            model_id=request.model_id,
            source_uri=request.source_uri,
            source_format=request.source_format,
            target_format=request.target_format,
            target_platform=request.target_platform,
            optimization_level=request.optimization_level,
            preserve_metadata=request.preserve_metadata
        )
        return ModelConversionResponse.from_orm(conversion)
    except Exception as e:
        logger.error(f"Error converting model: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/models/conversions/{conversion_id}", response_model=ModelConversionResponse)
async def get_conversion(conversion_id: str, db: Session = Depends(get_db)):
    service = ModelConversionService(db)
    conversion = service.get_conversion(conversion_id)
    if not conversion:
        raise HTTPException(status_code=404, detail="Conversion not found")
    return ModelConversionResponse.from_orm(conversion)

@app.get("/api/v1/models/{model_id}/conversions")
async def get_model_conversions(model_id: str, db: Session = Depends(get_db)):
    service = ModelConversionService(db)
    conversions = service.get_model_conversions(model_id)
    return [ModelConversionResponse.from_orm(c) for c in conversions]

# SQL Translation Endpoints
@app.post("/api/v1/sql/translate", response_model=SQLTranslationResponse)
async def translate_sql(request: SQLTranslationRequest, db: Session = Depends(get_db)):
    """Translate SQL between platforms."""
    try:
        service = SQLTranslationService(db)
        translation = service.translate_sql(
            source_sql=request.source_sql,
            source_platform=request.source_platform,
            target_platform=request.target_platform,
            validate_equivalence=request.validate_equivalence
        )
        return SQLTranslationResponse.from_orm(translation)
    except Exception as e:
        logger.error(f"Error translating SQL: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/sql/translations/{translation_id}", response_model=SQLTranslationResponse)
async def get_translation(translation_id: str, db: Session = Depends(get_db)):
    service = SQLTranslationService(db)
    translation = service.get_translation(translation_id)
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")
    return SQLTranslationResponse.from_orm(translation)

# Platform Compatibility Endpoints
@app.post("/api/v1/compatibility/analyze", response_model=PlatformCompatibilityResponse)
async def analyze_compatibility(request: PlatformCompatibilityRequest, db: Session = Depends(get_db)):
    """Analyze platform compatibility."""
    try:
        service = PlatformCompatibilityService(db)
        analysis = service.analyze_compatibility(
            resource_id=request.resource_id,
            resource_type=request.resource_type,
            source_platform=request.source_platform,
            target_platforms=request.target_platforms
        )
        return PlatformCompatibilityResponse.from_orm(analysis)
    except Exception as e:
        logger.error(f"Error analyzing compatibility: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/compatibility/{analysis_id}", response_model=PlatformCompatibilityResponse)
async def get_compatibility_analysis(analysis_id: str, db: Session = Depends(get_db)):
    service = PlatformCompatibilityService(db)
    analysis = service.get_analysis(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return PlatformCompatibilityResponse.from_orm(analysis)

# Table Conversion Endpoints
@app.post("/api/v1/tables/convert", response_model=TableConversionResponse)
async def convert_table(request: TableConversionRequest, db: Session = Depends(get_db)):
    """Convert table format."""
    try:
        service = TableConversionService(db)
        conversion = service.convert_table(
            table_name=request.table_name,
            source_path=request.source_path,
            source_format=request.source_format,
            target_format=request.target_format,
            preserve_partitioning=request.preserve_partitioning,
            preserve_stats=request.preserve_stats
        )
        return TableConversionResponse.from_orm(conversion)
    except Exception as e:
        logger.error(f"Error converting table: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/tables/conversions/{conversion_id}", response_model=TableConversionResponse)
async def get_table_conversion(conversion_id: str, db: Session = Depends(get_db)):
    service = TableConversionService(db)
    conversion = service.get_conversion(conversion_id)
    if not conversion:
        raise HTTPException(status_code=404, detail="Conversion not found")
    return TableConversionResponse.from_orm(conversion)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8024)
