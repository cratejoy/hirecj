import { Route } from 'wouter'
import { EditorLayout } from '@/layouts/EditorLayout'
import { PlaygroundView } from '@/views/PlaygroundView'
import { UserPersonasView } from '@/views/UserPersonasView'
import { SystemPromptsView } from '@/views/SystemPromptsView'
import { WorkflowEditorView } from '@/views/WorkflowEditorView'
import { ToolEditorView } from '@/views/ToolEditorView'
import { TestsView } from '@/views/TestsView'
import { KnowledgeListView } from '@/views/KnowledgeListView'
import { KnowledgeDetailView } from '@/views/KnowledgeDetailView'
import { Toaster } from '@/components/ui/toaster'

function App() {
  return (
    <>
      <EditorLayout>
      <Route path="/" component={PlaygroundView} />
      <Route path="/personas" component={UserPersonasView} />
      <Route path="/prompts" component={SystemPromptsView} />
      <Route path="/workflows" component={WorkflowEditorView} />
      <Route path="/tools" component={ToolEditorView} />
      <Route path="/settings">
        <div className="flex h-full items-center justify-center">
          <div className="text-center">
            <h2 className="text-2xl font-semibold mb-2">Settings</h2>
            <p className="text-muted-foreground">Editor configuration options coming soon</p>
          </div>
        </div>
      </Route>
      <Route path="/tests" component={TestsView} />
      <Route path="/knowledge" component={KnowledgeListView} />
      <Route path="/knowledge/:graphId" component={KnowledgeDetailView} />
    </EditorLayout>
    <Toaster />
    </>
  )
}

export default App