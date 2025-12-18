export interface DebugInfo {
    intent: string;
    search_query: string;
    filters: {
        genre?: string;
        platform?: string;
        sort_by?: string;
    };
    igdb_context_preview?: string;
}

export interface Message {
    role: 'user' | 'assistant';
    content: string;
    debugInfo?: DebugInfo;
}
