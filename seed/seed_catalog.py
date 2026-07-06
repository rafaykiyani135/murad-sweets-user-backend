import asyncio
import sys
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
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
    },
    {
        "slug": "mishti-per-pound",
        "name": "Mishti Per Pound",
        "description": "Premium traditional sweets sold by the pound",
        "sort_order": 5
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
        "images": ["/KaloJam.png"]
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
        "images": ["/BrownChomChom.png"]
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
        "images": ["/WhiteChomChom.png"]
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
        "images": ["/KalujamSandwich.png"]
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
        "images": ["/KheerMouchak.png"]
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
        "images": ["/MalaiKari.png"]
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
        "images": ["/RajBhog.png"]
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
        "images": ["/KatariBhog.png"]
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
        "images": ["/Laddu.png"]
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
        "images": ["/Shandesh.png"]
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
        "images": ["/GulabJamun.png"]
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
        "images": ["/Peda.png"]
    },
    # Specialty
    {
        "orig_id": "spec-1",
        "slug": "malai-jarda-half-tray",
        "name": "Malai Jarda - Half Tray",
        "category_slug": "specialty",
        "description": "Sweet rice dessert mixed with saffron, nuts, and mini gulab jamuns.",
        "price_cents": 4500,
        "unit_label": "Half Tray",
        "product_type": "standard",
        "in_stock": True,
        "images": ["/MalaiJardaTray.png"]
    },
    {
        "orig_id": "spec-2",
        "slug": "roshmalai-half-tray",
        "name": "RoshMalai - Half Tray",
        "category_slug": "specialty",
        "description": "Soft chenna dumplings soaked in sweetened, thickened milk.",
        "price_cents": 5000,
        "unit_label": "Half Tray",
        "product_type": "standard",
        "in_stock": True,
        "images": ["/RoshMalaiTray.png"]
    },
    {
        "orig_id": "spec-3",
        "slug": "mishti-doi-16oz",
        "name": "Mishti Doi - 16 oz",
        "category_slug": "specialty",
        "description": "Classic Bengali fermented sweet yogurt.",
        "price_cents": 1000,
        "unit_label": "16 oz",
        "product_type": "standard",
        "in_stock": True,
        "images": ["/MishtiDoi.png"]
    },
    {
        "orig_id": "spec-4",
        "slug": "roshmalai-cake",
        "name": "RoshMalai Cake",
        "category_slug": "specialty",
        "description": "Vanilla sponge cake soaked in saffron milk and topped with Rasmalai pieces.",
        "price_cents": 700,
        "unit_label": "per piece",
        "product_type": "standard",
        "in_stock": True,
        "images": ["/RasMalai.png"]
    },
    {
        "orig_id": "spec-5",
        "slug": "payesh-kheer",
        "name": "Payesh Kheer",
        "category_slug": "specialty",
        "description": "Rich rice pudding made with slow-cooked milk, jaggery, and nuts.",
        "price_cents": 600,
        "unit_label": "per container",
        "product_type": "standard",
        "in_stock": True,
        "images": ["/PayeshKheer.png"]
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
        "product_type": "custom_box",
        "in_stock": True,
        "images": ["/SmallPartyTray.png"]
    },
    {
        "orig_id": "17",
        "slug": "large-party-tray",
        "name": "Large Party Tray",
        "category_slug": "party-trays",
        "description": "A grand presentation tray with 35-40 pieces of our finest sweets, featuring an assortment of chom chom, kalojam, shandesh, and laddus.",
        "price_cents": 6000,
        "unit_label": "per tray (~40 pcs)",
        "product_type": "custom_box",
        "in_stock": True,
        "images": ["/LargePartyTray.png"]
    },
    # Pitha
    {
        "orig_id": "pitha-1",
        "slug": "nokshi-pitha-10pc",
        "name": "Nokshi Pitha (10 pieces)",
        "category_slug": "pitha",
        "description": "Beautifully carved, deep-fried rice flour pitha soaked in thick jaggery syrup.",
        "price_cents": 3000,
        "unit_label": "10 pieces",
        "product_type": "standard",
        "in_stock": True,
        "preorder_only": True,
        "min_quantity": 1,
        "prep_time_hours": 24,
        "images": ["/NokshiPitha.png"]
    },
    {
        "orig_id": "pitha-2",
        "slug": "patishapta-pitha-10pc",
        "name": "Patishapta Pitha (10 pieces)",
        "category_slug": "pitha",
        "description": "Delicate crepes filled with a rich coconut and milk kheer mixture.",
        "price_cents": 3000,
        "unit_label": "10 pieces",
        "product_type": "standard",
        "in_stock": True,
        "preorder_only": True,
        "min_quantity": 1,
        "prep_time_hours": 24,
        "images": ["/Patishapta.png"]
    },
    {
        "orig_id": "pitha-3",
        "slug": "puli-pitha-10pc",
        "name": "Puli Pitha (10 pieces)",
        "category_slug": "pitha",
        "description": "Steamed or fried half-moon dumplings stuffed with coconut and jaggery.",
        "price_cents": 2500,
        "unit_label": "10 pieces",
        "product_type": "standard",
        "in_stock": True,
        "preorder_only": True,
        "min_quantity": 1,
        "prep_time_hours": 24,
        "images": ["/PuliPitha.png"]
    },
    # Mishti Per Pound
    {
        "orig_id": "mpp-1",
        "slug": "katari-bhog-lb",
        "name": "Katari Bhog",
        "category_slug": "mishti-per-pound",
        "description": "Premium regional delicacy known for its unique texture and authentic, rich taste.",
        "price_cents": 1500,
        "unit_label": "per lb",
        "product_type": "standard",
        "in_stock": True,
        "images": ["/KatariBhog.png"]
    },
    {
        "orig_id": "mpp-2",
        "slug": "brown-chom-chom-lb",
        "name": "Brown Chom Chom",
        "category_slug": "mishti-per-pound",
        "description": "Classic rich and caramelized Bengali sweet, deeply satisfying and soaked in sweet syrup.",
        "price_cents": 1300,
        "unit_label": "per lb",
        "product_type": "standard",
        "in_stock": True,
        "images": ["/BrownChomChom.png"]
    },
    {
        "orig_id": "mpp-3",
        "slug": "malai-kari-lb",
        "name": "Malai Kari",
        "category_slug": "mishti-per-pound",
        "description": "Luxuriously soft sweets drenched in a thickened, sweetened milk infused with cardamom.",
        "price_cents": 1300,
        "unit_label": "per lb",
        "product_type": "standard",
        "in_stock": True,
        "images": ["/MalaiKari.png"]
    },
    {
        "orig_id": "mpp-4",
        "slug": "shandesh-lb",
        "name": "Shandesh",
        "category_slug": "mishti-per-pound",
        "description": "Delicate milk-based sweet, perfectly balanced and adorned with a touch of tradition.",
        "price_cents": 1300,
        "unit_label": "per lb",
        "product_type": "standard",
        "in_stock": True,
        "images": ["/Shandesh.png"]
    },
    {
        "orig_id": "mpp-5",
        "slug": "kheer-mouchak-lb",
        "name": "Kheer Mouchak",
        "category_slug": "mishti-per-pound",
        "description": "A honeycomb-shaped royal delight made with chenna, soaked in saffron syrup, and covered with creamy kheer.",
        "price_cents": 1200,
        "unit_label": "per lb",
        "product_type": "standard",
        "in_stock": True,
        "images": ["/KheerMouchak.png"]
    },
    {
        "orig_id": "mpp-6",
        "slug": "kala-jamun-sandwich-lb",
        "name": "Kala Jamun Sandwich",
        "category_slug": "mishti-per-pound",
        "description": "An elegant presentation of classic Kala Jamun, beautifully layered with rich malai cream.",
        "price_cents": 1300,
        "unit_label": "per lb",
        "product_type": "standard",
        "in_stock": True,
        "images": ["/KalujamSandwich.png"]
    },
    {
        "orig_id": "mpp-7",
        "slug": "laddu-lb",
        "name": "Laddu",
        "category_slug": "mishti-per-pound",
        "description": "Perfectly round and irresistibly sweet, our laddus melt in your mouth with every bite.",
        "price_cents": 1300,
        "unit_label": "per lb",
        "product_type": "standard",
        "in_stock": True,
        "images": ["/Laddu.png"]
    },
    # {
    #     "orig_id": "mpp-8",
    #     "slug": "sponge-roshogolla-lb",
    #     "name": "Sponge RoshoGolla",
    #     "category_slug": "mishti-per-pound",
    #     "description": "Incredibly soft and spongy cottage cheese balls soaked in a light, sweet syrup.",
    #     "price_cents": 1300,
    #     "unit_label": "per lb",
    #     "product_type": "standard",
    #     "in_stock": True,
    #     "images": ["/SpongeRoshoGolla.png"]
    # },
    {
        "orig_id": "mpp-9",
        "slug": "white-chom-chom-lb",
        "name": "White Chom Chom",
        "category_slug": "mishti-per-pound",
        "description": "Soft, spongy, and delicately sweet, these traditional white treats are a timeless favorite.",
        "price_cents": 1200,
        "unit_label": "per lb",
        "product_type": "standard",
        "in_stock": True,
        "images": ["/WhiteChomChom.png"]
    },
    {
        "orig_id": "mpp-10",
        "slug": "kalojam-lb",
        "name": "Kalojam",
        "category_slug": "mishti-per-pound",
        "description": "Deep-fried to a beautiful dark color, our KaloJam offers a rich, dense texture bursting with flavor.",
        "price_cents": 1200,
        "unit_label": "per lb",
        "product_type": "standard",
        "in_stock": True,
        "images": ["/KaloJam.png"]
    },
    {
        "orig_id": "mpp-11",
        "slug": "rajbhog-lb",
        "name": "Rajbhog",
        "category_slug": "mishti-per-pound",
        "description": "A majestic, saffron-infused spongy sweet filled with premium nuts and cardamom.",
        "price_cents": 1200,
        "unit_label": "per lb",
        "product_type": "standard",
        "in_stock": True,
        "images": ["/RajBhog.png"]
    },
    {
        "orig_id": "mpp-12",
        "slug": "gulab-jamun-lb",
        "name": "Gulab Jamun",
        "category_slug": "mishti-per-pound",
        "description": "Golden, soft, and warm, soaking in a fragrant rose and cardamom syrup.",
        "price_cents": 1200,
        "unit_label": "per lb",
        "product_type": "standard",
        "in_stock": True,
        "images": ["/GulabJamun.png"]
    },
    {
        "orig_id": "mpp-13",
        "slug": "classic-roshogolla-lb",
        "name": "Classic RoshoGolla",
        "category_slug": "mishti-per-pound",
        "description": "Traditional Bengali sweet made of chenna balls boiled in light sugar syrup.",
        "price_cents": 1200,
        "unit_label": "per lb",
        "product_type": "standard",
        "in_stock": True,
        "images": ["/ClassRoshGolla.png"]
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
        "images": ["/3-piece-box.png"]
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
        "images": ["/6-piece-box.png"]
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
        "images": ["/9-piece-box.png"]
    }
]

async def seed_database():
    print(settings.async_database_url)
    # Connect directly using SQLAlchemy async session
    engine = create_async_engine(settings.async_database_url, echo=True, connect_args={"statement_cache_size": 0})
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
                product.is_active = True
                product.is_in_stock = prod_data["in_stock"]
                product.base_price_cents = prod_data["price_cents"]
                product.category_id = cat_id
                product.name = prod_data["name"]
                product.description = prod_data["description"]
                product.product_type = prod_data["product_type"]
                product.unit_label = prod_data.get("unit_label")
                # Update quantity_on_hand on re-seed only if explicitly set in data
                if "quantity_on_hand" in prod_data and product.quantity_on_hand is None:
                    product.quantity_on_hand = prod_data["quantity_on_hand"]
                # Update metadata_json (images) to sync with any changes
                product.metadata_json = {"images": prod_data["images"]}
                
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
