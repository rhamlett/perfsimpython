/**
 * Dashboard logic for Performance Problem Simulator
 * Handles UI interactions, form submissions, and real-time updates
 */

// WebSocket client instance
let wsClient = null;

// DOM element references
const elements = {};

/**
 * Initialize the dashboard on page load
 */
document.addEventListener('DOMContentLoaded', function() {
  // Cache DOM elements
  cacheElements();
  
  // Set up event listeners
  setupEventListeners();
  
  // Initialize charts
  if (typeof initializeCharts === 'function') {
    initializeCharts();
  }
  
  // Connect to WebSocket
  connectWebSocket();
});

/**
 * Cache frequently accessed DOM elements
 */
function cacheElements() {
  // Header controls
  elements.sidebarToggle = document.getElementById('sidebar-toggle');
  elements.panelToggle = document.getElementById('panel-toggle');
  
  // Containers
  elements.sidebar = document.getElementById('sidebar');
  elements.sidePanel = document.getElementById('side-panel');
  elements.mainContent = document.getElementById('main-content');
  elements.overlay = document.getElementById('overlay');
  
  // Metric tiles
  elements.cpuValue = document.getElementById('cpu-value');
  elements.memoryValue = document.getElementById('memory-value');
  elements.processMemoryValue = document.getElementById('process-memory-value');
  elements.activeSimsValue = document.getElementById('active-sims-value');
  
  // Simulation list
  elements.simulationList = document.getElementById('simulation-list');
  
  // Event log
  elements.eventLog = document.getElementById('event-log-list');
}

/**
 * Set up event listeners for UI interactions
 */
function setupEventListeners() {
  // Sidebar toggle
  if (elements.sidebarToggle) {
    elements.sidebarToggle.addEventListener('click', toggleSidebar);
  }
  
  // Panel toggle
  if (elements.panelToggle) {
    elements.panelToggle.addEventListener('click', togglePanel);
  }
  
  // Overlay click closes sidebar/panel
  if (elements.overlay) {
    elements.overlay.addEventListener('click', closeAllDrawers);
  }
  
  // CPU stress form
  const cpuForm = document.getElementById('cpu-form');
  if (cpuForm) {
    cpuForm.addEventListener('submit', handleCpuFormSubmit);
  }
  
  // CPU stop all button
  const cpuStopAllBtn = document.getElementById('cpu-stop-all');
  if (cpuStopAllBtn) {
    cpuStopAllBtn.addEventListener('click', handleCpuStopAll);
  }
  
  // Memory allocate form
  const memoryForm = document.getElementById('memory-form');
  if (memoryForm) {
    memoryForm.addEventListener('submit', handleMemoryFormSubmit);
  }
  
  // Memory release all button
  const memoryReleaseAllBtn = document.getElementById('memory-release-all');
  if (memoryReleaseAllBtn) {
    memoryReleaseAllBtn.addEventListener('click', handleMemoryReleaseAll);
  }
  
  // Blocking form
  const blockingForm = document.getElementById('blocking-form');
  if (blockingForm) {
    blockingForm.addEventListener('submit', handleBlockingFormSubmit);
  }
  
  // Slow request form
  const slowForm = document.getElementById('slow-form');
  if (slowForm) {
    slowForm.addEventListener('submit', handleSlowFormSubmit);
  }
  
  // Failed requests form
  const failedForm = document.getElementById('failed-form');
  if (failedForm) {
    failedForm.addEventListener('submit', handleFailedFormSubmit);
  }
  
  // Crash form
  const crashForm = document.getElementById('crash-form');
  if (crashForm) {
    crashForm.addEventListener('submit', handleCrashFormSubmit);
  }
}

/**
 * Connect to WebSocket for real-time updates
 */
function connectWebSocket() {
  wsClient = new WebSocketClient({
    onMessage: handleWebSocketMessage,
    onStatusChange: handleConnectionStatusChange
  });
  
  wsClient.connect();
}

/**
 * Handle incoming WebSocket messages
 */
function handleWebSocketMessage(data) {
  // Update metric tiles
  updateMetricTiles(data);
  
  // Update charts
  if (typeof updateCharts === 'function') {
    updateCharts(data);
  }
  
  // Update active simulations list
  updateSimulationList(data.active_simulations || []);
  
  // Update event log if new events
  if (data.events) {
    updateEventLog(data.events);
  }
}

/**
 * Handle WebSocket connection status changes
 */
function handleConnectionStatusChange(status) {
  console.log('Connection status:', status);
}

/**
 * Update metric tile values
 */
