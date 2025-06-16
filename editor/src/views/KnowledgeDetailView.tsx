import React, { useState, useCallback, useEffect } from 'react'
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
  Upload, 
  Link as LinkIcon,
  Search,
  FileText,
  FileJson,
  FileCode,
  Globe,
  Loader2,
  X,
  CheckCircle,
  AlertCircle,
  AlertTriangle
} from 'lucide-react'

const API_BASE = '/api/v1/knowledge'

interface UploadedFile {
  filename: string
  status: 'pending' | 'uploading' | 'success' | 'error'
  error?: string
}

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
  const [activeTab, setActiveTab] = useState<'upload' | 'query'>('upload')
  const [uploadMode, setUploadMode] = useState<'files' | 'url'>('files')
  const [urlInput, setUrlInput] = useState('')
  const [queryInput, setQueryInput] = useState('')
  const [queryMode, setQueryMode] = useState('hybrid')
  const [queryResult, setQueryResult] = useState('')
  const [querying, setQuerying] = useState(false)
  const [uploadingUrl, setUploadingUrl] = useState(false)
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([])
  const [isDragging, setIsDragging] = useState(false)
  const [queryDuration, setQueryDuration] = useState<number | null>(null)
  const [stuckDocuments, setStuckDocuments] = useState<StuckDocument[]>([])
  const [loadingStuck, setLoadingStuck] = useState(false)
  const [retrying, setRetrying] = useState(false)

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

  const retryAllStuck = async () => {
    try {
      setRetrying(true)
      const response = await fetch(`${API_BASE}/graphs/${graphId}/retry-stuck`, {
        method: 'POST'
      })
      
      if (!response.ok) {
        throw new Error('Failed to retry stuck documents')
      }
      
      toast({
        title: "Success",
        description: "Reprocessing triggered for stuck documents"
      })
      
      // Reload stuck documents after a short delay
      setTimeout(() => {
        loadStuckDocuments()
      }, 2000)
      
    } catch (error) {
      console.error('Error retrying stuck documents:', error)
      toast({
        title: "Error",
        description: "Failed to retry stuck documents",
        variant: "destructive"
      })
    } finally {
      setRetrying(false)
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

  // File upload handlers
  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    
    const files = Array.from(e.dataTransfer.files)
    handleFiles(files)
  }, [])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const files = Array.from(e.target.files)
      handleFiles(files)
    }
  }

  const handleFiles = async (files: File[]) => {
    // Add files to state with pending status
    const newFiles: UploadedFile[] = files.map(file => ({
      filename: file.name,
      status: 'pending' as const
    }))
    setUploadedFiles(prev => [...prev, ...newFiles])

    // Update to uploading status
    setUploadedFiles(prev => 
      prev.map(f => 
        newFiles.find(nf => nf.filename === f.filename) 
          ? { ...f, status: 'uploading' as const }
          : f
      )
    )

    try {
      const formData = new FormData()
      files.forEach(file => {
        formData.append('files', file)
      })

      const response = await fetch(`${API_BASE}/graphs/${graphId}/upload`, {
        method: 'POST',
        body: formData
      })

      if (!response.ok) {
        throw new Error('Upload failed')
      }

      const result = await response.json()

      // Update file statuses based on result
      setUploadedFiles(prev => 
        prev.map(f => {
          const uploadedFile = newFiles.find(nf => nf.filename === f.filename)
          if (!uploadedFile) return f

          const successful = result.details?.successful?.find(
            (s: any) => s.filename === f.filename
          )
          const failed = result.details?.failed?.find(
            (s: any) => s.filename === f.filename
          )

          if (successful) {
            return { ...f, status: 'success' as const }
          } else if (failed) {
            return { 
              ...f, 
              status: 'error' as const, 
              error: failed.error 
            }
          }
          return f
        })
      )

      toast({
        title: "Upload Complete",
        description: `Successfully uploaded ${result.uploaded} file(s)${
          result.failed > 0 ? `, ${result.failed} failed` : ''
        }`
      })
    } catch (error) {
      console.error('Upload error:', error)
      
      // Mark all new files as error
      setUploadedFiles(prev => 
        prev.map(f => 
          newFiles.find(nf => nf.filename === f.filename)
            ? { ...f, status: 'error' as const, error: 'Upload failed' }
            : f
        )
      )
      
      toast({
        title: "Upload Failed",
        description: "Failed to upload files. Please try again.",
        variant: "destructive"
      })
    }
  }

  const handleUrlSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!urlInput.trim()) {
      toast({
        title: "Invalid Input",
        description: "Please enter a URL",
        variant: "destructive"
      })
      return
    }

    try {
      setUploadingUrl(true)
      
      const response = await fetch(`${API_BASE}/graphs/${graphId}/url`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          url: urlInput,
          metadata: {}
        })
      })

      if (!response.ok) {
        throw new Error('Failed to ingest URL')
      }

      await response.json()
      
      toast({
        title: "Success",
        description: "URL content ingested successfully"
      })
      
      setUrlInput('')
    } catch (error) {
      console.error('URL ingest error:', error)
      toast({
        title: "Error",
        description: "Failed to ingest URL content",
        variant: "destructive"
      })
    } finally {
      setUploadingUrl(false)
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

  const removeFile = (filename: string) => {
    setUploadedFiles(prev => prev.filter(f => f.filename !== filename))
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
              Upload documents and query your knowledge base
            </p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b px-6">
        <div className="flex gap-8">
          <button
            className={`py-3 px-1 border-b-2 font-medium text-sm transition-colors ${
              activeTab === 'upload' 
                ? 'border-primary text-foreground' 
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
            onClick={() => setActiveTab('upload')}
          >
            <Upload className="h-4 w-4 inline mr-2" />
            Upload Content
          </button>
          <button
            className={`py-3 px-1 border-b-2 font-medium text-sm transition-colors ${
              activeTab === 'query' 
                ? 'border-primary text-foreground' 
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
            onClick={() => setActiveTab('query')}
          >
            <Search className="h-4 w-4 inline mr-2" />
            Query Knowledge
          </button>
        </div>
      </div>

      {/* Content */}
      <ScrollArea className="flex-1">
        <div className="p-6">
          {activeTab === 'upload' && (
            <div className="max-w-4xl mx-auto">
              {/* Upload Mode Selector */}
              <div className="mb-6">
                <Label>Upload Mode</Label>
                <div className="flex gap-4 mt-2">
                  <Button
                    variant={uploadMode === 'files' ? 'default' : 'outline'}
                    onClick={() => setUploadMode('files')}
                    className="flex-1"
                  >
                    <FileText className="h-4 w-4 mr-2" />
                    Files
                  </Button>
                  <Button
                    variant={uploadMode === 'url' ? 'default' : 'outline'}
                    onClick={() => setUploadMode('url')}
                    className="flex-1"
                  >
                    <Globe className="h-4 w-4 mr-2" />
                    URL
                  </Button>
                </div>
              </div>

              {uploadMode === 'files' && (
                <>
                  {/* File Upload */}
                  <div
                    className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                      isDragging 
                        ? 'border-primary bg-primary/5' 
                        : 'border-muted-foreground/25 hover:border-muted-foreground/50'
                    }`}
                    onDrop={handleDrop}
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                  >
                    <Upload className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
                    <h3 className="text-lg font-semibold mb-2">
                      Drop files here or click to browse
                    </h3>
                    <p className="text-sm text-muted-foreground mb-4">
                      Supported: .txt, .md, .json files
                    </p>
                    <input
                      type="file"
                      multiple
                      accept=".txt,.md,.json"
                      onChange={handleFileSelect}
                      className="hidden"
                      id="file-input"
                    />
                    <label htmlFor="file-input">
                      <Button asChild>
                        <span>Select Files</span>
                      </Button>
                    </label>
                  </div>

                  {/* Uploaded Files List */}
                  {uploadedFiles.length > 0 && (
                    <div className="mt-6 space-y-2">
                      <h3 className="font-semibold mb-3">Uploaded Files</h3>
                      {uploadedFiles.map((file) => {
                        const FileIcon = getFileIcon(file.filename)
                        return (
                          <div
                            key={file.filename}
                            className="flex items-center gap-3 p-3 rounded-lg border bg-card"
                          >
                            <FileIcon className="h-4 w-4 text-muted-foreground" />
                            <span className="flex-1 text-sm">{file.filename}</span>
                          {file.status === 'pending' && (
                            <span className="text-sm text-muted-foreground">Waiting...</span>
                          )}
                          {file.status === 'uploading' && (
                            <Loader2 className="h-4 w-4 animate-spin text-primary" />
                          )}
                          {file.status === 'success' && (
                            <CheckCircle className="h-4 w-4 text-green-600" />
                          )}
                          {file.status === 'error' && (
                            <div className="flex items-center gap-2">
                              <AlertCircle className="h-4 w-4 text-destructive" />
                              {file.error && (
                                <span className="text-xs text-destructive">{file.error}</span>
                              )}
                            </div>
                          )}
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => removeFile(file.filename)}
                          >
                            <X className="h-4 w-4" />
                          </Button>
                        </div>
                        )
                      })}
                    </div>
                  )}
                </>
              )}

              {uploadMode === 'url' && (
                <form onSubmit={handleUrlSubmit}>
                  <div className="space-y-4">
                    <div>
                      <Label htmlFor="url-input">URL to Ingest</Label>
                      <div className="flex gap-2 mt-2">
                        <Input
                          id="url-input"
                          type="url"
                          placeholder="https://example.com/article"
                          value={urlInput}
                          onChange={(e) => setUrlInput(e.target.value)}
                          disabled={uploadingUrl}
                          className="flex-1"
                        />
                        <Button type="submit" disabled={uploadingUrl}>
                          {uploadingUrl ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <LinkIcon className="h-4 w-4" />
                          )}
                          <span className="ml-2">Ingest</span>
                        </Button>
                      </div>
                      <p className="text-sm text-muted-foreground mt-2">
                        The content from the URL will be fetched and added to your knowledge base
                      </p>
                    </div>
                  </div>
                </form>
              )}

              {/* Processing Status Section */}
              {stuckDocuments.length > 0 && (
                <Card className="mt-6 p-4 border-amber-200 bg-amber-50/50">
                  <div className="flex items-center gap-2 mb-3">
                    <AlertTriangle className="h-5 w-5 text-amber-600" />
                    <h3 className="font-semibold text-amber-900">
                      Processing Status
                    </h3>
                    <div className="ml-auto flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={retryAllStuck}
                        disabled={retrying || loadingStuck}
                      >
                        {retrying ? (
                          <>
                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                            Retrying...
                          </>
                        ) : (
                          'Retry All'
                        )}
                      </Button>
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
                  </div>
                </Card>
              )}
            </div>
          )}

          {activeTab === 'query' && (
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
          )}
        </div>
      </ScrollArea>
    </div>
  )
}