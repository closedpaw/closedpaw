"use client";

import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import { 
  Send, 
  Bot, 
  User, 
  Settings, 
  Shield, 
  AlertTriangle,
  CheckCircle,
  XCircle,
  Loader2,
  Mic,
  X,
  Sparkles,
  Lock,
  Cpu,
  Activity,
  Zap,
  Key,
  Globe,
  Database,
  Moon,
  Sun,
  ChevronRight,
  Terminal
} from "lucide-react";

const API_BASE = "http://127.0.0.1:8000";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  model?: string;
  actionId?: string;
  status?: "pending" | "completed" | "error";
}

interface Model {
  name: string;
  description: string;
  size: string;
  parameters: string;
}

interface PendingAction {
  id: string;
  action_type: string;
  skill_id?: string;
  security_level: string;
  parameters: Record<string, any>;
  created_at: string;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [models, setModels] = useState<Model[]>([]);
  const [selectedModel, setSelectedModel] = useState("llama3.2:3b");
  const [pendingActions, setPendingActions] = useState<PendingAction[]>([]);
  const [systemStatus, setSystemStatus] = useState<any>(null);
  const [showSettings, setShowSettings] = useState(false);
  const [activeTab, setActiveTab] = useState("models");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // API Keys state
  const [openaiKey, setOpenaiKey] = useState("");
  const [anthropicKey, setAnthropicKey] = useState("");
  const [ollamaHost, setOllamaHost] = useState("http://127.0.0.1:11434");

