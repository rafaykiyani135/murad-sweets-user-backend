import asyncio
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.security import get_password_hash
from app.db.base import Base
from app.models.category import Category
from app.models.product import Product, ProductOption, CustomBoxRule
from app.models.admin_user import AdminUser
from app.services.pricing import get_deterministic_uuid

# Initial Category Definitions
CATEGORIES_DATA = [
    {
        "slug": "dry-sweets",
        "name": "Dry Sweets (Mix & Match)",
        "description": "Choose a box size, fill each slot with your favorite sweets",
        "sort_order": 1
    },
    {
        "slug": "specialty",
        "name": "Specialty Items",
        "description": "Premium fusion sweets and traditional delights",
        "sort_order": 2
    },
    {
        "slug": "party-trays",
        "name": "Party Trays",
        "description": "Beautiful arrangements for gatherings and celebrations",
        "sort_order": 3
    },
    {
        "slug": "pitha",
        "name": "Traditional Pitha (Pre-Order Only)",
        "description": "Steamed and fried rice crepes made the authentic way",
        "sort_order": 4
    }
]

# Initial Products from products.ts
PRODUCTS_DATA = [
    {
        "orig_id": "1",
        "slug": "kalojam",
        "name": "Kalojam",
        "category_slug": "dry-sweets",
        "description": "Traditional deep-fried milk-solid dumplings soaked in cardamom-infused sugar syrup, featuring a dark, caramelized outer layer and a soft, melt-in-your-mouth center.",
        "price_cents": 0,
        "product_type": "selection_item",
        "in_stock": True,
        "quantity_on_hand": 50,
        "images": ["https://images.unsplash.com/photo-1601356616077-695728ecf769?w=600&auto=format&fit=crop&q=80"]
    },
    {
        "orig_id": "2",
        "slug": "brown-chom-chom",
        "name": "Brown Chom Chom",
        "category_slug": "dry-sweets",
        "description": "Classic Bangladeshi oval-shaped sweet made of dense chenna (curdled milk), slowly cooked to a rich mahogany brown color and rolled in mawa crumbs.",
        "price_cents": 0,
        "product_type": "selection_item",
        "in_stock": True,
        "quantity_on_hand": 50,
        "images": ["https://images.unsplash.com/photo-1548680373-ab6d4a5b48d7?w=600&auto=format&fit=crop&q=80"]
    },
    {
        "orig_id": "3",
        "slug": "white-chom-chom",
        "name": "White Chom Chom",
        "category_slug": "dry-sweets",
        "description": "Delicate, ivory-white chom chom made of soft chenna, simmered in light sugar syrup, offering a moist texture and mild sweetness.",
        "price_cents": 0,
        "product_type": "selection_item",
        "in_stock": True,
        "quantity_on_hand": 50,
        "images": ["https://images.unsplash.com/photo-1589135306090-e5550a6f0a0d?w=600&auto=format&fit=crop&q=80"]
    },
    {
        "orig_id": "4",
        "slug": "kalojam-sandwich",
        "name": "Kalojam Sandwich",
        "category_slug": "dry-sweets",
        "description": "An elegant variation of Kalojam, sliced open and filled with a thick layer of sweetened cream (malai) and garnished with nuts.",
        "price_cents": 0,
        "product_type": "selection_item",
        "in_stock": True,
        "quantity_on_hand": 50,
        "images": ["https://images.unsplash.com/photo-1605697040924-852290747ef4?w=600&auto=format&fit=crop&q=80"]
    },
    {
        "orig_id": "5",
        "slug": "kheer-mouchak",
        "name": "Kheer Mouchak",
        "category_slug": "dry-sweets",
        "description": "A honeycomb-shaped royal delight made with chenna, soaked in saffron syrup, and covered with creamy, reduced milk kheer.",
        "price_cents": 0,
        "product_type": "selection_item",
        "in_stock": True,
        "quantity_on_hand": 50,
        "images": ["https://images.unsplash.com/photo-1505253716362-afaea1d3d1af?w=600&auto=format&fit=crop&q=80"]
    },
    {
        "orig_id": "6",
        "slug": "malaikari",
        "name": "Malaikari",
        "category_slug": "dry-sweets",
        "description": "Plump chenna rounds cooked in syrup and then coated with a luscious, rich saffron malai reduction.",
        "price_cents": 0,
        "product_type": "selection_item",
        "in_stock": True,
        "quantity_on_hand": 50,
        "images": ["https://images.unsplash.com/photo-1589135306090-e5550a6f0a0d?w=600&auto=format&fit=crop&q=80"]
    },
    {
        "orig_id": "7",
        "slug": "rajbhog",
        "name": "Rajbhog",
        "category_slug": "dry-sweets",
        "description": "Grand-sized chenna spheres stuffed with dry fruits, simmered in a fragrant saffron and cardamom syrup.",
        "price_cents": 0,
        "product_type": "selection_item",
        "in_stock": True,
        "quantity_on_hand": 50,
        "images": ["https://images.unsplash.com/photo-1601356616077-695728ecf769?w=600&auto=format&fit=crop&q=80"]
    },
    {
        "orig_id": "8",
        "slug": "kathari-bhog",
        "name": "Kathari Bhog",
        "category_slug": "dry-sweets",
        "description": "An artisanal Bangladeshi sweet consisting of small, textured chenna balls cooked in premium date jaggery syrup for an earthy, deep flavor.",
        "price_cents": 0,
        "product_type": "selection_item",
        "in_stock": True,
        "quantity_on_hand": 50,
        "images": ["https://images.unsplash.com/photo-1548680373-ab6d4a5b48d7?w=600&auto=format&fit=crop&q=80"]
    },
    {
        "orig_id": "9",
        "slug": "laddu",
        "name": "Laddu",
        "category_slug": "dry-sweets",
        "description": "Aromatic Motichoor Laddus made from tiny chickpea flour globules fried in pure ghee, sweetened and shaped into golden spheres.",
        "price_cents": 0,
        "product_type": "selection_item",
        "in_stock": True,
        "quantity_on_hand": 50,
        "images": ["/laddu.png"]
    },
    {
        "orig_id": "10",
        "slug": "shandesh",
        "name": "Shandesh",
        "category_slug": "dry-sweets",
        "description": "Traditional dry sweet made from fresh paneer and date molasses (Nolen Gur), molded into artistic patterns.",
        "price_cents": 0,
        "product_type": "selection_item",
        "in_stock": True,
        "quantity_on_hand": 50,
        "images": ["https://images.unsplash.com/photo-1589135306090-e5550a6f0a0d?w=600&auto=format&fit=crop&q=80"]
    },
    {
        "orig_id": "11",
        "slug": "gulab-jamun-dry",
        "name": "Gulab Jamun (dry)",
        "category_slug": "dry-sweets",
        "description": "Soft milk-solid balls fried, sweetened, and rolled in dry desiccated coconut, making them clean and easy to handle.",
        "price_cents": 0,
        "product_type": "selection_item",
        "in_stock": True,
        "quantity_on_hand": 50,
        "images": ["/gulab-jamun.png"]
    },
    {
        "orig_id": "12",
        "slug": "peda",
        "name": "Peda",
        "category_slug": "dry-sweets",
        "description": "Rich, semi-soft sweet made of condensed milk, sugar, and traditional flavorings including green cardamom and saffron.",
        "price_cents": 0,
        "product_type": "selection_item",
        "in_stock": False,  # Sold out in frontend
        "quantity_on_hand": 0,
        "images": ["https://images.unsplash.com/photo-1589135306090-e5550a6f0a0d?w=600&auto=format&fit=crop&q=80"]
    },
    # Specialty
    {
        "orig_id": "13",
        "slug": "rasmalai-cake",
        "name": "Rasmalai Cake",
        "category_slug": "specialty",
        "description": "An innovative fusion dessert merging vanilla sponge cake soaked in saffron cardamom milk (ras) and topped with actual Rasmalai pieces and pistachios.",
        "price_cents": 700,
        "unit_label": "per cake (8oz)",
        "product_type": "standard",
        "in_stock": True,
        "quantity_on_hand": 20,
        "images": ["/rasmalai.png"]
    },
    {
        "orig_id": "14",
        "slug": "gulab-jamun",
        "name": "Gulab Jamun",
        "category_slug": "specialty",
        "description": "Soft, golden-brown dumplings made of milk solids, deep-fried and soaked in a warm, fragrant sugar syrup with rosewater and cardamom.",
        "price_cents": 600,
        "unit_label": "per box (4pc)",
        "product_type": "standard",
        "in_stock": True,
        "quantity_on_hand": 20,
        "images": ["/gulab-jamun.png"]
    },
    {
        "orig_id": "15",
        "slug": "mishti-doi",
        "name": "Mishti Doi",
        "category_slug": "specialty",
        "description": "Classic Bengali fermented sweet yogurt, prepared in traditional clay pots by boiling milk until thickened, sweetening with brown sugar/jaggery, and fermenting overnight.",
        "price_cents": 1000,
        "unit_label": "per box (16oz)",
        "product_type": "standard",
        "in_stock": True,
        "quantity_on_hand": 20,
        "images": ["/mishti-doi.png"]
    },
    # Party Trays
    {
        "orig_id": "16",
        "slug": "small-party-tray",
        "name": "Small Party Tray",
        "category_slug": "party-trays",
        "description": "A beautiful arrangement of 15-18 assorted premium dry sweets, perfect for family get-togethers and intimate celebrations.",
        "price_cents": 3000,
        "unit_label": "per tray (~18 pcs)",
        "product_type": "standard",
        "in_stock": True,
        "images": ["https://images.unsplash.com/photo-1601356616077-695728ecf769?w=600&auto=format&fit=crop&q=80"]
    },
    {
        "orig_id": "17",
        "slug": "large-party-tray",
        "name": "Large Party Tray",
        "category_slug": "party-trays",
        "description": "A grand presentation tray with 35-40 pieces of our finest sweets, featuring an assortment of chom chom, kalojam, shandesh, and laddus.",
        "price_cents": 6000,
        "unit_label": "per tray (~40 pcs)",
        "product_type": "standard",
        "in_stock": True,
        "images": ["https://images.unsplash.com/photo-1601356616077-695728ecf769?w=600&auto=format&fit=crop&q=80"]
    },
    # Pitha
    {
        "orig_id": "18",
        "slug": "jhal-pitha",
        "name": "Jhal Pitha",
        "category_slug": "pitha",
        "description": "Savory, spicy steamed rice cakes flavored with green chilies, coriander, onion, and a hint of traditional spices. Perfect for winter evenings.",
        "price_cents": 400,
        "unit_label": "per pc",
        "product_type": "standard",
        "in_stock": True,
        "preorder_only": True,
        "min_quantity": 10,
        "prep_time_hours": 24,
        "images": ["https://images.unsplash.com/photo-1519676867240-f03562e64548?w=600&auto=format&fit=crop&q=80"]
    },
    {
        "orig_id": "19",
        "slug": "puli-pitha",
        "name": "Puli Pitha",
        "category_slug": "pitha",
        "description": "Sweet, half-moon shaped dumplings stuffed with coconut and liquid date molasses (khejur gur), steamed to perfection.",
        "price_cents": 300,
        "unit_label": "per pc",
        "product_type": "standard",
        "in_stock": True,
        "preorder_only": True,
        "min_quantity": 10,
        "prep_time_hours": 24,
        "images": ["https://images.unsplash.com/photo-1519676867240-f03562e64548?w=600&auto=format&fit=crop&q=80"]
    },
    {
        "orig_id": "20",
        "slug": "patishapta",
        "name": "Patishapta",
        "category_slug": "pitha",
        "description": "Delicate, thin crepes made from rice flour batter, filled with a rich mixture of coconut, milk reduction (kheer), and cardamom, rolled beautifully.",
        "price_cents": 250,
        "unit_label": "per pc",
        "product_type": "standard",
        "in_stock": True,
        "preorder_only": True,
        "min_quantity": 10,
        "prep_time_hours": 24,
        "images": ["https://images.unsplash.com/photo-1587314168485-3236d6710814?w=600&auto=format&fit=crop&q=80"]
    },
    # CUSTOM BOXES (Mix & Match and Assorted)
    {
        "orig_id": "mixmatch-3",
        "slug": "mixmatch-3",
        "name": "3 Pieces Mix & Match Box",
        "category_slug": "dry-sweets",
        "description": "Customize your own 3-pack box of traditional dry sweets.",
        "price_cents": 500,
        "product_type": "custom_box",
        "in_stock": True,
        "images": ["https://images.unsplash.com/photo-1601356616077-695728ecf769?w=600&auto=format&fit=crop&q=80"]
    },
    {
        "orig_id": "mixmatch-6",
        "slug": "mixmatch-6",
        "name": "6 Pieces Mix & Match Box",
        "category_slug": "dry-sweets",
        "description": "Customize your own 6-pack box of traditional dry sweets.",
        "price_cents": 1000,
        "product_type": "custom_box",
        "in_stock": True,
        "images": ["https://images.unsplash.com/photo-1601356616077-695728ecf769?w=600&auto=format&fit=crop&q=80"]
    },
    {
        "orig_id": "mixmatch-9",
        "slug": "mixmatch-9",
        "name": "9 Pieces Mix & Match Box",
        "category_slug": "dry-sweets",
        "description": "Customize your own 9-pack box of traditional dry sweets.",
        "price_cents": 1500,
        "product_type": "custom_box",
        "in_stock": True,
        "images": ["https://images.unsplash.com/photo-1601356616077-695728ecf769?w=600&auto=format&fit=crop&q=80"]
    }
]

