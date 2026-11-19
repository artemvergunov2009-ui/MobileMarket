import uuid 
import uvicorn
from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from Database import Session, Category, Product, CartItem, User, Order, OrderItem, create_tables, add_data

app = FastAPI()
templates = Jinja2Templates(directory=".")

create_tables()
add_data()


def get_session_id(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id:
        session_id = str(uuid.uuid4())
    return session_id


def show(request: Request, db, page: str, **data):
    session_id = get_session_id(request)
    cart_items = db.query(CartItem).filter(CartItem.session_id == session_id).all()

    data["user"] = request.cookies.get("user")
    data["cart_count"] = sum(item.quantity for item in cart_items)

    response = templates.TemplateResponse(request, page, data)
    response.set_cookie(key="session_id", value=session_id)
    return response


@app.get("/")
def index(request: Request, category: int = None, q: str = None):
    db = Session()

    query = db.query(Product)
    if category:
        query = query.filter(Product.category_id == category)
    if q:
        query = query.filter(Product.name.ilike(f"%{q}%"))

    products = query.order_by(Product.id).all()
    categories = db.query(Category).all()

    response = show(request, db, "index.html", products=products, categories=categories, q=q)
    db.close()
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
        db.add(CartItem(session_id=session_id, product_id=product_id, quantity=1))

    db.commit()
    db.close()

    referer = request.headers.get("referer", "/").split("#")[0]
    response = RedirectResponse(url=f"{referer}#product-{product_id}", status_code=303)
    response.set_cookie(key="session_id", value=session_id)
    return response


@app.get("/cart")
def cart_page(request: Request):
    db = Session()
    session_id = get_session_id(request)

    cart_items = db.query(CartItem).filter(CartItem.session_id == session_id).all()
    items = [item for item in cart_items if item.product]
    total = sum(item.product.price * item.quantity for item in items)

    response = show(request, db, "cart.html", items=items, total=total)
    db.close()
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


@app.get("/order")
def order_page(request: Request):
    db = Session()
    session_id = get_session_id(request)

    items = []
    total = 0
    if request.cookies.get("user"):
        cart_items = db.query(CartItem).filter(CartItem.session_id == session_id).all()
        items = [item for item in cart_items if item.product]
        if not items:
            db.close()
            return RedirectResponse(url="/cart", status_code=303)
        total = sum(item.product.price * item.quantity for item in items)

    response = show(request, db, "order.html", items=items, total=total)
    db.close()
    return response


@app.post("/order")
def create_order(request: Request,
                 customer_name: str = Form(...),
                 phone: str = Form(...),
                 address: str = Form(...)):
    db = Session()
    session_id = get_session_id(request)

    if not request.cookies.get("user"):
        db.close()
        return RedirectResponse(url="/login", status_code=303)

    cart_items = db.query(CartItem).filter(CartItem.session_id == session_id).all()
    if not cart_items:
        db.close()
        return RedirectResponse(url="/cart", status_code=303)

    new_order = Order(customer_name=customer_name, phone=phone, address=address)
    db.add(new_order)
    db.flush()

    for item in cart_items:
        if item.product:
            db.add(OrderItem(
                order_id=new_order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                price=item.product.price
            ))
        db.delete(item)

    order_id = new_order.id
    db.commit()

    response = show(request, db, "order_success.html",
                    order_id=order_id, customer_name=customer_name, phone=phone)
    db.close()
    return response


@app.get("/login")
def login_page(request: Request):
    db = Session()
    response = show(request, db, "login.html", error="")
    db.close()
    return response


@app.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    db = Session()
    user = db.query(User).filter(User.username == username, User.password == password).first()

    if not user:
        response = show(request, db, "login.html", error="Неверный логин или пароль")
        db.close()
        return response

    db.close()
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(key="user", value=user.username)
    return response


@app.get("/register")
def register_page(request: Request):
    db = Session()
    response = show(request, db, "register.html", error="")
    db.close()
    return response


@app.post("/register")
def register(request: Request, username: str = Form(...), password: str = Form(...)):
    db = Session()
    existing = db.query(User).filter(User.username == username).first()

    if existing:
        response = show(request, db, "register.html", error="Такой логин уже занят")
        db.close()
        return response

    db.add(User(username=username, password=password))
    db.commit()
    db.close()

    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(key="user", value=username)
    return response


@app.get("/logout")
def logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("user")
    return response


@app.get("/about")
def about_page(request: Request):
    db = Session()
    response = show(request, db, "about.html")
    db.close()
    return response



if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
