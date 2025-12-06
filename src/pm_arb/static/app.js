/**
 * Prediction Market Arbitrage Detector - Frontend Application
 */

const API_BASE = '/api';
let allPairs = [];
let allOpportunities = [];

// Initialize app
document.addEventListener('DOMContentLoaded', function() {
    setupEventListeners();
    loadInitialData();
    setupAutoRefresh();
});

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Tab navigation
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.addEventListener('click', function() {
            const tabName = this.dataset.tab;
            switchTab(tabName);
        });
    });

    // Refresh buttons
    document.getElementById('refresh-pairs').addEventListener('click', loadPairs);
    document.getElementById('refresh-opportunities').addEventListener('click', loadOpportunities);

    // Filters
    document.getElementById('search-filter').addEventListener('input', filterPairs);
    document.getElementById('confirmed-filter').addEventListener('change', filterPairs);

    // Modal close
    document.querySelector('.close').addEventListener('click', closeModal);
    window.addEventListener('click', function(event) {
        const modal = document.getElementById('pair-modal');
        if (event.target === modal) {
            closeModal();
        }
    });
}

/**
 * Switch between tabs
 */
function switchTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Deactivate all nav tabs
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Show selected tab
    document.getElementById(tabName + '-tab').classList.add('active');
    
    // Activate selected nav tab
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
    
    // Load data for tab if needed
    if (tabName === 'opportunities') {
        loadOpportunities();
    } else if (tabName === 'stats') {
        loadStats();
    }
}

/**
 * Load all initial data
 */
function loadInitialData() {
    loadPairs();
    loadStats();
}

/**
 * Setup auto-refresh
 */
function setupAutoRefresh() {
    // Refresh every 30 seconds
    setInterval(function() {
        if (document.querySelector('.nav-tab.active').dataset.tab === 'pairs') {
            loadPairs();
        }
    }, 30000);
}

/**
 * Load and display matched pairs
 */
function loadPairs() {
    const container = document.getElementById('pairs-container');
    container.innerHTML = '<div class="loading">Loading matched pairs...</div>';

    fetch(`${API_BASE}/pairs`)
        .then(response => {
            if (!response.ok) throw new Error('Failed to load pairs');
            return response.json();
        })
        .then(data => {
            allPairs = data.pairs || [];
            displayPairs(allPairs);
            updateHeaderStats();
        })
        .catch(error => {
            console.error('Error loading pairs:', error);
            container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">⚠️</div><p>Error loading pairs. Please try again.</p></div>';
        });
}

/**
 * Display pairs in the grid
 */
function displayPairs(pairs) {
    const container = document.getElementById('pairs-container');
    
    if (pairs.length === 0) {
        container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">🔍</div><p>No matched pairs found.</p></div>';
        return;
    }

    container.innerHTML = pairs.map(pair => `
        <div class="pair-card ${pair.is_manual_confirmed ? 'confirmed' : ''}" data-pair-id="${pair.id}">
            <div class="pair-header">
                <div class="pair-title">Market Pair #${pair.id}</div>
                ${pair.is_manual_confirmed ? '<span class="pair-badge badge-confirmed">✓ Confirmed</span>' : ''}
            </div>

            <div class="pair-markets">
                <div class="market-side">
                    <div class="market-label">Market A</div>
                    <div class="market-info">
                        <div class="market-source">${pair.source_a}</div>
                        <div class="market-id">ID: ${pair.market_id_a}</div>
                    </div>
                </div>
                <div style="text-align: center; padding: 10px; color: var(--text-light);">↔️</div>
                <div class="market-side">
                    <div class="market-label">Market B</div>
                    <div class="market-info">
                        <div class="market-source">${pair.source_b}</div>
                        <div class="market-id">ID: ${pair.market_id_b}</div>
                    </div>
                </div>
            </div>

            <div class="pair-metrics">
                <div class="metric-item">
                    <span class="metric-label">Similarity</span>
                    <span class="metric-value">${(pair.similarity * 100).toFixed(1)}%</span>
                </div>
                <div class="metric-item">
                    <span class="metric-label">Classifier</span>
                    <span class="metric-value">${(pair.classifier_probability * 100).toFixed(1)}%</span>
                </div>
                <div class="metric-item">
                    <span class="metric-label">Name Sim</span>
                    <span class="metric-value">${(pair.name_similarity * 100).toFixed(1)}%</span>
                </div>
                <div class="metric-item">
                    <span class="metric-label">Category</span>
                    <span class="metric-value">${(pair.category_similarity * 100).toFixed(1)}%</span>
                </div>
            </div>

            ${pair.notes ? `<div style="padding: 10px; background: var(--light); border-radius: 6px; margin-bottom: 15px; font-size: 0.9em; color: var(--text-light);"><strong>Notes:</strong> ${pair.notes}</div>` : ''}

            <div class="pair-actions">
                <button class="btn btn-primary btn-small" onclick="viewPairDetail(${pair.id})">👁️ View</button>
                ${!pair.is_manual_confirmed ? `<button class="btn btn-success btn-small" onclick="confirmPair(${pair.id})">✓ Confirm</button>` : ''}
                <button class="btn btn-danger btn-small" onclick="deletePair(${pair.id})">🗑️ Delete</button>
            </div>
        </div>
    `).join('');
}

