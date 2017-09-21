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
            
            bajaItem = Bajas(
                razonSocial = request.form['razonsocial'],
                sucursal = request.form['sucursal'],
                usuaria=request.form['usuaria'],
                nombre = request.form['nombre'],
                apellido = request.form['apellido'],
                cuit = request.form['cuit'],
                fechaIngreso = request.form['date-ingreso'],
                fechaEgreso = request.form['date-egreso'],
                fechaBaja = request.form['date-baja'],
                mejorRemu = request.form['remuneracion'],
                situacion = request.form['situacion'],
                suspensionDesde = request.form['date-desde'],
                suspensionHasta = request.form['date-hasta'],
                comentarios = request.form['comentarios'])

            session.add(bajaItem)
            session.commit()
            print ('New Baja Item Successfully Created !!!')  
            
            return redirect(url_for('showMain'))
           
            

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
               

    
# Show movie details
@app.route('/bajas/view/<int:id>', methods=['GET'])
def showBaja(id):
    item = session.query(Bajas).filter_by(id = id).one()
    
    return render_template('view-baja.html', item = item)

    # if 'username' in login_session:
    #     username = login_session['username']
    #     return render_template('movie.html', movie = movie, genres = genres, 
    #             username = checkUserLogged(), picture = login_session['picture'])
    # else:
    #     return render_template('movie.html', movie = movie, genres = genres, 
    #             username = "")

        
# Show all genres
@app.route('/', methods=['GET'])
@app.route('/public/', methods=['GET'])
def showMain():
    listbajas = session.query(Bajas).order_by(Bajas.razonSocial.desc())
    
    return render_template('public.html', listbajas = listbajas)

    # if 'username' not in login_session:
    #     return render_template('public.html')
    #     # return render_template('main.html', lastmovies = lastmovies, genres = genres,
    #     # username = "")
    # else:
    #     return render_template('public.html', lastmovies = lastmovies, genres = genres,
    #     username = checkUserLogged(), picture = login_session['picture'])


if __name__ == '__main__':
    app.secret_key = "secret key"
    app.debug = True
    app.run(host = '0.0.0.0', port = 8080)
