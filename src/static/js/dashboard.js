/**
 * Performance Problem Simulator - Dashboard JavaScript (Python Edition)
 * Matching .NET Core version functionality
 */

// ==========================================================================
// Configuration & State
// ==========================================================================

const CONFIG = {
    maxDataPoints: 240,  // 1 minute of data at 250ms intervals
    maxLatencyDataPoints: 600, // 60 seconds of chart data at 100ms updates
    latencyChartUpdateIntervalMs: 100, // Chart update rate (fixed)
    latencyProbeIntervalMs: 200, // Health probe rate (display-only, actual probes are server-side)
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
    lastProcessId: null,
    lastInstanceId: null,  // Server instance ID (unique per server start - reliable for containers)
    checkProcessIdOnNextMessage: false,
    // Idle state tracking
    isIdle: false,
    intentionalDisconnect: false,
    idleTimeoutMinutes: 20,
    secondsUntilIdle: -1,
    // Track processed event keys to avoid duplicate server event display
    processedEventKeys: new Set(),
    // Slow request generator tracking
    slowRequestGeneratorRunning: false,
    slowRequestGeneratorCount: 0,
    slowRequestGeneratorMax: 0
};

// ==========================================================================
// Latency Threshold Colors (matches Node.js version)
// ==========================================================================

// RGB values for smooth color interpolation
const LATENCY_RGB = {
    good:     { r: 16,  g: 124, b: 16  }, // Green (< 150ms)
    degraded: { r: 255, g: 185, b: 0   }, // Yellow (150ms - 1s)
    severe:   { r: 255, g: 140, b: 0   }, // Orange (1s - 30s)
    critical: { r: 209, g: 52,  b: 56  }  // Red (30s+)
};

/**
 * Interpolates between two RGB colors.
 * @param {Object} color1 - Start color {r, g, b}
 * @param {Object} color2 - End color {r, g, b}
 * @param {number} t - Interpolation factor (0-1)
 * @returns {string} - RGB color string
 */
function lerpColor(color1, color2, t) {
    t = Math.max(0, Math.min(1, t)); // Clamp to 0-1
    const r = Math.round(color1.r + (color2.r - color1.r) * t);
    const g = Math.round(color1.g + (color2.g - color1.g) * t);
    const b = Math.round(color1.b + (color2.b - color1.b) * t);
    return `rgb(${r}, ${g}, ${b})`;
}

/**
 * Gets a smoothly interpolated color for a latency value.
 * Blends between threshold colors based on where the value falls.
 * @param {number} latencyMs - Latency value in milliseconds
 * @returns {string} - RGB color string
 */
function getInterpolatedLatencyColor(latencyMs) {
    if (latencyMs <= 0) return lerpColor(LATENCY_RGB.good, LATENCY_RGB.good, 0);
    
    // 0-150ms: green → yellow
    if (latencyMs <= 150) {
        const t = latencyMs / 150;
        return lerpColor(LATENCY_RGB.good, LATENCY_RGB.degraded, t);
    }
    
    // 150-1000ms: yellow → orange
    if (latencyMs <= 1000) {
        const t = (latencyMs - 150) / (1000 - 150);
        return lerpColor(LATENCY_RGB.degraded, LATENCY_RGB.severe, t);
    }
    
    // 1000-30000ms: orange → red
    if (latencyMs <= 30000) {
        const t = (latencyMs - 1000) / (30000 - 1000);
        return lerpColor(LATENCY_RGB.severe, LATENCY_RGB.critical, t);
    }
    
    // >30000ms: solid red
    return lerpColor(LATENCY_RGB.critical, LATENCY_RGB.critical, 1);
}

/**
 * Gets a smoothly interpolated RGBA color for a latency value (for gradient fills).
 * @param {number} latencyMs - Latency value in milliseconds
 * @param {number} alpha - Alpha value (0-1)
 * @returns {string} - RGBA color string
 */
