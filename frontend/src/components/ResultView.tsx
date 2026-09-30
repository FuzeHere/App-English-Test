"use client";

import React, { useState } from "react";
import {
  Award,
  BookOpen,
  Headphones,
  PenTool,
  CheckCircle2,
  XCircle,
  ChevronDown,
  ChevronUp,
  ArrowLeft,
  Info,
} from "lucide-react";

interface ResultViewProps {
  report: any;
  onBackToDashboard: () => void;
}

export default function ResultView({ report, onBackToDashboard }: ResultViewProps) {
  const [showAdvancedTheta, setShowAdvancedTheta] = useState<boolean>(false);
  const [expandedReviewSkill, setExpandedReviewSkill] = useState<string | null>("reading");

  if (!report) return null;

  const readingMod = report.modules?.reading;
  const listeningMod = report.modules?.listening;
  const writingMod = report.modules?.writing;

  return (
    <div id="result-report-container" className="space-y-6 pb-12">
      {/* Top Action & Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <span className="text-xs font-bold uppercase tracking-wider text-blue-900">
            Laporan Hasil Evaluasi — {report.mode === "FULL_SIMULATION" ? "Simulasi Penuh" : "Mode Latihan"}
          </span>
          <h1 className="text-2xl font-extrabold text-slate-900 mt-0.5">
            Hasil & Diagnostik Kemampuan (A1–C1)
          </h1>
        </div>
        <button
          id="back-to-dashboard-from-result"
          type="button"
          onClick={onBackToDashboard}
          className="inline-flex items-center gap-2 rounded-md border border-slate-300 bg-white hover:bg-slate-50 px-4 py-2 text-xs font-semibold text-slate-800 cursor-pointer"
        >
          <ArrowLeft className="h-4 w-4" /> Kembali ke Dashboard
        </button>
      </div>

      {/* Prominent Simulator Disclaimer Banner (PRD Section 14.3 & 18.1) */}
      <div className="rounded-lg border border-blue-200 bg-blue-50/70 px-4 py-3 text-xs text-blue-950 flex items-start gap-2.5">
        <Info className="h-4 w-4 text-blue-800 shrink-0 mt-0.5" />
        <div>
          <strong>PENTING (Simulator Estimate):</strong> {report.disclaimer}
        </div>
      </div>

      {/* Overall & Skill Level Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="rounded-lg border-2 border-blue-900 bg-slate-900 text-white p-5 shadow-xs">
          <div className="text-xs font-semibold uppercase tracking-wider text-blue-300">
            Perkiraan Level Keseluruhan
          </div>
          <div className="mt-2 flex items-baseline gap-3">
            <span id="overall-cefr-badge" className="text-4xl font-extrabold tracking-tight">
              {report.overall_level ||
                report.skill_levels?.reading ||
                report.skill_levels?.listening ||
                report.skill_levels?.writing ||
                "—"}
            </span>
            <span className="text-xs text-slate-300">Skala CEFR (A1–C1)</span>
          </div>
          <p className="mt-2 text-[11px] text-slate-300">
            Agregasi transparan dari modul yang diselesaikan pada sesi ini.
          </p>
        </div>

        {/* Reading Card */}
        <div className="rounded-lg border border-slate-300 bg-white p-5 shadow-xs">
          <div className="flex items-center justify-between text-xs font-bold uppercase text-slate-600">
            <span>Reading</span>
            <BookOpen className="h-4 w-4 text-blue-800" />
          </div>
          <div className="mt-2 text-3xl font-extrabold text-slate-900">
            {report.skill_levels?.reading || "—"}
          </div>
          <div className="mt-1 text-xs text-slate-500">
            {readingMod
              ? `Akurasi: ${readingMod.accuracy_percent}% • ${readingMod.confidence_label}`
              : "Tidak diambil pada sesi ini"}
          </div>
        </div>

        {/* Listening Card */}
        <div className="rounded-lg border border-slate-300 bg-white p-5 shadow-xs">
          <div className="flex items-center justify-between text-xs font-bold uppercase text-slate-600">
            <span>Listening</span>
            <Headphones className="h-4 w-4 text-blue-800" />
          </div>
          <div className="mt-2 text-3xl font-extrabold text-slate-900">
            {report.skill_levels?.listening || "—"}
          </div>
          <div className="mt-1 text-xs text-slate-500">
            {listeningMod
              ? `Akurasi: ${listeningMod.accuracy_percent}% • ${listeningMod.confidence_label}`
              : "Tidak diambil pada sesi ini"}
          </div>
        </div>

        {/* Writing Card */}
        <div className="rounded-lg border border-slate-300 bg-white p-5 shadow-xs">
          <div className="flex items-center justify-between text-xs font-bold uppercase text-slate-600">
            <span>Writing</span>
            <PenTool className="h-4 w-4 text-blue-800" />
          </div>
          <div className="mt-2 text-3xl font-extrabold text-slate-900">
            {report.skill_levels?.writing || "—"}
          </div>
          <div className="mt-1 text-xs text-slate-500">
            {writingMod
              ? `${writingMod.confidence_label}`
              : "Tidak diambil pada sesi ini"}
          </div>
        </div>
      </div>

      {/* READING & LISTENING OBJECTIVE MODULE DETAILS */}
      {[readingMod, listeningMod].filter(Boolean).map((mod: any) => (
        <div
          key={mod.skill}
          className="rounded-lg border border-slate-300 bg-white p-6 shadow-xs space-y-5"
        >
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 pb-4">
            <div>
              <h2 className="text-base font-extrabold uppercase tracking-wider text-slate-900">
                {mod.skill.toUpperCase()} DETAILS
              </h2>
              <p className="text-xs text-slate-600 mt-0.5">
                Perkiraan level: <strong>{mod.estimated_cefr}</strong> • Akurasi:{" "}
                <strong>{mod.accuracy_percent}%</strong> • Tingkat keyakinan:{" "}
                <strong>{mod.confidence_label}</strong>
              </p>
            </div>
            <button
              type="button"
              onClick={() => setShowAdvancedTheta((v) => !v)}
              className="rounded border border-slate-300 bg-slate-50 hover:bg-slate-100 px-3 py-1.5 text-xs font-medium text-slate-700 cursor-pointer"
            >
              {showAdvancedTheta ? "Sembunyikan Detail Statistik IRT" : "Lihat Detail Statistik IRT (θ & SE)"}
            </button>
          </div>

          {/* Optional Advanced Statistical View per PRD Section 17.3 */}
          {showAdvancedTheta && (
            <div className="rounded-md bg-slate-900 text-slate-100 p-4 text-xs font-mono grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <span className="text-slate-400 block">Estimated ability theta (EAP):</span>
                <strong className="text-sm text-blue-300">
                  {mod.final_theta >= 0 ? `+${mod.final_theta}` : mod.final_theta}
                </strong>
              </div>
              <div>
                <span className="text-slate-400 block">Standard error (SE):</span>
                <strong className="text-sm text-blue-300">{mod.standard_error}</strong>
              </div>
              <div>
                <span className="text-slate-400 block">Diagnostic status:</span>
                <strong className="text-sm text-emerald-300">{mod.confidence_label}</strong>
              </div>
            </div>
          )}

          {/* Task Type Performance Table */}
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-2.5">
              Performa per Tipe Tugas (Task Performance)
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {(mod.task_performance || []).map((tp: any) => (
                <div
                  key={tp.task_type}
                  className="rounded border border-slate-200 bg-slate-50/70 p-3 flex items-center justify-between"
                >
                  <div>
                    <div className="text-xs font-bold text-slate-900">{tp.label}</div>
                    <div className="text-[11px] text-slate-500">
                      {tp.correct_units}/{tp.total_units} benar ({tp.accuracy_percent}%)
                    </div>
                  </div>
                  <span
                    className={`rounded px-2 py-0.5 text-xs font-bold ${
                      tp.rating === "Strong"
                        ? "bg-emerald-100 text-emerald-800"
                        : tp.rating === "Good"
                        ? "bg-blue-100 text-blue-800"
                        : "bg-amber-100 text-amber-800"
                    }`}
                  >
                    {tp.rating}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Expandable Objective Item Review (PRD Section 18.2) */}
          <div className="border-t border-slate-200 pt-4">
            <button
              type="button"
              onClick={() =>
                setExpandedReviewSkill(expandedReviewSkill === mod.skill ? null : mod.skill)
              }
              className="flex w-full items-center justify-between text-left text-xs font-bold uppercase tracking-wider text-blue-900 hover:text-blue-700 cursor-pointer"
            >
              <span>
                Tinjauan Jawaban & Penjelasan ({ (mod.item_review || []).length } Tugas)
              </span>
              {expandedReviewSkill === mod.skill ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </button>

            {expandedReviewSkill === mod.skill && (
              <div className="mt-4 space-y-3">
                {(mod.item_review || []).map((item: any) => (
                  <div
                    key={item.position}
                    className="rounded-md border border-slate-200 bg-slate-50/50 p-4 space-y-2 text-xs"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        {item.is_correct ? (
                          <CheckCircle2 className="h-4 w-4 text-emerald-700" />
                        ) : (
                          <XCircle className="h-4 w-4 text-amber-700" />
                        )}
                        <span className="font-bold text-slate-900">
                          #{item.position} • {item.task_type_label}
                        </span>
                        <span className="rounded bg-white border border-slate-200 px-2 py-0.5 font-semibold text-slate-700">
                          Level Soal: {item.cefr_target}
                        </span>
                      </div>
                      <span className="text-slate-500 font-mono">
                        Skor: {item.correct_sub_items}/{item.sub_item_count} • θ: {item.pre_theta} →{" "}
                        {item.post_theta}
                      </span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
                      <div className="rounded bg-white p-2.5 border border-slate-200">
                        <span className="font-bold text-slate-700 block mb-1">
                          Jawaban benar:
                        </span>
                        <span className="font-mono text-slate-800">
                          {JSON.stringify(item.correct_answer_summary)}
                        </span>
                      </div>
                      <div className="rounded bg-white p-2.5 border border-slate-200">
                        <span className="font-bold text-slate-700 block mb-1">
                          Penjelasan:
                        </span>
                        <span className="text-slate-700">{item.explanation}</span>
                      </div>
                    </div>

                    {item.transcript && (
                      <div className="rounded bg-white p-2.5 border border-slate-200">
                        <span className="font-bold text-slate-700 block mb-1">
                          Listening Transcript:
                        </span>
                        <p className="whitespace-pre-line text-slate-600">{item.transcript}</p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      ))}

      {/* WRITING MODULE DETAILS (PRD Section 13 & 18.3) */}
      {writingMod && (
        <div className="rounded-lg border border-slate-300 bg-white p-6 shadow-xs space-y-6">
          <div className="border-b border-slate-200 pb-4 flex flex-wrap items-center justify-between gap-4">
            <div>
              <h2 className="text-base font-extrabold uppercase tracking-wider text-slate-900">
                WRITING DETAILS — EVALUASI TULISAN AI
              </h2>
              <p className="text-xs text-slate-600 mt-0.5">
                Perkiraan level Writing: <strong>{writingMod.estimated_cefr || "Pending"}</strong> •{" "}
                {writingMod.confidence_label}
              </p>
            </div>
            {writingMod.rubric_averages && (
              <div className="flex items-center gap-3 text-xs">
                <span className="rounded bg-slate-100 px-3 py-1.5 font-semibold text-slate-800">
                  Communicative Achievement: {writingMod.rubric_averages.communicative_achievement ?? "—"}/5
                </span>
                <span className="rounded bg-slate-100 px-3 py-1.5 font-semibold text-slate-800">
                  Organisation: {writingMod.rubric_averages.organisation ?? "—"}/5
                </span>
                <span className="rounded bg-slate-100 px-3 py-1.5 font-semibold text-slate-800">
                  Language: {writingMod.rubric_averages.language ?? "—"}/5
                </span>
              </div>
            )}
          </div>

          {(writingMod.parts || []).map((part: any) => {
            const ev = part.evaluation || {};
            const fb = ev.feedback || {};
            return (
              <div
                key={part.part_number}
                className="rounded-lg border border-slate-200 bg-slate-50/50 p-5 space-y-5"
              >
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 pb-3">
                  <div>
                    <h3 className="text-sm font-bold text-slate-900">
                      Part {part.part_number} ({part.prompt?.text_type?.toUpperCase()}) — Perkiraan Level:{" "}
                      <span className="text-blue-900">{ev.estimated_cefr || "Pending"}</span>
                    </h3>
                    <p className="text-xs text-slate-500">
                      Jumlah kata: {part.word_count} kata (Minimum: {part.minimum_words} kata) • Provider:{" "}
                      <span className="font-mono">{ev.provider} ({ev.model})</span>
                    </p>
                  </div>
                  <div className="flex items-center gap-2 text-xs font-bold">
                    <span className="rounded bg-white border border-slate-200 px-2.5 py-1">
                      CA: {ev.communicative_achievement ?? "—"}/5
                    </span>
                    <span className="rounded bg-white border border-slate-200 px-2.5 py-1">
                      Org: {ev.organisation ?? "—"}/5
                    </span>
                    <span className="rounded bg-white border border-slate-200 px-2.5 py-1">
                      Lang: {ev.language ?? "—"}/5
                    </span>
                  </div>
                </div>

                {/* Bilingual Summary (English + Indonesian support per PRD Section 46) */}
                {(fb.summary_en || fb.summary_id) && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                    <div className="rounded bg-white p-3.5 border border-slate-200">
                      <span className="font-bold text-slate-700 block mb-1">
                        Assessment Summary (English):
                      </span>
                      <p className="text-slate-800 leading-relaxed">{fb.summary_en}</p>
                    </div>
                    <div className="rounded bg-white p-3.5 border border-slate-200">
                      <span className="font-bold text-slate-700 block mb-1">
                        Ringkasan Evaluasi (Bahasa Indonesia):
                      </span>
                      <p className="text-slate-800 leading-relaxed">{fb.summary_id}</p>
                    </div>
                  </div>
                )}

                {/* Candidate Response Text */}
                <div className="rounded bg-white p-4 border border-slate-200">
                  <span className="text-xs font-bold uppercase text-slate-600 block mb-1.5">
                    Teks Jawaban Anda:
                  </span>
                  <p className="text-xs whitespace-pre-line leading-relaxed text-slate-800 font-sans">
                    {part.response_text || "(Tidak ada teks yang dikirim)"}
                  </p>
                </div>

                {/* Secondary Diagnostics: Grammar, Vocabulary, Coherence, Task Completion (PRD Section 13.4) */}
                {fb.diagnostics && (
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                    <div className="rounded bg-white p-3.5 border border-slate-200">
                      <span className="font-bold text-slate-900 block mb-1.5">
                        Grammar Diagnostics
                      </span>
                      <ul className="list-disc pl-4 space-y-1 text-slate-700">
                        {(fb.diagnostics.grammar || []).map((g: string, i: number) => (
                          <li key={i}>{g}</li>
                        ))}
                      </ul>
                    </div>
                    <div className="rounded bg-white p-3.5 border border-slate-200">
                      <span className="font-bold text-slate-900 block mb-1.5">
                        Vocabulary Diagnostics
                      </span>
                      <ul className="list-disc pl-4 space-y-1 text-slate-700">
                        {(fb.diagnostics.vocabulary || []).map((v: string, i: number) => (
                          <li key={i}>{v}</li>
                        ))}
                      </ul>
                    </div>
                    <div className="rounded bg-white p-3.5 border border-slate-200">
                      <span className="font-bold text-slate-900 block mb-1.5">
                        Coherence & Task Completion
                      </span>
                      <ul className="list-disc pl-4 space-y-1 text-slate-700">
                        {(fb.diagnostics.coherence || []).map((c: string, i: number) => (
                          <li key={i}>{c}</li>
                        ))}
                        {(fb.task_completion?.bullet_analysis || []).map((b: string, i: number) => (
                          <li key={`b-${i}`}>{b}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                )}

                {/* Specific Evidence Corrections (Original -> Suggested + Why per PRD Section 13.5) */}
                {(fb.corrections || []).length > 0 && (
                  <div>
                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-2">
                      Koreksi Kalimat Spesifik (Evidence-Based Corrections)
                    </h4>
                    <div className="space-y-2.5">
                      {fb.corrections.map((corr: any, idx: number) => (
                        <div
                          key={idx}
                          className="rounded bg-white border border-slate-200 p-3.5 text-xs grid grid-cols-1 md:grid-cols-3 gap-3"
                        >
                          <div>
                            <span className="font-bold text-rose-700 block">Original:</span>
                            <span className="line-through text-slate-700">{corr.original}</span>
                          </div>
                          <div>
                            <span className="font-bold text-emerald-700 block">Suggested:</span>
                            <span className="font-semibold text-slate-900">{corr.suggested}</span>
                          </div>
                          <div>
                            <span className="font-bold text-slate-700 block">Why / Mengapa:</span>
                            <p className="text-slate-700">{corr.why_en}</p>
                            {corr.why_id && (
                              <p className="text-slate-500 mt-0.5 italic">{corr.why_id}</p>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* CAN-DO STYLE SUMMARY (PRD Section 17.4) */}
      {(report.can_do_statements || []).length > 0 && (
        <div className="rounded-lg border border-slate-300 bg-white p-6 shadow-xs">
          <div className="flex items-center gap-2 mb-3">
            <Award className="h-5 w-5 text-blue-900" />
            <h2 className="text-sm font-extrabold uppercase tracking-wider text-slate-900">
              CAN-DO STYLE SUMMARY (Indikator Kemampuan Praktis)
            </h2>
          </div>
          <p className="text-xs text-slate-600 mb-3">
            Pada perkiraan level ini, simulator mengindikasikan bahwa Anda secara umum dapat:
          </p>
          <ul className="grid grid-cols-1 md:grid-cols-2 gap-2.5 text-xs text-slate-800">
            {report.can_do_statements.map((stmt: string, idx: number) => (
              <li
                key={idx}
                className="flex items-start gap-2 rounded bg-slate-50 border border-slate-200 p-3"
              >
                <CheckCircle2 className="h-4 w-4 text-blue-800 shrink-0 mt-0.5" />
                <span>{stmt}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
