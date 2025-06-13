import React from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Checkbox } from '@/components/ui/checkbox'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Save, X } from 'lucide-react'
import { mockPersonas } from '@/lib/mockData'

const industries = [
  'Beauty & Personal Care',
  'Electronics & Tech',
  'Fashion & Apparel',
  'Home & Garden',
  'Food & Beverage',
  'Health & Wellness',
  'Sports & Outdoors',
  'Toys & Games'
]

const communicationStyles = [
  'Collaborative',
  'Direct',
  'Detail-oriented',
  'Brief'
]

export function UserPersonasView() {
  const [selectedPersona] = React.useState(mockPersonas[0])
  const [formData, setFormData] = React.useState({
    name: selectedPersona.name,
    business: selectedPersona.business,
    role: selectedPersona.role,
    industry: selectedPersona.industry,
    communicationStyle: selectedPersona.communicationStyle,
    traits: selectedPersona.traits.join(', '),
    annualRevenue: selectedPersona.businessMetrics.annualRevenue,
    growthRate: selectedPersona.businessMetrics.growthRate,
    teamSize: selectedPersona.businessMetrics.teamSize.toString(),
    yearsInBusiness: selectedPersona.businessMetrics.yearsInBusiness.toString(),
    subscriptionRevenue: selectedPersona.businessMetrics.subscriptionRevenue,
    customerLTV: selectedPersona.businessMetrics.customerLTV,
    monthlyActiveCustomers: selectedPersona.businessMetrics.monthlyActiveCustomers
  })

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }))
  }

  const handleStyleToggle = (style: string) => {
    setFormData(prev => ({
      ...prev,
      communicationStyle: prev.communicationStyle.includes(style)
        ? prev.communicationStyle.filter(s => s !== style)
        : [...prev.communicationStyle, style]
    }))
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b p-4">
        <h1 className="text-xl font-semibold">
          Current Persona: {selectedPersona.name} - {selectedPersona.business}
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
          {/* Basic Information */}
          <Card>
            <CardHeader>
              <CardTitle>BASIC INFORMATION</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="name">Name</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => handleInputChange('name', e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="business">Business</Label>
                <Input
                  id="business"
                  value={formData.business}
                  onChange={(e) => handleInputChange('business', e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="role">Role</Label>
                <Input
                  id="role"
                  value={formData.role}
                  onChange={(e) => handleInputChange('role', e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="industry">Industry</Label>
                <Select value={formData.industry} onValueChange={(value) => handleInputChange('industry', value)}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {industries.map(industry => (
                      <SelectItem key={industry} value={industry}>
                        {industry}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>

          {/* Personality & Communication */}
          <Card>
            <CardHeader>
              <CardTitle>PERSONALITY & COMMUNICATION</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Communication Style</Label>
                <div className="flex flex-wrap gap-4">
                  {communicationStyles.map(style => (
                    <div key={style} className="flex items-center space-x-2">
                      <Checkbox
                        id={style}
                        checked={formData.communicationStyle.includes(style)}
                        onCheckedChange={() => handleStyleToggle(style)}
                      />
                      <Label
                        htmlFor={style}
                        className="text-sm font-normal cursor-pointer"
                      >
                        {style}
                      </Label>
                    </div>
                  ))}
                </div>
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="traits">Key Traits (comma-separated)</Label>
                <Input
                  id="traits"
                  value={formData.traits}
                  onChange={(e) => handleInputChange('traits', e.target.value)}
                  placeholder="thoughtful, values-driven, analytical, empathetic"
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="patterns">Speaking Patterns</Label>
                <Textarea
                  id="patterns"
                  placeholder="Uses sustainability jargon, asks clarifying questions, references metrics"
                  className="min-h-[80px]"
                />
              </div>
            </CardContent>
          </Card>

          {/* Business Context */}
          <Card>
            <CardHeader>
              <CardTitle>BUSINESS CONTEXT</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="revenue">Annual Revenue</Label>
                  <Input
                    id="revenue"
                    value={formData.annualRevenue}
                    onChange={(e) => handleInputChange('annualRevenue', e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="growth">Growth Rate</Label>
                  <Select value={formData.growthRate} onValueChange={(value) => handleInputChange('growthRate', value)}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="5%">5%</SelectItem>
                      <SelectItem value="10%">10%</SelectItem>
                      <SelectItem value="15%">15%</SelectItem>
                      <SelectItem value="25%">25%</SelectItem>
                      <SelectItem value="32%">32%</SelectItem>
                      <SelectItem value="50%">50%</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="team">Team Size</Label>
                  <Input
                    id="team"
                    value={formData.teamSize}
                    onChange={(e) => handleInputChange('teamSize', e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="years">Years in Business</Label>
                  <Input
                    id="years"
                    value={formData.yearsInBusiness}
                    onChange={(e) => handleInputChange('yearsInBusiness', e.target.value)}
                  />
                </div>
              </div>
              
              <div className="mt-6 space-y-4">
                <h4 className="font-medium">Key Metrics</h4>
                <div className="grid gap-4 md:grid-cols-3">
                  <div className="space-y-2">
                    <Label htmlFor="subscription">Subscription Revenue</Label>
                    <Input
                      id="subscription"
                      value={formData.subscriptionRevenue}
                      onChange={(e) => handleInputChange('subscriptionRevenue', e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="ltv">Customer LTV</Label>
                    <Input
                      id="ltv"
                      value={formData.customerLTV}
                      onChange={(e) => handleInputChange('customerLTV', e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="customers">Monthly Active Customers</Label>
                    <Input
                      id="customers"
                      value={formData.monthlyActiveCustomers}
                      onChange={(e) => handleInputChange('monthlyActiveCustomers', e.target.value)}
                    />
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}