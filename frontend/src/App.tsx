/** App shell: switch between the patient Intake view and the staff Sessions view. */
import { useState } from "react";
import { Intake } from "./pages/Intake";
import { Sessions } from "./pages/Sessions";

type View = "intake" | "sessions";

export default function App() {
  const [view, setView] = useState<View>("intake");

  return (
    <div className="app">
      <nav className="topnav">
        <span className="brand">OPD Intelligence</span>
        <button className={view === "intake" ? "navbtn active" : "navbtn"} onClick={() => setView("intake")}>
          Patient intake
        </button>
        <button
          className={view === "sessions" ? "navbtn active" : "navbtn"}
          onClick={() => setView("sessions")}
        >
          Staff · Sessions &amp; reports
        </button>
      </nav>
      {view === "intake" ? <Intake /> : <Sessions />}
    </div>
  );
}
