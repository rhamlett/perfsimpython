/**
 * WebSocket client for real-time metrics updates
 * Manages connection with exponential backoff reconnection
 */

class WebSocketClient {
  constructor(options = {}) {
    this.url = options.url || this.getWebSocketUrl();
    this.reconnectBaseDelay = options.reconnectBaseDelay || 1000;
    this.maxRetries = options.maxRetries || 5;
    this.onMessage = options.onMessage || (() => {});
    this.onStatusChange = options.onStatusChange || (() => {});
    
    this.ws = null;
    this.retryCount = 0;
    this.reconnectTimer = null;
    this.status = 'disconnected';
  }

  /**
   * Get WebSocket URL based on current location
   */
  getWebSocketUrl() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${window.location.host}/ws/metrics`;
  }

  /**
   * Connect to WebSocket server
   */
  connect() {
    if (this.ws && (this.ws.readyState === WebSocket.CONNECTING || this.ws.readyState === WebSocket.OPEN)) {
      return;
    }

    this.setStatus('connecting');
    
    try {
      this.ws = new WebSocket(this.url);
      
      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.retryCount = 0;
        this.setStatus('connected');
      };
      
      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.onMessage(data);
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
        }
      };
      
      this.ws.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason);
        this.ws = null;
        
        if (event.code !== 1000) {
          // Abnormal close, try to reconnect
          this.scheduleReconnect();
        } else {
          this.setStatus('disconnected');
        }
      };
      
      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        // onclose will be called after onerror
      };
    } catch (e) {
      console.error('Failed to create WebSocket:', e);
      this.scheduleReconnect();
    }
  }

  /**
   * Schedule a reconnection attempt with exponential backoff
   */
  scheduleReconnect() {
    if (this.retryCount >= this.maxRetries) {
      console.log('Max retries reached, stopping reconnection attempts');
      this.setStatus('disconnected');
      return;
    }

    this.setStatus('reconnecting');
    this.retryCount++;
    
    // Exponential backoff: 1s, 2s, 4s, 8s, 16s
    const delay = this.reconnectBaseDelay * Math.pow(2, this.retryCount - 1);
    console.log(`Reconnecting in ${delay}ms (attempt ${this.retryCount}/${this.maxRetries})`);
    
    this.reconnectTimer = setTimeout(() => {
      this.connect();
    }, delay);
  }

  /**
   * Set and broadcast connection status
   */
  setStatus(status) {
    this.status = status;
    this.onStatusChange(status);
    this.updateStatusDisplay(status);
  }

  /**
   * Update the connection status display in the UI
   */
  updateStatusDisplay(status) {
    const statusDot = document.getElementById('connection-status-dot');
    const statusText = document.getElementById('connection-status-text');
    
    if (statusDot) {
      statusDot.className = 'status-dot ' + status;
    }
    
    if (statusText) {
      const statusLabels = {
        'connected': 'Connected',
        'disconnected': 'Disconnected',
        'reconnecting': 'Reconnecting...',
        'connecting': 'Connecting...'
      };
      statusText.textContent = statusLabels[status] || status;
    }
  }

  /**
   * Disconnect from WebSocket server
   */
  disconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }
    
    this.setStatus('disconnected');
  }

  /**
   * Check if WebSocket is currently connected
   */
  isConnected() {
    return this.ws && this.ws.readyState === WebSocket.OPEN;
  }

  /**
   * Send a message through WebSocket
   */
  send(data) {
    if (this.isConnected()) {
      this.ws.send(JSON.stringify(data));
      return true;
    }
    return false;
  }
}

// Export for use in other modules
window.WebSocketClient = WebSocketClient;
