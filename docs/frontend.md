# DRS v3 Frontend Documentation & Architecture

This document provides a comprehensive overview of the Next.js frontend application for the Dynamic Translation and Refining System (DRS v3). It details the folder structure, route mappings, component roles, styling choices, and REST API integration to assist backend developers and system maintainers.

---

## 1. Technology Stack Overview

- **Core Framework**: React 19 / Next.js 15 (App Router).
- **Language**: TypeScript (`.ts`, `.tsx`).
- **Styling**: Tailwind CSS & CSS Variables (`globals.css`) with support for a dark/light theme provider.
- **Iconography**: Lucide React.
- **Client API Engine**: Native Fetch API wrapped inside a stateful Bearer JWT client (`api-client.ts`).

---

## 2. Directory Structure

Below is the directory tree of the `drs-v3-ui` workspace:

```text
drs-v3-ui/
├── app/                             # Next.js App Router (pages and layouts)
│   ├── dashboard/                   # Dashboard Routes
│   │   ├── [projectId]/             # Project Specific Routes
│   │   │   ├── [chapterId]/         # Chapter Editor View
│   │   │   │   └── page.tsx         # Translation Workspace entrypoint
│   │   │   ├── memory/              # Dedicated Shared Cache Management
│   │   │   │   └── page.tsx         # Glossary, Entities, and Style Rules Page
│   │   │   └── page.tsx             # Project detail page (chapter list, settings)
│   │   └── page.tsx                 # Main dashboard page (projects list)
│   ├── api-client.ts                # API client engine, REST endpoints
│   ├── globals.css                  # Core CSS variables (Light/Dark themes)
│   ├── layout.tsx                   # Main HTML layout wrapper
│   ├── page.tsx                     # Landing / Login page
│   └── theme-provider.tsx           # Global React Context for Dark/Light mode
├── components/                      # Reusable UI Components
│   ├── CenterPanel.tsx              # Core translation and autopilot interface
│   ├── LandingHeader.tsx            # Header decoration for landing page
│   ├── LeftSidebar.tsx              # Workspace document/chapter browser
│   ├── MemoryManager.tsx            # Legacy sidebar memory component
│   ├── RightPanel.tsx               # Contextual glossary matching sidebar
│   └── TopNavigation.tsx            # Header navigations & project selector
├── next.config.mjs                  # Next.js configuration
├── tailwind.config.ts               # Tailwind design tokens & configuration
└── package.json                     # NPM packages & build scripts
```

---

## 3. Core Pages & Routes

### 1. Landing & Login Page (`/`)
- **Location**: `app/page.tsx`
- **Role**: Provides the entry gate to the translation dashboard.
- **Features**:
  - Beautiful glassmorphic log-in card with theme selection support.
  - Automatically executes authentication checks.
  - Sets up mock session credentials if developer testing is preferred.

### 2. Main Dashboard (`/dashboard`)
- **Location**: `app/dashboard/page.tsx`
- **Role**: Lists all available translation projects in the workspace.
- **Features**:
  - Displays project cards with language directions (e.g., Japanese ➔ Vietnamese).
  - Contains a **Create Project** modal to register new target directories with specific styles or content types (Manga/Novel).

### 3. Project Detail Page (`/dashboard/[projectId]`)
- **Location**: `app/dashboard/[projectId]/page.tsx`
- **Role**: Focuses on managing the contents of a specific translation project.
- **Features**:
  - Lists all imported chapters / documents, showing draft status.
  - Features the **Workspace Settings** modal containing details like model tone notes.
  - Hosts the **Project Memory Portal**: a shortcut link directing users to the shared cache controller.

### 4. Shared Project Memory Management (`/dashboard/[projectId]/memory`)
- **Location**: `app/dashboard/[projectId]/memory/page.tsx`
- **Role**: Centralized dashboard to audit and manage the project's global glossary and style guides.
- **Features**:
  - Divided into three clean tabs:
    1. **Glossary**: Lists source terms, target translations, and context notes. Allows adding and deleting items.
    2. **Entities**: Lists character names, locations, objects, and pronouns.
    3. **Style Rules**: Lists tone directives and guidelines. Displays side-by-side **Before (Avoid)** and **After (Preferred)** text examples.
  - Fuzzy-search input in the header dynamically filters cache entries matching queried terms.

