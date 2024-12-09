from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import unittest
import os
from app import app, db, User
from werkzeug.security import generate_password_hash
import tempfile
import time
from PIL import Image

class TestFunctional(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Set up Chrome options for testing
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless')  # Run in headless mode
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        cls.browser = webdriver.Chrome(options=chrome_options)
        cls.browser.implicitly_wait(10)

        # Create test app
        cls.db_fd, app.config['DATABASE'] = tempfile.mkstemp()
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + app.config['DATABASE']
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SERVER_NAME'] = 'localhost:5000'
        cls.app = app.test_client()
        
        # Create database and test user
        with app.app_context():
            db.create_all()
            test_user = User(username='test_admin')
            test_user.password_hash = generate_password_hash('test_password')
            db.session.add(test_user)
            db.session.commit()

        # Start the Flask application in a separate thread
        import threading
        threading.Thread(target=app.run).start()
        time.sleep(1)  # Wait for the server to start

    @classmethod
    def tearDownClass(cls):
        cls.browser.quit()
        with app.app_context():
            db.session.remove()
            db.drop_all()
        os.close(cls.db_fd)
        os.unlink(app.config['DATABASE'])

    def test_navigation_links(self):
        """Test that navigation links work correctly"""
        self.browser.get('http://localhost:5000')
        
        # Test Gallery link
        gallery_link = self.browser.find_element(By.CSS_SELECTOR, 'a[href="#gallery"]')
        gallery_link.click()
        time.sleep(1)  # Wait for smooth scroll
        gallery_section = self.browser.find_element(By.ID, 'gallery')
        self.assertTrue(gallery_section.is_displayed())
        
        # Test About link
        about_link = self.browser.find_element(By.CSS_SELECTOR, 'a[href="#about"]')
        about_link.click()
        time.sleep(1)
        about_section = self.browser.find_element(By.ID, 'about')
        self.assertTrue(about_section.is_displayed())
        
        # Test Contact link
        contact_link = self.browser.find_element(By.CSS_SELECTOR, 'a[href="#contact"]')
        contact_link.click()
        time.sleep(1)
        contact_section = self.browser.find_element(By.ID, 'contact')
        self.assertTrue(contact_section.is_displayed())

    def test_contact_form(self):
        """Test the contact form submission"""
        self.browser.get('http://localhost:5000')
        
        # Find form elements
        name_input = self.browser.find_element(By.ID, 'name')
        email_input = self.browser.find_element(By.ID, 'email')
        message_input = self.browser.find_element(By.ID, 'message')
        submit_button = self.browser.find_element(By.CSS_SELECTOR, '#contact-form button[type="submit"]')
        
        # Fill out the form
        name_input.send_keys('Test User')
        email_input.send_keys('test@example.com')
        message_input.send_keys('This is a test message')
        
        # Submit the form
        submit_button.click()
        
        try:
            # Wait for success message
            alert = WebDriverWait(self.browser, 3).until(EC.alert_is_present())
            self.assertIn('Message sent successfully', alert.text)
            alert.accept()
        except TimeoutException:
            self.fail("Alert did not appear")

    def test_admin_login(self):
        """Test the admin login process"""
        self.browser.get('http://localhost:5000/login')
        
        # Find login form elements
        username_input = self.browser.find_element(By.NAME, 'username')
        password_input = self.browser.find_element(By.NAME, 'password')
        submit_button = self.browser.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
        
        # Fill out the form
        username_input.send_keys('test_admin')
        password_input.send_keys('test_password')
        
        # Submit the form
        submit_button.click()
        
        # Wait for redirect to admin page
        WebDriverWait(self.browser, 3).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'admin-container'))
        )
        
        # Verify we're on the admin page
        self.assertIn('Admin Panel', self.browser.page_source)

    def test_image_upload_and_display(self):
        """Test image upload and display functionality"""
        # Login first
        self.browser.get('http://localhost:5000/login')
        username_input = self.browser.find_element(By.NAME, 'username')
        password_input = self.browser.find_element(By.NAME, 'password')
        username_input.send_keys('test_admin')
        password_input.send_keys('test_password')
        self.browser.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
        
        # Wait for redirect to admin page
        WebDriverWait(self.browser, 3).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'admin-container'))
        )
        
        # Find the file input and upload button
        file_input = self.browser.find_element(By.CSS_SELECTOR, 'input[type="file"]')
        
        # Create a temporary test image
        test_image_path = os.path.join(tempfile.gettempdir(), 'test_image.jpg')
        img = Image.new('RGB', (100, 100), color='red')
        img.save(test_image_path)
        
        try:
            # Upload the image
            file_input.send_keys(test_image_path)
            upload_button = self.browser.find_element(By.ID, 'upload-button')
            upload_button.click()
            
            # Wait for the upload to complete and image to appear
            WebDriverWait(self.browser, 5).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'image-container'))
            )
            
            # Verify the image is displayed
            images = self.browser.find_elements(By.CLASS_NAME, 'image-container')
            self.assertGreater(len(images), 0)
            
            # Test image rotation
            rotate_button = self.browser.find_element(By.CSS_SELECTOR, '.rotate-button')
            rotate_button.click()
            
            # Wait for rotation to complete
            time.sleep(1)
            
            # Test image deletion
            delete_button = self.browser.find_element(By.CSS_SELECTOR, '.delete-button')
            delete_button.click()
            
            # Accept the confirmation dialog
            alert = WebDriverWait(self.browser, 3).until(EC.alert_is_present())
            alert.accept()
            
            # Wait for the image to be removed
            WebDriverWait(self.browser, 3).until(
                EC.invisibility_of_element_located((By.CLASS_NAME, 'image-container'))
            )
            
        finally:
            # Clean up the test image
            if os.path.exists(test_image_path):
                os.remove(test_image_path)

    def test_gallery_view(self):
        """Test the public gallery view"""
        # First upload an image as admin
        self.test_image_upload_and_display()
        
        # Go to the public gallery page
        self.browser.get('http://localhost:5000')
        
        # Wait for gallery section
        gallery_section = WebDriverWait(self.browser, 3).until(
            EC.presence_of_element_located((By.ID, 'gallery'))
        )
        
        # Verify images are displayed
        images = gallery_section.find_elements(By.CLASS_NAME, 'gallery-image')
        self.assertGreater(len(images), 0)
        
        # Test lightbox functionality
        images[0].click()
        
        # Wait for lightbox to appear
        lightbox = WebDriverWait(self.browser, 3).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'lightbox'))
        )
        self.assertTrue(lightbox.is_displayed())
        
        # Close lightbox
        close_button = self.browser.find_element(By.CLASS_NAME, 'close-lightbox')
        close_button.click()
        
        # Wait for lightbox to disappear
        WebDriverWait(self.browser, 3).until(
            EC.invisibility_of_element_located((By.CLASS_NAME, 'lightbox'))
        )

if __name__ == '__main__':
    unittest.main()
