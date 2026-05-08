import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import {
  Send,
  LogOut,
  Shield,
  Terminal,
  User as UserIcon,
  Activity,
  ChevronRight,
  Loader2,
  Lock,
  MessageSquare,
  AlertTriangle,
  Mail,
  History,
  PlusCircle,
  Save,
  Key,
  FileText,
  Target,
  Trophy,
  Home,
  UserCheck
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const API_BASE_URL = 'http://localhost:8000';

function App() {
  // --- AUTH STATES ---
  const [user, setUser] = useState(JSON.parse(localStorage.getItem('user')) || null);
  const [authView, setAuthView] = useState('login'); // 'login' or 'register'
  const [authEmail, setAuthEmail] = useState('');
  const [authPassword, setAuthPassword] = useState('');

  // Registration Profile Fields
  const [regFaction, setRegFaction] = useState('USEC');
  const [regLevel, setRegLevel] = useState(1);
  const [regHideout, setRegHideout] = useState('Básico');
  const [regPlaystyle, setRegPlaystyle] = useState('Dinamico');

  const [authError, setAuthError] = useState('');
  const [isAuthLoading, setIsAuthLoading] = useState(false);

  // --- CHAT STATES ---
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [timer, setTimer] = useState(0);
  const [threadId, setThreadId] = useState(Math.random().toString(36).substring(7));
  const [savedConversations, setSavedConversations] = useState([]);
  const [currentConvId, setCurrentConvId] = useState(null);
  const [isSaving, setIsSaving] = useState(false);

  const chatEndRef = useRef(null);

  // --- EFFECTS ---
  useEffect(() => {
    if (user) {
      fetchSavedConversations();
    }
  }, [user]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // --- AUTH FUNCTIONS ---
  const handleRegister = async (e) => {
    e.preventDefault();
    setAuthError('');
    setIsAuthLoading(true);
    try {
      await axios.post(`${API_BASE_URL}/register`, {
        email: authEmail,
        password: authPassword,
        faction: regFaction,
        level: parseInt(regLevel),
        hideout_progress: regHideout,
        playstyle: regPlaystyle
      });
      setAuthView('login');
      setAuthError('Registro completado. Ahora inicia sesión.');
    } catch (error) {
      setAuthError(error.response?.data?.detail || 'Error en el registro');
    } finally {
      setIsAuthLoading(false);
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setAuthError('');
    setIsAuthLoading(true);
    try {
      const response = await axios.post(`${API_BASE_URL}/login`, {
        email: authEmail,
        password: authPassword
      });
      const userData = {
        token: response.data.access_token,
        id: response.data.user_id,
        email: authEmail,
        profile: response.data.profile
      };
      localStorage.setItem('user', JSON.stringify(userData));
      setUser(userData);
    } catch (error) {
      setAuthError(error.response?.data?.detail || 'Error en el login');
    } finally {
      setIsAuthLoading(false);
    }
  };

  const handleAppLogout = () => {
    localStorage.removeItem('user');
    setUser(null);
    setMessages([]);
    setSavedConversations([]);
  };

  // --- CONVERSATION FUNCTIONS ---
  const fetchSavedConversations = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/conversations`, {
        headers: { Authorization: `Bearer ${user.token}` }
      });
      setSavedConversations(response.data);
    } catch (error) {
      console.error("Error fetching conversations:", error);
    }
  };

  const saveCurrentConversation = async () => {
    if (messages.length === 0 || isSaving) return;
    setIsSaving(true);
    try {
      const firstUserMsg = messages.find(m => m.role === 'user');
      const title = firstUserMsg ? firstUserMsg.content.substring(0, 30) + "..." : "Conversación Nueva";

      const response = await axios.post(`${API_BASE_URL}/conversations`, {
        title,
        messages,
        thread_id: threadId
      }, {
        headers: { Authorization: `Bearer ${user.token}` }
      });

      await fetchSavedConversations();
      setCurrentConvId(response.data.id);

      // Visual feedback
      setTimeout(() => setIsSaving(false), 2000);
    } catch (error) {
      console.error("Error saving conversation:", error);
      setIsSaving(false);
    }
  };

  const loadConversation = (conv) => {
    setMessages(conv.messages);
    setCurrentConvId(conv.id);
    setThreadId(conv.thread_id || Math.random().toString(36).substring(7));
  };

  const startNewChat = () => {
    setMessages([]);
    setThreadId(Math.random().toString(36).substring(7));
    setCurrentConvId(null);
  };

  // --- CHAT FUNCTIONS ---
  const sendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMsg = { id: Date.now(), role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);
    setTimer(0);

    const startTime = Date.now();
    const interval = setInterval(() => {
      setTimer((Date.now() - startTime) / 1000);
    }, 100);

    try {
      const response = await axios.post(`${API_BASE_URL}/chat`, {
        message: input,
        thread_id: threadId,
        user_id: user?.id
      });

      clearInterval(interval);
      const endTime = Date.now();
      const duration = (endTime - startTime) / 1000;

      const sherpaMsg = {
        id: Date.now() + 1,
        role: 'sherpa',
        content: response.data.response,
        duration: duration.toFixed(2)
      };
      setMessages(prev => [...prev, sherpaMsg]);
    } catch (error) {
      clearInterval(interval);
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        role: 'sherpa',
        content: 'Error de conexión. Inténtalo de nuevo.'
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  // --- VIEWS ---
  if (!user) {
    return (
      <div className="login-overlay">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="login-card"
        >
          <div className="flex items-center gap-3 mb-6">
            <Shield size={32} className="text-accent-color" />
            <h2>{authView === 'login' ? 'Acceso al Búnker' : 'Reclutamiento'}</h2>
          </div>

          <form onSubmit={authView === 'login' ? handleLogin : handleRegister}>
            <div className="input-group">
              <label><Mail size={12} className="inline mr-1" /> Correo Electrónico</label>
              <input
                type="email"
                placeholder="operador@tarkov.com"
                value={authEmail}
                onChange={(e) => setAuthEmail(e.target.value)}
                required
              />
            </div>
            <div className="input-group">
              <label><Key size={12} className="inline mr-1" /> Contraseña</label>
              <input
                type="password"
                placeholder="********"
                value={authPassword}
                onChange={(e) => setAuthPassword(e.target.value)}
                required
              />
            </div>

            {authView === 'register' && (
              <div className="grid grid-cols-2 gap-4 mb-6">
                <div className="input-group !mb-0">
                  <label>Facción</label>
                  <select value={regFaction} onChange={(e) => setRegFaction(e.target.value)} className="select-industrial">
                    <option value="BEAR">BEAR</option>
                    <option value="USEC">USEC</option>
                  </select>
                </div>
                <div className="input-group !mb-0">
                  <label>Nivel (1-99)</label>
                  <input
                    type="number"
                    min="1"
                    max="99"
                    value={regLevel}
                    onChange={(e) => setRegLevel(e.target.value)}
                    className="!p-2"
                    required
                  />
                </div>
                <div className="input-group !mb-0">
                  <label>Hideout</label>
                  <select value={regHideout} onChange={(e) => setRegHideout(e.target.value)} className="select-industrial">
                    <option value="Básico">Básico</option>
                    <option value="Intermedio">Intermedio</option>
                    <option value="Avanzado">Avanzado</option>
                  </select>
                </div>
                <div className="input-group !mb-0">
                  <label>Estilo de Juego</label>
                  <select value={regPlaystyle} onChange={(e) => setRegPlaystyle(e.target.value)} className="select-industrial">
                    <option value="Agresivo pvp">Agresivo PvP</option>
                    <option value="Looter">Looter</option>
                    <option value="Orientado a quests">Quests</option>
                    <option value="Rateador">Rateador</option>
                    <option value="Pasivo pve">Pasivo PvE</option>
                    <option value="Dinamico">Dinámico</option>
                  </select>
                </div>
              </div>
            )}

            {authError && <div className="text-danger text-[10px] mb-4 uppercase tracking-tighter">{authError}</div>}

            <button type="submit" className="btn-primary" disabled={isAuthLoading}>
              {isAuthLoading ? <Loader2 size={18} className="animate-spin" /> : <Terminal size={18} />}
              {authView === 'login' ? 'Entrar al Sistema' : 'Finalizar Registro'}
            </button>
          </form>

          <div className="mt-8 text-center">
            <button
              onClick={() => {
                setAuthView(authView === 'login' ? 'register' : 'login');
                setAuthError('');
              }}
              className="btn-link-industrial"
            >
              {authView === 'login' ? '[ RECLUTAR NUEVO OPERADOR ]' : '[ REGRESAR AL ACCESO ]'}
            </button>
          </div>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="app-container">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="app-title">Tarkov Sherpa</div>
          <div className="text-[10px] text-accent-color/60 font-mono tracking-widest uppercase mb-1">Sector: Norvinsk</div>
          <div className="text-[9px] text-secondary font-mono truncate opacity-50">{user.email}</div>
        </div>

        <div className="sidebar-content">
          {/* Profile Status */}
          <div className="mb-8">
            <h3 className="sidebar-label">
              <UserCheck size={14} className="text-accent-color" /> Perfil PMC
            </h3>
            <div className="space-y-3">
              <div className="stat-card">
                <div className="flex justify-between items-center mb-2">
                  <span className="stat-label flex items-center gap-1"><Trophy size={10} /> Nivel</span>
                  <span className="stat-value text-xs">{user.profile?.level}</span>
                </div>
                <div className="level-bar">
                  <div className="level-progress" style={{ width: `${(user.profile?.level / 79) * 100}%` }}></div>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div className="p-2 bg-black/40 border border-border-color rounded">
                  <div className="stat-label mb-1">Facción</div>
                  <div className="text-[10px] font-bold text-accent-color">{user.profile?.faction}</div>
                </div>
                <div className="p-2 bg-black/40 border border-border-color rounded">
                  <div className="stat-label mb-1">Playstyle</div>
                  <div className="text-[10px] font-bold text-accent-color truncate">{user.profile?.playstyle}</div>
                </div>
              </div>
              <div className="p-2 bg-black/40 border border-border-color rounded">
                <div className="stat-label mb-1">Hideout</div>
                <div className="text-[10px] font-bold text-accent-green">{user.profile?.hideout_progress}</div>
              </div>
            </div>
          </div>

          {/* Saved Chats */}
          <div className="mb-8">
            <div className="flex items-center justify-between mb-4">
              <h3 className="sidebar-label !mb-0">
                <History size={14} className="text-accent-color" /> Archivos
              </h3>
              <button onClick={startNewChat} className="text-accent-color hover:text-white transition-colors">
                <PlusCircle size={16} />
              </button>
            </div>
            <div className="space-y-1">
              {savedConversations.map(conv => (
                <button
                  key={conv.id}
                  onClick={() => loadConversation(conv)}
                  className={`conv-item ${currentConvId === conv.id ? 'active' : ''}`}
                >
                  <FileText size={12} className="conv-item-icon" />
                  <span className="truncate">{conv.title}</span>
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="sidebar-footer">
          <button onClick={handleAppLogout} className="btn-danger">
            <LogOut size={14} /> Finalizar Despliegue
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="main-content">
        <div className="chat-window">
          {messages.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center text-center p-8 opacity-50">
              <Shield size={64} className="mb-4 text-accent-color" />
              <h2 className="text-xl font-bold uppercase tracking-[0.3em] mb-2">Sherpa Online</h2>
              <p className="text-xs text-secondary max-w-xs">Preparado para el despliegue. Analizando perfil {user.profile?.faction} Nvl.{user.profile?.level}.</p>
            </div>
          )}
          <AnimatePresence initial={false}>
            {messages.map((msg) => (
              <motion.div
                key={msg.id}
                initial={{ opacity: 0, x: msg.role === 'user' ? 20 : -20 }}
                animate={{ opacity: 1, x: 0 }}
                className={`message ${msg.role}`}
              >
                <div className="message-header">{msg.role === 'user' ? 'Operador' : 'Sombra-1'}</div>
                <div className="message-content">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                </div>
                {msg.role === 'sherpa' && msg.duration && (
                  <div className="response-timer">
                    <Activity size={10} /> LATENCIA: {msg.duration}s
                  </div>
                )}
              </motion.div>
            ))}
          </AnimatePresence>
          {isLoading && (
            <div className="message sherpa">
              <div className="message-header">Sombra-1</div>
              <div className="loading-spinner">
                <div className="dot"></div>
                <div className="dot" style={{ animationDelay: '0.2s' }}></div>
                <div className="dot" style={{ animationDelay: '0.4s' }}></div>
              </div>
              <div className="response-timer mt-2">
                <Loader2 size={10} className="animate-spin" /> PROCESANDO: {timer.toFixed(1)}s
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        <div className="input-area">
          {messages.length > 0 && !currentConvId && (
            <button
              onClick={saveCurrentConversation}
              className={`btn-save-compact ${isSaving ? 'bg-accent-green !text-white' : ''}`}
              title="Guardar Conversación"
              disabled={isSaving}
            >
              {isSaving ? <UserCheck size={16} /> : <Save size={16} />}
            </button>
          )}
          <form onSubmit={sendMessage} className="flex w-full gap-0 border-t border-border-color bg-black">
            <input
              className="chat-input !border-none !bg-transparent flex-1 min-w-0"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Escribe tu mensaje..."
            />
            <button type="submit" className="send-btn !h-full !w-16 !bg-accent-color !text-black hover:!bg-white" disabled={isLoading || !input.trim()}>
              {isLoading ? <Loader2 className="animate-spin" /> : <Send size={20} />}
            </button>
          </form>
        </div>
      </main>
    </div>
  );
}

export default App;
