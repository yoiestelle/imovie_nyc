import os
from flask import Flask, request, render_template, g, redirect, url_for, session, Response
from sqlalchemy import * 
from sqlalchemy import text 
from sqlalchemy.pool import NullPool 
from datetime import datetime, timedelta
tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)

# Use the DB credentials you received by e-mail
DB_USER = "oe2196"
DB_PASSWORD = "A102030o"
DB_SERVER = "w4111.cisxo09blonu.us-east-1.rds.amazonaws.com"

DATABASEURI = "postgresql://"+DB_USER+":"+DB_PASSWORD+"@"+DB_SERVER+"/w4111"

app.secret_key = 'A102030o'
# This line creates a database engine that knows how to connect to the URI above
engine = create_engine(DATABASEURI) # type: ignore

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
    return render_template('index.html')

#########The following is for calendar################



######The following is for content related to Movies#########
@app.route('/movies', methods=['GET', 'POST'])
def find_movie():

    base_query = """
        SELECT Movie.mid, Movie.title, Movie.synopsis, 
               CAST(AVG(Reviews_Rate_Write.rating) AS DECIMAL(10, 2)) AS average_rating
        FROM Movie
        LEFT JOIN Reviews_Rate_Write ON Movie.mid = Reviews_Rate_Write.mid
    """

    #If the user submits a search term, add a WHERE clause
    if request.method == 'POST':
        search_term = request.form['name']
        # Add the search condition to the query
        base_query += " WHERE Movie.title LIKE :search "
        params = {'search': f"%{search_term}%"}
    else:
        params = {}

    #Complete the query adding the GROUP BY clause
    base_query += "GROUP BY Movie.mid"

    final_query = text(base_query)

    #Execute the query with parameters using text()
    cursor = g.conn.execute(final_query, **params)

    #populate movies dict
    movies = [
        {
            'mid': row['mid'],
            'title': row['title'],
            'synopsis': row['synopsis'],
            'average_rating': row['average_rating']
        }
        for row in cursor
    ]
    cursor.close()
    return render_template('movies.html', data=movies)


@app.route('/movie/<int:mid>', methods=['GET'])
def movie_details(mid):
    query = """
        SELECT Movie.title, Movie.synopsis, Movie.length, Movie.director_name, 
               Movie.cast_name, Movie.is_black_n_white, Movie.release_year, 
               Movie.dub_langs, Movie.sub_langs, Movie.film_size, 
               Movie.ticket_purchase_link,
               CAST(AVG(Reviews_Rate_Write.rating) AS DECIMAL(10, 2)) AS average_rating
        FROM Movie
        LEFT JOIN Reviews_Rate_Write ON Movie.mid = Reviews_Rate_Write.mid
        WHERE Movie.mid = :mid
        GROUP BY Movie.mid
    """
    

    movie = g.conn.execute(text(query), {'mid': mid}).fetchone()

    query = """
        SELECT Event.event_time, Event.event_date
        FROM Play
        LEFT JOIN Event ON Play.eid = Event.eid
        WHERE Play.mid = :mid
    """
    screenings = g.conn.execute(text(query), {'mid': mid}).fetchall()

    reviews_query = """
        SELECT Reviews_Rate_Write.content, Reviews_Rate_Write.rating, Reviews_Rate_Write.writer, 
               Reviews_Rate_Write.time, Reviews_Rate_Write.date
        FROM Reviews_Rate_Write
        WHERE Reviews_Rate_Write.mid = :mid
        LIMIT 2
    """
    reviews = g.conn.execute(text(reviews_query), {'mid': mid}).fetchall()

    return render_template('movie-details.html', movie=movie, mid=mid, reviews=reviews, screenings=screenings)

@app.route('/movie/<int:mid>/reviews', methods=['GET'])
def all_reviews(mid):
    movie_query ="""
        SELECT Movie.title
        FROM Movie
        WHERE Movie.mid = :mid
    """
    reviews_query = """
        SELECT Reviews_Rate_Write.content, Reviews_Rate_Write.rating, Reviews_Rate_Write.writer, 
               Reviews_Rate_Write.time, Reviews_Rate_Write.date
        FROM Reviews_Rate_Write
        WHERE Reviews_Rate_Write.mid = :mid
    """
    movie= g.conn.execute(text(movie_query), {'mid':mid}).fetchone()

    reviews = g.conn.execute(text(reviews_query), {'mid': mid}).fetchall()

    return render_template('review.html', reviews=reviews, mid=mid, movie=movie)


##############################################




######The following is for content related to Events and Film Series#########

@app.route('/events', methods=['GET'])
def events():

    query = """
        SELECT *
        FROM Event
    """

    events = g.conn.execute(text(query)).fetchall()

    return render_template('events.html', events=events)

@app.route('/film-series', methods=['GET'])
def filmseries():

    query = """
        SELECT *
        FROM Film_series
    """

    filmseries = g.conn.execute(text(query)).fetchall()

    return render_template('film-series.html', filmseries=filmseries)

@app.route('/film-series/<int:fsid>', methods=['GET'])
def filmseriesinfo(fsid):

    film_query = """
        SELECT *
        FROM Film_series
        WHERE Film_series.fsid = :fsid
    """
    screenings_query = """
        SELECT Event.event_date, Event.event_time, Movie.title, Movie.mid
        FROM Include
        LEFT JOIN Event ON Event.eid=Include.eid
        LEFT JOIN Play ON Play.eid=Include.eid
        LEFT JOIN Movie ON Movie.mid=Play.mid
        WHERE Include.fsid = :fsid
    """

    filmseries = g.conn.execute(text(film_query), {'fsid': fsid}).fetchone()
    screenings = g.conn.execute(text(screenings_query), {'fsid': fsid}).fetchall()

    return render_template('film-series-info.html', film=filmseries, screenings=screenings)

##############################################


@app.route('/calendar', methods=['GET'])
def calendar_view():
    # Default to the current week if no specific week is chosen
    if 'week_start' in session:
        week_start = datetime.strptime(session['week_start'], '%Y-%m-%d')
    else:
        # Calculate the start of the current week (Monday)
        today = datetime.now()
        week_start = today - timedelta(days=today.weekday())
        session['week_start'] = week_start.strftime('%Y-%m-%d')

    # Calculate the end of the week (Sunday)
    week_end = week_start + timedelta(days=6)

    # Fetch events within the specified week range
    events_query = """
        SELECT Event.event_date, Event.event_time, Event.eid, Event.title
        FROM Event
        WHERE Event.event_date BETWEEN :week_start AND :week_end
        ORDER BY Event.event_date, Event.event_time
    """
    events = g.conn.execute(text(events_query), {
        'week_start': week_start.strftime('%Y-%m-%d'),
        'week_end': week_end.strftime('%Y-%m-%d')
    }).fetchall()

    return render_template('calendar.html', events=events, week_start=week_start, week_end=week_end)

# Route to navigate to the previous or next week
@app.route('/calendar/navigate', methods=['POST'])
def navigate_week():
    direction = request.form.get('direction', 'next')
    current_start = datetime.strptime(session.get('week_start', datetime.now().strftime('%Y-%m-%d')), '%Y-%m-%d')
    
    # Adjust the week start based on the navigation direction
    if direction == 'previous':
        new_week_start = current_start - timedelta(days=7)
    else:
        new_week_start = current_start + timedelta(days=7)
    
    # Update session with new week
    session['week_start'] = new_week_start.strftime('%Y-%m-%d')
    return redirect(url_for('calendar_view'))




@app.route('/login')
def login():
    os.abort(401)
    this_is_never_executed()


if __name__ == "__main__":
  import click # type: ignore

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

