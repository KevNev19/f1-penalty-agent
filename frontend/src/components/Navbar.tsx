import React from 'react';

const Navbar: React.FC = () => {
    return (
        <nav className="fixed top-0 left-0 w-full z-50 bg-f1-dark/90 backdrop-blur-md border-b border-f1-red/30 px-6 py-4">
            <div className="max-w-7xl mx-auto flex items-center justify-between">
                {/* Logo Section */}
                <div className="flex items-center space-x-2">
                    <div className="bg-f1-red text-white py-1 px-3 font-bold text-xl f1-slant transform skew-x-[-15deg] flex items-center">
                        <span className="transform skew-x-[15deg]">PitWall</span>
                    </div>
                    <span className="text-white font-bold text-xl tracking-tighter">AI</span>
                </div>

                {/* Navigation Links */}
                <div className="hidden md:flex items-center space-x-8">
                    <a href="#" className="text-f1-silver hover:text-white transition-colors uppercase text-sm font-bold tracking-widest border-b-2 border-transparent hover:border-f1-red pb-1">
                        Regulations
                    </a>
                    <a href="#" className="text-f1-silver hover:text-white transition-colors uppercase text-sm font-bold tracking-widest border-b-2 border-transparent hover:border-f1-red pb-1">
                        Penalties
                    </a>
                    <a href="#" className="text-f1-silver hover:text-white transition-colors uppercase text-sm font-bold tracking-widest border-b-2 border-transparent hover:border-f1-red pb-1">
                        Archive
                    </a>
                </div>

                {/* Call to Action */}
                <div>
                    <button className="bg-f1-red hover:bg-red-700 text-white px-6 py-2 rounded-sm font-bold uppercase text-xs tracking-widest transition-all hover:scale-105 active:scale-95 shadow-lg shadow-f1-red/20">
                        Launch Agent
                    </button>
                </div>
            </div>
        </nav>
    );
};

export default Navbar;
