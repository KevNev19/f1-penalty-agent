import React, { createContext, useContext, useState, type ReactNode } from 'react';
import type { SourceInfo } from '../services/api';

export interface Message {
    role: 'user' | 'agent';
    content: string;
    sources?: SourceInfo[];
    isLoading?: boolean;
}

interface ChatContextType {
    messages: Message[];
    setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
    clearMessages: () => void;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

export const ChatProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const [messages, setMessages] = useState<Message[]>([]);

    const clearMessages = () => setMessages([]);

    return (
        <ChatContext.Provider value={{ messages, setMessages, clearMessages }}>
            {children}
        </ChatContext.Provider>
    );
};

export const useChat = (): ChatContextType => {
    const context = useContext(ChatContext);
    if (!context) {
        throw new Error('useChat must be used within a ChatProvider');
    }
    return context;
};
