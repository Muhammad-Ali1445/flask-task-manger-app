from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime, date
import enum

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = (
    "postgresql://postgres:123456@localhost:5432/flask_task_db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    tasks = db.relationship("Task", backref="user", lazy=True)


class TaskStatus(enum.Enum):
    PENDING = "Pending"
    IN_PROGRESS = "In Progress"
    COMPLETE = "Completed"


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(100), nullable=False)
    status = db.Column(db.Enum(TaskStatus), default=TaskStatus.PENDING, nullable=False)
    due_date = db.Column(db.Date(), default=date.today(), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime(), default=datetime.now(), nullable=False)

    @property
    def friendly_time(self):
        return self.created_at.strftime("%I:%M %p")


@app.route("/test")
def test():
    return "Testing Route"


@app.route("/task/<int:id>", methods=["GET"])
def get_single_task(id):
    task = Task.query.get_or_404(id)
    return render_template("index.html", tasks=[task])


@app.route("/tasks", methods=["GET"])
def get_all_tasks():
    all_tasks = Task.query.all()
    return render_template("index.html", tasks=all_tasks)


@app.route("/create_task", methods=["GET", "POST"])
def create_task():

    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        status_str = request.form.get("status")

        try:
            # Convert string to Enum object
            task_status = TaskStatus[status_str.upper()]

            # Create and Save Task
            newTask = Task(title=title, description=description, status=task_status)
            db.session.add(newTask)
            db.session.commit()

            # Redirect to the 'index' function (your list view)
            return redirect(url_for("get_all_tasks"))

        except Exception as e:
            db.session.rollback()
            # It's better to return a clear error or flash a message
            return f"Error: {str(e)}", 400

    return render_template("form.html")


@app.route("/update/<int:id>", methods=["GET", "POST"])
def update_task(id):
    task = Task.query.get_or_404(id)

    if request.method == "POST":
        task.title = request.form.get("title")
        task.description = request.form.get("description")
        status_str = request.form.get("status")
        task.status = TaskStatus[status_str.upper()]

        try:
            db.session.commit()
            return redirect(url_for("get_all_tasks"))
        except Exception as e:
            db.session.rollback()
            return f"update failed:{str(e)},400"

    return render_template("update.html", task=task)


@app.route("/delete/<int:id>", methods=["POST"])
def delete_task(id):
    task_to_delete = Task.query.get_or_404(id)

    try:
        db.session.delete(task_to_delete)
        db.session.commit()
        return redirect(url_for("get_all_tasks"))
    except Exception as e:
        db.session.rollback()
        return f"Error deleting task:{str(e)}", 400


if __name__ == "__main__":
    # with app.app_context():
    #     db.create_all()
    app.run(debug=True)
