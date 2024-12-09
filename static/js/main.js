document.addEventListener('DOMContentLoaded', () => {
    // Gallery management
    const gallery = document.querySelector('.gallery-grid');
    const modal = document.querySelector('.modal');
    const modalImg = document.querySelector('.modal-image');
    let currentImageIndex = 0;
    let images = [];

    // Fetch and display gallery images
    const loadGallery = async () => {
        try {
            const response = await fetch('/gallery');
            images = await response.json();
            
            gallery.innerHTML = images.map((image, index) => `
                <div class="gallery-item">
                    <img src="${image.url}" 
                         alt="Gallery image" 
                         class="gallery-image" 
                         loading="lazy"
                         data-index="${index}"
                         onclick="openModal(${index})">
                </div>
            `).join('');
        } catch (error) {
            console.error('Error loading gallery:', error);
        }
    };

    // Modal functions
    window.openModal = (index) => {
        currentImageIndex = index;
        modal.style.display = 'block';
        modalImg.src = images[index].url;
        document.body.style.overflow = 'hidden';
    };

    window.closeModal = () => {
        modal.style.display = 'none';
        document.body.style.overflow = 'auto';
    };

    window.nextImage = () => {
        currentImageIndex = (currentImageIndex + 1) % images.length;
        modalImg.src = images[currentImageIndex].url;
    };

    window.prevImage = () => {
        currentImageIndex = (currentImageIndex - 1 + images.length) % images.length;
        modalImg.src = images[currentImageIndex].url;
    };

    // Keyboard navigation
    document.addEventListener('keydown', (e) => {
        if (modal.style.display === 'block') {
            if (e.key === 'Escape') closeModal();
            if (e.key === 'ArrowRight') nextImage();
            if (e.key === 'ArrowLeft') prevImage();
        }
    });

    // Image upload handling
    const uploadForm = document.getElementById('upload-form');
    if (uploadForm) {
        uploadForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(uploadForm);
            
            try {
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                if (result.success) {
                    loadGallery();
                    uploadForm.reset();
                } else {
                    alert('Upload failed: ' + result.error);
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Upload failed');
            }
        });
    }

    // Contact form handling
    const contactForm = document.getElementById('contact-form');
    if (contactForm) {
        contactForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(contactForm);
            const data = Object.fromEntries(formData.entries());
            
            try {
                const response = await fetch('/contact', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                if (result.success) {
                    alert('Message sent successfully!');
                    contactForm.reset();
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Failed to send message');
            }
        });
    }

    // Initialize gallery
    loadGallery();

    // Lazy loading for images
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    observer.unobserve(img);
                }
            });
        });

        document.querySelectorAll('img[data-src]').forEach(img => {
            imageObserver.observe(img);
        });
    }
});
