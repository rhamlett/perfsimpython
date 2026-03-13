/**
 * Chart.js integration for metrics visualization
 * Handles CPU and memory trend charts
 */

// Chart configuration constants
const MAX_DATA_POINTS = 60; // 30 seconds at 500ms intervals
const CHART_COLORS = {
  cpu: {
    line: 'rgb(48, 105, 152)',
    fill: 'rgba(48, 105, 152, 0.1)'
  },
  memory: {
    line: 'rgb(255, 212, 59)',
    fill: 'rgba(255, 212, 59, 0.1)'
  },
  latency: {
    line: 'rgb(40, 167, 69)',
    fill: 'rgba(40, 167, 69, 0.1)'
  }
};

// Store chart data
const chartData = {
  labels: [],
  cpu: [],
  memory: [],
  latency: []
};

// Chart instances
let cpuMemoryChart = null;
let latencyChart = null;

/**
 * Initialize the charts
 */
function initializeCharts() {
  // Check if Chart.js is loaded
  if (typeof Chart === 'undefined') {
    console.error('Chart.js not loaded');
    return;
  }

  // Initialize CPU/Memory chart
  const cpuMemoryCtx = document.getElementById('cpu-memory-chart');
  if (cpuMemoryCtx) {
    cpuMemoryChart = new Chart(cpuMemoryCtx, {
      type: 'line',
      data: {
        labels: chartData.labels,
        datasets: [
          {
            label: 'CPU %',
            data: chartData.cpu,
            borderColor: CHART_COLORS.cpu.line,
            backgroundColor: CHART_COLORS.cpu.fill,
            fill: true,
            tension: 0.4,
            pointRadius: 0
          },
          {
            label: 'Memory %',
            data: chartData.memory,
            borderColor: CHART_COLORS.memory.line,
            backgroundColor: CHART_COLORS.memory.fill,
            fill: true,
            tension: 0.4,
            pointRadius: 0
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false
        },
        scales: {
          x: {
            display: true,
            title: {
              display: false
            },
            ticks: {
              maxTicksLimit: 10,
              font: {
                size: 10
              }
            }
          },
          y: {
            display: true,
            min: 0,
            max: 100,
            title: {
              display: true,
              text: '%'
            },
            ticks: {
              font: {
                size: 10
              }
            }
          }
        },
        plugins: {
          legend: {
            position: 'top',
            labels: {
              boxWidth: 12,
              font: {
                size: 11
              }
            }
          },
          tooltip: {
            callbacks: {
              label: function(context) {
                return context.dataset.label + ': ' + context.parsed.y.toFixed(1) + '%';
              }
            }
          }
        },
        animation: {
          duration: 0
        }
      }
    });
  }

  // Initialize Latency chart (placeholder for future use)
  const latencyCtx = document.getElementById('latency-chart');
  if (latencyCtx) {
    latencyChart = new Chart(latencyCtx, {
      type: 'line',
      data: {
        labels: chartData.labels,
        datasets: [
          {
            label: 'Response Time (ms)',
            data: chartData.latency,
            borderColor: CHART_COLORS.latency.line,
            backgroundColor: CHART_COLORS.latency.fill,
            fill: true,
            tension: 0.4,
            pointRadius: 0
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false
        },
        scales: {
          x: {
            display: true,
            ticks: {
              maxTicksLimit: 10,
              font: {
                size: 10
              }
            }
          },
          y: {
            display: true,
            min: 0,
            title: {
              display: true,
              text: 'ms'
            },
            ticks: {
              font: {
                size: 10
              }
            }
          }
        },
        plugins: {
          legend: {
            position: 'top',
            labels: {
              boxWidth: 12,
              font: {
                size: 11
              }
            }
          }
        },
        animation: {
          duration: 0
        }
      }
    });
  }
}

/**
 * Update charts with new metrics data
 */
function updateCharts(metrics) {
  if (!cpuMemoryChart) return;

  // Get current time for label
  const now = new Date();
  const timeLabel = now.toLocaleTimeString('en-US', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });

  // Add new data points
  chartData.labels.push(timeLabel);
  chartData.cpu.push(metrics.cpu_percent || 0);
  chartData.memory.push(metrics.memory?.percent || 0);
  chartData.latency.push(0); // Placeholder for latency

  // Remove old data points if exceeding max
  while (chartData.labels.length > MAX_DATA_POINTS) {
    chartData.labels.shift();
    chartData.cpu.shift();
    chartData.memory.shift();
    chartData.latency.shift();
  }

  // Update charts
  cpuMemoryChart.update('none');
  if (latencyChart) {
    latencyChart.update('none');
  }
}

/**
 * Clear all chart data
 */
function clearCharts() {
  chartData.labels = [];
  chartData.cpu = [];
  chartData.memory = [];
  chartData.latency = [];

  if (cpuMemoryChart) {
    cpuMemoryChart.update();
  }
  if (latencyChart) {
    latencyChart.update();
  }
}

// Export functions for use in other modules
window.initializeCharts = initializeCharts;
window.updateCharts = updateCharts;
window.clearCharts = clearCharts;
