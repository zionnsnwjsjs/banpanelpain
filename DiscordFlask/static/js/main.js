// Main JavaScript for Game Ban Manager

/**
 * Refresh the bans table
 */
function refreshBans() {
    const refreshButton = document.querySelector('button[onclick="refreshBans()"]');
    const originalContent = refreshButton.innerHTML;
    
    // Show loading state
    refreshButton.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Atualizando...';
    refreshButton.disabled = true;
    
    // Reload the page to refresh data
    setTimeout(() => {
        window.location.reload();
    }, 500);
}

/**
 * Show toast notification
 */
function showToast(message, type = 'info') {
    // Create toast container if it doesn't exist
    let toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
        toastContainer.style.zIndex = '1055';
        document.body.appendChild(toastContainer);
    }
    
    // Create toast element
    const toastId = 'toast-' + Date.now();
    const toastHtml = `
        <div id="${toastId}" class="toast" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="toast-header">
                <i class="fas fa-${type === 'success' ? 'check-circle text-success' : type === 'error' ? 'exclamation-triangle text-danger' : 'info-circle text-info'} me-2"></i>
                <strong class="me-auto">Sistema de Bans</strong>
                <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        </div>
    `;
    
    toastContainer.insertAdjacentHTML('beforeend', toastHtml);
    
    // Initialize and show toast
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement);
    toast.show();
    
    // Remove toast element after it's hidden
    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.remove();
    });
}

/**
 * Copy text to clipboard
 */
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast('Copiado para a área de transferência!', 'success');
    }).catch(() => {
        showToast('Falha ao copiar para área de transferência', 'error');
    });
}

/**
 * Format time remaining
 */
function formatTimeRemaining(timeString) {
    if (!timeString) return '';
    
    const parts = timeString.split(':');
    if (parts.length >= 3) {
        const hours = parseInt(parts[0]);
        const minutes = parseInt(parts[1]);
        
        if (hours > 0) {
            return `${hours}h ${minutes}m`;
        } else {
            return `${minutes}m`;
        }
    }
    return timeString;
}

/**
 * Add click-to-copy functionality and form validation
 */
document.addEventListener('DOMContentLoaded', function() {
    // Make player IDs clickable to copy
    document.querySelectorAll('code').forEach(code => {
        if (code.textContent.trim()) {
            code.style.cursor = 'pointer';
            code.title = 'Clique para copiar';
            code.addEventListener('click', function() {
                copyToClipboard(this.textContent);
            });
        }
    });
    
    // Form validation for player ID
    const playerIdInput = document.getElementById('player_id');
    if (playerIdInput) {
        playerIdInput.addEventListener('input', function() {
            const value = this.value.trim();
            
            if (value.length > 0) {
                this.setCustomValidity('');
                this.classList.remove('is-invalid');
                this.classList.add('is-valid');
            } else {
                this.setCustomValidity('ID do jogador é obrigatório');
                this.classList.add('is-invalid');
                this.classList.remove('is-valid');
            }
        });
    }
    
    // Reason textarea validation
    const reasonInput = document.getElementById('reason');
    if (reasonInput) {
        reasonInput.addEventListener('input', function() {
            const value = this.value.trim();
            
            if (value.length >= 10) {
                this.classList.remove('is-invalid');
                this.classList.add('is-valid');
            } else if (value.length > 0) {
                this.classList.add('is-invalid');
                this.classList.remove('is-valid');
            } else {
                this.classList.remove('is-invalid', 'is-valid');
            }
        });
    }
    
    // Auto-dismiss alerts after 5 seconds
    document.querySelectorAll('.alert').forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
    
    // Update time remaining for temporary bans every minute
    setInterval(updateTimeRemaining, 60000);
});

/**
 * Update time remaining displays
 */
function updateTimeRemaining() {
    document.querySelectorAll('[data-expires-at]').forEach(element => {
        const expiresAt = new Date(element.getAttribute('data-expires-at'));
        const now = new Date();
        const remaining = expiresAt - now;
        
        if (remaining <= 0) {
            element.textContent = 'Expirado';
            element.classList.add('text-muted');
        } else {
            const hours = Math.floor(remaining / (1000 * 60 * 60));
            const minutes = Math.floor((remaining % (1000 * 60 * 60)) / (1000 * 60));
            element.textContent = `${hours}h ${minutes}m`;
        }
    });
}

/**
 * API helper functions for game ban management
 */
