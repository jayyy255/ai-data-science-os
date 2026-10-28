import React, { useState, useRef, useEffect } from 'react';
import { useProjectStore } from '../store/useProjectStore';
import { Send, BrainCircuit, User, BookOpen, AlertTriangle, ChevronDown } from 'lucide-react';
import api, { errorMessage } from '../api';
import MarkdownContent from '../components/MarkdownContent';


export default function AiAssistantPage() {
  const { getActiveProject, getChatHistory, addChatMessage } = useProjectStore();
  const project = getActiveProject();

  const [inputMsg, setInputMsg] = useState('');
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [contextExpanded, setContextExpanded] = useState(false);
  const messagesEndRef = useRef(null);

  const suggestionChips = [
    'Why was the champion model selected?',
    'What preprocessing was applied?',
    `Which features influence ${project.targetVariable} most?`,
    'What data quality issues need attention?'
  ];

  useEffect(() => {
    setMessages(getChatHistory(project.id, project.name));
  }, [project.id, project.name, getChatHistory]);

  useEffect(() => {
    const anchor = messagesEndRef.current;
    if (anchor?.parentElement) anchor.parentElement.scrollTop = anchor.parentElement.scrollHeight;
  }, [messages, loading]);

  const handleSend = async (textToSend) => {
    if (!textToSend.trim() || loading || !project.id) return;

    // Add user message
    const userMsg = { sender: 'user', text: textToSend };
    setMessages(prev => [...prev, userMsg]);
    addChatMessage(project.id, userMsg);
    setInputMsg('');
    setLoading(true);

    try {
      const res = await api.post(`/projects/${project.id}/chat`, {
        question: textToSend
      });
      let responseText = res.data.answer;

      const aiMsg = { sender: 'ai', text: responseText };
      setMessages(prev => [...prev, aiMsg]);
      addChatMessage(project.id, aiMsg);
      setLoading(false);
    } catch (err) {
      console.warn("Backend API chat failed.", err);
      const errMsg = { sender: 'ai', text: errorMessage(err) };
      setMessages(prev => [...prev, errMsg]);
      addChatMessage(project.id, errMsg);
      setLoading(false);
    }
  };

  return (
    <div className="assistant-layout flex flex-col xl:flex-row gap-4 xl:gap-6 items-stretch">
      {/* Left panel: Context grounding */}
      <div className="assistant-context w-full xl:w-72 flex-shrink-0 bg-brand-dark-surface border border-brand-dark-border rounded-xl p-4 xl:p-5 overflow-y-auto">
        <button type="button" className="w-full flex items-center justify-between gap-3 text-sm xl:hidden" aria-expanded={contextExpanded} aria-controls="assistant-context-content" onClick={() => setContextExpanded(value => !value)}>
          <span className="flex items-center gap-2"><BookOpen className="w-4 h-4" />Project context</span>
          <ChevronDown className={`w-4 h-4 shrink-0 transition-transform ${contextExpanded ? 'rotate-180' : ''}`} />
        </button>
        <div id="assistant-context-content" className={`${contextExpanded ? 'flex' : 'hidden'} xl:flex flex-col justify-between gap-4 xl:h-full pt-4 xl:pt-0`}>
        <div className="space-y-4">
          <div className="flex items-center gap-2 border-b border-brand-dark-border/40 pb-2">
            <BookOpen className="w-4.5 h-4.5 text-brand-primary" />
            <h3 className="text-sm font-semibold text-zinc-200">Grounding Context</h3>
          </div>

          <div className="space-y-3.5">
            <div className="bg-brand-dark-bg/60 p-3 rounded-xl border border-brand-dark-border/20 text-xs space-y-1">
              <span className="text-[10px] text-zinc-500 font-mono uppercase">Reference Card</span>
              <p className="font-dataset-name dataset-card-title text-zinc-200">{project.name}</p>
              <p className="text-[10px] text-zinc-400 font-mono">Status: {project.status}</p>
            </div>

            <div className="bg-brand-dark-bg/60 p-3 rounded-xl border border-brand-dark-border/20 text-xs space-y-2">
              <span className="text-[10px] text-zinc-500 font-mono uppercase block">Active Memory Registers</span>
              <div className="flex justify-between items-center text-[10px] font-mono">
                <span className="text-zinc-500">Decisions</span>
                <span className="text-violet-300 font-bold">{project.featureEngineeringDecisions?.length} logged</span>
              </div>
              <div className="flex justify-between items-center text-[10px] font-mono">
                <span className="text-zinc-500">{project.problemType === 'regression' ? 'Test MSE' : 'Test F1'}</span>
                <span className="text-emerald-400 font-bold">{(project.problemType === 'regression' ? project.bestMse : project.bestF1) ?? 'N/A'}</span>
              </div>
            </div>

            <div className="flex items-start gap-2 bg-brand-primary/5 border border-brand-primary/10 p-3 rounded-xl">
              <AlertTriangle className="w-4 h-4 text-brand-primary flex-shrink-0 mt-0.5" />
              <p className="text-[10px] text-zinc-400 leading-relaxed">
                Answers use this project's dataset profile, feature decisions, and training results. Review generated suggestions against your data.
              </p>
            </div>
          </div>
        </div>

        <div className="pt-4 border-t border-brand-dark-border/40 text-[10px] text-zinc-500 font-mono text-center">
          Gemini when configured; project summary otherwise
        </div>
        </div>
      </div>

      {/* Right panel: Chat workspace */}
      <div className="assistant-conversation min-w-0 flex-1 bg-brand-dark-surface border border-brand-dark-border rounded-xl flex flex-col overflow-hidden shadow-2xl">
        {/* Chat header */}
        <div className="p-4 border-b border-brand-dark-border bg-brand-dark-bg/20 flex items-center gap-3">
          <div className="bg-brand-primary/10 p-2 rounded-xl border border-brand-primary/20 text-brand-primary">
            <BrainCircuit className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-zinc-200">Chat Assistant</h3>
            <p className="text-[10px] font-mono text-zinc-500">Context from project records and recent timeline events</p>
          </div>
        </div>

        {/* Message history */}
        <div className="min-h-0 flex-1 overflow-y-auto p-3 sm:p-4 space-y-4" aria-label="Chat messages">
          {messages.map((msg, i) => {
            const isAI = msg.sender === 'ai';
            return (
              <div
                key={i}
                className={`flex gap-3 min-w-0 max-w-2xl ${isAI ? 'mr-auto' : 'ml-auto flex-row-reverse'}`}
              >
                <div className={`
                  w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0
                  ${isAI ? 'bg-brand-primary/10 border border-brand-primary/20 text-brand-primary' : 'bg-brand-dark-card border border-brand-dark-border text-zinc-300'}
                `}>
                  {isAI ? <BrainCircuit className="w-4 h-4" /> : <User className="w-4 h-4" />}
                </div>

                <div className={`
                  min-w-0 p-3.5 rounded-2xl text-sm leading-relaxed border
                  ${isAI
                    ? 'bg-brand-dark-bg/60 border-brand-dark-border/40 text-zinc-200'
                    : 'bg-brand-primary/10 border-brand-primary/20 text-violet-100'}
                `}>
                  {isAI ? (
                    <MarkdownContent>{msg.text}</MarkdownContent>
                  ) : (
                    msg.text
                  )}
                </div>
              </div>
            );
          })}

          {loading && (
            <div className="flex gap-3 mr-auto">
              <div className="w-8 h-8 rounded-full bg-brand-primary/10 border border-brand-primary/20 text-brand-primary flex items-center justify-center text-xs font-bold flex-shrink-0">
                <BrainCircuit className="w-4 h-4" />
              </div>
              <div className="bg-brand-dark-bg/60 border border-brand-dark-border/40 p-3.5 rounded-2xl flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-brand-primary animate-bounce"></span>
                <span className="w-1.5 h-1.5 rounded-full bg-brand-primary animate-bounce delay-150"></span>
                <span className="w-1.5 h-1.5 rounded-full bg-brand-primary animate-bounce delay-300"></span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input box & suggestion chips */}
        <div className="shrink-0 p-3 sm:p-4 border-t border-brand-dark-border bg-brand-dark-bg/20 space-y-3">
          {/* Suggestion Chips */}
          <div className="flex gap-2 flex-wrap">
            {suggestionChips.map((chip, idx) => (
              <button
                key={idx}
                onClick={() => handleSend(chip)}
                className="text-[10px] font-semibold bg-brand-dark-card hover:bg-brand-dark-border border border-brand-dark-border text-zinc-400 hover:text-zinc-200 py-1.5 px-3 rounded-full transition-all cursor-pointer"
              >
                {chip}
              </button>
            ))}
          </div>

          {/* Form */}
          <form
            onSubmit={(e) => { e.preventDefault(); handleSend(inputMsg); }}
            className="flex gap-2"
          >
            <input
              type="text"
              value={inputMsg}
              onChange={(e) => setInputMsg(e.target.value)}
              aria-label="Message to assistant"
              className="min-w-0 flex-1 bg-brand-dark-bg border border-brand-dark-border focus:border-brand-primary focus:ring-1 focus:ring-brand-primary outline-none py-2 px-3 rounded-xl text-sm font-medium transition-all"
              placeholder="Ask about HPO trials or metrics..."
              disabled={loading}
            />
            <button
              type="submit"
              aria-label="Send message"
              disabled={loading}
              className="bg-brand-primary hover:bg-brand-primary-hover p-2.5 rounded-xl text-white transition-all shadow-lg shadow-brand-primary/25 cursor-pointer flex-shrink-0"
            >
              <Send className="w-4 h-4 fill-white" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
