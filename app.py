import os
from flask import Flask, render_template, request, redirect, url_for
from flask_dance.contrib.github import make_github_blueprint, github
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from datetime import datetime
from flask_login import UserMixin, login_user, logout_user, current_user, LoginManager, login_required
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin, SQLAlchemyStorage
from flask_dance.consumer import oauth_authorized
from sqlalchemy.orm.exc import NoResultFound


os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
blueprint = make_github_blueprint(
     client_id = os.environ.get("CLIENT_ID"),
     client_secret = os.environ.get("CLIENT_SECRET")
)
app.register_blueprint(blueprint, url_prefix="/login")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
db = SQLAlchemy(app)
login_manager = LoginManager(app)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    email = db.Column(db.String(200), unique=True)
    tasks = db.relationship('Todo', backref='author', lazy=True)

    def __repr__(self):
        return f"User('{self.username}','{self.email}')"


class OAuth(OAuthConsumerMixin, db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey(User.id))
    user = db.relationship(User)


class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.DateTime, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id))

    def __repr__(self):
        return '<Task %r>' % self.id


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

blueprint.storage = SQLAlchemyStorage(OAuth, db.session, user=current_user, user_required=False)


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        task_content = request.form['content']
        new_task = Todo(content=task_content, author=current_user)
        try:
            db.session.add(new_task)
            db.session.commit()
            return redirect('/')
        except:
            return 'There was an error'
    else:
        page = request.args.get('page', 1, type=int)
        tasks = Todo.query.order_by(Todo.date_created.desc()).paginate(page=page, per_page=5)
        return render_template('index.html', tasks=tasks)


@app.route('/login', methods=['POST'])
def login():
    if not github.authorized:
        return redirect(url_for("github.login"))
    return redirect(url_for('/'))


@oauth_authorized.connect_via(blueprint)
def logged_in(blueprint, token):
    account_info = blueprint.session.get("/user")
    if account_info.ok:
        account_info_json = account_info.json()
        username = account_info_json["login"]
        query = User.query.filter_by(username=username)

        try:
            user = query.one()
        except NoResultFound:
            user = User()
            user.username = account_info_json['login']
            db.session.add(user)
            db.session.commit()

        login_user(user)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/')


@app.route('/delete/<int:id>')
def delete(id):
    task_to_delete = Todo.query.get_or_404(id)
    try:
        db.session.delete(task_to_delete)
        db.session.commit()
        return redirect('/')
    except:
        return 'There was an error'


@app.route('/update/<int:id>', methods=['GET', 'POST'])
def update(id):
    task = Todo.query.get_or_404(id)
    if request.method == 'POST':
        task.content = request.form['content']
        try:
            db.session.commit()
            return redirect('/')
        except:
            return 'There was an error'
    else:
        return render_template('update.html', task=task)


@app.route('/due/<int:id>', methods=['GET', 'POST'])
def set_due_date(id):
    task = Todo.query.get_or_404(id)
    if request.method == 'POST':
        date = request.form['due']
        date_object = datetime.strptime(date, "%Y-%m-%d").date()
        task.due_date = date_object
        db.session.commit()
        return redirect('/')
    else:
        return render_template('set_due_date.html', task=task)


@app.route('/filter', methods=['GET', 'POST'])
def filter():
    if request.method == 'POST':
        option = request.form['filter']
        if option == 'due_date':
            date = request.form['filter_date']
            date_object = datetime.strptime(date, "%Y-%m-%d")
            tasks = Todo.query.filter_by(due_date=date_object).all()
            return render_template('filtered_list.html', tasks=tasks, option=option, date=date)

        else:
            date = request.form['filter_date']
            date_object = datetime.strptime(date, "%Y-%m-%d")
            tasks = Todo.query.filter(func.DATE(Todo.date_created) == date_object.date()).all()
            return render_template('filtered_list.html', tasks=tasks, option=option, date=date)

    else:
            return render_template('filtered_list.html')



if __name__ == "__main__":
    app.run(debug=True)

