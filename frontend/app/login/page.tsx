"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button, Card } from "@/components/ui";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });
    if (!response.ok) {
      setError("Invalid admin credentials");
      return;
    }
    const data = await response.json();
    localStorage.setItem("roiscraft_token", data.access_token);
    router.push("/dashboard");
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-6">
      <Card className="w-full max-w-md p-6">
        <div className="mb-6">
          <p className="text-sm text-gold">ROISCRAFT Intelligence</p>
          <h1 className="text-2xl font-semibold">Admin access</h1>
        </div>
        <form className="space-y-4" onSubmit={submit}>
          <input className="h-11 w-full rounded-md border border-line bg-ink px-3 outline-none focus:border-gold" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
          <input className="h-11 w-full rounded-md border border-line bg-ink px-3 outline-none focus:border-gold" placeholder="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          {error ? <p className="text-sm text-coral">{error}</p> : null}
          <Button className="w-full" type="submit">Sign in</Button>
        </form>
      </Card>
    </main>
  );
}
