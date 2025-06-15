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
import { Save, X, Plus, Pencil, Trash2 } from 'lucide-react'
import { mockTools } from '@/lib/mockData'

const toolTypes = ['API Call', 'Database Query', 'File Operation', 'External Service']
const authTypes = ['Bearer Token', 'API Key', 'OAuth 2.0', 'Basic Auth', 'None']
const httpMethods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']
const paramTypes = ['string', 'integer', 'boolean', 'array', 'object']

export function ToolEditorView() {
  const [selectedTool] = React.useState(mockTools[0])
  const [formData, setFormData] = React.useState({
    name: selectedTool.name,
    type: selectedTool.type,
    description: selectedTool.description,
    endpoint: selectedTool.endpoint,
    method: selectedTool.method,
    authType: selectedTool.authType,
    parameters: selectedTool.parameters,
    headers: [
      { key: 'Content-Type', value: 'application/json' },
      { key: 'Authorization', value: 'Bearer {{api_key}}' }
    ],
    successResponse: '{ "available": true,\n  "quantity": 150,\n  "locations": ["NYC", "LA"] }',
    errorResponse: '{ "error": "Product not found" }'
  })

  const handleInputChange = (field: string, value: any) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }))
  }

  const handleParameterChange = (index: number, field: string, value: any) => {
    const newParams = [...formData.parameters]
    newParams[index] = { ...newParams[index], [field]: value }
    setFormData(prev => ({ ...prev, parameters: newParams }))
  }

  const addParameter = () => {
    setFormData(prev => ({
      ...prev,
      parameters: [...prev.parameters, { name: '', type: 'string', required: false, description: '' }]
    }))
  }

  const removeParameter = (index: number) => {
    setFormData(prev => ({
      ...prev,
      parameters: prev.parameters.filter((_, i) => i !== index)
    }))
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b p-4">
        <h1 className="text-xl font-semibold">
          Tool: {selectedTool.name}
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

      {/* Form Content */}
      <div className="flex-1 overflow-auto p-6">
        <div className="mx-auto max-w-4xl space-y-6">
          {/* Tool Configuration */}
          <Card>
            <CardHeader>
              <CardTitle>TOOL CONFIGURATION</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="name">Name</Label>
                  <Input
                    id="name"
                    value={formData.name}
                    onChange={(e) => handleInputChange('name', e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="type">Type</Label>
                  <Select value={formData.type} onValueChange={(value) => handleInputChange('type', value)}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {toolTypes.map(type => (
                        <SelectItem key={type} value={type}>
                          {type}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  value={formData.description}
                  onChange={(e) => handleInputChange('description', e.target.value)}
                  className="min-h-[60px]"
                />
              </div>
            </CardContent>
          </Card>

          {/* Parameters */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                PARAMETERS
                <Button size="sm" onClick={addParameter}>
                  <Plus className="mr-2 h-3 w-3" />
                  Add
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="grid grid-cols-12 gap-2 text-sm font-medium text-cratejoy-slate bg-cratejoy-smoke rounded px-2 py-1">
                  <div className="col-span-3">Parameter</div>
                  <div className="col-span-2">Type</div>
                  <div className="col-span-1">Required</div>
                  <div className="col-span-5">Description</div>
                  <div className="col-span-1"></div>
                </div>
                <div className="border-t border-cratejoy-smoke"></div>
                {formData.parameters.map((param, index) => (
                  <div key={index} className="grid grid-cols-12 gap-2 items-center py-2">
                    <div className="col-span-3">
                      <Input
                        value={param.name}
                        onChange={(e) => handleParameterChange(index, 'name', e.target.value)}
                        placeholder="parameter_name"
                      />
                    </div>
                    <div className="col-span-2">
                      <Select 
                        value={param.type} 
                        onValueChange={(value) => handleParameterChange(index, 'type', value)}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {paramTypes.map(type => (
                            <SelectItem key={type} value={type}>
                              {type}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="col-span-1 flex justify-center">
                      <Checkbox
                        checked={param.required}
                        onCheckedChange={(checked) => handleParameterChange(index, 'required', checked)}
                      />
                    </div>
                    <div className="col-span-5">
                      <Input
                        value={param.description}
                        onChange={(e) => handleParameterChange(index, 'description', e.target.value)}
                        placeholder="Description"
                      />
                    </div>
                    <div className="col-span-1 flex gap-1">
                      <Button size="icon" variant="ghost" className="h-8 w-8">
                        <Pencil className="h-3 w-3" />
                      </Button>
                      <Button 
                        size="icon" 
                        variant="ghost" 
                        className="h-8 w-8"
                        onClick={() => removeParameter(index)}
                      >
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* API Configuration */}
          <Card>
            <CardHeader>
              <CardTitle>API CONFIGURATION</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="endpoint">Endpoint</Label>
                <Input
                  id="endpoint"
                  value={formData.endpoint}
                  onChange={(e) => handleInputChange('endpoint', e.target.value)}
                  placeholder="https://api.example.com/v1/resource"
                />
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="method">Method</Label>
                  <Select value={formData.method} onValueChange={(value) => handleInputChange('method', value)}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {httpMethods.map(method => (
                        <SelectItem key={method} value={method}>
                          {method}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="auth">Authentication</Label>
                  <Select value={formData.authType} onValueChange={(value) => handleInputChange('authType', value)}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {authTypes.map(auth => (
                        <SelectItem key={auth} value={auth}>
                          {auth}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="space-y-2">
                <Label>Headers</Label>
                <div className="space-y-2">
                  {formData.headers.map((header, index) => (
                    <Input
                      key={index}
                      value={`${header.key}: ${header.value}`}
                      className="font-mono text-sm"
                      readOnly
                    />
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Response Handling */}
          <Card>
            <CardHeader>
              <CardTitle>RESPONSE HANDLING</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="success">Success Response</Label>
                <Textarea
                  id="success"
                  value={formData.successResponse}
                  onChange={(e) => handleInputChange('successResponse', e.target.value)}
                  className="min-h-[120px] font-mono text-sm"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="error">Error Response</Label>
                <Textarea
                  id="error"
                  value={formData.errorResponse}
                  onChange={(e) => handleInputChange('errorResponse', e.target.value)}
                  className="min-h-[120px] font-mono text-sm"
                />
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}