import React, { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useToast } from '@/components/ui/use-toast'
import { 
  Database, 
  Clock, 
  FileText, 
  Search,
  AlertCircle,
  Loader2,
  AlertTriangle
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
  stuck_count?: number
}

export function KnowledgeListView() {
  const { toast } = useToast()
  const [graphs, setGraphs] = useState<KnowledgeGraph[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')

  useEffect(() => {
    loadGraphs()
  }, [])

  const loadGraphs = async () => {
    try {
      setLoading(true)
      const response = await fetch(`${API_BASE}/graphs`)
      if (!response.ok) throw new Error('Failed to load knowledge graphs')
      
      const data = await response.json()
      const graphList = data.graphs || []
      
      // Fetch stuck counts for each graph
      const graphsWithStuckCounts = await Promise.all(
        graphList.map(async (graph: KnowledgeGraph) => {
          try {
            const statsResponse = await fetch(`${API_BASE}/graphs/${graph.id}/statistics`)
            if (statsResponse.ok) {
              const stats = await statsResponse.json()
              return { ...graph, stuck_count: stats.stuck_count || 0 }
            }
          } catch (error) {
            console.error(`Error fetching stats for ${graph.id}:`, error)
          }
          return graph
        })
      )
      
      setGraphs(graphsWithStuckCounts)
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
              View your RAG knowledge bases. Use the Knowledge CLI to create and manage graphs.
            </p>
          </div>
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
          {/* CLI Instructions */}
          <Card className="p-6 mb-6 bg-muted/50">
            <h3 className="text-lg font-semibold mb-3">Managing Knowledge Graphs</h3>
            <p className="text-sm text-muted-foreground mb-4">
              Use the Knowledge CLI to create and manage knowledge graphs:
            </p>
            <div className="space-y-3">
              <div className="font-mono text-sm bg-background rounded-lg p-3 border">
                <p className="text-muted-foreground mb-1"># Create a new knowledge graph:</p>
                <p>knowledge.py create &lt;namespace_id&gt; --name "Graph Name" --description "Description"</p>
              </div>
              <div className="font-mono text-sm bg-background rounded-lg p-3 border">
                <p className="text-muted-foreground mb-1"># List all knowledge graphs:</p>
                <p>knowledge.py list</p>
              </div>
              <div className="font-mono text-sm bg-background rounded-lg p-3 border">
                <p className="text-muted-foreground mb-1"># Delete a knowledge graph:</p>
                <p>knowledge.py delete &lt;namespace_id&gt;</p>
              </div>
            </div>
          </Card>

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
                  : 'Use the Knowledge CLI to create your first knowledge graph'}
              </p>
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

                    {graph.stuck_count && graph.stuck_count > 0 && (
                      <div className="flex items-center gap-2 mt-3 text-sm text-amber-600">
                        <AlertTriangle className="h-4 w-4" />
                        <span>{graph.stuck_count} stuck document{graph.stuck_count !== 1 ? 's' : ''}</span>
                      </div>
                    )}

                    {graph.status !== 'active' && !graph.stuck_count && (
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