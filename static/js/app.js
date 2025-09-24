// Telegram Wallet Style - Balans AI Application

class BalansAI {
    constructor() {
        this.currentUser = null;
        this.currentTab = 'home';
        this.userTariff = 'FREE';
        this.userLimits = null;
        this.data = {
            transactions: [],
            statistics: null
        };
        this.charts = {
            monthly: null,
            category: null,
            weekly: null,
            incomeExpense: null,
            daily: null
        };
        this.goals = [];
        this.currentFilter = 'all';
        
        this.init();
    }

    async init() {
        try {
            // Telegram WebApp sozlash
            if (window.Telegram && window.Telegram.WebApp) {
                const tg = window.Telegram.WebApp;
                tg.ready();
                tg.expand();
                tg.enableClosingConfirmation();
                
                // Full screen va Wallet style
                tg.setHeaderColor('#007aff');
                tg.setBackgroundColor('#ffffff');
                
                // Main button ni yashirish
                tg.MainButton.hide();
                tg.BackButton.hide();
                
                // Foydalanuvchi ma'lumotlari
                if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
                    this.currentUser = tg.initDataUnsafe.user;
                    await this.updateUserInfo();
                } else {
                    // Test uchun
                    this.currentUser = { id: 123456789, first_name: 'Test User' };
                    await this.updateUserInfo();
                }
                
                // Tema sozlash
                this.setTheme(tg.colorScheme || 'light');
            } else {
                // Test rejimi
                this.currentUser = { id: 123456789, first_name: 'Test User' };
                await this.updateUserInfo();
                console.log('Telegram WebApp mavjud emas, test rejimida ishlayapti');
            }
            
            // Barcha ma'lumotlar yuklangandan keyin loading ni yashirish
            await this.loadAllData();
            
            // Event listeners sozlash
            this.setupEventListeners();
            
        } catch (error) {
            console.error('Init xatoligi:', error);
        }
    }

    showLoading() {
        const loadingScreen = document.getElementById('loadingScreen');
        const app = document.getElementById('app');
        if (loadingScreen) loadingScreen.style.display = 'flex';
        if (app) app.style.display = 'none';
    }

    hideLoading() {
        const loadingScreen = document.getElementById('loadingScreen');
        const app = document.getElementById('app');
        if (loadingScreen) loadingScreen.style.display = 'none';
        if (app) app.style.display = 'block';
    }

    async loadAllData() {
        try {
            console.log('Ma\'lumotlar yuklash boshlandi...');
            
            // Barcha asosiy ma'lumotlarni parallel yuklash
            await Promise.all([
                this.loadUserTariff(),
                this.loadTransactions(),
                this.loadStatistics(),
                this.loadDebts(),
                this.loadChartsData(),
                this.loadGoals()
            ]);
            
            console.log('Barcha ma\'lumotlar yuklandi');
        } catch (error) {
            console.error('Ma\'lumotlar yuklashda xatolik:', error);
        }
    }

    updateUserInfo() {
        if (this.currentUser) {
            // Profile sahifasida
            const profileName = document.getElementById('profileName');
            if (profileName) {
                profileName.textContent = this.currentUser.first_name || 'Foydalanuvchi';
            }
            
            // Avatar
            const profileAvatar = document.getElementById('profileAvatar');
            if (profileAvatar && this.currentUser.first_name) {
                profileAvatar.textContent = this.currentUser.first_name.charAt(0).toUpperCase();
            }
        }
    }

    setTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        
        // Chart.js uchun rang sozlamalari
        this.chartColors = {
            income: '#34c759',
            expense: '#ff3b30',
            debt: '#ff9500',
            text: theme === 'dark' ? '#ffffff' : '#000000',
            grid: theme === 'dark' ? '#48484a' : '#e5e5ea'
        };
    }

    setupEventListeners() {
        // Bottom navigation
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const tabName = e.target.closest('.nav-item').dataset.tab;
                this.switchTab(tabName);
            });
        });

        // Filter tabs
        document.querySelectorAll('.filter-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
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
        // Transaction form olib tashlandi - faqat ko'rish va o'chirish

        // Modal close events
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.closeModal(modal.id);
                }
            });
        });

        // Haptic feedback for Telegram
        document.addEventListener('click', (e) => {
            if (e.target.closest('button, .nav-item, .wallet-action-btn') && window.Telegram?.WebApp) {
                window.Telegram.WebApp.HapticFeedback.impactOccurred('light');
            }
        });
    }

    switchTab(tabName) {
        console.log('Switching to tab:', tabName);
        
        // Update active nav item
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active');
        });
        
        const navItem = document.querySelector(`[data-tab="${tabName}"]`);
        if (navItem) {
            navItem.classList.add('active');
        } else {
            console.error('Nav item not found for tab:', tabName);
        }

        // Show corresponding content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        
        const tabContent = document.getElementById(tabName);
        if (tabContent) {
            tabContent.classList.add('active');
        } else {
            console.error('Tab content not found for tab:', tabName);
        }

        this.currentTab = tabName;
        this.renderCurrentTab();
    }

    setFilter(filter) {
        this.currentFilter = filter;
        
        // Update filter buttons
        document.querySelectorAll('.filter-tab').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-filter="${filter}"]`).classList.add('active');
        
        this.renderTransactions();
    }

    async loadUserTariff() {
        if (!this.currentUser) return;

        try {
            const response = await fetch(`/api/user/tariff/${this.currentUser.id}`);
            const result = await response.json();
            
            if (result.success) {
                this.userTariff = result.data.tariff;
                this.userLimits = result.data;
                console.log('Tarif yuklandi:', this.userTariff, this.userLimits);
                this.updateTariffUI();
            } else {
                console.error('Tarif yuklashda xatolik:', result.message);
            }
        } catch (error) {
            console.error('Tarif ma\'lumotlarini yuklashda xatolik:', error);
        }
    }

    updateTariffUI() {
        // Tariff badge
        const tariffBadge = document.getElementById('tariffBadge');
        const tariffText = document.getElementById('tariffText');
        const upgradeBtn = document.getElementById('upgradeBtn');
        
        if (tariffText) {
            tariffText.textContent = this.userTariff || 'FREE';
            console.log('Tariff text yangilandi:', tariffText.textContent);
        }
        
        if (this.userTariff === 'PREMIUM') {
            if (tariffBadge) {
                tariffBadge.classList.add('premium');
                tariffBadge.classList.remove('free');
            }
            if (upgradeBtn) upgradeBtn.style.display = 'none';
        } else {
            if (tariffBadge) {
                tariffBadge.classList.add('free');
                tariffBadge.classList.remove('premium');
            }
            if (upgradeBtn) upgradeBtn.style.display = 'block';
        }
        
        // Profile tariff
        const profileTariff = document.getElementById('profileTariff');
        if (profileTariff) {
            profileTariff.textContent = this.userTariff;
            profileTariff.className = `tariff-badge-small ${this.userTariff.toLowerCase()}`;
        }
        
        // Analytics premium badge
        const analyticsPremiumBadge = document.getElementById('analyticsPremiumBadge');
        if (analyticsPremiumBadge) {
            analyticsPremiumBadge.style.display = this.userTariff === 'PREMIUM' ? 'none' : 'flex';
        }
        
        // Advanced analytics section
        const advancedAnalytics = document.getElementById('advancedAnalytics');
        if (advancedAnalytics) {
            advancedAnalytics.style.display = this.userLimits?.advanced_analytics ? 'none' : 'block';
        }
    }

    async loadAllData() {
        if (!this.currentUser) return;

        try {
            this.showLoading();
            
            // Ma'lumotlarni parallel yuklash
            const [transactions, statistics, limits, debts] = await Promise.all([
                this.fetchData(`/api/transactions/${this.currentUser.id}`),
                this.fetchData(`/api/statistics/${this.currentUser.id}`),
                this.fetchData(`/api/check-limits/${this.currentUser.id}`),
                this.fetchData(`/api/debts/${this.currentUser.id}`)
            ]);

            this.data.transactions = transactions || [];
            this.data.statistics = statistics || this.getEmptyStatistics();
            this.userLimits = limits || {};
            this.data.debts = debts || { debts: [], summary: { total_debts: 0, total_given: 0, total_received: 0, net_balance: 0 } };

            this.hideLoading();
            this.renderCurrentTab();
            this.updateAILimitText();
            this.updateDebtsSection();
            
            // Premium foydalanuvchilar uchun advanced analytics yuklash
            if (this.userLimits?.data?.advanced_analytics) {
                await this.loadAdvancedAnalytics();
            }
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
            case 'home':
                this.renderHome();
                break;
            case 'transactions':
                this.renderTransactions();
                break;
            case 'analytics':
                this.renderAnalytics();
                break;
            case 'profile':
                this.renderProfile();
                break;
        }
    }

    renderHome() {
        if (!this.data.statistics) return;

        const stats = this.data.statistics;

        // Main balance
        document.getElementById('mainBalance').textContent = 
            this.formatCurrency(stats.balance);

        // Balance change calculation
        const balanceChange = document.getElementById('balanceChange');
        if (balanceChange) {
            // Bu oyda o'zgarish (soddalashtirilgan)
            const changePercent = stats.total_income > 0 ? 
                ((stats.balance / stats.total_income) * 100).toFixed(1) : 0;
            balanceChange.innerHTML = `
                <span class="change-icon">${changePercent >= 0 ? '📈' : '📉'}</span>
                <span class="change-text">Bu oyda ${changePercent >= 0 ? '+' : ''}${changePercent}%</span>
            `;
        }

        // Home stats
        document.getElementById('totalIncomeHome').textContent = 
            this.formatNumber(stats.total_income);
        document.getElementById('totalExpenseHome').textContent = 
            this.formatNumber(stats.total_expense);
        document.getElementById('totalDebtHome').textContent = 
            this.formatNumber(stats.total_debt);

        // Recent transactions
        this.renderRecentTransactions(stats.recent_transactions);
    }

    renderRecentTransactions(transactions) {
        const container = document.getElementById('recentTransactionsList');
        
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
            <div class="transaction-item">
                <div class="transaction-icon ${transaction.transaction_type}">
                    ${this.getTransactionIcon(transaction.transaction_type)}
                </div>
                <div class="transaction-info">
                    <div class="transaction-title">${this.escapeHtml(transaction.description || transaction.category)}</div>
                    <div class="transaction-category">${this.escapeHtml(transaction.category)}</div>
                </div>
                <div class="transaction-right">
                    <div class="transaction-amount ${transaction.transaction_type}">
                        ${transaction.transaction_type === 'expense' ? '-' : '+'}${this.formatCurrency(transaction.amount)}
                    </div>
                    <div class="transaction-date">${this.formatDate(transaction.created_at)}</div>
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
            <div class="transaction-item">
                <div class="transaction-icon ${transaction.transaction_type}">
                    ${this.getTransactionIcon(transaction.transaction_type)}
                </div>
                <div class="transaction-info">
                    <div class="transaction-title">${this.escapeHtml(transaction.description || transaction.category)}</div>
                    <div class="transaction-category">${this.escapeHtml(transaction.category)}</div>
                </div>
                <div class="transaction-right">
                    <div class="transaction-amount ${transaction.transaction_type}">
                        ${transaction.transaction_type === 'expense' ? '-' : '+'}${this.formatCurrency(transaction.amount)}
                    </div>
                    <div class="transaction-date">${this.formatDate(transaction.created_at)}</div>
                </div>
                <div class="transaction-actions">
                    <button class="btn-secondary btn-small" onclick="app.editTransaction(${transaction.id})">
                        ✏️
                    </button>
                    <button class="btn-danger btn-small" onclick="app.deleteTransaction(${transaction.id})">
                        🗑️
                    </button>
                </div>
            </div>
        `).join('');
    }

    renderAnalytics() {
        this.renderCharts();
        this.updateAILimitText();
    }

    renderProfile() {
        // Tariff details
        const tariffDetails = document.getElementById('tariffDetails');
        if (tariffDetails && this.userLimits) {
            const limits = this.userLimits.limits || {};
            tariffDetails.innerHTML = `
                <div class="tariff-feature">
                    <span>Oylik tranzaksiyalar:</span>
                    <span>${limits.transactions_per_month === -1 ? 'Cheksiz' : limits.transactions_per_month}</span>
                </div>
                <div class="tariff-feature">
                    <span>Kunlik AI so'rovlar:</span>
                    <span>${limits.ai_requests_per_day === -1 ? 'Cheksiz' : limits.ai_requests_per_day}</span>
                </div>
                <div class="tariff-feature">
                    <span>Kengaytirilgan tahlil:</span>
                    <span>${limits.advanced_analytics ? '✅' : '❌'}</span>
                </div>
                <div class="tariff-feature">
                    <span>Ma'lumot eksporti:</span>
                    <span>${limits.export_data ? '✅' : '❌'}</span>
                </div>
            `;
        }
    }

    renderCharts() {
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

    updateAILimitText() {
        const aiLimitText = document.getElementById('aiLimitText');
        if (aiLimitText && this.userLimits) {
            const limits = this.userLimits.limits || {};
            const usage = this.userLimits.usage || {};
            
            if (limits.ai_requests_per_day === -1) {
                aiLimitText.textContent = 'Cheksiz AI so\'rovlar';
            } else {
                const remaining = limits.ai_requests_per_day - (usage.daily_ai_requests || 0);
                aiLimitText.textContent = `Qolgan: ${remaining}/${limits.ai_requests_per_day}`;
            }
        }
    }

    getTransactionIcon(type) {
        const icons = {
            income: '📥',
            expense: '📤',
            debt: '🏦'
        };
        return icons[type] || '💰';
    }

    selectTransactionType(type) {
        document.querySelectorAll('.type-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-type="${type}"]`).classList.add('active');
        document.getElementById('transactionType').value = type;

        // Modal title ni yangilash
        const titles = {
            income: '📥 Daromad qo\'shish',
            expense: '📤 Xarajat qo\'shish',
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

    showUpgradeModal() {
        this.showModal('upgradeModal');
    }

    async upgradeToPremium() {
        if (!this.currentUser) return;

        try {
            const response = await fetch('/api/user/upgrade', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: this.currentUser.id })
            });

            const result = await response.json();
            if (result.success) {
                this.closeModal('upgradeModal');
                await this.loadUserTariff();
                await this.loadAllData();
                this.showNotification('Premium tarifga muvaffaqiyatli o\'tdingiz!', 'success');
                
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

    async showAIAnalysis() {
        if (!this.userLimits?.data?.can_use_ai) {
            this.showNotification(this.userLimits?.data?.ai_message || 'AI limit tugagan', 'warning');
            this.showUpgradeModal();
            return;
        }
        
        this.requestAIAnalysis();
    }

    async getAIReport() {
        try {
            this.showLoading();
            const response = await this.fetchData(`/api/ai/report/${this.currentUser.id}`);
            
            if (response && response.success) {
                // AI hisobotni modal da ko'rsatish
                this.showAIReportModal(response.report);
            } else {
                if (response.limit_exceeded) {
                    this.showNotification(response.message, 'warning');
                    this.showUpgradeModal();
                } else {
                    this.showNotification(response.message || 'Xatolik yuz berdi', 'error');
                }
            }
        } catch (error) {
            this.showNotification('AI hisobotida xatolik yuz berdi', 'error');
        } finally {
            this.hideLoading();
        }
    }

    showAIReportModal(report) {
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.style.display = 'block';
        modal.innerHTML = `
            <div class="modal-content ai-report-modal">
                <div class="modal-header">
                    <h3>🤖 AI Moliyaviy Hisobot</h3>
                    <span class="close" onclick="this.parentElement.parentElement.parentElement.remove()">&times;</span>
                </div>
                <div class="ai-report-content">
                    <div class="report-text">${report}</div>
                </div>
                <div class="modal-actions">
                    <button class="btn-primary" onclick="this.parentElement.parentElement.parentElement.remove()">
                        Yopish
                    </button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        
        // Modal tashqarisiga bosilganda yopish
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        });
    }

    async requestAIAnalysis() {
        if (!this.currentUser) return;

        this.showModal('aiAnalysisModal');
        const content = document.getElementById('aiAnalysisContent');
        content.innerHTML = `
            <div class="ai-loading">
                <div class="loading-spinner"></div>
                <p>AI tahlil qilmoqda...</p>
            </div>
        `;

        try {
            const response = await fetch(`/api/ai/analysis/${this.currentUser.id}`);
            const result = await response.json();

            if (result.success) {
                content.innerHTML = `
                    <div class="ai-result-content">
                        ${result.analysis.replace(/\n/g, '<br>')}
                    </div>
                `;
                
                // AI limit ni yangilash
                await this.loadAllData();
            } else {
                content.innerHTML = `
                    <div class="ai-error">
                        <p>❌ ${result.message}</p>
                    </div>
                `;
            }
        } catch (error) {
            content.innerHTML = `
                <div class="ai-error">
                    <p>❌ AI tahlil qilishda xatolik yuz berdi</p>
                </div>
            `;
        }
    }

    async exportData() {
        if (!this.userLimits?.export_data) {
            this.showNotification('Ma\'lumotlar eksporti Premium tarifida mavjud', 'warning');
            return;
        }

        // Bu yerda eksport funksiyasini qo'shish mumkin
        this.showNotification('Eksport funksiyasi tez orada qo\'shiladi', 'info');
    }

    // Qarzlar bo'limini yangilash
    updateDebtsSection() {
        if (!this.data.debts) return;

        const { debts, summary } = this.data.debts;

        // Xulosani yangilash
        document.getElementById('totalDebts').textContent = `${summary.total_debts || 0} ta`;
        document.getElementById('totalGiven').textContent = this.formatCurrency(summary.total_given || 0);
        document.getElementById('totalReceived').textContent = this.formatCurrency(summary.total_received || 0);
        document.getElementById('netBalance').textContent = this.formatCurrency(summary.net_balance || 0);

        // Qarzlar ro'yxatini yangilash
        const debtItems = document.getElementById('debtItems');
        if (!debts || debts.length === 0) {
            debtItems.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">💰</div>
                    <h4>Qarzlar yo'q</h4>
                    <p>Hali hech qanday qarz ma'lumoti kiritilmagan</p>
                </div>
            `;
            return;
        }

        debtItems.innerHTML = debts.map(debt => `
            <div class="debt-item ${debt.debt_type}">
                <div class="debt-icon">
                    ${debt.debt_type === 'bergan' ? '📤' : '📥'}
                </div>
                <div class="debt-content">
                    <div class="debt-header">
                        <span class="debt-category">${debt.category}</span>
                        <span class="debt-amount ${debt.debt_type}">
                            ${debt.debt_type === 'bergan' ? '+' : '-'}${this.formatCurrency(debt.debt_amount)}
                        </span>
                    </div>
                    <div class="debt-description">${debt.description || 'Tavsif yo\'q'}</div>
                    <div class="debt-date">${this.formatDate(debt.created_at)}</div>
                </div>
                <button class="debt-delete-btn" onclick="app.deleteTransaction(${debt.id})">
                    🗑️
                </button>
            </div>
        `).join('');
    }

    // Kengaytirilgan tahlillarni yuklash
    async loadAdvancedAnalytics() {
        if (!this.currentUser) return;

        try {
            const response = await this.fetchData(`/api/advanced-stats/${this.currentUser.id}`);
            if (response) {
                this.updateAdvancedAnalytics(response);
            }
        } catch (error) {
            console.error('Advanced analytics yuklashda xatolik:', error);
        }
    }

    // Kengaytirilgan tahlillarni yangilash
    updateAdvancedAnalytics(data) {
        const { highest_expense, lowest_expense, most_expensive_day, daily_stats, category_breakdown } = data;

        // Premium foydalanuvchilar uchun ko'rsatish
        const analyticsLock = document.getElementById('analyticsLock');
        const analyticsContent = document.getElementById('advancedAnalyticsContent');
        
        if (this.userLimits?.data?.advanced_analytics) {
            analyticsLock.style.display = 'none';
            analyticsContent.style.display = 'block';

            // Eng yuqori xarajat
            if (highest_expense) {
                document.getElementById('highestExpense').textContent = this.formatCurrency(highest_expense.amount);
                document.getElementById('highestExpenseDetail').textContent = 
                    `${highest_expense.category} - ${highest_expense.date}`;
            }

            // Eng kam xarajat
            if (lowest_expense) {
                document.getElementById('lowestExpense').textContent = this.formatCurrency(lowest_expense.amount);
                document.getElementById('lowestExpenseDetail').textContent = 
                    `${lowest_expense.category} - ${lowest_expense.date}`;
            }

            // Eng qimmat kun
            if (most_expensive_day) {
                document.getElementById('mostExpensiveDay').textContent = most_expensive_day.date;
                document.getElementById('mostExpensiveDayAmount').textContent = 
                    this.formatCurrency(most_expensive_day.amount);
            }

            // Top kategoriyalar
            const topCategories = document.getElementById('topCategories');
            if (category_breakdown && category_breakdown.length > 0) {
                topCategories.innerHTML = category_breakdown.map((cat, index) => `
                    <div class="category-item">
                        <div class="category-rank">${index + 1}</div>
                        <div class="category-info">
                            <div class="category-name">${cat.category}</div>
                            <div class="category-amount">${this.formatCurrency(cat.amount)}</div>
                        </div>
                    </div>
                `).join('');
            }

            // Kunlik grafik
            if (daily_stats && daily_stats.length > 0) {
                this.createDailyChart(daily_stats);
            }
        } else {
            analyticsLock.style.display = 'block';
            analyticsContent.style.display = 'none';
        }
    }

    // Kunlik grafik yaratish
    createDailyChart(dailyStats) {
        const ctx = document.getElementById('dailyChart');
        if (!ctx) return;

        // Eski grafikni yo'q qilish
        if (this.dailyChart) {
            this.dailyChart.destroy();
        }

        const labels = dailyStats.map(d => d.day_name.substring(0, 3));
        const expensesData = dailyStats.map(d => d.expenses);
        const incomeData = dailyStats.map(d => d.income);

        this.dailyChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Xarajatlar',
                    data: expensesData,
                    borderColor: '#ef4444',
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    tension: 0.4
                }, {
                    label: 'Daromadlar',
                    data: incomeData,
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    tension: 0.4
                }]
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
                            callback: function(value) {
                                return value.toLocaleString() + ' so\'m';
                            }
                        }
                    }
                }
            }
        });
    }

    // CRUD Operations - Faqat o'chirish va ko'rish

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
            month: 'short'
        });
    }

    formatMonth(monthString) {
        const [year, month] = monthString.split('-');
        const date = new Date(year, month - 1);
        return date.toLocaleDateString('uz-UZ', {
            month: 'short'
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
        document.querySelectorAll('.transaction-list').forEach(list => {
            list.innerHTML = `
                <div class="loading">
                    <div class="loading-spinner"></div>
                    <p>Ma'lumotlar yuklanmoqda...</p>
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

    async loadChartsData() {
        try {
            console.log('Charts data yuklash boshlandi...');
            const response = await fetch(`/api/charts/${this.currentUser.id}`);
            
            if (!response.ok) {
                console.log('Charts API xatoligi:', response.status);
                return;
            }
            
            const data = await response.json();
            console.log('Charts data yuklandi:', data);
            
            if (data.monthly) {
                this.createMonthlyChart(data.monthly);
            }
            if (data.weekly) {
                this.createWeeklyChart(data.weekly);
            }
            if (data.daily) {
                this.createDailyChart(data.daily);
            }
            if (data.categories) {
                this.createCategoryChart(data.categories);
                this.createIncomeExpenseChart(data.categories);
            }
        } catch (error) {
            console.error('Charts data yuklashda xatolik:', error);
        }
    }

    createWeeklyChart(data) {
        const ctx = document.getElementById('weeklyChart');
        if (!ctx || !data.length) return;

        if (this.charts.weekly) {
            this.charts.weekly.destroy();
        }

        const labels = data.map(item => `Hafta ${item.week}`);
        const incomeData = data.map(item => parseFloat(item.income) || 0);
        const expenseData = data.map(item => parseFloat(item.expense) || 0);

        this.charts.weekly = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Daromad',
                    data: incomeData,
                    borderColor: '#34c759',
                    backgroundColor: 'rgba(52, 199, 89, 0.1)',
                    tension: 0.4
                }, {
                    label: 'Xarajat',
                    data: expenseData,
                    borderColor: '#ff3b30',
                    backgroundColor: 'rgba(255, 59, 48, 0.1)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return value.toLocaleString() + ' so\'m';
                            }
                        }
                    }
                }
            }
        });
    }

    createIncomeExpenseChart(data) {
        const ctx = document.getElementById('incomeExpenseChart');
        if (!ctx || !data.length) return;

        if (this.charts.incomeExpense) {
            this.charts.incomeExpense.destroy();
        }

        const totalIncome = data.reduce((sum, item) => sum + (parseFloat(item.income) || 0), 0);
        const totalExpense = data.reduce((sum, item) => sum + (parseFloat(item.expense) || 0), 0);

        this.charts.incomeExpense = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Daromad', 'Xarajat'],
                datasets: [{
                    data: [totalIncome, totalExpense],
                    backgroundColor: ['#34c759', '#ff3b30'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                    }
                }
            }
        });
    }

    createDailyChart(data) {
        const ctx = document.getElementById('dailyChart');
        if (!ctx || !data.length) return;

        if (this.charts.daily) {
            this.charts.daily.destroy();
        }

        const labels = data.map(item => {
            const date = new Date(item.date);
            return date.toLocaleDateString('uz-UZ', { day: 'numeric', month: 'short' });
        });
        const incomeData = data.map(item => parseFloat(item.income) || 0);
        const expenseData = data.map(item => parseFloat(item.expense) || 0);

        this.charts.daily = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Daromad',
                    data: incomeData,
                    backgroundColor: 'rgba(52, 199, 89, 0.8)',
                    borderColor: '#34c759',
                    borderWidth: 1
                }, {
                    label: 'Xarajat',
                    data: expenseData,
                    backgroundColor: 'rgba(255, 59, 48, 0.8)',
                    borderColor: '#ff3b30',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return value.toLocaleString() + ' so\'m';
                            }
                        }
                    }
                }
            }
        });
    }

    // Goals functions
    async loadGoals() {
        try {
            const response = await fetch(`/api/goals/${this.currentUser.id}`);
            if (response.ok) {
                const data = await response.json();
                this.goals = data.goals || [];
                this.updateGoalsDisplay();
            }
        } catch (error) {
            console.error('Goals yuklashda xatolik:', error);
        }
    }

    updateGoalsDisplay() {
        const goalItems = document.getElementById('goalItems');
        if (!goalItems) return;

        if (this.goals.length === 0) {
            goalItems.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">🎯</div>
                    <h4>Maqsadlar yo'q</h4>
                    <p>Birinchi maqsadingizni qo'shing</p>
                </div>
            `;
            return;
        }

        const activeGoals = this.goals.filter(goal => goal.status === 'active').length;
        const completedGoals = this.goals.filter(goal => goal.status === 'completed').length;
        const totalSaved = this.goals.reduce((sum, goal) => sum + (parseFloat(goal.current_amount) || 0), 0);

        // Update summary
        document.getElementById('activeGoals').textContent = `${activeGoals} ta`;
        document.getElementById('completedGoals').textContent = `${completedGoals} ta`;
        document.getElementById('totalSaved').textContent = `${totalSaved.toLocaleString()} so'm`;

        // Render goals
        goalItems.innerHTML = this.goals.map(goal => this.renderGoal(goal)).join('');
    }

    renderGoal(goal) {
        const progress = (parseFloat(goal.current_amount) / parseFloat(goal.target_amount)) * 100;
        const isUrgent = new Date(goal.deadline) < new Date(Date.now() + 7 * 24 * 60 * 60 * 1000);
        
        return `
            <div class="goal-item ${isUrgent ? 'urgent' : ''}">
                <div class="goal-header">
                    <h3 class="goal-title">${this.escapeHtml(goal.name)}</h3>
                    <span class="goal-category">${this.escapeHtml(goal.category)}</span>
                </div>
                
                <div class="goal-progress">
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${Math.min(progress, 100)}%"></div>
                    </div>
                    <div class="progress-text">
                        <span>${progress.toFixed(1)}%</span>
                        <span>${this.formatDate(goal.deadline)}</span>
                    </div>
                </div>
                
                <div class="goal-amount">
                    <span class="goal-current">${parseFloat(goal.current_amount).toLocaleString()} so'm</span>
                    <span class="goal-target">/ ${parseFloat(goal.target_amount).toLocaleString()} so'm</span>
                </div>
                
                <div class="goal-deadline">
                    <span>📅</span>
                    <span>Muddat: ${this.formatDate(goal.deadline)}</span>
                </div>
                
                <div class="goal-actions">
                    <button class="goal-btn primary" onclick="app.addToGoal(${goal.id})">
                        Qo'shish
                    </button>
                    <button class="goal-btn secondary" onclick="app.editGoal(${goal.id})">
                        Tahrirlash
                    </button>
                </div>
            </div>
        `;
    }

    showAddGoalModal() {
        this.openModal('addGoalModal');
        
        // Set default deadline to 1 month from now
        const deadline = new Date();
        deadline.setMonth(deadline.getMonth() + 1);
        document.getElementById('goalDeadline').value = deadline.toISOString().split('T')[0];
    }

    async addGoal(goalData) {
        try {
            const response = await fetch(`/api/goals/${this.currentUser.id}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(goalData)
            });

            if (response.ok) {
                this.closeModal('addGoalModal');
                await this.loadGoals();
                this.showNotification('Maqsad muvaffaqiyatli qo\'shildi!', 'success');
            } else {
                this.showNotification('Maqsad qo\'shishda xatolik!', 'error');
            }
        } catch (error) {
            console.error('Add goal xatoligi:', error);
            this.showNotification('Maqsad qo\'shishda xatolik!', 'error');
        }
    }

    async addToGoal(goalId) {
        const amount = prompt('Qancha pul qo\'shmoqchisiz?');
        if (!amount || isNaN(amount) || parseFloat(amount) <= 0) return;

        try {
            const response = await fetch(`/api/goals/${goalId}/add`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ amount: parseFloat(amount) })
            });

            if (response.ok) {
                await this.loadGoals();
                this.showNotification('Pul muvaffaqiyatli qo\'shildi!', 'success');
            } else {
                this.showNotification('Pul qo\'shishda xatolik!', 'error');
            }
        } catch (error) {
            console.error('Add to goal xatoligi:', error);
            this.showNotification('Pul qo\'shishda xatolik!', 'error');
        }
    }

    async editGoal(goalId) {
        const goal = this.goals.find(g => g.id === goalId);
        if (!goal) return;

        const newName = prompt('Yangi nom:', goal.name);
        if (!newName) return;

        try {
            const response = await fetch(`/api/goals/${goalId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ name: newName })
            });

            if (response.ok) {
                await this.loadGoals();
                this.showNotification('Maqsad muvaffaqiyatli yangilandi!', 'success');
            } else {
                this.showNotification('Maqsad yangilashda xatolik!', 'error');
            }
        } catch (error) {
            console.error('Edit goal xatoligi:', error);
            this.showNotification('Maqsad yangilashda xatolik!', 'error');
        }
    }

    // Notifications
    showNotifications() {
        this.openModal('notificationsModal');
    }

    // Form handlers
    setupFormHandlers() {
        // Goal form
        const goalForm = document.getElementById('goalForm');
        if (goalForm) {
            goalForm.addEventListener('submit', (e) => {
                e.preventDefault();
                
                const formData = {
                    name: document.getElementById('goalName').value,
                    target_amount: parseFloat(document.getElementById('goalAmount').value),
                    deadline: document.getElementById('goalDeadline').value,
                    category: document.getElementById('goalCategory').value
                };

                this.addGoal(formData);
            });
        }
    }
}

// Global functions for HTML onclick events
// showAddTransactionModal funksiyasi olib tashlandi

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