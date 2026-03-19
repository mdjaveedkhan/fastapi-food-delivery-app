from fastapi import FastAPI, HTTPException, Query, Response
from pydantic import BaseModel, Field
from typing import Optional
import math

app = FastAPI()

# DATA
menu = [
    {"id": 1, "name": "Pizza", "price": 200, "category": "Pizza", "is_available": True},
    {"id": 2, "name": "Burger", "price": 150, "category": "Burger", "is_available": True},
    {"id": 3, "name": "Coke", "price": 50, "category": "Drink", "is_available": True},
    {"id": 4, "name": "Pasta", "price": 180, "category": "Pizza", "is_available": False},
    {"id": 5, "name": "Ice Cream", "price": 120, "category": "Dessert", "is_available": True},
    {"id": 6, "name": "Sandwich", "price": 100, "category": "Burger", "is_available": True}
]

orders = []
cart = []
order_counter = 1


# HELPER FUNCTIONS
def find_menu_item(item_id):
    for item in menu:
        if item["id"] == item_id:
            return item
    return None


def calculate_bill(price, quantity, order_type):
    total = price * quantity
    if order_type == "delivery":
        total += 30
    return total


def filter_menu_logic(category, max_price, is_available):
    result = []
    for item in menu:
        if category is not None and item["category"].lower() != category.lower():
            continue
        if max_price is not None and item["price"] > max_price:
            continue
        if is_available is not None and item["is_available"] != is_available:
            continue
        result.append(item)
    return result


# PYDANTIC MODELS
class OrderRequest(BaseModel):
    customer_name: str = Field(..., min_length=2)
    item_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0, le=20)
    delivery_address: str = Field(..., min_length=10)
    order_type: str = "delivery"


class NewMenuItem(BaseModel):
    name: str = Field(..., min_length=2)
    price: int = Field(..., gt=0)
    category: str = Field(..., min_length=2)
    is_available: bool = True


class CheckoutRequest(BaseModel):
    customer_name: str
    delivery_address: str


# HOME ROUTE
@app.get("/")
def home():
    return {"message": "Welcome to QuickBite Food Delivery"}

# Get all menu
@app.get("/menu")
def get_menu():
    return {"total": len(menu), "items": menu}


# Summary
@app.get("/menu/summary")
def summary():
    available = 0
    unavailable = 0
    categories = set()

    for item in menu:
        if item["is_available"]:
            available += 1
        else:
            unavailable += 1
        categories.add(item["category"])

    return {
        "total": len(menu),
        "available": available,
        "unavailable": unavailable,
        "categories": list(categories)
    }


# Filter
@app.get("/menu/filter")
def filter_menu(category: Optional[str] = None,
                max_price: Optional[int] = None,
                is_available: Optional[bool] = None):

    result = filter_menu_logic(category, max_price, is_available)
    return {"count": len(result), "items": result}


# Search
@app.get("/menu/search")
def search(keyword: str):
    result = []

    for item in menu:
        if keyword.lower() in item["name"].lower() or keyword.lower() in item["category"].lower():
            result.append(item)

    if not result:
        return {"message": "No items found"}

    return {"count": len(result), "items": result}


# Sort
@app.get("/menu/sort")
def sort(sort_by: str = "price", order: str = "asc"):

    if sort_by not in ["price", "name", "category"]:
        raise HTTPException(400, "Invalid sort field")

    reverse = True if order == "desc" else False

    sorted_data = sorted(menu, key=lambda x: x[sort_by], reverse=reverse)

    return {"sorted_by": sort_by, "order": order, "items": sorted_data}


# Pagination
@app.get("/menu/page")
def paginate(page: int = 1, limit: int = 3):

    start = (page - 1) * limit
    data = menu[start:start + limit]

    total_pages = math.ceil(len(menu) / limit)

    return {
        "page": page,
        "limit": limit,
        "total": len(menu),
        "total_pages": total_pages,
        "items": data
    }


