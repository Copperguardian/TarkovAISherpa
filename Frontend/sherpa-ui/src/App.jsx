import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { 
  Send, 
  LogOut, 
  Shield, 
  Terminal, 
  User, 
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
  FileText
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
  const [authError, setAuthError] = useState('');
  const [isAuthLoading, setIsAuthLoading] = useState(false);

  // --- TRACKER STATES ---
  const [token, setToken] = useState(localStorage.getItem('tarkov_token') || '');
  const [showTrackerLogin, setShowTrackerLogin] = useState(!localStorage.getItem('tarkov_token'));
  const [tempToken, setTempToken] = useState('');
  const [isValidating, setIsValidating] = useState(false);
  const [trackerError, setTrackerError] = useState('');
  const [userProgress, setUserProgress] = useState(null);

  // --- CHAT STATES ---
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [timer, setTimer] = useState(0);
  const [timerInterval, setTimerInterval] = useState(null);
  const [threadId, setThreadId] = useState(Math.random().toString(36).substring(7));
  const [savedConversations, setSavedConversations] = useState([]);
  const [currentConvId, setCurrentConvId] = useState(null);
  
  const chatEndRef = useRef(null);

  // --- EFFECTS ---
  useEffect(() => {
    if (user && token) {
      fetchUserProgress();
    }
    if (user) {
      fetchSavedConversations();
    }
  }, [user, token]);

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
        password: authPassword
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
        email: authEmail
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
    localStorage.removeItem('tarkov_token');
    setUser(null);
    setToken('');
    setMessages([]);
    setSavedConversations([]);
  };

  // --- TRACKER FUNCTIONS ---
  const fetchUserProgress = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/tracker/progress`, {
        params: { token }
      });
      setUserProgress(response.data);
    } catch (error) {
      console.error("Error fetching progress:", error);
      if (error.response?.status === 401) {
        setToken('');
        localStorage.removeItem('tarkov_token');
      }
    }
  };

  const handleTrackerLogin = async (e) => {
    e.preventDefault();
    setTrackerError('');
    if (!tempToken.trim()) return;
    setIsValidating(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/tracker/progress`, {
        params: { token: tempToken }
      });
      localStorage.setItem('tarkov_token', tempToken);
      setToken(tempToken);
      setUserProgress(response.data);
      setShowTrackerLogin(false);
    } catch (error) {
      setTrackerError('Token de TarkovTracker inválido.');
    } finally {
      setIsValidating(false);
    }
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
    if (messages.length === 0) return;
    try {
      const title = messages[0].content.substring(0, 30) + "...";
      await axios.post(`${API_BASE_URL}/conversations`, {
        title,
        messages,
        thread_id: threadId
      }, {
        headers: { Authorization: `Bearer ${user.token}` }
      });
      fetchSavedConversations();
    } catch (error) {
      console.error("Error saving conversation:", error);
    }
  };

  const loadConversation = (conv) => {
    setMessages(conv.messages);
    setCurrentConvId(conv.id);
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
    setTimerInterval(interval);

    try {
      const response = await axios.post(`${API_BASE_URL}/chat`, {
        message: input,
        thread_id: threadId,
        tarkov_token: token,
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
      setTimerInterval(null);
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
              {authView === 'register' && (
                <p className="text-[9px] text-secondary mt-1">Mín. 8 caracteres, una mayúscula y un número.</p>
              )}
            </div>
            
            {authError && <div className="text-danger text-[10px] mb-4 uppercase tracking-tighter">{authError}</div>}
            
            <button type="submit" className="btn-primary" disabled={isAuthLoading}>
              {isAuthLoading ? <Loader2 size={18} className="animate-spin" /> : <Terminal size={18} />}
              {authView === 'login' ? 'Entrar' : 'Registrarse'}
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
          <div className="flex items-center gap-2 mb-1">
            <Shield size={20} className="text-accent-color" />
            <span className="font-bold tracking-widest text-sm uppercase">Tarkov Sherpa</span>
          </div>
          <div className="text-[9px] text-secondary font-mono truncate">{user.email}</div>
        </div>

        <div className="sidebar-content">
          {/* Saved Chats */}
          <div className="mb-8">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-[10px] uppercase tracking-widest text-secondary flex items-center gap-2">
                <History size={14} /> Archivos
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

          {/* Tracker Status */}
          <div className="mb-8">
            <h3 className="text-[10px] uppercase tracking-widest text-secondary mb-4 flex items-center gap-2">
              <Activity size={14} /> Inteligencia
            </h3>
            {token ? (
              userProgress ? (
                <div className="space-y-4">
                  <div className="stat-card">
                    <div className="stat-label">Nivel</div>
                    <div className="stat-value">{userProgress.level || '??'}</div>
                    <div className="level-bar">
                      <div className="level-progress" style={{ width: `${(userProgress.level / 79) * 100}%` }}></div>
                    </div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-label">Tareas</div>
                    <div className="stat-value">{userProgress.tasks?.filter(t => t.complete).length || 0}</div>
                  </div>
                </div>
              ) : (
                <div className="text-[10px] text-secondary italic">Sincronizando...</div>
              )
            ) : (
              <button onClick={() => setShowTrackerLogin(true)} className="w-full btn-secondary text-[9px]">
                Vincular TarkovTracker
              </button>
            )}
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
              <p className="text-xs text-secondary max-w-xs">Preparado para el despliegue. Solicita información técnica o táctica.</p>
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
              className="absolute -top-14 right-8 btn-primary !w-auto !rounded-full !p-3"
              title="Guardar Conversación"
            >
              <Save size={18} />
            </button>
          )}
          <form onSubmit={sendMessage} className="flex-1 flex gap-4">
            <input 
              className="chat-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Escribe tu mensaje..."
            />
            <button type="submit" className="send-btn" disabled={isLoading || !input.trim()}>
              {isLoading ? <Loader2 className="animate-spin" /> : <Send size={20} />}
            </button>
          </form>
        </div>
      </main>

      {/* Tracker Login Overlay */}
      {showTrackerLogin && (
        <div className="login-overlay" style={{ zIndex: 100 }}>
          <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="login-card max-w-sm">
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-sm uppercase tracking-widest text-accent-color">Vincular Inteligencia</h3>
              <button onClick={() => setShowTrackerLogin(false)} className="text-secondary hover:text-white">×</button>
            </div>
            <p className="text-[10px] text-secondary mb-6">Vincula tu API Key de Tarkov Tracker para obtener datos de tu perfil real.</p>
            <form onSubmit={handleTrackerLogin}>
              <div className="input-group">
                <label>API TOKEN</label>
                <input 
                  type="password" 
                  value={tempToken}
                  onChange={(e) => setTempToken(e.target.value)}
                  placeholder="Introducir token..."
                  required
                />
              </div>
              {trackerError && <div className="text-danger text-[10px] mb-4 uppercase">{trackerError}</div>}
              <button type="submit" className="btn-primary" disabled={isValidating}>
                {isValidating ? <Loader2 size={16} className="animate-spin mr-2" /> : <Terminal size={16} className="mr-2" />}
                {isValidating ? 'Validando...' : 'Sincronizar'}
              </button>
            </form>
          </motion.div>
        </div>
      )}
    </div>
  );
}

export default App;
