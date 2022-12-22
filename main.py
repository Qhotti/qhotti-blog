from flask import Flask, render_template, redirect, url_for, flash,abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm,RegisterForm,LoginForm,CommentForm
from flask_gravatar import Gravatar
from functools import wraps
import sys
import logging

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

app.logger.addHandler(logging.StreamHandler(sys.stdout))
app.logger.setLevel(logging.ERROR)



##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)

##CONFIGURE TABLES

class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.String(250), nullable=False)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(100))
    
    

class Comment(UserMixin, db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(250), unique=True)


# with app.app_context():
    # db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# admin decorator 
def admin_only(function):
    @wraps(function)
    def wrapper_function(*args, **kwargs):
        if current_user.id == 1:
            return function(*args, **kwargs)
        else:
            return abort(403)
    return wrapper_function


# shows all posts
@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts, logged_in=current_user.is_authenticated)

# allows registration
@app.route('/register',methods=['POST','GET'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        
        if User.query.filter_by(email=form.email.data).first():
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login'))
        else:
            new_user = User(
                email=form.email.data,
                name=form.name.data,
                password=generate_password_hash(form.password.data, method='pbkdf2:sha256', salt_length=8))
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for('get_all_posts'))
    return render_template("register.html",form=form, logged_in=current_user.is_authenticated)



# allows user to login
@app.route('/login',methods=['POST','GET'])
def login():
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user == None:
            flash("Email does not exist. Try registering.")
            return redirect(url_for('login'))
        elif check_password_hash(user.password, form.password.data) == False:
            flash("Password incorrect.")
            return redirect(url_for('login'))
        else:
            email = form.email.data
            password = form.password.data
            user = User.query.filter_by(email=email).first()
            if check_password_hash(user.password, password):
                login_user(user)
                return redirect(url_for('get_all_posts'))
    
    return render_template("login.html",form=form, logged_in=current_user.is_authenticated)

# allows user to logout
@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))



# shows post that user clicked
@app.route("/post/<int:post_id>",methods=['POST','GET'])
def show_post(post_id):
    form=CommentForm()
    requested_post = BlogPost.query.get(post_id)
    comments = Comment.query.all()
    if form.validate_on_submit():
        new_comment = Comment(
            text=form.comment.data)
        
        db.session.add(new_comment)
        db.session.commit()
    return render_template("post.html", post=requested_post, logged_in=current_user.is_authenticated,form=form,all_comments=comments)

# about page
@app.route("/about")
def about():
    return render_template("about.html", logged_in=current_user.is_authenticated)

# contact page
@app.route("/contact")
def contact():
    return render_template("contact.html", logged_in=current_user.is_authenticated)



# adds a new post
@app.route("/new-post",methods=['POST','GET'])
@login_required
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form, logged_in=current_user.is_authenticated)



# allows admin to edit post
@app.route("/edit-post/<int:post_id>",methods=['POST','GET'])
@login_required
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form, logged_in=current_user.is_authenticated)



# allows admin to delete a post
@app.route("/delete/<int:post_id>")
@login_required
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(debug=True)
