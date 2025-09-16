// Balans AI - Premium JavaScript Application

class BalansAI {
    constructor() {
        this.currentUser = null;
        this.currentTab = 'dashboard';
        this.data = {
            transactions: [],
            statistics: null
        };
        this.charts = {
            monthly: null,
            category: null,
            yearly: null
        };
        this.currentFilter = 'all';
        
        this.init();
    }

    async init() {
        // Telegram WebApp sozlash
        if (window.Telegram && window.Telegram.WebApp) {
            const tg = window.Telegram.WebApp;
            tg.ready();
            tg.expand();
            tg.enableClosingConfirmation();
            
            // Full screen rejimi
            tg.setHeaderColor('#2481cc');
            tg.setBackgroundColor('#ffffff');
            
            // Foydalanuvchi ma'lumotlari
            if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
                this.currentUser = tg.initDataUnsafe.user;
                this.updateUserInfo();
            } else {
                // Test uchun
                this.currentUser = { id: 123456789, first_name: 'Test User' };
                this.updateUserInfo();
            }
            
            // Tema sozlash
            this.setTheme(tg.colorScheme || 'light');
            
            // Telegram tugmalarni yashirish
            tg.MainButton.hide();
            tg.BackButton.hide();
        } else {
            // Test rejimi
            this.currentUser = { id: 123456789, first_name: 'Test User' };
            this.updateUserInfo();
            console.log('Telegram WebApp mavjud emas, test rejimida ishlayapti');
        }

