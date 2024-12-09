import unittest
from app import app, db, User
import os
import tempfile
from werkzeug.security import generate_password_hash
from io import BytesIO

class TestRoutes(unittest.TestCase):
    def setUp(self):
        # Create a temporary database
        self.db_fd, app.config['DATABASE'] = tempfile.mkstemp()
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + app.config['DATABASE']
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        
        with app.app_context():
            db.create_all()
            # Create test user
            test_user = User(username='test_admin')
            test_user.password_hash = generate_password_hash('test_password')
            db.session.add(test_user)
            db.session.commit()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()
        os.close(self.db_fd)
        os.unlink(app.config['DATABASE'])

    def test_index_page(self):
        """Test the landing page loads correctly"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Portfolio', response.data)
        self.assertIn(b'Gallery', response.data)
        self.assertIn(b'About', response.data)
        self.assertIn(b'Contact', response.data)

    def test_login_page(self):
        """Test the login page loads correctly"""
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Login', response.data)

    def test_successful_login(self):
        """Test successful login with correct credentials"""
        response = self.client.post('/login', data={
            'username': 'test_admin',
            'password': 'test_password'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Admin Panel', response.data)

    def test_failed_login(self):
        """Test failed login with incorrect credentials"""
        response = self.client.post('/login', data={
            'username': 'test_admin',
            'password': 'wrong_password'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Invalid username or password', response.data)

    def test_logout(self):
        """Test logout functionality"""
        # First login
        self.client.post('/login', data={
            'username': 'test_admin',
            'password': 'test_password'
        })
        # Then logout
        response = self.client.get('/logout', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Login', response.data)

    def test_protected_admin_route(self):
        """Test that admin route requires authentication"""
        response = self.client.get('/admin', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Please log in to access this page', response.data)

if __name__ == '__main__':
    unittest.main()
