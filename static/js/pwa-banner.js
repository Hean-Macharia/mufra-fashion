/**
 * PWA Install Banner
 * Shows a beautiful, animated banner prompting users to install the app
 * Only shows on first visit and can be dismissed
 */

(function() {
    const BANNER_DISMISSED = 'mufra-install-banner-dismissed';
    let deferredPrompt = null;
    
    // Capture the install prompt
    window.addEventListener('beforeinstallprompt', (e) => {
        e.preventDefault();
        deferredPrompt = e;
        
        // Check if user dismissed the banner before
        if (sessionStorage.getItem(BANNER_DISMISSED)) {
            return;
        }
        
        // Show install banner after a short delay
        setTimeout(() => {
            showInstallBanner();
        }, 2000);
    });
    
    function showInstallBanner() {
        // Check if banner already exists
        if (document.getElementById('pwa-install-banner')) {
            return;
        }
        
        // Create banner HTML
        const banner = document.createElement('div');
        banner.id = 'pwa-install-banner';
        banner.className = 'pwa-install-banner';
        banner.innerHTML = `
            <div class="pwa-banner-content">
                <div class="pwa-banner-left">
                    <div class="pwa-banner-icon">
                        <i class="fas fa-mobile-alt"></i>
                    </div>
                    <div class="pwa-banner-text">
                        <h4 class="pwa-banner-title">Install MUFRA App</h4>
                        <p class="pwa-banner-subtitle">Shop your favorite fashions on the go!</p>
                    </div>
                </div>
                <div class="pwa-banner-actions">
                    <button class="btn btn-primary btn-sm pwa-install-yes" id="pwa-banner-install">
                        <i class="fas fa-download me-2"></i>Install
                    </button>
                    <button class="btn btn-ghost btn-sm pwa-install-no" id="pwa-banner-dismiss">
                        ✕
                    </button>
                </div>
            </div>
        `;
        
        // Add to body
        document.body.appendChild(banner);
        
        // Trigger animation
        setTimeout(() => {
            banner.classList.add('show');
        }, 100);
        
        // Install button handler
        const installBtn = banner.querySelector('#pwa-banner-install');
        installBtn.addEventListener('click', async () => {
            if (deferredPrompt) {
                deferredPrompt.prompt();
                const { outcome } = await deferredPrompt.userChoice;
                console.log(`User response: ${outcome}`);
                deferredPrompt = null;
                closeBanner();
            }
        });
        
        // Dismiss button handler
        const dismissBtn = banner.querySelector('#pwa-banner-dismiss');
        dismissBtn.addEventListener('click', () => {
            sessionStorage.setItem(BANNER_DISMISSED, 'true');
            closeBanner();
        });
        
        // Auto-close after 30 seconds if user doesn't interact
        setTimeout(() => {
            if (banner.parentElement) {
                closeBanner();
            }
        }, 30000);
        
        // Close on scroll down
        let lastScrollTop = 0;
        const scrollListener = () => {
            const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
            if (scrollTop > lastScrollTop + 100) {
                // User scrolled down
                sessionStorage.setItem(BANNER_DISMISSED, 'true');
                closeBanner();
                window.removeEventListener('scroll', scrollListener);
            }
            lastScrollTop = scrollTop <= 0 ? 0 : scrollTop;
        };
        window.addEventListener('scroll', scrollListener);
    }
    
    function closeBanner() {
        const banner = document.getElementById('pwa-install-banner');
        if (banner) {
            banner.classList.remove('show');
            setTimeout(() => {
                if (banner.parentElement) {
                    banner.remove();
                }
            }, 300);
        }
    }
    
    // Show banner for standalone mode too (update available)
    if (window.navigator.standalone === true) {
        // Check for updates periodically
        if ('serviceWorker' in navigator) {
            setInterval(() => {
                navigator.serviceWorker.getRegistration()
                    .then((registration) => {
                        if (registration) {
                            registration.update();
                        }
                    });
            }, 60000);
        }
    }
    
    // Detect update to service worker
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.getRegistration()
            .then((registration) => {
                if (registration) {
                    registration.addEventListener('updatefound', () => {
                        const newWorker = registration.installing;
                        newWorker.addEventListener('statechange', () => {
                            if (newWorker.state === 'activated') {
                                // Show update notification
                                showUpdateBanner();
                            }
                        });
                    });
                }
            });
    }
    
    function showUpdateBanner() {
        // Check if update banner already exists
        if (document.getElementById('pwa-update-banner')) {
            return;
        }
        
        const banner = document.createElement('div');
        banner.id = 'pwa-update-banner';
        banner.className = 'pwa-update-banner';
        banner.innerHTML = `
            <div class="pwa-banner-content">
                <div class="pwa-banner-left">
                    <div class="pwa-banner-icon">
                        <i class="fas fa-sync-alt"></i>
                    </div>
                    <div class="pwa-banner-text">
                        <h4 class="pwa-banner-title">Update Available</h4>
                        <p class="pwa-banner-subtitle">Refresh to get the latest version</p>
                    </div>
                </div>
                <div class="pwa-banner-actions">
                    <button class="btn btn-primary btn-sm" id="pwa-refresh-page">
                        <i class="fas fa-redo me-2"></i>Refresh
                    </button>
                    <button class="btn btn-ghost btn-sm" id="pwa-update-dismiss">
                        ✕
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(banner);
        
        setTimeout(() => {
            banner.classList.add('show');
        }, 100);
        
        document.getElementById('pwa-refresh-page').addEventListener('click', () => {
            window.location.reload();
        });
        
        document.getElementById('pwa-update-dismiss').addEventListener('click', () => {
            banner.classList.remove('show');
            setTimeout(() => banner.remove(), 300);
        });
    }
})();
