"""Example: Data monetization workflow."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from products.product_manager import ProductManager, ProductTier, AccessLevel
from billing.usage_tracker import UsageTracker
from datetime import datetime, timedelta


def main():
    """Run data monetization example."""
    print("=" * 80)
    print(" DataForge Data Monetization - Example")
    print("=" * 80)

    # Initialize components
    product_manager = ProductManager()
    usage_tracker = UsageTracker()

    # Create data products
    print("\n1. Creating Data Products...")
    
    free_product = product_manager.create_product(
        name="Weather Data API - Free",
        description="Basic weather data access",
        tier=ProductTier.FREE,
        access_level=AccessLevel.PUBLIC,
        price_monthly=0.0,
        price_per_request=0.0,
    )
    print(f"✓ Created: {free_product.name} (${free_product.price_monthly}/month)")

    premium_product = product_manager.create_product(
        name="Weather Data API - Premium",
        description="Advanced weather analytics",
        tier=ProductTier.PROFESSIONAL,
        access_level=AccessLevel.PREMIUM,
        price_monthly=99.0,
        price_per_request=0.01,
    )
    print(f"✓ Created: {premium_product.name} (${premium_product.price_monthly}/month + ${premium_product.price_per_request}/request)")

    # Simulate usage
    print("\n2. Recording API Usage...")
    
    customer_id = "customer_001"
    
    for i in range(100):
        usage_tracker.record_usage(
            customer_id=customer_id,
            product_id=premium_product.product_id,
            requests=1,
            cost=premium_product.price_per_request,
        )
    
    print(f"✓ Recorded 100 API requests for {customer_id}")

    # Calculate bill
    print("\n3. Calculating Bill...")
    
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)
    
    bill = usage_tracker.calculate_bill(customer_id, start_date, end_date)
    
    print(f"  Total Requests: {bill['total_requests']}")
    print(f"  Usage Cost: ${bill['total_cost']:.2f}")
    print(f"  Subscription: ${premium_product.price_monthly:.2f}")
    print(f"  Total Bill: ${bill['total_cost'] + premium_product.price_monthly:.2f}")

    print("\n" + "=" * 80)
    print(" Example Complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
