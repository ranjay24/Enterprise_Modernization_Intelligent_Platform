import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { MessageSquare, X, Send, Sparkles, Lightbulb, Code2, DollarSign, ArrowRight } from 'lucide-react';
import { GlassCard } from '@/components/ui/GlassCard';
import { Input } from '@/components/ui/Input';
import { cn } from '@/utils/cn';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
}

const suggestedPrompts = [
  { icon: Lightbulb, text: 'What is the biggest migration blocker?' },
  { icon: Code2, text: 'Why was Billing grouped separately?' },
  { icon: FileText, text: 'Generate an ADR for PaymentService' },
  { icon: DollarSign, text: 'Estimate AWS cost for migration' },
];

function sanitizeMarkdown(text: string) {
  return text
    .replace(/```(\w+)?\n([\s\S]*?)```/g, (_, lang, code) => {
      return `<pre class="text-mono text-xs leading-relaxed p-3 rounded-lg bg-[var(--bg-card)] border border-[var(--border-subtle)] overflow-x-auto"><code>${code.trim()}</code></pre>`;
    })
    .replace(/\*\*(.*?)\*\*/g, '<strong class="font-semibold">$1</strong>')
    .replace(/\n/g, '<br />');
}

function TypingIndicator() {
  return (
    <div className="flex items-center gap-3 px-4 py-3">
      <div className="w-6 h-6 rounded-full bg-[var(--accent-purple)]/15 flex items-center justify-center shrink-0">
        <Sparkles className="w-3 h-3 text-[var(--accent-purple)]" />
      </div>
      <div className="flex gap-1">
        <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent-purple)] animate-typing" style={{ animationDelay: '0ms' }} />
        <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent-purple)] animate-typing" style={{ animationDelay: '200ms' }} />
        <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent-purple)] animate-typing" style={{ animationDelay: '400ms' }} />
      </div>
    </div>
  );
}

const panelVariants = {
  hidden: { opacity: 0, y: 20, scale: 0.96 },
  visible: { opacity: 1, y: 0, scale: 1, transition: { duration: 0.25, ease: [0.16, 1, 0.3, 1] as [number, number, number, number] } },
  exit: { opacity: 0, y: 20, scale: 0.96, transition: { duration: 0.2, ease: [0.16, 1, 0.3, 1] as [number, number, number, number] } },
};

function FileText({ className }: { className?: string }) {
  return <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/></svg>;
}

const mockResponses: Record<string, string> = {
  blocker: `## Migration Blocker Analysis

The **OrderManagementService** is the primary migration blocker with **2,400 LOC** across **14 tightly coupled classes**.

**Key issues:**
- 85% coupling score — highest in the codebase
- Circular dependency chain with PaymentService and CartService
- Shared database access with no schema isolation

**Recommendation:** Decompose into Order, Fulfillment, and Tracking services before proceeding with other migrations.`,
  billing: `## Billing Service Grouping

The **BillingService** was grouped separately because:

1. **Domain independence** — Billing has its own distinct business domain (invoicing, payments, collections) with minimal cross-domain interaction
2. **Data isolation** — Billing operates on its own database schema with no shared tables
3. **API surface** — Only 3 REST endpoints, all self-contained

This makes it an ideal early candidate for extraction — **90% readiness score** with low risk.`,
  adr: `## ADR: Extract PaymentService as Independent Microservice

**Status:** Proposed

**Context:** PaymentService handles payment processing, refunds, and reconciliation. Currently tightly coupled with OrderService in a circular dependency.

**Decision:** Extract PaymentService as an independent microservice communicating via async events (SQS).

**Consequences:**
- ✅ Eliminates circular dependency with OrderService
- ✅ Independent scaling during peak payment periods
- ✅ Reduced blast radius for payment failures
- ⚠️ Requires eventual consistency patterns
- ⚠️ Additional infrastructure for message broker

**Confidence:** 91%`,
  cost: `## AWS Migration Cost Estimate

Based on the current architecture analysis:

| Category | Current (On-Prem) | Post-Migration (AWS) |
|----------|-------------------|---------------------|
| Compute | $4,800/mo | $3,200/mo |
| Storage | $2,200/mo | $1,400/mo |
| Networking | $1,800/mo | $1,200/mo |
| Operations | $2,600/mo | $1,600/mo |
| Licensing | $1,000/mo | $800/mo |

**Total Savings:** $4,200/mo ($50,400/yr)
**Payback Period:** 8 months
**3-Year Savings:** $151,200`,
};

