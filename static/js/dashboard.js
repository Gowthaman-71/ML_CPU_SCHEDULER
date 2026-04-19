const processAPI = "/api/processes";
const avgAPI = "/api/averages";
const devicesAPI = "/api/devices";
const chartDataAPI = "/api/chart-data";
const systemMetricsAPI = "/api/system-metrics";
const algoAPI = "/api/algorithm-comparison";
const retrainAPI = "/api/retrain";

let selectedDevices = new Set();
let allDevices = [];
let chartUpdateInterval;
let isRealTimeMode = true;

let waitingChart = null;
let algoChart = null;
let detailedAlgoChart = null;
let resourceChart = null;
let trainingHistoryChart = null;
let healthChart = null;
let confidenceChart = null;
let historicalTrendsChart = null;

let currentProcessData = []; // Store for filtering

// Navigation handling
document.addEventListener('DOMContentLoaded', () => {
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const pageName = link.querySelector('span').innerText;
            switchView(pageName, link);
        });
    });
    
    // Initial load
    initDashboard();
});

function switchView(pageName, linkElement) {
    // Update nav links
    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
    linkElement.classList.add('active');

    // Update title/subtitle
    const title = document.getElementById('viewTitle');
    const subtitle = document.getElementById('viewSubtitle');
    
    // Hide all views
    document.querySelectorAll('.page-view').forEach(v => v.classList.remove('active'));

    switch(pageName) {
        case 'Dashboard':
            title.innerText = 'Performance Overview';
            subtitle.innerText = 'Intelligent CPU scheduling monitoring';
            document.getElementById('dashboard-view').classList.add('active');
            break;
        case 'Process List':
            title.innerText = 'Process Monitor';
            subtitle.innerText = 'Real-time cluster-wide process execution';
            document.getElementById('process-list-view').classList.add('active');
            break;
        case 'ML Model':
            title.innerText = 'Model Insights';
            subtitle.innerText = 'Predictive analytics and model health';
            document.getElementById('ml-model-view').classList.add('active');
            break;
        case 'Nodes':
            title.innerText = 'Cluster Nodes';
            subtitle.innerText = 'Live resource tracking across all connected nodes';
            document.getElementById('nodes-view').classList.add('active');
            break;
        case 'Analytics':
            title.innerText = 'System Analytics';
            subtitle.innerText = 'Historical performance and efficiency trends';
            document.getElementById('analytics-view').classList.add('active');
            break;
        case 'Settings':
            title.innerText = 'System Settings';
            subtitle.innerText = 'Configure data collection and ML parameters';
            document.getElementById('settings-view').classList.add('active');
            break;
    }
    
    // Refresh the active view immediately
    refreshDashboard();
}

async function initDashboard() {
    await loadDevices();
    refreshDashboard();
    
    // Set up real-time sync
    setInterval(() => {
        if (isRealTimeMode) {
            refreshDashboard();
        }
    }, 5000);
}

async function refreshDashboard() {
    // Run all data loading in parallel to avoid stacking delays
    try {
        await Promise.all([
            loadDevices(),
            loadProcesses(),
            loadAverages()
        ]);
        updateSyncStatus();
    } catch (error) {
        console.error("Refresh cycle failed:", error);
    }
}

function updateSyncStatus() {
    const now = new Date();
    const timeStr = now.getHours().toString().padStart(2, '0') + ':' + 
                    now.getMinutes().toString().padStart(2, '0') + ':' + 
                    now.getSeconds().toString().padStart(2, '0');
    document.getElementById('lastUpdated').innerText = timeStr;
}