function updateMetricTiles(data) {
  if (elements.cpuValue && data.cpu_percent !== undefined) {
    elements.cpuValue.textContent = data.cpu_percent.toFixed(1);
    
    // Update tile class based on value
    const tile = elements.cpuValue.closest('.metric-tile');
    if (tile) {
      tile.classList.remove('success', 'warning', 'danger');
      if (data.cpu_percent > 80) {
        tile.classList.add('danger');
      } else if (data.cpu_percent > 50) {
        tile.classList.add('warning');
      }
    }
  }
  
  if (elements.memoryValue && data.memory) {
    elements.memoryValue.textContent = data.memory.percent.toFixed(1);
    
    const tile = elements.memoryValue.closest('.metric-tile');
    if (tile) {
      tile.classList.remove('success', 'warning', 'danger');
      if (data.memory.percent > 80) {
        tile.classList.add('danger');
      } else if (data.memory.percent > 60) {
        tile.classList.add('warning');
      }
    }
  }
  
  if (elements.processMemoryValue && data.process) {
    elements.processMemoryValue.textContent = data.process.memory_mb.toFixed(0);
  }
  
  if (elements.activeSimsValue && data.active_simulations) {
    elements.activeSimsValue.textContent = data.active_simulations.length;
  }
}

/**
 * Update the list of active simulations
 */
function updateSimulationList(simulations) {
  if (!elements.simulationList) return;
  
  if (simulations.length === 0) {
    elements.simulationList.innerHTML = '<div class="no-simulations">No active simulations</div>';
    return;
  }
  
  const html = simulations.map(sim => `
    <div class="simulation-item">
      <div class="simulation-info">
        <span class="simulation-type">${formatSimulationType(sim.type)}</span>
        <span class="simulation-details">
          Running for ${formatDuration(sim.elapsed_seconds)}
          ${sim.duration_seconds ? ` / ${sim.duration_seconds}s` : ''}
        </span>
      </div>
      <button class="btn btn-sm btn-danger" onclick="stopSimulation('${sim.type}', '${sim.id}')">
        Stop
      </button>
    </div>
  `).join('');
  
  elements.simulationList.innerHTML = html;
}

/**
 * Update the event log
 */
function updateEventLog(events) {
  if (!elements.eventLog) return;
  
  const html = events.map(event => `
    <div class="event-item">
      <span class="event-time">${formatEventTime(event.timestamp)}</span>
      <span class="event-type ${event.event_type}">${event.event_type}</span>
      <span class="event-message">${event.message}</span>
    </div>
  `).join('');
  
  elements.eventLog.innerHTML = html;
}

/**
 * Add a new event to the log
 */
function addEventToLog(type, message) {
  if (!elements.eventLog) return;
  
  const now = new Date();
  const html = `
    <div class="event-item">
      <span class="event-time">${formatEventTime(now.toISOString())}</span>
      <span class="event-type ${type}">${type}</span>
      <span class="event-message">${message}</span>
    </div>
  `;
  
  elements.eventLog.insertAdjacentHTML('afterbegin', html);
  
  // Limit to 100 events
  while (elements.eventLog.children.length > 100) {
    elements.eventLog.lastChild.remove();
  }
}

/**
 * Toggle sidebar visibility
 */
function toggleSidebar() {
  elements.sidebar?.classList.toggle('open');
  elements.mainContent?.classList.toggle('sidebar-open');
  elements.overlay?.classList.toggle('active', elements.sidebar?.classList.contains('open'));
}

/**
 * Toggle side panel visibility
 */
function togglePanel() {
  elements.sidePanel?.classList.toggle('open');
  elements.mainContent?.classList.toggle('panel-open');
}

/**
 * Close all drawers
 */
function closeAllDrawers() {
  elements.sidebar?.classList.remove('open');
  elements.mainContent?.classList.remove('sidebar-open');
  elements.overlay?.classList.remove('active');
}

/**
 * Format simulation type for display
 */
function formatSimulationType(type) {
  const types = {
    'cpu_stress': 'CPU Stress',
    'memory_pressure': 'Memory Pressure',
    'sync_blocking': 'Sync Blocking',
    'async_blocking': 'Async Blocking',
    'slow_request': 'Slow Request',
    'failed_request': 'Failed Request'
  };
  return types[type] || type;
}

/**
 * Format duration in seconds to human-readable string
 */