async def seed_database():
    # Connect directly using SQLAlchemy async session
    engine = create_async_engine(settings.async_database_url, echo=True)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        # Create Tables first in case lifespan hasn't run yet
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        print("Seeding categories...")
        category_mapping = {}
        for cat_data in CATEGORIES_DATA:
            # Check if category already exists
            from sqlalchemy import select
            result = await session.execute(
                select(Category).where(Category.slug == cat_data["slug"])
            )
            category = result.scalar_one_or_none()
            if not category:
                category = Category(
                    slug=cat_data["slug"],
                    name=cat_data["name"],
                    description=cat_data["description"],
                    sort_order=cat_data["sort_order"],
                    is_active=True
                )
                session.add(category)
                await session.flush()
            category_mapping[cat_data["slug"]] = category.id

        print("Seeding products...")
        for prod_data in PRODUCTS_DATA:
            # Deterministic UUID based on original ID
            db_id = get_deterministic_uuid(prod_data["orig_id"])
            
            result = await session.execute(
                select(Product).where(Product.id == db_id)
            )
            product = result.scalar_one_or_none()
            
            cat_id = category_mapping[prod_data["category_slug"]]
            
            if not product:
                product = Product(
                    id=db_id,
                    category_id=cat_id,
                    slug=prod_data["slug"],
                    name=prod_data["name"],
                    description=prod_data["description"],
                    base_price_cents=prod_data["price_cents"],
                    unit_label=prod_data.get("unit_label"),
                    product_type=prod_data["product_type"],
                    min_quantity=prod_data.get("min_quantity", 1),
                    max_quantity=prod_data.get("max_quantity"),
                    is_active=True,
                    is_in_stock=prod_data["in_stock"],
                    quantity_on_hand=prod_data.get("quantity_on_hand"),  # None = untracked
                    preorder_only=prod_data.get("preorder_only", False),
                    prep_time_hours=prod_data.get("prep_time_hours", 0),
                    metadata_json={"images": prod_data["images"]}
                )
                session.add(product)
            else:
                # Update quantity_on_hand on re-seed only if explicitly set in data
                if "quantity_on_hand" in prod_data and product.quantity_on_hand is None:
                    product.quantity_on_hand = prod_data["quantity_on_hand"]
                
        # Seed default Admin User
        admin_username = "admin"
        admin_email = "admin@muradsweets.com"
        result = await session.execute(
            select(AdminUser).where(AdminUser.username == admin_username)
        )
        admin = result.scalar_one_or_none()
        
        if not admin:
            print("Creating default admin user...")
            admin = AdminUser(
                username=admin_username,
                email=admin_email,
                hashed_password=get_password_hash("adminpassword"),
                is_active=True
            )
            session.add(admin)
            print("Default admin created: username='admin', password='adminpassword'")

        await session.commit()
        print("Database seeding completed successfully!")

if __name__ == "__main__":
    asyncio.run(seed_database())