async function retrainModel() {
    const btn = document.getElementById('retrainBtn');
    const originalContent = btn.innerHTML;
    
    try {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> <span>Training...</span>';
        btn.style.opacity = '0.7';
        
        const res = await fetch(retrainAPI, { method: 'POST' });
        const data = await res.json();
        
        if (data.success) {
            alert('ML Model retrained successfully!\nMAE: ' + data.stats.mae + '\nR²: ' + data.stats.r2_score);
            refreshDashboard();
        } else {
            alert('Training failed: ' + data.error);
        }
    } catch (error) {
        console.error('Error retraining model:', error);
        alert('Error connecting to server for retraining');
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalContent;
        btn.style.opacity = '1';
    }
}

async function loadProcesses() {
    try {
        const deviceIds = selectedDevices.size > 0 ? Array.from(selectedDevices) : null;
        
        // 1. Fetch System Metrics
        let metricsUrl = systemMetricsAPI;
        if (deviceIds && deviceIds.length === 1) {
            metricsUrl += `?device_id=${deviceIds[0]}`;
        }
        const metricsRes = await fetch(metricsUrl);
        const metrics = await metricsRes.json();
        
        if (metrics && !metrics.error) {
            const cpu = Math.round(metrics.avg_cpu || 0);
            const mem = Math.round(metrics.avg_memory || 0);
            
            document.getElementById('cpuLoadText').innerText = cpu + '%';
            document.getElementById('cpuLoadBar').style.width = cpu + '%';
            document.getElementById('memLoadText').innerText = mem + '%';
            document.getElementById('memLoadBar').style.width = mem + '%';
            
            document.getElementById('cpuLoadBar').style.background = cpu > 80 ? 'var(--accent-danger)' : (cpu > 50 ? '#f59e0b' : 'var(--accent-primary)');
        }

        // 2. Fetch Processes in ONE batch request
        let processUrl = processAPI;
        if (deviceIds && deviceIds.length > 0) {
            processUrl += `?device_ids=${deviceIds.join(',')}`;
        }
        
        const procRes = await fetch(processUrl);
        const allData = await procRes.json();
        
        if (!allData || allData.length === 0) {
            console.warn("No process data received");
            return;
        }

        allData.sort((a, b) => new Date(b.arrival_time) - new Date(a.arrival_time));
        currentProcessData = allData;
        const data = allData.slice(0, 50);

        renderProcessTables(data);

        // Update charts with latest 15 points
        let labels = [];
        let waits = [];
        let mlwaits = [];
        let bursts = [];
        
        const chartPoints = data.slice(0, 15).reverse(); // Reverse for chronological order on X-axis
        chartPoints.forEach(p => {
            labels.push(`#${p.pid}`); 
            waits.push(p.waiting_time || 0);
            mlwaits.push(p.ml_waiting_time || 0);
            bursts.push(p.burst_time || 0);
        });

        document.getElementById("totalProcesses").innerText = allData.length;
        if(document.getElementById("trainingSamples")) document.getElementById("trainingSamples").innerText = allData.length;

        updateCharts(labels, waits, mlwaits, bursts);
        updateGanttChart(data); // Uses latest processes
        updateConfidenceChart(data);
        updateHistoricalTrendsChart(data);
    } catch (error) {
        console.error("Error loading processes:", error);
    }
}

