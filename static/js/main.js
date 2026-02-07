// Main JavaScript file for MUFRA FASHIONS

document.addEventListener('DOMContentLoaded', function() {
    // Initialize all features
    initializeCart();
    initializeSearch();
    initializeMobileMenu();
    initializeImageGallery();
    initializeQuantityControls();
    initializeCheckoutForm();
    
    // Update cart count from server
    updateCartCountFromServer();
    
    // Add form validation to all forms
    initializeFormValidation();
});

// Cart functionality
function initializeCart() {
    const cartCount = document.querySelector('.cart-count');
    if (!cartCount) return;
    
    // Update cart count from session
    updateCartCount();
    
    // Set up cart item quantity updates
    document.querySelectorAll('.item-quantity input').forEach(input => {
        input.addEventListener('change', function() {
            const productId = this.closest('.cart-item').dataset.productId;
            const size = this.closest('.cart-item').dataset.size || '';
            const color = this.closest('.cart-item').dataset.color || '';
            const quantity = parseInt(this.value);
            
            updateCartItem(productId, size, color, quantity);
        });
    });
    
    // Set up remove item buttons
    document.querySelectorAll('.remove-item').forEach(button => {
        button.addEventListener('click', function() {
            const cartItem = this.closest('.cart-item');
            const productId = cartItem.dataset.productId;
            const size = cartItem.dataset.size || '';
            const color = cartItem.dataset.color || '';
            
            removeCartItem(productId, size, color);
        });
    });
}

function updateCartCount() {
    const cartCount = document.querySelector('.cart-count');
    if (cartCount) {
        // Check if we have cart data in localStorage (fallback)
        const cart = JSON.parse(localStorage.getItem('mufra_cart') || '[]');
        cartCount.textContent = cart.length;
    }
}

function updateCartCountFromServer() {
    fetch('/api/cart_count')
        .then(response => response.json())
        .then(data => {
            const cartCount = document.querySelector('.cart-count');
            if (cartCount) {
                cartCount.textContent = data.count;
            }
        })
        .catch(error => {
            console.log('Could not fetch cart count from server:', error);
        });
}

function updateCartItem(productId, size, color, quantity) {
    fetch('/add_to_cart', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({
            'product_id': productId,
            'quantity': quantity.toString(),
            'size': size,
            'color': color
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('Cart updated successfully', 'success');
            setTimeout(() => {
                location.reload();
            }, 1000);
        } else {
            showToast('Error updating cart', 'error');
        }
    })
    .catch(error => {
        showToast('Error updating cart', 'error');
        console.error('Error:', error);
    });
}

function removeCartItem(productId, size, color) {
    if (confirm('Are you sure you want to remove this item from your cart?')) {
        fetch('/add_to_cart', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams({
                'product_id': productId,
                'quantity': '0',
                'size': size,
                'color': color
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showToast('Item removed from cart', 'success');
                setTimeout(() => {
                    location.reload();
                }, 1000);
            } else {
                showToast('Error removing item', 'error');
            }
        })
        .catch(error => {
            showToast('Error removing item', 'error');
            console.error('Error:', error);
        });
    }
}

// Search functionality
function initializeSearch() {
    const searchInput = document.querySelector('.search-bar input');
    const searchBtn = document.querySelector('.search-bar button');
    
    if (!searchInput || !searchBtn) return;
    
    searchBtn.addEventListener('click', performSearch);
    searchInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            performSearch();
        }
    });
    
    function performSearch() {
        const query = searchInput.value.trim();
        if (query) {
            window.location.href = `/categories?search=${encodeURIComponent(query)}`;
        }
    }
}

