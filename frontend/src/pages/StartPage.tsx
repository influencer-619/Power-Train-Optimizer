import { Link } from "react-router-dom";

export default function StartPage() {
  return (
    <div className="min-h-screen grid place-items-center p-8">
      <div className="max-w-2xl w-full rounded-xl border border-pine/20 bg-white/70 p-10 shadow-lg backdrop-blur">
        <div className="text-copper text-xs tracking-[0.14em] uppercase font-semibold mb-3">
          Avaada
        </div>
        <h1 className="font-display text-5xl text-pine leading-none mb-3">
          Data Center <span className="text-copper">PowerTrain</span>
        </h1>
        <p className="text-pine font-semibold mb-4">
          Captive &amp; Hybrid · Energy Cost · CFE
        </p>
        <p className="text-pine/80 mb-8">
          React source entry. The runtime EXE UI is the static SPA in <code>frontend/dist</code>.
          Open the packaged app or run <code>run_dev.bat</code> to use the full interface.
        </p>
        <Link className="inline-block rounded-lg bg-pine text-white px-4 py-3 font-semibold" to="/">
          Use static SPA via backend server
        </Link>
      </div>
    </div>
  );
}