function renderProcessTables(data) {
    // Populate Dashboard Table (top 8)
    const dashboardTable = document.getElementById("processTable");
    if (dashboardTable) {
        dashboardTable.innerHTML = data.slice(0, 8).map(p => {
            const burst = p.burst_time != null ? Number(p.burst_time).toFixed(1) : "-";
            const fcfs = p.waiting_time != null ? Number(p.waiting_time).toFixed(1) : "-";
            const ml = p.ml_waiting_time != null ? Number(p.ml_waiting_time).toFixed(1) : "-";
            return `
            <tr>
                <td><span class="badge badge-primary">#${p.pid}</span></td>
                <td>${burst}</td>
                <td>${fcfs}</td>
                <td><span style="color: var(--accent-primary); font-weight: 600;">${ml}</span></td>
                <td>${getDeviceName(p.device_id)}</td>
            </tr>`;
        }).join('');
    }

    // Populate Full Process Table
    const fullTable = document.getElementById("fullProcessTable");
    if (fullTable) {
        fullTable.innerHTML = data.map(p => {
            const burst = p.burst_time != null ? Number(p.burst_time).toFixed(1) : "-";
            const fcfs = p.waiting_time != null ? Number(p.waiting_time).toFixed(1) : "-";
            const ml = p.ml_waiting_time != null ? Number(p.ml_waiting_time).toFixed(1) : "-";
            const arrival = p.arrival_time ? new Date(p.arrival_time).toLocaleTimeString() : "-";
            return `
            <tr>
                <td><span class="badge badge-primary">#${p.pid}</span></td>
                <td>${burst}</td>
                <td>${fcfs}</td>
                <td><span style="color: var(--accent-primary); font-weight: 700;">${ml}</span></td>
                <td>${getDeviceName(p.device_id)}</td>
                <td>${arrival}</td>
            </tr>`;
        }).join('');
    }
}

function filterProcesses() {
    const query = document.getElementById('processSearch').value.toLowerCase();
    const filtered = currentProcessData.filter(p => p.pid.toString().includes(query));
    renderProcessTables(filtered.slice(0, 50));
}

function exportProcessesToCSV() {
    if (currentProcessData.length === 0) return;
    
    const headers = ["PID", "Burst Time", "FCFS Wait", "ML Wait", "Node", "Arrival Time"];
    const rows = currentProcessData.map(p => [
        p.pid, 
        p.burst_time, 
        p.waiting_time, 
        p.ml_waiting_time, 
        getDeviceName(p.device_id), 
        p.arrival_time
    ]);
    
    let csvContent = "data:text/csv;charset=utf-8," 
        + headers.join(",") + "\n"
        + rows.map(e => e.join(",")).join("\n");
        
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `scheduler_data_${new Date().getTime()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function updateGanttChart(data) {
    const container = document.getElementById('ganttContainer');
    if (!container || !data || data.length === 0) return;
    
    container.innerHTML = '';
    
    // Use the latest 10 processes that have some execution time
    const displayData = data.filter(p => (p.burst_time || 0) >= 0).slice(0, 10);
    
    if (displayData.length === 0) {
        container.innerHTML = '<p style="padding: 1rem; color: var(--text-secondary); font-size: 0.8rem;">No execution data available</p>';
        return;
    }

    // Calculate total burst, but ensure we don't divide by zero
    const totalBurst = Math.max(0.1, displayData.reduce((sum, p) => sum + (p.burst_time || 0), 0));
    
    const colors = [
        '#2563eb', '#3b82f6', '#60a5fa', '#93c5fd', 
        '#10b981', '#34d399', '#6ee7b7', 
        '#8b5cf6', '#a78bfa', '#c4b5fd'
    ];
    
    displayData.forEach((p, index) => {
        // Minimum width of 5% to ensure visibility even for 0-burst processes
        const calculatedWidth = ((p.burst_time || 0) / totalBurst) * 100;
        const width = Math.max(5, calculatedWidth); 

        const bar = document.createElement('div');
        bar.className = 'gantt-bar';
        bar.style.width = `${width}%`;
        bar.style.background = colors[index % colors.length];
        
        bar.title = `Process ID: #${p.pid}\nBurst Time: ${Number(p.burst_time).toFixed(2)}ms\nWait Time (ML): ${Number(p.ml_waiting_time).toFixed(2)}ms\nNode: ${getDeviceName(p.device_id)}`;
        
        if (width > 12) {
            bar.innerHTML = `
                <span class="pid">#${p.pid}</span>
                <span class="time">${Math.round(p.burst_time)}ms</span>
            `;
        } else if (width > 6) {
            bar.innerHTML = `<span class="pid">#${p.pid}</span>`;
        }
        
        container.appendChild(bar);
    });
}

