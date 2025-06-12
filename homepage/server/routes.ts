import type { Express } from "express";
import { createServer, type Server } from "http";
import { storage } from "./storage";
import { insertLeadSchema, insertChatMessageSchema } from "@shared/schema";
import { z } from "zod";
import { handleClientLog } from "./logging";
import { createProxyMiddleware } from 'http-proxy-middleware';

export async function registerRoutes(app: Express): Promise<Server> {
  // Get the agents service URL from environment
  const AGENTS_SERVICE_URL = process.env.AGENTS_SERVICE_URL || 'http://localhost:8000';
  const agentsUrl = new URL(AGENTS_SERVICE_URL);
  const agentsTarget = `${agentsUrl.protocol}//${agentsUrl.host}`;
  
  console.log(`[Proxy] Agents service target: ${agentsTarget}`);
  
  // Proxy /api/v1/* requests to the backend
  const apiProxy = createProxyMiddleware({
    target: agentsTarget,
    changeOrigin: true,
    logLevel: 'debug',
    pathFilter: '/api/v1/**',
    on: {
      proxyReq: (proxyReq, req, res) => {
        console.log(`[Proxy] Forwarding: ${req.method} ${req.url} -> ${proxyReq.path}`);
      },
      proxyRes: (proxyRes, req, res) => {
        console.log(`[Proxy] Response ${proxyRes.statusCode} for ${req.url}`);
      },
      error: (err, req, res) => {
        console.error('[Proxy] Error:', err);
      }
    }
  });
  
  app.use(apiProxy);
  
  // Proxy WebSocket connections to the backend
  const wsProxy = createProxyMiddleware({
    target: agentsTarget,
    changeOrigin: true,
    ws: true,  // Enable WebSocket proxy
    logLevel: 'debug',
    pathFilter: '/ws/chat/**',  // More specific path to avoid HMR conflicts
    on: {
      upgrade: (proxyReq, req, socket, head) => {
        console.log(`[WebSocket Proxy] Upgrade request: ${req.url}`);
      },
      open: (proxySocket) => {
        console.log('[WebSocket Proxy] WebSocket opened');
      },
      close: (res, socket, head) => {
        console.log('[WebSocket Proxy] WebSocket closed');
      },
      error: (err, req, socket) => {
        console.error('[WebSocket Proxy] Error:', err);
      }
    }
  });
  
  app.use(wsProxy);
  
  // Get initial chat message
  app.get("/api/chat/initial", (req, res) => {
    const initialMessage = {
      content: "Hey — I'm CJ, Cratejoy's always-on teammate. Pick an option to dive in or just tell me what's hurting your business. I'll show you how I fix it—no fluff.",
    };
    
    res.json(initialMessage);
  });
  
  // Save chat message
  app.post("/api/chat/message", async (req, res) => {
    try {
      const data = insertChatMessageSchema.parse(req.body);
      const savedMessage = await storage.createChatMessage(data);
      res.json(savedMessage);
    } catch (error) {
      if (error instanceof z.ZodError) {
        res.status(400).json({ message: "Invalid chat message data", errors: error.errors });
      } else {
        res.status(500).json({ message: "Failed to save chat message" });
      }
    }
  });
  
  // Get canned response based on message
  app.post("/api/chat/response", (req, res) => {
    const { message } = req.body;
    
    let response = {
      content: "That's a great question! To give you the most helpful answer, I'd need to understand a bit more about your specific business needs.",
    };
    
    if (!message) {
      return res.status(400).json({ message: "Message is required" });
    }
    
    // Generate appropriate response based on message content
    if (message.toLowerCase().includes("support") || message.includes("ticket")) {
      response.content = "I handle 70% of common support tickets automatically. For example, when a customer asks 'Where is my order?', I check your shipping API, pull the tracking info, and send a personalized response with the exact status—all in under 60 seconds.\n\nFounders tell me this saves them 3-7 hours per day of inbox time.";
    } 
    else if (message.toLowerCase().includes("review") || message.includes("nps")) {
      response.content = "Bad reviews can kill conversion rates. I automatically respond to every review—positive or negative—within minutes. For negative reviews, I apologize, offer a solution, and flag your team only when needed.\n\nOne founder saw their marketplace ratings increase from 3.8★ to 4.6★ in just 5 weeks after implementing my review rescue system.";
    }
    else if (message.toLowerCase().includes("convert") || message.toLowerCase().includes("page")) {
      response.content = "I analyze thousands of product reviews, support conversations, and purchase patterns to generate high-converting product descriptions and email copy.\n\nOne DTC brand saw a 9.4% conversion lift after implementing my optimized copy on their top 20 products. I can A/B test variations automatically and keep improving over time.";
    }
    else if (message.toLowerCase().includes("price") || message.toLowerCase().includes("cost")) {
      response.content = "Our pricing starts at $299/month, which is about the cost of one shift of human support. Unlike other tools, we don't charge per seat—we charge based on the value we create for you.\n\nMost merchants see 10-15x ROI within the first month through support cost savings and increased sales.";
    }
    
    res.json(response);
  });
  
  // Submit lead information
  app.post("/api/leads", async (req, res) => {
    try {
      const data = insertLeadSchema.parse(req.body);
      const lead = await storage.createLead(data);
      res.json(lead);
    } catch (error) {
      if (error instanceof z.ZodError) {
        res.status(400).json({ message: "Invalid lead data", errors: error.errors });
      } else {
        res.status(500).json({ message: "Failed to save lead information" });
      }
    }
  });
  
  // Client logging endpoint
  app.post("/api/logs", handleClientLog);

  const httpServer = createServer(app);

  // Set up WebSocket upgrade handling on the HTTP server
  httpServer.on('upgrade', (request, socket, head) => {
    console.log(`[Server] Upgrade request for: ${request.url}`);
    
    // Let http-proxy-middleware handle WebSocket upgrades for /ws/chat/* paths
    if (request.url?.startsWith('/ws/chat/')) {
      wsProxy.upgrade(request, socket, head);
    } else {
      // Let other WebSocket connections (like Vite HMR) pass through
      console.log(`[Server] Non-chat WebSocket upgrade, letting it pass through`);
    }
  });

  return httpServer;
}
