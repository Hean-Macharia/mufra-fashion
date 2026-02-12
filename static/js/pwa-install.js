/**
 * Service Worker Registration
 * Registers the service worker and handles PWA installation
 */

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/static/js/service-worker.js')
      .then((registration) => {
        console.log('✅ Service Worker registered:', registration);
        
        // Listen for updates
        registration.addEventListener('updatefound', () => {
          const newWorker = registration.installing;
          newWorker.addEventListener('statechange', () => {
            if (newWorker.state === 'activated') {
              // New service worker is ready
              console.log('✅ Service Worker updated');
              // Optionally notify user of update
              if (window.MufraApp && window.MufraApp.notify) {
                window.MufraApp.notify('info', 'App updated! Refresh to see changes.');
              }
            }
          });
        });
      })
      .catch((error) => {
        console.log('❌ Service Worker registration failed:', error);
      });
  });
}

// Handle PWA install prompt
let deferredPrompt;

window.addEventListener('beforeinstallprompt', (e) => {
  // Prevent the mini-infobar from appearing on mobile
  e.preventDefault();
  // Stash the event for later use
  deferredPrompt = e;
  
  // Show install button if it exists
  const installBtn = document.getElementById('pwa-install-btn');
  if (installBtn) {
    installBtn.style.display = 'block';
  }
  
  console.log('✅ PWA installation available');
});

// Install app when user clicks install button
document.addEventListener('DOMContentLoaded', () => {
  const installBtn = document.getElementById('pwa-install-btn');
  
  if (installBtn) {
    installBtn.addEventListener('click', async () => {
      if (deferredPrompt) {
        // Show the install prompt
        deferredPrompt.prompt();
        
        // Wait for user response
        const { outcome } = await deferredPrompt.userChoice;
        console.log(`User response to install prompt: ${outcome}`);
        
        // Clear the deferredPrompt for re-use
        deferredPrompt = null;
        installBtn.style.display = 'none';
      }
    });
  }
});

// Track app installation
window.addEventListener('appinstalled', () => {
  console.log('✅ MUFRA FASHIONS app installed!');
  // You can send analytics or perform other actions
});

// Detect if running as standalone app
if (window.navigator.standalone === true || window.matchMedia('(display-mode: standalone)').matches) {
  console.log('✅ Running as PWA standalone app');
  document.documentElement.setAttribute('data-pwa', 'true');
}

// Check for updates periodically
setInterval(() => {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.getRegistration()
      .then((registration) => {
        if (registration) {
          registration.update();
        }
      });
  }
}, 60000); // Check every minute
