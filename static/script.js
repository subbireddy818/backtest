document.addEventListener('DOMContentLoaded', () => {
    const strategySelect = document.getElementById('strategySelect');
    const symbolInput = document.getElementById('symbolInput');
    const startDateInput = document.getElementById('startDate');
    const endDateInput = document.getElementById('endDate');
    const runBtn = document.getElementById('runBtn');
    const btnIcon = document.getElementById('btnIcon');
    const btnText = document.getElementById('btnText');
    const loader = document.getElementById('loader');
    const intervalButtons = document.querySelectorAll('.interval-btn');
    
    let currentInterval = '5m'; // Default 5m based on UI active state

    // Initialize dates
    const today = new Date();
    const fiveDaysAgo = new Date(today);
    fiveDaysAgo.setDate(today.getDate() - 5);
    
    const formatDate = (date) => date.toISOString().split('T')[0];
    startDateInput.value = formatDate(fiveDaysAgo);
    endDateInput.value = formatDate(today);

    // Global Date Picker Trigger
    [startDateInput, endDateInput].forEach(input => {
        input.addEventListener('click', () => {
            if (input.showPicker) {
                input.showPicker();
            }
        });
    });

    // Timeframe Toggle logic
    intervalButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            intervalButtons.forEach(b => b.classList.remove('bg-surface-container-highest', 'text-primary', 'font-bold'));
            btn.classList.add('bg-surface-container-highest', 'text-primary', 'font-bold');
            currentInterval = btn.dataset.interval;
        });
    });

    // Run Backtest
    runBtn.addEventListener('click', async () => {
        const payload = {
            strategy: strategySelect.value,
            symbol: symbolInput.value.trim(),
            interval: currentInterval,
            start_date: startDateInput.value,
            end_date: endDateInput.value
        };

        if (!payload.symbol) {
            showToast('Please enter a symbol.');
            return;
        }

        // Loading State
        runBtn.disabled = true;
        btnIcon.classList.add('hidden');
        btnText.textContent = 'Processing...';
        loader.classList.remove('hidden');

        try {
            const response = await fetch('/backtest', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            
            const data = await response.json();
            
            if (!response.ok || data.error) {
                showToast(data.error || 'Backtest failed.');
            } else {
                updateUI(data);
            }
        } catch (error) {
            showToast('Network error occurred.');
            console.error(error);
        } finally {
            runBtn.disabled = false;
            btnIcon.classList.remove('hidden');
            btnText.textContent = 'Run Backtest';
            loader.classList.add('hidden');
        }
    });
});

function updateUI(data) {
    // 1. Update Metrics
    document.getElementById('metric-trades').textContent = data.total_trades;
    
    const pnlEl = document.getElementById('metric-pnl');
    pnlEl.textContent = (data.total_pnl >= 0 ? '+' : '') + data.total_pnl.toFixed(2);
    pnlEl.className = 'text-3xl font-bold data-font ' + (data.total_pnl >= 0 ? 'text-primary' : 'text-secondary');

    document.getElementById('metric-winrate').textContent = data.win_rate.toFixed(1) + '%';
    
    // Find Best Trade
    let bestTradeVal = 0;
    if (data.trades && data.trades.length > 0) {
        bestTradeVal = Math.max(...data.trades.map(t => t.pnl));
    }
    document.getElementById('metric-best').textContent = (bestTradeVal >= 0 ? '+' : '') + bestTradeVal.toFixed(2);

    // 2. Update Table
    const tbody = document.getElementById('tradeBody');
    tbody.innerHTML = '';

    if (!data.trades || data.trades.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="py-20 text-center text-on-surface/30">No trades found for this period.</td></tr>';
        return;
    }

    data.trades.forEach((trade, index) => {
        const tr = document.createElement('tr');
        tr.className = `group hover:bg-surface-bright transition-colors cursor-default ${index % 2 === 1 ? 'bg-surface-container-low' : ''}`;
        
        const pnlClass = trade.pnl >= 0 ? 'text-primary' : 'text-secondary';
        const pnlIcon = trade.pnl >= 0 ? 'arrow_upward' : 'arrow_downward';
        const badgeClass = trade.strong_entry ? 'bg-primary-container text-on-primary-container' : 'bg-on-surface/10 text-on-surface/60';
        const badgeText = trade.strong_entry ? 'Strong Entry' : 'Manual/Reg';

        tr.innerHTML = `
            <td class="px-8 py-4 text-on-surface/80">${trade.entry_time}</td>
            <td class="px-8 py-4 text-on-surface/80">${trade.exit_time}</td>
            <td class="px-8 py-4">
                <div class="flex flex-col gap-0.5">
                    <span class="font-bold">${trade.entry_price.toFixed(2)}</span>
                    <span class="text-on-surface/40">${trade.exit_price.toFixed(2)}</span>
                </div>
            </td>
            <td class="px-8 py-4">
                <span class="px-2 py-0.5 bg-primary/10 text-primary rounded-full text-[10px] font-bold">${trade.entry_rsi || '--'}</span> / 
                <span class="text-on-surface/60">${trade.exit_rsi || '--'}</span>
            </td>
            <td class="px-8 py-4 text-on-surface/60">${trade.duration_formatted || '--'}</td>
            <td class="px-8 py-4 ${pnlClass}">
                <div class="flex items-center gap-1 font-bold">
                    <span class="material-symbols-outlined text-sm">${pnlIcon}</span>
                    ${(trade.pnl >= 0 ? '+' : '')}${trade.pnl.toFixed(2)}
                </div>
            </td>
            <td class="px-8 py-4">
                <div class="flex flex-col items-start gap-1">
                    <span class="px-3 py-1 ${badgeClass} rounded text-[9px] font-bold uppercase tracking-tighter">${badgeText}</span>
                    <span class="text-[10px] opacity-40">${trade.exit_reason}</span>
                </div>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function showToast(message) {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.classList.remove('hidden');
    setTimeout(() => toast.classList.add('hidden'), 4000);
}
