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
import { MessageDetailsView } from '@/components/playground/MessageDetailsView'
import { usePlaygroundChat } from '@/hooks/usePlaygroundChat'
import { useSearch } from 'wouter'
import { useConversationCapture } from '@/hooks/useConversationCapture'
import { Download } from 'lucide-react'

const API_BASE = '/api/v1'

interface Message {
  id: string;
  messageId?: string;  // The backend message_id for debug lookups
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
  // Get URL search params
  const searchString = useSearch()
  const searchParams = new URLSearchParams(searchString)
  const urlWorkflow = searchParams.get('workflow')
  
  // WebSocket hook
  const {
    messages: wsMessages,
    isConnected,
    conversationStarted,
    thinking,
    startConversation: wsStartConversation,
    sendMessage: wsSendMessage,
    resetConversation,
    requestMessageDetails
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
  const [showMessageDetails, setShowMessageDetails] = useState(false)
  const [selectedMessageId, setSelectedMessageId] = useState<string | undefined>()
  
  // Prompt state for conversation capture
  const [cjPrompt, setCjPrompt] = useState<string>('')
  const [cjPromptVersion, setCjPromptVersion] = useState<string>('')
  const [cjPromptFile, setCjPromptFile] = useState<string>('')
  const [workflowPrompt, setWorkflowPrompt] = useState<string>('')
  const [workflowPromptFile, setWorkflowPromptFile] = useState<string>('')
  const [toolDefinitions, setToolDefinitions] = useState<any[]>([])
  
  const { toast } = useToast()

  // Load initial data
  useEffect(() => {
    loadWorkflows()
    loadPersonas()
    loadScenarios()
    loadCjPrompt()
  }, [])

  // Track previous workflow to detect changes
  const prevWorkflowRef = useRef<string | null>(null)
  
  // Load workflow YAML when selection changes
  useEffect(() => {
    if (selectedWorkflowId) {
      // If conversation is active and workflow actually changed, reset it
      // Only reset if we had a previous workflow AND it's different from current
      if (conversationStarted && prevWorkflowRef.current !== null && prevWorkflowRef.current !== selectedWorkflowId) {
        resetConversation('workflow_change', selectedWorkflowId)
        setLocalUserMessages({})
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
        // Check if URL has a workflow parameter
        if (urlWorkflow) {
          // Try to find the workflow from URL param
          const urlWorkflowItem = data.workflows.find((w: any) => 
            w.id === urlWorkflow || 
            w.name?.toLowerCase() === urlWorkflow.toLowerCase()
          )
          if (urlWorkflowItem) {
            console.log('🎯 Selected workflow from URL:', urlWorkflowItem.id, urlWorkflowItem.name)
            setSelectedWorkflowId(urlWorkflowItem.id)
            return
          } else {
            console.warn('⚠️ Could not find workflow from URL:', urlWorkflow)
          }
        }
        
        // Otherwise set ad_hoc_support as default if it exists, otherwise use first workflow
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
  
  const loadCjPrompt = async () => {
    try {
      // First get the list of versions to find the latest
      const versionsResponse = await fetch(`${API_BASE}/prompts`)
      const versionsData = await versionsResponse.json()
      
      if (versionsData.versions && versionsData.versions.length > 0) {
        const latestVersion = versionsData.versions[0] // Already sorted by version
        setCjPromptVersion(latestVersion)
        
        // Set the CJ prompt file path
        const promptFile = `prompts/cj/versions/${latestVersion}.yaml`
        setCjPromptFile(promptFile)
        
        // Now fetch the actual prompt content
        const promptResponse = await fetch(`${API_BASE}/prompts/${latestVersion}`)
        const promptData = await promptResponse.json()
        setCjPrompt(promptData.prompt || '')
        
        console.log(`Loaded CJ prompt version ${latestVersion} from ${promptFile} (${promptData.prompt?.length || 0} chars)`)
      }
    } catch (error) {
      console.error('Failed to load CJ prompt:', error)
      // Don't show error toast, just use empty prompt for capture
      setCjPrompt('')
      setCjPromptVersion('')
      setCjPromptFile('')
    }
  }

  const loadWorkflowYaml = async (workflowId: string) => {
    try {
      setLoading(true)
      const response = await fetch(`${API_BASE}/workflows/${workflowId}/raw`)
      const data = await response.json()
      const parsed = parseWorkflow(data.content)
      setWorkflow(parsed)
      
      // Set the workflow file path
      const workflowFile = `prompts/workflows/${workflowId}.yaml`
      setWorkflowPromptFile(workflowFile)
      
      // Extract workflow prompt from the parsed workflow
      if (parsed.workflow) {
        setWorkflowPrompt(parsed.workflow)
      } else {
        setWorkflowPrompt(parsed.description || '')
      }
      
      // Extract tool definitions if available
      if (parsed.available_tools) {
        // Convert tool names to tool definitions (in a real implementation, 
        // we'd fetch full tool definitions from the API)
        const toolDefs = parsed.available_tools.map((toolName: string) => ({
          name: toolName,
          description: `Tool: ${toolName}`,
          parameters: {}
        }))
        setToolDefinitions(toolDefs)
      } else {
        setToolDefinitions([])
      }
      
      console.log(`Loaded workflow ${workflowId} from ${workflowFile}`)
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
    console.log('🚀 PlaygroundView.startConversation', {
      timestamp: new Date().toISOString(),
      workflow: workflow?.name,
      workflowId: selectedWorkflowId,
      personaId: selectedPersona,
      scenarioId: selectedScenario,
      trustLevel
    })
    
    if (!workflow || !selectedPersona || !selectedScenario) {
      console.warn('❌ Early return - missing required data', {
        hasWorkflow: !!workflow,
        hasPersona: !!selectedPersona,
        hasScenario: !!selectedScenario
      })
      return
    }
    
    try {
      const config = {
        workflow: selectedWorkflowId,
        personaId: selectedPersona,
        scenarioId: selectedScenario,
        trustLevel: trustLevel
      }
      console.log('📤 Starting conversation', {
        config,
        isAgentInitiated: workflow && isAgentInitiated(workflow)
      })
      
      // For agent-initiated workflows, add the initial prompt message to local messages
      if (workflow && isAgentInitiated(workflow)) {
        const initialAction = workflow.behavior?.initial_action
        if (initialAction?.type === 'process_message' && initialAction.message) {
          // Add the prompt message that CJ is responding to
          setLocalUserMessages({
            0: initialAction.message
          })
        } else if (initialAction?.type === 'static_message' && initialAction.content) {
          // For static messages, we might want to show what triggered it
          setLocalUserMessages({
            0: "Start daily briefing"
          })
        }
      }
      
      await wsStartConversation(config)
      console.log('✅ wsStartConversation completed successfully')
    } catch (error) {
      console.error('❌ Failed to start conversation:', error)
      toast({
        title: 'Error',
        description: 'Failed to start conversation',
        variant: 'destructive',
      })
    }
  }

  const sendMessage = (content: string) => {
    console.log('📨 PlaygroundView.sendMessage', { content })
    
    if (!content.trim()) {
      console.warn('❌ Empty content, returning')
      return
    }
    
    // Start message capture if available
    if (canCapture) {
      console.log('🎯 Starting message capture for turn', wsMessages.length + 1)
      conversationCapture.startMessage(content)
      setIsCapturingMessage(true)
      capturingMessageIndex.current = wsMessages.length
    }
    
    // Track user message locally (since hook only gives us agent messages)
    console.log('📝 Tracking user message', { index: wsMessages.length })
    setLocalUserMessages(prev => ({
      ...prev,
      [wsMessages.length]: content
    }))
    
    // Send message via WebSocket
    wsSendMessage(content)
    setInputMessage('')
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
    
    // For agent-initiated workflows, add the initial user message when we get the first ws message
    if (workflow && isAgentInitiated(workflow) && wsMessages.length > 0 && localUserMessages[0] && !wsMessages[0].data.content.includes('thinking')) {
      combined.push({
        id: 'user-0',
        role: 'user',
        content: localUserMessages[0],
        timestamp: new Date(wsMessages[0].data.timestamp).toISOString()
      })
    }
    
    wsMessages.forEach((msg, index) => {
      // Skip user message for index 0 if agent-initiated (already added above)
      if (localUserMessages[index] && !(workflow && isAgentInitiated(workflow) && index === 0)) {
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
        messageId: msg.data.message_id || undefined,  // Include message_id if available
        role: 'agent',
        content: msg.data.content,
        timestamp: msg.data.timestamp,
        isThinking: msg.data.content === 'CJ is thinking...'
      })
    })
    
    return combined
  }, [wsMessages, localUserMessages, workflow])

  // Get selected persona and scenario objects
  const selectedPersonaObj = personas.find(p => p.id === selectedPersona)
  const selectedScenarioObj = scenarios.find(s => s.id === selectedScenario)

  // Initialize conversation capture hook - always call the hook to follow React rules
  const conversationCapture = useConversationCapture(
    workflow && selectedPersonaObj && selectedScenarioObj ? {
      workflow,
      persona: {
        ...selectedPersonaObj,
        role: 'Founder', // Default role - could be extended
        industry: 'E-commerce', // Default industry - could be extended
        communicationStyle: ['direct', 'brief'], // Default style
        traits: ['data-driven'] // Default traits
      },
      scenario: selectedScenarioObj,
      trustLevel,
      cjPrompt,
      cjPromptVersion,
      cjPromptFile,
      workflowPrompt,
      workflowPromptFile,
      toolDefinitions
    } : {
      // Provide default props when data isn't ready
      workflow: { name: '', description: '' } as WorkflowConfig,
      persona: { id: '', name: '', business: '', role: '', industry: '', communicationStyle: [], traits: [] },
      scenario: { id: '', name: '', description: '' },
      trustLevel: 3,
      cjPrompt: '',
      cjPromptVersion: '',
      cjPromptFile: '',
      workflowPrompt: '',
      workflowPromptFile: '',
      toolDefinitions: []
    }
  )

  // Only use conversation capture when we have valid data
  const canCapture = workflow && selectedPersonaObj && selectedScenarioObj

  // Track conversation capture state
  const [isCapturingMessage, setIsCapturingMessage] = useState(false)
  const capturingMessageIndex = useRef<number>(-1)
  
  // Track previous message count to detect new messages
  const prevMessageCountRef = useRef(0)
  
  // Capture agent messages when they arrive
  useEffect(() => {
    if (!canCapture || !isCapturingMessage || wsMessages.length === 0) return
    
    // Check if we have a new message at the expected index
    const expectedIndex = capturingMessageIndex.current
    if (wsMessages.length > expectedIndex && expectedIndex >= 0) {
      const targetMessage = wsMessages[expectedIndex]
      
      console.log('🔍 Processing agent message for capture', {
        expectedIndex,
        messageContent: targetMessage.data.content.substring(0, 50) + '...',
        isThinking: targetMessage.data.content.includes('thinking...')
      })
      
      // Update thinking state if present
      if (thinking && thinking.data.status) {
        console.log('💭 Capturing thinking state:', thinking.data.status)
        conversationCapture.captureThinking(thinking.data.status)
      }
      
      // Check if this is the final response (not a thinking message)
      if (!targetMessage.data.content.includes('thinking...') && 
          targetMessage.data.content !== 'CJ is thinking...') {
        console.log('✅ Completing message capture with response')
        
        // Request message details if we have a message_id
        if (targetMessage.data.message_id) {
          console.log('📊 Requesting message details for:', targetMessage.data.message_id)
          requestMessageDetails(targetMessage.data.message_id)
            .then(debugData => {
              console.log('📊 Received message details:', {
                hasThinking: !!debugData?.response?.thinking_content,
                intermediateCount: debugData?.response?.choices?.length || 0,
                groundingCount: debugData?.grounding?.length || 0
              })
              conversationCapture.completeMessage(targetMessage.data.content, null, debugData)
            })
            .catch(err => {
              console.error('Failed to get message details:', err)
              // Complete without debug data if request fails
              conversationCapture.completeMessage(targetMessage.data.content)
            })
            .finally(() => {
              // Reset capture state
              setIsCapturingMessage(false)
              capturingMessageIndex.current = -1
            })
        } else {
          // No message_id, complete without debug data
          conversationCapture.completeMessage(targetMessage.data.content)
          // Reset capture state
          setIsCapturingMessage(false)
          capturingMessageIndex.current = -1
        }
      }
    }
  }, [wsMessages, thinking, conversationCapture, canCapture, isCapturingMessage, requestMessageDetails])
  
  // Handle agent-initiated workflows
  useEffect(() => {
    // For agent-initiated workflows, capture the first agent message
    if (workflow && isAgentInitiated(workflow) && canCapture && 
        wsMessages.length === 1 && !isCapturingMessage && 
        capturingMessageIndex.current === -1) {
      const firstMessage = wsMessages[0]
      if (!firstMessage.data.content.includes('thinking...')) {
        console.log('🤖 Capturing agent-initiated first message')
        // For agent-initiated, we need to create a synthetic user message
        const initialPrompt = localUserMessages[0] || 
          (workflow.behavior?.initial_action?.message) || 
          'Start workflow'
        
        conversationCapture.startMessage(initialPrompt)
        conversationCapture.completeMessage(firstMessage.data.content, {
          prompt: 0,
          completion: 0,
          thinking: 0
        })
      }
    }
  }, [workflow, canCapture, wsMessages, isCapturingMessage, conversationCapture, localUserMessages])
  
  // Handle export conversation
  const handleExportConversation = async () => {
    if (!canCapture) {
      toast({
        title: 'Error',
        description: 'No conversation to export',
        variant: 'destructive',
      })
      return
    }
    
    // If we're still capturing a message, complete it first
    if (isCapturingMessage) {
      console.log('⚠️ Still capturing a message, completing it before export')
      const currentIndex = capturingMessageIndex.current
      if (currentIndex >= 0 && wsMessages[currentIndex]) {
        const message = wsMessages[currentIndex]
        if (!message.data.content.includes('thinking...')) {
          conversationCapture.completeMessage(message.data.content, {
            prompt: 0,
            completion: 0,
            thinking: 0
          })
        }
      }
      setIsCapturingMessage(false)
      capturingMessageIndex.current = -1
    }
    
    try {
      console.log('📤 Exporting conversation...')
      const conversation = await conversationCapture.captureConversation('playground')
      console.log('📊 Exported conversation data:', {
        id: conversation.id,
        messageCount: conversation.messages.length,
        messages: conversation.messages.map(m => ({
          turn: m.turn,
          userInput: m.user_input.substring(0, 50) + '...',
          agentResponse: m.agent_processing.final_response.substring(0, 50) + '...'
        }))
      })
      // Get the full path from the current directory
      const fullPath = conversation.filePath 
        ? `/Users/aelaguiz/workspace/hirecj/${conversation.filePath}`
        : `hirecj_evals/conversations/playground/${new Date().toISOString().split('T')[0]}/${conversation.id}.json`
      
      // Create a clickable toast that copies the path
      toast({
        title: 'Conversation Exported',
        description: (
          <div 
            className="cursor-pointer hover:underline break-all"
            onClick={async () => {
              try {
                await navigator.clipboard.writeText(fullPath)
                toast({
                  title: 'Copied!',
                  description: 'Path copied to clipboard',
                })
              } catch (err) {
                console.error('Failed to copy:', err)
              }
            }}
          >
            {fullPath}
          </div>
        ),
      })
    } catch (error) {
      console.error('Failed to export conversation:', error)
      toast({
        title: 'Error',
        description: 'Failed to export conversation',
        variant: 'destructive',
      })
    }
  }

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
          console.log('💬 MerchantInitiatedView.onSendMessage', {
            message,
            conversationStarted
          })
          
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
          {conversationStarted && (
            <Button
              size="sm"
              variant="outline"
              onClick={handleExportConversation}
              title="Export conversation for evaluation"
            >
              <Download className="mr-2 h-3 w-3" />
              Export for Eval
            </Button>
          )}
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
                            <Button 
                              size="sm" 
                              variant="ghost" 
                              onClick={() => {
                                setSelectedMessageId(message.messageId)
                                setShowMessageDetails(true)
                              }}
                              disabled={!message.messageId}
                            >
                              📋 Details
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
      
      {/* Message Details View */}
      <MessageDetailsView 
        isOpen={showMessageDetails} 
        onClose={() => setShowMessageDetails(false)}
        messageId={selectedMessageId}
        onRequestDetails={requestMessageDetails}
      />
    </div>
  )
}