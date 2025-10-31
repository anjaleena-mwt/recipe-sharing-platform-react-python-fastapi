from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(30), unique=True, nullable=False)
    user_email = Column(String(30), unique=True, nullable=False)
    password = Column(String(200), nullable=False)
    address = Column(String(200), nullable=False)  
    phone_number = Column(String(20), nullable=False)

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)

class Recipe(Base):
    __tablename__ = "recipes"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)
    ingredients = Column(Text, nullable=False)   
    methods = Column(Text, nullable=False)      
    youtube_link = Column(String(300))    
    image_url = Column(String(300))         
    user_id = Column(Integer, ForeignKey("users.id"))
    category_id = Column(Integer, ForeignKey("categories.id"))
    approved = Column(Boolean, default=False)

    user = relationship("User")
    category = relationship("Category")
