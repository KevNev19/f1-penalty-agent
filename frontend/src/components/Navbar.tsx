import React from 'react';
import { Link, useLocation } from 'react-router-dom';

const Navbar: React.FC = () => {
    const location = useLocation();

    return (
        <nav className="fixed top-0 left-0 w-full z-50 bg-gradient-to-r from-f1-dark/98 via-f1-dark/95 to-f1-dark/98 backdrop-blur-lg border-b border-f1-red/20 px-4 md:px-6 py-3 shadow-2xl">
            <div className="max-w-7xl mx-auto flex items-center justify-between">
                {/* Logo Section - Same style as main header */}
                <Link to="/" className="flex items-center group">
                    <img
                        src="/favicon.png"
                        alt="PitWallAI Icon"
                        className="relative z-10 h-8 md:h-10 w-auto group-hover:scale-110 transition-transform duration-300 drop-shadow-[0_0_8px_rgba(255,10,10,0.3)] -mr-2 md:-mr-3"
                    />
                    <span className="text-base md:text-lg font-black italic tracking-tight text-white group-hover:text-f1-red transition-colors duration-300 translate-y-0.5 -ml-1 md:-ml-2">
                        PitWall
                    </span>
                    <span className="text-base md:text-lg font-black italic tracking-tight text-f1-red group-hover:text-white transition-colors duration-300 translate-y-0.5">
                        AI
                    </span>
                </Link>

                {/* Navigation Links */}
                <div className="flex items-center gap-1 md:gap-4">
                    <Link
                        to="/"
                        className={`px-3 py-2 text-xs md:text-sm font-semibold uppercase tracking-wider rounded-md transition-all duration-200 ${location.pathname === '/'
                            ? 'text-white bg-f1-red/20 border border-f1-red/40'
                            : 'text-f1-silver hover:text-white hover:bg-white/5'
                            }`}
                    >
                        Assistant
                    </Link>
                    <Link
                        to="/admin"
                        className={`px-3 py-2 text-xs md:text-sm font-semibold uppercase tracking-wider rounded-md transition-all duration-200 ${location.pathname === '/admin'
                            ? 'text-white bg-f1-red/20 border border-f1-red/40'
                            : 'text-f1-silver hover:text-white hover:bg-white/5'
                            }`}
                    >
                        Status
                    </Link>
                </div>
            </div>
        </nav>
    );
};

export default Navbar;