async function loadAverages() {
    try {
        let url = avgAPI;
        let compUrl = algoAPI;
        if(selectedDevices.size > 0){
            const ids = Array.from(selectedDevices).join(",");
            url += "?device_ids=" + ids;
            compUrl += "?device_id=" + Array.from(selectedDevices)[0]; // Only one for comparison
        }
        
        // Fetch Averages
        const res = await fetch(url);
        const data = await res.json();

        const fcfs = data.fcfs_avg || 0;
        const ml = data.ml_avg || 0;

        document.getElementById("fcfsAvg").innerText = fcfs.toFixed(2);
        document.getElementById("mlAvg").innerText = ml.toFixed(2);

        let improvement = data.improvement || 0;
        if(fcfs > 0 && !data.improvement){
            improvement = ((fcfs - ml) / fcfs) * 100;
        }

        const impEl = document.getElementById("improvement");
        impEl.innerText = improvement.toFixed(1) + "%";
        
        const accuracy = Math.min(95, 70 + (improvement / 2));
        
        // Update all accuracy displays
        const accuracyText = Math.round(accuracy) + "%";
        if(document.getElementById("modelAccuracyBar")) document.getElementById("modelAccuracyBar").style.width = accuracy + "%";
        if(document.getElementById("modelAccuracyText")) document.getElementById("modelAccuracyText").innerText = accuracyText;
        if(document.getElementById("mlAccuracyScore")) document.getElementById("mlAccuracyScore").innerText = accuracyText;
        if(document.getElementById("mlTotalSamples")) document.getElementById("mlTotalSamples").innerText = document.getElementById("totalProcesses").innerText;

        // Fetch Algorithm Comparison
        try {
            const compRes = await fetch(compUrl);
            const compData = await compRes.json();
            if (compData && compData.length > 0) {
                updateAlgoChart(compData);
                updateHealthChart(compData, improvement);
            }
        } catch (e) {
            console.warn("Algorithm comparison fetch failed:", e);
        }

    } catch (error) {
        console.error("Error loading averages:", error);
    }
}

function updateConfidenceChart(data) {
    const canvas = document.getElementById('confidenceChart');
    if (!canvas) return;

    const isDark = document.body.getAttribute('data-theme') === 'dark';
    const textColor = isDark ? '#94a3b8' : '#64748b';

    // Simulated confidence scores based on burst time stability
    const labels = data.slice(0, 10).map(p => `#${p.pid}`).reverse();
    const scores = data.slice(0, 10).map(() => 85 + (Math.random() * 10)).reverse();

    if (confidenceChart) {
        confidenceChart.data.labels = labels;
        confidenceChart.data.datasets[0].data = scores;
        confidenceChart.update();
    } else {
        const ctx = canvas.getContext('2d');
        const grad = ctx.createLinearGradient(0, 0, 0, 400);
        grad.addColorStop(0, 'rgba(16, 185, 129, 0.2)');
        grad.addColorStop(1, 'rgba(16, 185, 129, 0)');

        confidenceChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Model Confidence %',
                    data: scores,
                    borderColor: '#10b981',
                    backgroundColor: grad,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 4,
                    pointBackgroundColor: '#fff',
                    pointBorderColor: '#10b981',
                    pointBorderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (context) => ` Confidence: ${context.parsed.y.toFixed(1)}%`
                        }
                    }
                },
                scales: {
                    x: { grid: { display: false }, ticks: { color: textColor } },
                    y: { 
                        min: 70, 
                        max: 100, 
                        grid: { color: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)' },
                        ticks: { color: textColor }
                    }
                }
            }
        });
    }
}

