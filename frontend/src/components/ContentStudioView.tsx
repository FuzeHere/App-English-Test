"use client";

import React, { useEffect, useState, useRef } from "react";
import {
  Database,
  Sparkles,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Edit3,
  AlertTriangle,
  Volume2,
  Trash2,
  Play,
  Pause,
  RotateCcw,
} from "lucide-react";
import { api, API_BASE_URL } from "@/lib/api";

const TASK_OPTIONS_BY_SKILL: Record<string, { code: string; label: string }[]> = {
  reading: [
    { code: "RT-01", label: "RT-01 — Open Cloze (5 gaps)" },
    { code: "RT-02", label: "RT-02 — Multiple-choice Cloze (5 gaps)" },
    { code: "RT-03", label: "RT-03 — Cross Text Matching (4 texts)" },
    { code: "RT-04", label: "RT-04 — Discrete Cloze (1 gap)" },
    { code: "RT-05", label: "RT-05 — Discrete with a Graphic" },
    { code: "RT-06", label: "RT-06 — Gapped Text: Sentences" },
    { code: "RT-07", label: "RT-07 — Gapped Text: Paragraphs" },
    { code: "RT-08", label: "RT-08 — Comprehension: 5 Items" },
    { code: "RT-09", label: "RT-09 — Comprehension: 2 Items" },
  ],
  listening: [
    { code: "LT-01", label: "LT-01 — 1-Item Comprehension" },
    { code: "LT-02", label: "LT-02 — 2-Item Comprehension" },
    { code: "LT-03", label: "LT-03 — 5-Item Comprehension" },
  ],
  writing: [
    { code: "WT-01", label: "Part 1 — Email (Min 50 words)" },
    { code: "WT-02", label: "Part 2 — Wider-audience Writing (Min 180 words)" },
  ],
};

