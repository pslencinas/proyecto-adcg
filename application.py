from flask import Flask, g, render_template, jsonify, url_for, flash
from flask import request, redirect, make_response
from flask import session as login_session
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from functools import wraps
from database_setup import Base, Bajas, User
from oauth2client.client import flow_from_clientsecrets, FlowExchangeError
import random
import string
import httplib2
import json
import requests

app = Flask(__name__)

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']

# Connect to Database and create database session
engine = create_engine('postgresql://adecco:adecco2009@localhost/adeccodb')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


@app.route('/login')
def login():
    state = ''.join(random.choice(
        string.ascii_uppercase + string.digits) for x in xrange(32))
    # store it in session for later use
    login_session['state'] = state
    return render_template('login.html', STATE = state)


# GConnect
@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code, now compatible with Python3
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    # Submit request, parse response - Python3 compatible
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])

    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'),
                                     200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)

    login_session['user_id'] = user_id

    output = ''
    output += '<h3>Welcome, '
    output += login_session['username']
    output += '!</h3>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 100px; height: 100px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    print "Usuario " + login_session['username']
    return output
    

@app.route('/gdisconnect')
def gdisconnect():
        # Only disconnect a connected user.
    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] == '200':
        # Reset the user's sesson.
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return redirect(url_for('showGenres'))
    else:
        # For whatever reason, the given token was invalid.
        response = make_response(
            json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
    return response

# User Helper Functions
def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


def checkUserLogged():
    username = None
    if 'username' in login_session:
        username = login_session['username']
    return username

# JSON APIs to view Category Information
@app.route('/catalog/json')
def categoriesJSON():
    genres = session.query(Genre).all()
    genreList = []
    for genre in genres:
        genreItems = session.query(Movie).filter_by(
                            genre_id=genre.id).all()
        genreItemsList = []
        for items in genreItems:
            genreItemsList.append(items.serialize)
        genre = genre.serialize
        genre['items'] = genreItemsList
        genreList.append(genre)
    return jsonify(genres=genreList)


# Create a new Baja item
@app.route('/bajas/new/', methods=['GET', 'POST'])
def newBajaItem():

    # if 'username' not in login_session:
    #     return redirect(url_for('login'))

    #genres = session.query(Genre).order_by(asc(Genre.name))
    if request.method == 'GET':
        return render_template('add-baja.html',
                                #genres=genres,
                                username=checkUserLogged())
    else:
        if request.method == 'POST':
            item = session.query(Movie).filter_by(
                    name=request.form['name']).first()
            if not item:
                movieItem = Movie(
                    name = request.form['name'],
                    overview=request.form['overview'],
                    director = request.form['director'],
                    youtube_url = request.form['url_youtube'],
                    poster_url = request.form['url_poster'],
                    genre_id = request.form['category'],
                    user_id = login_session['user_id']) 
                session.add(movieItem)
                flash('New Movie Item %s Successfully Created'
                      % movieItem.name)
                session.commit()
                return redirect(url_for('showGenres'))
            else:
                flash('Movie has already created')
                return redirect(url_for('showGenres'))
            

# Edit Movie item
@app.route('/catalog/edit/<int:id>', methods=['GET', 'POST'])
def editItem(id):

    if 'username' not in login_session:
        return redirect(url_for('login'))
    else:
        movie = session.query(Movie).filter_by(id = id).one()
        genres = session.query(Genre).order_by(asc(Genre.name))

        if movie.user_id != login_session['user_id']:
            error = "you dont have privileges to edit this item!!!"
            return render_template('movie.html', movie = movie, genres = genres, 
                username = checkUserLogged(), picture = login_session['picture'],
                error = error)

        if request.method == 'GET':
            return render_template('edit-movie.html',
                                    movie = movie,
                                    genres = genres,
                                    username = checkUserLogged())
        else:
            if request.method == 'POST':
                movie.name = request.form['name']
                movie.overview=request.form['overview']
                movie.director = request.form['director']
                movie.youtube_url = request.form['url_youtube']
                movie.poster_url = request.form['url_poster']
                movie.genre_id = request.form['category']
                flash('Movie Item %s Successfully edited'
                          % movie.name)
                # session.commit()
                return redirect(url_for('showMovie', id=movie.id))
               


# Delete Movie item
@app.route('/catalog/delete/<int:id>', methods=['GET', 'POST'])
def deleteItem(id):

    if 'username' not in login_session:
        return redirect(url_for('login'))
    else:
        movie = session.query(Movie).filter_by(id = id).one()
        genres = session.query(Genre).order_by(asc(Genre.name))

        if movie.user_id != login_session['user_id']:
            error = "you dont have privileges to delete this item!!!"
            return render_template('movie.html', movie = movie, genres = genres, 
                username = checkUserLogged(), picture = login_session['picture'],
                error = error)

        if request.method == 'GET':
            return render_template('delete-movie.html',
                                    movie = movie,
                                    username = checkUserLogged())
        else:
            if request.method == 'POST':
                session.delete(movie)
                flash('Movie Item %s Successfully edited'
                          % movie.name)
                # session.commit()
                return redirect(url_for('showGenres'))
               


# Show movie from a genre
@app.route('/catalog/<int:genre_id>/items/', methods=['GET'])
def showMovies(genre_id):
    genre = session.query(Genre).filter_by(id = genre_id).one()
    genres = session.query(Genre).order_by(asc(Genre.name))
    
    movies = session.query(Movie).filter_by(genre_id = genre_id).all()
    
    if 'username' in login_session:
        username = login_session['username']
        return render_template('publicmovies.html', movies = movies, genres = genres,
            username = checkUserLogged(), picture = login_session['picture'])
    else:
        return render_template('publicmovies.html', movies = movies, genres = genres,
            username = "")

    
    
# Show movie details
@app.route('/catalog/movie/<int:id>', methods=['GET'])
def showMovie(id):
    movie = session.query(Movie).filter_by(id = id).one()
    genres = session.query(Genre).order_by(asc(Genre.name))
    
    if 'username' in login_session:
        username = login_session['username']
        return render_template('movie.html', movie = movie, genres = genres, 
                username = checkUserLogged(), picture = login_session['picture'])
    else:
        return render_template('movie.html', movie = movie, genres = genres, 
                username = "")

        
# Show all genres
@app.route('/', methods=['GET'])
@app.route('/public/', methods=['GET'])
def showGenres():
    # lastmovies = session.query(Movie).order_by(asc(Movie.name)).limit(5)
    # genres = session.query(Genre).order_by(asc(Genre.name))
    
    if 'username' not in login_session:
        return render_template('public.html')
        # return render_template('main.html', lastmovies = lastmovies, genres = genres,
        # username = "")
    else:
        return render_template('public.html', lastmovies = lastmovies, genres = genres,
        username = checkUserLogged(), picture = login_session['picture'])


if __name__ == '__main__':
    app.secret_key = "secret key"
    app.debug = True
    app.run(host = '0.0.0.0', port = 8080)
