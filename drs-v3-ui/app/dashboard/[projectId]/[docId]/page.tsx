'use client'

import React, { useState, use, useEffect } from 'react'
import TopNavigation from '@/components/TopNavigation'
import LeftSidebar from '@/components/LeftSidebar'
import CenterPanel from '@/components/CenterPanel'
import { listChapters, getProject, ProjectInfo } from '@/app/api-client'

interface PageProps {
  params: Promise<{ projectId: string; docId: string }>
}

export default function ChapterWorkspace({ params }: PageProps) {
  const { projectId, docId } = use(params)
  const [projectInfo, setProjectInfo] = useState<ProjectInfo | null>(null)
  
  // Format document name for display, e.g. "chapter1" -> "Chapter 1"
  const formatDoc = (ch: string) => {
    if (!ch) return ''
    if (ch.startsWith('chapter')) {
      return `Chapter ${ch.replace('chapter', '')}`
    }
    return ch.charAt(0).toUpperCase() + ch.slice(1)
  }
  
  const docName = formatDoc(docId)
  const projectName = projectInfo ? (projectInfo.description || (projectInfo.project_id === 'demo_project' ? 'Sample Document' : projectInfo.project_id)) : projectId
  const displayTitle = `${projectName} / ${docName}`

  const [currentProject, setCurrentProject] = useState(displayTitle)
  const [activeFile, setActiveFile] = useState(docId)
  const [sourceMode, setSourceMode] = useState<'text' | 'visual'>('text')
  const [selectedBlock, setSelectedBlock] = useState(0)
  const [showLeftSidebar, setShowLeftSidebar] = useState(true)
  const [glossaryRefreshKey] = useState(0)
  const [currentStep, setCurrentStep] = useState<'read' | 'edit' | 'review' | 'approve'>('read')
  const [pipelineStep, setPipelineStep] = useState<'idle' | 'translating' | 'polishing' | 'qa_check' | 'ready'>('idle')
  const [pipelineLogs, setPipelineLogs] = useState<string[]>([])

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const info = await getProject(projectId);
        if (active && info) {
          setProjectInfo(info);
          const pName = info.description || (info.project_id === 'demo_project' ? 'Sample Document' : info.project_id);
          setCurrentProject(`${pName} / ${formatDoc(docId)}`);
        }
      } catch (err) {
        console.error('Failed to load project in workspace:', err);
      }

      try {
        const chapters = await listChapters(projectId);
        if (active && chapters && chapters.length > 0) {
          // Find if there's a chapter matching docId or fallback to first
          const match = chapters.find(c => c.toLowerCase().includes(docId.toLowerCase()));
          setActiveFile(match || chapters[0]);
        }
      } catch (err) {
        console.error('Failed to load chapters in workspace:', err);
      }
    }
    load();
    return () => { active = false; };
  }, [projectId, docId]);

  // Resizable Sidebars state & functions
  const [leftWidth, setLeftWidth] = useState(320)
  const [isResizing, setIsResizing] = useState(false)

  const startResizeLeft = (e: React.MouseEvent) => {
    e.preventDefault()
    setIsResizing(true)
    const startX = e.clientX
    const startWidth = leftWidth
    
    const doDrag = (moveEvent: MouseEvent) => {
      const newWidth = Math.max(220, Math.min(480, startWidth + (moveEvent.clientX - startX)))
      setLeftWidth(newWidth)
    }
    
    const stopDrag = () => {
      setIsResizing(false)
      document.removeEventListener('mousemove', doDrag)
      document.removeEventListener('mouseup', stopDrag)
    }
    
    document.addEventListener('mousemove', doDrag)
    document.addEventListener('mouseup', stopDrag)
  }

  return (
    <div className="w-screen h-screen bg-themeBg text-themeText overflow-hidden flex flex-col">
      <TopNavigation 
        projectId={projectId}
        currentProject={currentProject}
        onProjectChange={setCurrentProject}
      />
      
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar Container */}
        <div 
          style={{ width: showLeftSidebar ? `${leftWidth}px` : '0px' }}
          className={`relative shrink-0 overflow-hidden flex ${isResizing ? '' : 'transition-[width] duration-150 ease-out'}`}
        >
          <div className="w-full h-full shrink-0">
            <LeftSidebar 
              projectId={projectId}
              activeFile={activeFile}
              onFileSelect={setActiveFile}
              projectName={projectName}
              onClose={() => setShowLeftSidebar(false)}
              glossaryRefreshKey={glossaryRefreshKey}
            />
          </div>
          {showLeftSidebar && (
            <div 
              onMouseDown={startResizeLeft}
              className="absolute top-0 right-0 w-1.5 h-full cursor-col-resize hover:bg-accent-purple/40 z-50 transition-colors"
            />
          )}
        </div>
        
        {/* Center Panel */}
        <CenterPanel 
          projectId={projectId}
          activeFile={activeFile}
          sourceMode={sourceMode}
          onSourceModeChange={setSourceMode}
          selectedBlock={selectedBlock}
          onBlockSelect={setSelectedBlock}
          showLeftSidebar={showLeftSidebar}
          onToggleLeft={() => setShowLeftSidebar(!showLeftSidebar)}
          currentStep={currentStep}
          onStepChange={setCurrentStep}
          pipelineStep={pipelineStep}
          setPipelineStep={setPipelineStep}
          pipelineLogs={pipelineLogs}
          setPipelineLogs={setPipelineLogs}
        />
      </div>
    </div>
  )
}
