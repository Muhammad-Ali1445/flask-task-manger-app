import enum
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime, date
from flask_login import UserMixin
from extensions import login_manager
from flask_login import login_user, current_user, login_required, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = (
    "postgresql://postgres:123456@localhost:5432/flask_task_db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.config["SECRET_KEY"] = "123456"

db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
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
    due_date = db.Column(db.Date(), default=date.today, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime(), default=datetime.now, nullable=False)

    @property
    def friendly_time(self):
        return self.created_at.strftime("%I:%M %p")


@app.route("/test")
def test():
    return "Testing Route"


# ----- Authentication ---------


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("get_all_tasks"))
        else:
            flash("Invalid username or password", "danger")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")

        existing_user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()
        if existing_user:
            flash("User already Exist", "danger")
            return redirect(url_for("login"))

        user = User(username=username, email=email, password="")
        user.set_password(password)

        try:
            db.session.add(user)
            db.session.commit()

            flash("Account Created successfully! Please login", "success")
            return redirect(url_for("login"))
        except Exception as e:
            db.session.rollback()
            return f"Error {str(e)}", 500
    return render_template("register.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logout Successfully", "info")
    return redirect(url_for("login"))


# ----------- Tasks ------------


# @app.route("/task/<int:id>", methods=["GET"])
# def get_single_task(id):
#     task = Task.query.get_or_404(id)
#     return render_template("index.html", tasks=[task])


@app.route("/task/<int:id>", methods=["GET"])
@login_required
def get_single_task(id):
    task = Task.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    return render_template("index.html", tasks=[task])


# -- tasks of logged in user
@app.route("/tasks", methods=["GET"])
@login_required
def get_all_tasks():
    all_tasks = Task.query.filter_by(user_id=current_user.id).all()
    return render_template("index.html", tasks=all_tasks)


@app.route("/create_task", methods=["GET", "POST"])
@login_required
def create_task():

    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        status_str = request.form.get("status")

        try:
            # Convert string to Enum object
            task_status = TaskStatus[status_str.upper()]

            # Create and Save Task
            newTask = Task(
                title=title,
                description=description,
                status=task_status,
                user_id=current_user.id,
            )
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
@login_required
def update_task(id):
    task = Task.query.filter_by(id=id, user_id=current_user.id).first_or_404()

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
@login_required
def delete_task(id):
    task_to_delete = Task.query.filter_by(id=id, user_id=current_user.id).first_or_404()

    try:
        db.session.delete(task_to_delete)
        db.session.commit()
        return redirect(url_for("get_all_tasks"))
    except Exception as e:
        db.session.rollback()
        return f"Error deleting task:{str(e)}", 400


@app.cli.command("create-admin")
def create_admin():
    """Custom command to create a default user."""
    # This automatically handles the 'app context' for you!
    user = User(username="ali", email="ali@gmail.com")
    user.set_password("123456")
    db.session.add(user)
    db.session.commit()
    print("User 'ali' created successfully!")


if __name__ == "__main__":
    # with app.app_context():
    #     db.create_all()
    app.run(debug=True)
