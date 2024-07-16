from typing import List
from pydantic import BaseModel
from datetime import datetime




class ProductModel(BaseModel):
    name: str
    price: int
    quantity:int 
    
class ProductBase(ProductModel):
    id: int 
    user_id: int 


class ProductUpdate(BaseModel):
    name: str | None = None
    price: float | None = None
    quantity:int | None = None

class ProductupdateOut(ProductUpdate):

    id : int


class ProductCreate(ProductModel):
    pass


class SalesModel(BaseModel):
    pid: int
    stock_quantity:int
    created_at: datetime


class SalesCreate(SalesModel):
    pass


class Sales(SalesModel):
    id : int
    user_id: int


class SalesUpdate(BaseModel):
    pid:ProductBase | None = None
    quantity:int | None = None
    created_at: datetime | None = None


class SalesUpdateOut(SalesUpdate):
    id: int
 

class UserOut(BaseModel):
    username : str
    email: str


class UserRegister(UserOut):
   password: str


class UserLogin(BaseModel):
    username : str
    password: str



class SaleData(BaseModel):
    date: str
    total_sales: float

class ProductSalesData(BaseModel):
    name: str
    sales_product: float

# class Dashboard(BaseModel):
#     sales_data: List[SaleData]
#     salesproduct_data: List[ProductSalesData]
    

    class config:
        orm_mode = True