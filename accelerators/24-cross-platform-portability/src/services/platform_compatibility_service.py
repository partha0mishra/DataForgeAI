"""Service for platform compatibility analysis."""
from typing import Dict, Any, List
import time
from sqlalchemy.orm import Session
from src.repositories.platform_compatibility_repository import PlatformCompatibilityRepository

class PlatformCompatibilityService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = PlatformCompatibilityRepository(db)
    
    def analyze_compatibility(self, resource_id: str, resource_type: str, 
                            source_platform: str, target_platforms: List[str]) -> Any:
        """Analyze platform compatibility."""
        start_time = time.time()
        
        # Simplified compatibility analysis
        compatibility_results = {}
        for platform in target_platforms:
            compatibility_results[platform] = {
                'compatible': True,
                'confidence': 0.85,
                'blockers': [],
                'warnings': [f'Manual review recommended for {platform}']
            }
        
        # Calculate portability score
        compatible_count = sum(1 for p in compatibility_results.values() if p['compatible'])
        portability_score = compatible_count / len(target_platforms)
        
        # Determine migration effort
        if portability_score >= 0.9:
            migration_effort = 'low'
        elif portability_score >= 0.7:
            migration_effort = 'medium'
        else:
            migration_effort = 'high'
        
        recommended_platform = max(compatibility_results.items(), 
                                  key=lambda x: x[1]['confidence'])[0]
        
        analysis_data = {
            'resource_id': resource_id,
            'resource_type': resource_type,
            'source_platform': source_platform,
            'target_platforms': target_platforms,
            'platform_compatibility': compatibility_results,
            'recommended_platform': recommended_platform,
            'portability_score': portability_score,
            'migration_effort': migration_effort,
            'analysis_duration_ms': (time.time() - start_time) * 1000
        }
        
        return self.repo.create(analysis_data)
    
    def get_analysis(self, analysis_id: str):
        return self.repo.get_by_id(analysis_id)
