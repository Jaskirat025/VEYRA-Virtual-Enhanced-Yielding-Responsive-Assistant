import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { VeyraProvider } from "./lib/useVeyra";
import { MiniWidget } from "./screens/MiniWidget";
import "./index.css";

const mini = new URLSearchParams(window.location.search).get("mini") === "1";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <VeyraProvider>{mini ? <MiniWidget /> : <App />}</VeyraProvider>
  </React.StrictMode>,
);
