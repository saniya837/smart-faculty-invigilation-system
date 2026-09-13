
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from functools import wraps
from models import User, db
from werkzeug.security import generate_password_hash

auth_bp = Blueprint("auth", __name__)


# ----------------------------
# Login Required Decorator
# ----------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first.", "error")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function


# ----------------------------
# Role Required Decorator
# ----------------------------
def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):

            if "user_id" not in session:
                flash("Please login first.", "error")
                return redirect(url_for("auth.login"))

            if session.get("role") != role:
                flash("Unauthorized access.", "error")

                if session.get("role") == "admin":
                    return redirect(url_for("admin.dashboard"))

                elif session.get("role") == "faculty":
                    return redirect(url_for("faculty.dashboard"))

                return redirect(url_for("auth.login"))

            return f(*args, **kwargs)

        return decorated_function
    return decorator


# ----------------------------
# First-Time Admin Setup
# ----------------------------
@auth_bp.route("/setup", methods=["GET", "POST"])
def setup():

    # If an admin already exists, setup is no longer allowed.
    existing_admin = User.query.filter_by(role="admin").first()

    if existing_admin:
        flash("Initial setup has already been completed.", "error")
        return redirect(url_for("auth.login"))

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        if not username or not password or not confirm_password:
            flash("Please fill in all fields.", "error")
            return render_template("setup.html")

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
            return render_template("setup.html")

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("setup.html")

        existing_user = User.query.filter_by(username=username).first()

        if existing_user:
            flash("Username already exists. Please choose another.", "error")
            return render_template("setup.html")

        admin = User(
            username=username,
            password=generate_password_hash(password),
            role="admin",
            faculty_id=None
        )

        db.session.add(admin)
        db.session.commit()

        flash("Admin account created successfully. Please login.", "success")

        return redirect(url_for("auth.login"))

    return render_template("setup.html")


# ----------------------------
# Login
# ----------------------------
@auth_bp.route("/login", methods=["GET", "POST"])
def login():

    if "user_id" in session:

        if session.get("role") == "admin":
            return redirect(url_for("admin.dashboard"))

        elif session.get("role") == "faculty":
            return redirect(url_for("faculty.dashboard"))

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if username == "" or password == "":
            flash("Please enter username and password.", "error")
            return render_template("login.html")

        user = User.query.filter_by(username=username).first()

        print("=" * 60)
        print("LOGIN ATTEMPT")
        print("Username entered :", username)
        print("User found :", user)

        if user:
            print("Stored Role :", user.role)
            print("Password Match :", user.check_password(password))

        print("=" * 60)

        if user and user.check_password(password):

            session.clear()

            session["user_id"] = user.id
            session["username"] = user.username
            session["role"] = user.role
            session["faculty_id"] = user.faculty_id

            flash("Login successful.", "success")

            if user.role == "admin":
                return redirect(url_for("admin.dashboard"))

            return redirect(url_for("faculty.dashboard"))

        flash("Invalid username or password.", "error")

    return render_template("login.html")


# ----------------------------
# Logout
# ----------------------------
@auth_bp.route("/logout")
@login_required
def logout():

    session.clear()

    flash("Logged out successfully.", "success")

    return redirect(url_for("auth.login"))