class BalansAI {
    constructor() {
        this.currentUser = null;
        this.currentTab = 'home';
        this.data = {
            balance: 0,
            income: 0,
            expense: 0,
            debt: 0,
            transactions: [],
            debts: [],
            tariff: 'Bepul',
            limits: {}
        };
        this.charts = {};
        this.isRealTimeMode = false;
        this.realTimeRecognition = null;
        this.isVoiceChatActive = false;
        this.voiceChatRecognition = null;
        this.audioStream = null;
        this.realtimeWS = null;
        
        // Configuration (will be set from server)
        this.config = {
            openaiApiKey: null
        };
    }

    async init() {
        try {
            console.log('BalansAI initializing...');
            
            // Telegram WebApp tekshirish - darhol
            if (window.Telegram && window.Telegram.WebApp) {
                console.log('Telegram WebApp detected');
                window.Telegram.WebApp.ready();
                window.Telegram.WebApp.expand();
                // Pull-to-close funksiyasini o'chirish
                window.Telegram.WebApp.disableVerticalSwipes();
                
                // Init data ni tekshirish
                const initData = window.Telegram.WebApp.initData;
                const initDataUnsafe = window.Telegram.WebApp.initDataUnsafe;
                
                console.log('Init data:', initData);
                console.log('Init data unsafe:', initDataUnsafe);
                
                if (initDataUnsafe && initDataUnsafe.user) {
                    const user = initDataUnsafe.user;
                    this.currentUser = {
                        id: user.id,
                        first_name: user.first_name,
                        last_name: user.last_name,
                        username: user.username
                    };
                    console.log('Telegram user found:', this.currentUser);
                } else {
                    // window.USER_ID dan olish
                    if (window.USER_ID) {
                        this.currentUser = { 
                            id: parseInt(window.USER_ID), 
                            first_name: 'User' 
                        };
                        console.log('User ID from window.USER_ID:', this.currentUser);
                    } else {
                        // URL dan user ID ni olish
                        const urlParams = new URLSearchParams(window.location.search);
                        const userId = urlParams.get('user_id') || urlParams.get('user');
                        if (userId) {
                            this.currentUser = { 
                                id: parseInt(userId), 
                                first_name: 'User' 
                            };
                            console.log('User ID from URL:', this.currentUser);
                        } else {
                            // Test rejimi
                            this.currentUser = { id: 123456789, first_name: 'Test User' };
                            console.log('Test mode activated');
                        }
                    }
                }
            } else {
                console.log('Telegram WebApp not detected, using test mode');
                // window.USER_ID dan olish
                if (window.USER_ID) {
                    this.currentUser = { 
                        id: parseInt(window.USER_ID), 
                        first_name: 'User' 
                    };
                    console.log('User ID from window.USER_ID:', this.currentUser);
                } else {
                    // URL dan user ID ni olish
                    const urlParams = new URLSearchParams(window.location.search);
                    const userId = urlParams.get('user_id') || urlParams.get('user');
                    if (userId) {
                        this.currentUser = { 
                            id: parseInt(userId), 
                            first_name: 'User' 
                        };
                        console.log('User ID from URL:', this.currentUser);
                    } else {
                        // Test rejimi
                        this.currentUser = { id: 123456789, first_name: 'Test User' };
                        console.log('Test mode activated');
                    }
                }
            }

            // Event listeners darhol
            this.setupEventListeners();
            
            // Ma'lumotlarni kutib yuklash
            try {
                await this.loadAllData();
                this.updateUI();
            } catch (error) {
                console.error('Load data error:', error);
            }
            
            // Loading ni yashirish
            this.hideLoading();
            console.log('BalansAI initialized successfully');
            
        } catch (error) {
            console.error('Init error:', error);
            this.hideLoading();
        }
    }

    async loadAllData() {
        try {
            console.log('Loading all data...');
            
            const userId = this.currentUser.id;
            
            // Parallel ma'lumotlar yuklash
            const [statistics, debts, tariff, config] = await Promise.all([
                this.fetchData(`/api/statistics/${userId}`),
                this.fetchData(`/api/debts/${userId}`),
                this.fetchData(`/api/user/tariff/${userId}`),
                this.fetchData(`/api/config`).catch(() => ({ success: false }))
            ]);
            
            // Config ni yuklash
            if (config.success && config.data) {
                this.config = config.data;
            }

            // Ma'lumotlarni saqlash
            if (statistics.success) {
                this.data.balance = statistics.data.balance || 0;
                this.data.income = statistics.data.total_income || 0;
                this.data.expense = statistics.data.total_expense || 0;
                this.data.debt = statistics.data.total_debt || 0;
                this.data.transactions = statistics.data.recent_transactions || [];
                this.data.monthly_income = statistics.data.monthly_income || 0;
                this.data.monthly_expense = statistics.data.monthly_expense || 0;
            }

            if (debts.success) {
                this.data.debts = debts.data.debts || [];
            }

            if (tariff.success) {
                this.data.tariff = tariff.data.tariff || 'Bepul';
                this.data.limits = tariff.data.limits || {};
                console.log('Tariff loaded:', this.data.tariff);
            }

            console.log('Data loaded:', this.data);
            console.log('Current tariff:', this.data.tariff);
            
        } catch (error) {
            console.error('Load data error:', error);
        }
    }

    async fetchData(url) {
        try {
            const response = await fetch(url);
            return await response.json();
        } catch (error) {
            console.error(`Fetch error for ${url}:`, error);
            return { success: false, data: {} };
        }
    }

    updateUI() {
        this.updateBalanceCard();
        this.updateRecentTransactions();
        this.updateAllTransactions();
        this.updateStats();
        this.updateTariffBadge();
        this.updateDebts();
        // Grafiklarni keyinchalik render qilish (on-demand)
        requestAnimationFrame(() => {
            this.updateCharts();
        });
    }

    updateBalanceCard() {
        const balance = this.data.balance;
        const balanceCard = document.getElementById('balanceCard');
        const balanceAmount = document.getElementById('balanceAmount');
        const balanceStatus = document.getElementById('balanceStatus');
        const totalIncome = document.getElementById('totalIncome');
        const totalExpense = document.getElementById('totalExpense');
        const totalDebt = document.getElementById('totalDebt');

        // Balans miqdorini ko'rsatish
        balanceAmount.textContent = this.formatMoney(balance);

        // Balans holatini belgilash
        balanceStatus.className = 'balance-status';
        if (balance > 0) {
            balanceStatus.classList.add('positive');
        } else if (balance === 0 && this.data.debt > 0) {
            balanceStatus.classList.add('warning');
        } else if (balance < 0) {
            balanceStatus.classList.add('negative');
        }

        // Boshqa ma'lumotlar
        totalIncome.textContent = this.formatMoney(this.data.income);
        totalExpense.textContent = this.formatMoney(this.data.expense);
        totalDebt.textContent = this.formatMoney(this.data.debt);
    }

    updateRecentTransactions() {
        const container = document.getElementById('recentTransactions');
        const transactions = this.data.transactions.slice(0, 5);

        if (transactions.length === 0) {
            container.innerHTML = '<div class="text-center" style="padding: 20px; color: var(--tg-theme-hint-color);">Tranzaksiyalar yo\'q</div>';
            return;
        }

        container.innerHTML = transactions.map(transaction => `
            <div class="transaction-item" onclick="app.showTransactionDetail(${transaction.id})">
                <div class="transaction-icon ${transaction.transaction_type}">
                    ${this.getTransactionIcon(transaction.transaction_type)}
                </div>
                <div class="transaction-content">
                    <div class="transaction-title">${this.truncateText(transaction.description || 'Tranzaksiya', 25)}</div>
                    <div class="transaction-category">${transaction.category}</div>
                    <div class="transaction-time">${this.formatTime(transaction.created_at)}</div>
                </div>
                <div class="transaction-amount ${transaction.transaction_type}">
                    ${transaction.transaction_type === 'income' ? '+' : '-'}${this.formatMoney(transaction.amount)}
                </div>
            </div>
        `).join('');
    }

    updateAllTransactions() {
        const container = document.getElementById('allTransactions');
        const transactions = this.data.transactions;

        if (transactions.length === 0) {
            container.innerHTML = '<div class="text-center" style="padding: 20px; color: var(--tg-theme-hint-color);">Tranzaksiyalar yo\'q</div>';
            return;
        }

        container.innerHTML = transactions.map(transaction => `
            <div class="transaction-item" onclick="app.showTransactionDetail(${transaction.id})">
                <div class="transaction-icon ${transaction.transaction_type}">
                    ${this.getTransactionIcon(transaction.transaction_type)}
                </div>
                <div class="transaction-content">
                    <div class="transaction-title">${this.truncateText(transaction.description || 'Tranzaksiya', 25)}</div>
                    <div class="transaction-category">${transaction.category}</div>
                    <div class="transaction-time">${this.formatTime(transaction.created_at)}</div>
                </div>
                <div class="transaction-amount ${transaction.transaction_type}">
                    ${transaction.transaction_type === 'income' ? '+' : '-'}${this.formatMoney(transaction.amount)}
                </div>
            </div>
        `).join('');
    }

    updateStats() {
        document.getElementById('monthlyIncome').textContent = this.formatMoney(this.data.monthly_income);
        document.getElementById('monthlyExpense').textContent = this.formatMoney(this.data.monthly_expense);
        
        const savingsRate = this.data.monthly_income > 0 
            ? Math.round(((this.data.monthly_income - this.data.monthly_expense) / this.data.monthly_income) * 100)
            : 0;
        document.getElementById('savingsRate').textContent = `${savingsRate}%`;
        
        document.getElementById('transactionsCount').textContent = this.data.transactions.length;
    }

