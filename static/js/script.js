// Cart functionality
function updateCartItem(index, quantity) {
    $.ajax({
        url: '/update-cart',
        method: 'POST',
        data: {
            item_index: index,
            quantity: quantity
        },
        success: function(response) {
            if (response.success) {
                location.reload();
            } else {
                alert(response.message || 'Failed to update cart');
            }
        }
    });
}

// Add to cart with AJAX
$(document).on('submit', '.add-to-cart-form', function(e) {
    e.preventDefault();
    const form = $(this);
    const button = form.find('button[type="submit"]');
    const originalText = button.html();
    
    button.prop('disabled', true).html('<span class="loading"></span> Adding...');
    
    $.ajax({
        url: form.attr('action'),
        method: 'POST',
        data: form.serialize(),
        success: function(response) {
            if (response.success) {
                // Update cart count in navbar
                $('.cart-count').text(response.cart_count || 1);
                
                // Show success message
                showToast('Success', 'Item added to cart!', 'success');
                
                // Reset form
                form.find('input[name="quantity"]').val(1);
            } else {
                showToast('Error', response.message || 'Failed to add item', 'error');
            }
        },
        error: function() {
            showToast('Error', 'An error occurred', 'error');
        },
        complete: function() {
            button.prop('disabled', false).html(originalText);
        }
    });
});

// Checkout form submission
$(document).on('submit', '#checkout-form', function(e) {
    e.preventDefault();
    const form = $(this);
    const button = form.find('button[type="submit"]');
    const originalText = button.html();
    
    button.prop('disabled', true).html('<span class="loading"></span> Processing...');
    
    $.ajax({
        url: '/process-checkout',
        method: 'POST',
        data: form.serialize(),
        success: function(response) {
            if (response.success) {
                window.location.href = `/order-confirmation/${response.order_id}`;
            } else {
                showToast('Error', response.message, 'error');
                button.prop('disabled', false).html(originalText);
            }
        },
        error: function() {
            showToast('Error', 'An error occurred', 'error');
            button.prop('disabled', false).html(originalText);
        }
    });
});

// Calculate delivery fee
$(document).on('change', '#county', function() {
    const county = $(this).val().toLowerCase();
    const deliveryFee = county.includes('embu') ? 100 : 200;
    $('#delivery-fee').text(`KES ${deliveryFee}`);
    
    // Recalculate total
    const subtotal = parseFloat($('#subtotal').text().replace('KES ', '')) || 0;
    const total = subtotal + deliveryFee;
    $('#total').text(`KES ${total}`);
});

// Toast notification
function showToast(title, message, type = 'info') {
    const toast = $(`
        <div class="toast align-items-center text-white bg-${type === 'error' ? 'danger' : type} border-0" role="alert">
            <div class="d-flex">
                <div class="toast-body">
                    <strong>${title}:</strong> ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `);
    
    $('#toast-container').append(toast);
    const bsToast = new bootstrap.Toast(toast[0]);
    bsToast.show();
    
    // Remove toast after hiding
    toast.on('hidden.bs.toast', function() {
        $(this).remove();
    });
}

// Initialize toast container
if (!$('#toast-container').length) {
    $('body').append('<div id="toast-container" class="position-fixed top-0 end-0 p-3" style="z-index: 1050"></div>');
}

// Image preview for file uploads
$(document).on('change', '.image-upload', function() {
    const input = $(this)[0];
    const preview = $(this).siblings('.image-preview');
    
    if (input.files && input.files[0]) {
        const reader = new FileReader();
        
        reader.onload = function(e) {
            preview.attr('src', e.target.result).show();
        }
        
        reader.readAsDataURL(input.files[0]);
    }
});

// Search with debounce
let searchTimeout;
$(document).on('input', '#search-input', function() {
    clearTimeout(searchTimeout);
    const query = $(this).val();
    
    if (query.length >= 2) {
        searchTimeout = setTimeout(() => {
            window.location.href = `/search?q=${encodeURIComponent(query)}`;
        }, 500);
    }
});

// Product quantity controls
$(document).on('click', '.quantity-minus', function() {
    const input = $(this).siblings('.quantity-input');
    let value = parseInt(input.val()) || 1;
    if (value > 1) {
        input.val(value - 1);
    }
});

$(document).on('click', '.quantity-plus', function() {
    const input = $(this).siblings('.quantity-input');
    let value = parseInt(input.val()) || 1;
    const max = input.attr('max') || 99;
    if (value < max) {
        input.val(value + 1);
    }
});

// Initialize tooltips
$(function() {
    $('[data-bs-toggle="tooltip"]').tooltip();
});

// Payment method selection
$(document).on('change', 'input[name="payment_method"]', function() {
    const method = $(this).val();
    $('.payment-details').hide();
    $(`#${method}-details`).show();
});
// Add to your existing script.js

// Password reset form validation
$(document).on('submit', '#resetPasswordForm', function(e) {
    e.preventDefault();
    const form = $(this);
    const button = form.find('button[type="submit"]');
    const originalText = button.html();
    
    button.prop('disabled', true).html('<span class="loading"></span> Resetting...');
    
    // Simulate API call
    setTimeout(function() {
        showToast('Success', 'Password reset successfully!', 'success');
        setTimeout(function() {
            window.location.href = "{{ url_for('login') }}";
        }, 1500);
    }, 1000);
});

// Add to existing showToast function for better styling
function showToast(title, message, type = 'info') {
    const icon = type === 'success' ? 'check-circle' : 
                 type === 'error' ? 'exclamation-triangle' : 
                 type === 'warning' ? 'exclamation-circle' : 'info-circle';
    
    const toast = $(`
        <div class="toast align-items-center text-white bg-${type === 'error' ? 'danger' : type} border-0" role="alert">
            <div class="d-flex">
                <div class="toast-body">
                    <i class="fas fa-${icon} me-2"></i>
                    <strong>${title}:</strong> ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `);
    
    $('#toast-container').append(toast);
    const bsToast = new bootstrap.Toast(toast[0]);
    bsToast.show();
    
    toast.on('hidden.bs.toast', function() {
        $(this).remove();
    });
} 