        this.setupEventListeners();
        await this.loadAllData();
    }

    updateUserInfo() {
        if (this.currentUser) {
            document.getElementById('userName').textContent = 
                this.currentUser.first_name || 'Foydalanuvchi';
            
            // Avatar
            const avatar = document.getElementById('userAvatar');
            if (this.currentUser.first_name) {
                avatar.textContent = this.currentUser.first_name.charAt(0).toUpperCase();
            }
        }
    }

    setTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        
        // Chart.js uchun rang sozlamalari
        this.chartColors = {
            income: theme === 'dark' ? '#10b981' : '#10b981',
            expense: theme === 'dark' ? '#ef4444' : '#ef4444',
            debt: theme === 'dark' ? '#f59e0b' : '#f59e0b',
            text: theme === 'dark' ? '#ffffff' : '#000000',
            grid: theme === 'dark' ? '#374151' : '#e5e7eb'
        };
    }

    setupEventListeners() {
        // Tab navigation
        document.querySelectorAll('.nav-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                const tabName = e.target.closest('.nav-tab').dataset.tab;
                this.switchTab(tabName);
            });
        });

        // Filter buttons
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const filter = e.target.dataset.filter;
                this.setFilter(filter);
            });
        });

        // Transaction type selector
        document.querySelectorAll('.type-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const type = e.target.closest('.type-btn').dataset.type;
                this.selectTransactionType(type);
            });
        });

        // Form submission
        document.getElementById('addTransactionForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.addTransaction();
        });

        // Modal close events
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.closeModal(modal.id);
                }
            });
        });

        // Haptic feedback for buttons (Telegram WebApp)
        document.addEventListener('click', (e) => {
            if (e.target.closest('button') && window.Telegram?.WebApp) {
                window.Telegram.WebApp.HapticFeedback.impactOccurred('light');
            }
        });
    }

    switchTab(tabName) {
        // Update active tab
        document.querySelectorAll('.nav-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

        // Show corresponding content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(tabName).classList.add('active');

        this.currentTab = tabName;
        this.renderCurrentTab();
    }

    setFilter(filter) {
        this.currentFilter = filter;
        
        // Update filter buttons
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-filter="${filter}"]`).classList.add('active');
        
        this.renderTransactions();
    }

    async loadAllData() {
        if (!this.currentUser) return;

        try {
            this.showLoading();
            
            // Ma'lumotlarni parallel yuklash
            const [transactions, statistics] = await Promise.all([
                this.fetchData(`/api/transactions/${this.currentUser.id}`),
                this.fetchData(`/api/statistics/${this.currentUser.id}`)
            ]);

            this.data.transactions = transactions || [];
            this.data.statistics = statistics || this.getEmptyStatistics();

            this.hideLoading();
            this.renderCurrentTab();
        } catch (error) {
            console.error('Ma\'lumotlarni yuklashda xatolik:', error);
            this.showNotification('Ma\'lumotlarni yuklashda xatolik yuz berdi', 'error');
            this.hideLoading();
        }
    }

    async fetchData(url) {
        try {
            const response = await fetch(url);
            const result = await response.json();
            return result.success ? result.data : null;
        } catch (error) {
            console.error(`API so'rov xatoligi (${url}):`, error);
            return null;
        }
    }

    getEmptyStatistics() {
        return {
            total_income: 0,
            total_expense: 0,
            total_debt: 0,
            balance: 0,
            monthly_data: [],
            category_data: [],
            recent_transactions: []
        };
    }

    renderCurrentTab() {
        switch (this.currentTab) {
            case 'dashboard':
                this.renderDashboard();
                break;
            case 'transactions':
                this.renderTransactions();
                break;
            case 'debts':
                this.renderDebts();
                break;
            case 'analytics':
                this.renderAnalytics();
                break;
        }
    }

    renderDashboard() {
        if (!this.data.statistics) return;

        const stats = this.data.statistics;

        // Main balance
        document.getElementById('mainBalance').textContent = 
            this.formatCurrency(stats.balance);

        // Quick stats
        document.getElementById('totalIncomeQuick').textContent = 
            this.formatNumber(stats.total_income);
        document.getElementById('totalExpenseQuick').textContent = 
            this.formatNumber(stats.total_expense);
        document.getElementById('totalDebtQuick').textContent = 
            this.formatNumber(stats.total_debt);

        // Recent transactions
        this.renderRecentTransactions(stats.recent_transactions);

        // Charts
        this.renderDashboardCharts();
    }

    renderRecentTransactions(transactions) {
        const container = document.getElementById('recentTransactions');
        
        if (!transactions || transactions.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">💰</div>
                    <p>Hozircha tranzaksiyalar yo'q</p>
                </div>
            `;
            return;
        }

        container.innerHTML = transactions.slice(0, 5).map(transaction => `
            <div class="data-item">
                <div class="item-header">
                    <div class="item-title">${this.escapeHtml(transaction.description || transaction.category)}</div>
                    <div class="item-amount ${transaction.transaction_type}">
                        ${transaction.transaction_type === 'expense' ? '-' : '+'}${this.formatCurrency(transaction.amount)}
                    </div>
                </div>
                <div class="item-meta">
                    <span class="item-category">${this.escapeHtml(transaction.category)}</span>
                    <span>${this.formatDate(transaction.created_at)}</span>
                </div>
            </div>
        `).join('');
    }

    renderTransactions() {
        const container = document.getElementById('transactionsList');
        let transactions = this.data.transactions;

        // Filter bo'yicha saralash
        if (this.currentFilter !== 'all') {
            transactions = transactions.filter(t => t.transaction_type === this.currentFilter);
        }

        if (!transactions || transactions.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">💰</div>
                    <p>Bu filtr bo'yicha tranzaksiyalar topilmadi</p>
                </div>
            `;
            return;
        }

        container.innerHTML = transactions.map(transaction => `
            <div class="data-item">
                <div class="item-header">
                    <div class="item-title">${this.escapeHtml(transaction.description || transaction.category)}</div>
                    <div class="item-amount ${transaction.transaction_type}">
                        ${transaction.transaction_type === 'expense' ? '-' : '+'}${this.formatCurrency(transaction.amount)}
                    </div>
                </div>
                ${transaction.description ? `<div class="item-description">${this.escapeHtml(transaction.description)}</div>` : ''}
                <div class="item-meta">
                    <span class="item-category">${this.escapeHtml(transaction.category)}</span>
                    <span>${this.formatDate(transaction.created_at)}</span>
                </div>
                <div class="item-actions">
                    <button class="btn-secondary btn-small" onclick="app.editTransaction(${transaction.id})">
                        ✏️ Tahrirlash
                    </button>
                    <button class="btn-danger btn-small" onclick="app.deleteTransaction(${transaction.id})">
                        🗑️ O'chirish
                    </button>
                </div>
            </div>
        `).join('');
    }

    renderDebts() {
        const debts = this.data.transactions.filter(t => t.transaction_type === 'debt');
        const totalDebt = debts.reduce((sum, debt) => sum + parseFloat(debt.amount), 0);
        
        document.getElementById('totalDebtAmount').textContent = this.formatCurrency(totalDebt);

        const container = document.getElementById('debtsList');
        
        if (debts.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">🏦</div>
                    <p>Qarzlar yo'q</p>
                </div>
            `;
            return;
        }

        container.innerHTML = debts.map(debt => `
            <div class="data-item">
                <div class="item-header">
                    <div class="item-title">${this.escapeHtml(debt.description || debt.category)}</div>
                    <div class="item-amount debt">${this.formatCurrency(debt.amount)}</div>
                </div>
                ${debt.description ? `<div class="item-description">${this.escapeHtml(debt.description)}</div>` : ''}
                <div class="item-meta">
                    <span class="item-category">${this.escapeHtml(debt.category)}</span>
                    <span>${this.formatDate(debt.created_at)}</span>
                </div>
                <div class="item-actions">
                    <button class="btn-secondary btn-small" onclick="app.editTransaction(${debt.id})">
                        ✏️ Tahrirlash
                    </button>
                    <button class="btn-danger btn-small" onclick="app.deleteTransaction(${debt.id})">
                        🗑️ O'chirish
                    </button>
                </div>
            </div>
        `).join('');
    }

    renderAnalytics() {
        if (!this.data.statistics) return;

        const stats = this.data.statistics;

        // Analytics cards
        if (stats.category_data && stats.category_data.length > 0) {
            const maxIncomeCategory = stats.category_data.reduce((max, cat) => 
                cat.income > max.income ? cat : max, stats.category_data[0]);
            const maxExpenseCategory = stats.category_data.reduce((max, cat) => 
                cat.expense > max.expense ? cat : max, stats.category_data[0]);

            document.getElementById('maxIncomeCategory').textContent = 
                `${maxIncomeCategory.category} (${this.formatCurrency(maxIncomeCategory.income)})`;
            document.getElementById('maxExpenseCategory').textContent = 
                `${maxExpenseCategory.category} (${this.formatCurrency(maxExpenseCategory.expense)})`;
        }

        // O'rtacha hisoblar
        const transactionCount = this.data.transactions.length;
        if (transactionCount > 0) {
            document.getElementById('avgIncome').textContent = 
                this.formatCurrency(stats.total_income / transactionCount);
            document.getElementById('avgExpense').textContent = 
                this.formatCurrency(stats.total_expense / transactionCount);
        }

        // Yillik chart
        this.renderYearlyChart();
    }

    renderDashboardCharts() {
        this.renderMonthlyChart();
        this.renderCategoryChart();
    }

    renderMonthlyChart() {
        const ctx = document.getElementById('monthlyChart');
        if (!ctx || !this.data.statistics) return;

        if (this.charts.monthly) {
            this.charts.monthly.destroy();
        }

        const monthlyData = this.data.statistics.monthly_data || [];
        
        this.charts.monthly = new Chart(ctx, {
            type: 'line',
            data: {
                labels: monthlyData.map(d => this.formatMonth(d.month)),
                datasets: [
                    {
                        label: 'Daromad',
                        data: monthlyData.map(d => d.income),
                        borderColor: this.chartColors.income,
                        backgroundColor: this.chartColors.income + '20',
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: 'Xarajat',
                        data: monthlyData.map(d => d.expense),
                        borderColor: this.chartColors.expense,
                        backgroundColor: this.chartColors.expense + '20',
                        tension: 0.4,
                        fill: true
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: value => this.formatNumber(value)
                        }
                    }
                }
            }
        });
    }

    renderCategoryChart() {
        const ctx = document.getElementById('categoryChart');
        if (!ctx || !this.data.statistics) return;

        if (this.charts.category) {
            this.charts.category.destroy();
        }

        const categoryData = this.data.statistics.category_data || [];
        const topCategories = categoryData
            .sort((a, b) => b.total - a.total)
            .slice(0, 5);

        this.charts.category = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: topCategories.map(c => c.category),
                datasets: [{
                    data: topCategories.map(c => c.total),
                    backgroundColor: [
                        this.chartColors.income,
                        this.chartColors.expense,
                        this.chartColors.debt,
                        '#8b5cf6',
                        '#06b6d4'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }

    renderYearlyChart() {
        const ctx = document.getElementById('yearlyChart');
        if (!ctx || !this.data.statistics) return;

        if (this.charts.yearly) {
            this.charts.yearly.destroy();
        }

        const monthlyData = this.data.statistics.monthly_data || [];
        
        this.charts.yearly = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: monthlyData.map(d => this.formatMonth(d.month)),
                datasets: [
                    {
                        label: 'Daromad',
                        data: monthlyData.map(d => d.income),
                        backgroundColor: this.chartColors.income
                    },
                    {
                        label: 'Xarajat',
                        data: monthlyData.map(d => d.expense),
                        backgroundColor: this.chartColors.expense
                    },
                    {
                        label: 'Qarz',
                        data: monthlyData.map(d => d.debt),
                        backgroundColor: this.chartColors.debt
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: value => this.formatNumber(value)
                        }
                    }
                }
            }
        });
    }

    selectTransactionType(type) {
        document.querySelectorAll('.type-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-type="${type}"]`).classList.add('active');
        document.getElementById('transactionType').value = type;

        // Modal title ni yangilash
        const titles = {
            income: '📈 Daromad qo\'shish',
            expense: '📉 Xarajat qo\'shish',
            debt: '🏦 Qarz qo\'shish'
        };
        document.getElementById('transactionModalTitle').textContent = titles[type] || '💰 Tranzaksiya qo\'shish';
    }

    // Modal functions
    showModal(modalId) {
        document.getElementById(modalId).classList.add('show');
        document.body.style.overflow = 'hidden';
    }

    closeModal(modalId) {
        document.getElementById(modalId).classList.remove('show');
        document.body.style.overflow = '';
        
        // Formalarni tozalash
        const form = document.querySelector(`#${modalId} form`);
        if (form) {
            form.reset();
            // Type selector ni reset qilish
            document.querySelectorAll('.type-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            document.getElementById('transactionType').value = '';
        }
    }

    // CRUD Operations
    async addTransaction() {
        const type = document.getElementById('transactionType').value;
        if (!type) {
            this.showNotification('Iltimos, tranzaksiya turini tanlang', 'warning');
            return;
        }

        const data = {
            user_id: this.currentUser.id,
            amount: parseFloat(document.getElementById('transactionAmount').value),
            category: document.getElementById('transactionCategory').value,
            description: document.getElementById('transactionDescription').value,
            transaction_type: type
        };

        try {
            const response = await fetch('/api/transactions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            const result = await response.json();
            if (result.success) {
                this.closeModal('addTransactionModal');
                await this.loadAllData();
                this.showNotification('Tranzaksiya qo\'shildi', 'success');
                
                // Haptic feedback
                if (window.Telegram?.WebApp) {
                    window.Telegram.WebApp.HapticFeedback.notificationOccurred('success');
                }
            } else {
                this.showNotification(result.message, 'error');
            }
        } catch (error) {
            this.showNotification('Xatolik yuz berdi', 'error');
        }
    }

    async deleteTransaction(id) {
        if (!await this.confirmAction('Tranzaksiyani o\'chirmoqchimisiz?')) return;

        try {
            const response = await fetch(`/api/transactions/${id}`, { method: 'DELETE' });
            const result = await response.json();
            
            if (result.success) {
                await this.loadAllData();
                this.showNotification('Tranzaksiya o\'chirildi', 'success');
                
                if (window.Telegram?.WebApp) {
                    window.Telegram.WebApp.HapticFeedback.notificationOccurred('success');
                }
            } else {
                this.showNotification(result.message, 'error');
            }
        } catch (error) {
            this.showNotification('Xatolik yuz berdi', 'error');
        }
    }

    // Utility functions
    formatCurrency(amount) {
        return new Intl.NumberFormat('uz-UZ').format(amount) + ' so\'m';
    }

    formatNumber(num) {
        return new Intl.NumberFormat('uz-UZ').format(num);
    }

    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('uz-UZ', {
            day: 'numeric',
            month: 'short',
            year: 'numeric'
        });
    }

    formatMonth(monthString) {
        const [year, month] = monthString.split('-');
        const date = new Date(year, month - 1);
        return date.toLocaleDateString('uz-UZ', {
            month: 'short',
            year: 'numeric'
        });
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showNotification(message, type = 'info') {
        if (window.Telegram && window.Telegram.WebApp) {
            window.Telegram.WebApp.showAlert(message);
        } else {
            alert(message);
        }
    }

    async confirmAction(message) {
        if (window.Telegram && window.Telegram.WebApp) {
            return new Promise((resolve) => {
                window.Telegram.WebApp.showConfirm(message, resolve);
            });
        } else {
            return confirm(message);
        }
    }

    showLoading() {
        // Loading indikatorini ko'rsatish
        document.querySelectorAll('.data-list').forEach(list => {
            list.innerHTML = `
                <div class="loading">
                    Ma'lumotlar yuklanmoqda...
                </div>
            `;
        });
    }

    hideLoading() {
        // Loading indikatorini yashirish
        document.querySelectorAll('.loading').forEach(loading => {
            loading.remove();
        });
    }
}

// Global functions for HTML onclick events
function showAddTransactionModal(type = null) {
    app.showModal('addTransactionModal');
    if (type) {
        setTimeout(() => app.selectTransactionType(type), 100);
    }
}

function closeModal(modalId) {
    app.closeModal(modalId);
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new BalansAI();
});

// Handle page visibility changes
document.addEventListener('visibilitychange', () => {
    if (!document.hidden && window.app) {
        // Sahifa ko'rinadigan bo'lganda ma'lumotlarni yangilash
        window.app.loadAllData();
    }
});

// Handle online/offline status
window.addEventListener('online', () => {
    if (window.app) {
        window.app.showNotification('Internet aloqasi tiklandi', 'success');
        window.app.loadAllData();
    }
});

window.addEventListener('offline', () => {
    if (window.app) {
        window.app.showNotification('Internet aloqasi uzildi', 'warning');
    }
});