function getInterpolatedLatencyColorRGBA(latencyMs, alpha) {
    let r, g, b;
    
    if (latencyMs <= 0) {
        r = LATENCY_RGB.good.r; g = LATENCY_RGB.good.g; b = LATENCY_RGB.good.b;
    } else if (latencyMs <= 150) {
        const t = latencyMs / 150;
        r = Math.round(LATENCY_RGB.good.r + (LATENCY_RGB.degraded.r - LATENCY_RGB.good.r) * t);
        g = Math.round(LATENCY_RGB.good.g + (LATENCY_RGB.degraded.g - LATENCY_RGB.good.g) * t);
        b = Math.round(LATENCY_RGB.good.b + (LATENCY_RGB.degraded.b - LATENCY_RGB.good.b) * t);
    } else if (latencyMs <= 1000) {
        const t = (latencyMs - 150) / (1000 - 150);
        r = Math.round(LATENCY_RGB.degraded.r + (LATENCY_RGB.severe.r - LATENCY_RGB.degraded.r) * t);
        g = Math.round(LATENCY_RGB.degraded.g + (LATENCY_RGB.severe.g - LATENCY_RGB.degraded.g) * t);
        b = Math.round(LATENCY_RGB.degraded.b + (LATENCY_RGB.severe.b - LATENCY_RGB.degraded.b) * t);
    } else if (latencyMs <= 30000) {
        const t = (latencyMs - 1000) / (30000 - 1000);
        r = Math.round(LATENCY_RGB.severe.r + (LATENCY_RGB.critical.r - LATENCY_RGB.severe.r) * t);
        g = Math.round(LATENCY_RGB.severe.g + (LATENCY_RGB.critical.g - LATENCY_RGB.severe.g) * t);
        b = Math.round(LATENCY_RGB.severe.b + (LATENCY_RGB.critical.b - LATENCY_RGB.severe.b) * t);
    } else {
        r = LATENCY_RGB.critical.r; g = LATENCY_RGB.critical.g; b = LATENCY_RGB.critical.b;
    }
    
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

/**
 * Creates a vertical gradient for the latency chart with smooth color blending.
 * Adds many intermediate color stops for seamless transitions between thresholds.
 * @param {CanvasRenderingContext2D} ctx - Canvas context
 * @param {Object} chartArea - Chart area dimensions
 * @param {Object} scales - Chart scales
 * @returns {CanvasGradient} - The gradient fill
 */
function createLatencyGradient(ctx, chartArea, scales) {
    if (!chartArea || !scales.y) return 'rgba(16, 124, 16, 0.2)';
    
    const gradient = ctx.createLinearGradient(0, chartArea.bottom, 0, chartArea.top);
    const yMax = scales.y.max || 200;
    
    // Add many color stops for smooth blending (20 stops from bottom to top)
    const numStops = 20;
    for (let i = 0; i <= numStops; i++) {
        const position = i / numStops; // 0 = bottom, 1 = top
        const latencyAtPosition = position * yMax;
        
        // Alpha increases slightly with latency for better visual distinction
        const alpha = 0.25 + (position * 0.25); // 0.25 at bottom to 0.50 at top
        
        const color = getInterpolatedLatencyColorRGBA(latencyAtPosition, alpha);
        gradient.addColorStop(position, color);
    }
    
    return gradient;
}

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

function formatLocalTime(date) {
    if (!date || !(date instanceof Date)) return '';
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    const seconds = date.getSeconds().toString().padStart(2, '0');
    return `${hours}:${minutes}:${seconds}`;
}

// ==========================================================================
// WebSocket Connection
// ==========================================================================

let wsDisconnectTime = null;
let wsDisconnectMessageTimeout = null;

function initializeWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/metrics`;
    
    updateConnectionStatus('connecting', 'Connecting...');
    
    try {
        state.wsConnection = new WebSocket(wsUrl);
        
        state.wsConnection.onopen = () => {
            // Clear any pending disconnect message
            if (wsDisconnectMessageTimeout) {
                clearTimeout(wsDisconnectMessageTimeout);
                wsDisconnectMessageTimeout = null;
            }
            
            state.intentionalDisconnect = false;
            updateConnectionStatus('connected', 'Connected');
            
            // Log reconnection if we were previously connected
            if (wsDisconnectTime) {
                logEvent('ws-connect', 'Reconnected to server');
                wsDisconnectTime = null;
                // Mark that we need to check for process ID change on next metrics message
                state.checkProcessIdOnNextMessage = true;
            }
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
            // If we intentionally disconnected for idle, don't reconnect or update status
            if (state.intentionalDisconnect) {
                return;
            }
            
            updateConnectionStatus('disconnected', 'Disconnected');
            
            // Record disconnect time if not already set
            if (!wsDisconnectTime) {
                wsDisconnectTime = Date.now();
            }
            
            // Only show disconnect message after 10 seconds
            if (!wsDisconnectMessageTimeout) {
                wsDisconnectMessageTimeout = setTimeout(() => {
                    logEvent('ws-disconnect', 'Connection lost. Attempting to reconnect...');
                    wsDisconnectMessageTimeout = null;
                }, 10000);
            }
            
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

/**
 * Ensures the WebSocket connection is open. If disconnected (e.g., after idle),
 * reconnects immediately. Called by simulation functions to wake the connection.
 */
function ensureWebSocket() {
    if (!state.wsConnection || state.wsConnection.readyState === WebSocket.CLOSED || state.wsConnection.readyState === WebSocket.CLOSING) {
        state.intentionalDisconnect = false;
        initializeWebSocket();
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
    
    // Check for server restart using instance_id (works in containers where PID is always 1)
    const currentInstanceId = processData.instance_id;
    const currentProcessId = processData.pid;
    
    // Get the previous instance ID from state or sessionStorage
    let previousInstanceId = state.lastInstanceId;
    if (previousInstanceId === null) {
        const storedInstanceId = sessionStorage.getItem('lastInstanceId');
        if (storedInstanceId) {
            previousInstanceId = storedInstanceId;
            state.lastInstanceId = previousInstanceId;
        }
    }
    
    // Check for restart: instance_id change is the reliable indicator
    if (currentInstanceId && previousInstanceId !== null && currentInstanceId !== previousInstanceId) {
        // Server instance changed - app was restarted
        logEvent('restart', `APPLICATION RESTARTED! Server instance changed (${previousInstanceId} → ${currentInstanceId}). This may indicate an unexpected crash (OOM, StackOverflow, FailFast, etc.).`, { icon: '🔄' });
    }
    
    // Clear the reconnection check flag
    state.checkProcessIdOnNextMessage = false;
    
    // Update the stored instance ID and process ID (both in state and sessionStorage)
    if (currentInstanceId) {
        state.lastInstanceId = currentInstanceId;
        sessionStorage.setItem('lastInstanceId', currentInstanceId);
    }
    if (currentProcessId) {
        state.lastProcessId = currentProcessId;
        sessionStorage.setItem('lastProcessId', currentProcessId.toString());
    }
    
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
    updateMetricCard('queue', eventLoopLagMs, 'ms', 100);

    // Update total memory display
    const totalMemoryEl = document.getElementById('memoryTotal');
    if (totalMemoryEl && totalMemoryMb) {
        const totalFormatted = totalMemoryMb >= 1024 
            ? (totalMemoryMb / 1024).toFixed(1) + ' GB'
            : Math.round(totalMemoryMb) + ' MB';
        totalMemoryEl.textContent = `of ${totalFormatted}`;
    }

    // Handle idle state from WebSocket broadcast
    const idleData = data.idle || {};
    if (idleData.is_idle !== undefined) {
        const wasIdle = state.isIdle;
        state.isIdle = idleData.is_idle;
        state.secondsUntilIdle = idleData.seconds_until_idle || -1;
        
        // Transition to idle - stop chart updates and disconnect WebSocket
        if (idleData.is_idle && !wasIdle) {
            stopLatencyChartUpdater();
            updateIdleDisplay(true);
            logEvent('warning', 'Application going idle, no health probes being sent.  There will be gaps in diagnostics and logs.');
            // Intentionally disconnect WebSocket to prevent reconnect cycle flicker
            state.intentionalDisconnect = true;
            if (state.wsConnection) {
                state.wsConnection.close();
            }
        }
        // Transition from idle
        else if (!idleData.is_idle && wasIdle) {
            updateIdleDisplay(false);
            startLatencyChartUpdater();
        }
    }

    // Handle slow request generator state
    const slowRequestData = data.slowRequestGenerator || {};
    if (slowRequestData.is_running !== undefined) {
        const wasRunning = state.slowRequestGeneratorRunning;
        state.slowRequestGeneratorRunning = slowRequestData.is_running;
        state.slowRequestGeneratorCount = slowRequestData.generated_count || 0;
        state.slowRequestGeneratorMax = slowRequestData.max_requests || 0;
        
        // Calculate active requests (in-flight slow requests)
        // Active = generated - completed (approximation based on timing)
        const activeCount = Math.max(0, Math.min(
            state.slowRequestGeneratorCount,
            Math.ceil(slowRequestData.delay_seconds / (slowRequestData.interval_seconds || 1))
        ));
        
        // Update overlay display
        updateSlowRequestOverlay(
            slowRequestData.is_running,
            state.slowRequestGeneratorCount,
            state.slowRequestGeneratorMax,
            activeCount
        );
        
        // Note: slow-request probe interval changes are handled
        // server-side by probe_service.set_slow_request_mode().
    }

    // Process server-side events broadcast via WebSocket
    const serverEvents = data.events || [];
    for (const event of serverEvents) {
        // Deduplicate events using timestamp + message as key
        const eventKey = `${event.timestamp}-${event.message}`;
        if (state.processedEventKeys.has(eventKey)) {
            console.warn('Duplicate event suppressed:', event.message, event.timestamp);
            continue; // Already displayed this event
        }
        state.processedEventKeys.add(eventKey);
        
        // Keep set size bounded
        if (state.processedEventKeys.size > 500) {
            const iterator = state.processedEventKeys.values();
            for (let i = 0; i < 250; i++) {
                state.processedEventKeys.delete(iterator.next().value);
            }
        }
        
        // Use simulation_type for icon/color (e.g., 'cpu_stress'), fall back to event_type
        const logType = event.simulation_type || event.event_type || 'system';
        const message = event.message || '';
        const simulationId = event.simulation_id || null;
        
        // Log the event using the server's timestamp
        logEvent(logType, message, { 
            serverTimestamp: event.timestamp, 
            icon: getServerEventIcon(logType),
            simulationId: simulationId
        });
    }

    // Update history for charts
    const timestamp = new Date();
    addToHistory(timestamp, cpuPercent, memoryMb, threadCount, eventLoopLagMs);
    
    // Update charts
    updateCharts();
    
    // Process server-side probe results (health probe latencies)
    const probeResults = data.probeResults || [];
    for (const probe of probeResults) {
        const isTimeout = probe.latencyMs >= CONFIG.latencyTimeoutMs;
        const isError = !probe.success;
        lastProbeResult = {
            timestamp: new Date(probe.timestamp * 1000),
            latencyMs: probe.latencyMs,
            isTimeout: isTimeout,
            isError: isError
        };
        updateLatencyDisplay(probe.latencyMs, isTimeout, isError);
        updateProbeVisualization(probe.latencyMs);
    }
    
    // Update active simulations (always update to clear when empty)
    updateSimulationsList(activeSimulations);
    
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
    
    // Format value - use 2 decimal places for queue (event loop lag) to match chart precision
    let displayValue = '--';
    if (typeof value === 'number') {
        if (type === 'queue') {
            displayValue = value.toFixed(2);
        } else if (value < 10) {
            displayValue = value.toFixed(1);
        } else {
            displayValue = Math.round(value);
        }
    }
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
                        backgroundColor: 'rgba(16, 124, 16, 0.2)',
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
                        borderColor: '#ffb900',
                        backgroundColor: 'rgba(255, 185, 0, 0.1)',
                        tension: 0.3,
                        fill: 'origin',
                        yAxisID: 'y',
                        pointRadius: 0,
                        borderWidth: 1
                    },
                    {
                        label: 'Active Threads',
                        data: [],
                        borderColor: '#8764b8',
                        backgroundColor: 'rgba(135, 100, 184, 0.2)',
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

    // Latency chart with dynamic gradient coloring based on latency thresholds
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
                        // Segment-based border color - smooth gradient based on data value
                        segment: {
                            borderColor: (ctx) => {
                                const p0 = ctx.p0.parsed?.y;
                                const p1 = ctx.p1.parsed?.y;
                                if (p0 == null || p1 == null) return 'rgba(0,0,0,0)';
                                const value = Math.max(p0, p1);
                                return getInterpolatedLatencyColor(value);
                            },
                        },
                        borderColor: '#107c10', // Default/fallback (green)
                        // Dynamic gradient fill based on latency thresholds
                        backgroundColor: (context) => {
                            const chart = context.chart;
                            const { ctx, chartArea, scales } = chart;
                            if (!chartArea) return 'rgba(16, 124, 16, 0.2)';
                            return createLatencyGradient(ctx, chartArea, scales);
                        },
                        tension: 0.2,
                        fill: true,
                        pointRadius: 0,
                        pointHoverRadius: 0,
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
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const value = context.raw;
                                if (value >= 1000) {
                                    return `Latency: ${(value / 1000).toFixed(1)}s`;
                                }
                                return `Latency: ${value.toFixed(0)}ms`;
                            }
                        }
                    }
                }
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
// Slow Request Overlay
// ==========================================================================

function updateSlowRequestOverlay(isRunning, completedCount, maxRequests, activeCount) {
    const overlay = document.getElementById('slowRequestOverlay');
    const statusEl = document.getElementById('slowRequestStatus');
    
    if (!overlay) return;
    
    if (isRunning) {
        overlay.classList.remove('hidden-until-loaded');
        if (statusEl) {
            statusEl.textContent = `Running: ${completedCount}/${maxRequests} completed, ${activeCount} active`;
        }
    } else {
        overlay.classList.add('hidden-until-loaded');
    }
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
        const typeClass = getSimulationTypeClass(sim.type);
        return `
            <div class="simulation-badge ${typeClass}">
                <span>${formatSimulationType(sim.type)}</span>
            </div>
        `;
    }).join('');
    
    container.innerHTML = html;
}

function getSimulationTypeClass(type) {
    const classMap = {
        'cpu_stress': 'cpu',
        'memory_pressure': 'memory',
        'sync_blocking': 'threadblock',
        'async_blocking': 'threadblock',
        'slow_request': 'slowrequest',
        'failed_request': 'failedrequests',
        'failed_requests': 'failedrequests',
    };
    return classMap[type] || 'cpu';
}

function formatSimulationType(type) {
    const types = {
        'cpu_stress': '🔥 CPU Stress',
        'memory_pressure': '📊 Memory',
        'sync_blocking': '🧵 Sync Block',
        'async_blocking': '🧵 Async Block',
        'slow_request': '🐌 Slow Request',
        'failed_request': '❌ Failed Requests',
        'failed_requests': '❌ Failed Requests',
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

/**
 * Wraps a message with a simulation ID tooltip for correlation.
 * Clicking the message copies the simulation ID to clipboard.
 * @param {string} message - The message to display
 * @param {string} simulationId - The full GUID simulation ID (shown in tooltip)
 * @returns {string} HTML string with message and tooltip
 */
function withSimulationId(message, simulationId) {
    if (!simulationId) return message;
    return `<span class="sim-msg" data-simid="${simulationId}" title="Click to copy Simulation ID: ${simulationId}">${message}</span>`;
}

/**
 * Copies the simulation ID to clipboard when a sim-msg element is clicked.
 * Shows a brief visual feedback to indicate successful copy.
 */
function initSimulationIdCopyHandlers() {
    document.getElementById('eventLog').addEventListener('click', async (e) => {
        const simMsg = e.target.closest('.sim-msg');
        if (!simMsg) return;
        
        const simId = simMsg.dataset.simid;
        if (!simId) return;
        
        try {
            await navigator.clipboard.writeText(simId);
            
            // Visual feedback
            simMsg.classList.add('copied');
            const originalTitle = simMsg.title;
            simMsg.title = 'Copied!';
            
            setTimeout(() => {
                simMsg.classList.remove('copied');
                simMsg.title = originalTitle;
            }, 1500);
        } catch (err) {
            console.error('Failed to copy simulation ID:', err);
        }
    });
}

function logEvent(type, message, options = {}) {
    const container = document.getElementById('eventLog');
    if (!container) return;
    
    // Use server timestamp if provided, otherwise current time
    let timestamp;
    let localTime;
    if (options.serverTimestamp) {
        const date = new Date(options.serverTimestamp);
        timestamp = formatUtcTime(date) + ' UTC';
        localTime = formatLocalTime(date);
    } else {
        const now = new Date();
        timestamp = formatUtcTime(now) + ' UTC';
        localTime = formatLocalTime(now);
    }
    
    const icon = options.icon || getEventIcon(type);
    
    // Wrap message with simulation ID if present (for click-to-copy)
    const displayMessage = withSimulationId(message, options.simulationId);
    
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    entry.innerHTML = `<span class="log-time" data-localtime="Local Time: ${localTime}"><span class="log-time-text">${timestamp}</span></span> <span class="log-icon">${icon}</span> ${displayMessage}`;
    
    container.insertBefore(entry, container.firstChild);
}

function getEventIcon(type) {
    const icons = {
        'system': '',
        'cpu': '🔥',
        'memory': '📊',
        'threads': '🧵',
        'slowrequest': '🐌',
        'failedrequests': '❌',
        'crash': '💥',
        'restart': '🔄',
        'loadtest': '📈',
        'success': '✅',
        'warning': '⚠️',
        'error': '🚨'
    };
    return icons[type] || '';
}

/**
 * Get icon for server-side events.
 * Maps server event_type to appropriate emoji icon.
 */
function getServerEventIcon(eventType) {
    const icons = {
        'system': '',
        'info': '',
        'admin_reset': '⚠️',
        'cpu': '🔥',
        'cpu_stress': '🔥',
        'memory': '📊',
        'memory_pressure': '📊',
        'threads': '🧵',
        'blocking': '🧵',
        'async_blocking': '🧵',
        'slowrequest': '🐌',
        'slow_request': '🐌',
        'slow_generator_started': '🐌',
        'slow_generator_stopped': '🐌',
        'failedrequests': '❌',
        'failed_requests': '❌',
        'failed_requests_stopped': '❌',
        'crash': '💥',
        'crash_triggered': '💥',
        'restart': '🔄',
        'loadtest': '📈',
        'load_test': '📈',
        'success': '✅',
        'warning': '⚠️',
        'error': '🚨'
    };
    return icons[eventType] || '';
}

// ==========================================================================
// Simulation Controls
// ==========================================================================

async function triggerCpuStress() {
    ensureWebSocket();
    const duration = parseInt(document.getElementById('cpuDuration').value) || 30;
    const level = document.getElementById('cpuLevel').value || 'high';
    
    try {
        // Server broadcasts detailed event via WebSocket with proper formatting
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
            // Server broadcasts detailed event via WebSocket, no need to log here
        } else if (response.status !== 405) {
            const error = await response.json();
            logEvent('error', `Failed: ${error.detail || 'Unknown error'}`);
        }
    } catch (err) {
        logEvent('error', `Request failed: ${err.message}`);
    }
}

async function stopCpuStress() {
    ensureWebSocket();
    try {
        // Server broadcasts stop event via WebSocket
        const response = await fetch(`${CONFIG.apiBaseUrl}/cpu/stop`, { method: 'POST' });
        
        if (!response.ok && response.status !== 405) {
            const error = await response.json();
            logEvent('error', `Stop failed: ${error.detail || 'Unknown error'}`);
        }
    } catch (err) {
        logEvent('error', `Stop request failed: ${err.message}`);
    }
}

async function allocateMemory() {
    ensureWebSocket();
    const sizeMb = parseInt(document.getElementById('memorySize').value) || 100;
    
    try {
        // Server broadcasts allocation event via WebSocket
        const response = await fetch(`${CONFIG.apiBaseUrl}/memory/allocate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ size_mb: sizeMb })
        });
        
        if (!response.ok) {
            const error = await response.json();
            logEvent('error', `Memory allocation failed: ${error.detail || 'Unknown error'}`);
        }
    } catch (err) {
        logEvent('error', `Memory allocation request failed: ${err.message}`);
    }
}