/**
 * Filter pairs based on search and confirmed status
 */
function filterPairs() {
    const searchTerm = document.getElementById('search-filter').value.toLowerCase();
    const confirmedOnly = document.getElementById('confirmed-filter').checked;

    const filtered = allPairs.filter(pair => {
        const matchesSearch = !searchTerm || 
            pair.source_a.toLowerCase().includes(searchTerm) ||
            pair.source_b.toLowerCase().includes(searchTerm) ||
            pair.market_id_a.toLowerCase().includes(searchTerm) ||
            pair.market_id_b.toLowerCase().includes(searchTerm);
        
        const matchesConfirmed = !confirmedOnly || pair.is_manual_confirmed;
        
        return matchesSearch && matchesConfirmed;
    });

    displayPairs(filtered);
}

/**
 * View pair details in modal
 */
function viewPairDetail(pairId) {
    const pair = allPairs.find(p => p.id === pairId);
    if (!pair) return;

    const modal = document.getElementById('pair-modal');
    const modalBody = document.getElementById('modal-body');

    modalBody.innerHTML = `
        <h2>Pair #${pair.id} Details</h2>
        
        <div style="margin: 20px 0;">
            <h3>Markets</h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                <div>
                    <h4>Market A</h4>
                    <p><strong>Source:</strong> ${pair.source_a}</p>
                    <p><strong>ID:</strong> ${pair.market_id_a}</p>
                </div>
                <div>
                    <h4>Market B</h4>
                    <p><strong>Source:</strong> ${pair.source_b}</p>
                    <p><strong>ID:</strong> ${pair.market_id_b}</p>
                </div>
            </div>
        </div>

        <div style="margin: 20px 0;">
            <h3>Similarity Metrics</h3>
            <table style="width: 100%;">
                <tr><td>Overall Similarity:</td><td><strong>${(pair.similarity * 100).toFixed(2)}%</strong></td></tr>
                <tr><td>Name Similarity:</td><td><strong>${(pair.name_similarity * 100).toFixed(2)}%</strong></td></tr>
                <tr><td>Category Similarity:</td><td><strong>${(pair.category_similarity * 100).toFixed(2)}%</strong></td></tr>
                <tr><td>Temporal Proximity:</td><td><strong>${(pair.temporal_proximity * 100).toFixed(2)}%</strong></td></tr>
                <tr><td>Classifier Probability:</td><td><strong>${(pair.classifier_probability * 100).toFixed(2)}%</strong></td></tr>
            </table>
        </div>

        <div style="margin: 20px 0;">
            <h3>Status</h3>
            <p><strong>Confirmed:</strong> ${pair.is_manual_confirmed ? '✓ Yes' : '✗ No'}</p>
            ${pair.confirmed_by ? `<p><strong>Confirmed By:</strong> ${pair.confirmed_by}</p>` : ''}
            <p><strong>Created:</strong> ${new Date(pair.created_at).toLocaleString()}</p>
        </div>

        ${pair.notes ? `
            <div style="margin: 20px 0; padding: 15px; background: var(--light); border-radius: 6px;">
                <h3>Notes</h3>
                <p>${pair.notes}</p>
            </div>
        ` : ''}
    `;

    modal.style.display = 'block';
}

/**
 * Confirm a matched pair
 */
function confirmPair(pairId) {
    if (!confirm('Confirm this matched pair?')) return;

    fetch(`${API_BASE}/pairs/${pairId}/confirm`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ confirmed_by: 'user' })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            loadPairs();
            showNotification('✓ Pair confirmed successfully!', 'success');
        } else {
            showNotification('Error confirming pair: ' + data.error, 'error');
        }
    })
    .catch(error => {
        console.error('Error confirming pair:', error);
        showNotification('Error confirming pair', 'error');
    });
}

/**
 * Delete a matched pair
 */
