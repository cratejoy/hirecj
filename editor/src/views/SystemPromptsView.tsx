import React from 'react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Save, Loader2, RotateCcw } from 'lucide-react'
import { useToast } from '@/components/ui/use-toast'

const API_BASE = '/api/v1'

export function SystemPromptsView() {
  const [versions, setVersions] = React.useState<string[]>([])
  const [selectedVersion, setSelectedVersion] = React.useState<string>('')
  const [promptContent, setPromptContent] = React.useState('')
  const [originalContent, setOriginalContent] = React.useState('')
  const [loading, setLoading] = React.useState(false)
  const [saving, setSaving] = React.useState(false)
  const { toast } = useToast()
  
  // Check if content has changed
  const hasChanges = promptContent !== originalContent

  // Load available versions on mount
  React.useEffect(() => {
    loadVersions()
  }, [])

  // Load prompt content when version changes
  React.useEffect(() => {
    if (selectedVersion) {
      loadPrompt(selectedVersion)
    }
  }, [selectedVersion])

  const loadVersions = async () => {
    try {
      setLoading(true)
      const response = await fetch(`${API_BASE}/prompts`)
      const data = await response.json()
      setVersions(data.versions)
      
      // Select the first version by default
      if (data.versions.length > 0 && !selectedVersion) {
        setSelectedVersion(data.versions[0])
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to load prompt versions',
        variant: 'destructive',
      })
    } finally {
      setLoading(false)
    }
  }

  const loadPrompt = async (version: string) => {
    try {
      setLoading(true)
      const response = await fetch(`${API_BASE}/prompts/${version}`)
      const data = await response.json()
      const content = data.prompt || ''
      setPromptContent(content)
      setOriginalContent(content) // Reset original content when loading
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to load prompt content',
        variant: 'destructive',
      })
    } finally {
      setLoading(false)
    }
  }

  const savePrompt = async () => {
    try {
      setSaving(true)
      const response = await fetch(`${API_BASE}/prompts/new-version`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          current_version: selectedVersion,
          prompt: promptContent 
        }),
      })

      if (!response.ok) {
        throw new Error('Failed to save')
      }

      const data = await response.json()
      
      // Update state with new version
      setOriginalContent(promptContent) // Update original to match saved
      
      // Reload versions to include the new one
      await loadVersions()
      
      // Select the new version
      setSelectedVersion(data.version)
      
      toast({
        title: 'Success',
        description: data.message,
      })
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to save prompt',
        variant: 'destructive',
      })
    } finally {
      setSaving(false)
    }
  }
  
  const revertChanges = () => {
    setPromptContent(originalContent)
    toast({
      title: 'Reverted',
      description: 'Changes have been reverted',
    })
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b p-4">
        <div className="flex items-center gap-4">
          <h1 className="text-xl font-semibold">
            System Prompts
            {hasChanges && <span className="ml-2 text-sm font-normal text-muted-foreground">(unsaved changes)</span>}
          </h1>
          <Select 
            value={selectedVersion} 
            onValueChange={setSelectedVersion}
            disabled={loading}
          >
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="Select version" />
            </SelectTrigger>
            <SelectContent>
              {versions.map(version => (
                <SelectItem key={version} value={version}>
                  {version}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex gap-2">
          {hasChanges && (
            <Button 
              onClick={revertChanges}
              variant="outline"
              disabled={loading}
            >
              <RotateCcw className="mr-2 h-4 w-4" />
              Revert
            </Button>
          )}
          <Button 
            onClick={savePrompt} 
            disabled={!hasChanges || saving || loading || !selectedVersion}
          >
            {saving ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="mr-2 h-4 w-4" />
                Save as New Version
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Editor */}
      <div className="flex-1 p-6">
        {loading ? (
          <div className="flex h-full items-center justify-center">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <Textarea
            value={promptContent}
            onChange={(e) => setPromptContent(e.target.value)}
            className="h-full resize-none font-mono text-sm"
            placeholder={hasChanges ? "You have unsaved changes..." : "Select a prompt version to edit..."}
            disabled={!selectedVersion}
          />
        )}
      </div>
    </div>
  )
}