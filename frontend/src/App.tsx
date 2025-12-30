import Navbar from './components/Navbar'
import PenaltyAgent from './components/PenaltyAgent'

function App() {
  return (
    <div className="min-h-screen bg-f1-dark text-white pt-24 overflow-x-hidden">
      <Navbar />

      {/* Hero Section */}
      <main className="max-w-7xl mx-auto px-6 py-12">
        <div className="relative">
          {/* Decorative Background Elements */}
          <div className="absolute -top-24 -right-24 w-96 h-96 bg-f1-red/10 rounded-full blur-3xl -z-10 animate-pulse"></div>

          <div className="flex flex-col items-center text-center">
            {/* Left Content */}
            <div className="max-w-4xl">
              <div className="inline-block border-l-4 border-f1-red pl-4 mb-4">
                <span className="text-f1-red font-bold uppercase tracking-[0.2em] text-sm">Official Strategic Assistant</span>
              </div>

              <h1 className="text-6xl md:text-8xl font-black uppercase italic tracking-tighter leading-tight mb-6">
                Master the <br />
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-f1-red to-red-400">
                  Regulations
                </span>
              </h1>

              <p className="text-xl text-f1-silver max-w-2xl mx-auto mb-10 font-medium">
                Real-time analysis of FIA Stewards' decisions, penalty precedents, and race regulations. Powered by PitWallAI.
              </p>
            </div>

            {/* Main Interactive Component */}
            <PenaltyAgent />
          </div>
        </div>
      </main>

      {/* Dynamic Background Grid */}
      <div className="fixed inset-0 pointer-events-none -z-20 opacity-20"
        style={{ backgroundImage: 'linear-gradient(#38383f 1px, transparent 1px), linear-gradient(90deg, #38383f 1px, transparent 1px)', backgroundSize: '40px 40px' }}>
      </div>
    </div>
  )
}

export default App
