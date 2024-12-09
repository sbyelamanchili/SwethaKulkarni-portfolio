import os
import pytest
from app import app, db, User
from PIL import Image
from io import BytesIO

@pytest.fixture
def test_client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    
    # Create a test upload folder
    test_upload_folder = os.path.join(app.static_folder, 'test_uploads')
    os.makedirs(test_upload_folder, exist_ok=True)
    app.config['UPLOAD_FOLDER'] = test_upload_folder
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            # Create test user
            test_user = User(username='test_admin')
            test_user.set_password('test_password')
            db.session.add(test_user)
            db.session.commit()
        yield client
        
        # Cleanup
        with app.app_context():
            db.session.remove()
            db.drop_all()
        # Remove test files
        for file in os.listdir(test_upload_folder):
            os.remove(os.path.join(test_upload_folder, file))
        os.rmdir(test_upload_folder)

@pytest.fixture
def authenticated_client(test_client):
    test_client.post('/login', data={
        'username': 'test_admin',
        'password': 'test_password'
    })
    return test_client

@pytest.fixture
def sample_image():
    # Create a small test image
    img = Image.new('RGB', (100, 100), color='red')
    img_io = BytesIO()
    img.save(img_io, 'JPEG')
    img_io.seek(0)
    return img_io
