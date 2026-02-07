// Admin JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize admin dashboard
    initializeAdminDashboard();
    
    // Load statistics
    loadStatistics();
    
    // Initialize modals
    initializeModals();
    
    // Initialize data tables
    initializeDataTables();
});

function initializeAdminDashboard() {
    // Toggle sidebar on mobile
    const sidebarToggle = document.getElementById('sidebarToggle');
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function() {
            document.querySelector('.admin-sidebar').classList.toggle('active');
        });
    }
    
    // Logout button
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function(e) {
            e.preventDefault();
            if (confirm('Are you sure you want to logout?')) {
                window.location.href = '/admin/logout';
            }
        });
    }
}

function loadStatistics() {
    // Fetch statistics from API
    fetch('/api/admin/statistics')
        .then(response => response.json())
        .then(data => {
            updateStatisticsDisplay(data);
        })
        .catch(error => {
            console.error('Error loading statistics:', error);
        });
}

function updateStatisticsDisplay(stats) {
    // Update DOM elements with statistics
    const elements = {
        'totalOrders': document.getElementById('totalOrders'),
        'totalRevenue': document.getElementById('totalRevenue'),
        'totalProducts': document.getElementById('totalProducts'),
        'pendingOrders': document.getElementById('pendingOrders')
    };
    
    for (const [key, element] of Object.entries(elements)) {
        if (element && stats[key] !== undefined) {
            element.textContent = key === 'totalRevenue' ? 
                `KSh ${stats[key].toFixed(2)}` : stats[key];
        }
    }
}

function initializeModals() {
    // Close modal buttons
    document.querySelectorAll('.modal-close, .btn-cancel').forEach(button => {
        button.addEventListener('click', function() {
            const modal = this.closest('.modal');
            if (modal) {
                modal.classList.remove('active');
            }
        });
    });
    
    // Open add product modal
    const addProductBtn = document.getElementById('addProductBtn');
    if (addProductBtn) {
        addProductBtn.addEventListener('click', function() {
            openModal('addProductModal');
        });
    }
    
    // Product form submission
    const productForm = document.getElementById('productForm');
    if (productForm) {
        productForm.addEventListener('submit', function(e) {
            e.preventDefault();
            saveProduct();
        });
    }
    
    // Close modal when clicking outside
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', function(e) {
            if (e.target === this) {
                this.classList.remove('active');
            }
        });
    });
}

function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('active');
    }
}

function saveProduct() {
    const form = document.getElementById('productForm');
    const formData = new FormData(form);
    
    fetch('/admin/add_product', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Product added successfully!');
            form.reset();
            document.getElementById('addProductModal').classList.remove('active');
            // Refresh products list
            window.location.reload();
        } else {
            alert('Error adding product: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Error adding product');
    });
}

function updateProductStock(productId, stock) {
    const formData = new FormData();
    formData.append('stock', stock);
    
    fetch(`/admin/update_product/${productId}`, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('Stock updated successfully!');
        } else {
            showToast('Error updating stock', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('Error updating stock', 'error');
    });
}

function toggleProductStatus(productId, isActive) {
    const formData = new FormData();
    formData.append('is_active', isActive);
    
    fetch(`/admin/update_product/${productId}`, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('Product status updated!');
            // Update button text
            const btn = document.querySelector(`[data-product="${productId}"] .status-btn`);
            if (btn) {
                btn.textContent = isActive ? 'Deactivate' : 'Activate';
                btn.className = isActive ? 'btn-action deactivate' : 'btn-action activate';
            }
        } else {
            showToast('Error updating product', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('Error updating product', 'error');
    });
}

function updateOrderStatus(orderId, status) {
    const formData = new FormData();
    formData.append('status', status);
    
    fetch(`/admin/update_order/${orderId}`, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('Order status updated!');
            // Update status badge
            const badge = document.querySelector(`[data-order="${orderId}"] .status-badge`);
            if (badge) {
                badge.textContent = status.charAt(0).toUpperCase() + status.slice(1);
                badge.className = `status-badge status-${status}`;
            }
        } else {
            showToast('Error updating order', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('Error updating order', 'error');
    });
}

function initializeDataTables() {
    // Initialize sorting and filtering for data tables
    const tables = document.querySelectorAll('.data-table table');
    
    tables.forEach(table => {
        const headers = table.querySelectorAll('th[data-sort]');
        
        headers.forEach(header => {
            header.style.cursor = 'pointer';
            header.addEventListener('click', function() {
                sortTable(table, this.dataset.sort);
            });
        });
    });
}

function sortTable(table, column) {
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    const isAscending = table.dataset.sortOrder !== 'asc';
    
    rows.sort((a, b) => {
        const aVal = a.querySelector(`td:nth-child(${getColumnIndex(table, column)})`).textContent;
        const bVal = b.querySelector(`td:nth-child(${getColumnIndex(table, column)})`).textContent;
        
        if (isAscending) {
            return aVal.localeCompare(bVal, undefined, {numeric: true});
        } else {
            return bVal.localeCompare(aVal, undefined, {numeric: true});
        }
    });
    
    // Clear and re-append rows
    rows.forEach(row => tbody.appendChild(row));
    
    // Update sort order
    table.dataset.sortOrder = isAscending ? 'asc' : 'desc';
}

function getColumnIndex(table, columnName) {
    const headers = table.querySelectorAll('th');
    for (let i = 0; i < headers.length; i++) {
        if (headers[i].dataset.sort === columnName) {
            return i + 1;
        }
    }
    return 1;
}

function showToast(message, type = 'success') {
    // Reuse toast function from main.js or create admin-specific version
    console.log(`${type.toUpperCase()}: ${message}`);
    // In practice, you would show a visual notification
    alert(`${type.toUpperCase()}: ${message}`);
}

// Search functionality for admin tables
function searchTable(tableId, searchTerm) {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    const rows = table.querySelectorAll('tbody tr');
    const searchLower = searchTerm.toLowerCase();
    
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(searchLower) ? '' : 'none';
    });
}