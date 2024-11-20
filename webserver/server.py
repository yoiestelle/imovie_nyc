import os
from flask import Flask, request, render_template, g, session, flash, redirect
import random
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import * 
from sqlalchemy import text 
from sqlalchemy.pool import NullPool 
from datetime import datetime, timedelta
tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)


DB_USER = "oe2196"
DB_PASSWORD = "A102030o"
DB_SERVER = "w4111.cisxo09blonu.us-east-1.rds.amazonaws.com"

DATABASEURI = "postgresql://"+DB_USER+":"+DB_PASSWORD+"@"+DB_SERVER+"/w4111"

app.secret_key = 'A102030o'

engine = create_engine(DATABASEURI)

@app.before_request
def before_request():
  try:
    g.conn = engine.connect()
  except:
    print("uh oh, problem connecting to database")
    import traceback; traceback.print_exc()
    g.conn = None

@app.teardown_request
def teardown_request(exception):
  try:
    g.conn.close()
  except Exception as e:
    pass


@app.route('/')
def index():
    logged_in = 'email' in session
    return render_template('index.html', logged_in=logged_in, username=session.get('username'))

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

    if request.method == 'POST':
        search_term = request.form['name']
        base_query += " WHERE Movie.title LIKE :search "
        params = {'search': f"%{search_term}%"}
    else:
        params = {}

    base_query += "GROUP BY Movie.mid"

    final_query = text(base_query)

    cursor = g.conn.execute(final_query, params)

    # Populate movies list
    movies = [
        {
            'mid': row[0],
            'title': row[1],
            'synopsis': row[2],
            'average_rating': row[3]
        }
        for row in cursor
    ]
    cursor.close()

    logged_in = 'email' in session
    return render_template('movies.html', logged_in=logged_in, username=session.get('username'), data=movies)


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

    logged_in = 'email' in session
    return render_template('movie-details.html', logged_in=logged_in, movie=movie, mid=mid, reviews=reviews, screenings=screenings)

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

    logged_in = 'email' in session
    return render_template('review.html', logged_in=logged_in, reviews=reviews, mid=mid, movie=movie)





######The following is for content related to Events and Film Series#########

@app.route('/events', methods=['GET'])
def events():

    query = """
        SELECT *
        FROM Event
    """

    events = g.conn.execute(text(query)).fetchall()

    logged_in = 'email' in session
    return render_template('events.html', logged_in=logged_in, events=events)

@app.route('/film-series', methods=['GET'])
def filmseries():

    query = """
        SELECT *
        FROM Film_series
    """

    filmseries = g.conn.execute(text(query)).fetchall()

    logged_in = 'email' in session
    return render_template('film-series.html', logged_in=logged_in, filmseries=filmseries)

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

    logged_in = 'email' in session
    return render_template('film-series-info.html', logged_in=logged_in, film=filmseries, screenings=screenings)

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

    logged_in = 'email' in session
    return render_template('calendar.html', logged_in=logged_in, events=events, week_start=week_start, week_end=week_end)

# Route to navigate to the previous or next week
@app.route('/calendar/navigate', methods=['POST'])
def navigate_week():
    direction = request.form.get('direction', 'next')
    current_start = datetime.strptime(session.get('week_start', datetime.now().strftime('%Y-%m-%d')), '%Y-%m-%d')
    
    if direction == 'previous':
        new_week_start = current_start - timedelta(days=7)
    else:
        new_week_start = current_start + timedelta(days=7)
    
    session['week_start'] = new_week_start.strftime('%Y-%m-%d')
    return calendar_view()


######Watchlists##########


######The following is for content related to Movies#########
@app.route('/watchlists', methods=['GET', 'POST'])
def find_watchlist():
    base_query = """
        SELECT Watchlist_own.wid, Watchlist_own.owner, Watchlist_own.name
        FROM Watchlist_own
        WHERE Watchlist_own.status = 'public'
    """

    if request.method == 'POST':
        search_term = request.form['name']
        base_query += " AND Watchlist_own.name LIKE :search "
        params = {'search': f"%{search_term}%"}
    else:
        params = {}

    final_query = text(base_query)

    cursor = g.conn.execute(final_query, params)

    # Populate watchlists list
    watchlists = [
        {
            'wid': row[0], 
            'owner': row[1], 
            'name': row[2] 
        }
        for row in cursor
    ]
    cursor.close()

    logged_in = 'email' in session
    return render_template('watchlists.html', logged_in=logged_in, username=session.get('username'), data=watchlists)


@app.route('/watchlists/<int:wid>', methods=['GET'])
def watchlist_details(wid):
    query = """
        SELECT Watchlist_own.wid, Watchlist_own.name, Watchlist_own.owner
        FROM Watchlist_own
        WHERE Watchlist_own.wid = :wid
    """
    
    watchlist = g.conn.execute(text(query), {'wid': wid}).fetchone()

    query = """
        SELECT Movie.mid, Movie.title, Track.if_watched
        FROM Track
        LEFT JOIN Movie ON Movie.mid = Track.mid
        WHERE Track.wid = :wid
    """
    movies = g.conn.execute(text(query), {'wid': wid}).fetchall()

    logged_in = 'email' in session
    return render_template('watchlists-details.html', logged_in=logged_in, watchlist=watchlist, wid=wid, movies=movies)

