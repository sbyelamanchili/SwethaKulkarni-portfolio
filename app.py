from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from PIL import Image
import os
import logging
import json
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Configure app
app.config.update(
    SECRET_KEY='your-secret-key-here',  # Change this in production!
    SQLALCHEMY_DATABASE_URI='sqlite:///portfolio.db',
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB max file size
    WTF_CSRF_ENABLED=True,
    WTF_CSRF_TIME_LIMIT=None  # No time limit for CSRF tokens
)

# Configure upload folder
UPLOAD_FOLDER = os.path.join(app.static_folder, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Configure allowed extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Initialize extensions
db = SQLAlchemy(app)
csrf = CSRFProtect(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'error'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# User Model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def create_admin_user():
    try:
        user = User.query.filter_by(username='admin').first()
        if not user:
            user = User(username='admin')
            user.set_password('admin123')  # Change this in production!
            db.session.add(user)
            db.session.commit()
            logger.info("Admin user created successfully")
        else:
            logger.info("Admin user already exists")
    except Exception as e:
        logger.error(f"Error creating admin user: {str(e)}")
        db.session.rollback()

@app.route('/')
def index():
    # Get all images from the uploads folder
    images = []
    try:
        logger.info(f"Upload folder path: {app.config['UPLOAD_FOLDER']}")
        if os.path.exists(app.config['UPLOAD_FOLDER']):
            for filename in os.listdir(app.config['UPLOAD_FOLDER']):
                if allowed_file(filename):
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    if os.path.isfile(file_path):
                        image_url = url_for('static', filename=f'uploads/{filename}')
                        logger.info(f"Adding image: {filename} with URL: {image_url}")
                        images.append({
                            'filename': filename,
                            'url': image_url
                        })
                    else:
                        logger.warning(f"File not found: {file_path}")
                else:
                    logger.warning(f"Skipping non-allowed file: {filename}")
        else:
            logger.warning(f"Upload folder does not exist: {app.config['UPLOAD_FOLDER']}")
        
        logger.info(f"Total images to display: {len(images)}")
        return render_template('index.html', images=images)
    except Exception as e:
        logger.error(f"Error loading images: {str(e)}")
        return render_template('index.html', images=[])

@app.route('/login', methods=['GET', 'POST'])
def login():
    logger.info(f"Login request received. Method: {request.method}")
    try:
        # If user is already authenticated, redirect to admin
        if current_user.is_authenticated:
            logger.info("User is already authenticated, redirecting to admin")
            return redirect(url_for('admin'))

        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            
            logger.info(f"Login attempt - Username provided: {bool(username)}, Password provided: {bool(password)}")
            
            if not username or not password:
                logger.warning("Missing username or password")
                flash('Please provide both username and password', 'error')
                return render_template('login.html')
            
            logger.debug(f"Login attempt for username: {username}")
            user = User.query.filter_by(username=username).first()
            
            if user and user.check_password(password):
                login_user(user, remember=True)
                logger.info(f"User {username} logged in successfully")
                flash('Logged in successfully!', 'success')
                
                # Get the next page from args or default to admin
                next_page = request.args.get('next')
                if not next_page or urlparse(next_page).netloc != '':
                    next_page = url_for('admin')
                
                logger.info(f"Redirecting to: {next_page}")
                return redirect(next_page)
            
            logger.warning(f"Failed login attempt for username: {username}")
            flash('Invalid username or password', 'error')
        
        logger.info("Rendering login template")
        return render_template('login.html')
    except Exception as e:
        logger.error(f"Error in login route: {str(e)}", exc_info=True)
        flash('An error occurred. Please try again.')
        return render_template('login.html')

@app.route('/admin')
@login_required
def admin():
    try:
        logger.info(f"Admin route accessed by user: {current_user.username}")
        
        # Get all images
        images = []
        upload_folder = app.config['UPLOAD_FOLDER']
        logger.info(f"Admin route - Checking upload folder: {upload_folder}")
        
        if os.path.exists(upload_folder):
            files = sorted(os.listdir(upload_folder))
            logger.info(f"Admin route - Found {len(files)} files in upload folder")
            
            for filename in files:
                if allowed_file(filename):
                    file_path = os.path.join(upload_folder, filename)
                    if os.path.isfile(file_path):
                        image_url = url_for('static', filename=f'uploads/{filename}')
                        logger.debug(f"Admin route - Processing image: {filename}")
                        logger.debug(f"Admin route - Generated URL: {image_url}")
                        images.append({
                            'filename': filename,
                            'url': image_url
                        })
                    else:
                        logger.warning(f"Admin route - File not found: {file_path}")
                else:
                    logger.warning(f"Admin route - Skipping non-allowed file: {filename}")
        else:
            logger.warning(f"Admin route - Upload folder does not exist: {upload_folder}")
            os.makedirs(upload_folder, exist_ok=True)
            logger.info(f"Admin route - Created upload folder: {upload_folder}")
        
        logger.info(f"Admin route - Total images to display: {len(images)}")
        return render_template('admin.html', 
                             images=images,
                             username=current_user.username)
    except Exception as e:
        logger.error(f"Error in admin route: {str(e)}", exc_info=True)
        flash('An error occurred while loading the admin page.', 'error')
        return render_template('error.html', error=str(e)), 500

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/delete-image', methods=['POST'])
@login_required
def delete_image():
    try:
        data = request.get_json()
        if not data or 'filename' not in data:
            return jsonify({'success': False, 'message': 'No filename provided'}), 400

        filename = data['filename']
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        logger.info(f"Attempting to delete image: {filename}")
        logger.info(f"Full file path: {file_path}")
        
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Successfully deleted image: {filename}")
            return jsonify({'success': True, 'message': 'Image deleted successfully'})
        else:
            logger.warning(f"File not found for deletion: {file_path}")
            return jsonify({'success': False, 'message': 'File not found'}), 404
            
    except Exception as e:
        logger.error(f"Error deleting image: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    if 'images' not in request.files:
        return jsonify({'error': 'No files uploaded'}), 400
    
    files = request.files.getlist('images')
    if not files or all(file.filename == '' for file in files):
        return jsonify({'error': 'No files selected'}), 400

    uploaded_files = []
    errors = []
    
    for file in files:
        if file.filename == '':
            continue
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            try:
                # Save and optimize image
                img = Image.open(file)
                img.thumbnail((1920, 1920))  # Max dimension 1920px
                img.save(filepath, optimize=True, quality=85)
                uploaded_files.append(filename)
            except Exception as e:
                errors.append(f"Error processing {filename}: {str(e)}")
        else:
            errors.append(f"Invalid file type: {file.filename}")
    
    if not uploaded_files and errors:
        return jsonify({'success': False, 'error': 'Upload failed', 'errors': errors}), 400
    
    return jsonify({
        'success': True,
        'uploaded_files': uploaded_files,
        'errors': errors if errors else None
    })

@app.route('/gallery')
def get_gallery():
    images = []
    try:
        logger.info("Loading gallery images...")
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            logger.warning(f"Upload folder does not exist: {app.config['UPLOAD_FOLDER']}")
            return jsonify([])

        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            if allowed_file(filename):
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                if os.path.isfile(file_path):
                    image_url = f'/static/uploads/{filename}'
                    logger.info(f"Adding image: {filename} with URL: {image_url}")
                    images.append({
                        'filename': filename,
                        'url': image_url
                    })
                else:
                    logger.warning(f"File not found: {file_path}")
        
        logger.info(f"Found {len(images)} images: {json.dumps(images)}")
        return jsonify(images)
    except Exception as e:
        logger.error(f"Error loading gallery: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/contact', methods=['POST'])
def contact():
    data = request.json
    # Here you would typically send an email or store the contact form data
    return jsonify({'success': True, 'message': 'Message sent successfully'})

@app.route('/rotate-image', methods=['POST'])
@login_required
def rotate_image():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
            
        filename = data.get('filename')
        degrees = data.get('degrees')
        
        if not filename or degrees is None:
            return jsonify({'success': False, 'message': 'Missing filename or degrees'}), 400

        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(file_path):
            return jsonify({'success': False, 'message': 'Image not found'}), 404

        try:
            with Image.open(file_path) as img:
                # Rotate the image
                rotated_img = img.rotate(-degrees, expand=True)  # Negative degrees for clockwise rotation
                # Save the rotated image, overwriting the original
                rotated_img.save(file_path, quality=95, optimize=True)
                
            return jsonify({
                'success': True,
                'message': 'Image rotated successfully',
                'url': url_for('static', filename=f'uploads/{filename}')
            })
            
        except Exception as e:
            logger.error(f"Error rotating image: {str(e)}")
            return jsonify({'success': False, 'message': 'Failed to rotate image'}), 500
            
    except Exception as e:
        logger.error(f"Error in rotate_image route: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/debug-login')
def debug_login():
    try:
        logger.info("Debug: Attempting to render login template")
        return render_template('login.html')
    except Exception as e:
        logger.error(f"Debug: Error rendering login template: {str(e)}", exc_info=True)
        return f"Error: {str(e)}", 500

@app.route('/debug-templates')
def debug_templates():
    try:
        template_list = app.jinja_loader.list_templates()
        return jsonify({
            'templates': list(template_list),
            'template_folder': app.template_folder
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/debug-db')
def debug_db():
    try:
        user_count = User.query.count()
        admin_user = User.query.filter_by(username='admin').first()
        return jsonify({
            'database_uri': app.config['SQLALCHEMY_DATABASE_URI'],
            'user_count': user_count,
            'admin_exists': admin_user is not None
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get-images')
@login_required
def get_images():
    try:
        images = []
        if os.path.exists(app.config['UPLOAD_FOLDER']):
            for filename in os.listdir(app.config['UPLOAD_FOLDER']):
                if allowed_file(filename):
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    if os.path.isfile(file_path):
                        images.append({
                            'filename': filename,
                            'url': f'/static/uploads/{filename}'
                        })
        logger.info(f"Found {len(images)} images in the uploads folder")
        return jsonify({'images': images, 'success': True})
    except Exception as e:
        logger.error(f"Error loading images: {str(e)}")
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/test-static')
def test_static():
    try:
        # Test if we can list files in the uploads directory
        upload_path = app.config['UPLOAD_FOLDER']
        if os.path.exists(upload_path):
            files = os.listdir(upload_path)
            urls = [url_for('static', filename=f'uploads/{f}') for f in files if allowed_file(f)]
            return jsonify({
                'status': 'success',
                'upload_path': upload_path,
                'files': files,
                'urls': urls
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f'Upload path does not exist: {upload_path}'
            })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.before_request
def log_request_info():
    logger.info(f"Request URL: {request.url}")
    logger.info(f"Request Headers: {dict(request.headers)}")
    logger.info(f"Request Method: {request.method}")

@app.after_request
def add_header(response):
    try:
        logger.info(f"Response Status: {response.status_code}")
        logger.info(f"Response Headers: {dict(response.headers)}")
        
        # Add MIME types for images
        if response.headers.get('Content-Type', '').startswith('image/'):
            logger.info("Setting cache headers for image response")
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '-1'
        return response
    except Exception as e:
        logger.error(f"Error in add_header: {str(e)}", exc_info=True)
        raise

@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', error='Page not found'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('error.html', error='Internal server error'), 500

@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
    db.session.rollback()
    return render_template('error.html', error='An unexpected error occurred'), 500

@app.route('/health-check')
def health_check():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    # Create error.html template if it doesn't exist
    error_template_path = os.path.join(app.template_folder, 'error.html')
    if not os.path.exists(error_template_path):
        with open(error_template_path, 'w') as f:
            f.write('''
<!DOCTYPE html>
<html>
<head>
    <title>Error</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
</head>
<body>
    <div class="error-container">
        <h1>Error</h1>
        <p>{{ error }}</p>
        <a href="{{ url_for('index') }}" class="btn">Return to Home</a>
    </div>
</body>
</html>
            ''')

    # Create database if it doesn't exist
    with app.app_context():
        db.create_all()
        create_admin_user()
    
    # Run the application
    app.run(
        host='127.0.0.1',  # Only listen on localhost
        port=8080,         # Use port 8080
        debug=True         # Enable debug mode
    )
