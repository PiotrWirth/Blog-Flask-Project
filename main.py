from flask import Flask, render_template, redirect, url_for, flash
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar
from flask import abort
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

gravatar = Gravatar(app, size=100, rating='g', default='retro', force_default=False, force_lower=False, use_ssl=False, base_url=None)



def admin_only_function(function):
    @wraps(function)
    def wrapper_function(*args, **kwargs):
        if current_user.id == 1:
            return function(*args, **kwargs)
        else:
            return abort(403)
    #wrapper_function.__name__ = function.__name__
    return wrapper_function

##CONFIGURE TABLES
class User(UserMixin,db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))
    posts = relationship("BlogPost", back_populates="author")
    comments = relationship("Comment", back_populates="comment_author")

class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    author = relationship("User", back_populates="posts")
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    comments = relationship("Comment", back_populates="parent_post")

class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    comment_author = relationship("User", back_populates="comments")
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    parent_post = relationship("BlogPost", back_populates="comments")

with app.app_context():
    db.create_all()

login_manager = LoginManager()
login_manager.init_app(app)

@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts,logged_in=current_user.is_authenticated)


@app.route('/register',methods=['GET','POST'])
def register():
    register_form = RegisterForm()
    if register_form.validate_on_submit():
        hashed_password = generate_password_hash(password=register_form.password.data,method='pbkdf2:sha256',salt_length=8)
        new_user = User(email=register_form.email.data,password=hashed_password,name=register_form.name.data)
        if db.session.query(User).filter_by(email=register_form.email.data).first():
            flash("This user already exists. Try to log in.")
            return redirect(url_for('login') )
        else:
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for('get_all_posts'))
    return render_template("register.html",form=register_form,logged_in=current_user.is_authenticated)


@app.route('/login',methods=['GET','POST'])
def login():
    login_form=LoginForm()
    if login_form.validate_on_submit():
        registered_user = db.session.query(User).filter_by(email=login_form.email.data).first()
        if registered_user:
            if check_password_hash(registered_user.password,login_form.password.data):
                login_user(registered_user)
                return redirect(url_for('get_all_posts'))
            else:
                flash('Invalid password')
                return redirect(url_for('login'))
        else:
                flash('Invalid email')
                return redirect(url_for('login'))
    return render_template("login.html",form=login_form, logged_in=current_user.is_authenticated)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>",methods=['GET','POST'])
def show_post(post_id):
    comment_form = CommentForm()
    requested_post = db.get_or_404(BlogPost, post_id)
    if comment_form.validate_on_submit():
        if current_user.is_authenticated:
            new_comment = Comment(
                body=comment_form.body.data,
                comment_author=current_user,
                parent_post=requested_post
            )
            db.session.add(new_comment)
            db.session.commit()
            return redirect(url_for("show_post", post_id=requested_post.id))
        else:
            flash("You need to login to leave a comment")
            return redirect(url_for("login"))
        
        
    return render_template("post.html", post=requested_post,logged_in=current_user.is_authenticated,form=comment_form)


@app.route("/about")
def about():
    return render_template("about.html",logged_in=current_user.is_authenticated)


@app.route("/contact")
def contact():
    return render_template("contact.html",logged_in=current_user.is_authenticated)


@app.route("/new-post",methods=['GET','POST'])
@login_required
@admin_only_function
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
    return render_template("make-post.html", form=form,logged_in=current_user.is_authenticated)


@app.route("/edit-post/<post_id>",methods=['GET','POST'])
@login_required
@admin_only_function
def edit_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    edit_form = CreatePostForm(title=post.title, subtitle=post.subtitle, img_url=post.img_url, body=post.body)
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for('show_post', post_id=post.id))
    return render_template('make-post.html',form=edit_form, is_edit=True,logged_in=current_user.is_authenticated)


@app.route("/delete/<int:post_id>")
@admin_only_function
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)

