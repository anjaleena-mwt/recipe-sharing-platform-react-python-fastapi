import re
import os
import uuid #give unique names to uploaded files
from fastapi import FastAPI, HTTPException, Depends, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from fastapi.staticfiles import StaticFiles

from database import session, engine        
from database_models import Base, User, Category, Recipe
from models import UserCreate, UserLogin, CategoryCreate, RecipeApproveReject

# Regex for phone number validation
phone_re = re.compile(r'^\+?\d{7,15}$')

# Create DB tables if not present
Base.metadata.create_all(bind=engine)

# Starts the FastAPI
app = FastAPI()

# Allow React app to call API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

 # This creates a database connection for each request and closes it afterward
def get_db():
    db = session()
    try:
        yield db
    finally:
        db.close()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Mount static files so they are served at /uploads/...
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

@app.post("/register", status_code=status.HTTP_201_CREATED)
def register(user: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(
        (User.username == user.username) | (User.user_email == user.user_email)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username or email already exists")

    if user.password != user.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    if not phone_re.match(user.phone_number):
        raise HTTPException(status_code=400, detail="Invalid phone number")

    db_user = User(
        username=user.username,
        user_email=user.user_email,
        password=user.password,
        address=user.address,
        phone_number=user.phone_number
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return {
        "message": "User registered successfully",
        "user_id": db_user.id,
        "username": db_user.username,
        "user_email": db_user.user_email,
        "address": db_user.address,
        "phone_number": db_user.phone_number
    }

@app.post("/login")
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.user_email == payload.user_email).first()
    if not user or user.password != payload.password:
        raise HTTPException(status_code=400, detail="Invalid email or password")

    return {
        "message": "Login successful",
        "username": user.username,
        "user_id": user.id,
        "user_email": user.user_email,
        "address": user.address,
        "phone_number": user.phone_number
    }

@app.get("/")
def greet():
    return {"message": "Welcome to RecipeRealm"}

# ---------------- Admin endpoints ----------------
@app.post("/admin/add-category")
def add_category(category: CategoryCreate, db: Session = Depends(get_db)):
    existing = db.query(Category).filter(Category.name == category.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Category already exists")
    db_category = Category(name=category.name)
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return {"message": "Category added", "id": db_category.id, "name": db_category.name}

@app.get("/admin/view-recipes")
def view_recipes(db: Session = Depends(get_db)):
    recipes = db.query(Recipe).all()
    result = []
    for r in recipes:
        result.append({
            "id": r.id,
            "title": r.title,
            "ingredients": r.ingredients,
            "methods": r.methods,
            "youtube_link": r.youtube_link,
            "user_id": r.user_id,
            "username": r.user.username if r.user else None,
            "category_id": r.category_id,
            "category_name": r.category.name if r.category else None,
            "approved": bool(r.approved)
        })
    return result


@app.post("/admin/approve-reject")
def approve_reject(data: RecipeApproveReject, db: Session = Depends(get_db)):
    recipe = db.query(Recipe).filter(Recipe.id == data.recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    recipe.approved = bool(data.approve)
    db.commit()
    return {"message": "Recipe updated", "id": recipe.id, "approved": recipe.approved}
from models import RecipeCreate, RecipeOut

# Create a recipe (only registered users )
@app.post("/recipes", response_model=RecipeOut)
async def create_recipe(
    title: str = Form(...),
    ingredients: str = Form(...),
    methods: str = Form(...),
    youtube_link: Optional[str] = Form(None),
    category_id: int = Form(...),
    user_id: int = Form(...),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    # validate user and category
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid user")

    cat = db.query(Category).filter(Category.id == int(category_id)).first()
    if not cat:
        raise HTTPException(status_code=400, detail="Invalid category")

    image_url = None
    if image:
        # basic validation: allow only common image types
        filename = image.filename
        ext = (os.path.splitext(filename)[1] or "").lower()
        allowed = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
        if ext not in allowed:
            raise HTTPException(status_code=400, detail="Unsupported image type")

        # create unique filename
        unique_name = f"{uuid.uuid4().hex}{ext}"
        dest = os.path.join(UPLOAD_DIR, unique_name)

        # save file
        with open(dest, "wb") as f:
            content = await image.read()
            f.write(content)

        # set public path (served by StaticFiles at /uploads)
        image_url = f"/uploads/{unique_name}"

    # create recipe row
    recipe = Recipe(
        title=title,
        ingredients=ingredients,
        methods=methods,
        youtube_link=youtube_link,
        image_url=image_url,
        user_id=int(user_id),
        category_id=int(category_id),
        approved=False
    )
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return recipe

# List recipes (public)
@app.get("/recipes")
def list_recipes(q: Optional[str] = None, category: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(Recipe).filter(Recipe.approved == True)  
    if q:
        qlow = f"%{q.lower()}%"
        query = query.filter(Recipe.title.ilike(qlow))
    if category:
        query = query.filter(Recipe.category_id == category)
    results = query.all()
    return [
        {
            "id": r.id,
            "title": r.title,
            "ingredients": r.ingredients,
            "methods": r.methods,
            "youtube_link": r.youtube_link,
            "image_url": r.image_url,
            "user_id": r.user_id,
            "username": r.user.username if r.user else None,
            "category_id": r.category_id,
            "category_name": r.category.name if r.category else None,
            "approved": bool(r.approved)
        }
        for r in results
    ]

# place this BEFORE the /recipes/{recipe_id} route
@app.get("/recipes/autocomplete")
def autocomplete_recipes(q: Optional[str] = None, db: Session = Depends(get_db)):
    # don't search for very short input
    if not q or len(q.strip()) < 2:
        return []

    pattern = f"%{q.lower()}%"
    results = (
        db.query(Recipe)
        .filter(Recipe.approved == True)
        .filter(Recipe.title.ilike(pattern))
        .limit(10)
        .all()
    )

    # return a plain list of objects
    return [{"id": r.id, "title": r.title} for r in results]

# Get recipe by id (for viewing details)
@app.get("/recipes/{recipe_id}")
def get_recipe(recipe_id: int, db: Session = Depends(get_db)):
    r = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return {
        "id": r.id,
        "title": r.title,
        "ingredients": r.ingredients,
        "methods": r.methods,
        "youtube_link": r.youtube_link,
        "image_url": r.image_url,
        "user_id": r.user_id,
        "username": r.user.username if r.user else None,
        "category_id": r.category_id,
        "category_name": r.category.name if r.category else None,
        "approved": bool(r.approved)
    }
#List all categories for the admin
@app.get("/admin/categories")
def list_categories(db: Session = Depends(get_db)):
    cats = db.query(Category).all()
    return [{"id": c.id, "name": c.name} for c in cats]

