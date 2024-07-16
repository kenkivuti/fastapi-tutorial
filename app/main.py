from fastapi import FastAPI, HTTPException, Depends
from datetime import timedelta
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func
import uvicorn
from dbservice import SessionLocal, User, Product, Sale
from models import *
from security import *
from fastapi.middleware.cors import CORSMiddleware
import sentry_sdk

sentry_sdk.init(
    dsn="https://1587107fcf7b86ca551377cc978a8e9f@o4507324311142400.ingest.us.sentry.io/4507324313239552",
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    traces_sample_rate=1.0,
    # Set profiles_sample_rate to 1.0 to profile 100%
    # of sampled transactions.
    # We recommend adjusting this value in production.
    profiles_sample_rate=1.0,
)


app = FastAPI()


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
        raise HTTPException(
            status_code=400, detail="Username already registered")
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

    #  for products


@app.get("/products")
def get_products(current_user: User = Depends(get_current_user)):
    products = db.query(Product).filter(
        Product.user_id == current_user.id).all()
    db.close()
    return products


@app.post("/products")
def create_product(product: ProductCreate, current_user: User = Depends(get_current_user)):

    db_product = Product(**product.model_dump(), user_id=current_user.id)
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    db.close()

    return db_product


@app.put("/products/{pid}")
async def update_item(pid: int, product: ProductUpdate, response_model=Product):
    prod = db.query(Product).filter(Product.id == pid).first()
    if not prod:
        raise HTTPException(status_code=404, detail="product does not exist")

    if not prod.name == product.name and product.name != None:
        prod.name = product.name

    if not prod.price == product.price and product.price != None:
        prod.price = product.price

    if not prod.stock_quantity == product.stock_quantity and product.stock_quantity != None:
        prod.stock_quantity = product.stock_quantity
    db.commit()

    prod = db.query(Product).filter(Product.id == pid).first()
    return prod


#     for sales

@app.get("/sales")
def get_sales(current_user: User = Depends(get_current_user)):
    try:
        sales = db.query(Sale).filter(
            Sale.user_id == current_user.id).all()
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
        # Raise HTTPException with 422 status code and error message
        raise HTTPException(status_code=422, detail=str(e))

    # dashboard


@app.get("/dashboard")
def dashboard(current_user: User = Depends(get_current_user)):
    try:
        sales_per_day = db.query(
            # extracts date from created at
            func.date(Sale.created_at).label('date'),
            # calculate the total number of sales per day
            func.sum(Sale.stock_quantity * Product.price).label('total_sales')
        ).join(Product).group_by(
            func.date(Sale.created_at)
        ).filter( Sale.user_id == current_user.id).all()

        #  to JSON format

        sales_data = [{'date': str(day), 'total_sales': sales}
                      for day, sales in sales_per_day]
    # Query sales per product for bar graph
        sales_per_product = db.query(
            Product.name,
            func.sum(Sale.stock_quantity*Product.price).label('sales_product')
        ).join(Sale).group_by(
            Product.name
        ).filter( Sale.user_id == current_user.id).all()

        #  JSON format

        salesproduct_data = [{'name': name, 'sales_product': sales_product}
                             for name, sales_product in sales_per_product]

        return ({'sales_data': sales_data, 'salesproduct_data': salesproduct_data})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# if __name__ == "__main__":
#     uvicorn.run(app, host="0.0.0.0", port=8000)
