# AI Interview Platform - Frontend Structure

## 📁 Project Structure

```
Frontend/
├── src/
│   ├── components/
│   │   ├── ui/
│   │   │   ├── Navbar.jsx          # Navigation bar component
│   │   │   ├── SkillBar.jsx        # Animated skill progress bar
│   │   │   ├── StatusBadge.jsx     # Status badge (Hire/Consider/Reject)
│   │   │   ├── ProgressRing.jsx    # Circular progress indicator
│   │   │   └── Waveform.jsx        # Audio waveform visualization
│   │   ├── interview/              # Interview-specific components (future)
│   │   ├── voice/                  # Voice screening components (future)
│   │   ├── report/                 # Report components (future)
│   │   └── recruiter/              # Recruiter dashboard components (future)
│   ├── pages/
│   │   ├── Landing.jsx             # Landing page with hero section
│   │   ├── Upload.jsx              # Resume upload page
│   │   ├── VoiceScreen.jsx         # Voice screening interface
│   │   ├── Interview.jsx           # Adaptive interview page
│   │   ├── Report.jsx              # Candidate report dashboard
│   │   └── Recruiter.jsx           # Recruiter dashboard
│   ├── design/
│   │   └── styles.css              # Global styles and design system
│   ├── App.jsx                     # Main app component with routing
│   └── main.jsx                    # Entry point
```

## 🎨 Design System

### Colors
- **void**: `#050507` - Deepest background
- **surface**: `#0D0D12` - Card/panel background
- **lift**: `#14141C` - Elevated surface
- **border**: `#1E1E2E` - Subtle borders
- **cyan**: `#00E5FF` - Primary accent (AI pulse)
- **violet**: `#7B61FF` - Secondary accent
- **green**: `#00FF94` - Positive/hire signal
- **amber**: `#FFB547` - Consider/warning
- **red**: `#FF4D6D` - Reject/alert

### Typography
- **Display**: 'Syne' - For headings
- **Mono**: 'JetBrains Mono' - For scores, timers, data
- **Body**: 'DM Sans' - For descriptions, UI copy

### Spacing
Base unit: 4px × scale (4, 8, 12, 16, 24, 32, 48, 64, 96)

## 🚀 Getting Started

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build
```

## 📦 Dependencies

- **React** - UI framework
- **Recharts** - Charts and data visualization
- **Vite** - Build tool

## 🔧 Key Features

1. **Landing Page** - Hero section with animated rings and stats
2. **Resume Upload** - Drag & drop with skill extraction visualization
3. **Voice Screening** - AI avatar with live waveform and skill tracking
4. **Adaptive Interview** - Dynamic depth adjustment with timer
5. **Report Dashboard** - Radar charts, skill cards, AI recommendations
6. **Recruiter Dashboard** - Candidate pipeline with filtering

## 📝 Notes

- All styles are in `src/design/styles.css`
- Components are modular and reusable
- Navigation handled through state in App.jsx
- Ready for backend integration
