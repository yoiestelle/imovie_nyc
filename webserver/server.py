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

@app.before_request
def before_request():
  """
  This function is run at the beginning of every web request 
  (every time you enter an address in the web browser).
  We use it to setup a database connection that can be used throughout the request

  The variable g is globally accessible
  """
  try:
    g.conn = engine.connect()
  except:
    print("uh oh, problem connecting to database")
    import traceback; traceback.print_exc()
    g.conn = None

@app.teardown_request
def teardown_request(exception):
  """
  At the end of the web request, this makes sure to close the database connection.
  If you don't the database could run out of memory!
  """
  try:
    g.conn.close()
  except Exception as e:
    pass


@app.route('/')
def index():
  
  return render_template("index.html")



#
# This is an example of a different path.  You can see it at
# 
#     localhost:8111/another
#
# notice that the functio name is another() rather than index()
# the functions for each app.route needs to have different names
#
@app.route('/movies')
def movies():
    cursor = g.conn.execute("""
        SELECT Movie.title, Movie.synopsis, AVG(Reviews_Rate_Write.rating) AS average_rating
        FROM Movie
        LEFT JOIN Reviews_Rate_Write ON Movie.mid = Reviews_Rate_Write.mid
        GROUP BY Movie.mid
    """)
    
    movies = [
        {'title': row['title'], 'synopsis': row['synopsis'], 'average_rating': row['average_rating']}
        for row in cursor
    ]
    
    cursor.close()
    
    context = dict(data=movies)
    return render_template("movies.html", **context)

@app.route('/findmovie', methods=['GET', 'POST'])
def find_movie():
    if request.method == 'POST':
        search_term = request.form['name']
        
        cmd = """
            SELECT Movie.title, Movie.synopsis, AVG(Reviews_Rate_Write.rating) AS average_rating
            FROM Movie
            LEFT JOIN Reviews_Rate_Write ON Movie.mid = Reviews_Rate_Write.mid
            WHERE Movie.title LIKE :search
            GROUP BY Movie.mid
        """
        cursor = g.conn.execute(cmd, search=f"%{search_term}%")
        
        movies = [
            {'title': row['title'], 'synopsis': row['synopsis'], 'average_rating': row['average_rating']}
            for row in cursor
        ]
        
        cursor.close()
        
        context = dict(data=movies)
        return render_template("movies.html", **context)
    return render_template("findmovie.html")


@app.route('/login')
def login():
    abort(401)
    this_is_never_executed()


if __name__ == "__main__":
  import click

  @click.command()
  @click.option('--debug', is_flag=True)
  @click.option('--threaded', is_flag=True)
  @click.argument('HOST', default='0.0.0.0')
  @click.argument('PORT', default=8111, type=int)
  def run(debug, threaded, host, port):
    HOST, PORT = host, port
    print("running on %s:%d" % (HOST, PORT))
    app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)
  run()

