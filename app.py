import json
import requests
import datetime
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for, session, logging
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
from sqlalchemy import and_
from sqlalchemy import func
from flask_marshmallow import Marshmallow
from geopy import distance
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps
from camelcase import CamelCase

# init flask
app = Flask(__name__)

app.config['SECRET_KEY'] = 'kitthecat7'

# env mode
ENV = "prod"

if ENV == "dev":
    app.debug = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:web989@localhost/restos'
else:
    app.debug = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://gdxsgvgdiwtgdi:f84939786f5c07e4c141db3bf1b0433577d6919ae252daefd56600fe782c5576@ec2-54-235-108-217.compute-1.amazonaws.com:5432/d5vbh504du1mi6'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# init db
db = SQLAlchemy(app)
ma = Marshmallow(app)

c = CamelCase()

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


# model/db - login table
class Login(db.Model):
    __tablename__ = 'login'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    username = db.Column(db.String(30))
    email = db.Column(db.String(100))
    password = db.Column(db.String(100))
    register_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def __init__(self, name, username, email, password):
        self.name = name
        self.username = username
        self.email = email
        self.password = password


# model/db - for register form with validators
class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min=1, max=50)])
    username = StringField('Username', [validators.Length(min=4, max=25)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Password do not match')
    ])
    confirm = PasswordField('Confirm Password')


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)

    if request.method == 'POST' and form.validate():
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(str(form.password.data))

        data = Login(name, username, email, password)
        db.session.add(data)
        db.session.commit()

        flash('You are now registered and can log in', 'success')

        return redirect(url_for('login'))

    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password_candidate = request.form['password']

        results = Login.query.filter_by(username=username).first()

        if results is not None and sha256_crypt.verify(password_candidate, results.password):
            # set the sessions
            session['logged_in'] = True
            session['username'] = username

            flash('You are now logged in.', 'success')

            return redirect(url_for('dashboard'))
        else:
            error = "User not found! Please register."
            return render_template('login.html', error=error)

    return render_template('login.html')


def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, please login', 'danger')
            return redirect(url_for('login'))
    return wrap


@app.route('/logout')
def logout():
    session.clear()
    flash('You are now logged out.', 'success')
    return redirect(url_for('login'))


class RestaurantSchema(ma.Schema):
    class Meta:
        fields = ('name', 'location', 'balance', 'hours')


class MenuSchema(ma.Schema):
    class Meta:
        fields = ('name', 'price')


class UserSchema(ma.Schema):
    class Meta:
        fields = ('name', 'location', 'balance')


class PurchaseSchema(ma.Schema):
    class Meta:
        fields = ('dish', 'restaurant_name', 'amount', 'date')


# Init schema
restaurant_schema = RestaurantSchema()
restaurant_schema = RestaurantSchema(many=True)
menu_schema = MenuSchema()
menu_schema = MenuSchema(many=True)

user_schema = UserSchema()
user_schema = UserSchema(many=True)
purchase_schema = PurchaseSchema()
purchase_schema = PurchaseSchema(many=True)


@app.route('/')
def home():
    restaurants = Restaurant.query.filter(
        Restaurant.hours.contains('Sun')).all()

    return render_template('home.html', restaurants=restaurants)


@app.route('/dashboard')
@is_logged_in
def dashboard():
    return render_template('dashboard.html')


@app.route('/restaurants', methods=['GET', 'POST'])
def restaurants():
    if request.method == 'POST':
        day = request.form['day']
        hour = request.form['hour']

        long_day = ""
        if day == 'Mon':
            long_day = 'Monday'
        if day == 'Tue':
            long_day = 'Tuesday'
        if day == 'Wed':
            long_day = 'Wednesday'
        if day == 'Thu':
            long_day = 'Thursday'
        if day == 'Fri':
            long_day = 'Friday'
        if day == 'Sat':
            long_day = 'Saturday'
        if day == 'Sun':
            long_day = 'Sunday'

        app.logger.info(long_day)

        results = Restaurant.query.filter(
            or_(Restaurant.hours.contains(long_day + ": " + hour + ":"),
                Restaurant.hours.contains(day + ": " + hour + ":"))
        ).all()

        props = {
            "message": "Filter: restos open on " + long_day + ", at " + hour,
            "usage": "/firstjson/<day>/<hour>",
            'day': day,
            'hour': hour,
            'long_day': long_day
        }

        return render_template('restaurant_result.html', results=results, props=props)

    return render_template('restaurants.html')


