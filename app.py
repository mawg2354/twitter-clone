from flask import Flask, render_template, redirect, url_for, flash, request
from models import db, User, Post, Comment, Notification
from dotenv import load_dotenv
import os
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from itsdangerous import URLSafeTimedSerializer as Serializer

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# File Upload Configuration
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_file(file, folder=''):
    if file and allowed_file(file.filename):
        from werkzeug.utils import secure_filename
        import uuid
        filename = secure_filename(file.filename)
        # Add unique ID to avoid collisions
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        path = os.path.join(app.config['UPLOAD_FOLDER'], folder, unique_filename)
        
        # Ensure subfolder exists
        subfolder_path = os.path.join(app.config['UPLOAD_FOLDER'], folder)
        if not os.path.exists(subfolder_path):
            os.makedirs(subfolder_path)
            
        file.save(path)
        return f"uploads/{folder}/{unique_filename}" if folder else f"uploads/{unique_filename}"
    return None

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        content = request.form.get('content')
        image_url = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                image_url = save_file(file, 'posts')
                
        if (content and len(content.strip()) > 0) or image_url:
            post = Post(content=content or "", user_id=current_user.id, image_url=image_url)
            db.session.add(post)
            db.session.commit()
            flash('Your tweet has been posted!', 'success')
        else:
            flash('Tweet cannot be empty!', 'error')
        return redirect(url_for('index'))
        
    posts = []
    if current_user.is_authenticated:
        # Get posts from followed users and self
        followed_ids = [u.id for u in current_user.followed]
        followed_ids.append(current_user.id)
        posts = Post.query.filter(Post.user_id.in_(followed_ids)).order_by(Post.created_at.desc()).all()
    return render_template('index.html', posts=posts)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        dob_str = request.form.get('dob')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return redirect(url_for('register'))
        
        # Check if user exists
        existing_user = User.query.filter_by(username=username).first()
        existing_email = User.query.filter_by(email=email).first()
        
        if existing_user or existing_email:
            flash('Username or email already exists.', 'error')
            return redirect(url_for('register'))
            
        from datetime import datetime
        dob = datetime.strptime(dob_str, '%Y-%m-%d').date() if dob_str else None
            
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(username=username, email=email, password_hash=hashed_password, date_of_birth=dob)
        db.session.add(user)
        db.session.commit()
        
        flash('Your account has been created! You can now log in.', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Login unsuccessful. Please check username and password.', 'error')
            
    return render_template('login.html')

@app.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            # Generate token
            s = Serializer(app.config['SECRET_KEY'])
            token = s.dumps({'user_id': user.id})
            # In a real app, send email. Here we just flash the link or print to console.
            reset_url = url_for('reset_token', token=token, _external=True)
            print(f"DEBUG: Password Reset Link: {reset_url}")
            flash('An email has been sent with instructions to reset your password.', 'info')
            return redirect(url_for('login'))
        else:
            flash('There is no account with that email. You must register first.', 'warning')
    return render_template('reset_request.html')

@app.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    s = Serializer(app.config['SECRET_KEY'])
    try:
        user_id = s.loads(token, max_age=1800)['user_id']
    except:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('reset_request'))
    
    user = User.query.get(user_id)
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('reset_token', token=token))
            
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return redirect(url_for('reset_token', token=token))
            
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        user.password_hash = hashed_password
        db.session.commit()
        flash('Your password has been updated! You are now able to log in', 'success')
        return redirect(url_for('login'))
        
    return render_template('reset_token.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/like/<int:post_id>', methods=['POST'])
@login_required
def like_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post in current_user.liked_posts:
        current_user.liked_posts.remove(post)
    else:
        current_user.liked_posts.append(post)
        if current_user.id != post.user_id:
            notification = Notification(type='like', sender_id=current_user.id, recipient_id=post.user_id, post_id=post.id)
            db.session.add(notification)
    db.session.commit()
    return redirect(request.referrer or url_for('index'))

@app.route('/post/<int:post_id>', methods=['GET', 'POST'])
@login_required
def post_detail(post_id):
    post = Post.query.get_or_404(post_id)
    if request.method == 'POST':
        content = request.form.get('content')
        if content:
            comment = Comment(content=content, user_id=current_user.id, post_id=post.id)
            db.session.add(comment)
            if current_user.id != post.user_id:
                notification = Notification(type='comment', sender_id=current_user.id, recipient_id=post.user_id, post_id=post.id)
                db.session.add(notification)
            db.session.commit()
            flash('Comment added!', 'success')
        return redirect(url_for('post_detail', post_id=post.id))
    return render_template('post.html', post=post)

@app.route('/user/<username>')
@login_required
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    posts = user.posts.order_by(Post.created_at.desc()).all()
    return render_template('profile.html', user=user, posts=posts)

@app.route('/edit_profile', methods=['POST'])
@login_required
def edit_profile():
    bio = request.form.get('bio')
    location = request.form.get('location')
    
    # Handle Profile Picture
    if 'profile_image' in request.files:
        file = request.files['profile_image']
        if file and file.filename != '':
            image_path = save_file(file, 'profiles')
            if image_path:
                current_user.profile_image = image_path
                
    # Handle Cover Image
    if 'cover_image' in request.files:
        file = request.files['cover_image']
        if file and file.filename != '':
            image_path = save_file(file, 'covers')
            if image_path:
                current_user.cover_image = image_path
    
    current_user.bio = bio
    current_user.location = location
    db.session.commit()
    flash('Your profile has been updated!', 'success')
    return redirect(url_for('profile', username=current_user.username))

@app.route('/follow/<username>', methods=['POST'])
@login_required
def follow(username):
    user = User.query.filter_by(username=username).first_or_404()
    if user == current_user:
        flash('You cannot follow yourself!', 'error')
        return redirect(url_for('profile', username=username))
    
    if user in current_user.followed:
        current_user.followed.remove(user)
    else:
        current_user.followed.append(user)
        notification = Notification(type='follow', sender_id=current_user.id, recipient_id=user.id)
        db.session.add(notification)
    db.session.commit()
    return redirect(url_for('profile', username=username))

@app.route('/search')
@login_required
def search():
    query = request.args.get('q', '')
    if not query:
        return redirect(url_for('index'))
    
    users = User.query.filter(User.username.ilike(f'%{query}%')).all()
    posts = Post.query.filter(Post.content.ilike(f'%{query}%')).all()
    
    return render_template('search.html', query=query, users=users, posts=posts)

@app.route('/notifications')
@login_required
def notifications():
    user_notifications = Notification.query.filter_by(recipient_id=current_user.id).order_by(Notification.created_at.desc()).all()
    
    # Mark as read
    unread = [n for n in user_notifications if not n.is_read]
    if unread:
        for n in unread:
            n.is_read = True
        db.session.commit()
        
    return render_template('notifications.html', notifications=user_notifications)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
