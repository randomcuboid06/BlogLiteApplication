# imports
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, LoginManager, login_user, logout_user, login_required, current_user
from sqlalchemy.sql import func
import os
from datetime import datetime

# setting up the app
app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///" + os.path.join(basedir, 'bloglitedb.db')
app.config['SECRET_KEY'] = 'very secret key'
db = SQLAlchemy()
db.init_app(app)
app.app_context().push()

# models

class Follow(db.Model):
    __tablename__ = 'follows'
    follower_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key = True)
    followed_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key = True)
    timestamp = db.Column(db.DateTime(timezone=True), default=func.now())

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True)
    username = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))
    date_created = db.Column(db.DateTime(timezone=True), default=func.now())
    posts = db.relationship('Posts',backref='users', passive_deletes=True)
    followed = db.relationship('Follow',foreign_keys=[Follow.follower_id],backref=db.backref('follower', lazy='joined'),lazy='dynamic',cascade='all, delete-orphan')
    followers = db.relationship('Follow',foreign_keys=[Follow.followed_id],backref=db.backref('followed', lazy='joined'),lazy='dynamic',cascade='all, delete-orphan')

class Posts(db.Model):
    __tablename__ = 'posts'
    post_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Text, nullable=False)
    text = db.Column(db.Text, nullable=False)
    image = db.Column(db.Text, nullable=False)
    date_created = db.Column(db.DateTime(timezone=True), default=func.now())
    author_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete="CASCADE"), nullable=False)

