/**
 * Performance Problem Simulator - Dashboard JavaScript (Python Edition)
 * Matching .NET Core version functionality
 */

// ==========================================================================
// Configuration & State
// ==========================================================================

const CONFIG = {
    maxDataPoints: 240,  // 1 minute of data at 250ms intervals
    maxLatencyDataPoints: 600, // 60 seconds of probe data
    latencyProbeIntervalMs: 100,
    latencyTimeoutMs: 30000,
    reconnectDelayMs: 2000,
    apiBaseUrl: '/api'
};

// Probe visualization history (24-dot indicator)
const probeHistory = [];
const MAX_PROBE_DOTS = 24;

const state = {
    wsConnection: null,
    charts: {},
    metricsHistory: {
        timestamps: [],
        cpu: [],
        memory: [],
        threads: [],
        eventLoopLag: []
    },
    latencyHistory: {
        timestamps: [],
        values: [],
        isTimeout: [],
        isError: []
    },
    latencyStats: {
        timeoutCount: 0
    },
    activeSimulations: new Map(),
    lastProcessId: null
};

// ==========================================================================
// UTC Time Formatting
// ==========================================================================

function formatUtcTime(date) {
    if (!date || !(date instanceof Date)) return '';
    const hours = date.getUTCHours().toString().padStart(2, '0');
    const minutes = date.getUTCMinutes().toString().padStart(2, '0');
    const seconds = date.getUTCSeconds().toString().padStart(2, '0');
    return `${hours}:${minutes}:${seconds}`;
}

function getCurrentUtcTime() {
    return formatUtcTime(new Date());
}

// ==========================================================================
// WebSocket Connection
// ==========================================================================

function initializeWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/metrics`;
    
    updateConnectionStatus('connecting', 'Connecting...');
    
    try {
        state.wsConnection = new WebSocket(wsUrl);
        
        state.wsConnection.onopen = () => {
            updateConnectionStatus('connected', 'Connected');
            logEvent('system', 'Connected to metrics hub');
        };
        
        state.wsConnection.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                handleMetricsUpdate(data);
            } catch (e) {
                console.error('Failed to parse WebSocket message:', e);
            }
        };
        
        state.wsConnection.onclose = (event) => {
            updateConnectionStatus('disconnected', 'Disconnected');
            logEvent('system', 'Connection closed. Attempting to reconnect...');
            setTimeout(initializeWebSocket, CONFIG.reconnectDelayMs);
        };
        
        state.wsConnection.onerror = (error) => {
            console.error('WebSocket error:', error);
            updateConnectionStatus('disconnected', 'Connection error');
        };
    } catch (e) {
        console.error('Failed to create WebSocket:', e);
        updateConnectionStatus('disconnected', 'Failed to connect');
        setTimeout(initializeWebSocket, CONFIG.reconnectDelayMs);
    }
}

function updateConnectionStatus(status, text) {
    const indicator = document.getElementById('connectionIndicator');
    const textEl = document.getElementById('connectionText');
    
    if (indicator) {
        indicator.className = `indicator ${status}`;
    }
    if (textEl) {
        textEl.textContent = text;
    }
}

// ==========================================================================
// Metrics Handling
// ==========================================================================

function handleMetricsUpdate(message) {
    // Extract metrics from the WebSocket message structure
    const data = message.data || message;
    const systemData = data.system || {};
    const processData = data.process || {};
    const asyncioData = data.asyncio || {};
    const simulationsData = data.simulations || {};
    
    // Update metric cards
    const cpuPercent = processData.cpu_percent || systemData.cpu_percent || 0;
    const memoryMb = processData.memory_mb || 0;
    const totalMemoryMb = systemData.memory_total_mb || 1000;
    const threadCount = processData.threads || 1;
    const pendingTasks = asyncioData.pending_tasks || 0;
    const eventLoopLagMs = asyncioData.event_loop_lag_ms || 0;
    const activeSimulations = simulationsData.items || [];

    updateMetricCard('cpu', cpuPercent, '%', 100);
    updateMetricCard('memory', memoryMb, 'MB', totalMemoryMb);
    updateMetricCard('threads', threadCount, 'threads', 100);
    updateMetricCard('queue', pendingTasks, 'tasks', 50);

    // Update total memory display
    const totalMemoryEl = document.getElementById('memoryTotal');
    if (totalMemoryEl && totalMemoryMb) {
        const totalFormatted = totalMemoryMb >= 1024 
            ? (totalMemoryMb / 1024).toFixed(1) + ' GB'
            : Math.round(totalMemoryMb) + ' MB';
        totalMemoryEl.textContent = `of ${totalFormatted}`;
    }

    // Update history for charts
    const timestamp = new Date();
    addToHistory(timestamp, cpuPercent, memoryMb, threadCount, eventLoopLagMs);
    
    // Update charts
    updateCharts();
    
    // Handle latency if present
    if (message.latency_ms !== undefined) {
        handleLatencyUpdate({
            timestamp: timestamp,
            latencyMs: message.latency_ms,
            isTimeout: message.latency_ms >= CONFIG.latencyTimeoutMs,
            isError: false
        });
    }
    
    // Update active simulations
    if (activeSimulations.length > 0) {
        updateSimulationsList(activeSimulations);
    }
    
    // Update last update time
    const lastUpdateEl = document.getElementById('lastUpdate');
    if (lastUpdateEl) {
        lastUpdateEl.textContent = formatUtcTime(timestamp) + ' UTC';
    }
}

function updateMetricCard(type, value, unit, maxForBar) {
    const valueEl = document.getElementById(`${type}Value`);
    const barEl = document.getElementById(`${type}Bar`);
    
    if (!valueEl) return;
    
    const card = valueEl.closest('.metric-card');
    
    // Format value
    const displayValue = typeof value === 'number' ? 
        (value < 10 ? value.toFixed(1) : Math.round(value)) : '--';
    valueEl.textContent = displayValue;
    
    // Update bar
    if (barEl) {
        const barPercent = Math.min(100, (value / maxForBar) * 100);
        barEl.style.width = `${barPercent}%`;
    }
    
    // Warning states based on percentage of max
    if (card) {
        card.classList.remove('warning', 'danger');
        const barPercent = (value / maxForBar) * 100;
        if (type === 'cpu' || type === 'memory') {
            if (barPercent > 80) card.classList.add('danger');
            else if (barPercent > 60) card.classList.add('warning');
        }
    }
}

function addToHistory(timestamp, cpu, memory, threads, eventLoopLag) {
    const history = state.metricsHistory;
    
    history.timestamps.push(timestamp);
    history.cpu.push(cpu);
    history.memory.push(memory);
    history.threads.push(threads);
    history.eventLoopLag.push(eventLoopLag);
    
    // Trim to max data points
    while (history.timestamps.length > CONFIG.maxDataPoints) {
        history.timestamps.shift();
        history.cpu.shift();
        history.memory.shift();
        history.threads.shift();
        history.eventLoopLag.shift();
    }
}

// ==========================================================================
// Charts
// ==========================================================================

function initializeCharts() {
    if (typeof Chart === 'undefined') {
        console.error('Chart.js not loaded');
        return;
    }

    // Resource chart (CPU + Memory)
    const resourceCtx = document.getElementById('resourceChart');
    if (resourceCtx) {
        state.charts.resource = new Chart(resourceCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'CPU %',
                        data: [],
                        borderColor: '#0078d4',
                        backgroundColor: 'rgba(0, 120, 212, 0.1)',
                        tension: 0.3,
                        fill: 'origin',
                        yAxisID: 'y',
                        pointRadius: 0,
                        borderWidth: 1
                    },
                    {
                        label: 'Memory MB',
                        data: [],
                        borderColor: '#107c10',
                        backgroundColor: 'rgba(16, 124, 16, 0.1)',
                        tension: 0.3,
                        fill: 'origin',
                        yAxisID: 'y1',
                        pointRadius: 0,
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                scales: {
                    x: {
                        display: true,
                        ticks: {
                            maxTicksLimit: 10,
                            callback: (value, index) => {
                                const date = state.metricsHistory.timestamps[index];
                                return date ? formatUtcTime(date) : '';
                            }
                        }
                    },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        min: 0,
                        max: 100,
                        title: { display: true, text: 'CPU %' }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        min: 0,
                        title: { display: true, text: 'Memory MB' },
                        grid: { drawOnChartArea: false }
                    }
                },
                plugins: { legend: { position: 'top' } }
            }
        });
    }

    // Event Loop Lag chart
    const threadCtx = document.getElementById('threadChart');
    if (threadCtx) {
        state.charts.threads = new Chart(threadCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Event Loop Lag (ms)',
                        data: [],
                        borderColor: '#e74c3c',
                        backgroundColor: 'rgba(231, 76, 60, 0.3)',
                        tension: 0.3,
                        fill: 'origin',
                        yAxisID: 'y',
                        pointRadius: 0,
                        borderWidth: 2
                    },
                    {
                        label: 'Active Threads',
                        data: [],
                        borderColor: '#8764b8',
                        backgroundColor: 'rgba(135, 100, 184, 0.2)',
                        tension: 0.3,
                        fill: false,
                        yAxisID: 'y1',
                        pointRadius: 0,
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                scales: {
                    x: {
                        display: true,
                        ticks: {
                            maxTicksLimit: 10,
                            callback: (value, index) => {
                                const date = state.metricsHistory.timestamps[index];
                                return date ? formatUtcTime(date) : '';
                            }
                        }
                    },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        min: 0,
                        title: { display: true, text: 'Lag (ms)' }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        min: 0,
                        title: { display: true, text: 'Threads' },
                        grid: { drawOnChartArea: false }
                    }
                },
                plugins: { legend: { position: 'top' } }
            }
        });
    }

    // Latency chart
    const latencyCtx = document.getElementById('latencyChart');
    if (latencyCtx) {
        state.charts.latency = new Chart(latencyCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Latency (ms)',
                        data: [],
                        borderColor: '#0078d4',
                        backgroundColor: 'rgba(0, 120, 212, 0.1)',
                        tension: 0.2,
                        fill: 'origin',
                        pointRadius: 0,
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                interaction: { mode: 'index', intersect: false },
                scales: {
                    x: {
                        display: true,
                        ticks: {
                            maxTicksLimit: 6,
                            maxRotation: 0,
                            font: { size: 10 },
                            callback: (value, index) => {
                                const date = state.latencyHistory.timestamps[index];
                                return date ? formatUtcTime(date) : '';
                            }
                        }
                    },
                    y: {
                        display: true,
                        position: 'left',
                        beginAtZero: true,
                        grace: '5%',
                        title: { display: true, text: 'Latency (ms)', font: { size: 10 } },
                        ticks: {
                            font: { size: 10 },
                            callback: (value) => {
                                if (value >= 1000) {
                                    return (value / 1000).toFixed(1) + 's';
                                }
                                return value + 'ms';
                            }
                        }
                    }
                },
                plugins: { legend: { display: false } }
            }
        });
    }
}

function updateCharts() {
    const history = state.metricsHistory;
    const labels = history.timestamps.map(t => formatUtcTime(t));
    
    // Update resource chart
    if (state.charts.resource) {
        state.charts.resource.data.labels = labels;
        state.charts.resource.data.datasets[0].data = history.cpu;
        state.charts.resource.data.datasets[1].data = history.memory;
        state.charts.resource.update('none');
    }
    
    // Update event loop lag chart
    if (state.charts.threads) {
        state.charts.threads.data.labels = labels;
        state.charts.threads.data.datasets[0].data = history.eventLoopLag;
        state.charts.threads.data.datasets[1].data = history.threads;
        state.charts.threads.update('none');
    }
}

// ==========================================================================
// Latency Monitoring
// ==========================================================================

function handleLatencyUpdate(measurement) {
    const timestamp = measurement.timestamp instanceof Date ? measurement.timestamp : new Date(measurement.timestamp);
    const latencyMs = measurement.latencyMs;
    const isTimeout = measurement.isTimeout;
    const isError = measurement.isError;

    addLatencyToHistory(timestamp, latencyMs, isTimeout, isError);
    updateLatencyDisplay(latencyMs, isTimeout, isError);
    updateLatencyChart();
    updateProbeVisualization(latencyMs);
}

function addLatencyToHistory(timestamp, latencyMs, isTimeout, isError) {
    const history = state.latencyHistory;
    
    history.timestamps.push(timestamp);
    history.values.push(latencyMs);
    history.isTimeout.push(isTimeout);
    history.isError.push(isError);
    
    if (isTimeout) {
        state.latencyStats.timeoutCount++;
    }
    
    while (history.timestamps.length > CONFIG.maxLatencyDataPoints) {
        history.timestamps.shift();
        const wasTimeout = history.isTimeout.shift();
        history.values.shift();
        history.isError.shift();
        
        if (wasTimeout) {
            state.latencyStats.timeoutCount = Math.max(0, state.latencyStats.timeoutCount - 1);
        }
    }
}

function updateLatencyDisplay(currentLatency, isTimeout, isError) {
    const history = state.latencyHistory;
    
    const currentEl = document.getElementById('latencyCurrent');
    if (currentEl) {
        currentEl.textContent = formatLatency(currentLatency);
        currentEl.className = `latency-value ${getLatencyClass(currentLatency, isTimeout)}`;
    }
    
    const avgEl = document.getElementById('latencyAverage');
    if (avgEl && history.values.length > 0) {
        const avg = history.values.reduce((a, b) => a + b, 0) / history.values.length;
        avgEl.textContent = formatLatency(avg);
        avgEl.className = `latency-value ${getLatencyClass(avg, false)}`;
    }
    
    const maxEl = document.getElementById('latencyMax');
    if (maxEl && history.values.length > 0) {
        const max = Math.max(...history.values);
        maxEl.textContent = formatLatency(max);
        maxEl.className = `latency-value ${getLatencyClass(max, false)}`;
    }
    
    const timeoutsEl = document.getElementById('latencyTimeouts');
    if (timeoutsEl) {
        timeoutsEl.textContent = state.latencyStats.timeoutCount;
        timeoutsEl.className = state.latencyStats.timeoutCount > 0 ? 'latency-value timeout' : 'latency-value';
    }
}

function formatLatency(ms) {
    if (ms >= 10000) {
        return (ms / 1000).toFixed(1) + 's';
    } else if (ms >= 1000) {
        return (ms / 1000).toFixed(2) + 's';
    } else {
        return ms.toFixed(1) + 'ms';
    }
}

function getLatencyClass(ms, isTimeout) {
    if (isTimeout) return 'timeout';
    if (ms > 1000) return 'danger';
    if (ms > 150) return 'warning';
    return 'good';
}

function updateProbeVisualization(latency) {
    let status = 'good';
    if (latency >= 30000) status = 'failed';
    else if (latency >= 1000) status = 'slow';
    else if (latency >= 150) status = 'degraded';

    probeHistory.push(status);
    if (probeHistory.length > MAX_PROBE_DOTS) {
        probeHistory.shift();
    }

    const vizEl = document.getElementById('probe-visualization');
    if (vizEl) {
        vizEl.innerHTML = probeHistory.map(s =>
            `<span class="probe-dot-inline ${s === 'good' ? '' : s}"></span>`
        ).join('');
    }
}

function updateLatencyChart() {
    if (!state.charts.latency) return;
    
    const history = state.latencyHistory;
    
    state.charts.latency.data.labels = history.timestamps.map(t => formatUtcTime(t));
    state.charts.latency.data.datasets[0].data = history.values;
    state.charts.latency.update('none');
}

// ==========================================================================
// Simulations List
// ==========================================================================

function updateSimulationsList(simulations) {
    const container = document.getElementById('simulationsList');
    if (!container) return;
    
    if (!simulations || simulations.length === 0) {
        container.innerHTML = '<p class="no-simulations">No active simulations</p>';
        return;
    }
    
    const html = simulations.map(sim => {
        const typeClass = sim.type?.toLowerCase().replace('_', '') || 'cpu';
        return `
            <div class="simulation-badge ${typeClass}">
                <span class="spinner"></span>
                <span>${formatSimulationType(sim.type)}</span>
                <span>${formatDuration(sim.elapsed_seconds || 0)}</span>
            </div>
        `;
    }).join('');
    
    container.innerHTML = html;
}

function formatSimulationType(type) {
    const types = {
        'cpu_stress': '🔥 CPU Stress',
        'memory_pressure': '📊 Memory',
        'sync_blocking': '🧵 Sync Block',
        'async_blocking': '🧵 Async Block',
        'slow_request': '🐌 Slow Request',
        'failed_request': '❌ Failed Request'
    };
    return types[type] || type;
}

function formatDuration(seconds) {
    if (seconds < 60) {
        return `${Math.floor(seconds)}s`;
    }
    const minutes = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${minutes}m ${secs}s`;
}