export function AIChat() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  const handleSend = (text: string) => {
    if (!text.trim() || isTyping) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: text.trim(),
      timestamp: Date.now(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setIsTyping(true);

    const lower = text.toLowerCase();
    let responseKey: string;
    if (lower.includes('blocker') || lower.includes('biggest')) responseKey = 'blocker';
    else if (lower.includes('billing') || lower.includes('group')) responseKey = 'billing';
    else if (lower.includes('adr')) responseKey = 'adr';
    else responseKey = 'cost';

    setTimeout(() => {
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: mockResponses[responseKey],
          timestamp: Date.now(),
        },
      ]);
      setIsTyping(false);
    }, 1200);
  };

  return (
    <>
      {/* FAB */}
      <button
        onClick={() => setOpen(true)}
        className={cn(
          'fixed bottom-6 right-6 z-40 w-12 h-12 rounded-full flex items-center justify-center',
          'bg-[var(--accent-purple)] text-white shadow-lg shadow-[var(--accent-purple)]/20',
          'hover:bg-[var(--accent-purple-strong)] hover:shadow-xl hover:shadow-[var(--accent-purple)]/30',
          'transition-all duration-[var(--duration-base)] ease-[var(--ease-out)]',
          'active:scale-95',
          open && 'scale-0 pointer-events-none'
        )}
        title="Ask EMIP AI (demo)"
      >
        <MessageSquare className="w-5 h-5" />
      </button>

      {/* Chat panel */}
      <AnimatePresence>
        {open && (
          <motion.div
            variants={panelVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            className="fixed bottom-6 right-6 z-40 w-[400px] max-w-[calc(100vw-48px)] h-[560px] max-h-[calc(100vh-120px)]"
          >
            <GlassCard glow="purple" hover={false} className="w-full h-full flex flex-col">
              {/* Header */}
              <div className="flex items-center justify-between p-4 border-b border-[var(--border-subtle)] shrink-0">
                <div className="flex items-center gap-2.5">
                  <div className="w-7 h-7 rounded-lg bg-[var(--accent-purple)]/15 flex items-center justify-center">
                    <Sparkles className="w-4 h-4 text-[var(--accent-purple)]" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-[var(--text-primary)]">Ask EMIP AI</h3>
                    <p className="text-[10px] text-[var(--text-secondary)]">Demo assistant · pre-written sample answers</p>
                  </div>
                </div>
                <button
                  onClick={() => setOpen(false)}
                  className="p-1.5 rounded-lg hover:bg-[var(--border-subtle)] text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-4 space-y-3">
                {messages.length === 0 ? (
                  <div className="h-full flex flex-col justify-center">
                    <div className="text-center mb-6">
                      <div className="w-10 h-10 rounded-2xl bg-[var(--accent-purple)]/10 flex items-center justify-center mx-auto mb-3">
                        <Sparkles className="w-5 h-5 text-[var(--accent-purple)]" />
                      </div>
                      <h4 className="text-sm font-semibold text-[var(--text-primary)] mb-1">How can I help?</h4>
                      <p className="text-xs text-[var(--text-secondary)]">
                        This demo assistant replies from pre-written examples about a sample analysis — it is not connected to your live job.
                      </p>
                    </div>
                    <div className="space-y-2">
                      {suggestedPrompts.map((prompt) => {
                        const Icon = prompt.icon;
                        return (
                          <button
                            key={prompt.text}
                            onClick={() => handleSend(prompt.text)}
                            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-card)] hover:border-[var(--accent-purple)]/30 hover:bg-[var(--accent-purple)]/5 transition-all text-left group"
                          >
                            <Icon className="w-4 h-4 text-[var(--accent-purple)] shrink-0" />
                            <span className="flex-1 text-xs text-[var(--text-secondary)] group-hover:text-[var(--text-primary)] transition-colors">{prompt.text}</span>
                            <ArrowRight className="w-3.5 h-3.5 text-[var(--text-muted)] opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
                          </button>
                        );
                      })}
                    </div>
                  </div>
                ) : (
                  <>
                    {messages.map((msg) => (
                      <div
                        key={msg.id}
                        className={cn(
                          'flex gap-2.5',
                          msg.role === 'user' ? 'justify-end' : 'justify-start'
                        )}
                      >
                        {msg.role === 'assistant' && (
                          <div className="w-6 h-6 rounded-full bg-[var(--accent-purple)]/15 flex items-center justify-center shrink-0 mt-0.5">
                            <Sparkles className="w-3 h-3 text-[var(--accent-purple)]" />
                          </div>
                        )}
                        <div
                          className={cn(
                            'max-w-[85%] rounded-xl px-3.5 py-2.5 text-sm leading-relaxed',
                            msg.role === 'user'
                              ? 'bg-[var(--accent-blue)] text-white rounded-tr-md'
                              : 'bg-[var(--accent-purple)]/8 text-[var(--text-primary)] rounded-tl-md border border-[var(--border-subtle)]'
                          )}
                          dangerouslySetInnerHTML={msg.role === 'assistant' ? { __html: sanitizeMarkdown(msg.content) } : undefined}
                        >
                          {msg.role === 'user' && msg.content}
                        </div>
                      </div>
                    ))}
                    {isTyping && (
                      <div className="flex justify-start">
                        <TypingIndicator />
                      </div>
                    )}
                    <div ref={messagesEndRef} />
                  </>
                )}
              </div>

              {/* Input */}
              <div className="p-4 pt-2 border-t border-[var(--border-subtle)] shrink-0">
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    handleSend(input);
                  }}
                  className="flex items-center gap-2"
                >
                  <Input
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Ask about your analysis..."
                    disabled={isTyping}
                    className="flex-1"
                  />
                  <button
                    type="submit"
                    disabled={!input.trim() || isTyping}
                    className="p-2 rounded-lg bg-[var(--accent-purple)] text-white hover:bg-[var(--accent-purple-strong)] disabled:opacity-30 disabled:cursor-not-allowed transition-colors shrink-0"
                  >
                    <Send className="w-4 h-4" />
                  </button>
                </form>
              </div>
            </GlassCard>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
