// Global variables
let autoRefreshInterval;
let lastRefreshTime = null;

// DOM elements
const messagesTable = document.getElementById('messages-table');
const messagesTbody = document.getElementById('messages-tbody');
const loadingDiv = document.getElementById('loading');
const emptyStateDiv = document.getElementById('empty-state');
const errorContainer = document.getElementById('error-container');
const lastUpdatedSpan = document.getElementById('last-updated');
const autoRefreshStatusSpan = document.getElementById('auto-refresh-status');
const refreshBtn = document.getElementById('refresh-btn');

// Initialize the app
document.addEventListener('DOMContentLoaded', function() {
    console.log('VoiceTriage frontend initialized');
    refreshMessages();
    startAutoRefresh();
});

// Fetch and display messages
async function refreshMessages() {
    try {
        // Show loading state
        showLoading();
        hideError();
        
        // Disable refresh button during fetch
        refreshBtn.disabled = true;
        refreshBtn.textContent = '🔄 Loading...';
        
        // Fetch messages from API
        const response = await fetch('/api/messages');
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const messages = await response.json();
        
        // Update last refresh time
        lastRefreshTime = new Date();
        updateStatusDisplay();
        
        // Render messages
        if (messages.length === 0) {
            showEmptyState();
        } else {
            renderMessages(messages);
        }
        
        console.log(`Loaded ${messages.length} messages`);
        
    } catch (error) {
        console.error('Error fetching messages:', error);
        showError(`Failed to load messages: ${error.message}`);
        showEmptyState();
    } finally {
        // Re-enable refresh button
        refreshBtn.disabled = false;
        refreshBtn.textContent = '🔄 Refresh Now';
        hideLoading();
    }
}

// Render messages in the table
function renderMessages(messages) {
    // Clear existing content
    messagesTbody.innerHTML = '';
    
    // Create table rows for each message
    messages.forEach(message => {
        const row = document.createElement('tr');
        
        // Format timestamp
        const timestamp = new Date(message.created_at).toLocaleString();
        
        // Create category badge
        const categoryBadge = createBadge(message.category, 'category');
        
        // Create urgency badge
        const urgencyBadge = createBadge(message.urgency, 'urgency');
        
        // Set row content
        row.innerHTML = `
            <td>${timestamp}</td>
            <td>${escapeHtml(message.from_number)}</td>
            <td class="transcript" title="${escapeHtml(message.transcript)}">${escapeHtml(message.transcript)}</td>
            <td>${categoryBadge.outerHTML}</td>
            <td>${urgencyBadge.outerHTML}</td>
        `;
        
        messagesTbody.appendChild(row);
    });
    
    // Show table and hide empty state
    messagesTable.style.display = 'table';
    emptyStateDiv.style.display = 'none';
}

// Create a badge element
function createBadge(text, type) {
    const badge = document.createElement('span');
    badge.className = `${type}-badge ${type}-${text.toLowerCase()}`;
    badge.textContent = text;
    return badge;
}

// Show loading state
function showLoading() {
    loadingDiv.style.display = 'block';
    messagesTable.style.display = 'none';
    emptyStateDiv.style.display = 'none';
}

// Hide loading state
function hideLoading() {
    loadingDiv.style.display = 'none';
}

// Show empty state
function showEmptyState() {
    emptyStateDiv.style.display = 'block';
    messagesTable.style.display = 'none';
}

// Show error message
function showError(message) {
    errorContainer.innerHTML = `
        <div class="error">
            <strong>Error:</strong> ${escapeHtml(message)}
        </div>
    `;
    errorContainer.style.display = 'block';
}

// Hide error message
function hideError() {
    errorContainer.style.display = 'none';
}

// Update status display
function updateStatusDisplay() {
    if (lastRefreshTime) {
        lastUpdatedSpan.textContent = `Last updated: ${lastRefreshTime.toLocaleTimeString()}`;
    }
}

// Start auto-refresh
function startAutoRefresh() {
    // Clear any existing interval
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
    }
    
    // Set new interval (10 seconds)
    autoRefreshInterval = setInterval(() => {
        refreshMessages();
    }, 10000);
    
    console.log('Auto-refresh started (10 second interval)');
}

// Stop auto-refresh
function stopAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
        console.log('Auto-refresh stopped');
    }
}

// Utility function to escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Manual refresh function (called by button click)
function manualRefresh() {
    refreshMessages();
}

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    stopAutoRefresh();
});

// Handle visibility change (pause refresh when tab is hidden)
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        stopAutoRefresh();
        autoRefreshStatusSpan.textContent = 'Auto-refresh: Paused (tab hidden)';
    } else {
        startAutoRefresh();
        autoRefreshStatusSpan.textContent = 'Auto-refresh: 10s';
    }
});
