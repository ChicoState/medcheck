export function App() {
  return (
    <main className="shell">
      <header className="masthead">
        <p className="eyebrow">Personal health workspace</p>
        <span
          className="status"
          aria-label="Application status: scaffold ready"
        >
          <span aria-hidden="true" /> Scaffold ready
        </span>
      </header>

      <section className="intro" aria-labelledby="page-title">
        <p className="kicker">Medcheck</p>
        <h1 id="page-title">A clear starting point for your health records.</h1>
        <p className="summary">
          The React and Vite foundation is ready. Your first workflow will have
          a focused home here once the product details are defined.
        </p>
      </section>

      <section className="next-step" aria-labelledby="next-step-title">
        <p className="card-label">Next step</p>
        <h2 id="next-step-title">Define the first user workflow</h2>
        <p>
          This shell is intentionally small: it proves the browser entrypoint,
          styling pipeline, and accessible React mount without inventing
          application behavior.
        </p>
      </section>
    </main>
  );
}
