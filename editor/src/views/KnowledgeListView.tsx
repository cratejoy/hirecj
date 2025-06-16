import React, { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useToast } from '@/components/ui/use-toast'
import { 
  Plus, 
  Database, 
  Clock, 
  FileText, 
  Trash2,
  Search,
  AlertCircle,
  Loader2
} from 'lucide-react'
import { Link } from 'wouter'

const API_BASE = '/api/v1/knowledge'

interface KnowledgeGraph {
  id: string
  name: string
  description: string
  created_at: string
  document_count: number
  last_updated: string
  status: string
}

export function KnowledgeListView() {
  const { toast } = useToast()
  const [graphs, setGraphs] = useState<KnowledgeGraph[]>([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  
  // Form state
  const [newGraphId, setNewGraphId] = useState('')
  const [newGraphName, setNewGraphName] = useState('')
  const [newGraphDescription, setNewGraphDescription] = useState('')

  useEffect(() => {
    loadGraphs()
  }, [])

  const loadGraphs = async () => {
    try {
      setLoading(true)
      const response = await fetch(`${API_BASE}/graphs`)
      if (!response.ok) throw new Error('Failed to load knowledge graphs')
      
      const data = await response.json()
      setGraphs(data.graphs || [])
    } catch (error) {
      console.error('Error loading graphs:', error)
      toast({
        title: "Error",
        description: "Failed to load knowledge graphs",
        variant: "destructive"
      })
    } finally {
      setLoading(false)
    }
  }

  const createGraph = async (e: React.FormEvent) => {
    e.preventDefault()
    
    // Validate form
    if (!newGraphId || !newGraphName) {
      toast({
        title: "Validation Error",
        description: "Graph ID and name are required",
        variant: "destructive"
      })
      return
    }

    // Validate ID format
    if (!/^[a-z0-9_]+$/.test(newGraphId)) {
      toast({
        title: "Validation Error",
        description: "Graph ID must contain only lowercase letters, numbers, and underscores",
        variant: "destructive"
      })
      return
    }

    try {
      setCreating(true)
      const response = await fetch(`${API_BASE}/graphs?graph_id=${newGraphId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          name: newGraphName,
          description: newGraphDescription
        })
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to create knowledge graph')
      }

      toast({
        title: "Success",
        description: `Knowledge graph "${newGraphName}" created successfully`
      })

      // Reset form
      setNewGraphId('')
      setNewGraphName('')
      setNewGraphDescription('')
      setShowCreateForm(false)
      
      // Reload graphs
      await loadGraphs()
    } catch (error: any) {
      console.error('Error creating graph:', error)
      toast({
        title: "Error",
        description: error.message || "Failed to create knowledge graph",
        variant: "destructive"
      })
    } finally {
      setCreating(false)
    }
  }

  const deleteGraph = async (graphId: string, graphName: string) => {
    if (!confirm(`Are you sure you want to delete "${graphName}"? This action cannot be undone.`)) {
      return
    }

    try {
      const response = await fetch(`${API_BASE}/graphs/${graphId}`, {
        method: 'DELETE'
      })

      if (!response.ok) {
        throw new Error('Failed to delete knowledge graph')
      }

      toast({
        title: "Success",
        description: `Knowledge graph "${graphName}" deleted successfully`
      })

      // Reload graphs
      await loadGraphs()
    } catch (error) {
      console.error('Error deleting graph:', error)
      toast({
        title: "Error",
        description: "Failed to delete knowledge graph",
        variant: "destructive"
      })
    }
  }

  const filteredGraphs = graphs.filter(graph => 
    graph.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    graph.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
    graph.id.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      })
    } catch {
      return dateString
    }
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="border-b px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold">Knowledge Graphs</h1>
            <p className="text-muted-foreground mt-1">
              Manage your RAG knowledge bases for enhanced agent capabilities
            </p>
          </div>
          <Button onClick={() => setShowCreateForm(true)} disabled={showCreateForm}>
            <Plus className="h-4 w-4 mr-2" />
            New Graph
          </Button>
        </div>
      </div>

      {/* Search Bar */}
      <div className="px-6 py-4 border-b">
        <div className="relative">
          <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search knowledge graphs..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>
      </div>

      {/* Content */}
      <ScrollArea className="flex-1">
        <div className="p-6">
          {/* Create Form */}
          {showCreateForm && (
            <Card className="p-6 mb-6">
              <form onSubmit={createGraph}>
                <h3 className="text-lg font-semibold mb-4">Create New Knowledge Graph</h3>
                
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="graph-id">Graph ID</Label>
                    <Input
                      id="graph-id"
                      placeholder="e.g., products, support_docs, policies"
                      value={newGraphId}
                      onChange={(e) => setNewGraphId(e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, '_'))}
                      disabled={creating}
                      className="mt-1"
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      Lowercase letters, numbers, and underscores only
                    </p>
                  </div>

                  <div>
                    <Label htmlFor="graph-name">Name</Label>
                    <Input
                      id="graph-name"
                      placeholder="e.g., Product Knowledge"
                      value={newGraphName}
                      onChange={(e) => setNewGraphName(e.target.value)}
                      disabled={creating}
                      className="mt-1"
                    />
                  </div>

                  <div>
                    <Label htmlFor="graph-description">Description</Label>
                    <Textarea
                      id="graph-description"
                      placeholder="What will this knowledge graph contain?"
                      value={newGraphDescription}
                      onChange={(e) => setNewGraphDescription(e.target.value)}
                      disabled={creating}
                      className="mt-1"
                      rows={3}
                    />
                  </div>
                </div>

                <div className="flex gap-2 mt-6">
                  <Button type="submit" disabled={creating}>
                    {creating && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                    Create Graph
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => {
                      setShowCreateForm(false)
                      setNewGraphId('')
                      setNewGraphName('')
                      setNewGraphDescription('')
                    }}
                    disabled={creating}
                  >
                    Cancel
                  </Button>
                </div>
              </form>
            </Card>
          )}

          {/* Loading State */}
          {loading && (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          )}

          {/* Empty State */}
          {!loading && filteredGraphs.length === 0 && (
            <div className="text-center py-12">
              <Database className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">
                {searchQuery ? 'No matching knowledge graphs' : 'No knowledge graphs yet'}
              </h3>
              <p className="text-muted-foreground mb-4">
                {searchQuery 
                  ? 'Try adjusting your search query' 
                  : 'Create your first knowledge graph to get started'}
              </p>
              {!searchQuery && !showCreateForm && (
                <Button onClick={() => setShowCreateForm(true)}>
                  <Plus className="h-4 w-4 mr-2" />
                  Create Knowledge Graph
                </Button>
              )}
            </div>
          )}

          {/* Graph Grid */}
          {!loading && filteredGraphs.length > 0 && (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {filteredGraphs.map((graph) => (
                <Link key={graph.id} href={`/knowledge/${graph.id}`}>
                  <Card className="p-6 hover:shadow-lg transition-shadow cursor-pointer group">
                    <div className="flex items-start justify-between mb-4">
                      <div className="p-2 bg-primary/10 rounded-lg">
                        <Database className="h-6 w-6 text-primary" />
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="opacity-0 group-hover:opacity-100 transition-opacity"
                        onClick={(e) => {
                          e.preventDefault()
                          e.stopPropagation()
                          deleteGraph(graph.id, graph.name)
                        }}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>

                    <h3 className="font-semibold text-lg mb-1">{graph.name}</h3>
                    <p className="text-sm text-muted-foreground mb-4 line-clamp-2">
                      {graph.description || 'No description provided'}
                    </p>

                    <div className="space-y-2 text-sm">
                      <div className="flex items-center gap-2 text-muted-foreground">
                        <FileText className="h-4 w-4" />
                        <span>{graph.document_count} documents</span>
                      </div>
                      <div className="flex items-center gap-2 text-muted-foreground">
                        <Clock className="h-4 w-4" />
                        <span>Updated {formatDate(graph.last_updated)}</span>
                      </div>
                    </div>

                    {graph.status !== 'active' && (
                      <div className="flex items-center gap-2 mt-3 text-sm text-amber-600">
                        <AlertCircle className="h-4 w-4" />
                        <span className="capitalize">{graph.status}</span>
                      </div>
                    )}
                  </Card>
                </Link>
              ))}
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  )
}