import React, { useState, useEffect, useRef } from 'react'
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
import { ConfigurationBar } from '@/components/playground/ConfigurationBar'
import { usePlaygroundChat } from '@/hooks/usePlaygroundChat'

const API_BASE = '/api/v1'

interface Message {
  id: string;
  role: 'agent' | 'user';
  content: string;
  timestamp: string;
  isThinking?: boolean;
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
  // WebSocket hook
  const {
    messages: wsMessages,
    thinking,
    isConnected,
    conversationStarted,
    startConversation: wsStartConversation,
    sendMessage: wsSendMessage,
    resetConversation
  } = usePlaygroundChat()

  // State for configuration
  const [workflows, setWorkflows] = useState<WorkflowListItem[]>([])
  const [selectedWorkflowId, setSelectedWorkflowId] = useState<string>('')
  const [workflow, setWorkflow] = useState<WorkflowConfig | null>(null)
  const [personas, setPersonas] = useState<Persona[]>([])
  const [selectedPersona, setSelectedPersona] = useState<string>('')
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [selectedScenario, setSelectedScenario] = useState<string>('')
  
  // State for user messages tracking (since hook only returns agent messages)
  const [localUserMessages, setLocalUserMessages] = useState<{[key: number]: string}>({})
  const [inputMessage, setInputMessage] = useState('')
  const [loading, setLoading] = useState(false)
  
  // UI state
  const [workflowExpanded, setWorkflowExpanded] = useState(false)
  const [trustLevel, setTrustLevel] = useState(3)
  
  const { toast } = useToast()

  // Load initial data
  useEffect(() => {
    loadWorkflows()
    loadPersonas()
    loadScenarios()
  }, [])

  // Track previous workflow to detect changes
  const prevWorkflowRef = useRef<string>('')
  
  // Load workflow YAML when selection changes
  useEffect(() => {
    if (selectedWorkflowId) {
      // If conversation is active and workflow actually changed, reset it
      if (conversationStarted && prevWorkflowRef.current && prevWorkflowRef.current !== selectedWorkflowId) {
        resetConversation('workflow_change', selectedWorkflowId)
      }
      prevWorkflowRef.current = selectedWorkflowId
      loadWorkflowYaml(selectedWorkflowId)
    }
  }, [selectedWorkflowId, conversationStarted, resetConversation])

  const loadWorkflows = async () => {
    try {
      const response = await fetch(`${API_BASE}/workflows`)
      const data = await response.json()
      setWorkflows(data.workflows || [])
      if (data.workflows?.length > 0 && !selectedWorkflowId) {
        // Set ad_hoc_support as default if it exists, otherwise use first workflow
        const adHocWorkflow = data.workflows.find((w: any) => w.id === 'ad_hoc_support')
        setSelectedWorkflowId(adHocWorkflow ? 'ad_hoc_support' : data.workflows[0].id)
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
    console.group('🚀 PlaygroundView.startConversation')
    console.log('Called at:', new Date().toISOString())
    console.log('workflow:', workflow)
    console.log('selectedWorkflowId:', selectedWorkflowId)
    console.log('selectedPersona:', selectedPersona)
    console.log('selectedScenario:', selectedScenario)
    console.log('trustLevel:', trustLevel)
    
    if (!workflow || !selectedPersona || !selectedScenario) {
      console.warn('❌ Early return - missing required data:', {
        hasWorkflow: !!workflow,
        hasPersona: !!selectedPersona,
        hasScenario: !!selectedScenario
      })
      console.groupEnd()
      return
    }
    
    try {
      const config = {
        workflow: selectedWorkflowId,
        personaId: selectedPersona,
        scenarioId: selectedScenario,
        trustLevel: trustLevel
      }
      console.log('📤 Calling wsStartConversation with config:', config)
      await wsStartConversation(config)
      console.log('✅ wsStartConversation completed successfully')
    } catch (error) {
      console.error('❌ Failed to start conversation:', error)
      toast({
        title: 'Error',
        description: 'Failed to start conversation',
        variant: 'destructive',
      })
    } finally {
      console.groupEnd()
    }
  }

  const sendMessage = (content: string) => {
    console.group('📨 PlaygroundView.sendMessage')
    console.log('Content:', content)
    
    if (!content.trim()) {
      console.warn('❌ Empty content, returning')
      console.groupEnd()
      return
    }
    
    // Track user message locally (since hook only gives us agent messages)
    console.log('📝 Tracking user message locally at index:', wsMessages.length)
    setLocalUserMessages(prev => ({
      ...prev,
      [wsMessages.length]: content
    }))
    
    // Send message via WebSocket
    console.log('🔌 Sending message via WebSocket')
    wsSendMessage(content)
    setInputMessage('')
    console.groupEnd()
  }

  const handleInputKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage(inputMessage)
    }
  }

