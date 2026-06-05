# DRS v3 - Premium Translation Workspace UI

A state-of-the-art dark mode translation workspace interface for Document Revision & Steering Hub, featuring glassmorphism design with violet/cyan accents, dual-pane editor, AI copilot, and glossary management.

## Features

- **Premium Dark Theme**: Deep slate/indigo palette with glowing violet/cyan accents
- **Triple-Panel Workspace**: Left sidebar (project explorer & glossary), center dual-pane editor, right AI copilot
- **Text & Visual Modes**: Toggle between Japanese source text and visual document preview
- **Memory Management**: Context-aware style rules and terminology matches
- **AI Variants**: Multiple translation suggestions with confidence scores
- **QA Reporting**: Automated typesetting and consistency checking
- **Glossary Promotion**: Submit proposed terms to the database with one click
- **Glassmorphism UI**: Semi-transparent backgrounds with backdrop blur effects

## Getting Started

### Prerequisites
- Node.js 18+ 
- pnpm (recommended) or npm

### Installation

```bash
cd drs-v3-ui
pnpm install
# or
npm install
```

### Running the Development Server

```bash
pnpm dev
# or
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

## Project Structure

```
drs-v3-ui/
├── app/
│   ├── globals.css          # Global styles with glassmorphism effects
│   ├── layout.tsx           # Root layout
│   └── page.tsx             # Main workspace page
├── components/
│   ├── TopNavigation.tsx    # Header with project selector & user profile
│   ├── LeftSidebar.tsx      # Files & glossary explorer
│   ├── CenterPanel.tsx      # Dual-pane editor (source & translation)
│   └── RightPanel.tsx       # AI copilot & approval gate
├── tailwind.config.ts       # Tailwind configuration with custom colors
├── next.config.mjs          # Next.js configuration
└── package.json             # Dependencies
```

## Technology Stack

- **React 18** - UI framework
- **Next.js 15** - React framework
- **Tailwind CSS** - Utility-first styling
- **Lucide Icons** - Icon library
- **TypeScript** - Type safety

## Customization

### Colors
Edit `tailwind.config.ts` to adjust the color palette:
- `background`: Main background color
- `accent-violet`: Primary accent
- `accent-cyan`: Secondary accent
- `accent-purple`: Tertiary accent

### Theme
Modify `app/globals.css` for glassmorphism effects, shadows, and gradients.

## License

MIT
