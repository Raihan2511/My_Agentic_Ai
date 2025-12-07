import React, { useState, useRef, useEffect } from 'react';
import { 
  Send, Bot, User, Loader, Database, FileText, RefreshCw, 
  Upload, TestTube, ChevronLeft, ChevronRight, Moon, Sun, 
  Terminal, PlayCircle, CheckCircle2, Plus, MessageSquare,
  Wifi, WifiOff, LayoutGrid
} from 'lucide-react';

// --- CONFIGURATION ---
const API_BASE = (typeof process !== 'undefined' && process.env && process.env.REACT_APP_API_URL) 
  ? process.env.REACT_APP_API_URL 
  : 'http://localhost:8000';

// Agent Definitions
const AGENTS = {
  TEST: { color: 'text-purple-600', bg: 'bg-purple-100', border: 'border-purple-200', icon: TestTube, label: 'Test Agent', darkColor: 'text-purple-400', darkBg: 'bg-purple-900/30', theme: 'purple' },
  READ: { color: 'text-blue-600', bg: 'bg-blue-100', border: 'border-blue-200', icon: Database, label: 'Read Agent', darkColor: 'text-blue-400', darkBg: 'bg-blue-900/30', theme: 'blue' },
  WRITE: { color: 'text-amber-600', bg: 'bg-amber-100', border: 'border-amber-200', icon: FileText, label: 'Write Agent', darkColor: 'text-amber-400', darkBg: 'bg-amber-900/30', theme: 'amber' },
  SYNC: { color: 'text-emerald-600', bg: 'bg-emerald-100', border: 'border-emerald-200', icon: RefreshCw, label: 'Sync Agent', darkColor: 'text-emerald-400', darkBg: 'bg-emerald-900/30', theme: 'emerald' },
  IMPORT: { color: 'text-rose-600', bg: 'bg-rose-100', border: 'border-rose-200', icon: Upload, label: 'Import Agent', darkColor: 'text-rose-400', darkBg: 'bg-rose-900/30', theme: 'rose' },
  DEFAULT: { color: 'text-slate-600', bg: 'bg-slate-100', border: 'border-slate-200', icon: Bot, label: 'Router', darkColor: 'text-slate-400', darkBg: 'bg-slate-800', theme: 'slate' }
};

// --- MOCK RESPONSE GENERATOR (Fallback) ---
const generateMockResponse = (input) => {
  const lowerInput = input.toLowerCase();
  if (lowerInput.includes('test')) return { response: "Initiating Selenium export sequence...\nSUCCESS.", agent: 'TEST', tool_calls: ['Export_Timetable'] };
  if (lowerInput.includes('sync')) return { response: "Starting full synchronization sequence...", agent: 'SYNC', tool_calls: ['Refresh_RAG_Database'] };
  if (lowerInput.includes('import')) return { response: "Importing 'unitime_batch.xml' to database...", agent: 'IMPORT', tool_calls: ['Import_File_to_Unitime'] };
  if (lowerInput.includes('process') || lowerInput.includes('email')) return { response: "Scanning inbox... Found 1 request. Added to batch.", agent: 'WRITE', tool_calls: ['Read_Email', 'Add_Offering_to_Batch_File'] };
  return { response: "According to the current schedule, CG 101 meets in Room 304.", agent: 'READ', tool_calls: ['Query_Student_Timetable'] };
};

// --- COMPONENTS ---

const TypewriterText = ({ text, onComplete }) => {
  const [displayedText, setDisplayedText] = useState('');
  const indexRef = useRef(0);

  useEffect(() => {
    setDisplayedText('');
    indexRef.current = 0;
    const timer = setInterval(() => {
      setDisplayedText((prev) => {
        if (indexRef.current < text.length) {
          const nextChar = text.charAt(indexRef.current);
          indexRef.current++;
          return prev + nextChar;
        }
        clearInterval(timer);
        if (onComplete) onComplete();
        return prev;
      });
    }, 10);
    return () => clearInterval(timer);
  }, [text, onComplete]);

  return <p className="leading-relaxed whitespace-pre-wrap">{displayedText}</p>;
};

