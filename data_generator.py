import asyncio
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from faker import Faker
import random
import json
from models import (
    User, Product, Interaction, Session, UserSegment, ProductCategory,
    InteractionType, GenerationRequest
)
from config import settings

class DataGenerator:
    def __init__(self):
        self.faker = Faker()
        self.users_cache = []
        self.products_cache = []
        self.sessions_cache = {}
        self.product_prices = {
            ProductCategory.ELECTRONICS: (50, 2000),
            ProductCategory.CLOTHING: (10, 200),
            ProductCategory.HOME: (20, 500),
            ProductCategory.BEAUTY: (15, 100),
            ProductCategory.SPORTS: (30, 300),
            ProductCategory.BOOKS: (10, 50),
            ProductCategory.TOYS: (15, 80),
            ProductCategory.AUTOMOTIVE: (50, 800),
            ProductCategory.GROCERY: (5, 50),
            ProductCategory.HEALTH: (10, 150)
        }

    def generate_user(self) -> User:
        user_id = str(uuid.uuid4())
        email = self.faker.email()
        first_name = self.faker.first_name()
        last_name = self.faker.last_name()
        age = random.randint(18, 80)
        gender = random.choice(['male', 'female', 'other'])
        location = self.faker.city() + ', ' + self.faker.country_code()

        segment_weights = [0.4, 0.35, 0.2, 0.05]
        user_segment = random.choices(list(UserSegment), weights=segment_weights)[0]

        registration_date = self.faker.date_time_between(start_date='-2y', end_date='now')
        last_active = self.faker.date_time_between(start_date=registration_date, end_date='now')

        segment_spending = {
            UserSegment.CASUAL: (0, 500),
            UserSegment.REGULAR: (500, 2000),
            UserSegment.POWER: (2000, 10000),
            UserSegment.PREMIUM: (10000, 50000)
        }
        total_spent = random.uniform(*segment_spending[user_segment])

        segment_orders = {
            UserSegment.CASUAL: (0, 10),
            UserSegment.REGULAR: (10, 50),
            UserSegment.POWER: (50, 200),
            UserSegment.PREMIUM: (200, 1000)
        }
        order_count = random.randint(*segment_orders[user_segment])

        preferences = random.sample(list(ProductCategory), k=random.randint(1, 4))
        device_type = random.choice(['mobile', 'desktop', 'tablet'])
        browser = random.choice(['chrome', 'firefox', 'safari', 'edge'])

        user = User(
            user_id=user_id,
            email=email,
            first_name=first_name,
            last_name=last_name,
            age=age,
            gender=gender,
            location=location,
            user_segment=user_segment,
            registration_date=registration_date,
            last_active=last_active,
            total_spent=total_spent,
            order_count=order_count,
            preferences=preferences,
            device_type=device_type,
            browser=browser
        )

        self.users_cache.append(user)
        return user

    def generate_product(self) -> Product:
        product_id = str(uuid.uuid4())
        category = random.choice(list(ProductCategory))
        price = random.uniform(*self.product_prices[category])
        name = self.faker.catch_phrase()
        description = self.faker.text(max_nb_chars=200)
        brand = self.faker.company()
        rating = random.uniform(3.0, 5.0)
        review_count = random.randint(0, 5000)
        in_stock = random.random() > 0.05
        popularity_score = random.random()

        tags = self._generate_tags(category)
        created_at = self.faker.date_time_between(start_date='-1y', end_date='now')
        updated_at = self.faker.date_time_between(start_date=created_at, end_date='now')

        product = Product(
            product_id=product_id,
            name=name,
            category=category,
            price=price,
            description=description,
            brand=brand,
            rating=rating,
            review_count=review_count,
            in_stock=in_stock,
            popularity_score=popularity_score,
            tags=tags,
            created_at=created_at,
            updated_at=updated_at
        )

        self.products_cache.append(product)
        return product

    def _generate_tags(self, category: ProductCategory) -> List[str]:
        tag_pools = {
            ProductCategory.ELECTRONICS: ['wireless', 'smart', 'portable', 'hd', 'bluetooth', 'touchscreen'],
            ProductCategory.CLOTHING: ['cotton', 'formal', 'casual', 'summer', 'winter', 'vintage'],
            ProductCategory.HOME: ['modern', 'vintage', 'compact', 'luxury', 'minimalist', 'decorative'],
            ProductCategory.BEAUTY: ['organic', 'natural', 'luxury', 'professional', 'skincare', 'moisturizing'],
            ProductCategory.SPORTS: ['outdoor', 'fitness', 'professional', 'lightweight', 'durable', 'waterproof'],
            ProductCategory.BOOKS: ['bestseller', 'fiction', 'non-fiction', 'educational', 'award-winning', 'classic'],
            ProductCategory.TOYS: ['educational', 'interactive', 'safe', 'creative', 'battery-operated', 'wooden'],
            ProductCategory.AUTOMOTIVE: ['durable', 'high-performance', 'fuel-efficient', 'luxury', 'sport', 'electric'],
            ProductCategory.GROCERY: ['organic', 'fresh', 'local', 'gluten-free', 'premium', 'artisanal'],
            ProductCategory.HEALTH: ['natural', 'vitamin-rich', 'organic', 'doctor-recommended', 'clinically-tested', 'safe']
        }
        return random.sample(tag_pools.get(category, ['premium', 'quality']), k=random.randint(2, 4))

    def generate_session(self, user: User) -> Session:
        session_id = str(uuid.uuid4())
        start_time = self.faker.date_time_between(start_date='-30d', end_date='now')
        duration = random.randint(60, 3600)
        end_time = start_time + timedelta(seconds=duration)

        device_type = random.choice(['mobile', 'desktop', 'tablet'])
        browser = random.choice(['chrome', 'firefox', 'safari', 'edge'])
        ip_address = self.faker.ipv4()
        location = self.faker.city()

        session = Session(
            session_id=session_id,
            user_id=user.user_id,
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            device_type=device_type,
            browser=browser,
            ip_address=ip_address,
            location=location,
            interactions_count=0,
            total_revenue=0.0,
            products_viewed=[],
            products_purchased=[]
        )

        self.sessions_cache[session_id] = session
        return session

    def generate_interaction(self, user: User, product: Product, session: Session) -> Interaction:
        interaction_id = str(uuid.uuid4())
        interaction_type = self._get_weighted_interaction_type(user.user_segment)
        timestamp = self.faker.date_time_between(start_date=session.start_time, end_date=session.end_time)

        duration = None
        if interaction_type == InteractionType.VIEW:
            duration = random.randint(5, 300)

        quantity = 1
        revenue = 0.0

        if interaction_type == InteractionType.PURCHASE:
            quantity = random.randint(1, 3)
            revenue = product.price * quantity
            session.total_revenue += revenue
            if product.product_id not in session.products_purchased:
                session.products_purchased.append(product.product_id)

        device_info = f"{session.device_type} - {session.browser}"
        page_url = f"/products/{product.category}/{product.product_id}"
        referrer = random.choice(['/home', '/search', '/category', '/recommendations', None])

        if product.product_id not in session.products_viewed:
            session.products_viewed.append(product.product_id)

        session.interactions_count += 1

        return Interaction(
            interaction_id=interaction_id,
            user_id=user.user_id,
            product_id=product.product_id,
            interaction_type=interaction_type,
            timestamp=timestamp,
            session_id=session.session_id,
            duration=duration,
            quantity=quantity,
            revenue=revenue,
            device_info=device_info,
            page_url=page_url,
            referrer=referrer
        )

    def _get_weighted_interaction_type(self, user_segment: UserSegment) -> InteractionType:
        weights = {
            UserSegment.CASUAL: {
                InteractionType.VIEW: 0.6,
                InteractionType.CLICK: 0.25,
                InteractionType.ADD_TO_CART: 0.08,
                InteractionType.PURCHASE: 0.02,
                InteractionType.WISHLIST: 0.05
            },
            UserSegment.REGULAR: {
                InteractionType.VIEW: 0.5,
                InteractionType.CLICK: 0.2,
                InteractionType.ADD_TO_CART: 0.15,
                InteractionType.PURCHASE: 0.08,
                InteractionType.WISHLIST: 0.07
            },
            UserSegment.POWER: {
                InteractionType.VIEW: 0.4,
                InteractionType.CLICK: 0.15,
                InteractionType.ADD_TO_CART: 0.2,
                InteractionType.PURCHASE: 0.15,
                InteractionType.WISHLIST: 0.1
            },
            UserSegment.PREMIUM: {
                InteractionType.VIEW: 0.35,
                InteractionType.CLICK: 0.1,
                InteractionType.ADD_TO_CART: 0.25,
                InteractionType.PURCHASE: 0.2,
                InteractionType.WISHLIST: 0.1
            }
        }

        segment_weights = weights.get(user_segment, weights[UserSegment.CASUAL])
        return random.choices(list(segment_weights.keys()), weights=list(segment_weights.values()))[0]

    def generate_users_batch(self, count: int) -> List[User]:
        return [self.generate_user() for _ in range(count)]

    def generate_products_batch(self, count: int) -> List[Product]:
        return [self.generate_product() for _ in range(count)]

    def generate_interactions_batch(self, count: int) -> List[Interaction]:
        interactions = []

        for _ in range(count):
            if not self.users_cache:
                self.generate_users_batch(100)
            if not self.products_cache:
                self.generate_products_batch(200)

            user = random.choice(self.users_cache)
            product = random.choice(self.products_cache)

            session_id = random.choice(list(self.sessions_cache.keys())) if self.sessions_cache else None
            if not session_id or random.random() > 0.7:
                session = self.generate_session(user)
            else:
                session = self.sessions_cache[session_id]

            interaction = self.generate_interaction(user, product, session)
            interactions.append(interaction)

        return interactions

    def generate_realistic_behavior(self, user_id: str) -> List[Interaction]:
        user = next((u for u in self.users_cache if u.user_id == user_id), None)
        if not user:
            user = self.generate_user()

        session = self.generate_session(user)
        interactions = []

        preferences = user.preferences
        interaction_count = random.randint(3, 15)

        for i in range(interaction_count):
            if random.random() < 0.8 and self.products_cache:
                product = random.choice([p for p in self.products_cache if p.category in preferences])
            else:
                product = random.choice(self.products_cache) if self.products_cache else self.generate_product()

            interaction = self.generate_interaction(user, product, session)
            interactions.append(interaction)

        return interactions

    async def generate_data_stream(self, data_type: str, count: int, rate: int):
        delay = 1.0 / rate if rate > 0 else 0.1

        for i in range(count):
            if data_type == "users":
                yield self.generate_user()
            elif data_type == "products":
                yield self.generate_product()
            elif data_type == "interactions":
                for interaction in self.generate_interactions_batch(1):
                    yield interaction

            if i < count - 1:
                await asyncio.sleep(delay)

    def to_json(self, obj) -> str:
        if hasattr(obj, 'dict'):
            return json.dumps(obj.dict(), default=str)
        return json.dumps(obj, default=str)

generator = DataGenerator()