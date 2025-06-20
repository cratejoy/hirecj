/**
 * Debug utility for development logging
 * Set VITE_DEBUG=true in environment to enable debug logs
 */

const DEBUG = import.meta.env.VITE_DEBUG === 'true' || import.meta.env.DEV;

export const debug = {
  log: (...args: any[]) => {
    if (DEBUG) console.log(...args);
  },
  
  error: (...args: any[]) => {
    // Always log errors
    console.error(...args);
  },
  
  warn: (...args: any[]) => {
    if (DEBUG) console.warn(...args);
  },
  
  group: (...args: any[]) => {
    if (DEBUG) console.group(...args);
  },
  
  groupEnd: () => {
    if (DEBUG) console.groupEnd();
  }
};