// Mobile menu functionality
function initializeMobileMenu() {
    // Check if we're on mobile
    if (window.innerWidth > 768) return;
    
    const header = document.querySelector('.header .container');
    const navbar = document.querySelector('.navbar');
    
    if (!header || !navbar) return;
    
    // Create mobile menu toggle button
    const menuToggle = document.createElement('button');
    menuToggle.innerHTML = '<i class="fas fa-bars"></i>';
    menuToggle.className = 'menu-toggle';
    menuToggle.setAttribute('aria-label', 'Toggle menu');
    menuToggle.style.cssText = `
        background: none;
        border: none;
        color: white;
        font-size: 1.5rem;
        cursor: pointer;
        padding: 5px;
    `;
    
    // Insert toggle button in header
    const logo = header.querySelector('.logo');
    if (logo) {
        header.insertBefore(menuToggle, logo.nextSibling);
    }
    
    // Initially hide navbar on mobile
    navbar.style.display = 'none';
    navbar.classList.add('mobile-nav');
    
    // Toggle menu visibility
    menuToggle.addEventListener('click', function(e) {
        e.stopPropagation();
        
        if (navbar.style.display === 'none') {
            navbar.style.display = 'block';
            menuToggle.innerHTML = '<i class="fas fa-times"></i>';
            
            // Add animation
            navbar.style.animation = 'slideDown 0.3s ease-out';
        } else {
            navbar.style.display = 'none';
            menuToggle.innerHTML = '<i class="fas fa-bars"></i>';
        }
    });
    
    // Close menu when clicking outside
    document.addEventListener('click', function(e) {
        if (!navbar.contains(e.target) && !menuToggle.contains(e.target)) {
            navbar.style.display = 'none';
            menuToggle.innerHTML = '<i class="fas fa-bars"></i>';
        }
    });
    
    // Close menu when clicking a link
    navbar.addEventListener('click', function(e) {
        if (e.target.tagName === 'A') {
            navbar.style.display = 'none';
            menuToggle.innerHTML = '<i class="fas fa-bars"></i>';
        }
    });
    
    // Add CSS for mobile menu animation
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideDown {
            from {
                opacity: 0;
                transform: translateY(-10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .mobile-nav {
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: #f8f9fa;
            z-index: 1000;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        
        .mobile-nav ul {
            flex-direction: column;
            padding: 10px;
        }
        
        .mobile-nav li {
            margin: 0;
            border-bottom: 1px solid #eee;
        }
        
        .mobile-nav a {
            display: block;
            padding: 15px;
        }
        
        .menu-toggle {
            display: block !important;
        }
        
        @media (min-width: 769px) {
            .menu-toggle {
                display: none !important;
            }
            .mobile-nav {
                display: block !important;
                position: static;
                background: transparent;
                box-shadow: none;
            }
            .mobile-nav ul {
                flex-direction: row;
                padding: 15px 0;
            }
            .mobile-nav li {
                border-bottom: none;
                margin-right: 30px;
            }
            .mobile-nav a {
                padding: 0;
            }
        }
    `;
    document.head.appendChild(style);
}

// Product image gallery
function initializeImageGallery() {
    const thumbnails = document.querySelectorAll('.thumbnail');
    const mainImage = document.getElementById('mainImage');
    
    if (!thumbnails.length || !mainImage) return;
    
    thumbnails.forEach(thumb => {
        thumb.addEventListener('click', function() {
            // Remove active class from all thumbnails
            thumbnails.forEach(t => t.classList.remove('active'));
            // Add active class to clicked thumbnail
            this.classList.add('active');
            // Update main image
            mainImage.src = this.src;
            
            // Add fade animation
            mainImage.style.opacity = '0.7';
            setTimeout(() => {
                mainImage.style.opacity = '1';
            }, 150);
        });
    });
}

// Quantity controls for product pages
function initializeQuantityControls() {
    document.querySelectorAll('.quantity-control').forEach(control => {
        const minusBtn = control.querySelector('button:first-child');
        const plusBtn = control.querySelector('button:last-child');
        const input = control.querySelector('input[type="number"]');
        
        if (!minusBtn || !plusBtn || !input) return;
        
        minusBtn.addEventListener('click', () => {
            let value = parseInt(input.value) - 1;
            if (value < parseInt(input.min)) value = parseInt(input.min);
            input.value = value;
            input.dispatchEvent(new Event('change'));
        });
        
        plusBtn.addEventListener('click', () => {
            let value = parseInt(input.value) + 1;
            if (value > parseInt(input.max)) value = parseInt(input.max);
            input.value = value;
            input.dispatchEvent(new Event('change'));
        });
        
        input.addEventListener('change', () => {
            let value = parseInt(input.value);
            if (value < parseInt(input.min)) value = parseInt(input.min);
            if (value > parseInt(input.max)) value = parseInt(input.max);
            input.value = value;
        });
    });
}

// Checkout form functionality
function initializeCheckoutForm() {
    const checkoutForm = document.querySelector('.checkout-form');
    if (!checkoutForm) return;
    
    const regionSelect = document.getElementById('region');
    const deliveryFeeSpan = document.getElementById('deliveryFee');
    
    if (regionSelect && deliveryFeeSpan) {
        regionSelect.addEventListener('change', function() {
            updateDeliveryFee(this.value);
        });
        
        // Initial calculation
        updateDeliveryFee(regionSelect.value);
    }
    
    // Payment method selection
    const paymentMethods = document.querySelectorAll('.payment-method input[type="radio"]');
    paymentMethods.forEach(method => {
        method.addEventListener('change', function() {
            document.querySelectorAll('.payment-method').forEach(pm => {
                pm.classList.remove('selected');
            });
            this.closest('.payment-method').classList.add('selected');
        });
    });
}

function updateDeliveryFee(region) {
    const deliveryFeeSpan = document.getElementById('deliveryFee');
    if (!deliveryFeeSpan) return;
    
    const fee = region === 'embu' ? 100 : 200;
    deliveryFeeSpan.textContent = `KSh ${fee}`;
    
    // Update any total calculations if they exist
    updateCheckoutTotal(fee);
}

function updateCheckoutTotal(deliveryFee) {
    const subtotalElement = document.getElementById('checkoutSubtotal');
    const totalElement = document.getElementById('checkoutTotal');
    
    if (subtotalElement && totalElement) {
        const subtotal = parseFloat(subtotalElement.textContent.replace('KSh ', '')) || 0;
        const total = subtotal + deliveryFee;
        totalElement.textContent = `KSh ${total.toFixed(2)}`;
    }
}

// Add to cart functionality for product pages
window.addToCart = function() {
    const productId = document.getElementById('productId')?.value;
    const quantity = document.getElementById('quantity')?.value || 1;
    const size = document.getElementById('size')?.value || '';
    const color = document.querySelector('.color-option.selected')?.title || 
                  document.querySelector('.color-option')?.title || '';
    
    if (!productId) {
        showToast('Product ID not found', 'error');
        return;
    }
    
    fetch('/add_to_cart', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({
            'product_id': productId,
            'quantity': quantity,
            'size': size,
            'color': color
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('Product added to cart!', 'success');
            
            // Update cart count
            const cartCount = document.querySelector('.cart-count');
            if (cartCount) {
                cartCount.textContent = data.cart_count;
            }
            
            // Update localStorage as fallback
            const cart = JSON.parse(localStorage.getItem('mufra_cart') || '[]');
            const existingItemIndex = cart.findIndex(item => 
                item.product_id === productId && 
                item.size === size && 
                item.color === color
            );
            
            if (existingItemIndex > -1) {
                cart[existingItemIndex].quantity += parseInt(quantity);
            } else {
                cart.push({
                    product_id: productId,
                    quantity: parseInt(quantity),
                    size: size,
                    color: color,
                    added_at: new Date().toISOString()
                });
            }
            
            localStorage.setItem('mufra_cart', JSON.stringify(cart));
        } else {
            showToast('Error adding to cart: ' + (data.error || 'Unknown error'), 'error');
        }
    })
    .catch(error => {
        showToast('Error adding to cart', 'error');
        console.error('Error:', error);
    });
};

// Buy now functionality
window.buyNow = function() {
    window.addToCart();
    
    // Wait a moment for cart to update, then redirect to checkout
    setTimeout(() => {
        window.location.href = '/checkout';
    }, 500);
};

// Color selection for product pages
window.selectColor = function(element) {
    document.querySelectorAll('.color-option').forEach(opt => {
        opt.classList.remove('selected');
    });
    element.classList.add('selected');
};

// Form validation
function initializeFormValidation() {
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!validateForm(this)) {
                e.preventDefault();
            }
        });
    });
}

function validateForm(form) {
    const requiredFields = form.querySelectorAll('[required]');
    let isValid = true;
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            field.style.borderColor = '#dc3545';
            isValid = false;
            
            // Add error message
            if (!field.nextElementSibling?.classList.contains('error-message')) {
                const errorMsg = document.createElement('div');
                errorMsg.className = 'error-message';
                errorMsg.textContent = 'This field is required';
                errorMsg.style.cssText = `
                    color: #dc3545;
                    font-size: 0.875rem;
                    margin-top: 0.25rem;
                `;
                field.parentNode.appendChild(errorMsg);
            }
            
            // Remove error on input
            field.addEventListener('input', function() {
                this.style.borderColor = '#ddd';
                const errorMsg = this.nextElementSibling;
                if (errorMsg?.classList.contains('error-message')) {
                    errorMsg.remove();
                }
            }, { once: true });
        }
        
        // Validate email format
        if (field.type === 'email' && field.value.trim()) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(field.value.trim())) {
                field.style.borderColor = '#dc3545';
                isValid = false;
                
                if (!field.nextElementSibling?.classList.contains('error-message')) {
                    const errorMsg = document.createElement('div');
                    errorMsg.className = 'error-message';
                    errorMsg.textContent = 'Please enter a valid email address';
                    errorMsg.style.cssText = `
                        color: #dc3545;
                        font-size: 0.875rem;
                        margin-top: 0.25rem;
                    `;
                    field.parentNode.appendChild(errorMsg);
                }
            }
        }
        
        // Validate phone number
        if (field.type === 'tel' && field.value.trim()) {
            const phoneRegex = /^[+]?[\d\s\-\(\)]+$/;
            if (!phoneRegex.test(field.value.trim())) {
                field.style.borderColor = '#dc3545';
                isValid = false;
                
                if (!field.nextElementSibling?.classList.contains('error-message')) {
                    const errorMsg = document.createElement('div');
                    errorMsg.className = 'error-message';
                    errorMsg.textContent = 'Please enter a valid phone number';
                    errorMsg.style.cssText = `
                        color: #dc3545;
                        font-size: 0.875rem;
                        margin-top: 0.25rem;
                    `;
                    field.parentNode.appendChild(errorMsg);
                }
            }
        }
    });
    
    if (!isValid) {
        showToast('Please fill in all required fields correctly', 'error');
    }
    
    return isValid;
}

// Toast notifications system
window.showToast = function(message, type = 'success') {
    // Remove existing toasts
    document.querySelectorAll('.toast').forEach(toast => {
        toast.remove();
    });
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <div class="toast-content">
            <i class="fas ${type === 'success' ? 'fa-check-circle' : 
                          type === 'error' ? 'fa-exclamation-circle' : 
                          type === 'warning' ? 'fa-exclamation-triangle' : 
                          'fa-info-circle'}"></i>
            <span>${message}</span>
        </div>
        <button class="toast-close" aria-label="Close notification">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'success' ? '#d4edda' : 
                     type === 'error' ? '#f8d7da' : 
                     type === 'warning' ? '#fff3cd' : 
                     '#d1ecf1'};
        color: ${type === 'success' ? '#155724' : 
                type === 'error' ? '#721c24' : 
                type === 'warning' ? '#856404' : 
                '#0c5460'};
        padding: 1rem 1.5rem;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        min-width: 300px;
        max-width: 400px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 9999;
        animation: slideInRight 0.3s ease-out;
        border-left: 4px solid ${type === 'success' ? '#28a745' : 
                               type === 'error' ? '#dc3545' : 
                               type === 'warning' ? '#ffc107' : 
                               '#17a2b8'};
    `;
    
    document.body.appendChild(toast);
    
    // Add close button functionality
    const closeBtn = toast.querySelector('.toast-close');
    closeBtn.addEventListener('click', () => {
        toast.style.animation = 'slideOutRight 0.3s ease-out';
        setTimeout(() => toast.remove(), 300);
    });
    
    // Auto remove after 5 seconds
    const autoRemove = setTimeout(() => {
        if (toast.parentNode) {
            toast.style.animation = 'slideOutRight 0.3s ease-out';
            setTimeout(() => toast.remove(), 300);
        }
    }, 5000);
    
    // Pause auto-remove on hover
    toast.addEventListener('mouseenter', () => {
        clearTimeout(autoRemove);
    });
    
    toast.addEventListener('mouseleave', () => {
        setTimeout(() => {
            if (toast.parentNode) {
                toast.style.animation = 'slideOutRight 0.3s ease-out';
                setTimeout(() => toast.remove(), 300);
            }
        }, 5000);
    });
};

// Add CSS for toast animations
const toastStyles = document.createElement('style');
toastStyles.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOutRight {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
    
    .toast {
        font-family: inherit;
    }
    
    .toast-content {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        flex: 1;
    }
    
    .toast-content i {
        font-size: 1.25rem;
    }
    
    .toast-close {
        background: none;
        border: none;
        cursor: pointer;
        color: inherit;
        margin-left: 1rem;
        padding: 0.25rem;
        border-radius: 4px;
        transition: background-color 0.2s;
    }
    
    .toast-close:hover {
        background-color: rgba(0, 0, 0, 0.1);
    }
    
    .toast-close:focus {
        outline: 2px solid rgba(0, 0, 0, 0.3);
        outline-offset: 2px;
    }
`;
document.head.appendChild(toastStyles);

// Image lazy loading
function initializeLazyLoading() {
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.classList.add('loaded');
                    observer.unobserve(img);
                }
            });
        });
        
        document.querySelectorAll('img[data-src]').forEach(img => {
            imageObserver.observe(img);
        });
    } else {
        // Fallback for older browsers
        document.querySelectorAll('img[data-src]').forEach(img => {
            img.src = img.dataset.src;
        });
    }
}

// Initialize lazy loading
initializeLazyLoading();

// Price formatting helper
window.formatPrice = function(price) {
    return new Intl.NumberFormat('en-KE', {
        style: 'currency',
        currency: 'KES',
        minimumFractionDigits: 2
    }).format(price).replace('KES', 'KSh');
};

// Add loading state to buttons
document.addEventListener('click', function(e) {
    if (e.target.tagName === 'BUTTON' || e.target.closest('button')) {
        const button = e.target.tagName === 'BUTTON' ? e.target : e.target.closest('button');
        
        if (button.type === 'submit' || button.classList.contains('btn-primary') || 
            button.classList.contains('btn-secondary')) {
            
            // Only add loading if not already loading
            if (!button.classList.contains('loading')) {
                button.classList.add('loading');
                
                // Add loading spinner
                const originalHTML = button.innerHTML;
                button.innerHTML = `
                    <span class="spinner"></span>
                    ${button.textContent}
                `;
                button.disabled = true;
                
                // Add spinner styles
                const spinnerStyle = document.createElement('style');
                if (!document.querySelector('#spinner-styles')) {
                    spinnerStyle.id = 'spinner-styles';
                    spinnerStyle.textContent = `
                        .spinner {
                            display: inline-block;
                            width: 1rem;
                            height: 1rem;
                            border: 2px solid rgba(255,255,255,0.3);
                            border-radius: 50%;
                            border-top-color: white;
                            animation: spin 1s ease-in-out infinite;
                            margin-right: 0.5rem;
                            vertical-align: middle;
                        }
                        
                        @keyframes spin {
                            to { transform: rotate(360deg); }
                        }
                    `;
                    document.head.appendChild(spinnerStyle);
                }
                
                // Auto remove loading state after 10 seconds (safety)
                setTimeout(() => {
                    button.classList.remove('loading');
                    button.innerHTML = originalHTML;
                    button.disabled = false;
                }, 10000);
            }
        }
    }
});

// Prevent double form submissions
document.addEventListener('submit', function(e) {
    const form = e.target;
    const submitButton = form.querySelector('button[type="submit"]');
    
    if (submitButton && !submitButton.classList.contains('loading')) {
        submitButton.classList.add('loading');
        submitButton.disabled = true;
        
        const originalHTML = submitButton.innerHTML;
        submitButton.innerHTML = `
            <span class="spinner"></span>
            ${submitButton.textContent}
        `;
        
        // Store original content to restore if needed
        submitButton.dataset.originalHtml = originalHTML;
    }
});

// Handle back/forward navigation
window.addEventListener('pageshow', function(event) {
    // Reset loading buttons on page show
    document.querySelectorAll('.loading').forEach(button => {
        button.classList.remove('loading');
        if (button.dataset.originalHtml) {
            button.innerHTML = button.dataset.originalHtml;
        }
        button.disabled = false;
    });
});

// Smooth scrolling for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
        const href = this.getAttribute('href');
        if (href === '#') return;
        
        e.preventDefault();
        const target = document.querySelector(href);
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Initialize tooltips
function initializeTooltips() {
    const tooltipElements = document.querySelectorAll('[title]');
    tooltipElements.forEach(element => {
        element.addEventListener('mouseenter', showTooltip);
        element.addEventListener('mouseleave', hideTooltip);
    });
}

function showTooltip(e) {
    const element = e.target;
    const tooltipText = element.getAttribute('title');
    
    if (!tooltipText) return;
    
    // Create tooltip element
    const tooltip = document.createElement('div');
    tooltip.className = 'tooltip';
    tooltip.textContent = tooltipText;
    tooltip.style.cssText = `
        position: absolute;
        background: rgba(0, 0, 0, 0.8);
        color: white;
        padding: 0.5rem 0.75rem;
        border-radius: 4px;
        font-size: 0.875rem;
        z-index: 10000;
        white-space: nowrap;
        pointer-events: none;
        transform: translateX(-50%);
        left: 50%;
        bottom: 100%;
        margin-bottom: 0.5rem;
    `;
    
    // Add arrow
    const arrow = document.createElement('div');
    arrow.style.cssText = `
        position: absolute;
        width: 0;
        height: 0;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 5px solid rgba(0, 0, 0, 0.8);
        left: 50%;
        top: 100%;
        transform: translateX(-50%);
    `;
    
    tooltip.appendChild(arrow);
    element.appendChild(tooltip);
    
    // Remove title attribute to prevent default tooltip
    element.removeAttribute('title');
    
    // Restore title when tooltip is hidden
    element.addEventListener('mouseleave', function restoreTitle() {
        element.setAttribute('title', tooltipText);
        element.removeEventListener('mouseleave', restoreTitle);
    }, { once: true });
}

function hideTooltip(e) {
    const tooltip = e.target.querySelector('.tooltip');
    if (tooltip) {
        tooltip.remove();
    }
}

// Initialize tooltips
initializeTooltips();

// Add CSS for tooltips
const tooltipStyle = document.createElement('style');
tooltipStyle.textContent = `
    .tooltip::before {
        content: '';
        position: absolute;
        width: 0;
        height: 0;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 5px solid rgba(0, 0, 0, 0.8);
        left: 50%;
        top: 100%;
        transform: translateX(-50%);
    }
`;
document.head.appendChild(tooltipStyle);

// Debounce function for performance
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Throttle function for performance
function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// Add resize listener with debounce
window.addEventListener('resize', debounce(function() {
    // Reinitialize mobile menu on resize
    if (window.innerWidth <= 768) {
        initializeMobileMenu();
    }
}, 250));

// Export functions for use in other scripts
window.MUFRA = {
    showToast,
    formatPrice,
    validateForm,
    updateCartCount,
    addToCart: window.addToCart,
    buyNow: window.buyNow,
    selectColor: window.selectColor
};

console.log('MUFRA FASHIONS JavaScript initialized successfully!');