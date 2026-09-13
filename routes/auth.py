
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from functools import wraps
from models import User, db

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