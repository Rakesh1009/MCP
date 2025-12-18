import React from 'react';
import { Message } from '@/lib/types';
import {
    DebugUserNode,
    DebugBrainNode,
    DebugConnector,
    DebugToolNode,
    DebugBotNode
} from '@/components/debug/DebugNodes';

interface DebugChainProps {
    messages: Message[];
}

export function DebugChain({ messages }: DebugChainProps) {
    return (
        <div className="space-y-8 p-4 max-w-3xl mx-auto">
            {messages.map((msg, i) => (
                <div key={i} className="relative">
                    {/* Main Timeline Connector Line */}
                    {i > 0 && (
                        <div className="absolute left-6 -top-8 bottom-1/2 w-0.5 bg-border -z-10" />
                    )}

                    {msg.role === 'user' ? (
                        <DebugUserNode content={msg.content} />
                    ) : (
                        <div className="space-y-6">
                            {/* 1. BRAIN NODE */}
                            {msg.debugInfo && (
                                <>
                                    <DebugBrainNode debugInfo={msg.debugInfo} />
                                    <DebugConnector />
                                </>
                            )}

                            {/* 2. TOOL NODE */}
                            {msg.debugInfo?.igdb_context_preview && (
                                <>
                                    <DebugToolNode context={msg.debugInfo.igdb_context_preview} />
                                    <DebugConnector />
                                </>
                            )}

                            {/* 3. FINAL RESPONSE NODE */}
                            <DebugBotNode content={msg.content} />
                        </div>
                    )}
                </div>
            ))}
        </div>
    );
}