@app.route('/menus/<int:id>')
def menus(id):
    results = Menu.query.filter_by(restaurant_id=id).all()
    resto = Restaurant.query.filter_by(id=id).first_or_404()

    props = {
        "usage": "/menusjson/",
    }

    return render_template('menus.html', results=results, props=props, resto=resto)


@app.route('/menusjson/<int:id>')
def menusjson(id):
    results = Menu.query.filter_by(restaurant_id=id).all()
    result = menu_schema.dump(results)

    return jsonify(result)


@app.route('/firstjson/<string:day>/<string:hour>')
def firstjson(day, hour):

    long_day = ""
    if day == 'Mon':
        long_day = 'Monday'
    if day == 'Tue':
        long_day = 'Tuesday'
    if day == 'Wed':
        long_day = 'Wednesday'
    if day == 'Thu':
        long_day = 'Thursday'
    if day == 'Fri':
        long_day = 'Friday'
    if day == 'Sat':
        long_day = 'Saturday'
    if day == 'Sun':
        long_day = 'Sunday'

    results = Restaurant.query.filter(
        or_(Restaurant.hours.contains(long_day + ": " + hour + ":"),
            Restaurant.hours.contains(day + ": " + hour + ":"))
    ).all()

    result = restaurant_schema.dump(results)

    return jsonify(result)


# @app.route('/secondjson')
# def secondjson():
#     res = requests.get('https://ipinfo.io')
#     result = res.json()

#     results = Restaurant.query.limit(1).all()
#     loc_arr = results[0].location.split(',')
#     lat = loc_arr[0]
#     lon = loc_arr[1]

#     from_db = (lat + ',' + lon)
#     curr_loc = (-8.679412, 115.136036)
#     tangguwisia = (-8.19292791439023, 114.95068201613135)
#     measure_disc = distance.distance(curr_loc, from_db).km

#     msg = "NO"
#     if measure_disc <= 5:
#         msg = "OK"

#     app.logger.info(f'>>>>> {measure_disc} >>>>> {from_db}')

#     return jsonify(result)


def check_resto_hours(props_results, day_name, open_daily):
    list_days = []  # 0-1
    list_day = []  # 0-3
    list_hours = []

    for result in props_results:

        # if hours not none
        if result.hours:
            # split the | and put it into list
            split_lines = result.hours.split(' | ')

            # loop it agian
            for line in split_lines:

                list_days.append((line))

    total_jam_mon = 0
    total_menit_mon = 0
    total_jam_menit_mon = ''
    list_jam_mon = []
    list_menit_mon = []
    list_am_pm = []

    list_hour_am_pm = []

    for line in list_days:  # line: Monday, Friday: 2:30 PM - 8 PM

        if day_name in line:

            get_list_hours_day = line.split(': ')
            # ['Monday, Friday', '2:30 PM - 8 PM']

            get_list_hours_only = get_list_hours_day[1].split(' - ')
            # ['2:30 PM', '8 PM']

            for hours in get_list_hours_only:

                hour_minute, am_pm = hours.split(' ')
                list_am_pm.append(am_pm)

                if 'PM' in am_pm:
                    if ':' in hour_minute:
                        hour, minute = hour_minute.split(':')
                        hour = int(hour) + 12

                        list_jam_mon.append(hour)
                        list_menit_mon.append(int(minute))
                    else:
                        hour_minute = int(hour_minute) + 12

                        list_jam_mon.append(hour_minute)
                else:
                    if ':' in hour_minute:
                        hour, minute = hour_minute.split(':')
                        list_hour_am_pm.append(hour)

                        if len(list_am_pm) == 2:
                            if 'AM' in list_am_pm[1]:
                                if 'PM' in list_am_pm[0]:
                                    hour = int(hour) + 24
                                elif 'AM' in list_am_pm[0]:
                                    if ((len(list_hour_am_pm) == 2) and (list_hour_am_pm[0] > list_hour_am_pm[1])) or ((list_am_pm[0] == 'AM') and (list_am_pm[1] == 'AM')):
                                        hour = int(hour) + 24
                                    else:
                                        hour = int(hour)
                                        # app.logger.info(
                                        #     f'>>>> Second: {hour} <<<')
                                else:
                                    hour = int(hour) + 12
                        else:

                            if len(list_hour_am_pm) == 2:
                                if list_hour_am_pm[0] > list_hour_am_pm[1]:
                                    hour = int(hour) + 24
                                else:
                                    hour = int(hour)
                            else:
                                hour = int(hour)

                        list_jam_mon.append(int(hour))
                        list_menit_mon.append(int(minute))
                    else:
                        if len(list_am_pm) == 2:
                            if 'AM' in list_am_pm[1]:
                                if 'PM' in list_am_pm[0]:
                                    hour_minute = int(hour_minute) + 24

                                elif 'AM' in list_am_pm[0]:
                                    if ((len(list_hour_am_pm) == 2) and (list_hour_am_pm[0] > list_hour_am_pm[1])) or ((list_am_pm[0] == 'AM') and (list_am_pm[1] == 'AM')):
                                        hour_minute = int(hour_minute) + 24
                                    else:
                                        hour_minute = int(hour_minute)
                                else:
                                    hour_minute = int(hour_minute) + 12
                        else:
                            hour_minute = int(hour_minute)
                            # app.logger.info(f'>>>> first: {hour_minute} <<<')

                        list_jam_mon.append(int(hour_minute))

    total_jam_mon = list_jam_mon[1] - list_jam_mon[0]

    if total_jam_mon < 0:
        total_jam_mon = abs(total_jam_mon)

    if not list_menit_mon:
        total_menit_mon = 0
    else:
        if len(list_menit_mon) == 2:
            total_menit_mon = list_menit_mon[1] + list_menit_mon[0]
            if total_menit_mon == 60:
                total_menit_mon = 0
                total_jam_mon = total_jam_mon + 1
        else:
            total_menit_mon = list_menit_mon[0]

    if not list_menit_mon:
        total_jam_menit_mon = str(total_jam_mon)
    else:
        total_jam_menit_mon = str(total_jam_mon) + ':' + str(total_menit_mon)

    # app.logger.info(f' >>> { total_jam_menit_mon } <<< ')

    if total_jam_mon == open_daily:
        return True
    else:
        return False


