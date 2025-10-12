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
            tariff: 'FREE',
            limits: {}
        };
        this.charts = {};
    }

    async init() {
        try {
            console.log('BalansAI initializing...');
            
            // Telegram WebApp tekshirish
            if (window.Telegram && window.Telegram.WebApp) {
                window.Telegram.WebApp.ready();
                window.Telegram.WebApp.expand();
                
                const user = window.Telegram.WebApp.initDataUnsafe?.user;
                if (user) {
                    this.currentUser = {
                        id: user.id,
                        first_name: user.first_name,
                        last_name: user.last_name,
                        username: user.username
                    };
                    console.log('Telegram user:', this.currentUser);
                }
            } else {
                // Test rejimi
                this.currentUser = { id: 123456789, first_name: 'Test User' };
                console.log('Test mode activated');
            }

            // Ma'lumotlarni yuklash
            await this.loadAllData();
            
            // UI ni yangilash
            this.updateUI();
            
            // Event listeners
            this.setupEventListeners();
            
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
            const [statistics, debts, tariff] = await Promise.all([
                this.fetchData(`/api/statistics/${userId}`),
                this.fetchData(`/api/debts/${userId}`),
                this.fetchData(`/api/user/tariff/${userId}`)
            ]);

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
                this.data.tariff = tariff.data.tariff || 'FREE';
                this.data.limits = tariff.data.limits || {};
            }

            console.log('Data loaded:', this.data);
            
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
        this.updateCharts();
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
        
        if (this.data.tariff === 'FREE') {
            if (analyticsLock) analyticsLock.style.display = 'block';
            if (aiLock) aiLock.style.display = 'block';
        } else if (this.data.tariff === 'PREMIUM') {
            if (analyticsLock) analyticsLock.style.display = 'none';
            if (aiLock) aiLock.style.display = 'block';
        } else if (this.data.tariff === 'MAX') {
            if (analyticsLock) analyticsLock.style.display = 'none';
            if (aiLock) aiLock.style.display = 'none';
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
        if (this.data.tariff === 'FREE') {
            this.createBasicChart();
            this.lockPremiumCharts();
        } else if (this.data.tariff === 'PREMIUM') {
            this.createPremiumCharts();
            this.lockMaxCharts();
        } else if (this.data.tariff === 'MAX') {
            this.createMaxCharts();
        }
    }

    lockPremiumCharts() {
        // Premium grafiklarni qulf qilish
        const premiumCharts = [
            'categoryChart', 'dailyChart', 'weeklyChart', 'incomeExpenseChart',
            'topExpensesChart', 'monthlyTrendChart', 'categoryDistributionChart',
            'yearlyChart', 'debtsChart', 'balanceChangeChart'
        ];
        
        premiumCharts.forEach(chartId => {
            const container = document.getElementById(chartId)?.parentElement;
            if (container) {
                container.innerHTML = `
                    <div class="chart-locked">
                        <div class="lock-icon">🔒</div>
                        <h4>Premium kerak</h4>
                        <p>Bu grafikni ko'rish uchun Premium tarifni sotib oling</p>
                        <button class="btn-primary" onclick="app.upgradeToPremium()">Premium sotib olish</button>
                    </div>
                `;
            }
        });
    }

    lockMaxCharts() {
        // MAX grafiklarni qulf qilish
        const maxCharts = [
            'topExpensesChart', 'monthlyTrendChart', 'categoryDistributionChart',
            'yearlyChart', 'debtsChart', 'balanceChangeChart'
        ];
        
        maxCharts.forEach(chartId => {
            const container = document.getElementById(chartId)?.parentElement;
            if (container) {
                container.innerHTML = `
                    <div class="chart-locked">
                        <div class="lock-icon">🔒</div>
                        <h4>MAX kerak</h4>
                        <p>Bu grafikni ko'rish uchun MAX tarifni sotib oling</p>
                        <button class="btn-primary" onclick="app.upgradeToMax()">MAX sotib olish</button>
                    </div>
                `;
            }
        });
    }

    createBasicChart() {
        // Faqat asosiy grafik
        this.createMonthlyChart();
    }

    createPremiumCharts() {
        // Premium grafiklar
        this.createMonthlyChart();
        this.createCategoryChart();
        this.createDailyChart();
        this.createWeeklyChart();
        this.createIncomeExpenseChart();
    }

    createMaxCharts() {
        // Barcha grafiklar
        this.createMonthlyChart();
        this.createCategoryChart();
        this.createDailyChart();
        this.createWeeklyChart();
        this.createIncomeExpenseChart();
        this.createTopExpensesChart();
        this.createMonthlyTrendChart();
        this.createCategoryDistributionChart();
        this.createYearlyChart();
        this.createDebtsChart();
        this.createBalanceChangeChart();
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
                .filter(t => t.type === 'income')
                .reduce((sum, t) => sum + t.amount, 0);
            
            const expense = monthTransactions
                .filter(t => t.type === 'expense')
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
            if (transaction.type === 'expense') {
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
                .filter(t => t.type === 'income')
                .reduce((sum, t) => sum + t.amount, 0);
            
            const expense = weekTransactions
                .filter(t => t.type === 'expense')
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
            
            if (transaction.type === 'income') {
                categoryStats[category].income += transaction.amount;
            } else if (transaction.type === 'expense') {
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
            if (transaction.type === 'expense') {
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
            if (transaction.type === 'expense') {
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

        // AI chat
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
        }

        // Show corresponding content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        
        const tabContent = document.getElementById(tabName);
        if (tabContent) {
            tabContent.classList.add('active');
        }

        this.currentTab = tabName;
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
        // MAX tarif tekshirish
        if (this.data.tariff !== 'MAX') {
            alert('AI suhbat faqat MAX tarifda mavjud. MAX tarifni sotib oling!');
            return;
        }

        const input = document.getElementById('aiInput');
        const message = input.value.trim();
        
        if (!message) return;
        
        // Disable input
        input.disabled = true;
        document.getElementById('aiSendBtn').disabled = true;
        
        // Add user message
        this.addAIMessage(message, 'user');
        input.value = '';
        
        // Send to AI
        try {
            const response = await this.fetchData(`/api/ai/advice?prompt=${encodeURIComponent(message)}`);
            
            if (response.success) {
                this.addAIMessage(response.data.response, 'ai');
            } else {
                this.addAIMessage('Kechirasiz, xatolik yuz berdi. Qayta urinib ko\'ring.', 'ai');
            }
        } catch (error) {
            console.error('AI error:', error);
            this.addAIMessage('Kechirasiz, xatolik yuz berdi. Qayta urinib ko\'ring.', 'ai');
        }
        
        // Enable input
        input.disabled = false;
        document.getElementById('aiSendBtn').disabled = false;
    }

    addAIMessage(message, sender) {
        const messagesContainer = document.getElementById('aiMessages');
        const messageDiv = document.createElement('div');
        messageDiv.className = 'ai-message';
        
        if (sender === 'user') {
            messageDiv.innerHTML = `
                <div class="ai-avatar">👤</div>
                <div class="ai-text">${message}</div>
            `;
        } else {
            messageDiv.innerHTML = `
                <div class="ai-avatar">🤖</div>
                <div class="ai-text">${message}</div>
            `;
        }
        
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
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
}

// Initialize app
let app;
document.addEventListener('DOMContentLoaded', () => {
    app = new BalansAI();
    app.init();
});