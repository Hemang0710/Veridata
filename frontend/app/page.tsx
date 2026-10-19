// Placeholder landing page (spec 004 task 1). The real UI — UploadPanel,
// QuestionBox, AnswerCard, ConfidenceBadge, ShowYourWork — is built in tasks
// 2–5. This only confirms the scaffold reads the backend URL from env.

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export default function Home() {
  return (
    <main style={{ maxWidth: 820, margin: "0 auto", display: "grid", gap: 16 }}>
      <h1>Veridata</h1>
      <p>Verified chat UI — under construction.</p>
      <p style={{ color: "#888" }}>
        Backend API base URL: <code>{API_BASE_URL}</code>
      </p>
    </main>
  );
}
