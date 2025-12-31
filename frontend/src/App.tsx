import { BrowserRouter, Routes, Route, Link, useNavigate, useLocation } from 'react-router-dom';
import Navbar from './components/Navbar';
import { ChatInterface } from './components/ChatInterface';
import { AdminPage } from './pages/AdminPage';

// Wrapper component to handle back navigation logic
const AdminPageWrapper = () => {
  const navigate = useNavigate();
  return <AdminPage onBack={() => navigate('/')} />;
};

// Home component to isolate verify home view
const Home = () => (
  <>
    <div className="text-center mb-8 animate-fade-in-down px-4">
      <h1 className="text-3xl md:text-5xl font-black italic mb-2 tracking-tighter">
        <span className="text-f1-red">FIA</span> REGULATION <span className="text-white">ASSISTANT</span>
      </h1>
      <p className="text-f1-silver text-sm md:text-lg font-medium max-w-2xl mx-auto">
        Real-time analysis of penalties, regulations, and stewards' decisions.
      </p>
      <div className="mt-4 flex justify-center">
        <span className="text-f1-red font-bold uppercase tracking-[0.2em] text-xs md:text-sm">Official Regulation Assistant</span>
      </div>
    </div>

    <ChatInterface />

    <div className="fixed bottom-4 right-4 z-50 hidden md:block">
      <Link
        to="/admin"
        className="bg-black/80 border border-f1-grey/30 hover:border-f1-red hover:bg-f1-red/10 text-f1-silver text-[10px] font-mono p-2 rounded uppercase tracking-widest backdrop-blur transition-all inline-block"
      >
        System Status
      </Link>
    </div>
  </>
);

function AppContent() {
  const location = useLocation();
  const isChatView = location.pathname === '/';

  return (
    <div className="min-h-screen bg-f1-black text-white bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-f1-grey/20 via-f1-black to-f1-black">
      <Navbar />

      <main className="container mx-auto px-4 pt-24 pb-12">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/admin" element={<AdminPageWrapper />} />
        </Routes>
      </main>

      {isChatView && (
        <footer className="fixed bottom-0 w-full text-center py-4 text-f1-silver/40 text-[10px] pointer-events-none">
          Not officially affiliated with Formula 1 or the FIA. Data for educational purposes only.
        </footer>
      )}

      {/* Dynamic Background Grid */}
      <div className="fixed inset-0 pointer-events-none -z-20 opacity-20"
        style={{ backgroundImage: 'linear-gradient(#38383f 1px, transparent 1px), linear-gradient(90deg, #38383f 1px, transparent 1px)', backgroundSize: '40px 40px' }}>
      </div>
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
