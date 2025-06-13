import React from 'react'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Card } from '@/components/ui/card'
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Pencil, MessageSquare, Workflow, ChevronDown } from 'lucide-react'
import { mockWorkflows, mockSystemPrompts, mockPersonas, mockConversation, mockScenarios } from '@/lib/mockData'

export function PlaygroundView() {
  const [selectedWorkflow, setSelectedWorkflow] = React.useState(mockWorkflows[0].id)
  const [selectedPrompt, setSelectedPrompt] = React.useState(mockSystemPrompts[0].id)
  const [selectedPersona, setSelectedPersona] = React.useState(mockPersonas[0].id)
  const [selectedScenario, setSelectedScenario] = React.useState(mockScenarios[3].id) // Default to steady operations
  const [workflowExpanded, setWorkflowExpanded] = React.useState(false)
  const [promptExpanded, setPromptExpanded] = React.useState(false)

  const currentWorkflow = mockWorkflows.find(w => w.id === selectedWorkflow)
  const currentPrompt = mockSystemPrompts.find(p => p.id === selectedPrompt)
  const currentPersona = mockPersonas.find(p => p.id === selectedPersona)
  const currentScenario = mockScenarios.find(s => s.id === selectedScenario)

  return (
    <div className="flex h-full flex-col">
      {/* Workflow Selector Bar */}
      <div className="border-b p-4">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">Workflow:</span>
          <Select value={selectedWorkflow} onValueChange={setSelectedWorkflow}>
            <SelectTrigger className="w-[300px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {mockWorkflows.map(workflow => (
                <SelectItem key={workflow.id} value={workflow.id}>
                  {workflow.version} - {workflow.name}
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
            Workflow Editor
          </Button>
        </div>
        
        {/* Expandable Workflow Editor */}
        {workflowExpanded && (
          <div className="mt-4 rounded-lg border bg-muted/50 p-4">
            <div className="flex gap-2">
              {currentWorkflow?.steps.map((step, index) => (
                <React.Fragment key={step.id}>
                  <div className="rounded bg-background px-3 py-2 text-sm">
                    {index + 1}. {step.name}
                  </div>
                  {index < currentWorkflow.steps.length - 1 && (
                    <span className="self-center">→</span>
                  )}
                </React.Fragment>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Main Content Area */}
      <div className="flex flex-1 overflow-hidden">
        {/* Agent Perspective (Left) */}
        <div className="flex flex-1 flex-col border-r">
          <div className="border-b bg-cratejoy-smoke p-4">
            <h2 className="font-semibold text-cratejoy-slate">AGENT PERSPECTIVE</h2>
          </div>
          <ScrollArea className="flex-1 p-4">
            <div className="space-y-4">
              {mockConversation.map((message) => (
                <div key={message.id} className="space-y-2">
                  {message.role === 'user' && (
                    <div className="text-sm font-medium text-muted-foreground">
                      {currentPersona?.name?.split(' ')[0]?.toUpperCase() || 'USER'}
                    </div>
                  )}
                  {message.role === 'agent' && (
                    <>
                      <div className="text-sm font-medium text-muted-foreground">CJ</div>
                      <Card className="p-4">
                        <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                      </Card>
                      <div className="flex gap-2">
                        <Button size="sm" variant="ghost" className="hover:bg-cratejoy-blue-green/20 hover:text-cratejoy-blue-green">
                          <MessageSquare className="mr-1 h-3 w-3" />
                          💭 Prompt
                        </Button>
                        <Button size="sm" variant="ghost" className="hover:bg-cratejoy-purple/20 hover:text-cratejoy-purple">
                          <Workflow className="mr-1 h-3 w-3" />
                          🔄 Workflow
                        </Button>
                      </div>
                    </>
                  )}
                </div>
              ))}
            </div>
          </ScrollArea>
          
          {/* System Prompt Selector */}
          <div className="border-t p-4">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">System Prompt:</span>
                <Select value={selectedPrompt} onValueChange={setSelectedPrompt}>
                  <SelectTrigger className="flex-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {mockSystemPrompts.map(prompt => (
                      <SelectItem key={prompt.id} value={prompt.id}>
                        {prompt.version} - {prompt.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button size="sm" variant="outline">
                  <Pencil className="mr-2 h-3 w-3" />
                  Edit
                </Button>
              </div>
              
              <Button
                size="sm"
                variant="ghost"
                className="w-full justify-start"
                onClick={() => setPromptExpanded(!promptExpanded)}
              >
                <ChevronDown className={`mr-2 h-4 w-4 transition-transform ${promptExpanded ? 'rotate-180' : ''}`} />
                System Prompt Editor
              </Button>
              
              {promptExpanded && (
                <Card className="p-3">
                  <p className="text-xs text-muted-foreground line-clamp-3">
                    {currentPrompt?.content}
                  </p>
                  <Button size="sm" variant="link" className="mt-2 h-auto p-0">
                    Click ✏ to expand
                  </Button>
                </Card>
              )}
            </div>
          </div>
        </div>

        {/* User Perspective (Right) */}
        <div className="flex flex-1 flex-col">
          <div className="border-b bg-cratejoy-smoke p-4">
            <h2 className="font-semibold text-cratejoy-slate">USER PERSPECTIVE</h2>
          </div>
          <ScrollArea className="flex-1 p-4">
            <div className="space-y-4">
              {mockConversation.map((message) => (
                <div key={message.id}>
                  {message.role === 'user' && (
                    <>
                      <div className="text-sm font-medium text-muted-foreground text-right">
                        {currentPersona?.name?.split(' ')[0]?.toUpperCase() || 'USER'}
                      </div>
                      <Card className="ml-auto max-w-[80%] bg-primary text-primary-foreground p-4 border-primary">
                        <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                      </Card>
                    </>
                  )}
                  {message.role === 'agent' && (
                    <>
                      <div className="text-sm font-medium text-muted-foreground">CJ</div>
                      <Card className="mr-auto max-w-[80%] p-4">
                        <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                      </Card>
                    </>
                  )}
                </div>
              ))}
            </div>
          </ScrollArea>
          
          {/* Merchant Persona Selector */}
          <div className="border-t p-4 space-y-3">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium">Merchant Persona:</span>
              <Select value={selectedPersona} onValueChange={setSelectedPersona}>
                <SelectTrigger className="flex-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {mockPersonas.map(persona => (
                    <SelectItem key={persona.id} value={persona.id}>
                      {persona.name} - {persona.business}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div className="rounded-lg border bg-muted/50 p-3 text-sm space-y-2">
              <div>
                <span className="font-medium">Business Context:</span>
                <div className="flex items-center gap-2">
                  <span>• Scenario:</span>
                  <Select value={selectedScenario} onValueChange={setSelectedScenario}>
                    <SelectTrigger className="h-7 w-[150px]">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {mockScenarios.map(scenario => (
                        <SelectItem key={scenario.id} value={scenario.id}>
                          {scenario.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>• Stress Level: {currentScenario?.stressLevel}</div>
                <div>• Emotional State: {currentScenario?.emotionalState}</div>
              </div>
              
              <div>
                <span className="font-medium">Communication Style:</span>
                <div>• {currentPersona?.communicationStyle.join(', ')}</div>
                <div>• {currentPersona?.traits.slice(0, 2).join(', ')}</div>
              </div>
              
              <div>
                <span className="font-medium">Business Details:</span>
                <div>• MRR: {currentPersona?.businessMetrics.mrr}</div>
                <div>• {currentPersona?.businessMetrics.monthlyActiveCustomers} active customers</div>
                <div>• {currentPersona?.businessMetrics.churnRate}% churn rate</div>
                <div>• {currentPersona?.businessMetrics.subscriptionRevenue} subscription</div>
              </div>
              
              {currentScenario?.keyMetrics && (
                <div>
                  <span className="font-medium">Current Situation:</span>
                  <div className="text-sm text-cratejoy-red">
                    {currentScenario.keyMetrics.issue}
                  </div>
                </div>
              )}
              
              <div className="flex gap-2 pt-2">
                <Button size="sm" variant="outline">
                  <Pencil className="mr-2 h-3 w-3" />
                  Edit Persona
                </Button>
                <Button size="sm" variant="outline">
                  📊 View Universe Data
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}