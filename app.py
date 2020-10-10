from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from datetime import datetime


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///new.db'
db = SQLAlchemy(app)


class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return '<Task %r>' % self.id


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        task_content = request.form['content']
        new_task = Todo(content=task_content)
        try:
            db.session.add(new_task)
            db.session.commit()
            return redirect('/')
        except:
            return 'There was an error'
    else:
        page = request.args.get('page', 1, type=int)
        tasks = Todo.query.order_by(Todo.date_created.desc()).paginate(page=page, per_page=8)
        return render_template('index.html', tasks=tasks)


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
            page = request.args.get('page', 1, type=int)
            tasks = Todo.query.filter_by(due_date=date_object).paginate(page=page, per_page=8)
            return render_template('filtered_list.html', tasks=tasks)
        else:
            date = request.form['filter_date']
            date_object = datetime.strptime(date, "%Y-%m-%d")
            page = request.args.get('page', 1, type=int)
            tasks = Todo.query.filter(func.DATE(Todo.date_created) == date_object.date()).paginate(page=page, per_page=8)
            return render_template('filtered_list.html', tasks=tasks)


if __name__ == "__main__":
    app.run(debug=True)

