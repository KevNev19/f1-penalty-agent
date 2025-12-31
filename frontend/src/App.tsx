import { BrowserRouter, Routes, Route, useNavigate } from 'react-router-dom';
import Navbar from './components/Navbar';
import { ChatInterface } from './components/ChatInterface';
import { AdminPage } from './pages/AdminPage';

// Wrapper component to handle back navigation logic
const AdminPageWrapper = () => {
  const navigate = useNavigate();
  return <AdminPage onBack={() => navigate('/')} />;
};

// Home component - compact header + full-height chat
const Home = () => (
  <div className="flex flex-col h-full overflow-hidden">
    {/* Hero Header - Icon + Styled Text Logo */}
    <div className="text-center py-4 px-4 flex-shrink-0">
      <div className="flex items-center justify-center">
        {/* Logo matching logo-pw.png: icon on left overlapping the P */}
        <div className="relative flex items-center">
          {/* Glow effect */}
          <div className="absolute left-0 top-1/2 -translate-y-1/2 blur-2xl opacity-40 bg-f1-red w-28 h-28 md:w-40 md:h-40 rounded-full" />

          {/* Icon on left - BIGGER, overlapping into the text */}
          <img
            src="/favicon.png"
            alt="PitWallAI Icon"
            className="relative z-20 h-20 md:h-28 lg:h-36 w-auto drop-shadow-[0_0_20px_rgba(255,10,10,0.5)] -mr-6 md:-mr-10 lg:-mr-12"
          />

          {/* PitWall as one word - shifted down and left to hug the earpiece */}
          <span className="text-2xl md:text-4xl lg:text-5xl font-black italic tracking-tight text-white drop-shadow-[0_0_15px_rgba(255,255,255,0.3)] translate-y-3 -ml-5 md:-ml-7">
            PitWall
          </span>

          {/* AI in red */}
          <span className="text-2xl md:text-4xl lg:text-5xl font-black italic tracking-tight text-f1-red drop-shadow-[0_0_15px_rgba(255,10,10,0.5)] translate-y-3">
            AI
          </span>
        </div>
      </div>
      <p className="text-white/60 text-xs md:text-sm font-semibold tracking-[0.3em] uppercase mt-1">
        Official AI Strategic Assistant
      </p>
    </div>

    {/* Chat takes remaining space */}
    <div className="flex-1 min-h-0 px-2 md:px-4 pb-2">
      <ChatInterface />
    </div>
  </div>
);


function AppContent() {

  return (
    <div className="min-h-screen text-white relative">
      {/* F1 Track Background */}
      <div
        className="fixed inset-0 -z-30 bg-cover bg-center bg-no-repeat"
        style={{ backgroundImage: 'url(/bg-track.png)' }}
      />
      {/* Dark overlay for readability */}
      <div className="fixed inset-0 -z-20 bg-gradient-to-b from-black/70 via-black/50 to-black/80" />

      <Navbar />

      <main className="pt-16 h-screen overflow-hidden">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/admin" element={<AdminPageWrapper />} />
        </Routes>
      </main>


    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AppContent />
    </BrowserRouter>
  );
}

export default App;
