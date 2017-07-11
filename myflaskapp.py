from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
from data import Articles
import pymysql.cursors
# from flask_pymongo import PyMongo
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps

app = Flask(__name__)

# CONFIG MYSQL
connection = pymysql.connect(host='hostname',
                             user='username',
                             password='password',
                             db='databasename',
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor)

Articles = Articles()


# index


@app.route('/')
def index():
    return render_template('index.html')


# about


@app.route('/about')
def about():
    return render_template('about.html')


# articles


@app.route('/articles')
def articles():
    # create cursor
    with connection.cursor() as cursor:
        result = cursor.execute("SELECT * FROM articles")
        articles = cursor.fetchall()
        if result > 0:
            render_template('articles.html', articles=articles)
        else:
            msg = 'no articles found'
            return render_template('articles.html', msg=msg)
        cursor.close()
    return render_template('articles.html', articles=articles)


# single article


@app.route('/article/<string:id>/')
def article(id):
    with connection.cursor() as cursor:
        result = cursor.execute("SELECT * FROM articles WHERE id = %s", [id])

        article = cursor.fetchone()

    return render_template('article.html', article=article)


# user register


class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min=1, max=50)])
    username = StringField('Username', [validators.Length(min=4, max=25)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match')
    ])
    confirm = PasswordField('Confirm Password')


# register


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

        # create cursor
        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO users(name, email, username, password) VALUES(%s, "
                           "%s, %s, %s)", (name, email, username, password))

        # commit to dB
        connection.commit()
        # close the connection
        cursor.close()

        flash('You are now registered and can log in', 'success')

        redirect(url_for('index'))
    return render_template('register.html', form=form)


# login


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password_candidate = request.form['password']

        # create cursor
        with connection.cursor() as cursor:
            # Read a single record
            sql = "SELECT * FROM `users` WHERE `username`=%s"
            result = cursor.execute(sql, [username])
            if result > 0:
                # Get stored hash
                data = cursor.fetchone()
                password = data['password']

                # Compare Passwords
                if sha256_crypt.verify(password_candidate, password):
                    # Passed
                    session['logged_in'] = True
                    session['username'] = username

                    flash('You are now logged in', 'success')
                    return redirect(url_for('dashboard'))
                else:
                    error = 'Invalid login'
                    return render_template('login.html', error=error)
                # Close connection
                cursor.close()
            else:
                error = 'Username not found'
                return render_template('login.html', error=error)

    return render_template('login.html')


# check if login


def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login', 'danger')
            return redirect(url_for('login'))

    return wrap


# log out


@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are logged out', 'success')
    return redirect(url_for('login'))


# dashboard


@app.route('/dashboard')
@is_logged_in
def dashboard():
    # create cursor
    with connection.cursor() as cursor:
        result = cursor.execute("SELECT * FROM articles")
        articles = cursor.fetchall()
        if result > 0:
            render_template('dashboard.html', articles=articles)
        else:
            msg = 'no articles found'
            return render_template('dashboard.html', msg=msg)
        cursor.close()
    return render_template('dashboard.html', articles=articles)


# add article

class ArticleForm(Form):
    title = StringField('Title', [validators.Length(min=1, max=225)])
    body = TextAreaField('body', [validators.Length(min=30)])


# add article route


@app.route('/add_article', methods=['GET', 'POST'])
@is_logged_in
def add_article():
    form = ArticleForm(request.form)
    if request.method == 'POST' and form.validate():
        title = form.title.data
        body = form.body.data

        # Create Cursor
        with connection.cursor() as cursor:
            # Execute
            cursor.execute("INSERT INTO articles(title, body, author) VALUES(%s, %s, %s)",
                           (title, body, session['username']))

            # Commit to DB
            connection.commit()

            # Close connection
            cursor.close()

            flash('Article Created', 'success')

            return redirect(url_for('dashboard'))

    return render_template('add_article.html', form=form)

# edit article


@app.route('/edit_article/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_article(id):
    # create cursor
    with connection.cursor() as cursor:
        # get user by id
        result = cursor.execute("SELECT * FROM articles WHERE id = %s", [id])

        article = cursor.fetchone()

        cursor.close()
        form = ArticleForm(request.form)

        # popular editor form fields
        form.title.data = article['title']
        form.body.data = article['body']

        if request.method == 'POST' and form.validate():
            title = request.form['title']
            body = request.form['body']

            # Create Cursor
            with connection.cursor() as cursor:
                # Execute
                cursor.execute("UPDATE articles SET title=%s, body=%s WHERE id=%s",
                               (title, body, id))

                # Commit to DB
                connection.commit()

                # Close connection
                cursor.close()

                flash('Article Updated', 'success')

                return redirect(url_for('dashboard'))

        return render_template('edit_article.html', form=form)

# delete article


@app.route('/delete_article/<string:id>', methods=['POST'])
@is_logged_in
def delete_article(id):
    with connection.cursor() as cursor:
        result = cursor.execute("DELETE FROM articles where id=%s", [id])
        connection.commit()
        cursor.close()
        flash("Article deleted", "SUCCESS")
    return redirect(url_for('dashboard'))


if __name__ == '__main__':
    app.secret_key = 'secret123'
    app.run(debug=True)
