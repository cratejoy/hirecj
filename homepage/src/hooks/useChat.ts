import { useState, useEffect } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { useToast } from '@/hooks/use-toast';

interface Message {
  id: string;
  sender: 'user' | 'cj';
  content: string;
  timestamp: string;
}

export const useChat = (setEmailModalOpen: (open: boolean) => void) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [showedFlashBrief, setShowedFlashBrief] = useState(false);
  const { toast } = useToast();

  // Initialize with morning greeting and flash brief offer
  useEffect(() => {
    const initialMessage: Message = {
      id: '1',
      sender: 'cj',
      content: "Morning, boss! 👋 Hope you had a good night. Would you like to see your daily flash brief?",
      timestamp: formatTimestamp()
    };
    
    setMessages([initialMessage]);
  }, []);
  
  const formatTimestamp = () => {
    const now = new Date();
    return now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };
  
  const addUserMessage = (content: string) => {
    const newMessage: Message = {
      id: uuidv4(),
      sender: 'user',
      content,
      timestamp: formatTimestamp()
    };
    
    setMessages((prev) => [...prev, newMessage]);
    simulateResponse(content);
  };
  
  const handleSendMessage = (message: string) => {
    if (message.trim()) {
      addUserMessage(message);
    }
  };
  
  const handleOptionClick = (option: number) => {
    let selectedOption = "";
    
    switch (option) {
      case 1:
        selectedOption = "I want to learn about: Slash 70% of support tickets";
        break;
      case 2:
        selectedOption = "I want to learn about: Rescue bad reviews & boost NPS";
        break;
      case 3:
        selectedOption = "I want to learn about: Make product pages convert higher";
        break;
      default:
        selectedOption = "I want to learn more about CJ";
    }
    
    addUserMessage(selectedOption);
  };
  
  const simulateResponse = (userMessage: string) => {
    setIsTyping(true);
    
    // Simulate typing delay
    setTimeout(() => {
      setIsTyping(false);
      
      let response = "";
      
      // Check if this is a response to the flash brief offer
      const userMsgLower = userMessage.toLowerCase();
      const isAffirmative = userMsgLower.includes('yes') || 
                           userMsgLower.includes('yeah') || 
                           userMsgLower.includes('sure') || 
                           userMsgLower.includes('ok') || 
                           userMsgLower.includes('okay') ||
                           userMsgLower.includes('definitely') ||
                           userMsgLower.includes('please');
                           
      // If user hasn't seen flash brief yet and gives affirmative response
      if (!showedFlashBrief && isAffirmative) {
        setShowedFlashBrief(true);
        response = "📊 **Daily Flash Report: May 21, 2025**\n\n" +
                  "**Ticket Stats (Last 24h)**\n" +
                  "• 42 tickets handled automatically (68% resolution rate)\n" +
                  "• Average response time: 38 seconds\n" + 
                  "• Top issue: Shipping delay questions (16 tickets)\n\n" +
                  
                  "**Revenue Impact**\n" + 
                  "• Recovered $1,840 in potential cancellations\n" + 
                  "• Saved 8.4 staff hours in ticket handling\n\n" +
                  
                  "**Action Items**\n" + 
                  "• 3 high-priority escalations waiting in Slack\n" + 
                  "• 1 knowledge base article needs updating\n\n" +
                  
                  "What area would you like me to focus on today?";
      }
      // If user has already seen flash brief or declined to see it
      else if (!showedFlashBrief && !isAffirmative) {
        setShowedFlashBrief(true);
        response = "No problem! I'm here whenever you need me. What can I help you with today?";
      }
      // Standard conversation flows after flash brief handled
      else if (userMessage.includes("Slash 70% of support tickets") || userMessage.includes("support")) {
        response = "I handle 70% of common support tickets automatically. For example, when a customer asks 'Where is my order?', I check your shipping API, pull the tracking info, and send a personalized response with the exact status—all in under 60 seconds.\n\nFounders tell me this saves them 3-7 hours per day of inbox time. Want me to explain how we integrate with your current system?";
      }
      else if (userMessage.includes("Rescue bad reviews") || userMessage.includes("review")) {
        response = "Bad reviews can kill conversion rates. I automatically respond to every review—positive or negative—within minutes. For negative reviews, I apologize, offer a solution, and flag your team only when needed.\n\nOne founder saw their marketplace ratings increase from 3.8★ to 4.6★ in just 5 weeks after implementing my review rescue system. Would you like to see a demo of how this works?";
      }
      else if (userMessage.includes("Make product pages convert") || userMessage.includes("convert")) {
        response = "I analyze thousands of product reviews, support conversations, and purchase patterns to generate high-converting product descriptions and email copy.\n\nOne DTC brand saw a 9.4% conversion lift after implementing my optimized copy on their top 20 products. I can A/B test variations automatically and keep improving over time. Would you like to see examples of before/after copy that drove conversion increases?";
      }
      else if (userMessage.toLowerCase().includes("price") || userMessage.toLowerCase().includes("cost")) {
        response = "Our pricing starts at $299/month, which is about the cost of one shift of human support. Unlike other tools, we don't charge per seat—we charge based on the value we create for you.\n\nWant me to show you a customized ROI calculation for your business?";
      }
      else if (userMessage.toLowerCase().includes("demo") || userMessage.toLowerCase().includes("trial")) {
        response = "I'd be happy to set up a personalized demo for you. This would include a custom walkthrough of how I'd handle your specific support and growth challenges.";
        
        // Show email modal after this response
        setTimeout(() => {
          setEmailModalOpen(true);
        }, 1000);
      }
      else if (userMessage.toLowerCase().includes("ticket") || userMessage.toLowerCase().includes("shipping delay")) {
        response = "I've reviewed the shipping delay tickets from today. The main issue seems to be with the East Coast fulfillment center. I've already drafted an email to affected customers explaining the situation and offering 15% off their next purchase as compensation. Would you like me to send these out automatically?";
      }
      else if (userMessage.toLowerCase().includes("escalation") || userMessage.toLowerCase().includes("high-priority") || userMessage.toLowerCase().includes("slack")) {
        response = "The 3 high-priority escalations are:\n\n1. VIP customer Rachel B. requesting a refund ($450)\n2. Potential bulk order inquiry from BoutiqueCorp (est. value $8,200)\n3. Influencer complaint about product quality (22k followers)\n\nWould you like me to handle any of these, or shall I connect you directly?";
      }
      else {
        response = "I'm here to help! Would you like me to assist with:\n\n1. Customer support automation\n2. Review management\n3. Conversion optimization\n4. Flash report details\n\nOr feel free to ask me about anything specific.";
      }
      
      const newMessage: Message = {
        id: uuidv4(),
        sender: 'cj',
        content: response,
        timestamp: formatTimestamp()
      };
      
      setMessages((prev) => [...prev, newMessage]);
    }, 1500);
  };
  
  const captureEmail = (data: { email: string, company: string, volume: string }) => {
    // Here we would normally send this data to the server
    // For now, just show a toast notification
    
    toast({
      title: "Demo request submitted!",
      description: `We'll contact ${data.email} with your personalized demo.`,
    });
    
    // Add confirmation message to chat
    const newMessage: Message = {
      id: uuidv4(),
      sender: 'cj',
      content: `Thanks for your interest! I've scheduled a personalized demo for ${data.email}. Our team will reach out within one business day to set up a time that works for you.`,
      timestamp: formatTimestamp()
    };
    
    setMessages((prev) => [...prev, newMessage]);
  };
  
  return {
    messages,
    addUserMessage,
    isTyping,
    handleSendMessage,
    handleOptionClick,
    captureEmail
  };
};