  // Combine agent messages from WebSocket with local user messages
  const messages: Message[] = React.useMemo(() => {
    const combined: Message[] = []
    
    wsMessages.forEach((msg, index) => {
      // Add user message if exists before this agent message
      if (localUserMessages[index]) {
        combined.push({
          id: `user-${index}`,
          role: 'user',
          content: localUserMessages[index],
          timestamp: new Date(msg.data.timestamp).toISOString()
        })
      }
      
      // Add agent message
      combined.push({
        id: `agent-${index}`,
        role: 'agent',
        content: msg.data.content,
        timestamp: msg.data.timestamp,
        isThinking: msg.data.content === 'CJ is thinking...'
      })
    })
    
    return combined
  }, [wsMessages, localUserMessages])

  // Get selected persona and scenario objects
  const selectedPersonaObj = personas.find(p => p.id === selectedPersona)
  const selectedScenarioObj = scenarios.find(s => s.id === selectedScenario)

  // Show connecting status if not connected
  if (!isConnected) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4" />
          <p className="text-muted-foreground">Connecting to playground service...</p>
        </div>
      </div>
    )
  }

  // If conversation hasn't started, show starter view
  if (!conversationStarted && workflow) {
    const starterView = isAgentInitiated(workflow) ? (
      <AgentInitiatedView 
        workflow={workflow}
        preview={getInitialMessage(workflow)}
        persona={selectedPersonaObj}
        scenario={selectedScenarioObj}
        trustLevel={trustLevel}
        onStart={startConversation}
        disabled={loading}
      />
    ) : (
      <MerchantInitiatedView
        workflow={workflow}
        persona={selectedPersonaObj}
        scenario={selectedScenarioObj}
        trustLevel={trustLevel}
        onSendMessage={async (message) => {
          console.group('💬 MerchantInitiatedView.onSendMessage')
          console.log('Message:', message)
          console.log('conversationStarted:', conversationStarted)
          
          // For merchant-initiated, we need to start the conversation first
          if (!conversationStarted) {
            console.log('📝 Conversation not started, starting it first...')
            try {
              await startConversation()
              console.log('✅ Conversation started, now sending message')
              // Now the conversation is started, send the message
              sendMessage(message)
            } catch (error) {
              console.error('❌ Failed to start conversation before sending message:', error)
              toast({
                title: 'Error',
                description: 'Failed to start conversation',
                variant: 'destructive',
              })
            }
          } else {
            console.log('✅ Conversation already started, sending message directly')
            sendMessage(message)
          }
          console.groupEnd()
        }}
        disabled={loading}
      />
    )

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
          </div>
        </div>
        
        <div className="flex-1">
          {starterView}
        </div>
        
        <ConfigurationBar
          personas={personas}
          selectedPersona={selectedPersona}
          onPersonaChange={setSelectedPersona}
          scenarios={scenarios}
          selectedScenario={selectedScenario}
          onScenarioChange={setSelectedScenario}
          trustLevel={trustLevel}
          onTrustLevelChange={setTrustLevel}
        />
      </div>
    )
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
                      {message.isThinking ? (
                        <div className="flex items-center gap-2 text-muted-foreground">
                          <Loader2 className="h-4 w-4 animate-spin" />
                          <span className="text-sm italic">{message.content}</span>
                        </div>
                      ) : (
                        <>
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
                        </>
                      )}
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
                disabled={!conversationStarted}
                className="flex-1"
              />
              <Button
                onClick={() => sendMessage(inputMessage)}
                disabled={!inputMessage.trim() || !conversationStarted}
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