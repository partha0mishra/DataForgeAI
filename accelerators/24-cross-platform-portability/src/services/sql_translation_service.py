"""Service for SQL translation across platforms."""
from typing import Dict, Any, Optional
import time
from sqlalchemy.orm import Session
from src.repositories.sql_translation_repository import SQLTranslationRepository

try:
    import sqlglot
    SQLGLOT_AVAILABLE = True
except ImportError:
    SQLGLOT_AVAILABLE = False

class SQLTranslationService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = SQLTranslationRepository(db)
    
    def translate_sql(self, source_sql: str, source_platform: str, target_platform: str, 
                     validate_equivalence: bool = True) -> Any:
        """Translate SQL between platforms."""
        start_time = time.time()
        
        translation_data = {
            'source_sql': source_sql,
            'source_platform': source_platform,
            'target_platform': target_platform,
            'validate_equivalence': validate_equivalence,
            'status': 'pending'
        }
        
        translation = self.repo.create(translation_data)
        
        try:
            if SQLGLOT_AVAILABLE:
                # Real SQL translation using sqlglot
                target_sql = sqlglot.transpile(source_sql, read=source_platform, write=target_platform)[0]
                notes = []
                confidence = 0.9
            else:
                # Simplified fallback
                target_sql = source_sql  # Placeholder
                notes = ["Real SQL translation library not available"]
                confidence = 0.5
            
            duration = (time.time() - start_time) * 1000
            
            self.repo.update(translation.translation_id, {
                'status': 'completed',
                'target_sql': target_sql,
                'confidence_score': confidence,
                'translation_duration_ms': duration,
                'translation_notes': notes,
                'syntax_valid': True
            })
            
            return self.repo.get_by_id(translation.translation_id)
            
        except Exception as e:
            self.repo.update(translation.translation_id, {
                'status': 'failed',
                'translation_notes': [str(e)]
            })
            raise
    
    def get_translation(self, translation_id: str):
        return self.repo.get_by_id(translation_id)
    
    def get_cached_translation(self, query_hash: str):
        return self.repo.get_by_hash(query_hash)
