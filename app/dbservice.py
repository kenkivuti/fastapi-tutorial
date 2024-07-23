from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func


SQLALCHEMY_DATABASE_URL = "postgresql://postgres:Kenkivuti254@172.17.0.1:5432/fastapidatabase"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()



class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    price = Column(Integer, nullable=False)
    quantity=Column(Integer,default=0)
    user_id=Column(Integer,ForeignKey("users.id"),nullable=True)
    product_image = Column(String)
# relationship
    sales= relationship("Sale",back_populates='products')
    # username=Column(String,ForeignKey('users.username'),nullable=True)
    user= relationship("User", back_populates="products")



class Sale(Base):
    __tablename__='sales'
    id=Column(Integer,primary_key=True)
    pid = Column(Integer, ForeignKey('products.id'), nullable=False)
    stock_quantity=Column(Integer,nullable=False)
    created_at=Column(DateTime,default=func.now() ,nullable=False)
    # relationship
    products=relationship("Product",back_populates='sales')
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)



class User(Base):
    __tablename__='users'
    id = Column(Integer,primary_key=True, nullable=False)
    username= Column(String(255),unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password=Column(String(255),nullable=False)
    # relationship
    products = relationship("Product", back_populates="user")

Base.metadata.create_all(bind=engine)
# Base.metadata.drop_all(bind=engine)