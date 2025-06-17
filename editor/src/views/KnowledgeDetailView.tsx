import React, { useState, useEffect } from 'react'
import { useParams, Link } from 'wouter'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { ScrollArea } from '@/components/ui/scroll-area'
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useToast } from '@/components/ui/use-toast'
import { 
  ArrowLeft,
  Search,
  FileText,
  FileJson,
  FileCode,
  Loader2,
  AlertTriangle
} from 'lucide-react'

const API_BASE = '/api/v1/knowledge'

interface StuckDocument {
  id: string
  status: 'pending' | 'processing'
  file_path: string
  updated_at: string
  minutes_stuck: number
  content_summary: string
}

export function KnowledgeDetailView() {
  const { graphId } = useParams()
  const { toast } = useToast()
  
  // State
  const [queryInput, setQueryInput] = useState('')
  const [queryMode, setQueryMode] = useState('hybrid')
  const [queryResult, setQueryResult] = useState('')
  const [querying, setQuerying] = useState(false)
  const [queryDuration, setQueryDuration] = useState<number | null>(null)
  const [stuckDocuments, setStuckDocuments] = useState<StuckDocument[]>([])
  const [loadingStuck, setLoadingStuck] = useState(false)

  // Load stuck documents on mount and periodically
  useEffect(() => {
    loadStuckDocuments()
    
    // Refresh stuck documents every 30 seconds
    const interval = setInterval(loadStuckDocuments, 30000)
    
    return () => clearInterval(interval)
  }, [graphId])

  const loadStuckDocuments = async () => {
    try {
      setLoadingStuck(true)
      const response = await fetch(`${API_BASE}/graphs/${graphId}/stuck`)
      if (response.ok) {
        const data = await response.json()
        setStuckDocuments(data.documents || [])
      }
    } catch (error) {
      console.error('Error loading stuck documents:', error)
    } finally {
      setLoadingStuck(false)
    }
  }


  // Get file icon based on extension
  const getFileIcon = (filename: string) => {
    const ext = filename.split('.').pop()?.toLowerCase()
    switch (ext) {
      case 'json':
        return FileJson
      case 'md':
        return FileCode
      case 'txt':
      default:
        return FileText
    }
  }


  const handleQuery = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!queryInput.trim()) {
      toast({
        title: "Invalid Input",
        description: "Please enter a query",
        variant: "destructive"
      })
      return
    }

    try {
      setQuerying(true)
      setQueryResult('')
      setQueryDuration(null)
      
      // Start timing
      const startTime = performance.now()
      
      const response = await fetch(`${API_BASE}/graphs/${graphId}/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          query: queryInput,
          mode: queryMode
        })
      })

      if (!response.ok) {
        throw new Error('Query failed')
      }

      const result = await response.json()
      
      // Calculate duration
      const endTime = performance.now()
      const duration = (endTime - startTime) / 1000 // Convert to seconds
      setQueryDuration(duration)
      
      setQueryResult(result.result || 'No results found')
    } catch (error) {
      console.error('Query error:', error)
      toast({
        title: "Query Failed",
        description: "Failed to query knowledge graph",
        variant: "destructive"
      })
    } finally {
      setQuerying(false)
    }
  }


  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="border-b px-6 py-4">
        <div className="flex items-center gap-4">
          <Link href="/knowledge">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back
            </Button>
          </Link>
          <div className="flex-1">
            <h1 className="text-2xl font-semibold">Knowledge Graph: {graphId}</h1>
            <p className="text-muted-foreground mt-1">
              Query your knowledge base. Use the Knowledge CLI to add documents.
            </p>
          </div>
        </div>
      </div>

      {/* Tab - Query only */}
      <div className="border-b px-6">
        <div className="flex gap-8">
          <button
            className="py-3 px-1 border-b-2 font-medium text-sm transition-colors border-primary text-foreground"
            disabled
          >
            <Search className="h-4 w-4 inline mr-2" />
            Query Knowledge
          </button>
        </div>
      </div>

      {/* Content */}
      <ScrollArea className="flex-1">
        <div className="p-6">
          {/* Processing Status Section - Show at top when there are stuck documents */}
              {stuckDocuments.length > 0 && (
                <div className="max-w-4xl mx-auto mb-6">
                  <Card className="p-4 border-amber-200 bg-amber-50/50">
                    <div className="flex items-center gap-2 mb-3">
                      <AlertTriangle className="h-5 w-5 text-amber-600" />
                      <h3 className="font-semibold text-amber-900">
                        Processing Status
                      </h3>
                      <div className="ml-auto">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={loadStuckDocuments}
                          disabled={loadingStuck}
                        >
                          {loadingStuck ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            'Refresh'
                          )}
                        </Button>
                      </div>
                    </div>
                    <p className="text-sm text-amber-800 mb-3">
                      {stuckDocuments.length} document{stuckDocuments.length !== 1 ? 's appear' : ' appears'} to be stuck
                    </p>
                    <div className="space-y-2">
                      {stuckDocuments.map((doc) => {
                        const FileIcon = getFileIcon(doc.file_path)
                        return (
                          <div key={doc.id} className="flex items-start gap-3 p-3 bg-white rounded-lg border border-amber-200">
                            <FileIcon className="h-4 w-4 text-amber-600 mt-0.5" />
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium text-gray-900 truncate">
                                {doc.file_path}
                              </p>
                              <p className="text-xs text-gray-600 mt-1">
                                Status: {doc.status === 'processing' ? 'Processing' : 'Pending'} for {doc.minutes_stuck} minute{doc.minutes_stuck !== 1 ? 's' : ''}
                              </p>
                              {doc.content_summary && (
                                <p className="text-xs text-gray-500 mt-1 truncate">
                                  {doc.content_summary}
                                </p>
                              )}
                              <p className="text-xs text-gray-500 mt-1">
                                Last updated: {new Date(doc.updated_at).toLocaleString()}
                              </p>
                            </div>
                          </div>
                        )
                      })}
                    </div>
                    <div className="mt-3 text-xs text-amber-700">
                      <p>• Documents processing for &gt;5 minutes are considered stuck</p>
                      <p>• Documents pending for &gt;10 minutes are considered stuck</p>
                      <p>• Use the Knowledge CLI to retry stuck documents</p>
                    </div>
                  </Card>
                </div>
              )}

              {/* CLI Instructions Card */}
              <div className="max-w-4xl mx-auto mb-6">
                <Card className="p-6 bg-muted/50">
                  <h3 className="font-semibold mb-3 flex items-center gap-2">
                    <FileText className="h-5 w-5" />
                    Adding Documents to Knowledge Graph
                  </h3>
                  <p className="text-sm text-muted-foreground mb-4">
                    Use the Knowledge CLI to manage documents in this knowledge graph:
                  </p>
                  <div className="space-y-3">
                    <div className="font-mono text-sm bg-background rounded-lg p-3 border">
                      <p className="text-muted-foreground mb-1"># Add files:</p>
                      <p>knowledge.py ingest file1.txt file2.md -n {graphId}</p>
                    </div>
                    <div className="font-mono text-sm bg-background rounded-lg p-3 border">
                      <p className="text-muted-foreground mb-1"># Add URL content:</p>
                      <p>knowledge.py ingest https://example.com/article -n {graphId}</p>
                    </div>
                    <div className="font-mono text-sm bg-background rounded-lg p-3 border">
                      <p className="text-muted-foreground mb-1"># Add podcast episodes:</p>
                      <p>knowledge.py podcast https://example.com/feed.xml -n {graphId}</p>
                    </div>
                  </div>
                </Card>
              </div>
              
              {/* Query Interface */}
            <div className="max-w-4xl mx-auto">
              <form onSubmit={handleQuery} className="space-y-4">
                <div>
                  <Label htmlFor="query-input">Query</Label>
                  <Textarea
                    id="query-input"
                    placeholder="Ask a question about your knowledge base..."
                    value={queryInput}
                    onChange={(e) => setQueryInput(e.target.value)}
                    disabled={querying}
                    className="mt-2"
                    rows={3}
                  />
                </div>

                <div>
                  <Label htmlFor="query-mode">Query Mode</Label>
                  <Select value={queryMode} onValueChange={setQueryMode} disabled={querying}>
                    <SelectTrigger id="query-mode" className="mt-2">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="naive">Naive</SelectItem>
                      <SelectItem value="local">Local</SelectItem>
                      <SelectItem value="global">Global</SelectItem>
                      <SelectItem value="hybrid">Hybrid (Recommended)</SelectItem>
                    </SelectContent>
                  </Select>
                  <p className="text-sm text-muted-foreground mt-2">
                    Hybrid mode combines local and global search for best results
                  </p>
                </div>

                <Button type="submit" disabled={querying}>
                  {querying && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                  Search Knowledge
                </Button>
              </form>

              {/* Query Results */}
              {queryResult && (
                <Card className="mt-6 p-6">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="font-semibold">Results</h3>
                    {queryDuration !== null && (
                      <span className="text-sm text-muted-foreground">
                        Response time: {queryDuration.toFixed(2)}s
                      </span>
                    )}
                  </div>
                  <div className="prose prose-sm max-w-none">
                    <pre className="whitespace-pre-wrap text-sm">{queryResult}</pre>
                  </div>
                </Card>
              )}
            </div>
        </div>
      </ScrollArea>
    </div>
  )
}