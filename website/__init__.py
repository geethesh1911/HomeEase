from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from os import path

db = SQLAlchemy()
#---------------------- App ----------------------------------
def create_app():
    app=Flask(__name__)
    app.config['SECRET_KEY']='DSiitm'
    app.config['SQLALCHEMY_DATABASE_URI']='sqlite:///database.db'
    db.init_app(app)

    from .views import views
    from .auth import auth
    
    app.register_blueprint(views,url_prefix='/')
    app.register_blueprint(auth,url_prefix='/')

    from .models import User,ProfessionalDetails
    
    create_database(app)

    return app

def create_database(app):
    if not path.exists('website/database.db'):
        with app.app_context():
            db.create_all() 
        print("Database created")