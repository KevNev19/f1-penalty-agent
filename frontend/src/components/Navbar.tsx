import React from 'react';
import { Link, useLocation } from 'react-router-dom';

const Navbar: React.FC = () => {
    const location = useLocation();

    return (
        <nav className="fixed top-0 left-0 w-full z-50 bg-f1-black/95 backdrop-blur-md border-b border-f1-red/30 px-6 py-4 shadow-lg">
            <div className="max-w-7xl mx-auto flex items-center justify-between">
                {/* Logo Section */}
                <Link to="/" className="flex items-center space-x-2 group">
                    <div className="bg-f1-red text-white py-1 px-3 font-bold text-xl f1-slant transform skew-x-[-15deg] flex items-center group-hover:bg-red-600 transition-colors">
                        <span className="transform skew-x-[15deg]">PitWall</span>
                    </div>
                    <span className="text-white font-bold text-xl tracking-tighter">AI</span>
                </Link>

                {/* Navigation Links */}
                <div className="flex items-center space-x-6">
                    <Link
                        to="/"
                        className={`text-sm font-bold uppercase tracking-widest transition-all hover:text-white ${location.pathname === '/' ? 'text-white border-b-2 border-f1-red' : 'text-f1-silver border-b-2 border-transparent'}`}
                    >
                        Assistant
                    </Link>
                    <Link
                        to="/admin"
                        className={`text-sm font-bold uppercase tracking-widest transition-all hover:text-white ${location.pathname === '/admin' ? 'text-white border-b-2 border-f1-red' : 'text-f1-silver border-b-2 border-transparent'}`}
                    >
                        System Status
                    </Link>
                </div>
            </div>
        </nav>
    );
};

export default Navbar;
