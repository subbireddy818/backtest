document.addEventListener('DOMContentLoaded', () => {
    // Set default dates to last 5 days
    const endDateInput = document.getElementById('end_date');
    const startDateInput = document.getElementById('start_date');
    
    const today = new Date();
    const fiveDaysAgo = new Date(today);
    fiveDaysAgo.setDate(today.getDate() - 5);
    
    // Format YYYY-MM-DD
    const formatDate = (date) => {
        const d = new Date(date);
        let month = '' + (d.getMonth() + 1);
        let day = '' + d.getDate();
        const year = d.getFullYear();

        if (month.length < 2) month = '0' + month;
        if (day.length < 2) day = '0' + day;

        return [year, month, day].join('-');
    };

    endDateInput.value = formatDate(today);
    startDateInput.value = formatDate(fiveDaysAgo);
    
    // Form submission handling
    const form = document.getElementById('backtestForm');
    const btnText = document.getElementById('btnText');
    const loader = document.getElementById('loader');
    const submitBtn = document.getElementById('runBtn');
    
    form.addEventListener('submit', async (e) => {
        e.preventDefault(); // Prevent reload
        
        // UI Loading State
        submitBtn.disabled = true;
        btnText.textContent = 'Processing...';
        loader.classList.remove('hidden');
        
        const payload = {
            strategy: document.getElementById('strategy').value,
            symbol: document.getElementById('symbol').value,
            start_date: startDateInput.value,
            end_date: endDateInput.value
        };
        
        try {
            const response = await fetch('/backtest', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });
            
            const data = await response.json();
            
            if (!response.ok || data.error) {
                showToast(data.error || 'Failed to run backtest.');
            } else {
                updateUI(data);
            }
            
        } catch (error) {
            showToast('Network error occurred.');
            console.error(error);
        } finally {
            // Restore UI State
            submitBtn.disabled = false;
            btnText.textContent = 'Run Backtest';
            loader.classList.add('hidden');
        }
    });
});

function updateUI(data) {
    // Update Summary Cards
    const pnlEl = document.getElementById('val-pnl');
    pnlEl.textContent = data.total_pnl.toFixed(2);
    pnlEl.className = 'val ' + (data.total_pnl >= 0 ? 'text-profit' : 'text-loss');
    
    document.getElementById('val-winrate').textContent = data.win_rate.toFixed(1) + '%';
    document.getElementById('val-trades').textContent = data.total_trades;
    
    // Update Table
    const tbody = document.getElementById('tradesBody');
    tbody.innerHTML = '';
    
    if (data.trades && data.trades.length > 0) {
        data.trades.forEach(trade => {
            const tr = document.createElement('tr');
            
            const pnlClass = trade.pnl >= 0 ? 'text-profit' : 'text-loss';
            const sign = trade.pnl >= 0 ? '+' : '';
            
            const strongBadge = trade.strong_entry ? '<span class="badge-strong">Strong</span>' : '<span class="badge-reg">Reg</span>';
            const rsiInfo = trade.entry_rsi ? `${trade.entry_rsi} / ${trade.exit_rsi}` : '--';
            
            tr.innerHTML = `
                <td>${trade.entry_time}</td>
                <td>${trade.exit_time}</td>
                <td>${trade.entry_rsi ? strongBadge : '--'}</td>
                <td>${trade.entry_price.toFixed(2)}</td>
                <td>${trade.exit_price.toFixed(2)}</td>
                <td>${rsiInfo}</td>
                <td style="font-family: monospace;">${trade.duration_formatted || '--'}</td>
                <td class="${pnlClass}">${sign}${trade.pnl.toFixed(2)}</td>
                <td style="font-size: 0.85em; opacity: 0.8;">${trade.exit_reason}</td>
            `;
            tbody.appendChild(tr);
        });
    } else {
        tbody.innerHTML = '<tr><td colspan="9" class="empty-state">No trades executed in this period.</td></tr>';
    }
}

function showToast(message) {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.classList.remove('hidden');
    
    setTimeout(() => {
        toast.classList.add('hidden');
    }, 4000);
}
