from datetime import datetime, timedelta
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, validator
from enum import Enum

class UserSegment(str, Enum):
    CASUAL = "casual"
    REGULAR = "regular"
    POWER = "power"
    PREMIUM = "premium"

class ProductCategory(str, Enum):
    ELECTRONICS = "electronics"
    CLOTHING = "clothing"
    HOME = "home"
    BEAUTY = "beauty"
    SPORTS = "sports"
    BOOKS = "books"
    TOYS = "toys"
    AUTOMOTIVE = "automotive"
    GROCERY = "grocery"
    HEALTH = "health"

class InteractionType(str, Enum):
    VIEW = "view"
    CLICK = "click"
    ADD_TO_CART = "add_to_cart"
    PURCHASE = "purchase"
    WISHLIST = "wishlist"
    REVIEW = "review"
    SHARE = "share"

class User(BaseModel):
    user_id: str
    email: str
    first_name: str
    last_name: str
    age: int = Field(..., ge=18, le=80)
    gender: str
    location: str
    user_segment: UserSegment
    registration_date: datetime
    last_active: datetime
    total_spent: float = Field(..., ge=0)
    order_count: int = Field(..., ge=0)
    preferences: List[ProductCategory] = []
    device_type: str
    browser: str

    @validator('age')
    def validate_age(cls, v):
        if v < 18 or v > 80:
            raise ValueError('Age must be between 18 and 80')
        return v

class Product(BaseModel):
    product_id: str
    name: str
    category: ProductCategory
    price: float = Field(..., gt=0)
    description: str
    brand: str
    rating: float = Field(..., ge=0, le=5)
    review_count: int = Field(..., ge=0)
    in_stock: bool
    popularity_score: float = Field(..., ge=0, le=1)
    tags: List[str] = []
    created_at: datetime
    updated_at: datetime

    @validator('price')
    def validate_price(cls, v):
        if v <= 0:
            raise ValueError('Price must be positive')
        return v

class Interaction(BaseModel):
    interaction_id: str
    user_id: str
    product_id: str
    interaction_type: InteractionType
    timestamp: datetime
    session_id: str
    duration: Optional[int] = None
    quantity: Optional[int] = Field(1, ge=1)
    revenue: Optional[float] = Field(0, ge=0)
    device_info: str
    page_url: Optional[str] = None
    referrer: Optional[str] = None

    @validator('quantity')
    def validate_quantity(cls, v, values):
        if 'interaction_type' in values and values['interaction_type'] == InteractionType.PURCHASE:
            if v < 1:
                raise ValueError('Quantity must be at least 1 for purchases')
        return v

class Session(BaseModel):
    session_id: str
    user_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[int] = None
    device_type: str
    browser: str
    ip_address: Optional[str] = None
    location: Optional[str] = None
    interactions_count: int = Field(0, ge=0)
    total_revenue: float = Field(0, ge=0)
    products_viewed: List[str] = []
    products_purchased: List[str] = []

class GenerationRequest(BaseModel):
    count: int = Field(100, ge=1, le=10000)
    rate: Optional[int] = Field(None, ge=1, le=1000)
    stream: bool = False
    batch_size: int = Field(100, ge=1, le=1000)

class GenerationResponse(BaseModel):
    success: bool
    message: str
    count_generated: int
    time_taken: float
    rate_per_second: float

class StreamStatus(BaseModel):
    is_running: bool
    start_time: Optional[datetime] = None
    total_generated: int = 0
    current_rate: int = 0
    target_rate: int = 0
    active_streams: List[str] = []