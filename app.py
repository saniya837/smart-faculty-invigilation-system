import os

import pymysql
pymysql.install_as_MySQLdb()

from flask import Flask, redirect, url_for, session

from config import Config

from models import (
    db,
    Department,
    Faculty,
    ExaminationHall,
    Exam,
    User,
    Assignment,
    Notification,
    ExchangeRequest
)

from routes import auth_bp, admin_bp, faculty_bp


print("Step 1: app.py loaded")


def create_app():
    print("Creating Flask app...")

    app = Flask(__name__)
    app.config.from_object(Config)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["REPORTS_FOLDER"], exist_ok=True)

    db.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(faculty_bp)

    @app.route("/")
    def index():
        if "user_id" in session:
            if session.get("role") == "admin":
                return redirect(url_for("admin.dashboard"))
            return redirect(url_for("faculty.dashboard"))

        return redirect(url_for("auth.login"))

    print("Flask app created")
    return app


def setup_database(app):
    with app.app_context():

        print("Running database setup...")

        try:
            print("Creating database tables...")

            db.create_all()

            print("Tables created successfully!")

        except Exception:
            print("DATABASE ERROR:")
            import traceback
            traceback.print_exc()
            raise


print("Starting application...")

app = create_app()


if __name__ == "__main__":

    setup_database(app)

    print("Starting Flask server...")

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )