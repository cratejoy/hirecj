import winston from 'winston';
import path from 'path';
import fs from 'fs';

// Ensure logs directory exists
const logDir = 'logs';
if (!fs.existsSync(logDir)) {
  fs.mkdirSync(logDir);
}

// Define log format
const logFormat = winston.format.combine(
  winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss' }),
  winston.format.errors({ stack: true }),
  winston.format.printf(({ timestamp, level, message, ...metadata }) => {
    let msg = `[${timestamp}] [${level.toUpperCase()}] ${message}`;
    
    // Add metadata if present
    if (Object.keys(metadata).length > 0) {
      msg += ` ${JSON.stringify(metadata)}`;
    }
    
    return msg;
  })
);

// Create the logger
export const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: logFormat,
  transports: [
    // Console transport
    new winston.transports.Console({
      format: winston.format.combine(
        winston.format.colorize(),
        logFormat
      )
    }),
    
    // File transport - all logs
    new winston.transports.File({
      filename: path.join(logDir, 'homepage-backend.log'),
      maxsize: 10 * 1024 * 1024, // 10MB
      maxFiles: 5,
      tailable: true
    }),
    
    // File transport - errors only
    new winston.transports.File({
      filename: path.join(logDir, 'homepage-backend.error.log'),
      level: 'error',
      maxsize: 10 * 1024 * 1024, // 10MB
      maxFiles: 5,
      tailable: true
    })
  ]
});

// Create specialized loggers
export const clientLogger = logger.child({ component: 'client' });
export const apiLogger = logger.child({ component: 'api' });
export const wsLogger = logger.child({ component: 'websocket' });

// Request logging middleware
export const requestLogger = (req: any, res: any, next: any) => {
  const start = Date.now();
  
  // Skip logging for static assets and Vite HMR requests
  const skipPaths = [
    '/@fs/',           // Vite file system
    '/@vite/',         // Vite internal
    '/node_modules/',  // Node modules
    '/src/',           // Source files in dev
    '.js',             // JS files
    '.jsx',            // JSX files
    '.ts',             // TS files
    '.tsx',            // TSX files
    '.css',            // CSS files
    '.scss',           // SCSS files
    '.png',            // Images
    '.jpg',
    '.jpeg',
    '.gif',
    '.svg',
    '.ico',
    '.woff',           // Fonts
    '.woff2',
    '.ttf',
    '.eot',
    '/__vite',         // Vite WebSocket
  ];
  
  const shouldSkip = skipPaths.some(path => 
    req.path.includes(path) || req.path.endsWith(path)
  );
  
  if (shouldSkip) {
    return next();
  }
  
  // Log request
  apiLogger.info(`[REQUEST_START] ${req.method} ${req.path}`, {
    query: req.query,
    body: req.body,
    ip: req.ip,
    userAgent: req.get('user-agent')
  });
  
  // Capture response
  const originalSend = res.send;
  res.send = function(data: any) {
    const duration = Date.now() - start;
    
    apiLogger.info(`[REQUEST_END] ${req.method} ${req.path}`, {
      status: res.statusCode,
      duration: `${duration}ms`
    });
    
    originalSend.call(this, data);
  };
  
  next();
};

// Client log endpoint handler
export const handleClientLog = (req: any, res: any) => {
  const { level = 'info', message, data, timestamp, component = 'unknown' } = req.body;
  
  // Validate log level
  const validLevels = ['debug', 'info', 'warn', 'error'];
  const logLevel = validLevels.includes(level) ? level : 'info';
  
  // Log with metadata
  clientLogger.log(logLevel, `[CLIENT] ${message}`, {
    component,
    clientTimestamp: timestamp,
    data,
    userAgent: req.get('user-agent'),
    ip: req.ip
  });
  
  res.json({ success: true });
};