@app.route('/create-watchlist', methods=['GET', 'POST'])
def create_watchlist():
    if 'email' not in session:
        return redirect('/login')

    if request.method == 'POST':
        while True:
            wid = random.randint(1, 10**6)
            query = "SELECT 1 FROM Watchlist_own WHERE wid = :wid"
            result = g.conn.execute(text(query), {'wid': wid}).fetchone()
            if not result:
                break

        name = request.form.get('name')
        if not name:
            return "Watchlist name is required", 400

        public_status = 'public' if 'public' in request.form else 'private'
        owner = session.get('email')

        query = """
            INSERT INTO Watchlist_own (wid, name, status, owner)
            VALUES (:wid, :name, :status, :owner)
        """
        g.conn.execute(text(query), {'wid': wid, 'name': name, 'status': public_status, 'owner': owner})

        return redirect(f'/watchlist/{wid}/add-movies')

    logged_in = 'email' in session
    return render_template('create_watchlist.html', logged_in=logged_in)


@app.route('/watchlist/<int:wid>/add-movies', methods=['GET', 'POST'])
def add_movies_to_watchlist(wid):
    if 'email' not in session:
        return redirect('/login')

    query = """
        SELECT Movie.mid, Movie.title, Movie.synopsis
        FROM Movie
    """
    params = {}

    if request.method == 'POST' and 'search' in request.form:
        search_term = request.form.get('search', '').strip()
        if search_term:
            query += " WHERE Movie.title LIKE :search"
            params = {'search': f"%{search_term}%"}

    cursor = g.conn.execute(text(query), params)
    movies = cursor.fetchall()
    cursor.close()

    if request.method == 'POST' and 'movies' in request.form:
        selected_movies = request.form.getlist('movies')
        for mid in selected_movies:
            query = """
                INSERT INTO Track (wid, mid, if_watched)
                VALUES (:wid, :mid, 0)
            """
            g.conn.execute(text(query), {'wid': wid, 'mid': mid})

        return redirect('/watchlists')

    logged_in = 'email' in session
    return render_template('add_movies_to_watchlist.html', logged_in=logged_in, wid=wid, movies=movies)



#####Login & SignUp & Profile#######
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        query = text("SELECT * FROM Users WHERE email = :email")
        
        with engine.connect() as connection:
            user = connection.execute(query, {'email': email}).fetchone()
        
        if user:
            user_password = user[2]
            if check_password_hash(user_password, password):
                session['username'] = user[1]
                session['email'] = user[0]
                flash("Successfully logged in!", "success")
                return index()
            else:
                flash("Invalid email or password.", "danger")
        else:
            flash("User not found.", "danger")
    
    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        description = request.form['description']
        hashed_password = generate_password_hash(password)
        
        try:
            query = text("INSERT INTO Users (email, username, password, description, is_admin) VALUES (:email, :username, :password, :description, 0)")
            engine.execute(query, {'email': email, 'username': username, 'password': hashed_password, 'description': description})
            flash("Account created successfully! Please log in.", "success")
            return login()
        except Exception as e:
            flash("Email already exists or there was an error. Please try again.", "danger")
    
    return render_template('signup.html')

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'email' not in session:
        flash("Please log in to access your profile.", "danger")
        return login()

    email = session['email']

    if request.method == 'POST':
        new_username = request.form['username']
        new_description = request.form['description']
        current_password = request.form['current_password']
        new_password = request.form['new_password']

        query = text("SELECT * FROM Users WHERE email = :email")
        user = engine.execute(query, {'email': email}).fetchone()

        if not user:
            flash("User not found.", "danger")
            return logout()

        if new_password and not check_password_hash(user['password'], current_password):
            flash("Incorrect current password.", "danger")
            return profile()

        update_query = text("""
            UPDATE Users
            SET username = :username,
                description = :description
                {password_clause}
            WHERE email = :email
        """.format(
            password_clause=", password = :new_password" if new_password else ""
        ))

        params = {
            'username': new_username,
            'description': new_description,
            'email': email
        }

        if new_password:
            hashed_password = generate_password_hash(new_password)
            params['new_password'] = hashed_password

        try:
            engine.execute(update_query, params)
            session['username'] = new_username
            flash("Profile updated successfully!", "success")
        except Exception as e:
            flash("An error occurred while updating your profile.", "danger")

        return profile()

    query = text("SELECT * FROM Users WHERE email = :email")
    user = engine.execute(query, {'email': email}).fetchone()

    logged_in = 'email' in session
    return render_template('profile.html', logged_in=logged_in, user=user)



#logout
@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return index()

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

