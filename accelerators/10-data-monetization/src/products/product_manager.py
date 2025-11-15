"""Data product management."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from dataforge_common.logging import get_logger

logger = get_logger(__name__)


class ProductTier(Enum):
    """Product pricing tiers."""
    FREE = "free"
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class AccessLevel(Enum):
    """Data access levels."""
    PUBLIC = "public"
    AUTHENTICATED = "authenticated"
    PREMIUM = "premium"


@dataclass
class RateLimit:
    """API rate limit configuration."""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    requests_per_day: int = 10000


@dataclass
class DataProduct:
    """A monetizable data product."""
    product_id: str
    name: str
    description: str
    tier: ProductTier
    access_level: AccessLevel
    price_monthly: float = 0.0
    price_per_request: float = 0.0
    rate_limits: RateLimit = field(default_factory=RateLimit)
    endpoints: List[str] = field(default_factory=list)
    schema: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


class ProductManager:
    """Manage data products."""

    def __init__(self):
        """Initialize product manager."""
        self.products: Dict[str, DataProduct] = {}

    def create_product(
        self,
        name: str,
        description: str,
        tier: ProductTier,
        access_level: AccessLevel,
        price_monthly: float = 0.0,
        price_per_request: float = 0.0,
        rate_limits: Optional[RateLimit] = None,
    ) -> DataProduct:
        """Create a data product."""
        product_id = f"prod_{len(self.products) + 1}_{datetime.utcnow().timestamp()}"

        product = DataProduct(
            product_id=product_id,
            name=name,
            description=description,
            tier=tier,
            access_level=access_level,
            price_monthly=price_monthly,
            price_per_request=price_per_request,
            rate_limits=rate_limits or RateLimit(),
        )

        self.products[product_id] = product
        logger.info(f"Created product: {product_id}")

        return product

    def get_product(self, product_id: str) -> Optional[DataProduct]:
        """Get product by ID."""
        return self.products.get(product_id)

    def list_products(self, tier: Optional[ProductTier] = None) -> List[DataProduct]:
        """List all products, optionally filtered by tier."""
        products = list(self.products.values())
        if tier:
            products = [p for p in products if p.tier == tier]
        return products
