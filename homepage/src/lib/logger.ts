/**
 * Client-side logging utility that sends logs to the backend
 */

type LogLevel = 'debug' | 'info' | 'warn' | 'error';

interface LogEntry {
  level: LogLevel;
  message: string;
  timestamp: string;
  component?: string;
  data?: any;
}

class ClientLogger {
  private buffer: LogEntry[] = [];
  private flushTimer: NodeJS.Timeout | null = null;
  private component: string;
  private enabled: boolean;
  
  constructor(component: string = 'client') {
    this.component = component;
    this.enabled = import.meta.env.MODE === 'development' || 
                   window.location.hostname === 'localhost';
  }
  
  private log(level: LogLevel, message: string, data?: any) {
    // Always log to console
    const consoleMethod = level === 'error' ? 'error' : level === 'warn' ? 'warn' : 'log';
    console[consoleMethod](`[${this.component}] ${message}`, data || '');
    
    if (!this.enabled) {
      return;
    }
    
    const entry: LogEntry = {
      level,
      message,
      timestamp: new Date().toISOString(),
      component: this.component,
      data
    };
    
    this.buffer.push(entry);
    this.scheduleFlush();
  }
  
  private scheduleFlush() {
    if (this.flushTimer) {
      return;
    }
    
    this.flushTimer = setTimeout(() => {
      this.flush();
    }, 1000); // Batch logs every second
  }
  
  private async flush() {
    if (this.buffer.length === 0) {
      return;
    }
    
    const logsToSend = [...this.buffer];
    this.buffer = [];
    this.flushTimer = null;
    
    try {
      // Send logs in batches
      for (const log of logsToSend) {
        await fetch('/api/logs', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(log),
        });
      }
    } catch (error) {
      // Don't log errors about logging to avoid infinite loop
      console.error('Failed to send logs to server:', error);
    }
  }
  
  debug(message: string, data?: any) {
    this.log('debug', message, data);
  }
  
  info(message: string, data?: any) {
    this.log('info', message, data);
  }
  
  warn(message: string, data?: any) {
    this.log('warn', message, data);
  }
  
  error(message: string, data?: any) {
    this.log('error', message, data);
  }
  
  // Create a child logger with a specific component name
  child(component: string): ClientLogger {
    return new ClientLogger(`${this.component}.${component}`);
  }
  
  // Force flush all pending logs
  async forceFlush() {
    if (this.flushTimer) {
      clearTimeout(this.flushTimer);
      this.flushTimer = null;
    }
    await this.flush();
  }
}

// Export singleton instance
export const logger = new ClientLogger();

// Flush logs before page unload
window.addEventListener('beforeunload', () => {
  logger.forceFlush();
});

// Log unhandled errors
window.addEventListener('error', (event) => {
  logger.error('Unhandled error', {
    message: event.message,
    filename: event.filename,
    lineno: event.lineno,
    colno: event.colno,
    stack: event.error?.stack
  });
});

// Log unhandled promise rejections
window.addEventListener('unhandledrejection', (event) => {
  logger.error('Unhandled promise rejection', {
    reason: event.reason,
    promise: event.promise
  });
});