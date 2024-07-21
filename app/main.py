from pathlib import Path
import os
import shutil
from uuid import uuid4
from fastapi import FastAPI, File, Form, HTTPException, Depends, UploadFile, Request
from fastapi.responses import FileResponse
from pydantic import Tag
from sqlalchemy import func
from sqlalchemy.orm import Session
import uvicorn
from dbservice import SessionLocal, User, Product, Sale
from models import *
from security import *
from fastapi.middleware.cors import CORSMiddleware
import sentry_sdk
from fastapi.staticfiles import StaticFiles

sentry_sdk.init(
    dsn="https://1587107fcf7b86ca551377cc978a8e9f@o4507324311142400.ingest.us.sentry.io/4507324313239552",
    traces_sample_rate=1.0,
    profiles_sample_rate=1.0,
)

app = FastAPI()

UPLOAD_DIRECTORY = "static/images"
os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")

origins = [
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://46.101.217.191:8000"  
           
           
           
           ]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)

db = SessionLocal()

@app.post("/register", response_model=UserOut)
def register_user(user: UserRegister):
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username already registered")
    password = pwd_context.hash(user.password)
    db_user = User(username=user.username, email=user.email, password=password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    db.close()
    return db_user

@app.post("/login")
async def login(form_data: UserLogin):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users")
def get_all_users():
    users = db.query(User).all()
    db.close()
    return users

@app.post("/products")
def create_product(
    name: str = Form(...),
    price: float = Form(...),
    quantity: int = Form(...),
    product_image: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    # Save the image to a directory
    image_filename = f"{uuid4()}_{product_image.filename}"
    image_path = os.path.join("static/images", image_filename)
    with open(image_path, "wb") as image_file:
        image_file.write(product_image.file.read())

    # Create and save the product to the database
    db_product = Product(
        name=name,
        price=price,
        quantity=quantity,
        product_image=image_filename,
        user_id=current_user.id
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    db.close()

    return db_product

@app.get('/products', response_model=list[ProductModel])
def fetch_products(request: Request):
    try:
        products = db.query(Product).all()
        print("products.......", products)
        products_with_images = []
        for product in products:
            image_filename = product.product_image  # assuming product_image is the filename in the database
            base_url = str(request.base_url)
            image_url = f"{base_url.rstrip('/')}/static/images/{image_filename}"
            print("Image URL:", image_url)
            products_with_images.append(ProductModel(
                id=product.id,
                name=product.name,
                quantity=product.quantity,
                price=product.price,
                product_image=image_url  # matching the field name expected by your React component
            ))
        return products_with_images
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/products/{pid}")
async def update_item(pid: int, product: ProductUpdate, response_model=Product):
    prod = db.query(Product).filter(Product.id == pid).first()
    if not prod:
        raise HTTPException(status_code=404, detail="product does not exist")

    if product.name is not None:
        prod.name = product.name
    if product.price is not None:
        prod.price = product.price
    if product.quantity is not None:
        prod.quantity = product.quantity
    db.commit()
    prod = db.query(Product).filter(Product.id == pid).first()
    return prod

@app.get("/sales")
def get_sales(current_user: User = Depends(get_current_user)):
    try:
        sales = db.query(Sale).filter(Sale.user_id == current_user.id).all()
        db.close()
        return sales
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/sales")
def create_sales(sale: SalesCreate, current_user: User = Depends(get_current_user)):
    try:
        db_sale = Sale(**sale.model_dump(), user_id=current_user.id)
        db.add(db_sale)
        db.commit()
        db.refresh(db_sale)
        return db_sale
    except Exception as e:
        db.rollback()
        db.close()
        raise HTTPException(status_code=422, detail=str(e))

@app.get("/dashboard")
def dashboard(current_user: User = Depends(get_current_user)):
    try:
        sales_per_day = db.query(
            func.date(Sale.created_at).label('date'),
            func.sum(Sale.stock_quantity * Product.price).label('total_sales')
        ).join(Product).group_by(
            func.date(Sale.created_at)
        ).filter(Sale.user_id == current_user.id).all()

        sales_data = [{'date': str(day), 'total_sales': sales} for day, sales in sales_per_day]

        sales_per_product = db.query(
            Product.name,
            func.sum(Sale.stock_quantity*Product.price).label('sales_product')
        ).join(Sale).group_by(
            Product.name
        ).filter(Sale.user_id == current_user.id).all()

        salesproduct_data = [{'name': name, 'sales_product': sales_product} for name, sales_product in sales_per_product]

        return {'sales_data': sales_data, 'salesproduct_data': salesproduct_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload-image/")
async def upload_image(file: UploadFile = File(...)):
    file_path = Path(UPLOAD_DIRECTORY) / file.filename
    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file: {e}")
    return {"filename": file.filename}

@app.get("/images/{filename}", tags=["Images"])
async def get_image(filename: str):
    file_path = Path(UPLOAD_DIRECTORY) / filename
    if file_path.exists():
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="Image not found")

@app.put("/images/{filename}")
async def update_image(filename: str, new_filename: str = None, file: UploadFile = File(...)):
    file_path = Path(UPLOAD_DIRECTORY) / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")

    new_file_path = Path(UPLOAD_DIRECTORY) / (new_filename if new_filename else filename)
    
    if new_file_path != file_path and new_file_path.exists():
        raise HTTPException(status_code=400, detail="New filename already exists")

    with new_file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    if new_file_path != file_path:
        file_path.unlink()

    return {"filename": new_file_path.name, "message": "Image updated successfully"}

# if __name__ == "__main__":
#     uvicorn.run(app, host="0.0.0.0", port=8000)