// ==========================================================================
// Event Logging
// ==========================================================================

function logEvent(type, message, options = {}) {
    const container = document.getElementById('eventLog');
    if (!container) return;
    
    const timestamp = getCurrentUtcTime();
    const icon = options.icon || getEventIcon(type);
    
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    entry.innerHTML = `<span class="log-time">${timestamp}</span> <span class="log-icon">${icon}</span> ${message}`;
    
    container.insertBefore(entry, container.firstChild);
    
    // Limit to 100 entries
    while (container.children.length > 100) {
        container.lastChild.remove();
    }
}

function getEventIcon(type) {
    const icons = {
        'system': '💻',
        'cpu': '🔥',
        'memory': '📊',
        'threads': '🧵',
        'slowrequest': '🐌',
        'failedrequests': '❌',
        'crash': '💥',
        'success': '✅',
        'warning': '⚠️',
        'error': '🚨'
    };
    return icons[type] || '📝';
}

// ==========================================================================
// Simulation Controls
// ==========================================================================

async function triggerCpuStress() {
    const duration = parseInt(document.getElementById('cpuDuration').value) || 30;
    const level = document.getElementById('cpuLevel').value || 'high';
    
    try {
        logEvent('cpu', `Triggering CPU stress for ${duration} seconds (${level})...`);
        const response = await fetch(`${CONFIG.apiBaseUrl}/cpu/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                duration_seconds: duration,
                intensity: level === 'high' ? 8 : 5,
                workers: level === 'high' ? 4 : 2
            })
        });
        
        if (response.ok) {
            const result = await response.json();
            logEvent('cpu', 'CPU stress started');
        } else {
            const error = await response.json();
            logEvent('error', `Failed: ${error.detail || 'Unknown error'}`);
        }
    } catch (err) {
        logEvent('error', `Request failed: ${err.message}`);
    }
}

async function stopCpuStress() {
    try {
        logEvent('cpu', 'Stopping CPU stress simulations...');
        const response = await fetch(`${CONFIG.apiBaseUrl}/cpu/stop`, { method: 'POST' });
        
        if (response.ok) {
            logEvent('cpu', 'CPU stress stopped');
        }
    } catch (err) {
        logEvent('error', `Stop request failed: ${err.message}`);
    }
}

async function allocateMemory() {
    const sizeMb = parseInt(document.getElementById('memorySize').value) || 100;
    
    try {
        logEvent('memory', `Allocating ${sizeMb} MB of memory...`);
        const response = await fetch(`${CONFIG.apiBaseUrl}/memory/allocate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ size_mb: sizeMb })
        });
        
        if (response.ok) {
            logEvent('memory', `Allocated ${sizeMb} MB`);
        } else {
            const error = await response.json();
            logEvent('error', `Failed: ${error.detail || 'Unknown error'}`);
        }
    } catch (err) {
        logEvent('error', `Request failed: ${err.message}`);
    }
}

