from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class UserCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=30)
    user_email: EmailStr
    password: str = Field(..., min_length=6)
    confirm_password: str = Field(..., min_length=6)
    address: str = Field(..., min_length=5, max_length=200)
    phone_number: str = Field(..., min_length=7, max_length=15)

class UserLogin(BaseModel):
    user_email: EmailStr
    password: str = Field(..., min_length=1)

class CategoryCreate(BaseModel):
    name: str

class RecipeApproveReject(BaseModel):
    recipe_id: int
    approve: bool

class RecipeCreate(BaseModel):
    title: str
    ingredients: str
    methods: str
    youtube_link: str
    image_url: str
    category_id: int
    user_id: int   

class RecipeOut(BaseModel): # Used when sending recipe data back to the frontend
    id: int
    title: str
    ingredients: str
    methods: str
    youtube_link: Optional[str] = None
    image_url: Optional[str] = None
    user_id: int
    approved: bool

class Config:
    orm_mode = True