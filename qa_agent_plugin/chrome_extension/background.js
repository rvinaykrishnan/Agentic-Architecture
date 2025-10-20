// Background service worker
console.log('AI QA Agent background service worker initialized');

// Handle extension installation
chrome.runtime.onInstalled.addListener((details) => {
  if (details.reason === 'install') {
    console.log('AI QA Agent installed successfully!');
    
    // Open welcome page
    chrome.tabs.create({
      url: 'https://github.com'
    });
  }
});

// Handle messages from content scripts
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'backgroundTask') {
    // Handle background tasks here
    sendResponse({ status: 'success' });
  }
  return true;
});

// Keep service worker alive
setInterval(() => {
  console.log('Service worker heartbeat');
}, 20000);