async function releaseMemory() {
    try {
        logEvent('memory', 'Releasing all memory allocations...');
        const response = await fetch(`${CONFIG.apiBaseUrl}/memory/release`, { method: 'POST' });
        
        if (response.ok) {
            logEvent('memory', 'Memory released');
        }
    } catch (err) {
        logEvent('error', `Release request failed: ${err.message}`);
    }
}

async function triggerThreadBlock() {
    const delay = parseFloat(document.getElementById('threadDelay').value) || 10;
    const count = parseInt(document.getElementById('threadConcurrent').value) || 10;
    
    try {
        logEvent('threads', `Starting ${count} blocking operations (${delay}s each)...`);
        const response = await fetch(`${CONFIG.apiBaseUrl}/blocking/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                type: 'sync',
                duration_seconds: delay,
                count: count
            })
        });
        
        if (response.ok) {
            logEvent('threads', 'Blocking operations started');
        } else {
            const error = await response.json();
            logEvent('error', `Failed: ${error.detail || 'Unknown error'}`);
        }
    } catch (err) {
        logEvent('error', `Request failed: ${err.message}`);
    }
}

async function stopThreadBlock() {
    try {
        logEvent('threads', 'Stopping blocking operations...');
        const response = await fetch(`${CONFIG.apiBaseUrl}/blocking/stop`, { method: 'POST' });
        
        if (response.ok) {
            logEvent('threads', 'Blocking operations stopped');
        }
    } catch (err) {
        logEvent('error', `Stop request failed: ${err.message}`);
    }
}

async function startSlowRequests() {
    const duration = parseInt(document.getElementById('slowRequestDuration').value) || 25;
    const interval = parseFloat(document.getElementById('slowRequestInterval').value) || 2;
    const maxRequests = parseInt(document.getElementById('slowRequestMax').value) || 10;
    
    try {
        logEvent('slowrequest', `Starting slow request generator (${duration}s, interval ${interval}s, max ${maxRequests})...`);
        const response = await fetch(`${CONFIG.apiBaseUrl}/slow/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                delay_seconds: duration,
                interval_seconds: interval,
                max_requests: maxRequests
            })
        });
        
        if (response.ok) {
            logEvent('slowrequest', 'Slow request generator started');
        } else {
            const error = await response.json();
            logEvent('error', `Failed: ${error.detail || 'Unknown error'}`);
        }
    } catch (err) {
        logEvent('error', `Request failed: ${err.message}`);
    }
}