    updateTariffBadge() {
        const badge = document.getElementById('tariffBadge');
        const tariffText = badge.querySelector('.tariff-text');
        
        tariffText.textContent = this.data.tariff;
        badge.className = `tariff-badge ${this.data.tariff.toLowerCase()}`;
        
        // Tarif cheklovlarini tekshirish
        this.updateTariffLimits();
    }

    updateTariffLimits() {
        const analyticsLock = document.getElementById('analyticsLock');
        const aiLock = document.getElementById('aiLock');
        const aiChatTariff = document.getElementById('aiChatTariff');
        const tariff = this.data.tariff || 'Bepul';
        
        // AI Chat tarif ko'rsatkichi
        if (aiChatTariff) {
            aiChatTariff.textContent = tariff.toUpperCase();
        }
        
        // AI input va buttonlarni yaratish
        const aiInput = document.getElementById('aiInput');
        const aiSendBtn = document.getElementById('aiSendBtn');
        const aiVoiceBtn = document.getElementById('aiVoiceBtn');
        const aiRealTimeBtn = document.getElementById('aiRealTimeBtn');
        
        // Bepul tarif
        if (tariff === 'Bepul' || tariff === 'FREE') {
            if (analyticsLock) analyticsLock.style.display = 'block';
            if (aiLock) aiLock.style.display = 'block';
            
            // AI inputlarni disable qilish
            if (aiInput) aiInput.disabled = true;
            if (aiSendBtn) aiSendBtn.disabled = true;
            if (aiVoiceBtn) aiVoiceBtn.disabled = true;
            if (aiRealTimeBtn) aiRealTimeBtn.disabled = true;
        } 
        // Plus, Biznes, Oila tariflar
        else if (tariff === 'Plus' || tariff === 'PLUS' || 
                 tariff === 'Biznes' || tariff === 'BIZNES' ||
                 tariff === 'Oila' || tariff === 'OILA' ||
                 tariff === 'Max' || tariff === 'MAX' ||
                 tariff === 'Biznes Plus' || tariff === 'BIZNES PLUS' ||
                 tariff === 'Biznes Max' || tariff === 'BIZNES MAX' ||
                 tariff === 'Oila Plus' || tariff === 'OILA PLUS' ||
                 tariff === 'Oila Max' || tariff === 'OILA MAX') {
            if (analyticsLock) analyticsLock.style.display = 'none';
            if (aiLock) aiLock.style.display = 'none';
            
            // AI inputlarni enable qilish
            if (aiInput) aiInput.disabled = false;
            if (aiSendBtn) aiSendBtn.disabled = false;
            if (aiVoiceBtn) aiVoiceBtn.disabled = false;
            if (aiRealTimeBtn) aiRealTimeBtn.disabled = false;
        }
    }

    updateDebts() {
        const totalDebtAmount = document.getElementById('totalDebtAmount');
        const debtCount = document.getElementById('debtCount');
        const debtsList = document.getElementById('debtsList');

        totalDebtAmount.textContent = this.formatMoney(this.data.debt);
        debtCount.textContent = this.data.debts.length;

        if (this.data.debts.length === 0) {
            debtsList.innerHTML = '<div class="text-center" style="padding: 20px; color: var(--tg-theme-hint-color);">Qarzlar yo\'q</div>';
            return;
        }

        debtsList.innerHTML = this.data.debts.map(debt => `
            <div class="debt-item">
                <div class="debt-info">
                    <div class="debt-title">${debt.description || 'Qarz'}</div>
                    <div class="debt-description">${debt.category} • ${this.formatDate(debt.created_at)}</div>
                </div>
                <div class="debt-amount">${this.formatMoney(debt.amount)}</div>
            </div>
        `).join('');
    }

    updateCharts() {
        console.log('Updating charts for tariff:', this.data.tariff);
        
        // Chart.js yuklanganligini tekshirish
        if (typeof Chart === 'undefined') {
            console.error('Chart.js is not loaded!');
            return;
        }
        
        // Eski grafiklarni tozalash
        if (this.charts) {
            Object.keys(this.charts).forEach(key => {
                if (this.charts[key]) {
                    this.charts[key].destroy();
                }
            });
        }
        this.charts = {};
        
        // Grafiklarni darhol render qilish
        const tariff = this.data.tariff || 'Bepul';
        
        // Bepul tarifida faqat asosiy grafik
        if (tariff === 'Bepul' || tariff === 'FREE') {
            console.log('Creating basic chart for Bepul tariff');
            this.createBasicChart();
            this.lockPremiumCharts();
        } 
        // Plus, Biznes, Oila - 5 ta grafik
        else if (tariff === 'Plus' || tariff === 'PLUS' || 
                 tariff === 'Biznes' || tariff === 'BIZNES' ||
                 tariff === 'Oila' || tariff === 'OILA') {
            console.log('Creating plus/business/family charts for tariff:', tariff);
            this.createPremiumCharts();
            requestAnimationFrame(() => this.lockMaxCharts());
        }
        // Max - 10 ta grafik
        else if (tariff === 'Max' || tariff === 'MAX' || 
                 tariff === 'Biznes Plus' || tariff === 'BIZNES PLUS' ||
                 tariff === 'Biznes Max' || tariff === 'BIZNES MAX' ||
                 tariff === 'Oila Plus' || tariff === 'OILA PLUS' ||
                 tariff === 'Oila Max' || tariff === 'OILA MAX') {
            console.log('Creating max charts for tariff:', tariff);
            this.createMaxCharts();
        }
        else {
            console.log('Unknown tariff:', tariff, '- creating default basic chart');
            this.createBasicChart();
            this.lockPremiumCharts();
        }
        
        console.log('Charts created:', Object.keys(this.charts));
    }

    lockPremiumCharts() {
        // PLUS/PRO grafiklarni qulf qilish (FREE uchun)
        const premiumFeatures = document.querySelectorAll('.premium-feature');
        
        premiumFeatures.forEach(feature => {
            if (!feature.classList.contains('locked')) {
                feature.classList.add('locked');
                const content = feature.querySelector('.analytics-table, canvas');
                if (content) {
                    content.style.filter = 'blur(4px)';
                    content.style.pointerEvents = 'none';
                }
                
                // Lock overlay qo'shish
                if (!feature.querySelector('.premium-lock-overlay')) {
                    const overlay = document.createElement('div');
                    overlay.className = 'premium-lock-overlay';
                    overlay.innerHTML = `
                        <div class="lock-content">
                            <div class="lock-icon">🔒</div>
                            <div class="lock-text">Plus yoki Pro kerak</div>
                            <button class="unlock-btn" onclick="window.location.href='/payment'">Tarifni yangilash</button>
                        </div>
                    `;
                    feature.appendChild(overlay);
                }
            }
        });
    }

    lockMaxCharts() {
        // MAX grafiklarni qulf qilish (Plus/Biznes/Oila uchun)
        // Faqat 6-11 grafiklarni qulf qilish (1-5 ochiq bo'ladi)
        const maxCharts = [
            'topExpensesChart', 'monthlyTrendChart', 'categoryDistributionChart',
            'yearlyChart', 'debtsChart', 'balanceChangeChart'
        ];
        
        console.log('Locking max charts:', maxCharts);
        
        maxCharts.forEach(chartId => {
            const container = document.getElementById(chartId);
            if (!container) {
                console.log(`Chart not found: ${chartId}`);
                return;
            }
            
            // Canvas elementni yashirish va qulf qilish
            const parentContainer = container.parentElement;
            if (parentContainer) {
                console.log(`Locking chart: ${chartId}`);
                parentContainer.innerHTML = `
                    <div class="chart-locked">
                        <div class="lock-icon">🔒</div>
                        <h4>Max, Biznes Plus yoki Oila Max kerak</h4>
                        <p>Bu grafikni ko'rish uchun yuqori tarifni sotib oling</p>
                    </div>
                `;
            }
        });
        
        console.log('Max charts locked successfully');
    }

    createBasicChart() {
        // FREE tarif - 3 ta grafik
        console.log('Creating FREE tariff charts');
        this.createIncomeExpenseGrowthChart();
        this.createNewCategoryChart();
        this.createNewMonthlyTrendChart();
    }

    createPremiumCharts() {
        // PLUS/PRO tarif - FREE + qo'shimcha 3 ta
        console.log('Creating PLUS/PRO tariff charts');
        
        // FREE grafiklar
        this.createIncomeExpenseGrowthChart();
        this.createNewCategoryChart();
        this.createNewMonthlyTrendChart();
        
        // PLUS grafiklar
        this.createTopExpensesTable();
        this.createTopIncomeSources();
        this.createLifetimeIncomeChart();
    }

    createMaxCharts() {
        // MAX tarif - hammasi
        console.log('Creating MAX tariff charts');
        
        // FREE grafiklar
        this.createIncomeExpenseGrowthChart();
        this.createNewCategoryChart();
        this.createNewMonthlyTrendChart();
        
        // PLUS grafiklar
        this.createTopExpensesTable();
        this.createTopIncomeSources();
        this.createLifetimeIncomeChart();
    }

