import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";

// Debug environment variables
console.log('=== Frontend Environment Variables ===')
console.log('VITE_API_BASE_URL:', import.meta.env.VITE_API_BASE_URL)
console.log('VITE_AUTH_URL:', import.meta.env.VITE_AUTH_URL)
console.log('VITE_WS_BASE_URL:', import.meta.env.VITE_WS_BASE_URL)
console.log('VITE_PUBLIC_URL:', import.meta.env.VITE_PUBLIC_URL)
console.log('===================================')

createRoot(document.getElementById("root")!).render(<App />);
