import React from "react";
import ReactDOM from "react-dom/client";

import { ToastProvider } from "@/components/feedback/ToastProvider";

import App from "./App";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ToastProvider>
      <App />
    </ToastProvider>
  </React.StrictMode>,
);
