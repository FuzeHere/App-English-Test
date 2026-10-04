export const API_BASE_URL =
  typeof window !== "undefined"
    ? (process.env.NEXT_PUBLIC_API_BASE_URL ?? "")
    : (process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000");

async function apiRequest<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers || {}),
    },
    ...options,
  });

  if (!res.ok) {
    let errDetail = `HTTP ${res.status}`;
    try {
      const data = await res.json();
      if (data.detail) {
        errDetail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
      }
    } catch {
      // ignore
    }
    throw new Error(errDetail);
  }
  return res.json();
}

export const api = {
  // Dashboard
  getDashboardSummary: () => apiRequest<any>("/api/dashboard/summary"),
  getRecentSessions: () => apiRequest<any>("/api/dashboard/recent-sessions"),
  getFocusAreas: () => apiRequest<any>("/api/dashboard/focus-areas"),

  // Practice
  startPractice: (payload: {
    skill: string;
    timed: boolean;
    target_units?: number;
    writing_part_mode?: string;
    task_type_filter?: string | null;
  }) =>
    apiRequest<any>("/api/practice/start", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getNextPracticeItem: (sessionId: string) =>
    apiRequest<any>(`/api/practice/${sessionId}/next`),
  submitPracticeAnswer: (sessionId: string, payload: any) =>
    apiRequest<any>(`/api/practice/${sessionId}/answer`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  finishPractice: (sessionId: string) =>
    apiRequest<any>(`/api/practice/${sessionId}/finish`, {
      method: "POST",
    }),

  // Full Simulation
  startSimulation: (includedSkills: string[] = ["reading", "listening", "writing"]) =>
    apiRequest<any>("/api/simulations/start", {
      method: "POST",
      body: JSON.stringify({ included_skills: includedSkills }),
    }),
  getCurrentSimulationState: (sessionId: string) =>
    apiRequest<any>(`/api/simulations/${sessionId}/current`),
  submitSimulationAnswer: (sessionId: string, payload: any) =>
    apiRequest<any>(`/api/simulations/${sessionId}/answer`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  finishSimulationModule: (sessionId: string) =>
    apiRequest<any>(`/api/simulations/${sessionId}/module/finish`, {
      method: "POST",
    }),
  finishSimulation: (sessionId: string) =>
    apiRequest<any>(`/api/simulations/${sessionId}/finish`, {
      method: "POST",
    }),

  // Results & History
  getResults: (sessionId: string) => apiRequest<any>(`/api/results/${sessionId}`),
  getHistory: () => apiRequest<any>("/api/history"),
  deleteHistorySession: (sessionId: string) =>
    apiRequest<any>(`/api/history/${sessionId}`, { method: "DELETE" }),
  deleteAllHistory: () =>
    apiRequest<any>("/api/history", { method: "DELETE" }),

  // Content Studio
  getBankHealth: () => apiRequest<any>("/api/content/bank-health"),
  generateContent: (payload: {
    skill: string;
    task_type: string;
    target_levels: string[];
    quantity: number;
    provider: string;
  }) =>
    apiRequest<any>("/api/content/generate", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getReviewQueue: () => apiRequest<any>("/api/content/review-queue"),
  getApprovedBank: (skill?: string) =>
    apiRequest<any>(`/api/content/approved${skill ? `?skill=${skill}` : ""}`),
  approveContent: (id: string) =>
    apiRequest<any>(`/api/content/${id}/approve`, { method: "POST" }),
  rejectContent: (id: string) =>
    apiRequest<any>(`/api/content/${id}/reject`, { method: "POST" }),
  regenerateContent: (id: string) =>
    apiRequest<any>(`/api/content/${id}/regenerate`, { method: "POST" }),
  updateContent: (id: string, payload: any) =>
    apiRequest<any>(`/api/content/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  deleteContent: (id: string) =>
    apiRequest<any>(`/api/content/${id}`, { method: "DELETE" }),
  deleteAllBank: (skill?: string) =>
    apiRequest<any>(`/api/content/bank/all${skill ? `?skill=${skill}` : ""}`, {
      method: "DELETE",
    }),
  resetDefaultBank: () =>
    apiRequest<any>("/api/content/bank/reset-default", { method: "POST" }),

  // Settings & AI Health
  getSettingsAI: () => apiRequest<any>("/api/settings/ai"),
  updateSettingsAI: (payload: any) =>
    apiRequest<any>("/api/settings/ai", {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  testAIConnections: () =>
    apiRequest<any>("/api/settings/ai/health-check", { method: "POST" }),
  previewTTS: (voice: string) =>
    apiRequest<any>(`/api/tts/preview?voice=${encodeURIComponent(voice)}`, {
      method: "POST",
    }),
};
