import React from 'react'
import { Link, useLocation } from 'wouter'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
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
    description: 'Editor configuration'
  }
]

export function EditorLayout({ children }: EditorLayoutProps) {
  const [location] = useLocation()

  return (
    <div className="flex h-screen bg-background">
      {/* Navigation Sidebar */}
      <div className="w-64 border-r">
        <div className="flex h-full flex-col">
          {/* Logo/Header */}
          <div className="flex h-16 items-center border-b px-6 bg-primary">
            <h1 className="text-xl font-semibold text-primary-foreground">Agent Editor</h1>
          </div>

          {/* Navigation Items */}
          <ScrollArea className="flex-1 px-3 py-4">
            <nav className="space-y-2">
              {navItems.map((item) => {
                const isActive = location === item.href || 
                  (item.href === '/' && location === '')
                
                return (
                  <Link key={item.href} href={item.href}>
                    <a className="block">
                      <Button
                        variant={isActive ? 'secondary' : 'ghost'}
                        className={cn(
                          'w-full justify-start text-left',
                          isActive && 'bg-primary text-primary-foreground hover:bg-primary/90'
                        )}
                      >
                        <item.icon className="mr-2 h-4 w-4" />
                        <div className="flex-1">
                          <div className="text-sm font-medium">{item.title}</div>
                          {isActive && (
                            <div className="text-xs text-muted-foreground">
                              {item.description}
                            </div>
                          )}
                        </div>
                        {isActive && (
                          <ChevronRight className="ml-2 h-4 w-4" />
                        )}
                      </Button>
                    </a>
                  </Link>
                )
              })}
            </nav>
          </ScrollArea>

          {/* Footer */}
          <div className="border-t p-4">
            <p className="text-xs text-muted-foreground">
              HireCJ Agent Editor v1.0
            </p>
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