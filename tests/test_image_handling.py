import unittest
from app import app, db, User
import os
import tempfile
from PIL import Image
from io import BytesIO
import json

class TestImageHandling(unittest.TestCase):
    def setUp(self):
        # Create a temporary database and upload folder
        self.db_fd, app.config['DATABASE'] = tempfile.mkstemp()
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + app.config['DATABASE']
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        
        # Create temporary upload folder
        self.test_upload_folder = tempfile.mkdtemp()
        app.config['UPLOAD_FOLDER'] = self.test_upload_folder
        
        self.client = app.test_client()
        
        # Create test image
        self.test_image = self._create_test_image()
        
        with app.app_context():
            db.create_all()
            # Create and login test user
            test_user = User(username='test_admin')
            test_user.set_password('test_password')
            db.session.add(test_user)
            db.session.commit()
            
        # Login
        self.client.post('/login', data={
            'username': 'test_admin',
            'password': 'test_password'
        })

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()
        os.close(self.db_fd)
        os.unlink(app.config['DATABASE'])
        
        # Clean up test upload folder
        for file in os.listdir(self.test_upload_folder):
            os.remove(os.path.join(self.test_upload_folder, file))
        os.rmdir(self.test_upload_folder)

    def _create_test_image(self):
        """Helper method to create a test image"""
        img = Image.new('RGB', (100, 100), color='red')
        img_io = BytesIO()
        img.save(img_io, 'JPEG', quality=70)
        img_io.seek(0)
        return img_io

    def test_upload_image(self):
        """Test image upload functionality"""
        response = self.client.post('/upload', data={
            'images': [(self.test_image, 'test.jpg')]
        }, content_type='multipart/form-data')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['uploaded_files']), 1)
        
        # Verify file exists in upload folder
        uploaded_file = os.path.join(self.test_upload_folder, data['uploaded_files'][0])
        self.assertTrue(os.path.exists(uploaded_file))
        
        # Verify image properties
        with Image.open(uploaded_file) as img:
            self.assertLessEqual(img.size[0], 1920)  # Check max dimension
            self.assertLessEqual(img.size[1], 1920)

    def test_upload_invalid_file(self):
        """Test uploading an invalid file type"""
        # Create a text file
        text_file = BytesIO(b'This is not an image')
        
        response = self.client.post('/upload', data={
            'images': [(text_file, 'test.txt')]
        }, content_type='multipart/form-data')
        
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('Invalid file type', str(data['errors']))

    def test_delete_image(self):
        """Test image deletion"""
        # First upload an image
        response = self.client.post('/upload', data={
            'images': [(self.test_image, 'test.jpg')]
        }, content_type='multipart/form-data')
        
        upload_data = json.loads(response.data)
        filename = upload_data['uploaded_files'][0]
        
        # Then delete it
        response = self.client.post('/delete-image', 
                                  json={'filename': filename},
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        
        # Verify file is deleted
        self.assertFalse(os.path.exists(os.path.join(self.test_upload_folder, filename)))

    def test_rotate_image(self):
        """Test image rotation"""
        # First upload an image
        response = self.client.post('/upload', data={
            'images': [(self.test_image, 'test.jpg')]
        }, content_type='multipart/form-data')
        
        upload_data = json.loads(response.data)
        filename = upload_data['uploaded_files'][0]
        
        # Get original image size
        original_path = os.path.join(self.test_upload_folder, filename)
        with Image.open(original_path) as img:
            original_size = img.size
        
        # Rotate image
        response = self.client.post('/rotate-image',
                                  json={'filename': filename, 'degrees': 90},
                                  content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        
        # Verify rotation
        with Image.open(original_path) as img:
            rotated_size = img.size
            self.assertEqual(original_size[0], rotated_size[1])
            self.assertEqual(original_size[1], rotated_size[0])

    def test_get_images(self):
        """Test retrieving image list"""
        # Upload multiple images
        test_images = [
            (self._create_test_image(), 'test1.jpg'),
            (self._create_test_image(), 'test2.jpg')
        ]
        
        for img, name in test_images:
            self.client.post('/upload', data={
                'images': [(img, name)]
            }, content_type='multipart/form-data')
        
        # Get image list
        response = self.client.get('/get-images')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['images']), 2)
        
        # Verify image URLs are correct
        for image in data['images']:
            self.assertTrue('filename' in image)
            self.assertTrue('url' in image)
            self.assertTrue(image['url'].startswith('/static/uploads/'))

    def test_static_file_headers(self):
        """Test static file response headers"""
        # Upload an image
        response = self.client.post('/upload', data={
            'images': [(self.test_image, 'test.jpg')]
        }, content_type='multipart/form-data')
        
        upload_data = json.loads(response.data)
        filename = upload_data['uploaded_files'][0]
        
        # Get the image and check headers
        response = self.client.get(f'/static/uploads/{filename}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['Content-Type'], 'image/jpeg')
        self.assertIn('no-cache', response.headers['Cache-Control'])
        self.assertEqual(response.headers['Pragma'], 'no-cache')
        self.assertEqual(response.headers['Expires'], '-1')

if __name__ == '__main__':
    unittest.main()
