interface ApiOptions extends RequestInit {
    skipAuth?: boolean;
    skip401Redirect?: boolean;
}
export declare function apiFetch(url: string, options?: ApiOptions): Promise<Response>;
export declare const api: {
    get: (url: string, options?: ApiOptions) => Promise<Response>;
    post: (url: string, body?: unknown, options?: ApiOptions) => Promise<Response>;
    put: (url: string, body?: unknown, options?: ApiOptions) => Promise<Response>;
    delete: (url: string, options?: ApiOptions) => Promise<Response>;
};
export {};