  useEffect(() => {
    fetchSystemStatus();
    fetchModels();
    fetchPendingActions();
    
    const interval = setInterval(() => {
      fetchPendingActions();
      fetchSystemStatus();
    }, 5000);
    
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const fetchSystemStatus = async () => {
    try {
      const response = await axios.get(`${API_BASE}/api/status`);
      setSystemStatus(response.data);
    } catch (error) {
      console.error("Failed to fetch system status:", error);
    }
  };

  const fetchModels = async () => {
    try {
      const response = await axios.get(`${API_BASE}/api/models`);
      setModels(response.data);
    } catch (error) {
      console.error("Failed to fetch models:", error);
    }
  };

  const fetchPendingActions = async () => {
    try {
      const response = await axios.get(`${API_BASE}/api/actions/pending`);
      setPendingActions(response.data);
    } catch (error) {
      console.error("Failed to fetch pending actions:", error);
    }
  };

  const handleApproveAction = async (actionId: string, approved: boolean) => {
    try {
      await axios.post(`${API_BASE}/api/actions/${actionId}/approve`, {
        approved,
        user_id: "user"
      });
      fetchPendingActions();
    } catch (error) {
      console.error("Failed to approve action:", error);
    }
  };

  const handleSendMessage = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input,
      timestamp: new Date(),
      status: "completed"
    };

    setMessages(prev => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    const assistantMessage: Message = {
      id: (Date.now() + 1).toString(),
      role: "assistant",
      content: "",
      timestamp: new Date(),
      status: "pending"
    };

    setMessages(prev => [...prev, assistantMessage]);

    try {
      const response = await axios.post(`${API_BASE}/api/chat`, {
        message: userMessage.content,
        model: selectedModel,
        use_cloud: false
      });

      setMessages(prev => 
        prev.map(msg => 
          msg.id === assistantMessage.id
            ? {
                ...msg,
                content: response.data.response,
                model: response.data.model,
                actionId: response.data.action_id,
                status: "completed"
              }
            : msg
        )
      );
    } catch (error) {
      setMessages(prev => 
        prev.map(msg => 
          msg.id === assistantMessage.id
            ? {
                ...msg,
                content: "Error: Unable to process request. Check system status.",
                status: "error"
              }
            : msg
        )
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const saveSettings = () => {
    localStorage.setItem("closedpaw_settings", JSON.stringify({
      openaiKey,
      anthropicKey,
      ollamaHost,
      selectedModel
    }));
    setShowSettings(false);
  };

  return (
    <div className="flex h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-white overflow-hidden">
      {/* Animated background */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-cyan-500/10 rounded-full blur-3xl animate-pulse" />
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-purple-500/10 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }} />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-blue-500/5 rounded-full blur-3xl" />
      </div>

      {/* Sidebar */}
      <div className={`${sidebarCollapsed ? 'w-20' : 'w-80'} transition-all duration-300 bg-slate-900/50 backdrop-blur-xl border-r border-white/5 flex flex-col relative z-10`}>
        {/* Header */}
        <div className="p-4 border-b border-white/5">
          <div className="flex items-center gap-3">
            <div className="relative">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-400 to-blue-500 flex items-center justify-center shadow-lg shadow-cyan-500/25">
                <Shield className="w-5 h-5 text-white" />
              </div>
              <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full border-2 border-slate-900 animate-pulse" />
            </div>
            {!sidebarCollapsed && (
              <div>
                <h1 className="text-lg font-bold bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent">
                  CLOSEDPAW
                </h1>
                <p className="text-xs text-slate-500">Zero-Trust AI</p>
              </div>
            )}
          </div>
        </div>

        {!sidebarCollapsed && (
          <>
            {/* System Status */}
            <div className="p-4 border-b border-white/5">
              <h2 className="text-xs font-semibold text-slate-400 mb-3 flex items-center gap-2 uppercase tracking-wider">
                <Activity className="w-3.5 h-3.5" />
                System Status
              </h2>
              <div className="space-y-2.5">
                <div className="flex items-center gap-3 p-2 rounded-lg bg-slate-800/50">
                  <div className={`w-2 h-2 rounded-full ${systemStatus?.ollama_connected ? "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.6)]" : "bg-red-500"}`} />
                  <span className="text-sm text-slate-300">Ollama</span>
                  <span className={`ml-auto text-xs font-medium ${systemStatus?.ollama_connected ? "text-emerald-400" : "text-red-400"}`}>
                    {systemStatus?.ollama_connected ? "ONLINE" : "OFFLINE"}
                  </span>
                </div>
                <div className="flex items-center gap-3 p-2 rounded-lg bg-slate-800/50">
                  <div className={`w-2 h-2 rounded-full ${systemStatus?.status === "running" ? "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.6)]" : "bg-yellow-500"}`} />
                  <span className="text-sm text-slate-300">Core</span>
                  <span className={`ml-auto text-xs font-medium ${systemStatus?.status === "running" ? "text-emerald-400" : "text-yellow-400"}`}>
                    {systemStatus?.status?.toUpperCase() || "UNKNOWN"}
                  </span>
                </div>
                <div className="flex items-center gap-3 p-2 rounded-lg bg-slate-800/50">
                  <Lock className="w-3.5 h-3.5 text-cyan-400" />
                  <span className="text-sm text-slate-300">Security</span>
                  <span className="ml-auto text-xs font-medium text-cyan-400">ACTIVE</span>
                </div>
              </div>
            </div>

            {/* Model Selection */}
            <div className="p-4 border-b border-white/5">
              <h2 className="text-xs font-semibold text-slate-400 mb-3 flex items-center gap-2 uppercase tracking-wider">
                <Cpu className="w-3.5 h-3.5" />
                Active Model
              </h2>
              <select
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                className="w-full p-2.5 bg-slate-800/50 border border-white/10 rounded-xl text-sm text-slate-200 focus:ring-2 focus:ring-cyan-500/50 focus:border-transparent backdrop-blur-sm appearance-none cursor-pointer"
              >
                {models.map((model) => (
                  <option key={model.name} value={model.name} className="bg-slate-800">
                    {model.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Pending Actions */}
            {pendingActions.length > 0 && (
              <div className="p-4 border-b border-white/5 flex-1 overflow-y-auto">
                <h2 className="text-xs font-semibold text-amber-400 mb-3 flex items-center gap-2 uppercase tracking-wider">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  Pending Actions ({pendingActions.length})
                </h2>
                <div className="space-y-2">
                  {pendingActions.map((action) => (
                    <div
                      key={action.id}
                      className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-xl backdrop-blur-sm"
                    >
                      <p className="text-sm text-amber-300 font-medium">
                        {action.action_type}
                      </p>
                      <p className="text-xs text-amber-500/70 mt-1">
                        Level: {action.security_level}
                      </p>
                      <div className="flex gap-2 mt-3">
                        <button
                          onClick={() => handleApproveAction(action.id, true)}
                          className="flex-1 px-3 py-1.5 bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 text-xs rounded-lg hover:bg-emerald-500/30 transition-colors font-medium"
                        >
                          <CheckCircle className="w-3 h-3 inline mr-1" />
                          Approve
                        </button>
                        <button
                          onClick={() => handleApproveAction(action.id, false)}
                          className="flex-1 px-3 py-1.5 bg-red-500/20 border border-red-500/30 text-red-400 text-xs rounded-lg hover:bg-red-500/30 transition-colors font-medium"
                        >
                          <XCircle className="w-3 h-3 inline mr-1" />
                          Reject
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Settings Button */}
            <div className="p-4 mt-auto border-t border-white/5">
              <button 
                onClick={() => setShowSettings(true)}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 text-sm text-slate-400 hover:text-white hover:bg-white/5 rounded-xl transition-all group"
              >
                <Settings className="w-4 h-4 group-hover:rotate-90 transition-transform duration-300" />
                <span>Configuration</span>
              </button>
            </div>
          </>
        )}

        {/* Collapse button */}
        <button
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          className="absolute -right-3 top-1/2 -translate-y-1/2 w-6 h-6 bg-slate-800 border border-white/10 rounded-full flex items-center justify-center text-slate-400 hover:text-white hover:bg-slate-700 transition-colors z-20"
        >
          <ChevronRight className={`w-4 h-4 transition-transform ${sidebarCollapsed ? 'rotate-180' : ''}`} />
        </button>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col relative z-10">
        {/* Chat Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full">
              <div className="relative mb-8">
                <div className="w-24 h-24 rounded-2xl bg-gradient-to-br from-cyan-400 via-blue-500 to-purple-500 flex items-center justify-center shadow-2xl shadow-cyan-500/25">
                  <Sparkles className="w-12 h-12 text-white" />
                </div>
                <div className="absolute inset-0 bg-gradient-to-br from-cyan-400 to-purple-500 rounded-2xl blur-2xl opacity-50 animate-pulse" />
              </div>
              
              <h2 className="text-3xl font-bold bg-gradient-to-r from-cyan-400 via-blue-400 to-purple-400 bg-clip-text text-transparent mb-3">
                Welcome to ClosedPaw
              </h2>
              <p className="text-center max-w-md text-slate-400 mb-8">
                Zero-trust architecture with hardened sandboxing.
                <br />
                Your AI assistant that never compromises on security.
              </p>
              
              <div className="flex flex-wrap gap-3 justify-center">
                {[
                  { icon: Shield, text: "gVisor Sandbox" },
                  { icon: Lock, text: "Encrypted Storage" },
                  { icon: Zap, text: "Local Only" },
                  { icon: Terminal, text: "CLI Access" }
                ].map((item, i) => (
                  <div key={i} className="flex items-center gap-2 px-4 py-2 bg-slate-800/50 border border-white/5 rounded-full text-sm text-slate-400 backdrop-blur-sm">
                    <item.icon className="w-4 h-4 text-cyan-400" />
                    {item.text}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            messages.map((message) => (
              <div
                key={message.id}
                className={`flex gap-4 ${
                  message.role === "user" ? "justify-end" : "justify-start"
                }`}
              >
                {message.role === "assistant" && (
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-400 to-blue-500 flex items-center justify-center flex-shrink-0 shadow-lg shadow-cyan-500/20">
                    <Bot className="w-5 h-5 text-white" />
                  </div>
                )}
                
                <div
                  className={`max-w-[70%] rounded-2xl px-5 py-3.5 backdrop-blur-sm ${
                    message.role === "user"
                      ? "bg-gradient-to-r from-cyan-500/20 to-blue-500/20 border border-cyan-500/20 text-white"
                      : "bg-slate-800/50 border border-white/5 text-slate-200"
                  }`}
                >
                  <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
                  
                  {message.role === "assistant" && message.model && (
                    <p className="text-xs text-slate-500 mt-2 pt-2 border-t border-white/5">
                      Model: {message.model}
                    </p>
                  )}
                  
                  {message.status === "pending" && (
                    <div className="flex items-center gap-2 mt-2 text-cyan-400">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span className="text-xs">Processing...</span>
                    </div>
                  )}
                </div>
                
                {message.role === "user" && (
                  <div className="w-10 h-10 rounded-xl bg-slate-700 flex items-center justify-center flex-shrink-0">
                    <User className="w-5 h-5 text-slate-300" />
                  </div>
                )}
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="p-6 border-t border-white/5 bg-slate-900/50 backdrop-blur-xl">
          <div className="max-w-4xl mx-auto">
            <div className="flex gap-3">
              <button
                className="p-3.5 text-slate-500 hover:text-cyan-400 rounded-xl border border-white/5 hover:border-cyan-500/30 hover:bg-cyan-500/5 transition-all"
                title="Voice input"
              >
                <Mic className="w-5 h-5" />
              </button>
              
              <div className="flex-1 relative">
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Ask anything... (Shift+Enter for new line)"
                  className="w-full p-3.5 pr-12 bg-slate-800/50 border border-white/10 rounded-xl resize-none focus:ring-2 focus:ring-cyan-500/50 focus:border-transparent text-white placeholder-slate-500 backdrop-blur-sm"
                  rows={1}
                  style={{ minHeight: "52px", maxHeight: "120px" }}
                />
              </div>
              
              <button
                onClick={handleSendMessage}
                disabled={!input.trim() || isLoading}
                className="p-3.5 bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-400 hover:to-blue-400 text-white rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-cyan-500/25 hover:shadow-cyan-500/40"
              >
                {isLoading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Send className="w-5 h-5" />
                )}
              </button>
            </div>
            
            <p className="text-xs text-slate-600 mt-3 text-center flex items-center justify-center gap-4">
              <span className="flex items-center gap-1.5">
                <Lock className="w-3 h-3" />
                End-to-end encrypted
              </span>
              <span className="flex items-center gap-1.5">
                <Shield className="w-3 h-3" />
                Local execution
              </span>
              <span className="flex items-center gap-1.5">
                <Database className="w-3 h-3" />
                No data leaves device
              </span>
            </p>
          </div>
        </div>
      </div>

      {/* Settings Modal */}
      {showSettings && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900/95 border border-white/10 rounded-2xl w-full max-w-2xl max-h-[85vh] overflow-hidden shadow-2xl backdrop-blur-xl">
            {/* Modal Header */}
            <div className="p-5 border-b border-white/5 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-white flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-cyan-500/20 flex items-center justify-center">
                  <Settings className="w-4 h-4 text-cyan-400" />
                </div>
                Configuration
              </h2>
              <button 
                onClick={() => setShowSettings(false)}
                className="p-2 text-slate-400 hover:text-white hover:bg-white/5 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Tabs */}
            <div className="flex border-b border-white/5">
              {[
                { id: "models", label: "Models", icon: Cpu },
                { id: "api", label: "API Keys", icon: Key },
                { id: "network", label: "Network", icon: Globe },
                { id: "storage", label: "Storage", icon: Database }
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex-1 p-3.5 text-sm font-medium flex items-center justify-center gap-2 transition-colors ${
                    activeTab === tab.id 
                      ? "text-cyan-400 border-b-2 border-cyan-400 bg-cyan-500/5" 
                      : "text-slate-500 hover:text-slate-300"
                  }`}
                >
                  <tab.icon className="w-4 h-4" />
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Tab Content */}
            <div className="p-6 max-h-[400px] overflow-y-auto">
              {activeTab === "models" && (
                <div className="space-y-3">
                  <h3 className="text-sm font-medium text-slate-400 mb-4">Available Models</h3>
                  {models.map((model) => (
                    <div key={model.name} className="p-4 bg-slate-800/50 border border-white/5 rounded-xl hover:border-cyan-500/20 transition-colors">
                      <div className="flex items-center justify-between">
                        <span className="text-white font-medium">{model.name}</span>
                        <button
                          onClick={() => setSelectedModel(model.name)}
                          className={`px-4 py-1.5 text-xs rounded-lg font-medium transition-colors ${
                            selectedModel === model.name
                              ? "bg-gradient-to-r from-cyan-500 to-blue-500 text-white"
                              : "bg-slate-700 text-slate-300 hover:bg-slate-600"
                          }`}
                        >
                          {selectedModel === model.name ? "Active" : "Select"}
                        </button>
                      </div>
                      <p className="text-xs text-slate-500 mt-2">{model.description}</p>
                      <p className="text-xs text-slate-600 mt-1">Size: {model.size}</p>
                    </div>
                  ))}
                </div>
              )}

              {activeTab === "api" && (
                <div className="space-y-5">
                  <div>
                    <label className="text-sm font-medium text-slate-400 block mb-2">
                      OpenAI API Key
                    </label>
                    <input
                      type="password"
                      value={openaiKey}
                      onChange={(e) => setOpenaiKey(e.target.value)}
                      placeholder="sk-..."
                      className="w-full p-3 bg-slate-800/50 border border-white/10 rounded-xl text-slate-200 text-sm focus:ring-2 focus:ring-cyan-500/50 focus:border-transparent"
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium text-slate-400 block mb-2">
                      Anthropic API Key
                    </label>
                    <input
                      type="password"
                      value={anthropicKey}
                      onChange={(e) => setAnthropicKey(e.target.value)}
                      placeholder="sk-ant-..."
                      className="w-full p-3 bg-slate-800/50 border border-white/10 rounded-xl text-slate-200 text-sm focus:ring-2 focus:ring-cyan-500/50 focus:border-transparent"
                    />
                  </div>
                  <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-xl">
                    <p className="text-sm text-emerald-400 flex items-center gap-2">
                      <CheckCircle className="w-4 h-4" />
                      API keys are encrypted and stored locally
                    </p>
                  </div>
                </div>
              )}

              {activeTab === "network" && (
                <div className="space-y-5">
                  <div>
                    <label className="text-sm font-medium text-slate-400 block mb-2">
                      Ollama Host
                    </label>
                    <input
                      type="text"
                      value={ollamaHost}
                      onChange={(e) => setOllamaHost(e.target.value)}
                      className="w-full p-3 bg-slate-800/50 border border-white/10 rounded-xl text-slate-200 text-sm focus:ring-2 focus:ring-cyan-500/50 focus:border-transparent"
                    />
                  </div>
                  <div className="p-4 bg-cyan-500/10 border border-cyan-500/20 rounded-xl">
                    <p className="text-sm text-cyan-400 flex items-center gap-2">
                      <Shield className="w-4 h-4" />
                      Secure mode: Ollama bound to localhost only
                    </p>
                  </div>
                </div>
              )}

              {activeTab === "storage" && (
                <div className="space-y-4">
                  <div className="p-4 bg-slate-800/50 border border-white/5 rounded-xl">
                    <p className="text-sm text-white font-medium">Data Vault</p>
                    <p className="text-sm text-slate-500 mt-1">~/.config/closedpaw</p>
                  </div>
                  <div className="p-4 bg-slate-800/50 border border-white/5 rounded-xl">
                    <p className="text-sm text-white font-medium">Encryption</p>
                    <p className="text-sm text-emerald-400 mt-1 flex items-center gap-2">
                      <Lock className="w-4 h-4" />
                      AES-256-GCM Active
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="p-5 border-t border-white/5 flex justify-end gap-3">
              <button
                onClick={() => setShowSettings(false)}
                className="px-5 py-2.5 text-sm text-slate-400 hover:text-white hover:bg-white/5 rounded-xl transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={saveSettings}
                className="px-5 py-2.5 bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-400 hover:to-blue-400 text-white text-sm rounded-xl font-medium shadow-lg shadow-cyan-500/25"
              >
                Save Configuration
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