export default function ContentStudioView() {
  const [subTab, setSubTab] = useState<"health" | "generate" | "review" | "approved">("health");
  const [bankHealth, setBankHealth] = useState<any>(null);
  const [reviewQueue, setReviewQueue] = useState<{ questions: any[]; writing_prompts: any[] }>({
    questions: [],
    writing_prompts: [],
  });
  const [approvedBank, setApprovedBank] = useState<{ questions: any[]; writing_prompts: any[] }>({
    questions: [],
    writing_prompts: [],
  });

  // Generator Form State
  const [genSkill, setGenSkill] = useState<string>("reading");
  const [genTaskType, setGenTaskType] = useState<string>("RT-04");
  const [genLevels, setGenLevels] = useState<string[]>(["B1", "B2"]);
  const [genQuantity, setGenQuantity] = useState<number>(2);
  const [genProvider, setGenProvider] = useState<string>("lm_studio");
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  // Edit Item Modal State
  const [editingItem, setEditingItem] = useState<any | null>(null);
  const [editExplanation, setEditExplanation] = useState<string>("");
  const [editCefr, setEditCefr] = useState<string>("B1");
  const [editTheta, setEditTheta] = useState<number>(0.0);

  // Live Audio Preview State
  const [playingAudioId, setPlayingAudioId] = useState<string | null>(null);
  const currentAudioRef = useRef<HTMLAudioElement | null>(null);

  // Danger / Reset Modals State
  const [confirmClearAllModal, setConfirmClearAllModal] = useState<boolean>(false);
  const [confirmResetModal, setConfirmResetModal] = useState<boolean>(false);
  const [isProcessingAction, setIsProcessingAction] = useState<boolean>(false);

  const loadAllStudioData = async () => {
    try {
      const [bh, rq, ab] = await Promise.all([
        api.getBankHealth(),
        api.getReviewQueue(),
        api.getApprovedBank(),
      ]);
      setBankHealth(bh);
      setReviewQueue(rq);
      setApprovedBank(ab);
    } catch (e: any) {
      setStatusMsg(`Error: ${e.message}`);
    }
  };

  useEffect(() => {
    loadAllStudioData();
  }, []);

  const toggleLevel = (lvl: string) => {
    setGenLevels((prev) =>
      prev.includes(lvl) ? prev.filter((x) => x !== lvl) : [...prev, lvl]
    );
  };

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsGenerating(true);
    setStatusMsg(null);
    try {
      const res = await api.generateContent({
        skill: genSkill,
        task_type: genTaskType,
        target_levels: genLevels.length ? genLevels : ["B1"],
        quantity: genQuantity,
        provider: genProvider,
      });
      setStatusMsg(
        `Berhasil membuat ${res.generated_count} item baru. Item telah masuk ke Review Queue untuk divalidasi & disetujui.`
      );
      await loadAllStudioData();
      setSubTab("review");
    } catch (err: any) {
      setStatusMsg(`Gagal membuat konten: ${err.message}`);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleApprove = async (id: string) => {
    try {
      await api.approveContent(id);
      setStatusMsg("Item berhasil disetujui (APPROVED) dan kini aktif di Question Bank.");
      await loadAllStudioData();
    } catch (err: any) {
      setStatusMsg(`Gagal menyetujui item: ${err.message}`);
    }
  };

  const handleReject = async (id: string) => {
    try {
      await api.rejectContent(id);
      setStatusMsg("Item ditolak (REJECTED).");
      await loadAllStudioData();
    } catch (err: any) {
      setStatusMsg(`Error: ${err.message}`);
    }
  };

  const handleRegenerate = async (id: string) => {
    try {
      await api.regenerateContent(id);
      setStatusMsg("Item berhasil dibuat ulang (Regenerated) dan masuk ke Review Queue.");
      await loadAllStudioData();
    } catch (err: any) {
      setStatusMsg(`Error: ${err.message}`);
    }
  };

  const handleSaveEdit = async () => {
    if (!editingItem) return;
    try {
      await api.updateContent(editingItem.id, {
        cefr_target: editCefr,
        difficulty_theta: editTheta,
        explanation: editExplanation,
      });
      setEditingItem(null);
      setStatusMsg(
        "Perubahan disimpan! Versi konten dinaikkan (version + 1) dan status kembali ke REVIEW sesuai aturan integritas."
      );
      await loadAllStudioData();
    } catch (err: any) {
      setStatusMsg(`Gagal menyimpan perubahan: ${err.message}`);
    }
  };

  const handleToggleLiveAudio = (id: string, url: string, transcript?: string) => {
    if (playingAudioId === id) {
      if (currentAudioRef.current) {
        currentAudioRef.current.pause();
        currentAudioRef.current = null;
      }
      if (typeof window !== "undefined" && "speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
      setPlayingAudioId(null);
      return;
    }

    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current = null;
    }
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }

    const fullUrl = url.startsWith("http") ? url : `${API_BASE_URL}${url}?t=${Date.now()}`;
    const audio = new Audio(fullUrl);
    currentAudioRef.current = audio;
    setPlayingAudioId(id);

    audio.onended = () => {
      setPlayingAudioId((curr) => (curr === id ? null : curr));
      currentAudioRef.current = null;
    };

    audio.onerror = () => {
      // Fallback to browser SpeechSynthesis if audio file is not playable
      if (transcript && typeof window !== "undefined" && "speechSynthesis" in window) {
        window.speechSynthesis.cancel();
        const u = new SpeechSynthesisUtterance(transcript);
        u.lang = "en-US";
        u.onend = () => setPlayingAudioId(null);
        u.onerror = () => setPlayingAudioId(null);
        window.speechSynthesis.speak(u);
      } else {
        setPlayingAudioId(null);
        setStatusMsg("Audio sedang diputar via speech synthesizer.");
      }
    };

    audio.play().catch(() => {
      if (transcript && typeof window !== "undefined" && "speechSynthesis" in window) {
        window.speechSynthesis.cancel();
        const u = new SpeechSynthesisUtterance(transcript);
        u.lang = "en-US";
        u.onend = () => setPlayingAudioId(null);
        u.onerror = () => setPlayingAudioId(null);
        window.speechSynthesis.speak(u);
      } else {
        setPlayingAudioId(null);
      }
    });
  };

  const handleDeleteItem = async (id: string) => {
    if (!window.confirm("Hapus butir soal ini secara permanen dari database?")) return;
    try {
      await api.deleteContent(id);
      setStatusMsg("Butir soal berhasil dihapus secara permanen.");
      await loadAllStudioData();
    } catch (err: any) {
      setStatusMsg(`Gagal menghapus: ${err.message}`);
    }
  };

  const handleClearAllBank = async () => {
    setIsProcessingAction(true);
    try {
      const res = await api.deleteAllBank();
      setConfirmClearAllModal(false);
      setStatusMsg(
        `Berhasil mengosongkan bank soal (${res.deleted_questions} soal, ${res.deleted_writing} writing prompts dihapus).`
      );
      await loadAllStudioData();
    } catch (err: any) {
      setStatusMsg(`Gagal menghapus bank: ${err.message}`);
    } finally {
      setIsProcessingAction(false);
    }
  };

  const handleResetDefaultBank = async () => {
    setIsProcessingAction(true);
    try {
      await api.resetDefaultBank();
      setConfirmResetModal(false);
      setStatusMsg("Bank soal bawaan berhasil dipulihkan (Reading, Listening & Writing).");
      await loadAllStudioData();
    } catch (err: any) {
      setStatusMsg(`Gagal mereset bank bawaan: ${err.message}`);
    } finally {
      setIsProcessingAction(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900">
            Content Studio — Manajemen Bank Soal
          </h1>
          <p className="text-xs text-slate-600 mt-0.5">
            Pre-generate, validasi skema & kunci jawaban, tinjau, dan setujui soal sebelum digunakan pada ujian adaptif.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Sub-navigation Tabs */}
          <div className="flex items-center gap-1 bg-white p-1 rounded-lg border border-slate-300">
            <button
              id="studio-tab-health"
              type="button"
              onClick={() => setSubTab("health")}
              className={`rounded px-3 py-1.5 text-xs font-semibold transition cursor-pointer ${
                subTab === "health"
                  ? "bg-blue-900 text-white"
                  : "text-slate-700 hover:bg-slate-100"
              }`}
            >
              Bank Health
            </button>
            <button
              id="studio-tab-generate"
              type="button"
              onClick={() => setSubTab("generate")}
              className={`rounded px-3 py-1.5 text-xs font-semibold transition cursor-pointer ${
                subTab === "generate"
                  ? "bg-blue-900 text-white"
                  : "text-slate-700 hover:bg-slate-100"
              }`}
            >
              Generate Bank
            </button>
            <button
              id="studio-tab-review"
              type="button"
              onClick={() => setSubTab("review")}
              className={`rounded px-3 py-1.5 text-xs font-semibold transition cursor-pointer ${
                subTab === "review"
                  ? "bg-blue-900 text-white"
                  : "text-slate-700 hover:bg-slate-100"
              }`}
            >
              Review Queue ({bankHealth?.review_queue_count ?? 0})
            </button>
            <button
              id="studio-tab-approved"
              type="button"
              onClick={() => setSubTab("approved")}
              className={`rounded px-3 py-1.5 text-xs font-semibold transition cursor-pointer ${
                subTab === "approved"
                  ? "bg-blue-900 text-white"
                  : "text-slate-700 hover:bg-slate-100"
              }`}
            >
              Question Bank ({bankHealth?.total_approved_tasks ?? 0})
            </button>
          </div>

          {/* Global Bank Maintenance Actions */}
          <div className="flex items-center gap-1.5">
            <button
              id="studio-reset-bank-btn"
              type="button"
              onClick={() => setConfirmResetModal(true)}
              className="inline-flex items-center gap-1 rounded border border-slate-300 bg-white hover:bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-700 cursor-pointer shadow-xs"
              title="Kembalikan bank soal bawaan sistem"
            >
              <RotateCcw className="h-3.5 w-3.5 text-blue-700" /> Reset Bawaan
            </button>
            <button
              id="studio-clear-all-bank-btn"
              type="button"
              onClick={() => setConfirmClearAllModal(true)}
              className="inline-flex items-center gap-1 rounded border border-rose-300 bg-rose-50 hover:bg-rose-100 px-3 py-1.5 text-xs font-semibold text-rose-800 cursor-pointer shadow-xs"
              title="Hapus seluruh bank soal"
            >
              <Trash2 className="h-3.5 w-3.5 text-rose-600" /> Hapus Semua Bank
            </button>
          </div>
        </div>
      </div>

      {statusMsg && (
        <div className="rounded-lg border border-blue-300 bg-blue-50 px-4 py-3 text-xs font-medium text-blue-950 flex items-center justify-between">
          <span>{statusMsg}</span>
          <button
            type="button"
            onClick={() => setStatusMsg(null)}
            className="text-blue-800 font-bold ml-4 cursor-pointer"
          >
            ✕
          </button>
        </div>
      )}

      {/* TAB 1: BANK HEALTH (PRD Section 21.4) */}
      {subTab === "health" && bankHealth && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Reading Health */}
          <div className="rounded-lg border border-slate-300 bg-white p-5 shadow-xs space-y-3">
            <h2 className="text-sm font-extrabold uppercase tracking-wider text-slate-900 border-b border-slate-200 pb-2.5">
              Reading Bank Health
            </h2>
            <div className="space-y-2 text-xs">
              {(bankHealth.reading || []).map((row: any) => (
                <div
                  key={row.cefr}
                  className="flex items-center justify-between rounded bg-slate-50 px-3 py-2 border border-slate-200"
                >
                  <span className="font-bold text-slate-900">Level {row.cefr}</span>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-slate-700">
                      {row.approved_units} / {row.target_units} unit ({row.approved_tasks} tugas)
                    </span>
                    {row.healthy ? (
                      <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                    ) : (
                      <AlertTriangle className="h-4 w-4 text-amber-600" />
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Listening Health */}
          <div className="rounded-lg border border-slate-300 bg-white p-5 shadow-xs space-y-3">
            <h2 className="text-sm font-extrabold uppercase tracking-wider text-slate-900 border-b border-slate-200 pb-2.5">
              Listening Bank Health
            </h2>
            <div className="space-y-2 text-xs">
              {(bankHealth.listening || []).map((row: any) => (
                <div
                  key={row.cefr}
                  className="flex items-center justify-between rounded bg-slate-50 px-3 py-2 border border-slate-200"
                >
                  <span className="font-bold text-slate-900">Level {row.cefr}</span>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-slate-700">
                      {row.approved_units} / {row.target_units} unit ({row.approved_tasks} tugas)
                    </span>
                    {row.healthy ? (
                      <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                    ) : (
                      <AlertTriangle className="h-4 w-4 text-amber-600" />
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Writing Health */}
          <div className="rounded-lg border border-slate-300 bg-white p-5 shadow-xs space-y-3">
            <h2 className="text-sm font-extrabold uppercase tracking-wider text-slate-900 border-b border-slate-200 pb-2.5">
              Writing Prompts Health
            </h2>
            <div className="space-y-2 text-xs">
              <div className="flex items-center justify-between rounded bg-slate-50 px-3 py-2.5 border border-slate-200">
                <span className="font-bold text-slate-900">Part 1 — Email Prompts</span>
                <span className="font-mono text-slate-700">
                  {bankHealth.writing?.part1_approved} / {bankHealth.writing?.part1_target} ✓
                </span>
              </div>
              <div className="flex items-center justify-between rounded bg-slate-50 px-3 py-2.5 border border-slate-200">
                <span className="font-bold text-slate-900">Part 2 — Wider-Audience Prompts</span>
                <span className="font-mono text-slate-700">
                  {bankHealth.writing?.part2_approved} / {bankHealth.writing?.part2_target} ✓
                </span>
              </div>
            </div>
            <div className="pt-2">
              <button
                type="button"
                onClick={() => setSubTab("generate")}
                className="w-full inline-flex items-center justify-center gap-2 rounded-md bg-blue-900 hover:bg-blue-800 px-4 py-2.5 text-xs font-semibold text-white cursor-pointer"
              >
                <Sparkles className="h-4 w-4" /> Buat Soal Baru (Generate)
              </button>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: GENERATE BANK (PRD Section 21.2) */}
      {subTab === "generate" && (
        <form
          onSubmit={handleGenerate}
          className="max-w-2xl rounded-lg border border-slate-300 bg-white p-6 shadow-xs space-y-5"
        >
          <h2 className="text-base font-extrabold text-slate-900 border-b border-slate-200 pb-3">
            Generate Original Question Bank Items
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold uppercase text-slate-700 mb-1.5">
                Skill
              </label>
              <select
                id="studio-gen-skill"
                value={genSkill}
                onChange={(e) => {
                  const sk = e.target.value;
                  setGenSkill(sk);
                  setGenTaskType(TASK_OPTIONS_BY_SKILL[sk][0].code);
                }}
                className="w-full rounded border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900"
              >
                <option value="reading">Reading</option>
                <option value="listening">Listening</option>
                <option value="writing">Writing</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold uppercase text-slate-700 mb-1.5">
                Task Type
              </label>
              <select
                id="studio-gen-task-type"
                value={genTaskType}
                onChange={(e) => setGenTaskType(e.target.value)}
                className="w-full rounded border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900"
              >
                {(TASK_OPTIONS_BY_SKILL[genSkill] || []).map((t) => (
                  <option key={t.code} value={t.code}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold uppercase text-slate-700 mb-2">
              Target CEFR Levels
            </label>
            <div className="flex flex-wrap gap-3">
              {["A1", "A2", "B1", "B2", "C1"].map((lvl) => {
                const checked = genLevels.includes(lvl);
                return (
                  <label
                    key={lvl}
                    className={`inline-flex items-center gap-2 rounded border px-3.5 py-2 text-xs font-bold cursor-pointer ${
                      checked
                        ? "border-blue-800 bg-blue-50 text-blue-950"
                        : "border-slate-300 bg-white text-slate-700"
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggleLevel(lvl)}
                      className="accent-blue-900"
                    />
                    <span>{lvl}</span>
                  </label>
                );
              })}
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold uppercase text-slate-700 mb-1.5">
                Quantity (Jumlah Item)
              </label>
              <input
                id="studio-gen-quantity"
                type="number"
                min={1}
                max={10}
                value={genQuantity}
                onChange={(e) => setGenQuantity(parseInt(e.target.value || "1", 10))}
                className="w-full rounded border border-slate-300 px-3 py-2 text-sm text-slate-900"
              />
            </div>

            <div>
              <label className="block text-xs font-bold uppercase text-slate-700 mb-1.5">
                AI Provider
              </label>
              <select
                id="studio-gen-provider"
                value={genProvider}
                onChange={(e) => setGenProvider(e.target.value)}
                className="w-full rounded border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900"
              >
                <option value="lm_studio">LM Studio (Local)</option>
                <option value="openai">OpenAI API</option>
                <option value="gemini">Gemini API</option>
              </select>
            </div>
          </div>

          <button
            id="studio-generate-submit-btn"
            type="submit"
            disabled={isGenerating}
            className="inline-flex items-center gap-2 rounded-md bg-blue-900 hover:bg-blue-800 px-5 py-2.5 text-sm font-semibold text-white cursor-pointer"
          >
            <Sparkles className="h-4 w-4" />
            <span>{isGenerating ? "Sedang Membuat & Memvalidasi..." : "Generate"}</span>
          </button>
        </form>
      )}

      {/* TAB 3: REVIEW QUEUE (PRD Section 21.3) */}
      {subTab === "review" && (
        <div className="space-y-4">
          {reviewQueue.questions.length === 0 && reviewQueue.writing_prompts.length === 0 ? (
            <div className="rounded-lg border border-slate-300 bg-white p-8 text-center text-sm text-slate-600">
              Antrean Review kosong. Semua soal telah ditinjau atau gunakan tab Generate untuk membuat soal baru.
            </div>
          ) : (
            <>
              {reviewQueue.questions.map((q: any) => (
                <div
                  key={q.id}
                  className="rounded-lg border border-slate-300 bg-white p-5 shadow-xs space-y-3"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 pb-3">
                    <div className="flex items-center gap-2">
                      <span className="rounded bg-amber-100 text-amber-900 px-2 py-0.5 text-xs font-bold">
                        STATUS: {q.status} (v{q.version})
                      </span>
                      <span className="text-sm font-bold text-slate-900">
                        {q.skill.toUpperCase()} • {q.task_type_label}
                      </span>
                      <span className="rounded bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-800">
                        CEFR: {q.cefr_target} (θ = {q.difficulty_theta})
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      {q.audio && (
                        <button
                          type="button"
                          onClick={() => handleToggleLiveAudio(q.id, q.audio.url, q.content_json?.transcript)}
                          className={`inline-flex items-center gap-1.5 rounded border px-2.5 py-1.5 text-xs font-semibold transition cursor-pointer ${
                            playingAudioId === q.id
                              ? "border-amber-400 bg-amber-50 text-amber-900 animate-pulse"
                              : "border-slate-300 bg-slate-50 hover:bg-slate-100 text-slate-800"
                          }`}
                        >
                          {playingAudioId === q.id ? (
                            <>
                              <Pause className="h-3.5 w-3.5 text-amber-700" />
                              <span>Stop Preview</span>
                            </>
                          ) : (
                            <>
                              <Volume2 className="h-3.5 w-3.5 text-blue-700" />
                              <span>Dengar ({q.audio.duration_seconds}s)</span>
                            </>
                          )}
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => handleApprove(q.id)}
                        className="inline-flex items-center gap-1 rounded bg-emerald-700 hover:bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white cursor-pointer"
                      >
                        <CheckCircle2 className="h-3.5 w-3.5" /> Approve
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setEditingItem(q);
                          setEditCefr(q.cefr_target);
                          setEditTheta(q.difficulty_theta);
                          setEditExplanation(q.explanation);
                        }}
                        className="inline-flex items-center gap-1 rounded border border-slate-300 bg-white hover:bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-700 cursor-pointer"
                      >
                        <Edit3 className="h-3.5 w-3.5" /> Edit
                      </button>
                      <button
                        type="button"
                        onClick={() => handleRegenerate(q.id)}
                        className="inline-flex items-center gap-1 rounded border border-slate-300 bg-white hover:bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-700 cursor-pointer"
                      >
                        <RefreshCw className="h-3.5 w-3.5" /> Regenerate
                      </button>
                      <button
                        type="button"
                        onClick={() => handleReject(q.id)}
                        className="inline-flex items-center gap-1 rounded border border-rose-300 bg-rose-50 hover:bg-rose-100 px-3 py-1.5 text-xs font-semibold text-rose-800 cursor-pointer"
                      >
                        <XCircle className="h-3.5 w-3.5" /> Reject
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDeleteItem(q.id)}
                        className="inline-flex items-center gap-1 rounded border border-rose-200 bg-rose-50 hover:bg-rose-100 px-2.5 py-1.5 text-xs font-semibold text-rose-700 cursor-pointer"
                        title="Hapus permanen dari database"
                      >
                        <Trash2 className="h-3.5 w-3.5" /> Hapus
                      </button>
                    </div>
                  </div>

                  <div className="text-xs text-slate-700 space-y-1.5">
                    <p>
                      <strong>Topik / Skenario:</strong> {q.primary_topic} — {q.scenario}
                    </p>
                    <p>
                      <strong>Cuplikan Konten:</strong>{" "}
                      {q.content_json?.title || q.content_json?.stem || JSON.stringify(q.content_json).slice(0, 180)}
                    </p>
                    <p>
                      <strong>Penjelasan Kunci:</strong> {q.explanation}
                    </p>
                    {q.validation_report && (
                      <div className="rounded bg-slate-50 p-2 border border-slate-200 font-mono text-[11px]">
                        Validation:{" "}
                        {q.validation_report.valid ? "✓ VALID" : `⚠ ERRORS: ${q.validation_report.errors?.join(", ")}`}
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {reviewQueue.writing_prompts.map((w: any) => (
                <div
                  key={w.id}
                  className="rounded-lg border border-slate-300 bg-white p-5 shadow-xs space-y-3"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 pb-3">
                    <div className="flex items-center gap-2">
                      <span className="rounded bg-amber-100 text-amber-900 px-2 py-0.5 text-xs font-bold">
                        STATUS: {w.status}
                      </span>
                      <span className="text-sm font-bold text-slate-900">
                        WRITING Part {w.task_part} ({w.text_type}) • CEFR {w.cefr_target}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => handleApprove(w.id)}
                        className="inline-flex items-center gap-1 rounded bg-emerald-700 hover:bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white cursor-pointer"
                      >
                        <CheckCircle2 className="h-3.5 w-3.5" /> Approve
                      </button>
                      <button
                        type="button"
                        onClick={() => handleReject(w.id)}
                        className="inline-flex items-center gap-1 rounded border border-rose-300 bg-rose-50 hover:bg-rose-100 px-3 py-1.5 text-xs font-semibold text-rose-800 cursor-pointer"
                      >
                        <XCircle className="h-3.5 w-3.5" /> Reject
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDeleteItem(w.id)}
                        className="inline-flex items-center gap-1 rounded border border-rose-200 bg-rose-50 hover:bg-rose-100 px-2.5 py-1.5 text-xs font-semibold text-rose-700 cursor-pointer"
                        title="Hapus prompt ini"
                      >
                        <Trash2 className="h-3.5 w-3.5" /> Hapus
                      </button>
                    </div>
                  </div>
                  <p className="text-xs text-slate-800 whitespace-pre-line">{w.prompt_text}</p>
                </div>
              ))}
            </>
          )}
        </div>
      )}

      {/* TAB 4: APPROVED QUESTION BANK */}
      {subTab === "approved" && (
        <div className="space-y-3">
          {approvedBank.questions.map((q: any) => (
            <div
              key={q.id}
              className="rounded-lg border border-slate-300 bg-white p-4 shadow-xs flex flex-wrap items-center justify-between gap-4"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="rounded bg-emerald-100 text-emerald-900 px-2 py-0.5 text-[11px] font-bold">
                    APPROVED (v{q.version})
                  </span>
                  <span className="text-xs font-bold uppercase text-slate-900">
                    {q.skill} • {q.task_type_label}
                  </span>
                  <span className="rounded bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-700">
                    {q.cefr_target} (θ = {q.difficulty_theta})
                  </span>
                </div>
                <p className="text-xs text-slate-700">
                  {q.content_json?.title || q.content_json?.stem}
                </p>
              </div>

              <div className="flex items-center gap-2">
                {q.audio && (
                  <button
                    type="button"
                    onClick={() => handleToggleLiveAudio(q.id, q.audio.url, q.content_json?.transcript)}
                    className={`inline-flex items-center gap-1.5 rounded border px-3 py-1 text-xs font-semibold transition cursor-pointer ${
                      playingAudioId === q.id
                        ? "border-amber-400 bg-amber-50 text-amber-900 animate-pulse"
                        : "border-slate-300 bg-slate-50 hover:bg-slate-100 text-slate-800"
                    }`}
                  >
                    {playingAudioId === q.id ? (
                      <>
                        <Pause className="h-3.5 w-3.5 text-amber-700" />
                        <span>Stop</span>
                      </>
                    ) : (
                      <>
                        <Volume2 className="h-3.5 w-3.5 text-blue-700" />
                        <span>Dengar ({q.audio.duration_seconds}s)</span>
                      </>
                    )}
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => {
                    setEditingItem(q);
                    setEditCefr(q.cefr_target);
                    setEditTheta(q.difficulty_theta);
                    setEditExplanation(q.explanation);
                  }}
                  className="inline-flex items-center gap-1 rounded border border-slate-300 bg-white hover:bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-700 cursor-pointer"
                >
                  <Edit3 className="h-3.5 w-3.5" /> Edit Metadata
                </button>
                <button
                  type="button"
                  onClick={() => handleDeleteItem(q.id)}
                  className="inline-flex items-center gap-1 rounded border border-rose-200 bg-rose-50 hover:bg-rose-100 px-2.5 py-1 text-xs font-semibold text-rose-700 cursor-pointer"
                  title="Hapus soal ini"
                >
                  <Trash2 className="h-3.5 w-3.5" /> Hapus
                </button>
              </div>
            </div>
          ))}

          {/* Approved Writing Prompts */}
          {approvedBank.writing_prompts?.map((w: any) => (
            <div
              key={w.id}
              className="rounded-lg border border-slate-300 bg-white p-4 shadow-xs flex flex-wrap items-center justify-between gap-4"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="rounded bg-emerald-100 text-emerald-900 px-2 py-0.5 text-[11px] font-bold">
                    APPROVED
                  </span>
                  <span className="text-xs font-bold uppercase text-slate-900">
                    WRITING • Part {w.task_part} ({w.text_type})
                  </span>
                  <span className="rounded bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-700">
                    CEFR: {w.cefr_target} (Min {w.minimum_words} kata)
                  </span>
                </div>
                <p className="text-xs text-slate-700 line-clamp-2">{w.prompt_text}</p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => handleDeleteItem(w.id)}
                  className="inline-flex items-center gap-1 rounded border border-rose-200 bg-rose-50 hover:bg-rose-100 px-2.5 py-1 text-xs font-semibold text-rose-700 cursor-pointer"
                  title="Hapus prompt ini"
                >
                  <Trash2 className="h-3.5 w-3.5" /> Hapus
                </button>
              </div>
            </div>
          ))}

          {approvedBank.questions.length === 0 && (!approvedBank.writing_prompts || approvedBank.writing_prompts.length === 0) && (
            <div className="text-center py-12 rounded-lg border border-dashed border-slate-300 bg-slate-50 text-slate-600 text-xs space-y-2">
              <p className="font-semibold text-sm text-slate-800">Bank soal saat ini kosong.</p>
              <p>Anda dapat membuat soal baru di tab <strong>Generate Bank</strong> atau memulihkan bank standar dengan tombol <strong>Reset Bawaan</strong> di atas.</p>
            </div>
          )}
        </div>
      )}

      {/* Confirmation Modal: Clear All Bank */}
      {confirmClearAllModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4">
          <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-2xl space-y-4">
            <div className="flex items-center gap-3 text-rose-600">
              <AlertTriangle className="h-6 w-6" />
              <h3 className="text-base font-extrabold text-slate-900">
                Kosongkan Seluruh Bank Soal?
              </h3>
            </div>
            <p className="text-xs text-slate-700 leading-relaxed">
              Tindakan ini akan <strong>menghapus permanen</strong> seluruh soal Reading, Listening, dan Writing prompt di database serta berkas audio terkait di semua perangkat.
            </p>
            <p className="text-xs text-amber-800 bg-amber-50 p-2.5 rounded border border-amber-200">
              Catatan: Status penghapusan ini akan tetap tersimpan konsisten dan tidak akan kembali otomatis saat server atau VPS dinyalakan ulang.
            </p>
            <div className="flex justify-end gap-2.5 pt-2">
              <button
                type="button"
                onClick={() => setConfirmClearAllModal(false)}
                disabled={isProcessingAction}
                className="rounded border border-slate-300 px-4 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 cursor-pointer"
              >
                Batal
              </button>
              <button
                type="button"
                onClick={handleClearAllBank}
                disabled={isProcessingAction}
                className="rounded bg-rose-700 hover:bg-rose-800 px-4 py-1.5 text-xs font-semibold text-white cursor-pointer"
              >
                {isProcessingAction ? "Menghapus..." : "Ya, Hapus Semua"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Confirmation Modal: Reset Default Bank */}
      {confirmResetModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4">
          <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-2xl space-y-4">
            <div className="flex items-center gap-3 text-blue-900">
              <RotateCcw className="h-6 w-6" />
              <h3 className="text-base font-extrabold text-slate-900">
                Pulihkan Bank Soal Bawaan?
              </h3>
            </div>
            <p className="text-xs text-slate-700 leading-relaxed">
              Tindakan ini akan menginisialisasi ulang bank soal standar terkalibrasi lengkap (Reading RT-01 s/d RT-09, Listening LT-01 s/d LT-03 dengan suara jernih, dan Writing prompts) pada level A1 hingga C1.
            </p>
            <div className="flex justify-end gap-2.5 pt-2">
              <button
                type="button"
                onClick={() => setConfirmResetModal(false)}
                disabled={isProcessingAction}
                className="rounded border border-slate-300 px-4 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 cursor-pointer"
              >
                Batal
              </button>
              <button
                type="button"
                onClick={handleResetDefaultBank}
                disabled={isProcessingAction}
                className="rounded bg-blue-900 hover:bg-blue-800 px-4 py-1.5 text-xs font-semibold text-white cursor-pointer"
              >
                {isProcessingAction ? "Memulihkan..." : "Ya, Pulihkan Bank Bawaan"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal for Editing Metadata / Explanation (PRD Section 21.3) */}
      {editingItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4">
          <div className="w-full max-w-lg rounded-lg bg-white p-6 shadow-xl space-y-4">
            <h3 className="text-base font-bold text-slate-900">
              Edit Item Metadata & Explanation ({editingItem.task_type})
            </h3>
            <p className="text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded p-2.5">
              Perhatian (PRD 21.3): Mengedit soal yang sudah disetujui akan menaikkan{" "}
              <code>content_version</code> dan mengembalikan status ke <code>REVIEW</code>.
            </p>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">CEFR Target</label>
                <select
                  value={editCefr}
                  onChange={(e) => setEditCefr(e.target.value)}
                  className="w-full rounded border border-slate-300 px-3 py-1.5 text-sm"
                >
                  {["A1", "A2", "B1", "B2", "C1"].map((l) => (
                    <option key={l} value={l}>
                      {l}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  Difficulty Theta (b)
                </label>
                <input
                  type="number"
                  step="0.05"
                  value={editTheta}
                  onChange={(e) => setEditTheta(parseFloat(e.target.value || "0"))}
                  className="w-full rounded border border-slate-300 px-3 py-1.5 text-sm"
                />
              </div>
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Answer Explanation
              </label>
              <textarea
                rows={4}
                value={editExplanation}
                onChange={(e) => setEditExplanation(e.target.value)}
                className="w-full rounded border border-slate-300 p-2.5 text-xs"
              />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setEditingItem(null)}
                className="rounded border border-slate-300 px-4 py-1.5 text-xs font-semibold text-slate-700 cursor-pointer"
              >
                Batal
              </button>
              <button
                type="button"
                onClick={handleSaveEdit}
                className="rounded bg-blue-900 px-4 py-1.5 text-xs font-semibold text-white cursor-pointer"
              >
                Simpan Perubahan
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