# Combined Browse
@app.get("/menu/browse")
def browse(keyword: Optional[str] = None,
           sort_by: str = "price",
           order: str = "asc",
           page: int = 1,
           limit: int = 4):

    data = menu

    if keyword:
        data = [i for i in data if keyword.lower() in i["name"].lower()]

    reverse = True if order == "desc" else False
    data = sorted(data, key=lambda x: x[sort_by], reverse=reverse)

    start = (page - 1) * limit
    paginated = data[start:start + limit]

    return {
        "total": len(data),
        "page": page,
        "items": paginated
    }


# Get by ID
@app.get("/menu/{item_id}")
def get_item(item_id: int):
    item = find_menu_item(item_id)
    if not item:
        return {"error": "Item not found"}
    return item


# MENU CRUD

@app.post("/menu")
def add_item(item: NewMenuItem, response: Response):

    for m in menu:
        if m["name"].lower() == item.name.lower():
            raise HTTPException(400, "Item already exists")

    new_id = len(menu) + 1
    new_item = item.dict()
    new_item["id"] = new_id

    menu.append(new_item)
    response.status_code = 201

    return new_item


@app.put("/menu/{item_id}")
def update_item(item_id: int,
                price: Optional[int] = None,
                is_available: Optional[bool] = None):

    item = find_menu_item(item_id)

    if not item:
        raise HTTPException(404, "Item not found")

    if price is not None:
        item["price"] = price

    if is_available is not None:
        item["is_available"] = is_available

    return item


@app.delete("/menu/{item_id}")
def delete_item(item_id: int):

    item = find_menu_item(item_id)

    if not item:
        raise HTTPException(404, "Item not found")

    if item["is_available"]:
        raise HTTPException(400, "Cannot delete available item")

    menu.remove(item)

    return {"message": f"{item['name']} deleted"}


# ORDERS

@app.get("/orders")
def get_orders():
    return {"total_orders": len(orders), "orders": orders}


@app.post("/orders")
def create_order(order: OrderRequest):
    global order_counter

    item = find_menu_item(order.item_id)

    if not item:
        raise HTTPException(404, "Item not found")

    if not item["is_available"]:
        raise HTTPException(400, "Item not available")

    total = calculate_bill(item["price"], order.quantity, order.order_type)

    new_order = {
        "order_id": order_counter,
        "customer_name": order.customer_name,
        "item": item["name"],
        "quantity": order.quantity,
        "total_price": total
    }

    orders.append(new_order)
    order_counter += 1

    return new_order


@app.get("/orders/search")
def order_search(name: str):
    result = []

    for o in orders:
        if name.lower() in o["customer_name"].lower():
            result.append(o)

    return result


@app.get("/orders/sort")
def order_sort(order: str = "asc"):
    reverse = True if order == "desc" else False
    return sorted(orders, key=lambda x: x["total_price"], reverse=reverse)


# CART WORKFLOW

@app.post("/cart/add")
def add_to_cart(item_id: int, quantity: int = 1):

    item = find_menu_item(item_id)

    if not item or not item["is_available"]:
        raise HTTPException(400, "Invalid item")

    for c in cart:
        if c["item_id"] == item_id:
            c["quantity"] += quantity
            return {"message": "Updated quantity"}

    cart.append({"item_id": item_id, "quantity": quantity})
    return {"message": "Added to cart"}


@app.get("/cart")
def view_cart():
    total = 0
    items = []

    for c in cart:
        item = find_menu_item(c["item_id"])
        price = item["price"] * c["quantity"]
        total += price
        items.append({"name": item["name"], "quantity": c["quantity"]})

    return {"items": items, "total": total}


@app.post("/cart/checkout")
def checkout(data: CheckoutRequest):

    if not cart:
        raise HTTPException(400, "Cart is empty")

    result = []
    total = 0

    for c in cart:
        item = find_menu_item(c["item_id"])
        price = item["price"] * c["quantity"]
        total += price

        result.append({
            "item": item["name"],
            "quantity": c["quantity"]
        })

    cart.clear()

    return {"orders": result, "grand_total": total}