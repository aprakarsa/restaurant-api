import json
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy


# init flask
app = Flask(__name__)


# env mode
ENV = "prod"

if ENV == "dev":
    app.debug = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:web989@localhost/restos'
else:
    app.debug = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://tbapjrqighdksb:b0f03e16699ed53d89251d813f00dd2fc9b2dc6caf27d877ccd604a642a3b0b7@ec2-54-235-108-217.compute-1.amazonaws.com:5432/d59rr8du1s2jve'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# init db
db = SQLAlchemy(app)


# model/db - restaurant table
class Restaurant(db.Model):
    __tablename__ = 'restaurant'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    location = db.Column(db.String(200))
    balance = db.Column(db.Float)
    hours = db.Column(db.Text)

    def __init__(self, name, location, balance, hours):
        self.name = name
        self.location = location
        self.balance = balance
        self.hours = hours


# model/db - menu table
class Menu(db.Model):
    __tablename__ = 'menu'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(300))
    price = db.Column(db.Float)
    restaurant_id = db.Column(db.Integer, db.ForeignKey(
        'restaurant.id'), nullable=False)

    def __init__(self, name, price, restaurant_id):
        self.name = name
        self.price = price
        self.restaurant_id = restaurant_id


# model/db - user table
class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    location = db.Column(db.String(200))
    balance = db.Column(db.Float)

    def __init__(self, name, location, balance):
        self.name = name
        self.location = location
        self.balance = balance


# model/db - purchase table
class Purchase(db.Model):
    __tablename__ = 'purchase'
    id = db.Column(db.Integer, primary_key=True)
    dish = db.Column(db.String(300))
    restaurant_name = db.Column(db.String(200))
    amount = db.Column(db.Float)
    date = db.Column(db.DateTime)
    user_id = db.Column(db.Integer, db.ForeignKey(
        'user.id'), nullable=False)

    def __init__(self, dish, restaurant_name, amount, date, user_id):
        self.dish = dish
        self.restaurant_name = restaurant_name
        self.amount = amount
        self.date = date
        self.user_id = user_id


# convert json file into sql
with open("./json/restaurants.json") as f:
    data = json.load(f)

# print(f'>>> Total of {len(data)} records <<<')
counter = 0
menu_counter = 0
for resto in data:
    counter += 1
    # print(f'id: {counter}')
    # print(f'name: {resto["name"]}')
    # print(f'location: {resto["location"]}')
    # print(f'business_hours: {resto["business_hours"]}')
    # print(f'balance: ${resto["balance"]}')

    name = resto["name"]
    location = resto["location"]
    balance = resto["balance"]
    business_hours = resto["business_hours"]

    data = Restaurant(name, location, balance, business_hours)
    db.session.add(data)
    db.session.commit()

    # print("menus:")
    for menu in resto['menu']:
        # print(f'  >> {menu["name"]} (${menu["price"]})')
        menu_counter += 1
        name = menu["name"]
        price = menu["price"]
        restaurant_id = counter

        data2 = Menu(name, price, restaurant_id)
        db.session.add(data2)
        db.session.commit()


# print(menu_counter)


# convert json file into sql
with open("./json/users.json") as f:
    users = json.load(f)

user_count = 0
dish_count = 0

# print(f'Total users: {len(users)}')

for user in users:
    user_count += 1

    # print(f'No: {user_count}')
    # print(f'Name: {user["name"]}')
    # print(f'Location: {user["location"]}')
    # print(f'Balance: {user["balance"]}')

    name = user["name"]
    location = user["location"]
    balance = user["balance"]

    data = User(name, location, balance)
    db.session.add(data)
    db.session.commit()

    # print(f'Total dishes: {len(user["purchases"])}')

    for purchase in user["purchases"]:
        dish_count += 1

        # print(f' > No: {dish_count}')
        # print(f'  >> dish: {purchase["dish"]}')
        # print(f'  >> resto name: {purchase["restaurant_name"]}')
        # print(f'  >> amount: {purchase["amount"]}')
        # print(f'  >> date: {purchase["date"]}')

        dish = purchase["dish"]
        restaurant_name = purchase["restaurant_name"]
        amount = purchase["amount"]
        date = purchase["date"]
        user_id = user_count

        data2 = Purchase(dish, restaurant_name, amount, date, user_id)
        db.session.add(data2)
        db.session.commit()

# print(f'Total users: {user_count}')
# print(f'Total dishes: {dish_count}')


@app.route('/')
def home():
    return render_template('home.html')


# run server
if __name__ == '__main__':
    app.secret_key = 'cat12345'
    app.run()
