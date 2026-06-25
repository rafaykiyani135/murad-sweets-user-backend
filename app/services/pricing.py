import uuid
from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.models.category import Category

# Allowed ZIP Codes for Delivery
ALLOWED_ZIP_CODES = {"11218", "11219", "11230", "11225", "11226", "11204", "11210"}
# Delivery variables are now managed by frontend distance calculator

def get_deterministic_uuid(frontend_id: str) -> uuid.UUID:
    """Generate a deterministic UUID from the frontend ID."""
    try:
        # If the frontend sent an actual backend UUID (which it does now), use it directly
        return uuid.UUID(frontend_id)
    except ValueError:
        pass
        
    # Fallback for old string slugs (e.g., assorted boxes)
    if frontend_id.startswith("assorted-"):
        parts = frontend_id.split("-")
        if len(parts) >= 2:
            frontend_id = f"assorted-{parts[1]}"
    return uuid.uuid5(uuid.NAMESPACE_DNS, f"frontend-id-{frontend_id}")

async def calculate_quote(
    db: AsyncSession,
    items: List[Dict[str, Any]],
    fulfillment_type: str,
    zip_code: Optional[str] = None
) -> Dict[str, Any]:
    """
    Recalculates cart totals and validates all catalog constraints using database values.
    """
    subtotal_cents = 0
    validated_items = []
    max_prep_time_hours = 0

    # 1. Validate Fulfillment (Removed outdated ZIP code check)
    if fulfillment_type == "delivery":
        if not zip_code:
            pass # ZIP codes are now handled by the frontend distance calculator


    # 2. Process and Recalculate each item
    for item in items:
        frontend_id = str(item.get("productId"))
        quantity = int(item.get("quantity", 1))

        if quantity <= 0:
            raise HTTPException(status_code=400, detail="Quantity must be greater than 0.")

        # Find the product in DB
        db_id = get_deterministic_uuid(frontend_id)
        product_result = await db.execute(select(Product).where(Product.id == db_id))
        product = product_result.scalar_one_or_none()

        if not product:
            raise HTTPException(status_code=404, detail=f"Product not found: {item.get('name', frontend_id)}")
        
        if not product.is_active:
            raise HTTPException(status_code=400, detail=f"Product {product.name} is currently inactive.")
        
        if not product.is_in_stock:
            raise HTTPException(status_code=400, detail=f"Product {product.name} is currently out of stock.")

        # Hard-block if tracked quantity is insufficient
        if product.quantity_on_hand is not None and product.quantity_on_hand < quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Only {product.quantity_on_hand} unit(s) of '{product.name}' left in stock."
            )

        # Check prep time
        if product.preorder_only and product.prep_time_hours > max_prep_time_hours:
            max_prep_time_hours = product.prep_time_hours

        # Enforce min/max quantity limits
        if quantity < product.min_quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Minimum quantity for {product.name} is {product.min_quantity}."
            )
        if product.max_quantity and quantity > product.max_quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Maximum quantity for {product.name} is {product.max_quantity}."
            )

        unit_price_cents = product.base_price_cents
        line_total_cents = unit_price_cents * quantity
        selections_data = None

        # 3. Check Mix & Match Custom Box Constraints
        if product.product_type == "custom_box":
            # Extract box size (3, 6, 9) from the slug (e.g. mixmatch-3 or assorted-3)
            box_size = 3
            if "3" in product.slug:
                box_size = 3
            elif "6" in product.slug:
                box_size = 6
            elif "9" in product.slug:
                box_size = 9

            mix_match = item.get("mixMatch")
            assorted_box = item.get("assortedBox")

            if not mix_match and not assorted_box:
                raise HTTPException(
                    status_code=400,
                    detail=f"Custom box {product.name} requires configuration details."
                )

            # Get selected items
            selected_items = []
            if mix_match:
                selected_items = mix_match.get("selectedItems", [])
                selections_data = {"type": "mix_match", "selectedItems": selected_items}
            elif assorted_box:
                selected_items = assorted_box.get("selectedItems", [])
                selections_data = {"type": "assorted", "selectedItems": selected_items}

            # Validate box items selections
            if mix_match:
                # selectedItems is a list of {id, name, quantity}
                total_selected = sum(int(s.get("quantity", 0)) for s in selected_items)
                if total_selected != box_size:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Selected items count ({total_selected}) must match box size ({box_size})."
                    )

                # Validate each selected sweet is active, in-stock, and in the "dry-sweets" category
                for selected in selected_items:
                    sweet_id = str(selected.get("id"))
                    sweet_qty = int(selected.get("quantity", 0))
                    if sweet_qty <= 0:
                        continue
                    
                    sweet_db_id = get_deterministic_uuid(sweet_id)
                    sweet_res = await db.execute(
                        select(Product).join(Category).where(Product.id == sweet_db_id)
                    )
                    sweet = sweet_res.scalar_one_or_none()
                    if not sweet or sweet.category.slug != "dry-sweets" or not sweet.is_active or not sweet.is_in_stock:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Invalid sweet selection: {selected.get('name', sweet_id)}. Only active, in-stock dry sweets are allowed."
                        )
                    # Hard-block if tracked quantity is insufficient for this sweet
                    if sweet.quantity_on_hand is not None and sweet.quantity_on_hand < sweet_qty:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Only {sweet.quantity_on_hand} unit(s) of '{sweet.name}' left in stock."
                        )
            
            elif assorted_box:
                # assortedBox selectedItems is a list of {name, color}
                total_selected = len(selected_items)
                if total_selected != box_size:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Selected items count ({total_selected}) must match box size ({box_size})."
                    )
                # For assorted, we validate that the sweet name matches a valid dry-sweet
                enriched_selected_items = []
                for selected in selected_items:
                    sweet_name = selected.get("name")
                    sweet_res = await db.execute(
                        select(Product).join(Category).where(
                            Product.name == sweet_name,
                            Category.slug == "dry-sweets",
                            Product.is_active == True,
                            Product.is_in_stock == True
                        )
                    )
                    sweet = sweet_res.scalar_one_or_none()
                    if not sweet:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Invalid assorted sweet: {sweet_name}. Must be an active in-stock dry sweet."
                        )
                    
                    enriched_selected_items.append({
                        "id": str(sweet.id),
                        "name": sweet.name,
                        "quantity": 1
                    })
                
                # Replace selections with the enriched items so inventory deduction works
                selections_data["selectedItems"] = enriched_selected_items

        subtotal_cents += line_total_cents

        validated_items.append({
            "product_id": product.id,
            "name_snapshot": product.name,
            "unit_price_cents": unit_price_cents,
            "quantity": quantity,
            "line_total_cents": line_total_cents,
            "selections": selections_data
        })

    # 4. Delivery Fee
    # The backend quote no longer computes delivery fees (frontend calculates via Mapbox/OSRM distance).
    # We return 0 here; the frontend adds its own dynamic delivery fee to the subtotal.
    delivery_fee_cents = 0
    tax_cents = 0  # No tax in MVP
    total_cents = subtotal_cents + tax_cents

    return {
        "subtotal_cents": subtotal_cents,
        "delivery_fee_cents": delivery_fee_cents,
        "tax_cents": tax_cents,
        "total_cents": total_cents,
        "validated_items": validated_items,
        "max_prep_time_hours": max_prep_time_hours
    }
