import os
from flask import Flask, render_template, redirect, request, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, current_user, logout_user, login_required
from flask_migrate import Migrate
from datetime import datetime
from pytz import timezone

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root@localhost/bazadan'
app.config['UPLOAD_FOLDER'] = 'static/photos'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


# Модель пользователя
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    registration_time = db.Column(db.DateTime, default=datetime.utcnow)
    photo = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}', '{self.registration_time}')"

    def is_active(self):
        return True

    def get_id(self):
        return str(self.id)

    def is_authenticated(self):
        return True




@app.route("/user-list")
@login_required
def user_list():
    users = User.query.all()
    return render_template("user_list.html", users=users)



@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect('/')

    if request.method == 'POST':
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']

        # Проверка наличия пользователя с таким же email или логином
        user_email = User.query.filter_by(email=email).first()
        user_username = User.query.filter_by(username=username).first()
        if user_email:
            flash('Пользователь с таким email уже зарегистрирован', 'danger')
            return redirect('/register')
        elif user_username:
            flash('Пользователь с таким логином уже существует', 'danger')
            return redirect('/register')

        # Хеширование пароля
        password_hash = generate_password_hash(password)

        # Создание нового пользователя
        moscow_tz = timezone('Europe/Moscow')
        registration_time = datetime.now(moscow_tz)

        new_user = User(email=email, username=username, password_hash=password_hash, registration_time=registration_time)
        db.session.add(new_user)
        db.session.commit()

        flash('Вы успешно зарегистрировались', 'success')
        return redirect('/login')

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect('/')

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Поиск пользователя по email
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            # Вход пользователя
            login_user(user)
            return redirect('/')
        else:
            flash('Неправильный email или пароль', 'danger')
            return redirect('/login')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/')


@app.route('/protected')
@login_required
def protected():
    return "Как ты сюда попал?"


@app.route('/upload_photo', methods=['POST'])
@login_required
def upload_photo():
    if 'photo' not in request.files:
        flash('Не удалось загрузить фотографию', 'danger')
        return redirect('/')

    photo = request.files['photo']

    if photo.filename == '':
        flash('Не выбран файл', 'danger')
        return redirect('/')

    if not allowed_file(photo.filename):
        flash('Недопустимый формат файла', 'danger')
        return redirect('/')

    filename = generate_filename(photo.filename)
    photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    current_user.photo = filename
    db.session.commit()

    flash('Фотография успешно загружена', 'success')
    return redirect('/')


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def generate_filename(filename):
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_string = os.urandom(8).hex()
    _, extension = os.path.splitext(filename)
    return f'{timestamp}_{random_string}{extension}'


if __name__ == '__main__':
    app.run()