function formatDuration(seconds) {
  if (seconds < 60) {
    return `${Math.floor(seconds)}s`;
  }
  const minutes = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${minutes}m ${secs}s`;
}

/**
 * Format event timestamp
 */
function formatEventTime(isoString) {
  try {
    const date = new Date(isoString);
    return date.toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  } catch (e) {
    return isoString;
  }
}

/**
 * Stop a specific simulation
 */
async function stopSimulation(type, id) {
  const endpoints = {
    'cpu_stress': '/api/cpu/stop',
    'memory_pressure': '/api/memory/release',
    'sync_blocking': '/api/blocking/stop',
    'async_blocking': '/api/blocking/stop',
    'slow_request': '/api/slow/stop'
  };
  
  const endpoint = endpoints[type];
  if (!endpoint) {
    console.error('Unknown simulation type:', type);
    return;
  }
  
  try {
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ simulation_id: id })
    });
    
    const result = await response.json();
    if (result.success) {
      addEventToLog('info', `Stopped ${formatSimulationType(type)} simulation`);
    }
  } catch (error) {
    console.error('Failed to stop simulation:', error);
    addEventToLog('error', `Failed to stop simulation: ${error.message}`);
  }
}

// Form submission handlers
async function handleCpuFormSubmit(event) {
  event.preventDefault();
  const formData = new FormData(event.target);
  
  try {
    const response = await fetch('/api/cpu/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        duration_seconds: formData.get('duration') ? parseFloat(formData.get('duration')) : null,
        intensity: parseInt(formData.get('intensity')) || 5,
        workers: parseInt(formData.get('workers')) || 1
      })
    });
    
    const result = await response.json();
    if (result.success) {
      addEventToLog('start', 'CPU stress started');
    } else {
      addEventToLog('error', result.message || 'Failed to start CPU stress');
    }
  } catch (error) {
    addEventToLog('error', `Failed to start CPU stress: ${error.message}`);
  }
}

async function handleCpuStopAll() {
  try {
    const response = await fetch('/api/cpu/stop-all', { method: 'POST' });
    const result = await response.json();
    addEventToLog('stop', `Stopped ${result.data?.stopped_count || 0} CPU simulation(s)`);
  } catch (error) {
    addEventToLog('error', `Failed to stop CPU stress: ${error.message}`);
  }
}

async function handleMemoryFormSubmit(event) {
  event.preventDefault();
  const formData = new FormData(event.target);
  
  try {
    const response = await fetch('/api/memory/allocate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        size_mb: parseInt(formData.get('size')) || 100
      })
    });
    
    const result = await response.json();
    if (result.success) {
      addEventToLog('start', `Allocated ${formData.get('size') || 100} MB memory`);
    } else {
      addEventToLog('error', result.message || 'Failed to allocate memory');
    }
  } catch (error) {
    addEventToLog('error', `Failed to allocate memory: ${error.message}`);
  }
}

async function handleMemoryReleaseAll() {
  try {
    const response = await fetch('/api/memory/release-all', { method: 'POST' });
    const result = await response.json();
    addEventToLog('stop', 'Released all memory blocks');
  } catch (error) {
    addEventToLog('error', `Failed to release memory: ${error.message}`);
  }
}

async function handleBlockingFormSubmit(event) {
  event.preventDefault();
  const formData = new FormData(event.target);
  const blockType = formData.get('type') || 'sync';
  
  try {
    const response = await fetch(`/api/blocking/${blockType}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        duration_seconds: parseFloat(formData.get('duration')) || 5,
        count: parseInt(formData.get('count')) || 1
      })
    });
    
    const result = await response.json();
    if (result.success) {
      addEventToLog('start', `Started ${blockType} blocking`);
    } else {
      addEventToLog('error', result.message || 'Failed to start blocking');
    }
  } catch (error) {
    addEventToLog('error', `Failed to start blocking: ${error.message}`);
  }
}

async function handleSlowFormSubmit(event) {
  event.preventDefault();
  const formData = new FormData(event.target);
  
  try {
    const response = await fetch('/api/slow/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        delay_seconds: parseFloat(formData.get('delay')) || 5,
        interval_seconds: parseFloat(formData.get('interval')) || 1,
        max_requests: parseInt(formData.get('count')) || 10
      })
    });
    
    const result = await response.json();
    if (result.success) {
      addEventToLog('start', 'Started slow request generator');
    } else {
      addEventToLog('error', result.message || 'Failed to start slow requests');
    }
  } catch (error) {
    addEventToLog('error', `Failed to start slow requests: ${error.message}`);
  }
}

async function handleFailedFormSubmit(event) {
  event.preventDefault();
  const formData = new FormData(event.target);
  
  try {
    const response = await fetch('/api/failed-requests', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        count: parseInt(formData.get('count')) || 10
      })
    });
    
    const result = await response.json();
    if (result.success) {
      addEventToLog('info', `Generated ${formData.get('count') || 10} failed requests`);
    } else {
      addEventToLog('error', result.message || 'Failed to generate errors');
    }
  } catch (error) {
    addEventToLog('error', `Failed to generate errors: ${error.message}`);
  }
}

async function handleCrashFormSubmit(event) {
  event.preventDefault();
  const formData = new FormData(event.target);
  const crashType = formData.get('type') || 'exception';
  
  // Confirm dangerous action
  if (!confirm(`WARNING: This will crash the application with a "${crashType}" crash. Continue?`)) {
    return;
  }
  
  try {
    addEventToLog('warning', `Triggering ${crashType} crash...`);
    
    const response = await fetch('/api/crash', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ crash_type: crashType })
    });
    
    // If we get here, the crash didn't happen as expected
    const result = await response.json();
    addEventToLog('error', result.message || 'Crash did not occur');
  } catch (error) {
    addEventToLog('error', `Crash triggered: connection lost`);
  }
}