async function releaseMemory() {
    ensureWebSocket();
    try {
        // Server broadcasts release event via WebSocket
        const response = await fetch(`${CONFIG.apiBaseUrl}/memory/release-all`, { method: 'POST' });
        
        if (!response.ok) {
            const error = await response.json();
            logEvent('error', `Memory release failed: ${error.detail || 'Unknown error'}`);
        }
    } catch (err) {
        logEvent('error', `Memory release request failed: ${err.message}`);
    }
}

async function triggerThreadBlock() {
    ensureWebSocket();
    const delay = parseFloat(document.getElementById('threadDelay').value) || 10;
    const count = parseInt(document.getElementById('threadConcurrent').value) || 10;
    
    try {
        // Server logs start event via WebSocket; no client-side duplicate needed
        const response = await fetch(`${CONFIG.apiBaseUrl}/blocking/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                type: 'async',
                duration_seconds: delay,
                count: count
            })
        });
        
        if (!response.ok && response.status !== 405) {
            const error = await response.json();
            logEvent('error', `Failed: ${error.detail || 'Unknown error'}`);
        }
    } catch (err) {
        logEvent('error', `Request failed: ${err.message}`);
    }
}

async function stopThreadBlock() {
    ensureWebSocket();
    try {
        // Server logs stop event via WebSocket; no client-side duplicate needed
        const response = await fetch(`${CONFIG.apiBaseUrl}/blocking/stop`, { method: 'POST' });
        
        if (!response.ok && response.status !== 405) {
            const error = await response.json();
            logEvent('error', `Stop failed: ${error.detail || 'Unknown error'}`);
        }
    } catch (err) {
        logEvent('error', `Stop request failed: ${err.message}`);
    }
}

async function startSlowRequests() {
    ensureWebSocket();
    const duration = parseInt(document.getElementById('slowRequestDuration').value) || 25;
    const interval = parseFloat(document.getElementById('slowRequestInterval').value) || 2;
    const maxRequests = parseInt(document.getElementById('slowRequestMax').value) || 10;
    
    try {
        // Server broadcasts start event via WebSocket
        const response = await fetch(`${CONFIG.apiBaseUrl}/slow/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                delay_seconds: duration,
                interval_seconds: interval,
                max_requests: maxRequests
            })
        });
        
        if (!response.ok && response.status !== 405) {
            const error = await response.json();
            logEvent('error', `Failed: ${error.detail || 'Unknown error'}`);
        }
    } catch (err) {
        logEvent('error', `Request failed: ${err.message}`);
    }
}