@app.route('/thirdjson')
def thirdjson():
    open_daily = 3
    day_name = 'Mon'
    results = Restaurant.query.filter_by(id=5).all()
    # results = Restaurant.query.all()

    # app.logger.info(f' >>> {check_resto_hours(results, day_name, open_daily)}')

    # class_list = []
    counter = 0
    for result in results:
        # class_list.append(result)
        if check_resto_hours(results, day_name, open_daily) is True:
            counter += 1

    app.logger.info(f' >>> function: {counter}')

    result = restaurant_schema.dump(results)

    return jsonify(result)


@app.route('/price_range_menu', methods=['GET', 'POST'])
def price_range_menu():
    if request.method == 'POST':
        min_price = request.form['minprice']
        max_price = request.form['maxprice']

        results = db.session.query(Restaurant).join(Menu).filter(
            and_(Menu.price >= min_price, Menu.price <= max_price)
        ).all()

        props = {
            "message": "Filter: restos with price menus from $" + str(min_price) + " to $" + str(max_price),
            "usage": "/fourthjson/<min_price>/<max_price>",
            "min_price": min_price,
            "max_price": max_price
        }

        return render_template('price_range_menu_result.html', results=results, props=props)

    return render_template('price_range_menu.html')


@app.route('/fourthjson/<int:min_price>/<int:max_price>')
def fourthjson(min_price, max_price):
    min_price = min_price
    max_price = max_price

    menu_list = db.session.query(Restaurant).join(Menu).filter(
        and_(Menu.price >= min_price, Menu.price <= max_price)
    ).all()

    results = restaurant_schema.dump(menu_list)

    return jsonify(results)


@app.route('/resto_dish', methods=['GET', 'POST'])
def resto_dish():
    if request.method == 'POST':
        resto_name = request.form["resto_name"]
        dish_name = request.form["dish_name"]

        resto_name_cap = resto_name.capitalize()
        dish_name_cap = dish_name.capitalize()

        results = db.session.query(Restaurant).join(Menu).filter(and_(Restaurant.name.like(
            f'%{resto_name_cap}%'), Menu.name.like(f'%{dish_name_cap}%')
        )).all()

        props = {
            "message": "Filter: resto name/dish name: " + resto_name + "/" + dish_name,
            "usage": "/sixthjson/<resto_name>/<dish_name>",
            "dish_name": dish_name,
            "resto_name": resto_name
        }

        return render_template('resto_dish_result.html', results=results, props=props)

    return render_template('resto_dish.html')


@app.route('/fifthjson/<string:resto_name>/<string:dish_name>')
def fifthjson(resto_name, dish_name):
    resto_name_cap = resto_name.capitalize()
    dish_name_cap = dish_name.capitalize()

    results = db.session.query(Restaurant).join(Menu).filter(and_(Restaurant.name.like(
        f'%{resto_name_cap}%'), Menu.name.like(f'%{dish_name_cap}%')
    )).all()

    result = restaurant_schema.dump(results)

    return jsonify(result)


