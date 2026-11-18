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
        return f'<span style="color: white; margin-right: 15px;">Привет, <b>{user}</b></span><a href="/logout">Выйти</a>'
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

        if p.id in [1, 2, 3]:
            buttons_html = f"""
            <div style="display: flex; gap: 8px; margin-top: auto;">
                <a href="/product/{p.id}" style="flex: 1; background: #ffedd5; color: #c2410c; text-decoration: none; padding: 10px 0; border-radius: 5px; font-weight: bold; border: 1px solid #fdba74; display: flex; align-items: center; justify-content: center;">О товаре</a>
                <form action="/cart/add/{p.id}" method="post" style="flex: 1; margin: 0;">
                    <button type="submit" style="width: 100%; height: 100%; padding: 10px 0;">В корзину</button>
                </form>
            </div>
            """
        else:
            buttons_html = f"""
            <form action="/cart/add/{p.id}" method="post" style="margin-top: auto;">
                <button type="submit" style="width: 100%; padding: 10px 0;">В корзину</button>
            </form>
            """

        cards_html += f"""
        <div class="card" id="product-{p.id}">
            <div class="photo">{img_tag}</div>
            <h3>{p.name}</h3>
            <div class="desc">{p.description}</div>
            <div class="price">{p.price} ₽</div>
            {buttons_html}
        </div>
        """

    if not cards_html:
        cards_html = "<p>Товары не найдены.</p>"

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

@app.get("/product/1", response_class=HTMLResponse)
def product_1_page(request: Request):
    db = Session()
    cart_items = db.query(CartItem).filter(CartItem.session_id == get_session_id(request)).all()
    cart_count = sum(item.quantity for item in cart_items)
    db.close()
    with open("product1.html", "r", encoding="utf-8") as f:
        html = f.read()
    return HTMLResponse(content=html.replace("{cart_count}", str(cart_count)).replace("{auth_links}", get_auth_html(request)))

@app.get("/product/2", response_class=HTMLResponse)
def product_2_page(request: Request):
    db = Session()
    cart_items = db.query(CartItem).filter(CartItem.session_id == get_session_id(request)).all()
    cart_count = sum(item.quantity for item in cart_items)
    db.close()
    with open("product2.html", "r", encoding="utf-8") as f:
        html = f.read()
    return HTMLResponse(content=html.replace("{cart_count}", str(cart_count)).replace("{auth_links}", get_auth_html(request)))

@app.get("/product/3", response_class=HTMLResponse)
def product_3_page(request: Request):
    db = Session()
    cart_items = db.query(CartItem).filter(CartItem.session_id == get_session_id(request)).all()
    cart_count = sum(item.quantity for item in cart_items)
    db.close()
    with open("product3.html", "r", encoding="utf-8") as f:
        html = f.read()
    return HTMLResponse(content=html.replace("{cart_count}", str(cart_count)).replace("{auth_links}", get_auth_html(request)))

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
        cart_content = '<p>Ваша корзина пока пуста.</p><a href="/" class="btn-order">Перейти к покупкам</a>'

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
    session_id = get_session_id(request)

    with open("order.html", "r", encoding="utf-8") as f:
        html = f.read()

    cart_count = 0

    if not user:
        content = """
        <div class="warn" style="color: #dc2626; font-size: 18px; font-weight: bold; margin-bottom: 15px;">Сначала нужно зарегистрироваться или войти!</div>
        <p>Оформлять заказы могут только авторизованные пользователи.</p>
        <a href="/login" class="btn" style="display: inline-block; background: #f97316; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold; margin: 5px;">Войти</a>
        <a href="/register" class="btn" style="display: inline-block; background: #f97316; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold; margin: 5px;">Регистрация</a>
        """
    else:
        db = Session()
        cart_items = db.query(CartItem).filter(CartItem.session_id == session_id).all()
        
        if not cart_items:
            db.close()
            return RedirectResponse(url="/cart", status_code=303)

        summary_html = "<ul style='list-style: none; padding: 0; margin: 0; text-align: left;'>"
        total = 0
        for item in cart_items:
            if item.product:
                sub = item.product.price * item.quantity
                total += sub
                cart_count += item.quantity
                summary_html += f"<li style='padding: 8px 0; border-bottom: 1px solid #fed7aa;'>{item.product.name} — {item.quantity} шт. <b>({sub} ₽)</b></li>"
        
        summary_html += f"</ul><div style='text-align: right; font-size: 18px; font-weight: bold; color: #ea580c; margin-top: 15px;'>К оплате: {total} ₽</div>"
        db.close()

        content = f"""
        <h2>Оформление заказа</h2>
        
        <div style="background: #fffaf5; padding: 20px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #fed7aa;">
            <h3 style="margin-top: 0; text-align: left;">Ваш заказ:</h3>
            {summary_html}
        </div>

        <form action="/order" method="post">
            <input type="text" name="customer_name" value="{user}" placeholder="Ваше имя" required style="width: 90%; padding: 10px; margin-bottom: 12px; border: 1px solid #fdba74; border-radius: 5px;">
            <input type="text" name="phone" placeholder="Телефон" required style="width: 90%; padding: 10px; margin-bottom: 12px; border: 1px solid #fdba74; border-radius: 5px;">
            <input type="text" name="address" placeholder="Адрес доставки" required style="width: 90%; padding: 10px; margin-bottom: 12px; border: 1px solid #fdba74; border-radius: 5px;">
            <button type="submit" style="width: 95%; background: #f97316; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-weight: bold;">Подтвердить заказ</button>
        </form>
        """

    html = html.replace("{cart_count}", str(cart_count))
    html = html.replace("{auth_links}", get_auth_html(request))
    html = html.replace("{order_content}", content)
    return HTMLResponse(content=html)

