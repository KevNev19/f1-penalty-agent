# PitWallAI Frontend

Modern React frontend for PitWallAI with an F1 broadcast-inspired design.

## 🎨 Design Features

- **F1 Visual Theme** - Authentic racing aesthetics with F1 red (#E10600) accents
- **Radio Message Cards** - Chat styled like team radio communications
- **Glassmorphism Design** - Premium frosted glass effects throughout
- **Track Background** - Immersive racing circuit backdrop
- **Responsive Layout** - Single-viewport design that works on all devices

## 🛠️ Tech Stack

- **React 18** - Modern React with hooks and functional components
- **TypeScript** - Type-safe development
- **Vite** - Lightning-fast development server and builds
- **TailwindCSS** - Utility-first CSS framework
- **React Markdown** + **remark-gfm** - Formatted AI responses
- **React Router DOM** - Client-side routing

## 📁 Project Structure

```
frontend/
├── public/
│   ├── bg-track.png       # Circuit background image
│   ├── logo-pw.png        # Main PitWallAI logo
│   └── favicon.png        # Browser favicon
├── src/
│   ├── components/
│   │   ├── ChatInterface.tsx  # Main chat component
│   │   └── Navbar.tsx         # Navigation header
│   ├── services/
│   │   └── api.ts            # API client for backend
│   ├── App.tsx               # Main app with routing
│   ├── index.css             # Global styles + Tailwind
│   └── main.tsx              # Entry point
├── index.html                # HTML template
├── tailwind.config.js        # Tailwind configuration
├── vite.config.ts            # Vite configuration
└── package.json              # Dependencies
```

## 🚀 Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev
# Available at http://localhost:5173

# Build for production
npm run build

# Preview production build
npm run preview
```

### Environment Variables

Create a `.env` file in the frontend directory:

```env
# API Backend URL (defaults to http://localhost:8000)
VITE_API_BASE_URL=http://localhost:8000
```

## 🎯 Components

### ChatInterface

Main chat component featuring:
- F1-styled message cards with "DRIVER" and "RACE ENGINEER" labels
- Real-time loading indicators with bouncing dots
- Markdown rendering for AI responses
- Source citations with clickable links
- Scrollable message history

### Navbar

Top navigation with:
- PitWallAI logo
- Responsive design
- Glassmorphism background effect

### Home

Landing page with:
- Centered logo display
- Tagline: "Your AI Race Engineer"
- Full-height chat interface

## 🎨 Styling

### Color Palette

| Token | Value | Usage |
|-------|-------|-------|
| `f1-red` | `#E10600` | Primary accent, buttons, borders |
| `f1-black` | `#15151E` | Backgrounds |
| `f1-grey` | `#38383F` | Secondary backgrounds, borders |
| `f1-silver` | `#F0F0F0` | Text on dark backgrounds |

### Key Classes

```css
/* Frosted glass effect */
.backdrop-blur-md .bg-white/10 .border-white/20

/* Message cards */
.rounded-lg .shadow-lg .border-l-4

/* Input styling */
.rounded-full .focus:ring-f1-red
```

## 🔌 API Integration

The frontend communicates with the backend via `src/services/api.ts`:

```typescript
// Ask a question
const response = await api.askQuestion("What is the penalty for track limits?", history);

// Health check
const health = await api.checkHealth();
```

## 📱 Responsive Design

- **Mobile**: Full-width layout, compact message cards
- **Tablet**: Slightly larger spacing
- **Desktop**: Max-width container (4xl), comfortable reading width

## 🧪 Development

```bash
# Lint code
npm run lint

# Type check
npx tsc --noEmit

# Build and analyze bundle
npm run build
```

## 📄 License

Part of the PitWallAI project - GPL v3.0
