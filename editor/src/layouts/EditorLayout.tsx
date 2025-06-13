import React from 'react'
import { Link, useLocation } from 'wouter'
import { cn } from '@/lib/utils'
import { ScrollArea } from '@/components/ui/scroll-area'
import { 
  Play, 
  Users, 
  FileText, 
  GitBranch, 
  Wrench,
  Settings,
  ChevronRight
} from 'lucide-react'

interface EditorLayoutProps {
  children: React.ReactNode
}

const navItems = [
  {
    title: 'Playground',
    icon: Play,
    href: '/',
    description: 'Test and refine agent conversations'
  },
  {
    title: 'User Personas',
    icon: Users,
    href: '/personas',
    description: 'Manage merchant personas for testing'
  },
  {
    title: 'System Prompts',
    icon: FileText,
    href: '/prompts',
    description: 'Edit agent system prompts'
  },
  {
    title: 'Workflow Editor',
    icon: GitBranch,
    href: '/workflows',
    description: 'Design conversation workflows'
  },
  {
    title: 'Tool Editor',
    icon: Wrench,
    href: '/tools',
    description: 'Configure agent tools and functions'
  },
  {
    title: 'Settings',
    icon: Settings,
    href: '/settings',
    description: 'Editor configuration',
    separator: true
  }
]

export function EditorLayout({ children }: EditorLayoutProps) {
  const [location] = useLocation()

  return (
    <div className="flex h-screen bg-background">
      {/* Navigation Sidebar */}
      <div className="w-72 border-r bg-muted/30">
        <div className="flex h-full flex-col">
          {/* Logo/Header */}
          <div className="flex h-20 items-center border-b px-8 bg-primary">
            <h1 className="text-2xl font-bold text-primary-foreground tracking-tight">Agent Editor</h1>
          </div>

          {/* Navigation Items */}
          <ScrollArea className="flex-1">
            <nav className="p-4 space-y-1">
              {navItems.map((item, index) => {
                const isActive = location === item.href || 
                  (item.href === '/' && location === '')
                
                return (
                  <React.Fragment key={item.href}>
                    {item.separator && index > 0 && (
                      <div className="my-4 border-t border-border/50" />
                    )}
                    <Link href={item.href}>
                      <a className="block">
                        <div
                          className={cn(
                            'flex items-center gap-3 rounded-lg px-4 py-3 text-sm transition-all',
                            isActive 
                              ? 'bg-primary text-primary-foreground shadow-sm hover:bg-primary/90' 
                              : 'hover:bg-accent/50 text-foreground/70 hover:text-foreground'
                          )}
                        >
                          <item.icon className={cn(
                            "h-5 w-5 shrink-0 transition-colors",
                            isActive ? "text-primary-foreground" : ""
                          )} />
                          <div className="flex-1 space-y-1">
                            <div className={cn(
                              "font-medium leading-none",
                              isActive ? "text-primary-foreground" : ""
                            )}>
                              {item.title}
                            </div>
                            {isActive && (
                              <div className="text-xs opacity-90 leading-normal">
                                {item.description}
                              </div>
                            )}
                          </div>
                          {isActive && (
                            <ChevronRight className="h-4 w-4 opacity-75" />
                          )}
                        </div>
                      </a>
                    </Link>
                  </React.Fragment>
                )
              })}
            </nav>
          </ScrollArea>

          {/* Footer */}
          <div className="border-t p-6">
            <div className="space-y-1">
              <p className="text-xs font-medium text-muted-foreground">HireCJ Agent Editor</p>
              <p className="text-xs text-muted-foreground/70">Version 1.0.0</p>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-hidden">
        {children}
      </div>
    </div>
  )
}