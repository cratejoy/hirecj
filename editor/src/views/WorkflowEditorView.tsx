import React from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Save, X, Plus, ArrowRight, Move } from 'lucide-react'
import { mockWorkflows } from '@/lib/mockData'

export function WorkflowEditorView() {
  const [selectedWorkflow] = React.useState(mockWorkflows[0])
  const [selectedStep, setSelectedStep] = React.useState('2')
  const [stepData, setStepData] = React.useState({
    name: 'Gather Information',
    description: 'Collect necessary details about the customer\'s issue or request',
    actions: [
      { id: '1', text: 'Ask clarifying questions', checked: true },
      { id: '2', text: 'Check order history', checked: true },
      { id: '3', text: 'Verify customer identity', checked: false }
    ],
    nextStep: 'Step 3 - Provide Solution',
    failStep: 'Step 1 - Identify Need'
  })

  const handleActionToggle = (actionId: string) => {
    setStepData(prev => ({
      ...prev,
      actions: prev.actions.map(action =>
        action.id === actionId ? { ...action, checked: !action.checked } : action
      )
    }))
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b p-4">
        <h1 className="text-xl font-semibold">
          Workflow: {selectedWorkflow.name} {selectedWorkflow.version}
        </h1>
        <div className="flex gap-2">
          <Button>
            <Save className="mr-2 h-4 w-4" />
            Save
          </Button>
          <Button variant="outline">
            <X className="mr-2 h-4 w-4" />
            Cancel
          </Button>
        </div>
      </div>

      {/* Workflow Steps */}
      <div className="border-b p-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold">WORKFLOW STEPS</h2>
          <div className="flex gap-2">
            <Button size="sm" variant="outline">
              <Plus className="mr-2 h-3 w-3" />
              Add Step
            </Button>
            <Button size="sm" variant="outline">
              <Move className="mr-2 h-3 w-3" />
              Reorder
            </Button>
          </div>
        </div>
        
        {/* Visual Workflow */}
        <Card className="p-6">
          <div className="overflow-x-auto">
            <div className="flex items-center gap-4 min-w-max">
              {/* Start */}
              <div className="flex flex-col items-center">
                <div className="rounded-lg border-2 border-dashed border-cratejoy-green p-4 text-center bg-cratejoy-green/10">
                  <div className="font-semibold text-cratejoy-green">START</div>
                  <div className="text-sm text-muted-foreground">Greeting</div>
                </div>
              </div>
              
              <ArrowRight className="h-6 w-6 text-muted-foreground" />
              
              {/* Steps */}
              {selectedWorkflow.steps.map((step, index) => (
                <React.Fragment key={step.id}>
                  <div className="flex flex-col items-center">
                    <Button
                      variant={selectedStep === step.id ? 'default' : 'outline'}
                      className="h-auto flex-col p-4"
                      onClick={() => setSelectedStep(step.id)}
                    >
                      <div className="font-semibold">STEP {step.id}</div>
                      <div className="text-sm">{step.name}</div>
                    </Button>
                  </div>
                  {index < selectedWorkflow.steps.length - 1 && (
                    <ArrowRight className="h-6 w-6 text-muted-foreground" />
                  )}
                </React.Fragment>
              ))}
              
              {/* Decision Node */}
              <div className="flex flex-col items-center">
                <div className="relative">
                  <ArrowRight className="h-6 w-6 text-muted-foreground mb-2" />
                  <div className="rounded-lg border-2 border-cratejoy-purple bg-cratejoy-purple/10 p-4 text-center">
                    <div className="font-semibold text-cratejoy-purple">DECISION</div>
                    <div className="text-sm">Resolved?</div>
                  </div>
                  <div className="absolute -bottom-10 left-1/2 -translate-x-1/2">
                    <div className="text-sm text-muted-foreground">↓</div>
                  </div>
                </div>
              </div>
              
              <ArrowRight className="h-6 w-6 text-muted-foreground" />
              
              {/* End */}
              <div className="flex flex-col items-center">
                <div className="rounded-lg border-2 border-dashed border-cratejoy-red p-4 text-center bg-cratejoy-red/10">
                  <div className="font-semibold text-cratejoy-red">END</div>
                  <div className="text-sm text-muted-foreground">Complete</div>
                </div>
              </div>
            </div>
            
            {/* Loop back arrow */}
            <div className="mt-8 flex items-center gap-4">
              <div className="rounded-lg border p-4 ml-[400px]">
                <div className="font-semibold">STEP 4</div>
                <div className="text-sm">Follow-up</div>
              </div>
              <div className="text-sm text-muted-foreground">← (loops back to Decision)</div>
            </div>
          </div>
        </Card>
      </div>

      {/* Selected Step Configuration */}
      <div className="flex-1 overflow-auto p-6">
        <div className="mx-auto max-w-4xl">
          <Card>
            <CardHeader>
              <CardTitle>SELECTED STEP: Step {selectedStep} - Gather Info</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="stepName">Step Name</Label>
                <Input
                  id="stepName"
                  value={stepData.name}
                  onChange={(e) => setStepData(prev => ({ ...prev, name: e.target.value }))}
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  value={stepData.description}
                  onChange={(e) => setStepData(prev => ({ ...prev, description: e.target.value }))}
                  className="min-h-[80px]"
                />
              </div>
              
              <div className="space-y-2">
                <Label>Actions</Label>
                <div className="space-y-2">
                  {stepData.actions.map(action => (
                    <div key={action.id} className="flex items-center space-x-2">
                      <Checkbox
                        id={action.id}
                        checked={action.checked}
                        onCheckedChange={() => handleActionToggle(action.id)}
                      />
                      <Label
                        htmlFor={action.id}
                        className="text-sm font-normal cursor-pointer"
                      >
                        {action.text}
                      </Label>
                    </div>
                  ))}
                </div>
              </div>
              
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="nextStep">Next Steps</Label>
                  <Select value={stepData.nextStep} onValueChange={(value) => setStepData(prev => ({ ...prev, nextStep: value }))}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {selectedWorkflow.steps.map(step => (
                        <SelectItem key={step.id} value={`Step ${step.id} - ${step.name}`}>
                          Step {step.id} - {step.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="failStep">If Failed</Label>
                  <Select value={stepData.failStep} onValueChange={(value) => setStepData(prev => ({ ...prev, failStep: value }))}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {selectedWorkflow.steps.map(step => (
                        <SelectItem key={step.id} value={`Step ${step.id} - ${step.name}`}>
                          Step {step.id} - {step.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}