async function stopSlowRequests() {
    ensureWebSocket();
    try {
        // Server broadcasts stop event via WebSocket
        const response = await fetch(`${CONFIG.apiBaseUrl}/slow/stop`, { method: 'POST' });
        
        if (!response.ok && response.status !== 405) {
            const error = await response.json();
            logEvent('error', `Stop failed: ${error.detail || 'Unknown error'}`);
        }
    } catch (err) {
        logEvent('error', `Stop request failed: ${err.message}`);
    }
}

async function generateFailedRequests() {
    ensureWebSocket();
    const count = parseInt(document.getElementById('failedRequestCount').value) || 10;
    
    try {
        // Server broadcasts start event via WebSocket
        const response = await fetch(`${CONFIG.apiBaseUrl}/failed-requests/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ count: count })
        });
        
        if (!response.ok && response.status !== 405) {
            const error = await response.json();
            logEvent('error', `Failed: ${error.detail || 'Unknown error'}`);
        }
    } catch (err) {
        logEvent('error', `Request failed: ${err.message}`);
    }
}

async function triggerCrash() {
    ensureWebSocket();
    const crashType = document.getElementById('crashType').value;
    const crashTypeDisplay = crashType.charAt(0).toUpperCase() + crashType.slice(1);
    
    if (!confirm(`This will CRASH the application using ${crashTypeDisplay}. Are you sure?`)) {
        return;
    }
    
    try {
        logEvent('crash', `CRASH: ${crashTypeDisplay} - Connection will be lost!`);
        const response = await fetch(`${CONFIG.apiBaseUrl}/crash`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ crash_type: crashType, confirmed: true })
        });
        
        // If we get here, the crash didn't happen (exception type returns error response)
        const result = await response.json();
        if (!response.ok) {
            logEvent('error', `An unexpected error occurred`);
        }
    } catch (err) {
        // Connection lost is expected for successful crash
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
    
    // Event log copy
    document.getElementById('btnCopyEventLog')?.addEventListener('click', copyEventLogToClipboard);
}

// ==========================================================================
// Event Log Copy
// ==========================================================================

/**
 * Copies the event log contents to clipboard as plain text.
 */
async function copyEventLogToClipboard() {
    const container = document.getElementById('eventLog');
    const btn = document.getElementById('btnCopyEventLog');
    if (!container || !btn) return;
    
    // Extract text content from all log entries
    const entries = container.querySelectorAll('.log-entry');
    const lines = Array.from(entries).map(entry => entry.textContent.trim());
    const logText = lines.join('\n');
    
    try {
        await navigator.clipboard.writeText(logText);
        // Visual feedback - save original HTML and show "✓ Copied!"
        const originalHTML = btn.innerHTML;
        btn.innerHTML = '<span class="copy-text">✓ Copied!</span>';
        btn.classList.add('copied');
        setTimeout(() => {
            btn.innerHTML = originalHTML;
            btn.classList.remove('copied');
        }, 2000);
    } catch (err) {
        console.error('Failed to copy event log:', err);
        logEvent('error', 'Failed to copy event log to clipboard');
    }
}

// ==========================================================================
// Latency Display (driven by server-side probes via WebSocket)
// ==========================================================================

let latencyChartUpdateInterval = null;
let lastProbeResult = null; // Store the last probe result for chart interpolation

async function fetchConfig() {
    try {
        const response = await fetch(`${CONFIG.apiBaseUrl}/config`);
        if (response.ok) {
            const data = await response.json();
            if (data.latencyProbeIntervalMs && data.latencyProbeIntervalMs >= 100) {
                CONFIG.latencyProbeIntervalMs = data.latencyProbeIntervalMs;
                console.log(`Health probe interval set to ${CONFIG.latencyProbeIntervalMs}ms from server config`);
            }
            // Update build time displays
            if (data.buildTime) {
                const sidebarBuildTime = document.getElementById('sidebarBuildTime');
                const footerBuildTime = document.getElementById('footerBuildTime');
                if (sidebarBuildTime) sidebarBuildTime.textContent = data.buildTime;
                if (footerBuildTime) footerBuildTime.textContent = data.buildTime;
            }
            // Update idle state
            if (data.idleTimeoutMinutes !== undefined) {
                state.idleTimeoutMinutes = data.idleTimeoutMinutes;
                state.isIdle = data.isIdle;
                state.secondsUntilIdle = data.secondsUntilIdle;
                console.log(`Idle timeout: ${state.idleTimeoutMinutes}m, isIdle: ${state.isIdle}`);
            }
        }
    } catch (error) {
        console.error('Failed to fetch config, using defaults:', error);
    }
}

// Record activity with the server (only called on page load, not WebSocket reconnects)
// Returns true if the app was idle and is now waking up
async function recordActivity(source = 'page_load') {
    try {
        const response = await fetch(`${CONFIG.apiBaseUrl}/activity`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ source: source })
        });
        if (response.ok) {
            const data = await response.json();
            if (data.wasIdle) {
                state.isIdle = false;
                updateIdleDisplay(false);
            }
            console.log(`Activity recorded: ${data.message}`);
            return data.wasIdle || false;
        }
    } catch (error) {
        console.error('Failed to record activity:', error);
    }
    return false;
}

// Update idle state display in UI
function updateIdleDisplay(isIdle) {
    const connectionText = document.getElementById('connectionText');
    const indicator = document.getElementById('connectionIndicator');
    
    if (isIdle) {
        if (connectionText) connectionText.textContent = 'Idle';
        if (indicator) indicator.className = 'indicator idle';
    } else {
        // Restore connected status if we have an active connection
        if (state.wsConnection && state.wsConnection.readyState === WebSocket.OPEN) {
            if (connectionText) connectionText.textContent = 'Connected';
            if (indicator) indicator.className = 'indicator connected';
        }
    }
}

function startLatencyChartUpdater() {
    if (latencyChartUpdateInterval) return;
    
    // Chart update interval (always runs at 100ms for smooth charts).
    // Probe results arrive via WebSocket; the chart interpolates by
    // repeating the last known value between arrivals.
    latencyChartUpdateInterval = setInterval(() => {
        if (lastProbeResult) {
            addLatencyToHistory(
                new Date(),
                lastProbeResult.latencyMs,
                lastProbeResult.isTimeout,
                lastProbeResult.isError
            );
            updateLatencyChart();
        }
    }, CONFIG.latencyChartUpdateIntervalMs);
}

function stopLatencyChartUpdater() {
    if (latencyChartUpdateInterval) {
        clearInterval(latencyChartUpdateInterval);
        latencyChartUpdateInterval = null;
    }
}

// ==========================================================================
// Initialization
// ==========================================================================

// ==========================================================================
// Footer Display
// ==========================================================================

async function fetchAndDisplayFooter() {
    try {
        const response = await fetch(`${CONFIG.apiBaseUrl}/footer`);
        if (response.ok) {
            const data = await response.json();
            const footerCredits = document.getElementById('footerCredits');
            if (footerCredits) {
                if (data.has_custom_footer && data.footer && data.footer.trim()) {
                    footerCredits.innerHTML = data.footer;
                } else {
                    footerCredits.style.display = 'none';
                }
            }
        }
    } catch (error) {
        console.error('Failed to fetch footer:', error);
    }
}

// ==========================================================================
// GitHub Link Display
// ==========================================================================

async function fetchAndDisplayGithubLink() {
    try {
        const response = await fetch(`${CONFIG.apiBaseUrl}/github-config`);
        if (response.ok) {
            const data = await response.json();
            if (data.is_configured && data.github_url) {
                const githubLink = document.getElementById('githubRepoLink');
                const githubLabel = document.getElementById('githubSectionLabel');
                if (githubLink) {
                    githubLink.href = data.github_url;
                    githubLink.classList.remove('hidden-until-loaded');
                }
                if (githubLabel) {
                    githubLabel.classList.remove('hidden-until-loaded');
                }
            }
        }
    } catch (error) {
        console.error('Failed to fetch GitHub config:', error);
        // Keep link hidden on error
    }
}

// ==========================================================================
// SKU Display
// ==========================================================================

// Fetches SKU info, updates the SKU badge, and returns the display message (without logging)
async function fetchAndDisplaySku() {
    try {
        const response = await fetch(`${CONFIG.apiBaseUrl}/sku`);
        if (response.ok) {
            const data = await response.json();
            const skuDisplay = document.getElementById('skuDisplay');
            if (skuDisplay) {
                skuDisplay.textContent = `SKU: ${data.sku}`;
            }
            if (data.is_azure && data.worker) {
                return `Application is currently running on ${data.sku} SKU on worker ${data.worker}`;
            } else {
                return 'Application is currently running on Local';
            }
        }
    } catch (error) {
        console.error('Failed to fetch SKU:', error);
    }
    return null;
}

document.addEventListener('DOMContentLoaded', async function() {
    // Initialize charts
    initializeCharts();
    
    // Set up event handlers
    setupEventHandlers();
    
    // Initialize simulation ID copy handlers for event log
    initSimulationIdCopyHandlers();
    await fetchConfig();
    
    // Gather data before logging so we can force a consistent message order
    const wasIdle = await recordActivity('page_load');
    const skuMessage = await fetchAndDisplaySku();
    
    // Log all startup messages in consistent order (oldest at bottom, newest at top)
    logEvent('warning', '⚖️ Deploy only in isolated, non-production environments. Licensed under MIT License.');
    logEvent('warning', '⚖️ This software is provided "AS IS" without warranty. The author shall not be liable for any damages arising from use or misuse.');
    if (state.idleTimeoutMinutes > 0) {
        logEvent('system', `Dashboard initialized (probe rate: ${CONFIG.latencyProbeIntervalMs}ms, idle timeout: ${state.idleTimeoutMinutes}m)`);
    } else {
        logEvent('system', `Dashboard initialized (probe rate: ${CONFIG.latencyProbeIntervalMs}ms, idle timeout: disabled)`);
    }
    if (skuMessage) {
        logEvent('system', skuMessage);
    }
    logEvent('system', 'Connected to metrics hub');
    if (wasIdle) {
        logEvent('system', 'App waking up from idle state. There may be gaps in diagnostics and logs.');
    }
    
    // Start async services (WebSocket, chart updater, etc.)
    initializeWebSocket();
    startLatencyChartUpdater();
    fetchAndDisplayFooter();
    fetchAndDisplayGithubLink();
});
