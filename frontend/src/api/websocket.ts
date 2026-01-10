import type { ProgressMessage } from '../types/progress';

type MessageHandler = (message: ProgressMessage) => void;

class WebSocketClient {
  private socket: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private jobId: string | null = null;
  private messageHandler: MessageHandler | null = null;
  private reconnectTimeout: number | null = null;

  connect(jobId: string, onMessage: MessageHandler): void {
    this.jobId = jobId;
    this.messageHandler = onMessage;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/ws/${jobId}`;

    this.socket = new WebSocket(wsUrl);

    this.socket.onopen = () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
    };

    this.socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as ProgressMessage;
        if (this.messageHandler) {
          this.messageHandler(data);
        }
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
      }
    };

    this.socket.onclose = () => {
      console.log('WebSocket closed');
      if (this.reconnectAttempts < this.maxReconnectAttempts && this.jobId && this.messageHandler) {
        this.reconnectAttempts++;
        const delay = 1000 * this.reconnectAttempts;
        console.log(`Reconnecting in ${delay}ms...`);
        this.reconnectTimeout = window.setTimeout(() => {
          if (this.jobId && this.messageHandler) {
            this.connect(this.jobId, this.messageHandler);
          }
        }, delay);
      }
    };

    this.socket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }

  disconnect(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
    this.jobId = null;
    this.messageHandler = null;
    this.reconnectAttempts = 0;
  }

  sendPing(): void {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send('ping');
    }
  }
}

export const wsClient = new WebSocketClient();
