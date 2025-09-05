// DOM elements
const textInput = document.getElementById('textInput');
const extractBtn = document.getElementById('extractBtn');
const loading = document.getElementById('loading');
const resultsSection = document.getElementById('resultsSection');
const resultsContent = document.getElementById('resultsContent');
const totalRuns = document.getElementById('totalRuns');
const successRate = document.getElementById('successRate');
const avgLatency = document.getElementById('avgLatency');

// Event listeners
extractBtn.addEventListener('click', handleExtract);
textInput.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.key === 'Enter') {
        handleExtract();
    }
});

// Load stats on page load
document.addEventListener('DOMContentLoaded', loadStats);

async function handleExtract() {
    const text = textInput.value.trim();
    
    if (!text) {
        alert('Please enter some text to extract.');
        return;
    }
    
    // Show loading state
    setLoading(true);
    hideResults();
    
    try {
        const response = await fetch('/api/extract', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ text })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        displayResults(result);
        await loadStats(); // Refresh stats after extraction
        
    } catch (error) {
        console.error('Extraction failed:', error);
        displayError('Extraction failed. Please try again.');
    } finally {
        setLoading(false);
    }
}

function displayResults(result) {
    const { data, valid, errors, latency_ms, est_cost_usd } = result;
    
    let html = `
        <div class="result-card">
            <div class="result-header">
                <h3>Extracted Data</h3>
                <span class="validity-badge ${valid ? 'valid' : 'invalid'}">
                    ${valid ? 'Valid' : 'Invalid'}
                </span>
            </div>
            
            <div class="metrics">
                <div class="metric">
                    <span>⏱️</span>
                    <span>${latency_ms}ms</span>
                </div>
                <div class="metric">
                    <span>💰</span>
                    <span>$${est_cost_usd.toFixed(4)}</span>
                </div>
            </div>
    `;
    
    if (data) {
        html += `
            <div class="data-grid">
                <div class="data-item">
                    <div class="data-label">Customer</div>
                    <div class="data-value">${escapeHtml(data.customer)}</div>
                </div>
                <div class="data-item">
                    <div class="data-label">Email</div>
                    <div class="data-value">${escapeHtml(data.email)}</div>
                </div>
                <div class="data-item">
                    <div class="data-label">Category</div>
                    <div class="data-value">
                        <span class="category-badge ${data.category}">${data.category}</span>
                    </div>
                </div>
                <div class="data-item">
                    <div class="data-label">Urgency</div>
                    <div class="data-value">
                        <span class="urgency-badge ${data.urgency}">${data.urgency}</span>
                    </div>
                </div>
                <div class="data-item" style="grid-column: 1 / -1;">
                    <div class="data-label">Summary</div>
                    <div class="data-value">${escapeHtml(data.summary)}</div>
                </div>
            </div>
        `;
    }
    
    if (errors && errors.length > 0) {
        html += `
            <div class="errors">
                <h4>Validation Errors:</h4>
                <ul class="error-list">
                    ${errors.map(error => `<li>${escapeHtml(error)}</li>`).join('')}
                </ul>
            </div>
        `;
    }
    
    html += '</div>';
    
    resultsContent.innerHTML = html;
    showResults();
}

function displayError(message) {
    resultsContent.innerHTML = `
        <div class="result-card">
            <div class="result-header">
                <h3>Error</h3>
                <span class="validity-badge invalid">Error</span>
            </div>
            <div class="errors">
                <h4>Extraction Failed</h4>
                <p>${escapeHtml(message)}</p>
            </div>
        </div>
    `;
    showResults();
}

async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        if (response.ok) {
            const stats = await response.json();
            updateStatsDisplay(stats);
        }
    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

function updateStatsDisplay(stats) {
    totalRuns.textContent = stats.runs;
    successRate.textContent = `${stats.success_rate_pct}%`;
    avgLatency.textContent = `${stats.avg_latency_ms}ms`;
}

function setLoading(isLoading) {
    if (isLoading) {
        loading.style.display = 'block';
        extractBtn.disabled = true;
        extractBtn.textContent = 'Processing...';
    } else {
        loading.style.display = 'none';
        extractBtn.disabled = false;
        extractBtn.textContent = 'Extract →';
    }
}

function showResults() {
    resultsSection.classList.remove('hidden');
    resultsSection.scrollIntoView({ behavior: 'smooth' });
}

function hideResults() {
    resultsSection.classList.add('hidden');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Auto-resize textarea
textInput.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = Math.max(150, this.scrollHeight) + 'px';
});

// Add some example text on double-click of placeholder
textInput.addEventListener('dblclick', function() {
    if (this.value === '') {
        this.value = `Hi, my name is John Doe and my email is john@example.com. I'm experiencing a bug where the application crashes when I click the submit button. This is urgent and needs immediate attention.`;
        this.dispatchEvent(new Event('input'));
    }
});