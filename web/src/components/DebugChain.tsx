import React from 'react';
import { Bot, User, Brain, Database, ArrowDown } from 'lucide-react';
import { Message } from '@/lib/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
    Accordion,
    AccordionContent,
    AccordionItem,
    AccordionTrigger,
} from '@/components/ui/accordion';
import { Badge } from '@/components/ui/badge';

interface DebugChainProps {
    messages: Message[];
}

export function DebugChain({ messages }: DebugChainProps) {
    // We process messages in pairs (User + AI) usually, but we'll just render linearly 
    // and treat AI messages as special expanding nodes.

    return (
        <div className="space-y-8 p-4 max-w-3xl mx-auto">
            {messages.map((msg, i) => (
                <div key={i} className="relative">
                    {/* Connector Line */}
                    {i > 0 && (
                        <div className="absolute left-6 -top-8 bottom-1/2 w-0.5 bg-border -z-10" />
                    )}

                    {msg.role === 'user' ? (
                        <div className="flex items-start gap-4">
                            <div className="bg-primary text-primary-foreground p-3 rounded-full shrink-0 z-10">
                                <User className="w-5 h-5" />
                            </div>
                            <Card className="flex-1 bg-muted/50 border-dashed">
                                <CardHeader className="py-3">
                                    <CardTitle className="text-sm font-medium text-muted-foreground">User Input</CardTitle>
                                </CardHeader>
                                <CardContent className="py-3 font-medium text-lg">
                                    &quot;{msg.content}&quot;
                                </CardContent>
                            </Card>
                        </div>
                    ) : (
                        <div className="space-y-6">
                            {/* 1. BRAIN NODE (If debug info exists) */}
                            {msg.debugInfo && (
                                <div className="flex items-start gap-4 animate-in fade-in slide-in-from-top-4 duration-500">
                                    <div className="bg-purple-500 text-white p-3 rounded-full shrink-0 z-10 border-4 border-background">
                                        <Brain className="w-5 h-5" />
                                    </div>
                                    <Card className="flex-1 border-purple-200 dark:border-purple-900 bg-purple-50/10">
                                        <CardHeader className="py-2 pb-0">
                                            <CardTitle className="text-xs text-purple-600 dark:text-purple-400 uppercase tracking-widest font-bold">Brain Analysis</CardTitle>
                                        </CardHeader>
                                        <CardContent className="py-4 space-y-3">
                                            <div className="flex flex-wrap gap-2">
                                                <Badge variant="outline" className="border-purple-500 text-purple-600">
                                                    Intent: {msg.debugInfo.intent}
                                                </Badge>
                                                {msg.debugInfo.search_query && (
                                                    <Badge variant="secondary">Query: &quot;{msg.debugInfo.search_query}&quot;</Badge>
                                                )}
                                                {msg.debugInfo.filters.genre && (
                                                    <Badge variant="secondary">Genre: {msg.debugInfo.filters.genre}</Badge>
                                                )}
                                                {msg.debugInfo.filters.sort_by && (
                                                    <Badge variant="secondary">Sort: {msg.debugInfo.filters.sort_by}</Badge>
                                                )}
                                                {msg.debugInfo.filters.platform && (
                                                    <Badge variant="secondary">Plat: {msg.debugInfo.filters.platform}</Badge>
                                                )}
                                            </div>
                                        </CardContent>
                                    </Card>
                                </div>
                            )}

                            {/* Connector */}
                            {msg.debugInfo && (
                                <div className="flex justify-start pl-6">
                                    <ArrowDown className="w-4 h-4 text-muted-foreground" />
                                </div>
                            )}

                            {/* 2. TOOL NODE */}
                            {msg.debugInfo?.igdb_context_preview && (
                                <div className="flex items-start gap-4 animate-in fade-in slide-in-from-top-4 duration-700">
                                    <div className="bg-orange-500 text-white p-3 rounded-full shrink-0 z-10 border-4 border-background">
                                        <Database className="w-5 h-5" />
                                    </div>
                                    <div className="flex-1">
                                        <Accordion type="single" collapsible>
                                            <AccordionItem value="item-1" className="border rounded-lg bg-orange-50/10 border-orange-200 dark:border-orange-900 px-4">
                                                <AccordionTrigger className="hover:no-underline py-3">
                                                    <span className="text-xs text-orange-600 dark:text-orange-400 uppercase tracking-widest font-bold">
                                                        IGDB Knowledge Found
                                                    </span>
                                                </AccordionTrigger>
                                                <AccordionContent>
                                                    <pre className="text-xs bg-muted p-2 rounded overflow-auto max-h-40">
                                                        {msg.debugInfo.igdb_context_preview}
                                                    </pre>
                                                </AccordionContent>
                                            </AccordionItem>
                                        </Accordion>
                                    </div>
                                </div>
                            )}

                            {/* Connector */}
                            {msg.debugInfo?.igdb_context_preview && (
                                <div className="flex justify-start pl-6">
                                    <ArrowDown className="w-4 h-4 text-muted-foreground" />
                                </div>
                            )}

                            {/* 3. FINAL RESPONSE NODE */}
                            <div className="flex items-start gap-4 animate-in fade-in slide-in-from-top-4 duration-1000">
                                <div className="bg-muted text-muted-foreground p-3 rounded-full shrink-0 z-10 border-4 border-background">
                                    <Bot className="w-5 h-5" />
                                </div>
                                <Card className="flex-1 shadow-md border-primary/20">
                                    <CardHeader className="py-3">
                                        <CardTitle className="text-sm font-medium text-muted-foreground">Final Answer</CardTitle>
                                    </CardHeader>
                                    <CardContent className="py-3 whitespace-pre-wrap">
                                        {msg.content}
                                    </CardContent>
                                </Card>
                            </div>
                        </div>
                    )}
                </div>
            ))}
        </div>
    );
}
