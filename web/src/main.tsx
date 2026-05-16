import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { App } from "./App";
import "./styles/tokens.css";
import "./styles/layout.css";
import "./styles/components.css";
import "./styles/forms.css";
import "./styles/pages/auth.css";
import "./styles/pages/dashboard.css";
import "./styles/pages/analytics.css";
import "./styles/pages/download.css";
import "./styles/pages/users.css";
import "./styles/pages/courses.css";
import "./styles/pages/lessons.css";
import "./styles/pages/tests.css";
import "./styles/pages/assignments.css";
import "./styles/pages/homework-reviews.css";
import "./styles/pages/tenant.css";
import "./styles/pages/settings.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
);