async function stopSlowRequests() {
    try {
        logEvent('slowrequest', 'Stopping slow requests...');
        const response = await fetch(`${CONFIG.apiBaseUrl}/slow/stop`, { method: 'POST' });
        
        if (response.ok) {
            logEvent('slowrequest', 'Slow requests stopped');
        }
    } catch (err) {
        logEvent('error', `Stop request failed: ${err.message}`);
    }
}

async function generateFailedRequests() {
    const count = parseInt(document.getElementById('failedRequestCount').value) || 10;
    
    try {
        logEvent('failedrequests', `Generating ${count} HTTP 500 errors...`);
        const response = await fetch(`${CONFIG.apiBaseUrl}/crash/failed-requests`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ count: count })
        });
        
        if (response.ok) {
            logEvent('failedrequests', `Generated ${count} failed requests`);
        } else {
            const error = await response.json();
            logEvent('error', `Failed: ${error.detail || 'Unknown error'}`);
        }
    } catch (err) {
        logEvent('error', `Request failed: ${err.message}`);
    }
}

async function triggerCrash() {
    const crashType = document.getElementById('crashType').value;
    
    if (!confirm(`This will CRASH the application using ${crashType}. Are you sure?`)) {
        return;
    }
    
    try {
        logEvent('crash', `Triggering ${crashType} crash...`);
        const response = await fetch(`${CONFIG.apiBaseUrl}/crash/trigger`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type: crashType })
        });
        
        // If we get here, the crash didn't happen
        const result = await response.json();
        logEvent('crash', result.message || 'Crash triggered');
    } catch (err) {
        logEvent('crash', 'Application crashed (connection lost)');
    }
}

