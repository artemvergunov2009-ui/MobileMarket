from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

engine = create_engine("postgresql+psycopg2://postgres:330017@localhost:5432/MobileMarket")
Session = sessionmaker(bind=engine)
Base = declarative_base()

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey("categories.id"))
    name = Column(String(200), nullable=False)
    description = Column(Text)
    price = Column(Integer, nullable=False)
    stock = Column(Integer, default=0)


class CartItem(Base):
    __tablename__ = "cart"
    id = Column(Integer, primary_key=True)
    session_id = Column(String(100), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer, default=1)
    product = relationship("Product")


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    customer_name = Column(String(100), nullable=False)
    phone = Column(String(30), nullable=False)
    address = Column(String(200), nullable=False)
    created_at = Column(DateTime, default=datetime.now)


class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer, nullable=False)
    price = Column(Integer, nullable=False)


def create_tables():
    Base.metadata.create_all(engine)


def add_data():
    db = Session()

    
    if db.query(Category).count() > 0:
        db.close()
        return

    names = ["Процессоры", "Видеокарты", "Материнские платы", "Оперативная память", "Накопители", "Блоки питания", "Периферия"]
    categories = [Category(name=n) for n in names]
    db.add_all(categories)
    db.flush()

    items = [
        (0, "AMD Ryzen 5 7600", "6 ядер, 12 потоков, сокет AM5.", 15990, 12),
        (0, "Intel Core i5-13400F", "10 ядер, сокет LGA1700.", 16490, 8),
        (0, "AMD Ryzen 7 7800X3D", "8 ядер с 3D V-Cache для игр.", 38990, 4),
        (1, "NVIDIA GeForce RTX 4060 8GB", "Видеокарта для игр в Full HD.", 31990, 10),
        (1, "NVIDIA GeForce RTX 4070 Super 12GB", "Мощная видеокарта для игр в 2K.", 62990, 5),
        (1, "AMD Radeon RX 7600 8GB", "Бюджетная видеокарта для Full HD.", 26990, 7),
        (2, "ASUS PRIME B650M-K", "Плата mATX, сокет AM5, DDR5.", 11990, 9),
        (2, "MSI PRO B760M-P", "Плата mATX, сокет LGA1700, DDR4.", 10490, 6),
        (3, "Kingston Fury Beast 16GB DDR5 5600", "Один модуль памяти 16 ГБ.", 4990, 20),
        (3, "Corsair Vengeance 32GB (2x16) DDR5 6000", "Комплект из двух модулей.", 9990, 11),
        (4, "Samsung 980 1TB NVMe", "Быстрый SSD M.2 на 1 ТБ.", 6990, 15),
        (4, "Kingston NV2 500GB NVMe", "Недорогой SSD M.2 на 500 ГБ.", 3290, 18),
        (4, "Seagate Barracuda 2TB", "Жёсткий диск 3.5 дюйма на 2 ТБ.", 4990, 14),
        (5, "be quiet! Pure Power 12 M 650W", "Тихий блок питания 650 Вт.", 7490, 9),
        (5, "Corsair RM750e 750W", "Модульный блок питания 750 Вт.", 11990, 6),
        (6, "Logitech G102", "Игровая проводная мышь.", 1990, 25),
        (6, "HyperX Alloy Origins", "Механическая клавиатура.", 8990, 7),
    ]
    for n, name, desc, price, stock in items:
        db.add(Product(category_id=categories[n].id, name=name,description=desc, price=price, stock=stock))

    db.commit()
    db.close()


if __name__ == "__main__":
    create_tables()
    add_data()

    db = Session()
    for p in db.query(Product).order_by(Product.id).all():
        print(p.id, p.name, p.price )
    db.close()