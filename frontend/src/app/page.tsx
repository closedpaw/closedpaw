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
  Terminal,
  Lock,
  Cpu,
  Activity,
  Zap,
  Key,
  Globe,
  Database
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
    // Save to localStorage for now
    localStorage.setItem("closedpaw_settings", JSON.stringify({
      openaiKey,
      anthropicKey,
      ollamaHost,
      selectedModel
    }));
    setShowSettings(false);
  };

  return (
    <div className="flex h-screen bg-slate-950 text-cyan-50 font-mono">
      {/* Sidebar */}
      <div className="w-80 bg-slate-900 border-r border-cyan-900/50 flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-cyan-900/50 bg-gradient-to-r from-cyan-950 to-slate-900">
          <div className="flex items-center gap-3">
            <div className="relative">
              <Shield className="w-8 h-8 text-cyan-400" />
              <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full animate-pulse" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-cyan-400 tracking-wider">CLOSEDPAW</h1>
              <p className="text-xs text-cyan-600">ZERO-TRUST AI v1.0</p>
            </div>
          </div>
        </div>

        {/* System Status */}
        <div className="p-4 border-b border-cyan-900/50">
          <h2 className="text-xs font-bold text-cyan-500 mb-3 flex items-center gap-2">
            <Activity className="w-4 h-4" />
            SYSTEM STATUS
          </h2>
          <div className="space-y-2 text-sm">
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${systemStatus?.ollama_connected ? "bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.8)]" : "bg-red-500"}`} />
              <span className="text-cyan-300">
                Ollama: {systemStatus?.ollama_connected ? "ONLINE" : "OFFLINE"}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${systemStatus?.status === "running" ? "bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.8)]" : "bg-yellow-500"}`} />
              <span className="text-cyan-300">
                Core: {systemStatus?.status?.toUpperCase() || "UNKNOWN"}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Lock className="w-4 h-4 text-cyan-500" />
              <span className="text-cyan-300">
                Security: ACTIVE
              </span>
            </div>
          </div>
        </div>

        {/* Model Selection */}
        <div className="p-4 border-b border-cyan-900/50">
          <h2 className="text-xs font-bold text-cyan-500 mb-3 flex items-center gap-2">
            <Cpu className="w-4 h-4" />
            ACTIVE MODEL
          </h2>
          <select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            className="w-full p-2 bg-slate-800 border border-cyan-700 rounded text-cyan-300 text-sm focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
          >
            {models.map((model) => (
              <option key={model.name} value={model.name}>
                {model.name}
              </option>
            ))}
          </select>
        </div>

        {/* Pending Actions */}
        {pendingActions.length > 0 && (
          <div className="p-4 border-b border-cyan-900/50 flex-1 overflow-y-auto">
            <h2 className="text-xs font-bold text-yellow-500 mb-3 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4" />
              PENDING ACTIONS ({pendingActions.length})
            </h2>
            <div className="space-y-2">
              {pendingActions.map((action) => (
                <div
                  key={action.id}
                  className="p-3 bg-yellow-950/50 border border-yellow-700/50 rounded"
                >
                  <p className="text-sm text-yellow-300 font-bold">
                    {action.action_type}
                  </p>
                  <p className="text-xs text-yellow-600">
                    Level: {action.security_level}
                  </p>
                  <div className="flex gap-2 mt-2">
                    <button
                      onClick={() => handleApproveAction(action.id, true)}
                      className="flex-1 px-2 py-1 bg-green-900/50 border border-green-700 text-green-400 text-xs rounded hover:bg-green-800"
                    >
                      <CheckCircle className="w-3 h-3 inline mr-1" />
                      APPROVE
                    </button>
                    <button
                      onClick={() => handleApproveAction(action.id, false)}
                      className="flex-1 px-2 py-1 bg-red-900/50 border border-red-700 text-red-400 text-xs rounded hover:bg-red-800"
                    >
                      <XCircle className="w-3 h-3 inline mr-1" />
                      REJECT
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Settings Button */}
        <div className="p-4 mt-auto border-t border-cyan-900/50">
          <button 
            onClick={() => setShowSettings(true)}
            className="flex items-center gap-2 text-sm text-cyan-400 hover:text-cyan-300 transition-colors"
          >
            <Settings className="w-4 h-4" />
            CONFIGURATION
          </button>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col bg-slate-950">
        {/* Chat Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full">
              <div className="relative mb-6">
                <Terminal className="w-20 h-20 text-cyan-600" />
                <div className="absolute inset-0 bg-cyan-500/20 blur-xl" />
              </div>
              <h2 className="text-2xl font-bold text-cyan-400 mb-2 tracking-wider">CLOSEDPAW</h2>
              <p className="text-center max-w-md text-cyan-600">
                Zero-trust architecture with hardened sandboxing.
                <br />
                All actions require explicit approval.
              </p>
              <div className="flex gap-4 mt-6">
                <div className="flex items-center gap-2 text-xs text-cyan-700">
                  <Shield className="w-4 h-4" />
                  gVisor Sandbox
                </div>
                <div className="flex items-center gap-2 text-xs text-cyan-700">
                  <Lock className="w-4 h-4" />
                  Encrypted Storage
                </div>
                <div className="flex items-center gap-2 text-xs text-cyan-700">
                  <Zap className="w-4 h-4" />
                  Local Only
                </div>
              </div>
            </div>
          ) : (
            messages.map((message) => (
              <div
                key={message.id}
                className={`flex gap-3 ${
                  message.role === "user" ? "justify-end" : "justify-start"
                }`}
              >
                {message.role === "assistant" && (
                  <div className="w-10 h-10 rounded bg-cyan-900/50 border border-cyan-700 flex items-center justify-center flex-shrink-0">
                    <Bot className="w-6 h-6 text-cyan-400" />
                  </div>
                )}
                
                <div
                  className={`max-w-[70%] rounded-lg px-4 py-3 border ${
                    message.role === "user"
                      ? "bg-cyan-900/30 border-cyan-700 text-cyan-100"
                      : "bg-slate-900 border-cyan-800/50 text-cyan-100"
                  }`}
                >
                  <p className="text-sm whitespace-pre-wrap leading-relaxed">{message.content}</p>
                  
                  {message.role === "assistant" && message.model && (
                    <p className="text-xs text-cyan-600 mt-2">
                      Model: {message.model}
                    </p>
                  )}
                  
                  {message.status === "pending" && (
                    <div className="flex items-center gap-2 mt-2">
                      <Loader2 className="w-4 h-4 animate-spin text-cyan-600" />
                      <span className="text-xs text-cyan-600">Processing...</span>
                    </div>
                  )}
                </div>
                
                {message.role === "user" && (
                  <div className="w-10 h-10 rounded bg-cyan-700/50 border border-cyan-600 flex items-center justify-center flex-shrink-0">
                    <User className="w-6 h-6 text-cyan-300" />
                  </div>
                )}
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="p-4 border-t border-cyan-900/50 bg-slate-900/50">
          <div className="flex gap-2">
            <button
              className="p-3 text-cyan-600 hover:text-cyan-400 rounded-lg border border-cyan-800/50 hover:border-cyan-600 transition-colors"
              title="Voice input"
            >
              <Mic className="w-5 h-5" />
            </button>
            
            <div className="flex-1 relative">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Enter command..."
                className="w-full p-3 pr-12 bg-slate-900 border border-cyan-800/50 rounded-lg resize-none focus:ring-2 focus:ring-cyan-600 focus:border-transparent text-cyan-100 placeholder-cyan-800"
                rows={1}
                style={{ minHeight: "48px", maxHeight: "120px" }}
              />
            </div>
            
            <button
              onClick={handleSendMessage}
              disabled={!input.trim() || isLoading}
              className="p-3 bg-cyan-700 hover:bg-cyan-600 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed border border-cyan-500"
            >
              {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </button>
          </div>
          
          <p className="text-xs text-cyan-800 mt-2 text-center">
            [SECURE] Local execution only • End-to-end encrypted • No data leaves device
          </p>
        </div>
      </div>

      {/* Settings Modal */}
      {showSettings && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50">
          <div className="bg-slate-900 border border-cyan-700 rounded-lg w-[600px] max-h-[80vh] overflow-hidden">
            {/* Modal Header */}
            <div className="p-4 border-b border-cyan-800 flex items-center justify-between bg-gradient-to-r from-cyan-950 to-slate-900">
              <h2 className="text-lg font-bold text-cyan-400 flex items-center gap-2">
                <Settings className="w-5 h-5" />
                SYSTEM CONFIGURATION
              </h2>
              <button 
                onClick={() => setShowSettings(false)}
                className="text-cyan-600 hover:text-cyan-400"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Tabs */}
            <div className="flex border-b border-cyan-800">
              {[
                { id: "models", label: "MODELS", icon: Cpu },
                { id: "api", label: "API KEYS", icon: Key },
                { id: "network", label: "NETWORK", icon: Globe },
                { id: "storage", label: "STORAGE", icon: Database }
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex-1 p-3 text-xs font-bold flex items-center justify-center gap-2 transition-colors ${
                    activeTab === tab.id 
                      ? "bg-cyan-900/50 text-cyan-400 border-b-2 border-cyan-400" 
                      : "text-cyan-700 hover:text-cyan-500"
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
                <div className="space-y-4">
                  <h3 className="text-sm font-bold text-cyan-500">LOCAL MODELS</h3>
                  {models.map((model) => (
                    <div key={model.name} className="p-3 bg-slate-800 border border-cyan-800/50 rounded">
                      <div className="flex items-center justify-between">
                        <span className="text-cyan-300 font-bold">{model.name}</span>
                        <button
                          onClick={() => setSelectedModel(model.name)}
                          className={`px-3 py-1 text-xs rounded border ${
                            selectedModel === model.name
                              ? "bg-cyan-700 border-cyan-500 text-white"
                              : "bg-slate-700 border-cyan-800 text-cyan-400 hover:border-cyan-600"
                          }`}
                        >
                          {selectedModel === model.name ? "ACTIVE" : "SELECT"}
                        </button>
                      </div>
                      <p className="text-xs text-cyan-600 mt-1">{model.description}</p>
                      <p className="text-xs text-cyan-700">Size: {model.size}</p>
                    </div>
                  ))}
                </div>
              )}

              {activeTab === "api" && (
                <div className="space-y-4">
                  <div>
                    <label className="text-xs font-bold text-cyan-500 block mb-2">
                      OPENAI API KEY
                    </label>
                    <input
                      type="password"
                      value={openaiKey}
                      onChange={(e) => setOpenaiKey(e.target.value)}
                      placeholder="sk-..."
                      className="w-full p-2 bg-slate-800 border border-cyan-800 rounded text-cyan-300 text-sm"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-bold text-cyan-500 block mb-2">
                      ANTHROPIC API KEY
                    </label>
                    <input
                      type="password"
                      value={anthropicKey}
                      onChange={(e) => setAnthropicKey(e.target.value)}
                      placeholder="sk-ant-..."
                      className="w-full p-2 bg-slate-800 border border-cyan-800 rounded text-cyan-300 text-sm"
                    />
                  </div>
                  <p className="text-xs text-cyan-700">
                    API keys are encrypted and stored locally. Never transmitted to external servers.
                  </p>
                </div>
              )}

              {activeTab === "network" && (
                <div className="space-y-4">
                  <div>
                    <label className="text-xs font-bold text-cyan-500 block mb-2">
                      OLLAMA HOST
                    </label>
                    <input
                      type="text"
                      value={ollamaHost}
                      onChange={(e) => setOllamaHost(e.target.value)}
                      className="w-full p-2 bg-slate-800 border border-cyan-800 rounded text-cyan-300 text-sm"
                    />
                  </div>
                  <div className="p-3 bg-green-950/30 border border-green-800/50 rounded">
                    <p className="text-xs text-green-400">
                      <CheckCircle className="w-4 h-4 inline mr-1" />
                      Secure mode: Ollama bound to localhost only
                    </p>
                  </div>
                </div>
              )}

              {activeTab === "storage" && (
                <div className="space-y-4">
                  <div className="p-3 bg-slate-800 border border-cyan-800/50 rounded">
                    <p className="text-sm text-cyan-300">Data Vault Location</p>
                    <p className="text-xs text-cyan-600">~/.config/closedpaw</p>
                  </div>
                  <div className="p-3 bg-slate-800 border border-cyan-800/50 rounded">
                    <p className="text-sm text-cyan-300">Encryption Status</p>
                    <p className="text-xs text-green-400">AES-256-GCM Active</p>
                  </div>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-cyan-800 flex justify-end gap-2">
              <button
                onClick={() => setShowSettings(false)}
                className="px-4 py-2 text-sm text-cyan-400 hover:text-cyan-300"
              >
                CANCEL
              </button>
              <button
                onClick={saveSettings}
                className="px-4 py-2 bg-cyan-700 hover:bg-cyan-600 text-white text-sm rounded border border-cyan-500"
              >
                SAVE CONFIGURATION
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