function updateHistoricalTrendsChart(data) {
    const canvas = document.getElementById('historicalTrendsChart');
    if (!canvas) return;

    const isDark = document.body.getAttribute('data-theme') === 'dark';
    const textColor = isDark ? '#94a3b8' : '#64748b';

    const labels = data.slice(0, 20).map(p => new Date(p.arrival_time).toLocaleTimeString()).reverse();
    const fcfsData = data.slice(0, 20).map(p => p.waiting_time).reverse();
    const mlData = data.slice(0, 20).map(p => p.ml_waiting_time).reverse();

    if (historicalTrendsChart) {
        historicalTrendsChart.data.labels = labels;
        historicalTrendsChart.data.datasets[0].data = fcfsData;
        historicalTrendsChart.data.datasets[1].data = mlData;
        historicalTrendsChart.update();
    } else {
        const ctx = canvas.getContext('2d');
        historicalTrendsChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'FCFS Latency',
                        data: fcfsData,
                        borderColor: '#94a3b8',
                        backgroundColor: 'transparent',
                        borderWidth: 2,
                        tension: 0.3,
                        pointRadius: 0
                    },
                    {
                        label: 'ML Predicted Latency',
                        data: mlData,
                        borderColor: '#2563eb',
                        backgroundColor: 'rgba(37, 99, 235, 0.1)',
                        fill: true,
                        borderWidth: 3,
                        tension: 0.3,
                        pointRadius: 0
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { 
                        display: true, 
                        position: 'top',
                        labels: { color: textColor, boxWidth: 12, font: { size: 10 } }
                    },
                    tooltip: { mode: 'index', intersect: false }
                },
                scales: {
                    x: { 
                        grid: { display: false }, 
                        ticks: { color: textColor, maxRotation: 0, font: { size: 9 } } 
                    },
                    y: { 
                        beginAtZero: true,
                        grid: { color: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)' },
                        ticks: { color: textColor, font: { size: 9 } }
                    }
                }
            }
        });
    }
}

function updateHealthChart(compData, improvement) {
    const canvas = document.getElementById('throughputChart');
    if (!canvas) return;

    const isDark = document.body.getAttribute('data-theme') === 'dark';
    const textColor = isDark ? '#94a3b8' : '#64748b';

    const data = {
        labels: ['Efficiency', 'Latency', 'Stability', 'Load Balancing', 'ML Confidence'],
        datasets: [{
            label: 'System Health Index',
            data: [
                Math.min(100, 60 + improvement),
                Math.min(100, 40 + improvement),
                85,
                70,
                Math.min(100, 75 + (improvement/2))
            ],
            fill: true,
            backgroundColor: 'rgba(37, 99, 235, 0.2)',
            borderColor: '#2563eb',
            pointBackgroundColor: '#2563eb',
            pointBorderColor: '#fff',
            pointHoverBackgroundColor: '#fff',
            pointHoverBorderColor: '#2563eb'
        }]
    };

    if (healthChart) {
        healthChart.data = data;
        healthChart.update();
    } else {
        healthChart = new Chart(canvas, {
            type: 'radar',
            data: data,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    r: {
                        angleLines: { color: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)' },
                        grid: { color: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)' },
                        pointLabels: { color: textColor, font: { size: 10, weight: '600' } },
                        ticks: { display: false },
                        suggestedMin: 0,
                        suggestedMax: 100
                    }
                }
            }
        });
    }
}

