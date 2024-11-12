import os
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response


tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)

# Use the DB credentials you received by e-mail
DB_USER = "oe2196"
DB_PASSWORD = "A102030o"
DB_SERVER = "w4111.cisxo09blonu.us-east-1.rds.amazonaws.com"

DATABASEURI = "postgresql://"+DB_USER+":"+DB_PASSWORD+"@"+DB_SERVER+"/w4111"

# This line creates a database engine that knows how to connect to the URI above
engine = create_engine(DATABASEURI)


@app.route('/')
def home():
    return "Hello, World!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8111, debug=True)
