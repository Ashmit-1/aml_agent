import type { ChatMessage } from '../types';
export declare const chatService: {
    getHealth(): Promise<any>;
    streamChat(message: string, history: ChatMessage[]): AsyncGenerator<{
        type: string;
        data: any;
    } | {
        type: string;
        data?: undefined;
    }, void, unknown>;
};