# routes
@app.route('/login',methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()
        if user:
            if user.password == password:
                flash('Logged in!', category='success')
                login_user(user, remember=True)
                return redirect(url_for('home'))
            else:
                flash('Password is incorrect!!', category='error')
        else:
            flash('No such user exists!!', category='error')
    return render_template('login.html', user=current_user)

@app.route('/')
@app.route('/home')
def home():
    posts_list = []
    try:
        if not current_user.followed.filter_by(followed_id=current_user.id).first():
            f_self = Follow(followed=current_user, follower=current_user)
            db.session.add(f_self)
            db.session.commit()
        posts_list = Posts.query.join(Follow, Follow.followed_id == Posts.author_id).filter(Follow.follower_id == current_user.id).all()
        return render_template('home.html', user=current_user, plist=posts_list)
    except:
        return render_template('home.html', user=current_user, plist=posts_list)

@app.route('/signup',methods=['GET','POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get("email")
        username = request.form.get("username")
        password = request.form.get("password") # name= "" in label 
        password1 = request.form.get("password1")

        email_exists = User.query.filter_by(email=email).first()
        username_exists = User.query.filter_by(username=username).first()
        if email_exists:
            flash('Email exists', category='error')
        elif username_exists:
            flash('Username already exists', category='error')
        elif password != password1:
            flash("Passwords don't match")
        else:
            new_user = User(username=username, email=email, password=password)
            db.session.add(new_user)
            db.session.commit()
            #print('User created')
            login_user(new_user, remember=True)
            return redirect(url_for('home'))
    return render_template('signup.html',user=current_user)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Successfully logged out !', category='success')
    return redirect(url_for('home'))

@app.route('/search', methods=['POST', 'GET'])
@login_required
def search():
    if request.method == 'POST':
        usrnm = request.form['username']
        search = '%{}%'.format(usrnm)
        usr_list = User.query.filter(User.username.like(search)).all()
        #print(usr_list)
        return render_template('search.html', user=current_user, user_list=usr_list)
    return render_template('search.html', user=current_user)

@app.route('/create_post', methods=['GET', 'POST'])
@login_required
def create_post():
    if request.method == 'POST':
        text = request.form.get('text', False)
        title = request.form.get('title', False)
        image = request.form.get('image', False)
        if not text:
            flash("Your message can't be empty", category='error')
        elif not title:
            flash("Your Title can't be empty !!", category='error')
        elif not image:
            flash("Your Image URL can't be empty !!", category='error')    
        else:
            post = Posts(text=text, author_id=current_user.id, title=title, image=image)
            flash('Post successfully created !!', category='success')
            db.session.add(post)
            db.session.commit()
            return redirect(url_for('home'))
    return render_template('create_post.html', user=current_user)

@app.route('/myprofile')
@login_required
def myprofile():
    user = User.query.filter_by(username=current_user.username).first()
    postlist = user.posts
    return render_template('profile.html', user=current_user, blog_list=postlist)

@app.route('/profile/<user_name>')
@login_required
def profile(user_name):
    user_for_posts = User.query.filter_by(username=user_name).first()
    posts = user_for_posts.posts
    return render_template('oprofile.html', user_name=user_name, user=current_user, posts=posts, profuser=user_for_posts)

@app.route('/delete_post/<post_id>', methods=['GET', 'POST'])
@login_required
def delete_post(post_id):
    if request.method == 'GET':
        return render_template('deleteconf.html', user=current_user)
    else:
        post = Posts.query.filter_by(post_id=post_id).first()
        db.session.delete(post)
        db.session.commit()
        flash('Post successfully deleted!!', category='success')
        return redirect(url_for('myprofile'))

@app.route('/edit_post/<post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    if request.method == 'GET':
        post = Posts.query.filter_by(post_id = post_id).first()
        return render_template('edit_post.html', user=current_user, post=post)
    if request.method == 'POST':
        post = Posts.query.filter_by(post_id = post_id).first()
        title = request.form.get('title', False)
        text = request.form.get('text', False)
        image = request.form.get('image', False)
        print('title type')
        if not title:
            flash("Title can't be empty", category='error')
            return render_template('edit_post.html', user=current_user, post=post)
        elif  not text:
            flash("Content can't be empty", category='error')
            return render_template('edit_post.html', user=current_user, post=post)
        elif not image:
            flash("Image URL can't be empty", category='error')
            return render_template('edit_post.html', user=current_user, post=post)
        else:
            post.title = title
            post.text = text
            post.image = image
            db.session.commit()
            flash('Post successfully updated !!', category='success')
            return redirect(url_for('myprofile'))

@app.route('/follow/<user_name>', methods=['GET', 'POST'])
@login_required
def follow(user_name):
    user = User.query.filter_by(username=user_name).first()
    currentuser_follows_user = current_user.followed.filter_by(followed_id=user.id).first()
    if currentuser_follows_user:
        flash('You already follow this user!', category='error')
        return render_template('oprofile.html', user_name=user.username, user=current_user, posts=user.posts, profuser=user)
    else:
        f = Follow(follower=current_user, followed=user)
        db.session.add(f)
        db.session.commit()
        flash('You are now following this user!', category='success')
        return render_template('oprofile.html', user_name=user.username, user=current_user, posts=user.posts, profuser=user)

@app.route('/unfollow/<user_name>', methods=['GET', 'POST'])
@login_required
def unfollow(user_name):
    user = User.query.filter_by(username=user_name).first()
    cu_follows_u = current_user.followed.filter_by(followed_id=user.id).first()
    if cu_follows_u:
        db.session.delete(cu_follows_u)
        db.session.commit()
        flash('You have unfollowed this user', category='success')
        return render_template('oprofile.html', user_name=user.username, user=current_user, posts=user.posts, profuser=user)
    else:
        flash("You don't follow this user!", category='error')
        return render_template('oprofile.html', user_name=user.username, user=current_user, posts=user.posts, profuser=user)

@app.route('/followers/<user_name>', methods=['GET', 'POST'])
@login_required
def followers(user_name):
    user = User.query.filter_by(username=user_name).first()
    followers_list = user.followers.all()
    followers_list = [f.follower_id for f in followers_list]
    followers = [(id, User.query.filter_by(id=id).first().username) for id in followers_list]
    return render_template('followers.html', user=user, followers=followers)

@app.route('/following/<user_name>', methods=['GET', 'POST'])
@login_required
def following(user_name):
    user = User.query.filter_by(username=user_name).first()
    following_list = user.followed.all()
    following_list = [f.followed_id for f in following_list]
    following = [(id, User.query.filter_by(id=id).first().username) for id in following_list]
    return render_template('following.html', user=user, following=following)

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

# starting the app
if __name__ == '__main__':
    db.create_all()
    app.run( debug = True )
    
    