'use client'

import React, { useState, use, useEffect } from 'react'
import TopNavigation from '@/components/TopNavigation'
import LeftSidebar from '@/components/LeftSidebar'
import CenterPanel from '@/components/CenterPanel'
import RightPanel from '@/components/RightPanel'
import { listChapters, getProject, ProjectInfo } from '@/app/api-client'

interface PageProps {
  params: Promise<{ projectId: string; chapterId: string }>
}

export default function ChapterWorkspace({ params }: PageProps) {
  const { projectId, chapterId } = use(params)
  const [projectInfo, setProjectInfo] = useState<ProjectInfo | null>(null)
  
  // Format chapter name for display, e.g. "chapter1" -> "Chapter 1"
  const formatChapter = (ch: string) => {
    if (!ch) return ''
    if (ch.startsWith('chapter')) {
      return `Chapter ${ch.replace('chapter', '')}`
    }
    return ch.charAt(0).toUpperCase() + ch.slice(1)
  }
  
  const chapterName = formatChapter(chapterId)
  const projectName = projectInfo ? (projectInfo.project_id === 'demo_project' ? 'Sample Document' : projectInfo.project_id) : projectId
  const displayTitle = `${projectName} / ${chapterName}`

  const [currentProject, setCurrentProject] = useState(displayTitle)
  const [activeFile, setActiveFile] = useState(chapterId)
  const [sourceMode, setSourceMode] = useState<'text' | 'visual'>('text')
  const [selectedBlock, setSelectedBlock] = useState(0)
  const [showLeftSidebar, setShowLeftSidebar] = useState(true)
  const [showRightPanel, setShowRightPanel] = useState(true)
  const [glossaryRefreshKey, setGlossaryRefreshKey] = useState(0)
  const [currentStep, setCurrentStep] = useState<'read' | 'edit' | 'review' | 'approve'>('read')

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const info = await getProject(projectId);
        if (active && info) {
          setProjectInfo(info);
          const pName = info.project_id === 'demo_project' ? 'Sample Document' : info.project_id;
          setCurrentProject(`${pName} / ${formatChapter(chapterId)}`);
        }
      } catch (err) {
        console.error('Failed to load project in workspace:', err);
      }

      try {
        const chapters = await listChapters(projectId);
        if (active && chapters && chapters.length > 0) {
          // Find if there's a chapter matching chapterId or fallback to first
          const match = chapters.find(c => c.toLowerCase().includes(chapterId.toLowerCase()));
          setActiveFile(match || chapters[0]);
        }
      } catch (err) {
        console.error('Failed to load chapters in workspace:', err);
      }
    }
    load();
    return () => { active = false; };
  }, [projectId, chapterId]);

  // Resizable Sidebars state & functions
  const [leftWidth, setLeftWidth] = useState(320)
  const [rightWidth, setRightWidth] = useState(320)
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

  const startResizeRight = (e: React.MouseEvent) => {
    e.preventDefault()
    setIsResizing(true)
    const startX = e.clientX
    const startWidth = rightWidth
    
    const doDrag = (moveEvent: MouseEvent) => {
      const newWidth = Math.max(220, Math.min(480, startWidth - (moveEvent.clientX - startX)))
      setRightWidth(newWidth)
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
          showRightPanel={showRightPanel}
          onToggleLeft={() => setShowLeftSidebar(!showLeftSidebar)}
          onToggleRight={() => setShowRightPanel(!showRightPanel)}
          currentStep={currentStep}
          onStepChange={setCurrentStep}
        />
        
        {/* Right Panel Container */}
        <div 
          style={{ width: showRightPanel ? `${rightWidth}px` : '0px' }}
          className={`relative shrink-0 overflow-hidden flex ${isResizing ? '' : 'transition-[width] duration-150 ease-out'}`}
        >
          {showRightPanel && (
            <div 
              onMouseDown={startResizeRight}
              className="absolute top-0 left-0 w-1.5 h-full cursor-col-resize hover:bg-accent-purple/40 z-50 transition-colors"
            />
          )}
          <div className="w-full h-full shrink-0">
            <RightPanel 
              projectId={projectId}
              selectedBlock={selectedBlock}
              onClose={() => setShowRightPanel(false)}
              onGlossaryUpdated={() => setGlossaryRefreshKey(prev => prev + 1)}
              currentStep={currentStep}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
