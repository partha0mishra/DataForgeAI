"""FastAPI REST API for Data Monetization."""

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from products.product_manager import ProductManager, ProductTier, AccessLevel, RateLimit
from billing.usage_tracker import UsageTracker

app = FastAPI(title="DataForge Data Monetization", version="0.1.0")

product_manager = ProductManager()
usage_tracker = UsageTracker()


class ProductCreate(BaseModel):
    """Product creation request."""
    name: str
    description: str
    tier: str
    price_monthly: float = 0.0
    price_per_request: float = 0.0


@app.get("/health")
async def health_check():
    """Health check."""
    return {"status": "healthy"}


@app.post("/products")
async def create_product(product: ProductCreate):
    """Create a data product."""
    created = product_manager.create_product(
        name=product.name,
        description=product.description,
        tier=ProductTier(product.tier),
        access_level=AccessLevel.AUTHENTICATED,
        price_monthly=product.price_monthly,
        price_per_request=product.price_per_request,
    )

    return {
        "product_id": created.product_id,
        "name": created.name,
        "tier": created.tier.value,
        "price_monthly": created.price_monthly,
    }


@app.get("/products")
async def list_products():
    """List all products."""
    products = product_manager.list_products()

    return {
        "products": [
            {
                "product_id": p.product_id,
                "name": p.name,
                "description": p.description,
                "tier": p.tier.value,
                "price_monthly": p.price_monthly,
            }
            for p in products
        ]
    }


@app.post("/usage/record")
async def record_usage(
    customer_id: str,
    product_id: str,
    requests: int = 1,
):
    """Record API usage."""
    product = product_manager.get_product(product_id)

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    cost = requests * product.price_per_request

    record = usage_tracker.record_usage(
        customer_id=customer_id,
        product_id=product_id,
        requests=requests,
        cost=cost,
    )

    return {
        "recorded": True,
        "requests": requests,
        "cost": cost,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010)
