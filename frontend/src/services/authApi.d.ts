export interface LoginResponse {
    status: string;
    token: string;
    user: {
        id: number;
        username: string;
    };
    expires_at: string;
}
export interface SignupResponse {
    status: string;
    message: string;
    user_id: number;
}
export interface UserResponse {
    id: number;
    username: string;
    created_at: string;
}
export declare const authApi: {
    login(username: string, password: string): Promise<LoginResponse>;
    signup(username: string, password: string): Promise<SignupResponse>;
    validateToken(): Promise<UserResponse | null>;
};