const GameBanAPI = {
    baseUrl: window.location.origin,
    
    /**
     * Get all bans
     */
    async getAllBans() {
        try {
            const response = await fetch(`${this.baseUrl}/api/bans`);
            return await response.json();
        } catch (error) {
            console.error('Error fetching bans:', error);
            throw error;
        }
    },
    
    /**
     * Check if player is banned
     */
    async checkBan(playerId) {
        try {
            const response = await fetch(`${this.baseUrl}/api/bans/check/${encodeURIComponent(playerId)}`);
            return await response.json();
        } catch (error) {
            console.error('Error checking ban:', error);
            throw error;
        }
    },
    
    /**
     * Add a new ban
     */
    async addBan(playerId, playerName, reason, banType = 'permanent', expiresInHours = null) {
        try {
            const data = {
                player_id: playerId,
                player_name: playerName,
                reason: reason,
                ban_type: banType
            };
            
            if (banType === 'temporary' && expiresInHours) {
                data.expires_in_hours = expiresInHours;
            }
            
            const response = await fetch(`${this.baseUrl}/api/bans`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });
            return await response.json();
        } catch (error) {
            console.error('Error adding ban:', error);
            throw error;
        }
    },
    
    /**
     * Remove a ban
     */
    async removeBan(banId) {
        try {
            const response = await fetch(`${this.baseUrl}/api/bans/${banId}`, {
                method: 'DELETE'
            });
            return await response.json();
        } catch (error) {
            console.error('Error removing ban:', error);
            throw error;
        }
    }
};

// Make GameBanAPI globally available
window.GameBanAPI = GameBanAPI;

/**
 * Advanced search functionality
 */
async function searchPlayer() {
    const searchInput = document.getElementById('search_player');
    const searchResult = document.getElementById('search_result');
    const searchTerm = searchInput.value.trim();
    
    if (!searchTerm) {
        searchResult.innerHTML = '<div class="alert alert-warning">Digite um ID ou nome do jogador</div>';
        return;
    }
    
    searchResult.innerHTML = '<div class="text-center"><i class="fas fa-spinner fa-spin"></i> Buscando...</div>';
    
    try {
        const response = await GameBanAPI.checkBan(searchTerm);
        
        if (response.success) {
            if (response.is_banned) {
                const ban = response.ban_info;
                let statusBadge = ban.ban_type === 'permanent' ? 
                    '<span class="badge bg-danger">Permanente</span>' : 
                    '<span class="badge bg-warning">Temporário</span>';
                
                let expirationInfo = '';
                if (ban.expires_at) {
                    const expiresAt = new Date(ban.expires_at);
                    expirationInfo = `<br><strong>Expira:</strong> ${expiresAt.toLocaleString('pt-BR')}`;
                    
                    if (ban.time_remaining) {
                        expirationInfo += `<br><strong>Tempo restante:</strong> ${ban.time_remaining}`;
                    }
                }
                
                searchResult.innerHTML = `
                    <div class="alert alert-danger">
                        <h6><i class="fas fa-ban me-2"></i>Jogador Banido</h6>
                        <strong>Motivo:</strong> ${ban.reason}<br>
                        <strong>Tipo:</strong> ${statusBadge}<br>
                        <strong>Banido por:</strong> ${ban.banned_by}<br>
                        <strong>Data:</strong> ${new Date(ban.created_at).toLocaleString('pt-BR')}
                        ${expirationInfo}
                    </div>
                `;
            } else {
                searchResult.innerHTML = `
                    <div class="alert alert-success">
                        <i class="fas fa-check-circle me-2"></i>Jogador não está banido
                        <br><small class="text-muted">ID: ${searchTerm}</small>
                    </div>
                `;
            }
        } else {
            searchResult.innerHTML = `<div class="alert alert-danger">Erro: ${response.error}</div>`;
        }
    } catch (error) {
        searchResult.innerHTML = '<div class="alert alert-danger">Erro ao buscar jogador</div>';
    }
}

/**
 * Export bans functionality
 */
function exportBans() {
    showToast('Preparando exportação...', 'info');
    
    GameBanAPI.getAllBans().then(response => {
        if (response.success && response.bans) {
            const csvContent = generateCSV(response.bans);
            downloadCSV(csvContent, 'bans_export.csv');
            showToast('Bans exportados com sucesso!', 'success');
        } else {
            showToast('Erro ao exportar bans', 'error');
        }
    }).catch(error => {
        showToast('Erro ao exportar bans', 'error');
    });
}

/**
 * Generate CSV content from bans data
 */
function generateCSV(bans) {
    const headers = ['ID', 'Player ID', 'Player Name', 'Reason', 'Ban Type', 'Created At', 'Expires At', 'Banned By'];
    const rows = [headers.join(',')];
    
    bans.forEach(ban => {
        const row = [
            ban.id,
            `"${ban.player_id}"`,
            `"${ban.player_name || ''}"`,
            `"${ban.reason.replace(/"/g, '""')}"`,
            ban.ban_type,
            `"${new Date(ban.created_at).toLocaleString('pt-BR')}"`,
            ban.expires_at ? `"${new Date(ban.expires_at).toLocaleString('pt-BR')}"` : '',
            `"${ban.banned_by}"`
        ];
        rows.push(row.join(','));
    });
    
    return rows.join('\n');
}

/**
 * Download CSV file
 */
function downloadCSV(content, filename) {
    const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    
    if (link.download !== undefined) {
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', filename);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
}