    createMonthlyChart() {
        const ctx = document.getElementById('monthlyChart');
        if (!ctx) return;

        const data = this.generateMonthlyData();
        
        this.charts.monthly = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Kirim',
                    data: data.income,
                    borderColor: '#4caf50',
                    backgroundColor: 'rgba(76, 175, 80, 0.1)',
                    tension: 0.4
                }, {
                    label: 'Chiqim',
                    data: data.expense,
                    borderColor: '#f44336',
                    backgroundColor: 'rgba(244, 67, 54, 0.1)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }

    createCategoryChart() {
        const ctx = document.getElementById('categoryChart');
        if (!ctx) return;

        const data = this.generateCategoryData();
        
        this.charts.category = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: data.labels,
                datasets: [{
                    data: data.values,
                    backgroundColor: [
                        '#ff6384',
                        '#36a2eb',
                        '#ffce56',
                        '#4bc0c0',
                        '#9966ff',
                        '#ff9f40'
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

    createDailyChart() {
        const ctx = document.getElementById('dailyChart');
        if (!ctx) return;

        const data = this.generateDailyData();
        
        this.charts.daily = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Kunlik tranzaksiyalar',
                    data: data.values,
                    backgroundColor: '#667eea'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }

    createWeeklyChart() {
        const ctx = document.getElementById('weeklyChart');
        if (!ctx) return;

        const data = this.generateWeeklyData();
        
        this.charts.weekly = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Haftalik kirim',
                    data: data.income,
                    backgroundColor: '#4caf50'
                }, {
                    label: 'Haftalik chiqim',
                    data: data.expense,
                    backgroundColor: '#f44336'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }

    createIncomeExpenseChart() {
        const ctx = document.getElementById('incomeExpenseChart');
        if (!ctx) return;

        const data = this.generateIncomeExpenseData();
        
        this.charts.incomeExpense = new Chart(ctx, {
            type: 'radar',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Kirim',
                    data: data.income,
                    borderColor: '#4caf50',
                    backgroundColor: 'rgba(76, 175, 80, 0.2)'
                }, {
                    label: 'Chiqim',
                    data: data.expense,
                    borderColor: '#f44336',
                    backgroundColor: 'rgba(244, 67, 54, 0.2)'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    r: {
                        beginAtZero: true
                    }
                }
            }
        });
    }

    createTopExpensesChart() {
        const ctx = document.getElementById('topExpensesChart');
        if (!ctx) return;

        const data = this.generateTopExpensesData();
        
        this.charts.topExpenses = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Xarajatlar',
                    data: data.values,
                    backgroundColor: '#ff9800'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        beginAtZero: true
                    }
                }
            }
        });
    }

    createMonthlyTrendChart() {
        const ctx = document.getElementById('monthlyTrendChart');
        if (!ctx) return;

        const data = this.generateMonthlyTrendData();
        
        this.charts.monthlyTrend = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Oylik tendensiya',
                    data: data.values,
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }

    createCategoryDistributionChart() {
        const ctx = document.getElementById('categoryDistributionChart');
        if (!ctx) return;

        const data = this.generateCategoryDistributionData();
        
        this.charts.categoryDistribution = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: data.labels,
                datasets: [{
                    data: data.values,
                    backgroundColor: [
                        '#ff6384',
                        '#36a2eb',
                        '#ffce56',
                        '#4bc0c0',
                        '#9966ff',
                        '#ff9f40',
                        '#ff6384',
                        '#36a2eb'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right'
                    }
                }
            }
        });
    }

    createYearlyChart() {
        const ctx = document.getElementById('yearlyChart');
        if (!ctx) return;

        const data = this.generateYearlyData();
        
        this.charts.yearly = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Yillik kirim',
                    data: data.income,
                    backgroundColor: '#4caf50'
                }, {
                    label: 'Yillik chiqim',
                    data: data.expense,
                    backgroundColor: '#f44336'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }

    createDebtsChart() {
        const ctx = document.getElementById('debtsChart');
        if (!ctx) return;

        const data = this.generateDebtsData();
        
        this.charts.debts = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Qarzlar',
                    data: data.values,
                    borderColor: '#ff9800',
                    backgroundColor: 'rgba(255, 152, 0, 0.1)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }

    createBalanceChangeChart() {
        const ctx = document.getElementById('balanceChangeChart');
        if (!ctx) return;

        const data = this.generateBalanceChangeData();
        
        this.charts.balanceChange = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Balans o\'zgarishi',
                    data: data.values,
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }

    // ===== YANGI CHART FUNKSIYALARI =====
    
    createIncomeExpenseGrowthChart() {
        const ctx = document.getElementById('incomeExpenseGrowthChart');
        if (!ctx) {
            console.log('incomeExpenseGrowthChart not found');
            return;
        }

        const data = this.generateMonthlyData();
        
        this.charts.incomeExpenseGrowth = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [
                    {
                        label: 'Daromad',
                        data: data.income,
                        borderColor: '#4CAF50',
                        backgroundColor: 'rgba(76, 175, 80, 0.1)',
                        fill: true,
                        tension: 0.4
                    },
                    {
                        label: 'Xarajat',
                        data: data.expense,
                        borderColor: '#F44336',
                        backgroundColor: 'rgba(244, 67, 54, 0.1)',
                        fill: true,
                        tension: 0.4
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
                            callback: function(value) {
                                return value.toLocaleString() + " so'm";
                            }
                        }
                    }
                }
            }
        });
    }

    createNewCategoryChart() {
        const ctx = document.getElementById('categoryChart');
        if (!ctx) {
            console.log('categoryChart not found');
            return;
        }

        const data = this.generateCategoryData();
        
        this.charts.newCategory = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: data.labels,
                datasets: [{
                    data: data.values,
                    backgroundColor: [
                        '#FF6384',
                        '#36A2EB',
                        '#FFCE56',
                        '#4BC0C0',
                        '#9966FF',
                        '#FF9F40'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'bottom'
                    }
                }
            }
        });
    }

    createNewMonthlyTrendChart() {
        const ctx = document.getElementById('monthlyTrendChart');
        if (!ctx) {
            console.log('monthlyTrendChart not found');
            return;
        }

        const data = this.generateMonthlyData();
        
        this.charts.newMonthlyTrend = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: [
                    {
                        label: 'Daromad',
                        data: data.income,
                        backgroundColor: 'rgba(76, 175, 80, 0.8)'
                    },
                    {
                        label: 'Xarajat',
                        data: data.expense,
                        backgroundColor: 'rgba(244, 67, 54, 0.8)'
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
                            callback: function(value) {
                                return value.toLocaleString() + " so'm";
                            }
                        }
                    }
                }
            }
        });
    }

    createTopExpensesTable() {
        const container = document.getElementById('topExpensesTable');
        if (!container) {
            console.log('topExpensesTable not found');
            return;
        }

        const topExpenses = this.getTopExpenses(5);
        
        if (topExpenses.length === 0) {
            container.innerHTML = '<div class="analytics-empty">Xarajat ma\'lumotlari mavjud emas</div>';
            return;
        }

        const totalAmount = topExpenses.reduce((sum, item) => sum + item.amount, 0);
        
        container.innerHTML = topExpenses.map((item, index) => `
            <div class="analytics-row">
                <div class="analytics-row-rank">${index + 1}</div>
                <div class="analytics-row-name">${item.category}</div>
                <div class="analytics-row-value">${this.formatMoney(item.amount)}</div>
                <div class="analytics-row-percent">${((item.amount / totalAmount) * 100).toFixed(1)}%</div>
            </div>
        `).join('');
    }

    createTopIncomeSources() {
        const container = document.getElementById('topIncomeSources');
        if (!container) {
            console.log('topIncomeSources not found');
            return;
        }

        const topIncome = this.getTopIncome(5);
        
        if (topIncome.length === 0) {
            container.innerHTML = '<div class="analytics-empty">Daromad ma\'lumotlari mavjud emas</div>';
            return;
        }

        const totalAmount = topIncome.reduce((sum, item) => sum + item.amount, 0);
        
        container.innerHTML = topIncome.map((item, index) => `
            <div class="analytics-row">
                <div class="analytics-row-rank">${index + 1}</div>
                <div class="analytics-row-name">${item.category}</div>
                <div class="analytics-row-value">${this.formatMoney(item.amount)}</div>
                <div class="analytics-row-percent">${((item.amount / totalAmount) * 100).toFixed(1)}%</div>
            </div>
        `).join('');
    }

    createLifetimeIncomeChart() {
        const ctx = document.getElementById('lifetimeIncomeChart');
        if (!ctx) {
            console.log('lifetimeIncomeChart not found');
            return;
        }

        const data = this.generateLifetimeIncomeData();
        
        this.charts.lifetimeIncome = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Jami daromad',
                    data: data.values,
                    borderColor: '#4CAF50',
                    backgroundColor: 'rgba(76, 175, 80, 0.1)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 3,
                    pointHoverRadius: 5
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return value.toLocaleString() + " so'm";
                            }
                        }
                    }
                }
            }
        });
    }

    // Helper functions for new charts
    getTopExpenses(limit = 5) {
        const expenses = this.data.transactions.filter(t => 
            t.transaction_type === 'expense' || t.type === 'expense'
        );
        
        const categoryTotals = {};
        expenses.forEach(t => {
            const category = t.category || 'Boshqa';
            categoryTotals[category] = (categoryTotals[category] || 0) + t.amount;
        });
        
        return Object.entries(categoryTotals)
            .map(([category, amount]) => ({ category, amount }))
            .sort((a, b) => b.amount - a.amount)
            .slice(0, limit);
    }

    getTopIncome(limit = 5) {
        const income = this.data.transactions.filter(t => 
            t.transaction_type === 'income' || t.type === 'income'
        );
        
        const categoryTotals = {};
        income.forEach(t => {
            const category = t.category || 'Boshqa';
            categoryTotals[category] = (categoryTotals[category] || 0) + t.amount;
        });
        
        return Object.entries(categoryTotals)
            .map(([category, amount]) => ({ category, amount }))
            .sort((a, b) => b.amount - a.amount)
            .slice(0, limit);
    }

    generateLifetimeIncomeData() {
        const income = this.data.transactions
            .filter(t => t.transaction_type === 'income' || t.type === 'income')
            .sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
        
        const labels = [];
        const values = [];
        let total = 0;
        
        income.forEach((t, index) => {
            total += t.amount;
            if (index % Math.ceil(income.length / 10) === 0 || index === income.length - 1) {
                const date = new Date(t.created_at);
                labels.push(`${date.getDate()}/${date.getMonth() + 1}`);
                values.push(total);
            }
        });
        
        if (labels.length === 0) {
            return {
                labels: ['Bugun'],
                values: [0]
            };
        }
        
        return { labels, values };
    }

    // Data generators
    generateMonthlyData() {
        // Haqiqiy ma'lumotlardan oylik statistikani olish
        const months = ['Yan', 'Fev', 'Mar', 'Apr', 'May', 'Iyun'];
        const currentMonth = new Date().getMonth();
        
        // Oxirgi 6 oy uchun ma'lumotlar
        const monthlyData = months.map((month, index) => {
            const monthTransactions = this.data.transactions.filter(t => {
                const transactionDate = new Date(t.created_at);
                const transactionMonth = transactionDate.getMonth();
                return transactionMonth === (currentMonth - 5 + index + 12) % 12;
            });
            
            const income = monthTransactions
                .filter(t => t.transaction_type === 'income' || t.type === 'income')
                .reduce((sum, t) => sum + t.amount, 0);
            
            const expense = monthTransactions
                .filter(t => t.transaction_type === 'expense' || t.type === 'expense')
                .reduce((sum, t) => sum + t.amount, 0);
            
            return { income, expense };
        });
        
        return {
            labels: months,
            income: monthlyData.map(d => d.income),
            expense: monthlyData.map(d => d.expense)
        };
    }

    generateCategoryData() {
        // Haqiqiy ma'lumotlardan kategoriya statistikani olish
        const categoryStats = {};
        
        this.data.transactions.forEach(transaction => {
            const type = transaction.transaction_type || transaction.type;
        if (type === 'expense') {
                const category = transaction.category || 'Boshqalar';
                categoryStats[category] = (categoryStats[category] || 0) + transaction.amount;
            }
        });
        
        // Kategoriyalarni miqdor bo'yicha tartiblash
        const sortedCategories = Object.entries(categoryStats)
            .sort(([,a], [,b]) => b - a)
            .slice(0, 5); // Faqat top 5
        
        if (sortedCategories.length === 0) {
            return {
                labels: ['Ma\'lumot yo\'q'],
                values: [100]
            };
        }
        
        const total = sortedCategories.reduce((sum, [, amount]) => sum + amount, 0);
        
        return {
            labels: sortedCategories.map(([category]) => category),
            values: sortedCategories.map(([, amount]) => Math.round((amount / total) * 100))
        };
    }

    generateDailyData() {
        // Haqiqiy ma'lumotlardan kunlik statistikani olish
        const days = ['Dush', 'Sesh', 'Chor', 'Pay', 'Jum', 'Shan', 'Yak'];
        const today = new Date();
        const startOfWeek = new Date(today);
        startOfWeek.setDate(today.getDate() - today.getDay() + 1); // Dushanbadan boshlash
        
        const dailyData = days.map((day, index) => {
            const dayDate = new Date(startOfWeek);
            dayDate.setDate(startOfWeek.getDate() + index);
            
            const dayTransactions = this.data.transactions.filter(t => {
                const transactionDate = new Date(t.created_at);
                return transactionDate.toDateString() === dayDate.toDateString();
            });
            
            return dayTransactions.reduce((sum, t) => sum + t.amount, 0);
        });
        
        return {
            labels: days,
            values: dailyData
        };
    }

    generateWeeklyData() {
        // Haqiqiy ma'lumotlardan haftalik statistikani olish
        const weeks = ['1-hafta', '2-hafta', '3-hafta', '4-hafta'];
        const today = new Date();
        const currentMonth = today.getMonth();
        const currentYear = today.getFullYear();
        
        const weeklyData = weeks.map((week, index) => {
            const weekStart = new Date(currentYear, currentMonth, index * 7 + 1);
            const weekEnd = new Date(currentYear, currentMonth, (index + 1) * 7);
            
            const weekTransactions = this.data.transactions.filter(t => {
                const transactionDate = new Date(t.created_at);
                return transactionDate >= weekStart && transactionDate <= weekEnd;
            });
            
            const income = weekTransactions
                .filter(t => t.transaction_type === 'income' || t.type === 'income')
                .reduce((sum, t) => sum + t.amount, 0);
            
            const expense = weekTransactions
                .filter(t => t.transaction_type === 'expense' || t.type === 'expense')
                .reduce((sum, t) => sum + t.amount, 0);
            
            return { income, expense };
        });
        
        return {
            labels: weeks,
            income: weeklyData.map(d => d.income),
            expense: weeklyData.map(d => d.expense)
        };
    }

    generateIncomeExpenseData() {
        // Haqiqiy ma'lumotlardan kirim-chiqim statistikani olish
        const categoryStats = {};
        
        this.data.transactions.forEach(transaction => {
            const category = transaction.category || 'Boshqalar';
            if (!categoryStats[category]) {
                categoryStats[category] = { income: 0, expense: 0 };
            }
            
            const type = transaction.transaction_type || transaction.type;
            if (type === 'income') {
                categoryStats[category].income += transaction.amount;
            } else if (type === 'expense') {
                categoryStats[category].expense += transaction.amount;
            }
        });
        
        // Kategoriyalarni umumiy miqdor bo'yicha tartiblash
        const sortedCategories = Object.entries(categoryStats)
            .sort(([,a], [,b]) => (b.income + b.expense) - (a.income + a.expense))
            .slice(0, 5); // Faqat top 5
        
        if (sortedCategories.length === 0) {
            return {
                labels: ['Ma\'lumot yo\'q'],
                income: [0],
                expense: [0]
            };
        }
        
        return {
            labels: sortedCategories.map(([category]) => category),
            income: sortedCategories.map(([, data]) => data.income),
            expense: sortedCategories.map(([, data]) => data.expense)
        };
    }

    generateTopExpensesData() {
        // Haqiqiy ma'lumotlardan eng katta xarajatlarni olish
        const expenseStats = {};
        
        this.data.transactions.forEach(transaction => {
            const type = transaction.transaction_type || transaction.type;
            if (type === 'expense') {
                const category = transaction.category || 'Boshqalar';
                expenseStats[category] = (expenseStats[category] || 0) + transaction.amount;
            }
        });
        
        // Xarajatlarni miqdor bo'yicha tartiblash
        const sortedExpenses = Object.entries(expenseStats)
            .sort(([,a], [,b]) => b - a)
            .slice(0, 5); // Faqat top 5
        
        if (sortedExpenses.length === 0) {
            return {
                labels: ['Ma\'lumot yo\'q'],
                values: [0]
            };
        }
        
        return {
            labels: sortedExpenses.map(([category]) => category),
            values: sortedExpenses.map(([, amount]) => amount)
        };
    }

    generateMonthlyTrendData() {
        // Haqiqiy ma'lumotlardan oylik tendensiyani olish
        const months = ['Yan', 'Fev', 'Mar', 'Apr', 'May', 'Iyun'];
        const currentMonth = new Date().getMonth();
        
        const monthlyData = months.map((month, index) => {
            const monthTransactions = this.data.transactions.filter(t => {
                const transactionDate = new Date(t.created_at);
                const transactionMonth = transactionDate.getMonth();
                return transactionMonth === (currentMonth - 5 + index + 12) % 12;
            });
            
            return monthTransactions.reduce((sum, t) => sum + t.amount, 0);
        });
        
        return {
            labels: months,
            values: monthlyData
        };
    }

    generateCategoryDistributionData() {
        // Haqiqiy ma'lumotlardan kategoriya taqsimotini olish
        const categoryStats = {};
        
        this.data.transactions.forEach(transaction => {
            const type = transaction.transaction_type || transaction.type;
        if (type === 'expense') {
                const category = transaction.category || 'Boshqalar';
                categoryStats[category] = (categoryStats[category] || 0) + transaction.amount;
            }
        });
        
        // Kategoriyalarni miqdor bo'yicha tartiblash
        const sortedCategories = Object.entries(categoryStats)
            .sort(([,a], [,b]) => b - a)
            .slice(0, 8); // Top 8 kategoriya
        
        if (sortedCategories.length === 0) {
            return {
                labels: ['Ma\'lumot yo\'q'],
                values: [100]
            };
        }
        
        const total = sortedCategories.reduce((sum, [, amount]) => sum + amount, 0);
        
        return {
            labels: sortedCategories.map(([category]) => category),
            values: sortedCategories.map(([, amount]) => Math.round((amount / total) * 100))
        };
    }

    generateYearlyData() {
        // Haqiqiy ma'lumotlardan yillik statistikani olish
        const years = ['2021', '2022', '2023', '2024'];
        const currentYear = new Date().getFullYear();
        
        const yearlyData = years.map((year, index) => {
            const yearTransactions = this.data.transactions.filter(t => {
                const transactionDate = new Date(t.created_at);
                const transactionYear = transactionDate.getFullYear();
                return transactionYear === (currentYear - 3 + index);
            });
            
            const income = yearTransactions
                .filter(t => t.type === 'income')
                .reduce((sum, t) => sum + t.amount, 0);
            
            const expense = yearTransactions
                .filter(t => t.type === 'expense')
                .reduce((sum, t) => sum + t.amount, 0);
            
            return { income, expense };
        });
        
        return {
            labels: years,
            income: yearlyData.map(d => d.income),
            expense: yearlyData.map(d => d.expense)
        };
    }

    generateDebtsData() {
        // Haqiqiy ma'lumotlardan qarzlar statistikani olish
        const months = ['Yan', 'Fev', 'Mar', 'Apr', 'May', 'Iyun'];
        const currentMonth = new Date().getMonth();
        
        const monthlyDebts = months.map((month, index) => {
            const monthDebts = this.data.debts.filter(d => {
                const debtDate = new Date(d.created_at);
                const debtMonth = debtDate.getMonth();
                return debtMonth === (currentMonth - 5 + index + 12) % 12;
            });
            
            return monthDebts.reduce((sum, d) => sum + d.amount, 0);
        });
        
        return {
            labels: months,
            values: monthlyDebts
        };
    }

    generateBalanceChangeData() {
        // Haqiqiy ma'lumotlardan balans o'zgarishini olish
        const days = ['1', '2', '3', '4', '5', '6', '7'];
        const today = new Date();
        
        const dailyBalance = days.map((day, index) => {
            const dayDate = new Date(today);
            dayDate.setDate(today.getDate() - 6 + index);
            
            const dayTransactions = this.data.transactions.filter(t => {
                const transactionDate = new Date(t.created_at);
                return transactionDate.toDateString() === dayDate.toDateString();
            });
            
            let balanceChange = 0;
            dayTransactions.forEach(t => {
                if (t.type === 'income') {
                    balanceChange += t.amount;
                } else if (t.type === 'expense') {
                    balanceChange -= t.amount;
                }
            });
            
            return balanceChange;
        });
        
        return {
            labels: days,
            values: dailyBalance
        };
    }

    setupEventListeners() {
        // Bottom navigation
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const tab = e.currentTarget.dataset.tab;
                this.switchTab(tab);
            });
        });

        // Filter tabs
        document.querySelectorAll('.filter-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                const filter = e.currentTarget.dataset.filter;
                this.setFilter(filter);
            });
        });

        // Search input
        const searchInput = document.getElementById('transactionSearch');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.filterTransactions(e.target.value);
            });
        }

        // AI chat (old)
        const aiInput = document.getElementById('aiInput');
        const aiSendBtn = document.getElementById('aiSendBtn');
        
        if (aiInput && aiSendBtn) {
            aiInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.sendAIMessage();
                }
            });
            
            aiSendBtn.addEventListener('click', () => {
                this.sendAIMessage();
            });
        }
        
        // AI Chat (new fullscreen) - Send button
        const aiInputChat = document.getElementById('aiInputChat');
        const aiSendBtnChat = document.getElementById('aiSendBtnChat');
        const aiVoiceBtnChat = document.getElementById('aiVoiceBtnChat');
        
        if (aiInputChat && aiSendBtnChat) {
            aiInputChat.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendAIMessage();
                }
            });
            
            aiSendBtnChat.addEventListener('click', () => {
                this.sendAIMessage();
            });
            
            // Auto-resize textarea
            aiInputChat.addEventListener('input', () => {
                aiInputChat.style.height = 'auto';
                aiInputChat.style.height = aiInputChat.scrollHeight + 'px';
            });
        }
        
        // Voice button (Chat)
        if (aiVoiceBtnChat) {
            aiVoiceBtnChat.addEventListener('click', () => {
                this.startVoiceRecognitionChat();
            });
        }

        // Voice button
        const aiVoiceBtn = document.getElementById('aiVoiceBtn');
        if (aiVoiceBtn) {
            aiVoiceBtn.addEventListener('click', () => {
                this.startVoiceRecognition();
            });
        }

        // Voice chat control button
        const voiceControlBtn = document.getElementById('voiceControlBtn');
        if (voiceControlBtn) {
            voiceControlBtn.addEventListener('click', () => {
                this.toggleVoiceChat();
            });
        }
    }

    switchTab(tabName) {
        console.log('Switching to tab:', tabName);
        
        // AI Chat - fullscreen mode
        if (tabName === 'ai-chat') {
            this.openAiChat();
            return;
        }
        
        // Close AI Chat if it's open
        const aiChat = document.getElementById('ai-chat');
        if (aiChat && aiChat.style.display !== 'none') {
            aiChat.style.display = 'none';
        }
        
        // Show bottom navigation
        const bottomNav = document.querySelector('.bottom-nav');
        if (bottomNav) {
            bottomNav.style.display = 'flex';
        }
        
        // Update active nav item
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active');
        });
        
        const navItem = document.querySelector(`[data-tab="${tabName}"]`);
        if (navItem) {
            navItem.classList.add('active');
        }

        // Show corresponding content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
            if (content.id === 'ai-chat') {
                content.style.display = 'none';
            } else {
                content.style.display = 'none';
            }
        });
        
        const tabContent = document.getElementById(tabName);
        if (tabContent) {
            tabContent.classList.add('active');
            tabContent.style.display = 'block';
        }

        this.currentTab = tabName;
    }
    
    openAiChat() {
        // Hide all other tabs
        document.querySelectorAll('.tab-content').forEach(tab => {
            if (tab.id !== 'ai-chat') {
                tab.style.display = 'none';
            }
        });
        
        // Hide bottom navigation
        const bottomNav = document.querySelector('.bottom-nav');
        if (bottomNav) {
            bottomNav.style.display = 'none';
        }
        
        // Show AI Chat fullscreen
        const aiChat = document.getElementById('ai-chat');
        if (aiChat) {
            aiChat.style.cssText = 'display: flex !important; visibility: visible !important;';
            
            console.log('AI Chat opened, scrolling to bottom...');
            
            // Scroll to bottom to show welcome message
            setTimeout(() => {
                const messagesContainer = document.getElementById('aiMessages');
                if (messagesContainer) {
                    messagesContainer.scrollTop = messagesContainer.scrollHeight;
                    console.log('Scrolled to:', messagesContainer.scrollHeight);
                }
            }, 200);
            
            // Focus input
            setTimeout(() => {
                const input = document.getElementById('aiInputChat');
                if (input) {
                    input.focus();
                }
            }, 300);
        }
        
        this.currentTab = 'ai-chat';
    }
    
    closeAiChat() {
        // Hide AI Chat
        const aiChat = document.getElementById('ai-chat');
        if (aiChat) {
            aiChat.style.cssText = 'display: none !important; visibility: hidden !important;';
        }
        
        // Show bottom navigation
        const bottomNav = document.querySelector('.bottom-nav');
        if (bottomNav) {
            bottomNav.style.display = 'flex';
        }
        
        // Show home tab
        this.switchTab('home');
    }

    setFilter(filter) {
        // Update filter buttons
        document.querySelectorAll('.filter-tab').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-filter="${filter}"]`).classList.add('active');
        
        // Filter transactions
        this.filterTransactions(document.getElementById('transactionSearch').value, filter);
    }

    filterTransactions(searchTerm = '', filter = 'all') {
        let filteredTransactions = this.data.transactions;
        
        // Filter by type
        if (filter !== 'all') {
            filteredTransactions = filteredTransactions.filter(t => t.transaction_type === filter);
        }
        
        // Filter by search term
        if (searchTerm) {
            filteredTransactions = filteredTransactions.filter(t => 
                (t.description || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
                (t.category || '').toLowerCase().includes(searchTerm.toLowerCase())
            );
        }
        
        // Update display
        const container = document.getElementById('allTransactions');
        if (filteredTransactions.length === 0) {
            container.innerHTML = '<div class="text-center" style="padding: 20px; color: var(--tg-theme-hint-color);">Tranzaksiyalar topilmadi</div>';
            return;
        }

        container.innerHTML = filteredTransactions.map(transaction => `
            <div class="transaction-item" onclick="app.showTransactionDetail(${transaction.id})">
                <div class="transaction-icon ${transaction.transaction_type}">
                    ${this.getTransactionIcon(transaction.transaction_type)}
                </div>
                <div class="transaction-content">
                    <div class="transaction-title">${this.truncateText(transaction.description || 'Tranzaksiya', 25)}</div>
                    <div class="transaction-category">${transaction.category}</div>
                    <div class="transaction-time">${this.formatTime(transaction.created_at)}</div>
                </div>
                <div class="transaction-amount ${transaction.transaction_type}">
                    ${transaction.transaction_type === 'income' ? '+' : '-'}${this.formatMoney(transaction.amount)}
                </div>
            </div>
        `).join('');
    }

    async sendAIMessage() {
        // Tarif tekshirish
        const allowedTariffs = ['Plus', 'PLUS', 'Max', 'MAX', 'Biznes', 'BIZNES', 'Oila', 'OILA',
                               'Biznes Plus', 'BIZNES PLUS', 'Biznes Max', 'BIZNES MAX',
                               'Oila Plus', 'OILA PLUS', 'Oila Max', 'OILA MAX'];
        if (!allowedTariffs.includes(this.data.tariff)) {
            alert('AI suhbat faqat Plus, Biznes, Oila yoki MAX tarifda mavjud!');
            return;
        }

        const input = document.getElementById('aiInputChat') || document.getElementById('aiInput');
        const message = input.value.trim();
        
        if (!message) return;
        
        // Disable input
        input.disabled = true;
        const sendBtn = document.getElementById('aiSendBtnChat') || document.getElementById('aiSendBtn');
        if (sendBtn) {
            sendBtn.disabled = true;
        }
        
        // Add user message
        this.addAIMessage(message, 'user');
        input.value = '';
        
        // Send to AI
        try {
            const userId = this.currentUser.id;
            const response = await this.fetchData(`/api/ai/advice?prompt=${encodeURIComponent(message)}&user_id=${userId}`);
            
            if (response && response.success) {
                this.addAIMessage(response.data.response, 'ai');
                
                // MAX tarif uchun keyboard hint
                if (this.data.tariff.toUpperCase() === 'MAX') {
                    console.log('🤖 MAX tariff - Advanced AI engaged!');
                }
            } else {
                this.addAIMessage('Kechirasiz, xatolik yuz berdi. Qayta urinib ko\'ring.', 'ai');
            }
        } catch (error) {
            console.error('AI error:', error);
            this.addAIMessage('Kechirasiz, xatolik yuz berdi. Qayta urinib ko\'ring.', 'ai');
        }
        
        // Enable input
        input.disabled = false;
        if (sendBtn) {
            sendBtn.disabled = false;
        }
        
        // Auto-focus input
        setTimeout(() => {
            input.focus();
        }, 100);
    }
    
    async startVoiceRecognitionChat() {
        // Tarif tekshirish
        const allowedTariffs = ['Plus', 'PLUS', 'Max', 'MAX', 'Biznes', 'BIZNES', 'Oila', 'OILA', 
                               'Biznes Plus', 'BIZNES PLUS', 'Biznes Max', 'BIZNES MAX',
                               'Oila Plus', 'OILA PLUS', 'Oila Max', 'OILA MAX'];
        
        if (!allowedTariffs.includes(this.data.tariff)) {
            alert('Ovozli suhbat faqat Plus, Biznes, Oila yoki MAX tarifda mavjud!');
            return;
        }

        const voiceBtnChat = document.getElementById('aiVoiceBtnChat');
        const voiceStatusChat = document.getElementById('aiVoiceStatusChat');
        const inputChat = document.getElementById('aiInputChat');

        // SpeechRecognition tekshirish
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            alert('Kechirasiz, sizning brauzeringiz ovozni tanib olshni qo\'llab-quvvatlamaydi.');
            return;
        }

        // Mikrofon ruxsatini tekshirish va so'rash
        try {
            await navigator.mediaDevices.getUserMedia({ audio: true });
        } catch (error) {
            alert('Mikrofon ruxsati rad etilgan. Brauzer sozlamalaridan mikrofon ruxsatini bering.');
            return;
        }

        let Recognition;
        try {
            Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            
            if (!Recognition) {
                alert('Speech recognition mavjud emas!');
                return;
            }
        } catch (error) {
            console.error('Recognition yaratishda xatolik:', error);
            alert('Ovoz tanib olish funksiyasi ishlamayapti.');
            return;
        }

        // Agar allaqachon active bo'lsa, to'xtatish
        if (this.recognition && this.recognition.isRecording) {
            this.recognition.stop();
            this.recognition.isRecording = false;
            voiceBtnChat.classList.remove('recording');
            voiceStatusChat.style.display = 'none';
            return;
        }

        const recognition = new Recognition();
        
        recognition.lang = 'ru-RU';
        recognition.continuous = false;
        recognition.interimResults = false;

        voiceBtnChat.classList.add('recording');
        voiceStatusChat.style.display = 'block';

        recognition.onstart = () => {
            console.log('Speech recognition started');
            this.recognition = recognition;
            this.recognition.isRecording = true;
        };

        recognition.onresult = (event) => {
            console.log('Speech recognition result:', event);
            const transcript = event.results[0][0].transcript;
            
            if (transcript) {
                inputChat.value = transcript;
                
                // Avtomatik ravishda yuborish
                setTimeout(() => {
                    this.sendAIMessage();
                }, 500);
            }
            
            voiceBtnChat.classList.remove('recording');
            voiceStatusChat.style.display = 'none';
            this.recognition.isRecording = false;
        };

        recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            
            let errorMessage = 'Ovoz eshitishda xatolik yuz berdi.';
            
            if (event.error === 'no-speech') {
                errorMessage = 'Ovoz topilmadi.';
            } else if (event.error === 'not-allowed') {
                errorMessage = 'Mikrofon ruxsati rad etilgan.';
            }
            
            alert(errorMessage);
            
            voiceBtnChat.classList.remove('recording');
            voiceStatusChat.style.display = 'none';
            if (this.recognition) {
                this.recognition.isRecording = false;
            }
        };

        recognition.onend = () => {
            if (this.recognition && this.recognition.isRecording) {
                voiceBtnChat.classList.remove('recording');
                voiceStatusChat.style.display = 'none';
                this.recognition.isRecording = false;
            }
        };

        try {
            recognition.start();
        } catch (error) {
            console.error('Recognition start error:', error);
            alert('Ovozni boshlashda xatolik.');
            voiceBtnChat.classList.remove('recording');
            voiceStatusChat.style.display = 'none';
        }
    }

    addAIMessage(message, sender) {
        const messagesContainer = document.getElementById('aiMessages');
        if (!messagesContainer) return;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender === 'user' ? 'user-message' : 'ai-message'}`;
        
        const now = new Date();
        const timeStr = now.toLocaleTimeString('uz-UZ', { hour: '2-digit', minute: '2-digit' });
        
        messageDiv.innerHTML = `
            <div class="message-avatar">${sender === 'user' ? '👤' : '🤖'}</div>
            <div class="message-content">
                <div class="message-text">${this.escapeHtml(message)}</div>
                <div class="message-time">${timeStr}</div>
            </div>
        `;
        
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    getTransactionIcon(type) {
        const icons = {
            income: '💰',
            expense: '💸',
            debt: '💳'
        };
        return icons[type] || '📄';
    }

    formatMoney(amount) {
        return new Intl.NumberFormat('uz-UZ', {
            style: 'currency',
            currency: 'UZS',
            minimumFractionDigits: 0
        }).format(amount);
    }

    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('uz-UZ');
    }

    formatTime(dateString) {
        const date = new Date(dateString);
        return date.toLocaleTimeString('uz-UZ', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
    }

    truncateText(text, maxLength) {
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    }

    showTransactionDetail(transactionId) {
        const transaction = this.data.transactions.find(t => t.id === transactionId);
        if (!transaction) return;

        const modal = document.getElementById('transactionModal');
        const modalTitle = document.getElementById('modalTitle');
        const modalBody = document.getElementById('modalBody');

        modalTitle.textContent = transaction.description || 'Tranzaksiya';
        
        modalBody.innerHTML = `
            <div class="modal-detail-item">
                <span class="modal-detail-label">Kategoriya</span>
                <span class="modal-detail-value">${transaction.category}</span>
            </div>
            <div class="modal-detail-item">
                <span class="modal-detail-label">Miqdor</span>
                <span class="modal-detail-value ${transaction.transaction_type}">${transaction.transaction_type === 'income' ? '+' : '-'}${this.formatMoney(transaction.amount)}</span>
            </div>
            <div class="modal-detail-item">
                <span class="modal-detail-label">Turi</span>
                <span class="modal-detail-value">${this.getTransactionTypeName(transaction.transaction_type)}</span>
            </div>
            <div class="modal-detail-item">
                <span class="modal-detail-label">Sana</span>
                <span class="modal-detail-value">${this.formatDate(transaction.created_at)}</span>
            </div>
            <div class="modal-detail-item">
                <span class="modal-detail-label">Vaqt</span>
                <span class="modal-detail-value">${this.formatTime(transaction.created_at)}</span>
            </div>
        `;

        modal.style.display = 'flex';
    }

    closeTransactionModal() {
        document.getElementById('transactionModal').style.display = 'none';
    }

    getTransactionTypeName(type) {
        const types = {
            'income': 'Kirim',
            'expense': 'Chiqim',
            'debt': 'Qarz'
        };
        return types[type] || type;
    }

    showLoading() {
        document.getElementById('loadingScreen').style.display = 'flex';
        document.getElementById('app').style.display = 'none';
    }

    hideLoading() {
        document.getElementById('loadingScreen').style.display = 'none';
        document.getElementById('app').style.display = 'block';
    }

    upgradeToPremium() {
        alert('Premium tarifni sotib olish uchun botga murojaat qiling!');
    }

    upgradeToMax() {
        alert('MAX tarifni sotib olish uchun botga murojaat qiling!');
    }

    // Voice recognition functions
    async startVoiceRecognition() {
        // Tarif tekshirish
        const allowedTariffs = ['Plus', 'PLUS', 'Max', 'MAX', 'Biznes', 'BIZNES', 'Oila', 'OILA', 
                               'Biznes Plus', 'BIZNES PLUS', 'Biznes Max', 'BIZNES MAX',
                               'Oila Plus', 'OILA PLUS', 'Oila Max', 'OILA MAX'];
        
        if (!allowedTariffs.includes(this.data.tariff)) {
            alert('Ovozli suhbat faqat Plus, Biznes, Oila yoki MAX tarifda mavjud!');
            return;
        }

        const voiceBtn = document.getElementById('aiVoiceBtn');
        const voiceStatus = document.getElementById('aiVoiceStatus');
        const input = document.getElementById('aiInput');

        // SpeechRecognition tekshirish
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            alert('Kechirasiz, sizning brauzeringiz ovozni tanib olshni qo\'llab-quvvatlamaydi.\n\nOvoz funksiyasini ishlatish uchun Chrome yoki Edge brauzeridan foydalaning.');
            return;
        }

        // Mikrofon ruxsatini tekshirish va so'rash
        try {
            await navigator.mediaDevices.getUserMedia({ audio: true });
        } catch (error) {
            alert('Mikrofon ruxsati rad etilgan. Iltimos, brauzer sozlamalaridan mikrofon ruxsatini bering.');
            return;
        }

        // Recognition qurish
        let Recognition;
        try {
            Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            
            if (!Recognition) {
                alert('Speech recognition mavjud emas!');
                return;
            }
        } catch (error) {
            console.error('Recognition yaratishda xatolik:', error);
            alert('Ovoz tanib olish funksiyasi ishlamayapti. Qayta urinib ko\'ring.');
            return;
        }

        // Agar allaqachon active bo'lsa, to'xtatish
        if (this.recognition && this.recognition.isRecording) {
            this.recognition.stop();
            this.recognition.isRecording = false;
            voiceBtn.classList.remove('recording');
            voiceStatus.style.display = 'none';
            return;
        }

        const recognition = new Recognition();
        
        recognition.lang = 'ru-RU'; // O'zbek tili yo'q, rus tilidan foydalanamiz
        recognition.continuous = false;
        recognition.interimResults = false;

        voiceBtn.classList.add('recording');
        voiceStatus.style.display = 'block';

        recognition.onstart = () => {
            console.log('Speech recognition started');
            this.recognition = recognition;
            this.recognition.isRecording = true;
        };

        recognition.onresult = (event) => {
            console.log('Speech recognition result:', event);
            const transcript = event.results[0][0].transcript;
            
            if (transcript) {
                input.value = transcript;
                
                // Avtomatik ravishda yuborish
                setTimeout(() => {
                    this.sendAIMessage();
                }, 500);
            }
            
            voiceBtn.classList.remove('recording');
            voiceStatus.style.display = 'none';
            this.recognition.isRecording = false;
        };

        recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            
            let errorMessage = 'Ovoz eshitishda xatolik yuz berdi.';
            
            switch(event.error) {
                case 'no-speech':
                    errorMessage = 'Ovoz topilmadi. Mikrofoningizni tekshiring.';
                    break;
                case 'audio-capture':
                    errorMessage = 'Mikrofonga kirish imkoni yo\'q. Ruxsatlarni tekshiring.';
                    break;
                case 'not-allowed':
                    errorMessage = 'Mikrofon ruxsati rad etilgan. Brauzer sozlamalaridan ruxsat bering.';
                    break;
                case 'network':
                    errorMessage = 'Tarmoq xatoligi. Internet bilan bog\'lanishni tekshiring.';
                    break;
            }
            
            voiceBtn.classList.remove('recording');
            voiceStatus.style.display = 'none';
            this.recognition.isRecording = false;
            
            // Xatolik haqida foydalanuvchiga ma\'lumot berish
            const messagesContainer = document.getElementById('aiMessages');
            const messageDiv = document.createElement('div');
            messageDiv.className = 'ai-message';
            messageDiv.innerHTML = `
                <div class="ai-avatar">⚠️</div>
                <div class="ai-text">${errorMessage}</div>
            `;
            messagesContainer.appendChild(messageDiv);
        };

        recognition.onend = () => {
            console.log('Speech recognition ended');
            voiceBtn.classList.remove('recording');
            voiceStatus.style.display = 'none';
            if (this.recognition) {
                this.recognition.isRecording = false;
            }
        };

        try {
            recognition.start();
        } catch (error) {
            console.error('Recognition start error:', error);
            voiceBtn.classList.remove('recording');
            voiceStatus.style.display = 'none';
            alert('Ovozni boshlashda xatolik yuz berdi. Qayta urinib ko\'ring.');
        }
    }

    // Real time chat
    toggleRealTimeChat() {
        // Tarif tekshirish
        const allowedTariffs = ['Plus', 'PLUS', 'Max', 'MAX', 'Biznes', 'BIZNES', 'Oila', 'OILA',
                               'Biznes Plus', 'BIZNES PLUS', 'Biznes Max', 'BIZNES MAX',
                               'Oila Plus', 'OILA PLUS', 'Oila Max', 'OILA MAX'];
        
        if (!allowedTariffs.includes(this.data.tariff)) {
            alert('Real vaqt suhbat faqat Plus, Biznes, Oila yoki MAX tarifda mavjud!');
            return;
        }

        const realTimeBtn = document.getElementById('aiRealTimeBtn');
        const realTimeStatus = document.getElementById('aiRealTimeStatus');
        
        // Real time rejim yoqilganmi tekshirish
        if (this.isRealTimeMode) {
            // Real time rejimni o'chirish
            this.isRealTimeMode = false;
            realTimeBtn.classList.remove('active');
            realTimeStatus.style.display = 'none';
            
            // Recognition to'xtatish
            if (this.recognition && this.recognition.isRecording) {
                this.recognition.stop();
            }
            
            this.addAIMessage('Real vaqt suhbat rejimi o\'chirildi.', 'ai');
        } else {
            // Real time rejimni yoqish
            this.isRealTimeMode = true;
            realTimeBtn.classList.add('active');
            realTimeStatus.style.display = 'block';
            
            this.addAIMessage('Real vaqt suhbat rejimi yoqildi. Gapirishingiz mumkin.', 'ai');
            
            // Avtomatik ravishda ovozni eshitishni boshlash
            this.startContinuousListening();
        }
    }

    startContinuousListening() {
        if (!this.isRealTimeMode) return;
        
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            this.addAIMessage('Ovoz tanib olish funksiyasi mavjud emas.', 'ai');
            this.isRealTimeMode = false;
            return;
        }

        const recognition = new SpeechRecognition();
        recognition.lang = 'ru-RU';
        recognition.continuous = true;
        recognition.interimResults = false;

        recognition.onresult = async (event) => {
            const transcript = event.results[event.results.length - 1][0].transcript;
            
            if (transcript && this.isRealTimeMode) {
                // Foydalanuvchi savolini ko'rsatish
                this.addAIMessage(transcript, 'user');
                
                // AI javob olish
                const aiResponse = await this.getAIResponseVoice(transcript);
                
                // AI javobini ko'rsatish
                this.addAIMessage(aiResponse, 'ai');
                
                // AI javobini ovozga o'tkazish
                this.speakText(aiResponse);
            }
        };

        recognition.onerror = (event) => {
            console.error('Real time recognition error:', event.error);
            if (this.isRealTimeMode) {
                this.isRealTimeMode = false;
                document.getElementById('aiRealTimeBtn').classList.remove('active');
                document.getElementById('aiRealTimeStatus').style.display = 'none';
            }
        };

        recognition.onend = () => {
            // Agar real time rejim yoqilgan bo'lsa, qayta boshlash
            if (this.isRealTimeMode) {
                recognition.start();
            }
        };

        recognition.start();
        this.realTimeRecognition = recognition;
    }

    async getAIResponseVoice(prompt) {
        try {
            const userId = this.currentUser.id;
            const response = await this.fetchData(`/api/ai/advice?prompt=${encodeURIComponent(prompt)}&user_id=${userId}`);
            
            if (response.success) {
                return response.data.response;
            } else {
                // OpenAI quota tugagan bo'lsa, oddiy javob
                if (response.error && response.error.includes('quota')) {
                    return 'Assalomu alaykum! Men sizning moliyaviy yordamchiingizman. Balansingiz va statistikangiz haqida ma\'lumot berishga tayyorman.';
                }
                return 'Kechirasiz, javob berishda xatolik yuz berdi.';
            }
        } catch (error) {
            console.error('AI voice error:', error);
            return 'Kechirasiz, xatolik yuz berdi.';
        }
    }

    async speakText(text) {
        // Speech synthesis ni tozalash
        speechSynthesis.cancel();
        
        try {
            // Server-side OpenAI TTS API
            const response = await fetch("/api/tts", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ text: text })
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.success && data.audio) {
                    // Base64 audio ni qayta qurish
                    const audioBlob = this.base64ToBlob(data.audio, 'audio/mpeg');
                    const audioUrl = URL.createObjectURL(audioBlob);
                    const audio = new Audio(audioUrl);
                    
                    return new Promise((resolve, reject) => {
                        audio.onended = () => {
                            URL.revokeObjectURL(audioUrl);
                            resolve();
                        };
                        audio.onerror = reject;
                        audio.play();
                    });
                }
            }
        } catch (error) {
            console.log('OpenAI TTS failed, falling back to Web Speech API:', error);
        }
        
        // Fallback to Web Speech API
        if ('speechSynthesis' in window) {
            // Voices yuklanishini kutish
            return new Promise((resolve, reject) => {
                const speak = () => {
                    let lang = 'ru-RU'; // Use Russian for better voice quality
                    
                    const voices = speechSynthesis.getVoices();
                    const ruVoice = voices.find(v => v.lang.includes('ru'));
                    
                    const utterance = new SpeechSynthesisUtterance(text);
                    utterance.lang = lang;
                    
                    // Tabiiy ovoz parametrlari
                    utterance.rate = 0.9;  // Slightly slower for naturalness
                    utterance.pitch = 1.1;  // Slightly higher pitch
                    utterance.volume = 1.0;
                    
                    // Ovozni tanlash
                    if (ruVoice) {
                        utterance.voice = ruVoice;
                    }
                    
                    utterance.onend = () => resolve();
                    utterance.onerror = reject;
                    
                    speechSynthesis.speak(utterance);
                };
                
                // Voices yuklanmagan bo'lsa, kutish
                if (speechSynthesis.getVoices().length === 0) {
                    speechSynthesis.onvoiceschanged = speak;
                } else {
                    speak();
                }
            });
        }
        
        return Promise.resolve();
    }
    
    // Helper function to convert base64 to blob
    base64ToBlob(base64, mimeType) {
        const byteCharacters = atob(base64);
        const byteNumbers = new Array(byteCharacters.length);
        for (let i = 0; i < byteCharacters.length; i++) {
            byteNumbers[i] = byteCharacters.charCodeAt(i);
        }
        const byteArray = new Uint8Array(byteNumbers);
        return new Blob([byteArray], { type: mimeType });
    }
    
    // WebRTC orqali audio streaming (future implementation)
    async setupAudioStream() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                    sampleRate: 44100
                }
            });
            return stream;
        } catch (error) {
            console.error('Audio stream error:', error);
            return null;
        }
    }

    // New voice chat function for separate page
    toggleVoiceChat() {
        // Tarif tekshirish
        const allowedTariffs = ['Plus', 'PLUS', 'Max', 'MAX', 'Biznes', 'BIZNES', 'Oila', 'OILA',
                               'Biznes Plus', 'BIZNES PLUS', 'Biznes Max', 'BIZNES MAX',
                               'Oila Plus', 'OILA PLUS', 'Oila Max', 'OILA MAX'];
        
        if (!allowedTariffs.includes(this.data.tariff)) {
            alert('Real vaqt suhbat faqat Plus, Biznes, Oila yoki MAX tarifda mavjud!');
            return;
        }

        const voiceControlBtn = document.getElementById('voiceControlBtn');
        const voiceWave = document.querySelector('.voice-wave');
        const voiceStatusText = document.getElementById('voiceStatusText');
        
        if (!this.isVoiceChatActive) {
            // Voice chat ni boshlash
            this.isVoiceChatActive = true;
            voiceControlBtn.classList.add('active');
            voiceControlBtn.querySelector('.control-text').textContent = 'To\'xtatish';
            if (voiceWave) voiceWave.classList.add('active');
            
            // Mikrofon ruxsatini so'rash
            navigator.mediaDevices.getUserMedia({ audio: true })
                .then(() => {
                    voiceStatusText.textContent = '🎙️ Gapirishingiz mumkin...';
                    this.startRealTimeVoiceChat();
                })
                .catch((error) => {
                    alert('Mikrofon ruxsati rad etilgan. Iltimos, brauzer sozlamalaridan ruxsat bering.');
                    this.stopVoiceChat();
                });
        } else {
            // Voice chat ni to'xtatish
            this.stopVoiceChat();
        }
    }
    
    // Real vaqt ovozli suhbat - Web Speech API (ishlaydi!)
    async startRealTimeVoiceChat() {
        console.log('🎙️ Starting Voice Chat...');
        this.startVoiceChatRecognition();
    }
    
    setupRealTimeAudio() {
        // Mikrofon streaming
        navigator.mediaDevices.getUserMedia({ 
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                sampleRate: 24000
            }
        }).then(stream => {
            this.audioStream = stream;
            
            const audioContext = new AudioContext({ sampleRate: 24000 });
            const source = audioContext.createMediaStreamSource(stream);
            const processor = audioContext.createScriptProcessor(4096, 1, 1);
            
            source.connect(processor);
            processor.connect(audioContext.destination);
            
            processor.onaudioprocess = (e) => {
                if (!this.isVoiceChatActive || !this.realtimeWS || this.realtimeWS.readyState !== WebSocket.OPEN) return;
                
                const inputData = e.inputBuffer.getChannelData(0);
                const pcm16 = new Int16Array(inputData.length);
                
                for (let i = 0; i < inputData.length; i++) {
                    pcm16[i] = Math.max(-1, Math.min(1, inputData[i])) * 0x7fff;
                }
                
                // Base64 encode
                const base64 = btoa(String.fromCharCode(...new Uint8Array(pcm16.buffer)));
                
                // Send audio delta
                this.realtimeWS.send(JSON.stringify({
                    type: 'input_audio_buffer.append',
                    audio: base64
                }));
                
                // Input audio buffer commit
                this.realtimeWS.send(JSON.stringify({
                    type: 'input_audio_buffer.commit'
                }));
            };
            
        }).catch(error => {
            console.error('Audio setup error:', error);
            this.stopVoiceChat();
        });
    }
    
    handleRealtimeMessage(data) {
        const voiceStatusText = document.getElementById('voiceStatusText');
        
        switch (data.type) {
            case 'response.audio.delta':
                if (data.delta) {
                    this.handleAudioDelta(data.delta);
                }
                break;
                
            case 'response.audio.done':
                if (voiceStatusText) {
                    voiceStatusText.textContent = '🎙️ Eshitilmoqda...';
                }
                break;
                
            case 'response.created':
                if (voiceStatusText) {
                    voiceStatusText.textContent = '🤖 AI javob bermoqda...';
                }
                break;
                
            case 'error':
                console.error('API error:', data.error);
                alert('Xatolik: ' + (data.error.message || 'Noma\'lum xato'));
                this.stopVoiceChat();
                break;
                
            case 'session.updated':
                console.log('Session updated');
                break;
        }
    }
    
    handleAudioDelta(audioDelta) {
        // Audio delta ni decode qilish va ijro etish
        try {
            // Base64 dan blob yaratish
            const binary = atob(audioDelta);
            const bytes = new Uint8Array(binary.length);
            for (let i = 0; i < binary.length; i++) {
                bytes[i] = binary.charCodeAt(i);
            }
            const blob = new Blob([bytes], { type: 'audio/opus' });
            const audioUrl = URL.createObjectURL(blob);
            
            // Audio ijro etish
            const audio = new Audio(audioUrl);
            audio.play().then(() => {
                URL.revokeObjectURL(audioUrl);
            }).catch(e => {
                console.error('Audio play error:', e);
                URL.revokeObjectURL(audioUrl);
            });
        } catch (error) {
            console.error('Audio delta error:', error);
        }
    }

    stopVoiceChat() {
        this.isVoiceChatActive = false;
        const voiceControlBtn = document.getElementById('voiceControlBtn');
        const voiceWave = document.querySelector('.voice-wave');
        const voiceStatusText = document.getElementById('voiceStatusText');
        
        if (voiceControlBtn) {
            voiceControlBtn.classList.remove('active');
            voiceControlBtn.querySelector('.control-text').textContent = 'Suhbatni boshlash';
        }
        if (voiceWave) voiceWave.classList.remove('active');
        if (voiceStatusText) voiceStatusText.textContent = 'Suhbatni boshlash uchun tugmani bosing';
        
        // WebSocket ni yopish
        if (this.realtimeWS) {
            this.realtimeWS.close();
            this.realtimeWS = null;
        }
        
        // Speech synthesis ni to'xtatish
        if ('speechSynthesis' in window) {
            speechSynthesis.cancel();
        }
        
        // Audio stream ni to'xtatish
        if (this.audioStream) {
            this.audioStream.getTracks().forEach(track => track.stop());
            this.audioStream = null;
        }
        
        // Recognition ni to'xtatish
        if (this.voiceChatRecognition) {
            this.voiceChatRecognition.stop();
            this.voiceChatRecognition = null;
        }
    }

    async startVoiceChatRecognition() {
        // Audio stream setup
        const enableFilter = document.getElementById('enableVoiceFilter')?.checked;
        
        if (enableFilter) {
            try {
                const stream = await this.setupAudioStream();
                if (stream) {
                    this.audioStream = stream;
                    console.log('Audio stream setup completed');
                }
            } catch (error) {
                console.error('Failed to setup audio stream:', error);
            }
        }

        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            alert('Ovoz tanib olish funksiyasi mavjud emas.');
            this.stopVoiceChat();
            return;
        }

        const recognition = new SpeechRecognition();
        recognition.lang = 'ru-RU'; // O'zbek tili yo'q, rus tilidan foydalanamiz
        recognition.continuous = true; // Real vaqt uchun true
        recognition.interimResults = false; // Final results ni olish
        recognition.maxAlternatives = 1; // Faqat eng yaxshi natijani olish

        recognition.onresult = async (event) => {
            // Faqat eng oxirgi (yakunlangan) natijani olish
            const lastResult = event.results[event.results.length - 1];
            
            if (!lastResult.isFinal || !this.isVoiceChatActive) return;
            
            const transcript = lastResult[0].transcript.trim();
            
            if (!transcript) return;
            
            console.log('User said:', transcript);
            
            // Status yangilash
            const voiceStatusText = document.getElementById('voiceStatusText');
            if (voiceStatusText) {
                voiceStatusText.textContent = '🤖 AI javob berishda...';
            }
            
            try {
                // AI javob olish
                const aiResponse = await this.getAIResponseVoice(transcript);
                console.log('AI response:', aiResponse);
                
                // Status yangilash
                if (voiceStatusText) {
                    voiceStatusText.textContent = '🗣️ AI javob bermoqda...';
                }
                
                // AI javobini ovozga o'tkazish
                await this.speakText(aiResponse);
            } catch (error) {
                console.error('AI response error:', error);
            } finally {
                // Status qayta tiklash
                if (voiceStatusText && this.isVoiceChatActive) {
                    voiceStatusText.textContent = '🎙️ Gapirishingiz mumkin...';
                }
            }
        };

        recognition.onerror = (event) => {
            console.error('Voice chat recognition error:', event.error);
            
            // Agar no-speech bo'lsa, faqat log qiling va davom ettiring
            if (event.error === 'no-speech') {
                console.log('No speech detected, continuing...');
                // Hech narsa qilmaymiz, recognition avtomatik qayta ishga tushadi
                return;
            }
            
            // Agar aborted bo'lsa, bu normal (qo'lda to'xtatilgan)
            if (event.error === 'aborted') {
                console.log('Recognition aborted');
                return;
            }
            
            // Boshqa xatolar uchun to'xtatish
            const errorMessage = {
                'not-allowed': 'Mikrofon ruxsati rad etilgan',
                'no-speech': 'Ovoz topilmadi',
                'audio-capture': 'Audio yozib bo\'lmadi',
                'network': 'Tarmoq xatoligi',
                'service-not-allowed': 'Servis rad etildi'
            }[event.error] || `Xatolik: ${event.error}`;
            
            console.error(errorMessage);
            
            // Barcha xatolarga javoban to'xtatish
            this.stopVoiceChat();
        };

        recognition.onend = () => {
            // Real vaqt rejimda qayta ishga tushirish
            if (this.isVoiceChatActive) {
                setTimeout(() => {
                    if (this.isVoiceChatActive) {
                        try {
                            recognition.start();
                        } catch (error) {
                            console.error('Recognition restart error:', error);
                        }
                    }
                }, 100);
            }
        };

        recognition.start();
        this.voiceChatRecognition = recognition;
    }
}

// Initialize app
let app;
document.addEventListener('DOMContentLoaded', () => {
    app = new BalansAI();
    app.init();
});