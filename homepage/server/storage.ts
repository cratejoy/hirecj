import { users, type User, type InsertUser, type Lead, type InsertLead, type ChatMessage, type InsertChatMessage } from "@shared/schema";

// modify the interface with any CRUD methods
// you might need

export interface IStorage {
  getUser(id: number): Promise<User | undefined>;
  getUserByUsername(username: string): Promise<User | undefined>;
  createUser(user: InsertUser): Promise<User>;
  
  // Lead management
  createLead(lead: InsertLead): Promise<Lead>;
  getLeadByEmail(email: string): Promise<Lead | undefined>;
  
  // Chat message management
  createChatMessage(message: InsertChatMessage): Promise<ChatMessage>;
  getChatMessagesByLeadId(leadId: number): Promise<ChatMessage[]>;
}

export class MemStorage implements IStorage {
  private users: Map<number, User>;
  private leads: Map<number, Lead>;
  private chatMessages: Map<number, ChatMessage>;
  
  currentUserId: number;
  currentLeadId: number;
  currentMessageId: number;

  constructor() {
    this.users = new Map();
    this.leads = new Map();
    this.chatMessages = new Map();
    
    this.currentUserId = 1;
    this.currentLeadId = 1;
    this.currentMessageId = 1;
  }

  async getUser(id: number): Promise<User | undefined> {
    return this.users.get(id);
  }

  async getUserByUsername(username: string): Promise<User | undefined> {
    return Array.from(this.users.values()).find(
      (user) => user.username === username,
    );
  }

  async createUser(insertUser: InsertUser): Promise<User> {
    const id = this.currentUserId++;
    const user: User = { ...insertUser, id };
    this.users.set(id, user);
    return user;
  }
  
  async createLead(insertLead: InsertLead): Promise<Lead> {
    const id = this.currentLeadId++;
    const createdAt = new Date();
    const lead: Lead = { 
      ...insertLead, 
      id, 
      createdAt,
      company: insertLead.company ?? null,
      volume: insertLead.volume ?? null
    };
    this.leads.set(id, lead);
    return lead;
  }
  
  async getLeadByEmail(email: string): Promise<Lead | undefined> {
    return Array.from(this.leads.values()).find(
      (lead) => lead.email === email,
    );
  }
  
  async createChatMessage(insertMessage: InsertChatMessage): Promise<ChatMessage> {
    const id = this.currentMessageId++;
    const createdAt = new Date();
    const chatMessage: ChatMessage = { 
      ...insertMessage, 
      id, 
      createdAt,
      leadId: insertMessage.leadId ?? null
    };
    this.chatMessages.set(id, chatMessage);
    return chatMessage;
  }
  
  async getChatMessagesByLeadId(leadId: number): Promise<ChatMessage[]> {
    return Array.from(this.chatMessages.values()).filter(
      (message) => message.leadId === leadId,
    );
  }
}

export const storage = new MemStorage();
