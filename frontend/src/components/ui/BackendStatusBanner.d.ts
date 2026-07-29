/**
 * Fixed banner at the top of the page that checks backend health on mount.
 * Shows a red warning banner when the backend is unreachable.
 * Retries every 30s while offline. Dismissable by the user.
 */
export declare const BackendStatusBanner: () => import("react").JSX.Element | null;
