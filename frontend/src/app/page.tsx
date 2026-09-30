"use client";

import React, { useEffect, useState, useCallback } from "react";
import {
  BookOpen,
  Headphones,
  PenTool,
  PlayCircle,
  Clock,
  History,
  Database,
  Settings,
  Info,
  CheckCircle2,
  AlertTriangle,
  Trash2,
  Eye,
  LayoutDashboard,
  Cpu,
  LogOut,
} from "lucide-react";
import { api } from "@/lib/api";
import QuestionRenderer from "@/components/QuestionRenderer";
import WritingWorkspace from "@/components/WritingWorkspace";
import ResultView from "@/components/ResultView";
import ContentStudioView from "@/components/ContentStudioView";
import SettingsAndAboutView from "@/components/SettingsAndAboutView";

type NavView =
  | "dashboard"
  | "practice_setup"
  | "simulation_setup"
  | "active_exam"
  | "result"
  | "history"
  | "studio"
  | "settings"
  | "about";

function formatRemainingTime(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return "Tanpa Batas Waktu";
  const s = Math.max(0, Math.floor(seconds));
  const mins = Math.floor(s / 60);
  const secs = s % 60;
  return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
}

export default function HomePage() {
  const [nav, setNav] = useState<NavView>("dashboard");
  const [errorBanner, setErrorBanner] = useState<string | null>(null);

  // Dashboard state
  const [summary, setSummary] = useState<any>(null);
  const [recentSessions, setRecentSessions] = useState<any[]>([]);
  const [focusAreas, setFocusAreas] = useState<any[]>([]);
  const [historyList, setHistoryList] = useState<any[]>([]);

  // Practice Setup state
  const [practiceSkill, setPracticeSkill] = useState<"reading" | "listening" | "writing">("reading");
  const [practiceTimed, setPracticeTimed] = useState<boolean>(false);
  const [practiceTargetUnits, setPracticeTargetUnits] = useState<number>(10);
  const [practiceTaskFilter, setPracticeTaskFilter] = useState<string>("");
  const [writingPartMode, setWritingPartMode] = useState<"part1" | "part2" | "full">("full");

  // Full Simulation Setup state
  const [simSkills, setSimSkills] = useState<string[]>(["reading", "listening", "writing"]);

  // Active Session / Exam state
  const [activeSessionState, setActiveSessionState] = useState<any>(null);
  const [remainingSeconds, setRemainingSeconds] = useState<number | null>(null);
  const [isSubmittingAnswer, setIsSubmittingAnswer] = useState<boolean>(false);
  const [practiceFeedback, setPracticeFeedback] = useState<any | null>(null);
  const [writingDrafts, setWritingDrafts] = useState<{ part1: string; part2: string }>({
    part1: "",
    part2: "",
  });

  // Result Report state
  const [activeResultReport, setActiveResultReport] = useState<any>(null);

  const loadDashboardData = useCallback(async () => {
    try {
      const [sumData, recData, focData] = await Promise.all([
        api.getDashboardSummary(),
        api.getRecentSessions(),
        api.getFocusAreas(),
      ]);
      setSummary(sumData);
      setRecentSessions(recData.sessions || []);
      setFocusAreas(focData.focus_areas || []);
    } catch (err: any) {
      setErrorBanner(`Gagal memuat data dari server backend: ${err.message}`);
    }
  }, []);

  const loadHistoryData = useCallback(async () => {
    try {
      const h = await api.getHistory();
      setHistoryList(h.history || []);
    } catch (err: any) {
      setErrorBanner(err.message);
    }
  }, []);

  // Recover active session on browser refresh if saved in sessionStorage (PRD Section 30.4)
  useEffect(() => {
    loadDashboardData();
    const savedSessionId =
      typeof window !== "undefined" ? sessionStorage.getItem("cest_active_session_id") : null;
    if (savedSessionId) {
      api
        .getCurrentSimulationState(savedSessionId)
        .then((st) => {
          if (st && !st.is_finished) {
            setActiveSessionState(st);
            setRemainingSeconds(st.timer?.remaining_seconds ?? null);
            setNav("active_exam");
          } else {
            sessionStorage.removeItem("cest_active_session_id");
          }
        })
        .catch(() => {
          sessionStorage.removeItem("cest_active_session_id");
        });
    }
  }, [loadDashboardData]);

  // Client countdown synchronized with authoritative server deadline (PRD Section 30.2 & 30.3)
  useEffect(() => {
    if (nav !== "active_exam" || remainingSeconds === null) return;
    if (remainingSeconds <= 0) {
      // Timeout reached: finalize module automatically
      if (activeSessionState?.session_id) {
        handleForceFinishModule(activeSessionState.session_id);
      }
      return;
    }
    const timer = setInterval(() => {
      setRemainingSeconds((prev) => (prev !== null ? Math.max(0, prev - 1) : null));
    }, 1000);
    return () => clearInterval(timer);
  }, [nav, remainingSeconds, activeSessionState?.session_id]);

  const openSessionResult = async (sessionId: string) => {
    try {
      sessionStorage.removeItem("cest_active_session_id");
      const rep = await api.getResults(sessionId);
      setActiveResultReport(rep);
      setNav("result");
      loadDashboardData();
    } catch (err: any) {
      setErrorBanner(`Gagal memuat hasil sesi: ${err.message}`);
    }
  };

  const handleStartPractice = async (
    overrideSkill?: "reading" | "listening" | "writing"
  ) => {
    setErrorBanner(null);
    const chosenSkill = overrideSkill || practiceSkill;
    try {
      const st = await api.startPractice({
        skill: chosenSkill,
        timed: practiceTimed,
        target_units: practiceTargetUnits,
        writing_part_mode: writingPartMode,
        task_type_filter: practiceTaskFilter || null,
      });
      setPracticeFeedback(null);
      setWritingDrafts({ part1: "", part2: "" });
      setActiveSessionState(st);
      setRemainingSeconds(st.timer?.remaining_seconds ?? null);
      sessionStorage.setItem("cest_active_session_id", st.session_id);
      setNav("active_exam");
    } catch (err: any) {
      setErrorBanner(err.message);
    }
  };

  const handleStartFullSimulation = async () => {
    setErrorBanner(null);
    try {
      const st = await api.startSimulation(
        simSkills.length > 0 ? simSkills : ["reading", "listening", "writing"]
      );
      setPracticeFeedback(null);
      setActiveSessionState(st);
      setRemainingSeconds(st.timer?.remaining_seconds ?? null);
      sessionStorage.setItem("cest_active_session_id", st.session_id);
      setNav("active_exam");
    } catch (err: any) {
      setErrorBanner(err.message);
    }
  };

  const handleSubmitObjective = async (
    answerPayload: any,
    responseTimeSeconds: number
  ) => {
    if (!activeSessionState) return;
    setIsSubmittingAnswer(true);
    setErrorBanner(null);
    const sessionId = activeSessionState.session_id;
    const isSim = activeSessionState.mode === "FULL_SIMULATION";

    try {
      const reqBody = {
        question_id: activeSessionState.question?.question_id,
        answer: answerPayload,
        response_time_seconds: responseTimeSeconds,
      };
      const res = isSim
        ? await api.submitSimulationAnswer(sessionId, reqBody)
        : await api.submitPracticeAnswer(sessionId, reqBody);

      if (!isSim && res.practice_feedback) {
        // Show explanation & correct answer first in Practice Mode before advancing
        setPracticeFeedback(res.practice_feedback);
        setIsSubmittingAnswer(false);
        return;
      }

      if (res.session_finished) {
        await openSessionResult(sessionId);
      } else {
        const nextSt = isSim
          ? await api.getCurrentSimulationState(sessionId)
          : await api.getNextPracticeItem(sessionId);
        if (nextSt.is_finished) {
          await openSessionResult(sessionId);
        } else {
          setActiveSessionState(nextSt);
          setRemainingSeconds(nextSt.timer?.remaining_seconds ?? null);
        }
      }
    } catch (err: any) {
      setErrorBanner(err.message);
    } finally {
      setIsSubmittingAnswer(false);
    }
  };

  const handleProceedNextPractice = async () => {
    if (!activeSessionState) return;
    const sessionId = activeSessionState.session_id;
    setPracticeFeedback(null);
    try {
      const nextSt = await api.getNextPracticeItem(sessionId);
      if (nextSt.is_finished) {
        await openSessionResult(sessionId);
      } else {
        setActiveSessionState(nextSt);
        setRemainingSeconds(nextSt.timer?.remaining_seconds ?? null);
      }
    } catch (err: any) {
      setErrorBanner(err.message);
    }
  };

  const handleSubmitWriting = async (part1Text: string, part2Text: string) => {
    if (!activeSessionState) return;
    setIsSubmittingAnswer(true);
    setErrorBanner(null);
    const sessionId = activeSessionState.session_id;
    const isSim = activeSessionState.mode === "FULL_SIMULATION";

    try {
      const payload = { part1_text: part1Text, part2_text: part2Text };
      const res = isSim
        ? await api.submitSimulationAnswer(sessionId, payload)
        : await api.submitPracticeAnswer(sessionId, payload);

      if (res.session_finished || res.module_finished) {
        const nextSt = await api.getCurrentSimulationState(sessionId);
        if (nextSt.is_finished) {
          await openSessionResult(sessionId);
        } else {
          setActiveSessionState(nextSt);
          setRemainingSeconds(nextSt.timer?.remaining_seconds ?? null);
        }
      }
    } catch (err: any) {
      setErrorBanner(err.message);
    } finally {
      setIsSubmittingAnswer(false);
    }
  };

  const handleForceFinishModule = async (sessionId: string) => {
    if (activeSessionState?.current_module === "writing") {
      await handleSubmitWriting(writingDrafts.part1, writingDrafts.part2);
      return;
    }
    try {
      const st = await api.finishSimulationModule(sessionId);
      if (st.is_finished) {
        await openSessionResult(sessionId);
      } else {
        setPracticeFeedback(null);
        setActiveSessionState(st);
        setRemainingSeconds(st.timer?.remaining_seconds ?? null);
      }
    } catch (err: any) {
      setErrorBanner(err.message);
    }
  };

  const handleDeleteHistoryItem = async (sessionId: string) => {
    try {
      await api.deleteHistorySession(sessionId);
      await loadHistoryData();
      await loadDashboardData();
    } catch (err: any) {
      setErrorBanner(err.message);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900">
      {/* Top Navigation / Exam Status Bar */}
      {nav === "active_exam" && activeSessionState ? (
        <header className="sticky top-0 z-40 border-b border-slate-300 bg-slate-900 text-white px-6 py-3 shadow-xs">
          <div className="mx-auto max-w-7xl flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <span className="rounded bg-blue-700 px-2.5 py-1 text-xs font-extrabold uppercase tracking-wider">
                {activeSessionState.mode === "FULL_SIMULATION"
                  ? "Full Test Simulation — Exam Conditions"
                  : "Practice Mode — Learn While You Test"}
              </span>
              <span className="text-sm font-bold capitalize">
                Modul Aktif: {activeSessionState.current_module}
              </span>
              {activeSessionState.progress && (
                <span className="text-xs text-slate-300 font-mono">
                  Unit Selesai: {activeSessionState.progress.completed_item_units} /{" "}
                  {activeSessionState.progress.target_min_units}
                </span>
              )}
            </div>

            <div className="flex items-center gap-4">
              {/* Fixed Timer Region (PRD Section 48.1 & 48.2) */}
              <div
                id="exam-timer-display"
                className={`flex items-center gap-2 rounded px-3.5 py-1.5 text-xs font-mono font-bold border ${
                  remainingSeconds !== null && remainingSeconds < 300
                    ? "bg-rose-950 border-rose-500 text-rose-200"
                    : "bg-slate-800 border-slate-700 text-slate-100"
                }`}
              >
                <Clock className="h-4 w-4 text-blue-300" />
                <span>Waktu tersisa: {formatRemainingTime(remainingSeconds)}</span>
              </div>

              <button
                id="finish-module-early-btn"
                type="button"
                onClick={() => handleForceFinishModule(activeSessionState.session_id)}
                className="inline-flex items-center gap-1.5 rounded border border-slate-600 bg-slate-800 hover:bg-slate-700 px-3 py-1.5 text-xs font-semibold text-slate-200 cursor-pointer"
              >
                <LogOut className="h-3.5 w-3.5" /> Selesaikan Modul
              </button>
            </div>
          </div>
        </header>
      ) : (
        <header className="sticky top-0 z-40 border-b border-slate-200 bg-white px-6 py-3.5 shadow-2xs">
          <div className="mx-auto max-w-7xl flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => {
                  setNav("dashboard");
                  loadDashboardData();
                }}
                className="flex items-center gap-2.5 text-left cursor-pointer"
              >
                <div className="flex h-9 w-9 items-center justify-center rounded-md bg-blue-950 text-white font-extrabold text-sm">
                  CE
                </div>
                <div>
                  <span className="text-sm font-extrabold tracking-tight text-slate-900 block leading-none">
                    CEST Practice Simulator
                  </span>
                  <span className="text-[11px] font-medium text-slate-500">
                    Reading • Listening • Writing (A1–C1)
                  </span>
                </div>
              </button>
            </div>

            {/* Indonesian Primary Navigation (PRD Section 7 & 47) */}
            <nav className="flex flex-wrap items-center gap-1.5 text-xs font-semibold">
              <button
                id="nav-dashboard"
                type="button"
                onClick={() => {
                  setNav("dashboard");
                  loadDashboardData();
                }}
                className={`inline-flex items-center gap-1.5 rounded-md px-3 py-2 transition cursor-pointer ${
                  nav === "dashboard"
                    ? "bg-blue-950 text-white"
                    : "text-slate-700 hover:bg-slate-100"
                }`}
              >
                <LayoutDashboard className="h-3.5 w-3.5" /> Dashboard
              </button>

              <button
                id="nav-practice"
                type="button"
                onClick={() => setNav("practice_setup")}
                className={`inline-flex items-center gap-1.5 rounded-md px-3 py-2 transition cursor-pointer ${
                  nav === "practice_setup"
                    ? "bg-blue-950 text-white"
                    : "text-slate-700 hover:bg-slate-100"
                }`}
              >
                <BookOpen className="h-3.5 w-3.5" /> Latihan
              </button>

              <button
                id="nav-simulation"
                type="button"
                onClick={() => setNav("simulation_setup")}
                className={`inline-flex items-center gap-1.5 rounded-md px-3 py-2 transition cursor-pointer ${
                  nav === "simulation_setup"
                    ? "bg-blue-950 text-white"
                    : "text-slate-700 hover:bg-slate-100"
                }`}
              >
                <PlayCircle className="h-3.5 w-3.5" /> Simulasi Penuh
              </button>

              <button
                id="nav-history"
                type="button"
                onClick={() => {
                  setNav("history");
                  loadHistoryData();
                }}
                className={`inline-flex items-center gap-1.5 rounded-md px-3 py-2 transition cursor-pointer ${
                  nav === "history"
                    ? "bg-blue-950 text-white"
                    : "text-slate-700 hover:bg-slate-100"
                }`}
              >
                <History className="h-3.5 w-3.5" /> Riwayat
              </button>

              <button
                id="nav-studio"
                type="button"
                onClick={() => setNav("studio")}
                className={`inline-flex items-center gap-1.5 rounded-md px-3 py-2 transition cursor-pointer ${
                  nav === "studio"
                    ? "bg-blue-950 text-white"
                    : "text-slate-700 hover:bg-slate-100"
                }`}
              >
                <Database className="h-3.5 w-3.5" /> Content Studio
              </button>

              <button
                id="nav-settings"
                type="button"
                onClick={() => setNav("settings")}
                className={`inline-flex items-center gap-1.5 rounded-md px-3 py-2 transition cursor-pointer ${
                  nav === "settings"
                    ? "bg-blue-950 text-white"
                    : "text-slate-700 hover:bg-slate-100"
                }`}
              >
                <Settings className="h-3.5 w-3.5" /> Pengaturan
              </button>

              <button
                id="nav-about"
                type="button"
                onClick={() => setNav("about")}
                className={`inline-flex items-center gap-1.5 rounded-md px-3 py-2 transition cursor-pointer ${
                  nav === "about"
                    ? "bg-blue-950 text-white"
                    : "text-slate-700 hover:bg-slate-100"
                }`}
              >
                <Info className="h-3.5 w-3.5" /> Disclaimer
              </button>
            </nav>
          </div>
        </header>
      )}

      {/* Main Content Container */}
      <main className="mx-auto w-full max-w-7xl flex-1 px-6 py-6">
        {errorBanner && (
          <div className="mb-6 rounded-lg border border-rose-300 bg-rose-50 px-4 py-3 text-xs font-medium text-rose-900 flex items-center justify-between">
            <span>{errorBanner}</span>
            <button
              type="button"
              onClick={() => setErrorBanner(null)}
              className="font-bold text-rose-800 ml-4 cursor-pointer"
            >
              ✕
            </button>
          </div>
        )}

        {/* ==================== 1. DASHBOARD VIEW (PRD Section 8) ==================== */}
        {nav === "dashboard" && (
          <div className="space-y-6">
            {/* Top Status & Content Bank Warning if needed */}
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <h1 className="text-2xl font-extrabold text-slate-900">
                  Dashboard Persiapan Ujian
                </h1>
                <p className="text-xs text-slate-600 mt-0.5">
                  Simulator latihan mandiri Reading, Listening, dan Writing (Skala CEFR A1–C1) • Bukan skor resmi Cambridge.
                </p>
              </div>

              <div className="flex items-center gap-3 text-xs">
                <div className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-slate-700">
                  <Cpu className="h-3.5 w-3.5 text-blue-900" />
                  <span>
                    AI Provider:{" "}
                    <strong className="uppercase">
                      {summary?.ai_provider_status?.default_provider || "lm_studio"}
                    </strong>
                  </span>
                </div>
                <div
                  className={`inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 font-medium ${
                    summary?.bank_health?.overall_healthy
                      ? "border-emerald-300 bg-emerald-50 text-emerald-900"
                      : "border-amber-300 bg-amber-50 text-amber-900"
                  }`}
                >
                  {summary?.bank_health?.overall_healthy ? (
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-700" />
                  ) : (
                    <AlertTriangle className="h-3.5 w-3.5 text-amber-700" />
                  )}
                  <span>
                    Question Bank: {summary?.bank_health?.total_approved_tasks ?? 0} Tugas Aktif
                  </span>
                </div>
              </div>
            </div>

            {/* CURRENT ESTIMATED LEVELS & QUICK START ACTIONS (PRD Section 8.2) */}
            <div className="rounded-lg border border-slate-300 bg-white p-6 shadow-xs space-y-6">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 pb-3">
                <h2 className="text-xs font-extrabold uppercase tracking-wider text-slate-700">
                  PERKIRAAN LEVEL SAAT INI (CURRENT ESTIMATED LEVELS)
                </h2>
                {summary?.latest_overall_simulation_level && (
                  <span className="rounded bg-blue-950 text-white px-3 py-1 text-xs font-bold">
                    Perkiraan Level Simulasi Penuh Terakhir: {summary.latest_overall_simulation_level}
                  </span>
                )}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Reading Level Card */}
                <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-5 flex items-center justify-between">
                  <div>
                    <span className="text-xs font-bold uppercase text-slate-500 block">
                      Reading
                    </span>
                    <span
                      id="dashboard-reading-level"
                      className="text-3xl font-extrabold text-slate-900 mt-1 block"
                    >
                      {summary?.estimated_levels?.reading || "Belum diuji"}
                    </span>
                    <span className="text-[11px] text-slate-500 mt-0.5 block">
                      {summary?.confidence_labels?.reading || "9 tipe tugas adaptif (1PL IRT)"}
                    </span>
                  </div>
                  <BookOpen className="h-8 w-8 text-blue-900/80" />
                </div>

                {/* Listening Level Card */}
                <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-5 flex items-center justify-between">
                  <div>
                    <span className="text-xs font-bold uppercase text-slate-500 block">
                      Listening
                    </span>
                    <span
                      id="dashboard-listening-level"
                      className="text-3xl font-extrabold text-slate-900 mt-1 block"
                    >
                      {summary?.estimated_levels?.listening || "Belum diuji"}
                    </span>
                    <span className="text-[11px] text-slate-500 mt-0.5 block">
                      {summary?.confidence_labels?.listening || "1, 2 & 5 butir soal audio"}
                    </span>
                  </div>
                  <Headphones className="h-8 w-8 text-blue-900/80" />
                </div>

                {/* Writing Level Card */}
                <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-5 flex items-center justify-between">
                  <div>
                    <span className="text-xs font-bold uppercase text-slate-500 block">
                      Writing
                    </span>
                    <span
                      id="dashboard-writing-level"
                      className="text-3xl font-extrabold text-slate-900 mt-1 block"
                    >
                      {summary?.estimated_levels?.writing || "Belum diuji"}
                    </span>
                    <span className="text-[11px] text-slate-500 mt-0.5 block">
                      {summary?.confidence_labels?.writing || "Part 1 Email & Part 2 Artikel"}
                    </span>
                  </div>
                  <PenTool className="h-8 w-8 text-blue-900/80" />
                </div>
              </div>

              {/* Action Buttons (PRD Section 8.2) */}
              <div className="flex flex-wrap items-center gap-3 pt-2">
                <button
                  id="btn-start-full-simulation"
                  type="button"
                  onClick={() => setNav("simulation_setup")}
                  className="inline-flex items-center gap-2 rounded-md bg-blue-950 hover:bg-blue-900 px-5 py-3 text-sm font-bold text-white shadow-xs transition cursor-pointer"
                >
                  <PlayCircle className="h-4 w-4" />
                  <span>Mulai Simulasi Penuh (Start Full Test Simulation)</span>
                </button>

                <button
                  id="btn-practice-reading"
                  type="button"
                  onClick={() => {
                    setPracticeSkill("reading");
                    setNav("practice_setup");
                  }}
                  className="inline-flex items-center gap-2 rounded-md border border-slate-300 bg-white hover:bg-slate-50 px-4 py-3 text-xs font-bold text-slate-800 transition cursor-pointer"
                >
                  <BookOpen className="h-4 w-4 text-blue-900" /> Practice Reading
                </button>

                <button
                  id="btn-practice-listening"
                  type="button"
                  onClick={() => {
                    setPracticeSkill("listening");
                    setNav("practice_setup");
                  }}
                  className="inline-flex items-center gap-2 rounded-md border border-slate-300 bg-white hover:bg-slate-50 px-4 py-3 text-xs font-bold text-slate-800 transition cursor-pointer"
                >
                  <Headphones className="h-4 w-4 text-blue-900" /> Practice Listening
                </button>

                <button
                  id="btn-practice-writing"
                  type="button"
                  onClick={() => {
                    setPracticeSkill("writing");
                    setNav("practice_setup");
                  }}
                  className="inline-flex items-center gap-2 rounded-md border border-slate-300 bg-white hover:bg-slate-50 px-4 py-3 text-xs font-bold text-slate-800 transition cursor-pointer"
                >
                  <PenTool className="h-4 w-4 text-blue-900" /> Practice Writing
                </button>
              </div>
            </div>

            {/* Bottom Two Columns: Recent Results Table & Focus Areas (No progress graphs per PRD 8.4) */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              {/* Recent Results Table */}
              <div className="lg:col-span-7 rounded-lg border border-slate-300 bg-white p-6 shadow-xs space-y-4">
                <div className="flex items-center justify-between border-b border-slate-200 pb-3">
                  <h2 className="text-xs font-extrabold uppercase tracking-wider text-slate-700">
                    Hasil Terakhir (Recent Results)
                  </h2>
                  <button
                    type="button"
                    onClick={() => {
                      setNav("history");
                      loadHistoryData();
                    }}
                    className="text-xs font-semibold text-blue-900 hover:underline cursor-pointer"
                  >
                    Lihat Semua Riwayat →
                  </button>
                </div>

                {recentSessions.length === 0 ? (
                  <p className="text-xs text-slate-500 py-6 text-center">
                    Belum ada sesi yang diselesaikan. Pilih Latihan atau Simulasi Penuh di atas untuk memulai.
                  </p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead>
                        <tr className="border-b border-slate-200 text-slate-500 uppercase">
                          <th className="py-2 pr-3">Tanggal</th>
                          <th className="py-2 px-2">Mode</th>
                          <th className="py-2 px-2">Reading</th>
                          <th className="py-2 px-2">Listening</th>
                          <th className="py-2 px-2">Writing</th>
                          <th className="py-2 pl-2 text-right">Aksi</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-200">
                        {recentSessions.map((s: any) => (
                          <tr key={s.session_id} className="hover:bg-slate-50">
                            <td className="py-2.5 pr-3 font-mono text-slate-700">
                              {s.started_at
                                ? new Date(s.started_at).toLocaleString("id-ID", {
                                    day: "2-digit",
                                    month: "short",
                                    hour: "2-digit",
                                    minute: "2-digit",
                                  })
                                : "—"}
                            </td>
                            <td className="py-2.5 px-2 font-semibold text-slate-800">
                              {s.mode === "FULL_SIMULATION" ? "Simulasi Penuh" : "Latihan"}
                            </td>
                            <td className="py-2.5 px-2 font-bold text-slate-900">
                              {s.reading || "—"}
                            </td>
                            <td className="py-2.5 px-2 font-bold text-slate-900">
                              {s.listening || "—"}
                            </td>
                            <td className="py-2.5 px-2 font-bold text-slate-900">
                              {s.writing || "—"}
                            </td>
                            <td className="py-2.5 pl-2 text-right">
                              <button
                                type="button"
                                onClick={() => openSessionResult(s.session_id)}
                                className="rounded bg-slate-100 hover:bg-slate-200 px-2.5 py-1 font-semibold text-blue-950 cursor-pointer"
                              >
                                Detail
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              {/* Focus Areas (Area yang perlu dilatih - PRD Section 8.2 & 47) */}
              <div className="lg:col-span-5 rounded-lg border border-slate-300 bg-white p-6 shadow-xs space-y-4">
                <div className="border-b border-slate-200 pb-3">
                  <h2 className="text-xs font-extrabold uppercase tracking-wider text-slate-700">
                    Area yang Perlu Dilatih (Focus Areas)
                  </h2>
                </div>
                <ul className="space-y-3 text-xs">
                  {focusAreas.map((fa: any, idx: number) => (
                    <li
                      key={idx}
                      className="rounded-md border border-slate-200 bg-slate-50/70 p-3.5 space-y-1"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-slate-900">• {fa.area}</span>
                        <span className="rounded bg-blue-100 text-blue-900 px-2 py-0.5 text-[10px] font-bold uppercase">
                          {fa.skill}
                        </span>
                      </div>
                      <p className="text-slate-600 leading-relaxed">{fa.recommendation}</p>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}

        {/* ==================== 2. PRACTICE SETUP VIEW (PRD Section 9.1 & 16) ==================== */}
        {nav === "practice_setup" && (
          <div className="max-w-2xl mx-auto rounded-lg border border-slate-300 bg-white p-8 shadow-xs space-y-6">
            <div className="border-b border-slate-200 pb-4">
              <span className="text-xs font-bold uppercase tracking-wider text-blue-900">
                Practice Mode — Learn while you test
              </span>
              <h1 className="text-xl font-extrabold text-slate-900 mt-1">
                Pengaturan Latihan Mandiri (Practice Setup)
              </h1>
              <p className="text-xs text-slate-600 mt-1">
                Pilih keterampilan yang ingin dilatih. Penjelasan jawaban, kunci jawaban, dan transkrip audio ditampilkan langsung setelah Anda menjawab setiap soal.
              </p>
            </div>

            {/* Skill Selection */}
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-2">
                1. Pilih Keterampilan (Skill)
              </label>
              <div className="grid grid-cols-3 gap-3">
                {(["reading", "listening", "writing"] as const).map((sk) => (
                  <button
                    key={sk}
                    id={`setup-skill-${sk}`}
                    type="button"
                    onClick={() => {
                      setPracticeSkill(sk);
                      setPracticeTaskFilter("");
                    }}
                    className={`rounded-md border p-3.5 text-center text-xs font-bold uppercase transition cursor-pointer ${
                      practiceSkill === sk
                        ? "border-blue-900 bg-blue-950 text-white"
                        : "border-slate-300 bg-white text-slate-800 hover:bg-slate-50"
                    }`}
                  >
                    {sk}
                  </button>
                ))}
              </div>
            </div>

            {/* Adaptive / Writing Options */}
            {practiceSkill !== "writing" ? (
              <div className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-2">
                      2. Tingkat Kesulitan
                    </label>
                    <div className="rounded border border-slate-300 bg-slate-50 px-3.5 py-2.5 text-xs font-semibold text-slate-800">
                      Adaptive (1PL IRT Rasch + EAP)
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-2">
                      3. Target Jumlah Unit Soal (PRD 16)
                    </label>
                    <select
                      id="practice-target-units-select"
                      value={practiceTargetUnits}
                      onChange={(e) => setPracticeTargetUnits(parseInt(e.target.value, 10))}
                      className="w-full rounded border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-900"
                    >
                      <option value={5}>5 item units (Latihan Cepat)</option>
                      <option value={10}>10 item units (Standar)</option>
                      <option value={20}>20 item units (Mendalam)</option>
                      <option value={30}>Sampai Ambang Keyakinan (SE ≤ 0.30)</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-2">
                    4. Filter Tipe Tugas (Opsional — PRD 9.1)
                  </label>
                  <select
                    id="practice-task-filter-select"
                    value={practiceTaskFilter}
                    onChange={(e) => setPracticeTaskFilter(e.target.value)}
                    className="w-full rounded border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-900"
                  >
                    <option value="">Semua Tipe Tugas (Adaptif Seimbang)</option>
                    {practiceSkill === "reading" ? (
                      <>
                        <option value="RT-01">RT-01 — Read &amp; Select (1–2 Kalimat)</option>
                        <option value="RT-02">RT-02 — Gapped Sentence (Kalimat Rumpang)</option>
                        <option value="RT-03">RT-03 — Multiple-Choice Cloze (5–6 Celah)</option>
                        <option value="RT-04">RT-04 — Open Cloze (Ketik 1 Kata / Celah)</option>
                        <option value="RT-05">RT-05 — Extended Reading (5 Soal Pilihan Ganda)</option>
                        <option value="RT-06">RT-06 — Gapped Text (Susun Kalimat / Paragraf)</option>
                        <option value="RT-07">RT-07 — Cross-Text Multiple Matching</option>
                        <option value="RT-08">RT-08 — Word Formation (Pembentukan Kata)</option>
                        <option value="RT-09">RT-09 — Key Word Transformation</option>
                      </>
                    ) : (
                      <>
                        <option value="LT-01">LT-01 — Short Monologue / Dialogue (1 Soal)</option>
                        <option value="LT-02">LT-02 — Medium Extract (2 Soal Pilihan Ganda)</option>
                        <option value="LT-03">LT-03 — Extended Interview / Talk (5 Soal)</option>
                      </>
                    )}
                  </select>
                </div>
              </div>
            ) : (
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-2">
                  2. Pilih Bagian Writing (PRD 9.1)
                </label>
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { id: "part1", label: "Part 1 (Email)" },
                    { id: "part2", label: "Part 2 (Article/Review)" },
                    { id: "full", label: "Full Writing (Part 1 + 2)" },
                  ].map((opt) => (
                    <button
                      key={opt.id}
                      type="button"
                      onClick={() => setWritingPartMode(opt.id as any)}
                      className={`rounded border p-3 text-xs font-bold transition cursor-pointer ${
                        writingPartMode === opt.id
                          ? "border-blue-900 bg-blue-50 text-blue-950"
                          : "border-slate-300 bg-white text-slate-700"
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Mode Timing Options */}
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-2">
                Mode Waktu
              </label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setPracticeTimed(false)}
                  className={`rounded border p-3 text-xs font-bold transition cursor-pointer ${
                    !practiceTimed
                      ? "border-blue-900 bg-blue-50 text-blue-950"
                      : "border-slate-300 bg-white text-slate-700"
                  }`}
                >
                  Relaxed (Tanpa Batas Waktu)
                </button>
                <button
                  type="button"
                  onClick={() => setPracticeTimed(true)}
                  className={`rounded border p-3 text-xs font-bold transition cursor-pointer ${
                    practiceTimed
                      ? "border-blue-900 bg-blue-50 text-blue-950"
                      : "border-slate-300 bg-white text-slate-700"
                  }`}
                >
                  Timed Practice (Dengan Hitung Mundur)
                </button>
              </div>
            </div>

            <div className="pt-2 flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={() => setNav("dashboard")}
                className="rounded border border-slate-300 px-4 py-2.5 text-xs font-semibold text-slate-700 cursor-pointer"
              >
                Batal
              </button>
              <button
                id="confirm-start-practice-btn"
                type="button"
                onClick={() => handleStartPractice()}
                className="rounded-md bg-blue-950 hover:bg-blue-900 px-6 py-2.5 text-sm font-bold text-white cursor-pointer"
              >
                Start Practice (Mulai Latihan)
              </button>
            </div>
          </div>
        )}

        {/* ==================== 3. FULL TEST SIMULATION SETUP (PRD Section 9.2) ==================== */}
        {nav === "simulation_setup" && (
          <div className="max-w-2xl mx-auto rounded-lg border border-slate-300 bg-white p-8 shadow-xs space-y-6">
            <div className="border-b border-slate-200 pb-4">
              <span className="text-xs font-bold uppercase tracking-wider text-blue-900">
                Full Test Simulation — Exam Conditions
              </span>
              <h1 className="text-xl font-extrabold text-slate-900 mt-1">
                FULL TEST SIMULATION
              </h1>
              <p className="text-xs text-slate-600 mt-1">
                Simulasi kondisi ujian berurutan dengan batas waktu ketat dan pemilihan butir adaptif.
              </p>
            </div>

            <div>
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-2">
                Included Skills (Urutan Modul):
              </h2>
              <div className="flex flex-wrap gap-3">
                {["reading", "listening", "writing"].map((sk) => {
                  const checked = simSkills.includes(sk);
                  return (
                    <label
                      key={sk}
                      className={`inline-flex items-center gap-2 rounded border px-4 py-2.5 text-xs font-bold uppercase cursor-pointer ${
                        checked
                          ? "border-blue-900 bg-blue-50 text-blue-950"
                          : "border-slate-300 bg-white text-slate-700"
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() =>
                          setSimSkills((prev) =>
                            prev.includes(sk)
                              ? prev.filter((s) => s !== sk)
                              : [...prev, sk]
                          )
                        }
                        className="accent-blue-900"
                      />
                      <span>{sk}</span>
                    </label>
                  );
                })}
              </div>
            </div>

            <div className="rounded-md bg-slate-50 border border-slate-200 p-4 text-xs space-y-2">
              <div className="font-bold text-slate-900">
                Perkiraan total waktu: ~105–130 menit (bergantung pada penghentian adaptif Reading/Listening & waktu Writing 45 menit)
              </div>
              <ul className="list-disc pl-5 space-y-1 text-slate-700">
                <li>Strict timer (Batas maks: Reading 59 mnt, Listening 59 mnt, Writing 45 mnt)</li>
                <li>Tidak ada penjelasan atau kunci jawaban selama ujian berlangsung</li>
                <li>Rekaman audio Listening diputar otomatis tepat 2 kali</li>
                <li>Kontrol jeda (pause), putar ulang (replay), dan geser (seek) dinonaktifkan</li>
                <li>Modul Reading dan Listening bersifat adaptif (1PL IRT Rasch + EAP)</li>
              </ul>
            </div>

            <div className="rounded border border-blue-200 bg-blue-50/60 p-3.5 text-[11px] text-blue-950">
              <strong>Pernyataan Penting:</strong> Simulasi ini meniru konstruk publik dan aturan waktu ujian untuk tujuan persiapan pribadi, serta tidak menghasilkan sertifikat atau skor resmi Cambridge.
            </div>

            <div className="pt-2 flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={() => setNav("dashboard")}
                className="rounded border border-slate-300 px-4 py-2.5 text-xs font-semibold text-slate-700 cursor-pointer"
              >
                Batal
              </button>
              <button
                id="begin-full-simulation-btn"
                type="button"
                onClick={handleStartFullSimulation}
                className="rounded-md bg-blue-950 hover:bg-blue-900 px-6 py-2.5 text-sm font-bold text-white cursor-pointer"
              >
                Begin Simulation (Mulai Simulasi Penuh)
              </button>
            </div>
          </div>
        )}

        {/* ==================== 4. ACTIVE EXAM VIEW ==================== */}
        {nav === "active_exam" && activeSessionState && (
          <div>
            {activeSessionState.current_module === "writing" ? (
              <WritingWorkspace
                writingData={activeSessionState.writing}
                isSimulation={activeSessionState.mode === "FULL_SIMULATION"}
                isSubmitting={isSubmittingAnswer}
                onSubmitWriting={handleSubmitWriting}
                onDraftChange={(p1, p2) => setWritingDrafts({ part1: p1, part2: p2 })}
              />
            ) : (
              activeSessionState.question && (
                <QuestionRenderer
                  question={activeSessionState.question}
                  isSimulation={activeSessionState.mode === "FULL_SIMULATION"}
                  isSubmitting={isSubmittingAnswer}
                  practiceFeedback={practiceFeedback}
                  onSubmitAnswer={handleSubmitObjective}
                  onProceedNextPractice={handleProceedNextPractice}
                />
              )
            )}
          </div>
        )}

        {/* ==================== 5. RESULT DETAILS VIEW ==================== */}
        {nav === "result" && activeResultReport && (
          <ResultView
            report={activeResultReport}
            onBackToDashboard={() => {
              setNav("dashboard");
              loadDashboardData();
            }}
          />
        )}

        {/* ==================== 6. HISTORY VIEW (PRD Section 19) ==================== */}
        {nav === "history" && (
          <div className="space-y-6">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <h1 className="text-2xl font-extrabold text-slate-900">
                  Riwayat Sesi Ujian & Latihan (History)
                </h1>
                <p className="text-xs text-slate-600 mt-0.5">
                  Tabel riwayat lengkap seluruh sesi beserta perkiraan level per keterampilan.
                </p>
              </div>
            </div>

            <div className="rounded-lg border border-slate-300 bg-white p-6 shadow-xs">
              {historyList.length === 0 ? (
                <p className="text-sm text-slate-500 py-8 text-center">
                  Belum ada catatan riwayat ujian.
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-slate-200 text-slate-500 uppercase">
                        <th className="py-3 pr-4">Date</th>
                        <th className="py-3 px-3">Mode</th>
                        <th className="py-3 px-3">Reading</th>
                        <th className="py-3 px-3">Listening</th>
                        <th className="py-3 px-3">Writing</th>
                        <th className="py-3 px-3">Overall</th>
                        <th className="py-3 px-3">Status</th>
                        <th className="py-3 pl-3 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200">
                      {historyList.map((item: any) => (
                        <tr key={item.session_id} className="hover:bg-slate-50">
                          <td className="py-3 pr-4 font-mono text-slate-700">
                            {item.started_at
                              ? new Date(item.started_at).toLocaleString("id-ID")
                              : "—"}
                          </td>
                          <td className="py-3 px-3 font-semibold text-slate-900">
                            {item.mode === "FULL_SIMULATION"
                              ? "Full Simulation"
                              : "Practice"}
                          </td>
                          <td className="py-3 px-3 font-bold text-slate-900">
                            {item.reading || "—"}
                          </td>
                          <td className="py-3 px-3 font-bold text-slate-900">
                            {item.listening || "—"}
                          </td>
                          <td className="py-3 px-3 font-bold text-slate-900">
                            {item.writing || "—"}
                          </td>
                          <td className="py-3 px-3">
                            <span className="rounded bg-blue-50 border border-blue-200 px-2 py-0.5 font-extrabold text-blue-950">
                              {item.overall ||
                                item.reading ||
                                item.listening ||
                                item.writing ||
                                "—"}
                            </span>
                          </td>
                          <td className="py-3 px-3">
                            <span
                              className={`rounded px-2 py-0.5 text-[11px] font-bold ${
                                item.status === "COMPLETED"
                                  ? "bg-emerald-100 text-emerald-800"
                                  : "bg-amber-100 text-amber-800"
                              }`}
                            >
                              {item.status}
                            </span>
                          </td>
                          <td className="py-3 pl-3 text-right space-x-2">
                            <button
                              type="button"
                              onClick={() => openSessionResult(item.session_id)}
                              className="inline-flex items-center gap-1 rounded bg-slate-100 hover:bg-slate-200 px-2.5 py-1 font-semibold text-slate-800 cursor-pointer"
                            >
                              <Eye className="h-3.5 w-3.5" /> Lihat Hasil
                            </button>
                            <button
                              type="button"
                              onClick={() => handleDeleteHistoryItem(item.session_id)}
                              className="inline-flex items-center gap-1 rounded border border-rose-200 bg-rose-50 hover:bg-rose-100 px-2.5 py-1 font-semibold text-rose-800 cursor-pointer"
                            >
                              <Trash2 className="h-3.5 w-3.5" /> Hapus
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ==================== 7. CONTENT STUDIO VIEW ==================== */}
        {nav === "studio" && <ContentStudioView />}

        {/* ==================== 8. SETTINGS & ABOUT VIEWS ==================== */}
        {nav === "settings" && (
          <SettingsAndAboutView
            mode="settings"
            onHistoryCleared={() => {
              loadDashboardData();
              loadHistoryData();
            }}
          />
        )}
        {nav === "about" && <SettingsAndAboutView mode="about" />}
      </main>
    </div>
  );
}