@app.route('/search_dish', methods=['GET', 'POST'])
def search_dish():
    if request.method == 'POST':
        dish_name = request.form["dish_name"]

        dish_name_cap = dish_name.capitalize()
        results = db.session.query(Restaurant).join(Menu).filter(
            or_(Menu.name.like(f'%{dish_name}%'),
                Menu.name.like(f'%{dish_name_cap}%'))
        ).all()

        result = restaurant_schema.dump(results)

        props = {
            "message": "Filter: restos that have: " + dish_name,
            "usage": "/sixthjson/<dish_name>",
            "dish_name": dish_name
        }

        return render_template('search_dish_result.html', results=results, props=props)

    return render_template('search_dish.html')


@app.route('/sixthjson/<string:dish_name>')
def sixthjson(dish_name):
    dish_name_cap = dish_name.capitalize()
    results = db.session.query(Restaurant).join(Menu).filter(
        or_(Menu.name.like(f'%{dish_name}%'),
            Menu.name.like(f'%{dish_name_cap}%'))
    ).all()

    result = restaurant_schema.dump(results)

    return jsonify(result)


@app.route('/purchases/<int:id>')
def purchase(id):
    results = Purchase.query.filter_by(user_id=id).all()
    users = User.query.filter_by(id=id).first_or_404()

    props = {
        "usage": "/purchasesjson"
    }

    return render_template('purchases.html', results=results, users=users, props=props)


@app.route('/purchasesjson/<int:id>')
def purchasesjson(id):
    results = Purchase.query.filter_by(user_id=id).all()
    result = purchase_schema.dump(results)

    return jsonify(result)


@app.route('/top_x_users', methods=['GET', 'POST'])
def top_x_users():
    if request.method == 'POST':
        start_date = request.form["start_date"]
        end_date = request.form["end_date"]

        results = db.session.query(User).join(Purchase).filter(
            Purchase.date.between(start_date, end_date)).order_by(Purchase.amount.desc()).all()

        props = {
            "message": "Filter: top top x users by total transaction amount within a date range",
            "usage": "/seventhjson/<start_date>/<end_date>",
            "start_date": start_date,
            "end_date": end_date
        }

        return render_template('top_x_users_result.html', results=results, props=props)

    return render_template('top_x_users.html')


@app.route('/seventhjson/<string:start_date>/<string:end_date>')
def seventhjson(start_date, end_date):
    results = db.session.query(User).join(Purchase).filter(
        Purchase.date.between(start_date, end_date)).order_by(Purchase.amount.desc()).all()

    result = user_schema.dump(results)

    return jsonify(result)


@app.route('/eightjson')
def eightjson():
    results = db.session.query(Purchase.restaurant_name, Purchase.amount).distinct().order_by(
        Purchase.amount.desc()).all()

    result = purchase_schema.dump(results)

    return jsonify(result)


@app.route('/trx_to_resto', methods=['GET', 'POST'])
def trx_to_resto():
    if request.method == 'POST':
        resto_name = request.form['resto_name']
        resto_name_cap = c.hump(resto_name)
        results = Restaurant.query.filter(Restaurant.name.like(
            f'%{resto_name_cap}%')).order_by(Restaurant.name.desc()).all()

        props = {
            "message": "Filter: restos name like: " + resto_name_cap,
            "usage": "/tenthjson/<resto_name>",
            "resto_name": resto_name
        }

        return render_template('trx_to_resto_result.html', results=results, props=props)

    return render_template('trx_to_resto.html')


@app.route('/tenthjson/<string:resto_name>')
def tenthjson(resto_name):
    resto_name_cap = c.hump(resto_name)

    results = Restaurant.query.filter(Restaurant.name.like(
        f'%{resto_name_cap}%')).order_by(Restaurant.name.desc()).all()

    result = restaurant_schema.dump(results)

    return jsonify(result)


@app.route('/purchases2/<string:resto_name>')
def purchase2(resto_name):
    resto_name_cap = c.hump(resto_name)
    results = Purchase.query.filter(
        Purchase.restaurant_name == resto_name_cap).all()

    props = {
        "usage": "/tenthjson2",
        "resto_name": resto_name
    }

    return render_template('purchases2.html', results=results, props=props)


@app.route('/tenthjson2/<string:resto_name>')
def tenthjson2(resto_name):
    resto_name_cap = c.hump(resto_name)

    resto_name_cap = c.hump(resto_name)
    results = Purchase.query.filter(
        Purchase.restaurant_name == resto_name_cap).all()

    result = purchase_schema.dump(results)

    return jsonify(result)


# run server
if __name__ == '__main__':
    # app.secret_key = 'kitthecat7'

    app.run()
