from flask import Flask, render_template, flash, redirect, url_for, session, request, Response, logging
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps
import tweepy
from tweepy.streaming import StreamListener
from tweepy import Stream 
import json
import pubsub
from datetime import datetime
from pytz import timezone
import pytz


# from flask.ext.tweepy import Tweepy


app = Flask(__name__)



CONSUMER_KEY = 'Pn26K8Y7om1jkjUlGpYpAwtPL'
CONSUMER_SECRET = '0pEJHN0EFOdK8LHLddwOfLr39z6230MKYJ7YumtQuHz4nZWMVH'
ACCESS_TOKEN = '396446643-h1mIgQS8crGcvMC8pwwkPaAxwyIu9rMYUD9l45aP'
ACCESS_TOKEN_SECRET = 'mDbdN8zuOJrwmv1lVbUid1LduBe0n2LRKpItjmFNFSTwi'

# MYSQL CONFIGS
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'
app.config['MYSQL_DB'] = 'mydemo'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# init MySQL
mysql = MySQL(app)


class MyStreamListener(tweepy.StreamListener):

	def on_status(self, status):
		print("User ID: " + str(status.user.id))
		print("User Name: " + status.user.name)
		print("Tweet Message: " + status.text)
		print("Tweet Favorited \t:" + str(status.favorited))
		print("Tweet Favorited count \t:" + str(status.favorite_count))
		print("Tweet Source: " + status.source)


	# def on_data(self, body):
		
	# 	tweet = json.loads(body)

	# 	date_format = '%Y-%m-%d'
	# 	time_format = '%H:%M:%S'

	# 	ts = tweet['timestamp_ms']
	# 	date = datetime.fromtimestamp(int(ts)/1000, tz=pytz.timezone('EST'))
	# 	tweet['MYT_local_date'] = date.strftime(date_format)
	# 	tweet['MYT_local_time'] = date.strftime(time_format)
 	
	def on_error(self, status_code):
		if status_code == 403:
			print("The request is understood, but it has been refused or access is not allowed. Limit is maybe reached")
			return False


 

@app.route('/')
def index():
	return render_template('_layout.html')


@app.route('/about')
def about():
	return render_template('about.html')


# Register Form Class
class RegisterForm(Form):
	name = StringField('Name', [validators.Length(min=1, max=50)])
	username = StringField('Username', [validators.Length(min= 4, max=25)])
	email = StringField('Email', [validators.Length(min=6, max=50)])
	password = PasswordField('Password', [
		validators.DataRequired(),
		validators.EqualTo('confirm', message='Passwords do not match')
		])
	confirm = PasswordField('Confirm Password')


# Register an account
@app.route('/register', methods=['GET', 'POST'])
def register():
	form = RegisterForm(request.form)
	if request.method == 'POST' and form.validate():
		name = form.name.data
		email = form.email.data
		username = form.username.data
		password = sha256_crypt.encrypt(str(form.password.data))

		# Create cursor
		cur = mysql.connection.cursor()

		# Execute query
		cur.execute("INSERT INTO myusers(Name, Email, Username, Password) VALUES (%s,%s,%s,%s)", (name, email, username, password))

		# Commit to db
		mysql.connection.commit()

		# Close connection
		cur.close()

		flash('you are now registerd and can login', 'success') 
		redirect(url_for('index'))


	return render_template('register.html', form=form)

# Login
@app.route('/', methods=['GET', 'POST'])
def login():
	if request.method == 'POST':
		username = request.form['Username']
		password_canidate = request.form['Password']

		# Create a cursor
		cur = mysql.connection.cursor()

		# Get username from db
		result = cur.execute("SELECT * FROM myusers WHERE Username = %s", 
			[username])
		if result > 0:
			data = cur.fetchone()
			password = data['Password']

			if sha256_crypt.verify(password_canidate, password):
				session['logged_in'] = True
				session['username'] = username

				
				return redirect(url_for('account'))
			else:
				error = 'invalid login credentials'
				return render_template('_layout.html', error=error)
				# Close connection
				cur.close()
		else:
			error = 'username not found'
			return render_template('_layout.html', error=error)

	return render_template('_layout.html')

@app.route('/SearchTweets')
def searchtweets():
	return render_template('SearchTweets.html')


# Make a tweet using tweepy
@app.route('/SearchTweets', methods=['GET', 'POST'])
def Maketweets():
	if request.method == 'POST':
		# Setting OAuth with Consumer key & Consumer secret key
		auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
		# Setting Access token keys
		auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
		
		api = tweepy.API(auth)
		status = request.form['tweets']
		api.update_status(status=status)
		flash('You successfully posted a new tweet. Check your twitter account!', 'success')
		return redirect(url_for('account'))

	return render_template('account.html')

@app.route('/stream')
def stream():
    # we will use Pub/Sub process to send real-time tweets to client
    def event_stream():
        # instantiate pubsub
        pubsub = red.pubsub()
        # subscribe to tweet_stream channel
        pubsub.subscribe('tweet_stream')
        # initiate server-sent events on messages pushed to channel
        for message in pubsub.listen():
            yield 'data: %s\n\n' % message['data']
    return Response(stream_with_context(event_stream()), mimetype="text/event-stream")



@app.route('/search', methods=['POST'])
def streamTweets():
			
	# Setting OAuth with Consumer key & Consumer secret key
	auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
	# Setting Access token keys
	auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
			
	api = tweepy.API(auth)
	tweet_term = request.form['search_term']
	myStreamListener = MyStreamListener()
	myStream = tweepy.Stream(auth, myStreamListener)
	tweets = myStream.filter(track=[tweet_term], async=True)
	
		
	
	return render_template('search.html', tweets=tweets)


	

# Check if user is logged in
def is_logged_in(f):
	@wraps(f)
	def wrap(*args, **kwargs):
		if 'logged_in' in session:
			return f(*args, **kwargs)
		else:
			flash('Unauthorized, Please login', 'danger')
			return redirect(url_for('login'))
	return wrap


@app.route('/logout')
@is_logged_in
def logout():
	session.clear()
	flash('You are now logged out', 'success')
	return redirect(url_for('login'))





@app.route('/account')
@is_logged_in
def account():
	return render_template('account.html')



if __name__ == '__main__':
	app.secret_key='secret123'
	app.run(debug=True)