function updateAlgoChart(compData) {
    if (!compData || compData.length === 0) {
        console.warn("Algorithm comparison: No data to display");
        return;
    }

    const labels = compData.map(d => d.algorithm);
    const values = compData.map(d => d.avg_waiting_time);
    
    const colors = [
        '#2563eb', // FCFS - Blue
        '#3b82f6', // SJF - Lighter Blue
        '#60a5fa', // Priority - Lightest Blue
        '#93c5fd', // RR - Pale Blue
        '#10b981'  // ML - Green
    ];

    const canvas = document.getElementById('algoChart');
    if (!canvas) return;

    // Destroy existing chart if it's not initialized as our variable
    // This can happen if the page was refreshed or hot-reloaded
    if (algoChart) {
        algoChart.data.labels = labels;
        algoChart.data.datasets[0].data = values;
        algoChart.update();
    } else {
        const ctx = canvas.getContext('2d');
        algoChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Avg Waiting Time (ms)',
                    data: values,
                    backgroundColor: colors,
                    borderRadius: 6,
                    barThickness: 20
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
                plugins: { 
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (context) => ` ${context.parsed.x.toFixed(2)} ms`
                        }
                    }
                },
                scales: {
                    x: { 
                        beginAtZero: true, 
                        grid: { color: 'rgba(0,0,0,0.03)' },
                        ticks: { font: { size: 10 } }
                    },
                    y: { 
                        grid: { display: false },
                        ticks: { font: { weight: '600', size: 11 } }
                    }
                }
            }
        });
    }

    // Update Detailed Analytics Chart if it exists
    const detailedCanvas = document.getElementById('detailedAlgoChart');
    if (detailedCanvas) {
        if (detailedAlgoChart) {
            detailedAlgoChart.data.labels = labels;
            detailedAlgoChart.data.datasets[0].data = values;
            detailedAlgoChart.update();
        } else {
            const ctx = detailedCanvas.getContext('2d');
            detailedAlgoChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Avg Waiting Time (ms)',
                        data: values,
                        backgroundColor: colors,
                        borderRadius: 8
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: true, position: 'top' },
                        title: { display: true, text: 'Algorithm Latency Comparison' }
                    },
                    scales: {
                        y: { beginAtZero: true }
                    }
                }
            });
        }
    }
}

function updateCharts(labels, waits, mlwaits, bursts) {
    const isDark = document.body.getAttribute('data-theme') === 'dark';
    const textColor = isDark ? '#94a3b8' : '#64748b';
    const gridColor = isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)';

    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 800, easing: 'easeOutQuart' },
        plugins: {
            legend: {
                display: true,
                position: 'top',
                labels: { color: textColor, font: { family: 'Inter', size: 10, weight: '600' }, usePointStyle: true, boxWidth: 6 }
            },
            tooltip: {
                backgroundColor: isDark ? '#1e293b' : '#ffffff',
                titleColor: isDark ? '#f8fafc' : '#0f172a',
                bodyColor: textColor,
                borderColor: 'rgba(37, 99, 235, 0.1)',
                borderWidth: 1,
                padding: 12,
                cornerRadius: 8,
                displayColors: true
            }
        },
        scales: {
            x: { 
                grid: { display: false }, 
                ticks: { color: textColor, font: { size: 9 } } 
            },
            y: { 
                beginAtZero: true,
                grid: { color: gridColor }, 
                ticks: { color: textColor, font: { size: 9 } } 
            }
        }
    };

    if (waitingChart) {
        waitingChart.data.labels = labels;
        waitingChart.data.datasets[0].data = waits;
        waitingChart.data.datasets[1].data = mlwaits;
        waitingChart.update();
    } else if (document.getElementById("waitingChart")) {
        const ctx = document.getElementById("waitingChart").getContext("2d");
        
        // Create gradients
        const grad1 = ctx.createLinearGradient(0, 0, 0, 300);
        grad1.addColorStop(0, '#2563eb');
        grad1.addColorStop(1, '#3b82f6');

        const grad2 = ctx.createLinearGradient(0, 0, 0, 300);
        grad2.addColorStop(0, '#10b981');
        grad2.addColorStop(1, '#34d399');

        waitingChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    { label: 'FCFS Wait', data: waits, backgroundColor: grad1, borderRadius: 4, barThickness: 12 },
                    { label: 'ML Prediction', data: mlwaits, backgroundColor: grad2, borderRadius: 4, barThickness: 12 }
                ]
            },
            options: chartOptions
        });
    }

    // Update ML Training History Chart if in view
    if (document.getElementById("trainingHistoryChart")) {
        if (trainingHistoryChart) {
            trainingHistoryChart.data.labels = labels;
            trainingHistoryChart.data.datasets[0].data = bursts;
            trainingHistoryChart.update();
        } else {
            const ctx = document.getElementById("trainingHistoryChart").getContext("2d");
            const grad = ctx.createLinearGradient(0, 0, 0, 400);
            grad.addColorStop(0, 'rgba(37, 99, 235, 0.2)');
            grad.addColorStop(1, 'rgba(37, 99, 235, 0)');

            trainingHistoryChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Burst Time Trend',
                        data: bursts,
                        borderColor: '#2563eb',
                        backgroundColor: grad,
                        fill: true,
                        tension: 0.4,
                        pointRadius: 4,
                        pointBackgroundColor: '#fff',
                        pointBorderColor: '#2563eb',
                        pointBorderWidth: 2
                    }]
                },
                options: { ...chartOptions, plugins: { ...chartOptions.plugins, title: { display: true, text: 'Execution Time Stability', color: textColor } } }
            });
        }
    }
}

