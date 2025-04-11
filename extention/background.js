document.addEventListener('DOMContentLoaded', function() {
  // Elements
  const urlInput = document.getElementById('url-input');
  const pasteBtn = document.getElementById('paste-btn');
  const useProxyCheck = document.getElementById('use-proxy');
  const proxyInput = document.getElementById('proxy-input');
  const processBtn = document.getElementById('process-btn');
  const rawMd = document.getElementById('raw-md');
  const processedContent = document.getElementById('processed-content');
  const statusBar = document.getElementById('status-bar');
  const tabBtns = document.querySelectorAll('.tab-btn');
  const tabContents = document.querySelectorAll('.tab-content');

  // Load saved proxy from storage
  chrome.storage.sync.get(['proxyUrl'], function(result) {
    if (result.proxyUrl) {
      proxyInput.value = result.proxyUrl;
      useProxyCheck.checked = true;
      proxyInput.disabled = false;
    }
  });

  // Toggle proxy input
  useProxyCheck.addEventListener('change', function() {
    proxyInput.disabled = !this.checked;
  });

  // Paste from clipboard
  pasteBtn.addEventListener('click', async function() {
    try {
      const text = await navigator.clipboard.readText();
      urlInput.value = text;
    } catch (err) {
      updateStatus('Failed to read clipboard', 'error');
    }
  });

  // Tab switching
  tabBtns.forEach(btn => {
    btn.addEventListener('click', function() {
      const tabId = this.getAttribute('data-tab');

      tabBtns.forEach(b => b.classList.remove('active'));
      tabContents.forEach(c => c.classList.remove('active'));

      this.classList.add('active');
      document.getElementById(tabId).classList.add('active');
    });
  });

  // Process listing
  processBtn.addEventListener('click', function() {
    const url = urlInput.value.trim();
    if (!url) {
      updateStatus('Please enter listing URL', 'error');
      return;
    }

    processBtn.disabled = true;
    updateStatus('Processing...');

    const options = {
      useProxy: useProxyCheck.checked,
      proxyUrl: proxyInput.value.trim()
    };

    // Save proxy to storage
    if (options.useProxy && options.proxyUrl) {
      chrome.storage.sync.set({ proxyUrl: options.proxyUrl });
    }

    // Send message to background script
    chrome.runtime.sendMessage(
      { action: 'processUrl', url, options },
      function(response) {
        if (response.error) {
          updateStatus(response.error, 'error');
          rawMd.value = response.error;
        } else {
          updateStatus('Completed successfully');
          rawMd.value = response.rawMd;
          processedContent.value = response.processedText;
        }
        processBtn.disabled = false;
      }
    );
  });

  function updateStatus(message, type = 'info') {
    statusBar.textContent = message;
    statusBar.style.color = type === 'error' ? '#ff6b6b' : 'white';
  }
});