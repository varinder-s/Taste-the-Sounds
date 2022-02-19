import os
import sqlite3

from flask import Flask, flash, redirect, render_template, request, session, json
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import getTrack, getFeatures, fillDB, getFood, updateDB

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Ensure all API keys are initialized
if not os.environ.get("SPOTIPY_CLIENT_ID") or not os.environ.get("SPOTIPY_CLIENT_SECRET") or not os.environ.get("SPOONACULAR_API_KEY"):
    raise RuntimeError("App credentials not set")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/response", methods=["POST"])
def response():
    
    # Ensure song was submitted
    if not request.form.get("song"):
        return redirect("/")
        
    # Get song from Spotify search
    song = request.form.get("song")
    track = getTrack(song)
    
    # Ensure search found a song
    if len(track["tracks"]["items"]) < 1:
        return redirect("/")
    track = track["tracks"]["items"][0]
    
    # Update database with track's audio features
    updateDB(track)
    
    # Get food info from Spoonacular
    food = getFood(track)
    if len(food) < 1:
        return redirect("/")
        
    # Allow logged in users to get multiple options for each search
    if "user_id" in session:
        data = json.dumps(food)
        return render_template("response.html",food=food, track=track, data=data)
    else:
        food = food[:1]
        data = json.dumps(food)
        return render_template("response.html",food=food, track=track, data=data)
    
@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Connect to SQLite database
        con = sqlite3.connect("project.db")
        con.row_factory = sqlite3.Row
        db = con.cursor()

        # Ensure username was submitted
        if not request.form.get("username"):
            return redirect("login.html")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return redirect("login.html")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", (request.form.get("username"),)).fetchall()

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return redirect("login.html")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        
        # Connect to SQLite database
        con = sqlite3.connect("project.db")
        con.row_factory = sqlite3.Row
        db = con.cursor()

        # Ensure user inputs a username
        if not request.form.get("username"):
            return render_template("register.html")
            
        # Ensure user inputs a username that is not taken
        rows = db.execute("SELECT * FROM users WHERE username = ?", (request.form.get("username"),)).fetchall()
        if len(rows) != 0:
            return render_template("register.html")
            
        # Ensure user inputs a password
        if not request.form.get("password") or not request.form.get("confirmation"):
            return render_template("register.html")
            
        # Ensure password and password confirmation match
        if request.form.get("password") != request.form.get("confirmation"):
            return render_template("register.html")
        
        # Insert username and password hash into database
        db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", [request.form.get("username"),
                   generate_password_hash(request.form.get("password"), method='pbkdf2:sha256', salt_length=8)])
        con.commit()
        return render_template("login.html")
    else:
        return render_template("register.html")
        
@app.route("/about")
def about():
    return render_template("about.html")

# Create an account in order to save search history and get a different recommendation if you don't like the first one, also allow users to pick the song if the results isnt for the song they had in mind (session[song] to store input)
# Add filters for the search (breakfast, lunch, dinner, dietary restrictions, etc)
# Add like buttons for rec to influence future answers
# Go through list of foods that match if they keep asking for different rec, after list is done, say that algo is work in progress and new matches will be available soon
