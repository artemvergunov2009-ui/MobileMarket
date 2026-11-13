import uuid
import uvicorn
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from Database import Session, Category, Product, CartItem, User, Order, OrderItem, create_tables, add_data

app = FastAPI()

create_tables()
add_data()

def get_session_id(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id:
        session_id = str(uuid.uuid4())
    return session_id

def get_auth_html(request: Request):
    user = request.cookies.get("user")
    if user:
        return f'<span style="color: white; margin-right: 15px;">Дароу, <b>{user}</b></span><a href="/logout">Выйти</a>'
    return '<a href="/login">Войти</a><a href="/register">Регистрация</a>'

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

    cats_html = '<a href="/">Все товары</a>'
    for c in categories:
        cats_html += f'<a href="/?category={c.id}">{c.name}</a>'

    cards_html = ""
    for p in products:
        if p.image:
            img_tag = f'<img src="{p.image}" alt="{p.name}">'
        else:
            img_tag = '<span style="color: #a8a29e; font-size: 13px;">Нет фото</span>'

        cards_html += f"""
        <div class="card" id="product-{p.id}">
            <div class="photo">{img_tag}</div>
            <h3>{p.name}</h3>
            <div class="desc">{p.description}</div>
            <div class="price">{p.price} ₽</div>
            <form action="/cart/add/{p.id}" method="post">
                <button type="submit">В корзину</button>
            </form>
        </div>
        """

    if not cards_html:
        cards_html = "<p>Товары не найдены</p>"

    db.close()

    with open("index.html", "r", encoding="utf-8") as f:
        html = f.read()

    html = html.replace("{cart_count}", str(cart_count))
    html = html.replace("{auth_links}", get_auth_html(request))
    html = html.replace("{categories}", cats_html)
    html = html.replace("{products}", cards_html)

    response = HTMLResponse(content=html)
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
        db.add(CartItem(session_id=session_id, product_id=product_id, quantity=1))

    db.commit()
    db.close()

    referer = request.headers.get("referer", "/").split("#")[0]
    response = RedirectResponse(url=f"{referer}#product-{product_id}", status_code=303)
    response.set_cookie(key="session_id", value=session_id)
    return response

@app.get("/cart", response_class=HTMLResponse)
def cart_page(request: Request):
    db = Session()
    session_id = get_session_id(request)

    cart_items = db.query(CartItem).filter(CartItem.session_id == session_id).all()
    total_price = 0
    cart_count = 0
    rows_html = ""

    for item in cart_items:
        if item.product:
            subtotal = item.product.price * item.quantity
            total_price += subtotal
            cart_count += item.quantity
            rows_html += f"""
            <tr>
                <td>{item.product.name}</td>
                <td>{item.product.price} ₽</td>
                <td>{item.quantity} шт.</td>
                <td><b>{subtotal} ₽</b></td>
                <td>
                    <form action="/cart/delete/{item.id}" method="post">
                        <button type="submit" class="btn-delete">Удалить</button>
                    </form>
                </td>
            </tr>
            """

    db.close()

    if rows_html:
        cart_content = f"""
        <table>
            <tr>
                <th>Товар</th>
                <th>Цена</th>
                <th>Количество</th>
                <th>Сумма</th>
                <th>Действие</th>
            </tr>
            {rows_html}
        </table>
        <div class="total">Итого: {total_price} ₽</div>
        <a href="/order" class="btn-order">Оформить заказ</a>
        """
    else:
        cart_content = '<p>Ваша корзина пока что пустая.</p><a href="/" class="btn-order">Перейти к покупкам</a>'

    with open("cart.html", "r", encoding="utf-8") as f:
        html = f.read()

    html = html.replace("{cart_count}", str(cart_count))
    html = html.replace("{auth_links}", get_auth_html(request))
    html = html.replace("{cart_content}", cart_content)

    response = HTMLResponse(content=html)
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

@app.get("/order", response_class=HTMLResponse)
def order_page(request: Request):
    user = request.cookies.get("user")

    with open("order.html", "r", encoding="utf-8") as f:
        html = f.read()

    if not user:
        content = """
        <div class="warn">Сначала нужно зарегаться или войти!</div>
        <p>Оформлять заказы могут только авторизованные пользователи</p>
        <a href="/login" class="btn">Войти</a>
        <a href="/register" class="btn">Регистрация</a>
        """
    else:
        content = f"""
        <h2>Оформление заказа</h2>
        <form action="/order" method="post">
            <input type="text" name="customer_name" value="{user}" placeholder="Ваше имя" required>
            <input type="text" name="phone" placeholder="Телефон" required>
            <input type="text" name="address" placeholder="Адрес доставки     Пример: г.Никитинск, ул.Самборская, дом В(8)" required>
            <button type="submit">Подтвердить заказ</button>
        </form>
        """

    html = html.replace("{auth_links}", get_auth_html(request))
    html = html.replace("{order_content}", content)
    return html

@app.post("/order", response_class=HTMLResponse)
def create_order(request: Request, customer_name: str = Form(...), phone: str = Form(...), address: str = Form(...)):
    user = request.cookies.get("user")
    session_id = get_session_id(request)

    with open("order.html", "r", encoding="utf-8") as f:
        html = f.read()

    if not user:
        content = '<div class="warn">Сначала нужно зарегаться или войти!</div><a href="/login" class="btn">Войти</a>'
        html = html.replace("{auth_links}", get_auth_html(request))
        html = html.replace("{order_content}", content)
        return html

    db = Session()
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
    db.close()

    content = f"""
    <div class="success">Заказ №{order_id} успешно оформлен!</div>
    <p>Спасибо за покупку, <b>{customer_name}</b>! Мы свяжемся с вами по номеру {phone}.</p>
    <a href="/" class="btn">Вернуться в магазин</a>
    """

    html = html.replace("{auth_links}", get_auth_html(request))
    html = html.replace("{order_content}", content)
    return html

@app.get("/login", response_class=HTMLResponse)
def login_page():
    with open("login.html", "r", encoding="utf-8") as f:
        html = f.read()
    return html.replace("{error}", "")

@app.post("/login", response_class=HTMLResponse)
def login(username: str = Form(...), password: str = Form(...)):
    db = Session()
    user = db.query(User).filter(User.username == username, User.password == password).first()
    db.close()

    if not user:
        with open("login.html", "r", encoding="utf-8") as f:
            html = f.read()
        return html.replace("{error}", '<div class="error">Неверный логин или пароль</div>')

    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(key="user", value=user.username)
    return response

@app.get("/register", response_class=HTMLResponse)
def register_page():
    with open("register.html", "r", encoding="utf-8") as f:
        html = f.read()
    return html.replace("{error}", "")

@app.post("/register", response_class=HTMLResponse)
def register(username: str = Form(...), password: str = Form(...)):
    db = Session()
    existing = db.query(User).filter(User.username == username).first()

    if existing:
        db.close()
        with open("register.html", "r", encoding="utf-8") as f:
            html = f.read()
        return html.replace("{error}", '<div class="error">Такой логин уже того... занят</div>')

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

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
