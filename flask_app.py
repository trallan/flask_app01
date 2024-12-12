from flask import Flask, render_template, redirect, url_for, request, session, flash, abort
from flask_socketio import SocketIO, emit
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import requests
import json
import secrets
from functools import wraps


app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
socketio = SocketIO(app, cors_allowed_origins="*")



def create_database():
	conn = sqlite3.connect('person.db')
	c = conn.cursor()
	c.execute('''CREATE TABLE IF NOT EXISTS persons (id INTEGER PRIMARY KEY, person TEXT)''')
	c.execute('''CREATE TABLE IF NOT EXISTS books (id INTEGER PRIMARY KEY,
		title TEXT,
		author TEXT,
		description TEXT,
		pages INTEGER,
		year INTEGER,
		rating REAL) ''')
	c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT) ''')
	c.execute('''CREATE TABLE IF NOT EXISTS blogpost (id INTEGER PRIMARY KEY, header TEXT, date DATETIME DEFAULT CURRENT_TIMESTAMP, textfield TEXT )''')
	conn.commit()
	conn.close()


create_database()


def login_required(f):
	@wraps(f)
	def decorated_function(*args, **kwargs):
		if 'user_id' not in session:
			flash('Please log in to access this page.', 'warning')
			return redirect(url_for('login'))
		return f(*args, **kwargs)
	return decorated_function


def role_required(required_role):
	def decorator(f):
		@wraps(f)
		def decorated_function(*args, **kwargs):
			if 'role' not in session or session['role'] != required_role:
				abort(403)
			return f(*args, **kwargs)
		return decorated_function
	return decorator

def get_meme():
	url = "https://meme-api.com/gimme"
	response = json.loads(requests.request("GET", url).text)
	meme_large = response["preview"][-2]
	#subreddit = response["subreddit"]
	return meme_large



@app.route('/')
@login_required
def index():
	conn = sqlite3.connect('person.db')
	c = conn.cursor()
	c.execute('SELECT * FROM persons')
	persons = c.fetchall()
	conn.close()
	return render_template('index.html', persons=persons)


@app.route('/login', methods=['GET', 'POST'])
def login():
	if request.method == 'POST':
		username = request.form['username']
		password = request.form['password']
		conn = sqlite3.connect('person.db')
		c = conn.cursor()
		c.execute("SELECT * FROM users WHERE username = ?", (username,))
		user = c.fetchone()
		conn.close()
		if user and check_password_hash(user[2], password):
			session['user_id'] = user[0]
			session['username'] = user[1]
			session['role'] = user[3]
			flash('Logged in successfully!', 'success')
			return redirect(url_for('index'))
		else:
			flash('Invalid username or password', 'danger')
			return render_template('login.html')

	return render_template('login.html')


@app.route('/logout')
def logout():
	session.clear()
	flash('You have been logged out.', 'info')
	return redirect(url_for('login'))


@app.route('/add', methods=['POST'])
@role_required('admin')
def add_person():
	person = request.form['person']
	if not person:
		return "Person name is required", 400
	if len(person) > 50:
		return "Person name cannot exceed 50 characters", 400
	conn = sqlite3.connect('person.db')
	c = conn.cursor()
	c.execute('INSERT INTO persons (person) VALUES (?)', (person,))
	conn.commit()
	conn.close()
	return redirect(url_for('index'))


@app.route('/delete/<int:person_id>' )
@role_required('admin')
def delete_person(person_id):
	conn = sqlite3.connect('person.db')
	c = conn.cursor()
	c.execute('DELETE FROM persons WHERE id = ?', (person_id,))
	conn.commit()
	conn.close()
	return redirect(url_for('index'))


@app.route('/update/<int:person_id>', methods=['GET'])
@role_required('admin')
def update_person_form(person_id):
        conn = sqlite3.connect('person.db')
        c = conn.cursor()
        c.execute('SELECT * FROM persons WHERE id = ?', (person_id,))
        person = c.fetchone()
        conn.close()

        if person:
                return render_template('update.html', person=person)
        else:
                return "Person not found", 404

@app.route('/update/<int:person_id>', methods=['POST'])
@role_required('admin')
def update_person(person_id):
        person_name = request.form['name']
        if not person_name:
                return "Person name is required", 400
        if len(person_name) > 50:
                return "Person name cannot exceed 50 characters", 400
        conn = sqlite3.connect('person.db')
        c = conn.cursor()
        c.execute('UPDATE persons SET person = ? WHERE id = ?', (person_name, person_id,))
        conn.commit()
        conn.close()

        return redirect(url_for('index'))


@app.route('/memes')
@login_required
def memes():
	meme_pic = get_meme()
	return render_template("meme_index.html", meme_pic=meme_pic)


@app.route('/addbook', methods=['POST'])
@role_required('admin')
def add_book():
	book_title = request.form['book_title']
	book_author = request.form['book_author']
	book_desc = request.form['book_desc']
	try:
		book_pages = int(request.form['book_pages'])
		book_year = int(request.form['book_year'])
		book_rating = int(request.form['book_rating'])
	except ValueError:
		return "Invalid input for pages, year, or rating.", 400
	conn = sqlite3.connect('person.db')
	c = conn.cursor()
	c.execute('INSERT INTO books (title, author, description, pages, year, rating) VALUES (?, ?, ?, ?, ?, ?)', (book_title, book_author, book_desc, book_pages, book_year, book_rating))
	conn.commit()
	conn.close()

	return redirect(url_for('book_list'))


@app.route('/books')
@login_required
def book_list():
	conn = sqlite3.connect('person.db')
	c = conn.cursor()
	c.execute("SELECT * FROM books")
	books = c.fetchall()
	conn.close()
	return render_template("books_index.html", books=books)


@app.route('/blog')
def blog_post():
	conn = sqlite3.connect('person.db')
	c = conn.cursor()
	c.execute('SELECT id, header, date, textfield FROM blogpost')
	blogposts = c.fetchall()
	conn.close()
	
	processed_blogposts = [
		{
			"id": post[0],
			"header":post[1],
			"date": post[2],
			"excerpt": post[3][:250],
			"full_text": post[3]
		}
		for post in blogposts
	]
	return render_template("blog.html", blogposts=processed_blogposts, role=session.get('role'))


@app.route('/createpost', methods=['GET', 'POST'])
@role_required('admin')
def add_post():
	if request.method == 'POST':
		header = request.form['post-header']
		textarea = request.form['post-textarea']
		if not header:
			return "Header is required", 400
		if not textarea:
			return "Textarea is required", 400
		conn = sqlite3.connect('person.db')
		c = conn.cursor()
		c.execute('INSERT INTO blogpost (header, textfield) VALUES (?, ?)', (header, textarea,))
		conn.commit()
		conn.close()
		return redirect(url_for("blog_post"))


	return render_template("create_post.html")


@app.route('/deletepost/<int:post_id>' )
@role_required('admin')
def delete_post(post_id):
        conn = sqlite3.connect('person.db')
        c = conn.cursor()
        c.execute('DELETE FROM blogpost WHERE id = ?', (post_id,))
        conn.commit()
        conn.close()
        return redirect(url_for('blog_post'))


@app.route('/editpost/<int:post_id>', methods=['GET', 'POST'])
@role_required('admin')
def edit_post(post_id):
    conn = sqlite3.connect('person.db')
    c = conn.cursor()

    if request.method == 'POST':
        # Update the post in the database
        header = request.form['post-header']
        textarea = request.form['post-textarea']
        if not header or not textarea:
            return "Header and Textarea are required", 400
        c.execute('UPDATE blogpost SET header = ?, textfield = ? WHERE id = ?', (header, textarea, post_id))
        conn.commit()
        conn.close()
        return redirect(url_for('blog_post'))

    # Fetch the current post data to pre-fill the form
    c.execute('SELECT header, textfield FROM blogpost WHERE id = ?', (post_id,))
    post = c.fetchone()
    conn.close()
    if not post:
        return "Post not found", 404
    return render_template('update_post.html', post_id=post_id, header=post[0], textfield=post[1])




if __name__ == '__main__':
	app.run(debug=True)
