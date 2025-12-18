'use client';

import { useState, useRef, useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { Send, Bot, User, Loader2, Bug } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';
import { Message } from '@/lib/types';
import { DebugChain } from '@/components/DebugChain';

// --- Zod Schema ---
const chatSchema = z.object({
  message: z.string().min(1, { message: "Message cannot be empty" }),
});

type ChatFormValues = z.infer<typeof chatSchema>;

// --- Component ---
export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isDebugMode, setIsDebugMode] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const { register, handleSubmit, reset } = useForm<ChatFormValues>({
    resolver: zodResolver(chatSchema),
  });

  const mutation = useMutation({
    mutationFn: async (text: string) => {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      });
      if (!res.ok) throw new Error('Failed to send message');
      return res.json();
    },
    onSuccess: (data) => {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: data.reply,
          debugInfo: data.debug_info // Capture debug info for the chain view
        }
      ]);
    },
    onError: () => {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'Error: Could not reach the AI.' },
      ]);
    },
  });

  const onSubmit = (data: ChatFormValues) => {
    // Add user message immediately
    setMessages((prev) => [...prev, { role: 'user', content: data.message }]);
    mutation.mutate(data.message);
    reset();
  };

  // Scroll to bottom
  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, mutation.isPending, isDebugMode]); // Trigger scroll on mode switch too

  return (
    <main className="flex flex-col h-screen bg-background text-foreground transition-colors duration-500">
      {/* Header */}
      <header className="flex-none p-4 border-b bg-card/50 backdrop-blur supports-[backdrop-filter]:bg-card/20 sticky top-0 z-20">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="p-2 bg-primary/10 rounded-lg">
              <Bot className="w-6 h-6 text-primary" />
            </div>
            <h1 className="text-xl font-bold tracking-tight">GameBrain AI</h1>
          </div>

          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsDebugMode(!isDebugMode)}
            className={cn(
              "gap-2 transition-all hover:bg-muted",
              isDebugMode && "bg-purple-100 text-purple-700 hover:bg-purple-200 dark:bg-purple-900/30 dark:text-purple-300"
            )}
          >
            <Bug className="w-4 h-4" />
            <span className="text-xs font-semibold">{isDebugMode ? 'DEV MODE' : 'CHAT'}</span>
          </Button>
        </div>
      </header>

      {/* Chat Area */}
      <div className={cn(
        "flex-1 overflow-y-auto p-4 space-y-6 transition-colors duration-500",
        isDebugMode ? "bg-slate-50 dark:bg-slate-950/50" : ""
      )}>
        {isDebugMode ? (
          // --- DEBUG CHAIN VIEW ---
          <DebugChain messages={messages} />
        ) : (
          // --- STANDARD CHAT VIEW ---
          <div className="max-w-4xl mx-auto space-y-6 pb-4">
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center h-[50vh] text-muted-foreground text-center space-y-2">
                <Bot className="w-12 h-12 opacity-20" />
                <p className="text-lg font-medium">No messages yet.</p>
                <p className="text-sm">Ask for a game recommendation to get started!</p>
              </div>
            )}

            {messages.map((msg, i) => (
              <div
                key={i}
                className={cn(
                  "flex gap-3 max-w-[85%]",
                  msg.role === 'user' ? "ml-auto flex-row-reverse" : ""
                )}
              >
                <div className={cn(
                  "w-8 h-8 rounded-full flex items-center justify-center shrink-0",
                  msg.role === 'user' ? "bg-primary text-primary-foreground" : "bg-muted"
                )}>
                  {msg.role === 'user' ? <User className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
                </div>

                <div className={cn(
                  "p-4 rounded-2xl whitespace-pre-wrap shadow-sm text-sm leading-relaxed",
                  msg.role === 'user'
                    ? "bg-primary text-primary-foreground rounded-tr-none"
                    : "bg-card border rounded-tl-none"
                )}>
                  {msg.content}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Loading State (Both Views) */}
        {mutation.isPending && (
          <div className="max-w-4xl mx-auto pt-4">
            <div className="flex gap-3 max-w-[85%] animate-pulse">
              <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center shrink-0">
                <Bot className="w-5 h-5 opacity-50" />
              </div>
              <div className="p-4 rounded-2xl bg-card border rounded-tl-none flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span className="text-sm text-muted-foreground">Thinking...</span>
              </div>
            </div>
          </div>
        )}
        <div ref={scrollRef} />
      </div>

      {/* Input Area */}
      <div className="flex-none p-4 border-t bg-background">
        <div className="max-w-4xl mx-auto">
          <form onSubmit={handleSubmit(onSubmit)} className="flex gap-2">
            <Input
              {...register('message')}
              placeholder="Ask about a game..."
              className="flex-1"
              autoComplete="off"
            />
            <Button type="submit" disabled={mutation.isPending} size="icon">
              {mutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            </Button>
          </form>
        </div>
      </div>
    </main>
  );
}
