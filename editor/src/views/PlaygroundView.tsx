import React, { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Pencil, MessageSquare, Workflow, ChevronDown, Send, Loader2 } from 'lucide-react'
import { useToast } from '@/components/ui/use-toast'
import { 
  parseWorkflow, 
  isAgentInitiated, 
  getInitialMessage,
  type WorkflowConfig 
} from '@/utils/workflowParser'
import { AgentInitiatedView } from '@/components/playground/AgentInitiatedView'
import { MerchantInitiatedView } from '@/components/playground/MerchantInitiatedView'

const API_BASE = '/api/v1'

interface Message {
  id: string;
  role: 'agent' | 'user';
  content: string;
  timestamp: string;
}

interface Persona {
  id: string;
  name: string;
  business: string;
}

interface Scenario {
  id: string;
  name: string;
  description: string;
}

interface WorkflowListItem {
  id: string;
  name: string;
  description: string;
}

export function PlaygroundView() {
  // State for configuration
  const [workflows, setWorkflows] = useState<WorkflowListItem[]>([])
  const [selectedWorkflowId, setSelectedWorkflowId] = useState<string>('')
  const [workflow, setWorkflow] = useState<WorkflowConfig | null>(null)
  const [personas, setPersonas] = useState<Persona[]>([])
  const [selectedPersona, setSelectedPersona] = useState<string>('')
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [selectedScenario, setSelectedScenario] = useState<string>('')
  
  // State for conversation
  const [conversationStarted, setConversationStarted] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [inputMessage, setInputMessage] = useState('')
  const [loading, setLoading] = useState(false)
  const [sendingMessage, setSendingMessage] = useState(false)
  
  // UI state
  const [workflowExpanded, setWorkflowExpanded] = useState(false)
  
  const { toast } = useToast()

  // Load initial data
  useEffect(() => {
    loadWorkflows()
    loadPersonas()
    loadScenarios()
  }, [])

  // Load workflow YAML when selection changes
  useEffect(() => {
    if (selectedWorkflowId) {
      loadWorkflowYaml(selectedWorkflowId)
    }
  }, [selectedWorkflowId])

  const loadWorkflows = async () => {
    try {
      const response = await fetch(`${API_BASE}/workflows`)
      const data = await response.json()
      setWorkflows(data.workflows || [])
      if (data.workflows?.length > 0 && !selectedWorkflowId) {
        setSelectedWorkflowId(data.workflows[0].id)
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to load workflows',
        variant: 'destructive',
      })
    }
  }

  const loadPersonas = async () => {
    try {
      const response = await fetch(`${API_BASE}/personas`)
      const data = await response.json()
      const personaList = data.personas?.map((p: any) => ({
        id: p.id,
        name: p.name,
        business: p.business
      })) || []
      setPersonas(personaList)
      if (personaList.length > 0 && !selectedPersona) {
        setSelectedPersona(personaList[0].id)
      }
    } catch (error) {
      console.error('Failed to load personas:', error)
    }
  }

  const loadScenarios = async () => {
    // For now, use mock scenarios
    const mockScenarios = [
      { id: 'growth_stall', name: 'Growth Stall', description: 'Business growth has plateaued' },
      { id: 'crisis', name: 'Crisis Mode', description: 'Urgent issues need attention' },
      { id: 'steady', name: 'Steady Operations', description: 'Normal business operations' },
    ]
    setScenarios(mockScenarios)
    setSelectedScenario('steady')
  }

  const loadWorkflowYaml = async (workflowId: string) => {
    try {
      setLoading(true)
      const response = await fetch(`${API_BASE}/workflows/${workflowId}/raw`)
      const data = await response.json()
      const parsed = parseWorkflow(data.content)
      setWorkflow(parsed)
      
      // Reset conversation when workflow changes
      setConversationStarted(false)
      setMessages([])
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to load workflow',
        variant: 'destructive',
      })
    } finally {
      setLoading(false)
    }
  }

  const startConversation = async () => {
    if (!workflow) return
    
    setConversationStarted(true)
    
    // If agent-initiated, simulate getting the initial message
    if (isAgentInitiated(workflow)) {
      const initialMessage = workflow.behavior?.initial_action
      if (initialMessage?.type === 'static_message' && initialMessage.content) {
        addMessage('agent', initialMessage.content)
      } else {
        // Simulate process_message
        addMessage('agent', 'Good morning! Let me check your current metrics...')
      }
    }
  }

  const sendMessage = async (content: string) => {
    if (!content.trim()) return
    
    // Add user message
    addMessage('user', content)
    setInputMessage('')
    
    // Simulate agent response
    setSendingMessage(true)
    setTimeout(() => {
      addMessage('agent', `I understand you're asking about "${content}". Let me help you with that...`)
      setSendingMessage(false)
    }, 1000)
  }

  const addMessage = (role: 'agent' | 'user', content: string) => {
    const newMessage: Message = {
      id: Date.now().toString(),
      role,
      content,
      timestamp: new Date().toISOString(),
    }
    setMessages(prev => [...prev, newMessage])
  }

  const handleInputKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage(inputMessage)
    }
  }

  // If conversation hasn't started, show starter view
  if (!conversationStarted && workflow) {
    if (isAgentInitiated(workflow)) {
      return (
        <div className="h-full">
          <AgentInitiatedView 
            workflow={workflow}
            preview={getInitialMessage(workflow)}
            onStart={startConversation}
            disabled={loading}
          />
        </div>
      )
    } else {
      return (
        <div className="h-full">
          <MerchantInitiatedView
            workflow={workflow}
            onSendMessage={(message) => {
              sendMessage(message)
              setConversationStarted(true)
            }}
            disabled={loading}
          />
        </div>
      )
    }
  }

  // Regular conversation view
  return (
    <div className="flex h-full flex-col">
      {/* Workflow Selector Bar */}
      <div className="border-b p-4">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">Workflow:</span>
          <Select value={selectedWorkflowId} onValueChange={setSelectedWorkflowId}>
            <SelectTrigger className="w-[300px]">
              <SelectValue placeholder="Select a workflow" />
            </SelectTrigger>
            <SelectContent>
              {workflows.map(workflow => (
                <SelectItem key={workflow.id} value={workflow.id}>
                  {workflow.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button size="sm" variant="outline">
            <Pencil className="mr-2 h-3 w-3" />
            Edit
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setWorkflowExpanded(!workflowExpanded)}
          >
            <ChevronDown className={`h-4 w-4 transition-transform ${workflowExpanded ? 'rotate-180' : ''}`} />
            Workflow Details
          </Button>
        </div>
        
        {/* Expandable Workflow Details */}
        {workflowExpanded && workflow && (
          <div className="mt-4 rounded-lg border bg-muted/50 p-4">
            <div className="space-y-2">
              <p className="text-sm"><strong>Name:</strong> {workflow.name}</p>
              <p className="text-sm"><strong>Description:</strong> {workflow.description}</p>
              {workflow.behavior?.initial_action && (
                <p className="text-sm">
                  <strong>Initial Action:</strong> {workflow.behavior.initial_action.type}
                </p>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Main Content Area */}
      <div className="flex flex-1 overflow-hidden">
        {/* Conversation View */}
        <div className="flex flex-1 flex-col">
          <ScrollArea className="flex-1 p-6">
            <div className="max-w-4xl mx-auto space-y-4">
              {messages.map((message) => (
                <div key={message.id} className="space-y-2">
                  {message.role === 'agent' && (
                    <div className="flex flex-col items-start">
                      <div className="text-sm font-medium text-muted-foreground mb-1">CJ</div>
                      <Card className="max-w-[70%] p-4">
                        <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                      </Card>
                      <div className="flex gap-2 mt-2">
                        <Button size="sm" variant="ghost">
                          <MessageSquare className="mr-1 h-3 w-3" />
                          💭 Prompt
                        </Button>
                        <Button size="sm" variant="ghost">
                          <Workflow className="mr-1 h-3 w-3" />
                          🔄 Workflow
                        </Button>
                      </div>
                    </div>
                  )}
                  {message.role === 'user' && (
                    <div className="flex flex-col items-end">
                      <div className="text-sm font-medium text-muted-foreground mb-1">YOU</div>
                      <Card className="max-w-[70%] bg-primary text-primary-foreground p-4">
                        <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                      </Card>
                    </div>
                  )}
                </div>
              ))}
              {sendingMessage && (
                <div className="flex items-center gap-2 text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span className="text-sm">CJ is typing...</span>
                </div>
              )}
            </div>
          </ScrollArea>
          
          {/* Message Input */}
          <div className="border-t p-4">
            <div className="flex gap-2">
              <Input
                placeholder="Type your message..."
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={handleInputKeyPress}
                disabled={sendingMessage}
                className="flex-1"
              />
              <Button
                onClick={() => sendMessage(inputMessage)}
                disabled={!inputMessage.trim() || sendingMessage}
                size="icon"
              >
                <Send className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Controls */}
      <div className="flex border-t">
        {/* Left Side - Persona */}
        <div className="flex-1 border-r p-4">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">Persona:</span>
            <Select value={selectedPersona} onValueChange={setSelectedPersona}>
              <SelectTrigger className="flex-1">
                <SelectValue placeholder="Select persona" />
              </SelectTrigger>
              <SelectContent>
                {personas.map(persona => (
                  <SelectItem key={persona.id} value={persona.id}>
                    {persona.name} - {persona.business}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        
        {/* Right Side - Scenario */}
        <div className="flex-1 p-4">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">Scenario:</span>
            <Select value={selectedScenario} onValueChange={setSelectedScenario}>
              <SelectTrigger className="flex-1">
                <SelectValue placeholder="Select scenario" />
              </SelectTrigger>
              <SelectContent>
                {scenarios.map(scenario => (
                  <SelectItem key={scenario.id} value={scenario.id}>
                    {scenario.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>
    </div>
  )
}