const ToolBlock = ({ tools, isDarkMode }) => {
  if (!tools || tools.length === 0) return null;
  return (
    <div className={`mt-3 mb-2 rounded-md overflow-hidden text-xs font-mono border ${isDarkMode ? 'bg-gray-900 border-gray-700' : 'bg-gray-50 border-gray-200'}`}>
      <div className={`px-3 py-1.5 border-b flex items-center gap-2 ${isDarkMode ? 'bg-gray-800 border-gray-700 text-gray-400' : 'bg-gray-100 border-gray-200 text-gray-500'}`}>
        <Terminal className="w-3 h-3" />
        <span>Tool Execution Log</span>
      </div>
      <div className="p-2 space-y-1">
        {tools.map((tool, idx) => (
          <div key={idx} className="flex items-start gap-2">
            <PlayCircle className="w-3 h-3 mt-0.5 text-green-500 shrink-0" />
            <span className={isDarkMode ? 'text-gray-300' : 'text-gray-700'}>Executed: <span className="font-bold text-blue-500">{tool}</span></span>
          </div>
        ))}
      </div>
    </div>
  );
};

const MessageBubble = ({ msg, isDarkMode }) => {
  const isUser = msg.sender === 'user';
  const isError = msg.isError;
  const agentConfig = AGENTS[msg.agent] || AGENTS.DEFAULT;

  return (
    <div className={`flex gap-4 ${isUser ? 'justify-end' : 'justify-start'} mb-6 group fade-in-up`}>
      {!isUser && (
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center shadow-sm shrink-0 transition-colors duration-300 ${isDarkMode ? agentConfig.darkBg : agentConfig.bg}`}>
          {React.createElement(agentConfig.icon, { className: `w-6 h-6 ${isDarkMode ? agentConfig.darkColor : agentConfig.color}` })}
        </div>
      )}
      <div className={`max-w-2xl w-full`}>
        {!isUser && (
          <div className="flex items-center gap-2 mb-1.5 ml-1">
            <span className={`text-xs font-bold uppercase tracking-wider ${isDarkMode ? agentConfig.darkColor : agentConfig.color}`}>{agentConfig.label}</span>
            <span className={`text-xs ${isDarkMode ? 'text-gray-500' : 'text-gray-400'}`}>• {msg.timestamp}</span>
          </div>
        )}
        <div className={`relative px-5 py-4 rounded-2xl shadow-sm border ${isUser ? 'bg-blue-600 text-white border-blue-600 rounded-tr-sm' : isError ? 'bg-red-50 border-red-200 text-red-800 rounded-tl-sm' : `${isDarkMode ? 'bg-gray-800 border-gray-700 text-gray-100' : 'bg-white border-gray-100 text-gray-800'} rounded-tl-sm`}`}>
          {!isUser && <ToolBlock tools={msg.toolCalls} isDarkMode={isDarkMode} />}
          <div className={isUser ? 'text-white' : ''}>
            {isUser || !msg.isTyping ? <p className="leading-relaxed whitespace-pre-wrap">{msg.text}</p> : msg.text}
          </div>
        </div>
      </div>
      {isUser && (
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-sm shrink-0">
          <User className="w-5 h-5 text-white" />
        </div>
      )}
    </div>
  );
};

// --- MAIN APP ---

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [currentAgent, setCurrentAgent] = useState('DEFAULT');
  const [isSidebarOpen, setSidebarOpen] = useState(true);
  const [isDarkMode, setDarkMode] = useState(false);
  const [isDemoMode, setDemoMode] = useState(false);
  
  const chatEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, isLoading]);
  useEffect(() => { inputRef.current?.focus(); }, []);

  const sendMessage = async (text = input) => {
    if (!text.trim() || isLoading) return;

    const userMsg = { id: Date.now(), sender: 'user', text: text, timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);
    setCurrentAgent('DEFAULT');

    if (isDemoMode) {
      setTimeout(() => { handleResponse(generateMockResponse(text)); }, 1500);
      return;
    }

    try {
      // Prepare history for backend
      const history = messages.map(m => ({
        role: m.sender === 'user' ? 'user' : 'bot',
        content: m.text
      }));

      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, history: history }) // Sending history
      });

      if (!res.ok) throw new Error(`Server error: ${res.status}`);
      const data = await res.json();
      handleResponse(data);

    } catch (error) {
      console.error(error);
      const errorMsg = { id: Date.now() + 1, sender: 'bot', text: 'Backend connection failed. Switching to Demo Mode.', isError: true, agent: 'DEFAULT', timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) };
      setMessages(prev => [...prev, errorMsg]);
      setDemoMode(true);
      setTimeout(() => { handleResponse(generateMockResponse(text)); }, 1000);
    } finally {
      setIsLoading(false);
    }
  };

  const handleResponse = (data) => {
    const detectedAgent = data.agent || 'READ';
    setCurrentAgent(detectedAgent);
    const botMsg = {
      id: Date.now() + 1, sender: 'bot', text: data.response, agent: detectedAgent,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      toolCalls: data.tool_calls || [], isTyping: true
    };
    setMessages(prev => [...prev, botMsg]);
    setIsLoading(false);
  };

  const resetToDashboard = () => {
    setMessages([]);
    setCurrentAgent('DEFAULT');
  };

  const quickActions = [
    { label: 'Check Schedule', query: 'Where is my CG 101 class?', icon: Database, desc: 'Student Query' },
    { label: 'Process Inbox', query: 'Process the new request in the inbox', icon: FileText, desc: 'Admin Task' },
    { label: 'Import Batch', query: 'Import the batch file', icon: Upload, desc: 'System Update' },
    { label: 'Sync Database', query: 'Run the full auto-sync now', icon: RefreshCw, desc: 'Maintenance' },
  ];

  const commandBar = [
    { label: 'Inbox', query: 'Process inbox', icon: FileText },
    { label: 'Import', query: 'Import batch file', icon: Upload },
    { label: 'Sync', query: 'Run sync', icon: RefreshCw },
    { label: 'Test', query: 'Test export', icon: TestTube },
  ];

  const activeAgentConfig = AGENTS[currentAgent] || AGENTS.DEFAULT;

  return (
    <div className={`flex h-screen overflow-hidden transition-colors duration-300 ${isDarkMode ? 'bg-gray-900 text-gray-100' : 'bg-gray-50 text-gray-800'}`}>
      <style>{`@keyframes fadeInUp { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } } .fade-in-up { animation: fadeInUp 0.4s ease-out forwards; }`}</style>

      {/* SIDEBAR */}
      <div className={`${isSidebarOpen ? 'w-64' : 'w-0'} transition-all duration-300 border-r flex flex-col relative ${isDarkMode ? 'bg-gray-900 border-gray-800' : 'bg-white border-gray-200'}`}>
        <div className="p-4 border-b border-opacity-50 flex items-center gap-2 overflow-hidden whitespace-nowrap">
           <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white shrink-0"><Bot size={20} /></div>
           <span className={`font-bold text-lg ${!isSidebarOpen && 'opacity-0'}`}>UniAssist.ai</span>
        </div>
        <div className="p-3 flex-1 overflow-y-auto">
          <button onClick={resetToDashboard} className={`w-full flex items-center gap-2 px-4 py-3 rounded-xl mb-4 transition-all ${isDarkMode ? 'bg-blue-600/20 text-blue-400 hover:bg-blue-600/30' : 'bg-blue-50 text-blue-700 hover:bg-blue-100'}`}>
            <Plus size={18} /><span className="font-medium text-sm">New Session</span>
          </button>
          <div className="space-y-1">
            <p className="px-4 text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Recent</p>
            {['Timetable Update', 'Instructor Prefs', 'Batch Import'].map((item, i) => (
              <button key={i} className={`w-full text-left px-4 py-2.5 rounded-lg text-sm flex items-center gap-3 ${isDarkMode ? 'text-gray-400 hover:bg-gray-800' : 'text-gray-600 hover:bg-gray-100'}`}>
                <MessageSquare size={16} className="opacity-50" /><span className="truncate">{item}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* MAIN CONTENT */}
      <div className="flex-1 flex flex-col min-w-0 relative">
        <button onClick={() => setSidebarOpen(!isSidebarOpen)} className={`absolute top-4 left-4 z-10 p-2 rounded-lg border ${isDarkMode ? 'bg-gray-800 border-gray-700 text-gray-400' : 'bg-white border-gray-200 text-gray-600'}`}>
          {isSidebarOpen ? <ChevronLeft size={18} /> : <ChevronRight size={18} />}
        </button>

        {/* HEADER */}
        <header className={`h-16 border-b flex items-center justify-between px-6 pl-16 ${isDarkMode ? 'bg-gray-900/50 border-gray-800 backdrop-blur-md' : 'bg-white/80 border-gray-200 backdrop-blur-md'}`}>
          <div className="flex items-center gap-4">
            {/* DASHBOARD BUTTON */}
            <button onClick={resetToDashboard} className={`p-2 rounded-lg transition-colors flex items-center gap-2 text-xs font-bold uppercase tracking-wider border ${isDarkMode ? 'bg-gray-800 border-gray-700 text-gray-300 hover:bg-gray-700' : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'}`}>
              <LayoutGrid size={14} /> Dashboard
            </button>
            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs font-semibold transition-colors duration-500 ${isDarkMode ? activeAgentConfig.darkBg + ' ' + activeAgentConfig.darkColor + ' border-transparent' : activeAgentConfig.bg + ' ' + activeAgentConfig.color + ' ' + activeAgentConfig.border}`}>
              {React.createElement(activeAgentConfig.icon, { size: 14 })} {activeAgentConfig.label}
            </div>
            <div onClick={() => setDemoMode(!isDemoMode)} className={`flex items-center gap-1.5 px-2 py-1 rounded cursor-pointer text-[10px] font-bold uppercase border ${isDemoMode ? (isDarkMode ? 'bg-orange-900/30 text-orange-400 border-orange-800' : 'bg-orange-50 text-orange-600 border-orange-200') : (isDarkMode ? 'bg-green-900/30 text-green-400 border-green-800' : 'bg-green-50 text-green-600 border-green-200')}`}>
              {isDemoMode ? <WifiOff size={10} /> : <Wifi size={10} />} {isDemoMode ? 'Demo' : 'Live'}
            </div>
          </div>
          <button onClick={() => setDarkMode(!isDarkMode)} className={`p-2 rounded-lg ${isDarkMode ? 'hover:bg-gray-800 text-yellow-400' : 'hover:bg-gray-100 text-gray-600'}`}>
            {isDarkMode ? <Sun size={20} /> : <Moon size={20} />}
          </button>
        </header>

        {/* MESSAGES */}
        <div className="flex-1 overflow-y-auto px-4 md:px-20 py-8 scroll-smooth">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center fade-in-up">
              <div className={`w-20 h-20 rounded-3xl mb-6 flex items-center justify-center shadow-lg bg-gradient-to-br from-blue-500 to-indigo-600`}><Bot size={40} className="text-white" /></div>
              <h1 className={`text-3xl font-bold mb-3 ${isDarkMode ? 'text-white' : 'text-gray-800'}`}>How can I help today?</h1>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full max-w-2xl mt-8">
                {quickActions.map((action, idx) => (
                  <button key={idx} onClick={() => sendMessage(action.query)} className={`p-4 rounded-xl border text-left transition-all hover:scale-[1.02] ${isDarkMode ? 'bg-gray-800 border-gray-700 hover:bg-gray-750' : 'bg-white border-gray-200 hover:border-blue-300 hover:shadow-md'}`}>
                    <div className="flex items-center gap-3 mb-1">
                      <div className={`p-2 rounded-lg ${isDarkMode ? 'bg-gray-700' : 'bg-blue-50 text-blue-600'}`}>{React.createElement(action.icon, { size: 18 })}</div>
                      <div>
                        <span className={`font-semibold block ${isDarkMode ? 'text-gray-200' : 'text-gray-700'}`}>{action.label}</span>
                        <span className={`text-xs ${isDarkMode ? 'text-gray-500' : 'text-gray-400'}`}>{action.desc}</span>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <>
              {messages.map((msg) => <MessageBubble key={msg.id} msg={msg} isDarkMode={isDarkMode} />)}
              {isLoading && <div className="flex gap-4 justify-start mb-6 animate-pulse"><div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${isDarkMode ? 'bg-gray-800' : 'bg-gray-100'}`}><Bot size={20} className={isDarkMode ? 'text-gray-600' : 'text-gray-400'} /></div><div className="flex items-center gap-2 mt-2"><Loader className="w-4 h-4 animate-spin text-blue-500" /><span className="text-sm text-gray-500">Processing...</span></div></div>}
              <div ref={chatEndRef} />
            </>
          )}
        </div>

        {/* INPUT AREA + COMMAND BAR */}
        <div className={`p-6 pt-2 pb-8 ${isDarkMode ? 'bg-gray-900' : 'bg-gray-50'}`}>
          <div className={`max-w-4xl mx-auto`}>
            
            {/* PERSISTENT COMMAND BAR */}
            {messages.length > 0 && (
               <div className="flex gap-2 mb-3 overflow-x-auto pb-1">
                 {commandBar.map((cmd, idx) => (
                   <button key={idx} onClick={() => sendMessage(cmd.query)} className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${isDarkMode ? 'bg-gray-800 border-gray-700 text-gray-300 hover:bg-gray-700' : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-100'}`}>
                     {React.createElement(cmd.icon, { size: 12 })}
                     {cmd.label}
                   </button>
                 ))}
               </div>
            )}

            <div className={`rounded-2xl shadow-lg border overflow-hidden transition-colors ${isDarkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`}>
               <div className="flex items-end gap-2 p-2">
                  <textarea ref={inputRef} value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } }} placeholder="Ask the University Agent..." disabled={isLoading} rows={1} className={`flex-1 max-h-40 px-4 py-3 bg-transparent border-none focus:ring-0 resize-none text-base scrollbar-hide ${isDarkMode ? 'text-white placeholder-gray-500' : 'text-gray-800 placeholder-gray-400'}`} style={{ minHeight: '52px' }} />
                  <button onClick={() => sendMessage()} disabled={isLoading || !input.trim()} className={`p-3 rounded-xl mb-1 transition-all flex items-center justify-center ${isLoading || !input.trim() ? (isDarkMode ? 'bg-gray-700 text-gray-500' : 'bg-gray-100 text-gray-400') : 'bg-blue-600 text-white hover:bg-blue-700'}`}><Send size={20} /></button>
               </div>
               <div className={`px-4 py-2 border-t text-[10px] flex justify-between ${isDarkMode ? 'border-gray-700 text-gray-500' : 'border-gray-50 text-gray-400'}`}>
                 <span className="flex items-center gap-1"><CheckCircle2 size={10} className="text-green-500" /> System Operational {isDemoMode && '(Simulated)'}</span>
                 <span>Shift + Return for new line</span>
               </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;