from flask import Flask
from markupsafe import escape
from flask import render_template, redirect, url_for, request, flash
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from flask_bcrypt import Bcrypt, generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_ckeditor import CKEditor
from datetime import datetime
from form import PostForm, LoginForm
import requests
import bleach
# migrating database
from flask_migrate import Migrate
# production settings
from config import ProductionConfig, DevelopmentConfig
from dotenv import load_dotenv
import os


# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Load configuration based on the environment
if os.environ.get('FLASK_ENV') == 'production':
    app.config.from_object(ProductionConfig)
else:
    app.config.from_object(DevelopmentConfig)


flask_bcrypt = Bcrypt(app)
app.secret_key =os.environ.get('SECRET_KEY')
login_manager = LoginManager()
login_manager.init_app(app)

# ckeditor
ckeditor = CKEditor(app)

# database congiguration
app.config['SQLALCHEMY_DATABASE_URI']=  os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)

print("SECRET_KEY:", os.environ.get('SECRET_KEY'))
print("DATABASE_URI:", os.environ.get('DATABASE_URL'))

# models for users
class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(250), unique=False, nullable=False)
    email= db.Column(db.String(200),  unique=False, nullable=False)
    password=db.Column(db.String(250), unique=False, nullable=False)
    posts = db.relationship('Posts', backref='author', lazy=True)


# models
class Posts(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(150), unique=False, nullable=False)
    subtitle = db.Column(db.String(250), unique=False, nullable=False)
    image_url = db.Column(db.String(250), unique=False, nullable=False)
    blog_content= db.Column(db.Text(10000), unique=False, nullable=False)
    # author = db.Column(db.String(250), unique=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)




with app.app_context():
    db.create_all()


# fetch user
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# route to register new users
@app.route('/register', methods =['POST', 'GET'])
def register():
    form = LoginForm()
    
    if form.validate_on_submit():
        
        # checking if user already exits withat email
        if User.query.filter_by(email=request.form.get('email')).first():
            #User already exists
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login_page'))
        
        # hashing users password
        password = form.password.data
        hashed_password = flask_bcrypt.generate_password_hash(password)

        new_user =User(name = form.name.data,
                   email = form.email.data,
                   password = hashed_password)
        
        # saving new user to db
        db.session.add(new_user)
        db.session.commit()
        # Log in the user after successful registration
        login_user(new_user)
        flash('Your account has been created! You can now log in.', 'success')
        return redirect(url_for('home_page'))
    return render_template('signup.html', form= form)


# login
@app.route('/login', methods=['GET', 'POST'])
def login_page():
    form = LoginForm()
    if request.method =='POST':
        email =form.email.data.strip() #.strip() to remove trailing whitespace in email
        password = form.password.data

        #Find user by email entered.
        user = User.query.filter_by(email=email).first()

        if user:
        #Check stored hash password against entered password hashed.
            if flask_bcrypt.check_password_hash(user.password, password):
                login_user(user)
                return redirect(url_for('home_page'))
            elif email !=user.email:
                flash('The email you have entered does not exist in our database', 'danger')
                return redirect(url_for('login_page'))
            else:
                # Invalid email or password
                flash('Invalid  password. Please try again.', 'danger')
                return redirect(url_for('login_page'))
        else:
            print("User not found.")
            flash('invalid email.', 'danger')
            return redirect(url_for('login_page'))
        
    return render_template('login.html', form=form)


# logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    # flash('You have been logged out.', 'success')
    return redirect(url_for('home_page'))



# route to create new post
@app.route('/create', methods =['GET', 'POST'])
@login_required
def create_post():
    form = PostForm()
    if form.validate_on_submit():
        
        # using bleach to strip HTML tags from the content
        plain_text = bleach.clean(form.content.data, tags=[], strip=True)
        if current_user.is_authenticated:
            blog = Posts(user_id =current_user.id, 
                        title = form.title.data,
                        subtitle =form.subtitle.data, 
                        image_url = form.image.data,
                        blog_content =plain_text,)
            db.session.add(blog)
            db.session.commit()
            return redirect(url_for('home_page'))
    return render_template('create_post.html', form= form)


#home route 
@app.route('/')
def home_page():
    all_post = Posts.query.all()
    current_year = datetime.now()
    current_year =current_year.strftime("%B %d, %Y")
    return render_template('index.html', posts =all_post, year= current_year)


# route to display image and content of post
@app.route('/full_post/<int:post_id>', methods =['GET', 'POST'])
@login_required
def full_post(post_id):
    if current_user.is_authenticated:
        post =db.session.query(Posts).filter(Posts.id == post_id).first()
        
    else:
        return redirect(url_for('login_page'))
    return render_template('content_img.html', posts =post)


# about page
@app.route('/about')
@login_required
def about_page():
    current_year = datetime.now()
    current_year =current_year.strftime("%B %d, %Y")
    return render_template('about.html', year= current_year)


# contact page
@app.route('/contact')
@login_required
def contact_page():
    current_year = datetime.now().year
    return render_template('contact.html', year=current_year)


# Edit post
@app.route('/edit<int:id>', methods=['GET', 'POST'])
@login_required
def edit_post(id):
    # movie_id = request.args.get('id')
    post = Posts.query.get(id)
    form= PostForm(obj=post) # the obj= movies makes sures that the form is prepopulated with the data before editing
    
    # Check if the current user is the author of the post
    if post.author != current_user:
        flash('You are not authorized to update this post.', 'danger')
        return redirect(url_for('home_page'))
    
    if form.validate_on_submit():
        
        post.title = form.title.data
        post.subtitle = form.subtitle.data
        post.image_url = form.image.data
        post.blog_content =form.content.data
        db.session.commit()
        return redirect(url_for('home_page'))
    return render_template('edit_post.html', form= form, post=post)


# delete route
@app.route('/delete/<int:post_id>', methods=['GET', 'POST'])
@login_required
def delete_post(post_id):
    # Fetch the post from the database
    post = Posts.query.get_or_404(post_id)

   # Check if the current user is the author of the post
    if post.author != current_user:
        # flash('You are not authorized to delete this post.', 'danger')
        return redirect(url_for('home_page'))
     
    if request.method == 'POST':
        db.session.delete(post)
        db.session.commit()

        # Flash a success message
        flash('Post deleted successfully!', 'success')
        return redirect(url_for('home_page'))

    return render_template('confirm_delete.html', post=post)