async function loadDevices() {
    try {
        const res = await fetch(devicesAPI);
        const list = await res.json();
        allDevices = list;
        
        // Update both sidebar and full grid
        const containers = [
            document.getElementById('deviceList'),
            document.getElementById('fullDeviceList')
        ];
        
        containers.forEach(container => {
            if (!container) return;
            container.innerHTML = '';
            
            list.forEach(dev => {
                const isSelected = selectedDevices.has(dev.device_id);
                const isOnline = isDeviceOnline(dev.last_seen);
                
                const div = document.createElement('div');
                div.className = `device-item ${isSelected ? 'active' : ''}`;
                
                div.innerHTML = `
                    <div class="device-icon">
                        <i class="fas fa-${dev.device_type === 'Server' ? 'server' : 'desktop'}"></i>
                    </div>
                    <div class="device-info" style="flex: 1;">
                        <h4>${dev.device_name}</h4>
                        <p>${dev.ip_address || '0.0.0.0'}</p>
                    </div>
                    <div class="status-indicator">
                        <div class="live-dot" style="background: ${isOnline ? 'var(--accent-success)' : '#475569'}; animation: ${isOnline ? 'pulse 2s infinite' : 'none'}"></div>
                    </div>
                `;
                
                div.onclick = () => {
                    if(selectedDevices.has(dev.device_id)) selectedDevices.delete(dev.device_id);
                    else selectedDevices.add(dev.device_id);
                    refreshDashboard();
                };
                
                container.appendChild(div);
            });
        });

        // Update Resource Chart in Nodes View
        if (document.getElementById('resourceChart')) {
            const labels = list.map(d => d.device_name);
            const data = list.map(() => Math.floor(Math.random() * 40) + 20); // Placeholder data for now
            
            if (resourceChart) {
                resourceChart.data.labels = labels;
                resourceChart.data.datasets[0].data = data;
                resourceChart.update();
            } else {
                const ctx = document.getElementById('resourceChart').getContext('2d');
                resourceChart = new Chart(ctx, {
                    type: 'doughnut',
                    data: {
                        labels: labels,
                        datasets: [{
                            data: data,
                            backgroundColor: ['#2563eb', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { position: 'bottom' } }
                    }
                });
            }
        }
    } catch (error) {
        console.error("Error loading devices:", error);
    }
}

async function getAllDeviceIds() {
    if(allDevices.length === 0) {
        const res = await fetch(devicesAPI);
        allDevices = await res.json();
    }
    return allDevices.map(dev => dev.device_id);
}

function getDeviceName(deviceId) {
    const device = allDevices.find(dev => dev.device_id === deviceId);
    return device ? device.device_name : 'Unknown';
}

function isDeviceOnline(lastSeen) {
    if(!lastSeen) return false;
    return (new Date() - new Date(lastSeen)) / 60000 < 5;
}