// ==========================================================================
// Event Handlers Setup
// ==========================================================================

function setupEventHandlers() {
    // CPU controls
    document.getElementById('btnTriggerCpu')?.addEventListener('click', triggerCpuStress);
    document.getElementById('btnStopCpu')?.addEventListener('click', stopCpuStress);
    
    // Memory controls
    document.getElementById('btnAllocateMemory')?.addEventListener('click', allocateMemory);
    document.getElementById('btnReleaseMemory')?.addEventListener('click', releaseMemory);
    
    // Thread blocking controls
    document.getElementById('btnTriggerThreadBlock')?.addEventListener('click', triggerThreadBlock);
    document.getElementById('btnStopThreadBlock')?.addEventListener('click', stopThreadBlock);
    
    // Slow request controls
    document.getElementById('btnStartSlowRequests')?.addEventListener('click', startSlowRequests);
    document.getElementById('btnStopSlowRequests')?.addEventListener('click', stopSlowRequests);
    
    // Failed request controls
    document.getElementById('btnStartFailedRequests')?.addEventListener('click', generateFailedRequests);
    
    // Crash controls
    document.getElementById('btnTriggerCrash')?.addEventListener('click', triggerCrash);
}

// ==========================================================================
// Latency Probe (Client-side)
// ==========================================================================

let latencyProbeInterval = null;

async function startLatencyProbe() {
    if (latencyProbeInterval) return;
    
    latencyProbeInterval = setInterval(async () => {
        const startTime = performance.now();
        try {
            const response = await fetch('/api/health', { 
                method: 'GET',
                cache: 'no-store'
            });
            const endTime = performance.now();
            const latencyMs = endTime - startTime;
            
            handleLatencyUpdate({
                timestamp: new Date(),
                latencyMs: latencyMs,
                isTimeout: latencyMs >= CONFIG.latencyTimeoutMs,
                isError: !response.ok
            });
        } catch (err) {
            const endTime = performance.now();
            handleLatencyUpdate({
                timestamp: new Date(),
                latencyMs: endTime - startTime,
                isTimeout: false,
                isError: true
            });
        }
    }, CONFIG.latencyProbeIntervalMs);
}

function stopLatencyProbe() {
    if (latencyProbeInterval) {
        clearInterval(latencyProbeInterval);
        latencyProbeInterval = null;
    }
}

// ==========================================================================
// Initialization
// ==========================================================================

document.addEventListener('DOMContentLoaded', function() {
    // Initialize charts
    initializeCharts();
    
    // Set up event handlers
    setupEventHandlers();
    
    // Connect to WebSocket
    initializeWebSocket();
    
    // Start latency probe
    startLatencyProbe();
    
    // Log startup
    logEvent('system', 'Dashboard initialized');
});
