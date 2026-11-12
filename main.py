import uuid
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from Database import Session, Category, Product, CartItem, create_tables, add_data

app = FastAPI()
templates = Jinja2Templates(directory=".")

create_tables()
add_data()

def get_session_id(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id:
        session_id = str(uuid.uuid4())
    return session_id

@app.get("/", response_class=HTMLResponse)
def index(request: Request, category: int = None, q: str = None):
    db = Session()
    session_id = get_session_id(request)

    categories = db.query(Category).all()
    query = db.query(Product)

    if category:
        query = query.filter(Product.category_id == category)

    if q:
        query = query.filter(Product.name.ilike(f"%{q}%"))

    products = query.order_by(Product.id).all()
    cart_items = db.query(CartItem).filter(CartItem.session_id == session_id).all()
    cart_count = sum(item.quantity for item in cart_items)
    db.close()

    response = templates.TemplateResponse(request, "index.html", {
        "categories": categories,
        "products": products,
        "selected_category": category,
        "search_query": q or "",
        "cart_count": cart_count
    })
    response.set_cookie(key="session_id", value=session_id)
    return response

@app.post("/cart/add/{product_id}")
def add_to_cart(request: Request, product_id: int):
    db = Session()
    session_id = get_session_id(request)

    item = db.query(CartItem).filter(
        CartItem.session_id == session_id,
        CartItem.product_id == product_id
    ).first()

    if item:
        item.quantity += 1
    else:
        new_item = CartItem(session_id=session_id, product_id=product_id, quantity=1)
        db.add(new_item)

    db.commit()
    db.close()

    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(key="session_id", value=session_id)
    return response

@app.get("/cart", response_class=HTMLResponse)
def cart_page(request: Request):
    db = Session()
    session_id = get_session_id(request)

    cart_items = db.query(CartItem).filter(CartItem.session_id == session_id).all()
    
    items = []
    total_price = 0
    cart_count = 0

    for item in cart_items:
        if item.product:
            subtotal = item.product.price * item.quantity
            total_price += subtotal
            cart_count += item.quantity
            items.append({
                "id": item.id,
                "name": item.product.name,
                "price": item.product.price,
                "quantity": item.quantity,
                "subtotal": subtotal
            })

    db.close()

    response = templates.TemplateResponse(request, "cart.html", {
        "items": items,
        "total_price": total_price,
        "cart_count": cart_count
    })
    response.set_cookie(key="session_id", value=session_id)
    return response

@app.post("/cart/delete/{item_id}")
def delete_from_cart(request: Request, item_id: int):
    db = Session()
    session_id = get_session_id(request)

    item = db.query(CartItem).filter(
        CartItem.id == item_id,
        CartItem.session_id == session_id
    ).first()

    if item:
        db.delete(item)
        db.commit()

    db.close()
    return RedirectResponse(url="/cart", status_code=303)

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