@app.post("/order", response_class=HTMLResponse)
def create_order(request: Request, customer_name: str = Form(...), phone: str = Form(...), address: str = Form(...)):
    user = request.cookies.get("user")
    session_id = get_session_id(request)

    with open("order.html", "r", encoding="utf-8") as f:
        html = f.read()

    if not user:
        content = '<div style="color: #dc2626; font-size: 18px; font-weight: bold; margin-bottom: 15px;">Сначала нужно зарегистрироваться или войти!</div><a href="/login" style="display: inline-block; background: #f97316; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold;">Войти</a>'
        html = html.replace("{auth_links}", get_auth_html(request))
        html = html.replace("{order_content}", content)
        return HTMLResponse(content=html)

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
    <div style="color: #16a34a; font-size: 20px; font-weight: bold; margin-bottom: 15px;">Заказ №{order_id} успешно оформлен!</div>
    <p>Спасибо за покупку, <b>{customer_name}</b>! Мы свяжемся с вами по номеру {phone}.</p>
    <a href="/" style="display: inline-block; background: #f97316; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold; margin-top: 15px;">Вернуться в каталог</a>
    """

    html = html.replace("{auth_links}", get_auth_html(request))
    html = html.replace("{cart_count}", "0")
    html = html.replace("{order_content}", content)
    return HTMLResponse(content=html)

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
        return html.replace("{error}", '<div class="error">Такой логин уже занят</div>')

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

@app.get("/about", response_class=HTMLResponse)
def about_page(request: Request):
    db = Session()
    cart_items = db.query(CartItem).filter(CartItem.session_id == get_session_id(request)).all()
    cart_count = sum(item.quantity for item in cart_items)
    db.close()
    with open("about.html", "r", encoding="utf-8") as f:
        html = f.read()
    return HTMLResponse(content=html.replace("{cart_count}", str(cart_count)).replace("{auth_links}", get_auth_html(request)))

@app.get("/delivery", response_class=HTMLResponse)
def delivery_page(request: Request):
    db = Session()
    cart_items = db.query(CartItem).filter(CartItem.session_id == get_session_id(request)).all()
    cart_count = sum(item.quantity for item in cart_items)
    db.close()
    with open("delivery.html", "r", encoding="utf-8") as f:
        html = f.read()
    return HTMLResponse(content=html.replace("{cart_count}", str(cart_count)).replace("{auth_links}", get_auth_html(request)))

@app.get("/contacts", response_class=HTMLResponse)
def contacts_page(request: Request):
    db = Session()
    cart_items = db.query(CartItem).filter(CartItem.session_id == get_session_id(request)).all()
    cart_count = sum(item.quantity for item in cart_items)
    db.close()
    with open("contacts.html", "r", encoding="utf-8") as f:
        html = f.read()
    return HTMLResponse(content=html.replace("{cart_count}", str(cart_count)).replace("{auth_links}", get_auth_html(request)))

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