function deletePair(pairId) {
    if (!confirm('Delete this pair? This action cannot be undone.')) return;

    fetch(`${API_BASE}/pairs/${pairId}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            loadPairs();
            showNotification('✓ Pair deleted successfully!', 'success');
        } else {
            showNotification('Error deleting pair: ' + data.error, 'error');
        }
    })
    .catch(error => {
        console.error('Error deleting pair:', error);
        showNotification('Error deleting pair', 'error');
    });
}

/**
 * Load and display arbitrage opportunities
 */
function loadOpportunities() {
    const container = document.getElementById('opportunities-container');
    container.innerHTML = '<div class="loading">Loading arbitrage opportunities...</div>';

    fetch(`${API_BASE}/arbitrage-opportunities`)
        .then(response => {
            if (!response.ok) throw new Error('Failed to load opportunities');
            return response.json();
        })
        .then(data => {
            allOpportunities = data.opportunities || [];
            displayOpportunities(allOpportunities);
        })
        .catch(error => {
            console.error('Error loading opportunities:', error);
            container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">⚠️</div><p>Error loading opportunities. Please try again.</p></div>';
        });
}

/**
 * Display arbitrage opportunities
 */
function displayOpportunities(opportunities) {
    const container = document.getElementById('opportunities-container');
    
    if (opportunities.length === 0) {
        container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">💼</div><p>No arbitrage opportunities found at this time.</p></div>';
        return;
    }

    container.innerHTML = opportunities.map(opp => `
        <div class="opportunity-card">
            <div class="opportunity-header">
                <div class="opportunity-title">💰 Arbitrage Opportunity</div>
                <span style="font-size: 1.4em; font-weight: bold; color: var(--success);">${(opp.potential_profit * 100).toFixed(2)}%</span>
            </div>

            <div class="opportunity-details">
                <div class="detail-box">
                    <div class="detail-label">Market A</div>
                    <div class="detail-value" style="font-size: 0.9em;">${opp.source_a}</div>
                    <div style="font-size: 0.8em; color: var(--text-light); margin-top: 5px;">${opp.market_id_a}</div>
                </div>

                <div class="detail-box">
                    <div class="detail-label">Market B</div>
                    <div class="detail-value" style="font-size: 0.9em;">${opp.source_b}</div>
                    <div style="font-size: 0.8em; color: var(--text-light); margin-top: 5px;">${opp.market_id_b}</div>
                </div>

                <div class="detail-box">
                    <div class="detail-label">Potential Profit</div>
                    <div class="detail-value">$${(opp.potential_profit).toFixed(2)}</div>
                </div>

                <div class="detail-box">
                    <div class="detail-label">ROI</div>
                    <div class="detail-value">${(opp.roi * 100).toFixed(1)}%</div>
                </div>

                <div class="detail-box">
                    <div class="detail-label">Confidence</div>
                    <div class="detail-value">${(opp.confidence * 100).toFixed(1)}%</div>
                </div>
            </div>

            <div style="padding: 15px; background: rgba(16, 185, 129, 0.1); border-radius: 6px;">
                <strong>Strategy:</strong> ${opp.strategy}
            </div>
        </div>
    `).join('');
}

/**
 * Load and display statistics
 */
function loadStats() {
    fetch(`${API_BASE}/stats`)
        .then(response => {
            if (!response.ok) throw new Error('Failed to load stats');
            return response.json();
        })
        .then(data => {
            if (data.success) {
                displayStats(data.stats);
            }
        })
        .catch(error => {
            console.error('Error loading stats:', error);
        });
}

/**
 * Display statistics
 */
function displayStats(stats) {
    // Update header stats
    document.getElementById('stat-total').textContent = stats.total_pairs;
    document.getElementById('stat-confirmed').textContent = stats.confirmed_pairs;

    // Update stats tab
    document.querySelector('#stats-similarity .metric:first-child .metric-value').textContent = 
        (stats.avg_similarity * 100).toFixed(2) + '%';
    document.querySelector('#stats-similarity .metric:last-child .metric-value').textContent = 
        (stats.avg_classifier_probability * 100).toFixed(2) + '%';

    document.querySelector('#stats-status .metric:nth-child(1) .metric-value').textContent = 
        stats.total_pairs;
    document.querySelector('#stats-status .metric:nth-child(2) .metric-value').textContent = 
        stats.confirmed_pairs;
    document.querySelector('#stats-status .metric:nth-child(3) .metric-value').textContent = 
        stats.unconfirmed_pairs;

    document.getElementById('update-time').textContent = 
        new Date(stats.timestamp).toLocaleString();
}

/**
 * Update header statistics
 */
function updateHeaderStats() {
    const confirmed = allPairs.filter(p => p.is_manual_confirmed).length;
    document.getElementById('stat-total').textContent = allPairs.length;
    document.getElementById('stat-confirmed').textContent = confirmed;
}

/**
 * Close modal
 */
function closeModal() {
    document.getElementById('pair-modal').style.display = 'none';
}

/**
 * Show notification (toast)
 */
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        border-radius: 6px;
        color: white;
        font-weight: 500;
        z-index: 2000;
        animation: slideIn 0.3s ease;
        ${type === 'success' ? 'background: var(--success);' : ''}
        ${type === 'error' ? 'background: var(--danger);' : ''}
        ${type === 'info' ? 'background: var(--primary);' : ''}
    `;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    // Remove after 4 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 4000);
}

// Add animation styles for notifications
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);