### 5. Translation Workspace (`/dashboard/[projectId]/[chapterId]`)
- **Location**: `app/dashboard/[projectId]/[chapterId]/page.tsx`
- **Role**: The main interface for editing text and orchestrating the translation.
- **Features**:
  - A three-section layout containing the left chapter navigator, the main translation editor, and contextual alerts.
  - The right sidebar has been completely removed to offer maximum layout space for reading and editing.

---

## 4. Reusable Layout Components

### 1. `CenterPanel.tsx` (Core Editor Panel)
- **State Orchestrator**: Handles the multi-stage translation lifecycle (Draft ➔ Polish ➔ QA ➔ Final Approved).
- **Inline Autopilot Indicator & Log**: When background AI processes run, displays a pulsing status dot with an inline, collapsible "AI Thinking" process block that expands on click to reveal real-time CLI logs, while the underlying text container transitions to a low-opacity blur to signal active processing.
- **Candidate Options Selector**: Renders option selector buttons (Option 1: Neutral, Option 2: Formal, Option 3: Concise) once the refiner completes drafts.
- **QA Score Badge**: Shows the computed quality grade (e.g., `QA Score: 96/100`) directly next to editing toggles.
- **Alignment Highlighting**: Hovering over a sentence in the translation view pops up the corresponding sentence in the original language using an absolute alignment tooltip.

### 2. `LeftSidebar.tsx` (Chapter Navigator)
- Renders project documents.
- Includes a drop-down menu to toggle active targets and display progress badges indicating whether chapters have been approved.

### 3. `TopNavigation.tsx` (Header bar)
- Keeps tracks of navigation crumbs (`Lilia / Project ID / Chapter ID`).
- Renders the global project selection dropdown.
- Contains the theme toggler (Sun/Moon).
- Features the **Project Memory** shortcut button to easily access the glossary page from the editor.

---

## 5. API Layer & REST Client Engine

All networking with the Python backend is managed inside `app/api-client.ts`. It includes:

### 1. Authentication & Auto-Login Flow
- **Token Management**: Checks JWT expiration periods locally using base64 payload decoders (`isTokenExpired`).
- **Silent Re-Login**: If a token expires or returns a `401 Unauthorized` response, `apiFetch` automatically calls `/api/auth/login` in the background with salted admin credentials to fetch a fresh token before retrying the initial request, ensuring uninterrupted service.

### 2. Primary Endpoints Mapping
The following table summarizes the routes mapped in `api-client.ts`:

| Function Name | Method | Endpoint Path | Role |
| :--- | :--- | :--- | :--- |
| `listProjects` | `GET` | `/api/projects` | Fetch all available directories |
| `createProject` | `POST` | `/api/projects` | Create a new project workspace |
| `getProjectMemory` | `GET` | `/api/memory/{projectId}` | Fetch full project memory payload |
| `addGlossaryTerm` | `POST` | `/api/memory/{projectId}/glossary` | Insert a term mapping |
| `deleteGlossaryTerm` | `DELETE` | `/api/memory/{projectId}/glossary/{srcLang}/{tgtLang}/{term}` | Delete a term mapping |
| `addEntity` | `POST` | `/api/memory/{projectId}/entities` | Add character pronouns/notes |
| `deleteEntity` | `DELETE` | `/api/memory/{projectId}/entities/{entityId}` | Delete character entry |
| `addStyleRule` | `POST` | `/api/memory/{projectId}/style-rules` | Enforce tone/guideline |
| `deleteStyleRule` | `DELETE` | `/api/memory/{projectId}/style-rules/{ruleId}` | Delete style constraint |
| `runTranslate` | `POST` | `/api/translation/translate` | Trigger AI Autopilot pipeline |
| `approveTranslation` | `POST` | `/api/translation/approve/{projectId}/{sessionId}`| Approve draft & promote memory |

---

## 6. Design System & Light/Dark Theming

The layout uses Tailwind utility classes linked to CSS variables defined in `app/globals.css`. 

### Key Custom Theme Colors:
- `bg-themeBg`: Main page background.
- `text-themeText`: Prime text colors.
- `bg-themeCard`: Containers, panels, and forms.
- `border-themeBorder`: Structural grids and dividers.

### Theme Provider usage:
Wrapping components in `ThemeProvider` triggers class shifts (`.dark`) on the root document block. Theme status is consumed via the React hook:
```typescript
import { useTheme } from '@/app/theme-provider'
const { theme, toggleTheme } = useTheme()
```
