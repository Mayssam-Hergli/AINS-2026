import React, { useState, useRef, useEffect } from "react";
import { useAuth } from '../context/AuthContext';
import { useActiveProfile } from '../hooks/useActiveProfile';
import { useLang } from '../context/LanguageContext';
import { roadmapApi } from '../api/roadmap';
import { Send, Bot, User, Sparkles } from "lucide-react";

export default function AssistantPage() {
  const { token } = useAuth();
  const { profile } = useActiveProfile();
  const { isAr } = useLang();

  // --- Chat States ---
  const [chatMessages, setChatMessages] = useState([
    { 
      role: "assistant", 
      content: "Bonjour ! Je suis votre conseiller virtuel. Je connais votre diagnostic, vos scores et vos points faibles. Comment puis-je vous aider aujourd'hui ?" 
    }
  ]);
  const [chatInput, setChatInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  
  // Ref for auto-scrolling to the latest message
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  async function handleSendMessage(e) {
    if (e) e.preventDefault();
    if (!chatInput.trim() || isSending || !profile?.id) return;

    const userText = chatInput.trim();
    setChatInput("");
    setIsSending(true);
    
    // Add user's message to the UI instantly
    setChatMessages((prev) => [...prev, { role: "user", content: userText }]);

    try {
      // Using the dedicated askLLM endpoint we configured for broad questions
      const res = await roadmapApi.askLLM(token, {
        profileId: profile.id,
        question: userText
      });

      if (res && res.status === "success") {
        setChatMessages((prev) => [...prev, { role: "assistant", content: res.data.reply }]);
      } else {
        setChatMessages((prev) => [...prev, { role: "assistant", content: "Désolé, une erreur est survenue côté serveur." }]);
      }
    } catch (err) {
      setChatMessages((prev) => [...prev, { role: "assistant", content: "Impossible de joindre l'assistant. Vérifiez votre connexion ou réessayez plus tard." }]);
    } finally {
      setIsSending(false);
    }
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6 py-8 px-4">
      {/* Header section */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Sparkles className="text-amber-500" size={24} />
          Assistant
        </h1>
        <p className="text-gray-500 text-sm mt-1">
          Assistant conversationnel trilingue (FR / AR / Darija)
        </p>
      </div>

      <div className="bg-amber-50 border border-amber-200 rounded-xl px-5 py-4 text-sm text-amber-800">
        <strong>Contexte Actif</strong> — L'assistant est ancré sur votre profil, votre diagnostic récent et vos scores. Il vous fournira des conseils personnalisés selon votre stade de maturité.
      </div>

      {/* Chat Interface */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden flex flex-col" style={{ height: "60vh", minHeight: "500px" }}>
        
        {/* Chat Header */}
        <div className="px-5 py-4 border-b border-gray-100 bg-gray-50 flex items-center justify-between">
          <p className="text-sm font-medium text-gray-700">Conversation en direct</p>
          <span className="flex items-center gap-2 text-xs font-medium text-emerald-600 bg-emerald-50 px-2 py-1 rounded-full border border-emerald-100">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            En ligne
          </span>
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-5 flex flex-col gap-4 bg-[#F9FAFB]">
          {chatMessages.map((msg, idx) => {
            const isUser = msg.role === "user";
            return (
              <div key={idx} className={`flex gap-3 max-w-[85%] ${isUser ? "ml-auto flex-row-reverse" : "mr-auto"}`}>
                <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${isUser ? "bg-primary-600 text-white" : "bg-emerald-100 text-emerald-700"}`}>
                  {isUser ? <User size={16} /> : <Bot size={18} />}
                </div>
                <div className={`px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
                  isUser 
                    ? "bg-primary-600 text-white rounded-tr-none" 
                    : "bg-white border border-gray-200 text-gray-800 rounded-tl-none shadow-sm"
                }`}>
                  {msg.content}
                </div>
              </div>
            );
          })}
          
          {/* Loading Indicator */}
          {isSending && (
            <div className="flex gap-3 max-w-[85%] mr-auto">
              <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 bg-emerald-100 text-emerald-700">
                <Bot size={18} />
              </div>
              <div className="px-4 py-3 rounded-2xl text-sm bg-white border border-gray-200 text-gray-500 rounded-tl-none shadow-sm flex items-center gap-2">
                <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }}></span>
                <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }}></span>
                <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }}></span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="p-4 bg-white border-t border-gray-100">
          <form onSubmit={handleSendMessage} className="flex gap-3">
            <input
              type="text"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              disabled={isSending}
              className="flex-1 border border-gray-300 focus:border-primary-500 focus:ring-2 focus:ring-primary-200 rounded-xl px-4 py-3 text-sm bg-gray-50 text-gray-900 transition-all outline-none disabled:opacity-60"
              placeholder="Posez votre question en français, arabe ou darija..."
            />
            <button
              type="submit"
              disabled={!chatInput.trim() || isSending}
              className="bg-primary-600 hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white px-5 py-3 rounded-xl text-sm font-medium transition-colors flex items-center justify-center"
            >
              <Send size={18} />
            </button>
          </form>
        </div>
        
      </div>
    </div>
  );
}