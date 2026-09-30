"use client";

import React, { useState } from "react";
import { PenTool, ArrowRight, CheckCircle2, AlertTriangle, Loader2 } from "lucide-react";

interface WritingWorkspaceProps {
  writingData: any;
  isSimulation: boolean;
  isSubmitting: boolean;
  onSubmitWriting: (part1Text: string, part2Text: string) => void;
  onDraftChange?: (part1Text: string, part2Text: string) => void;
}

function countWords(text: string): number {
  const cleaned = (text || "").trim();
  if (!cleaned) return 0;
  return cleaned.split(/\s+/).filter(Boolean).length;
}

export default function WritingWorkspace({
  writingData,
  isSimulation,
  isSubmitting,
  onSubmitWriting,
  onDraftChange,
}: WritingWorkspaceProps) {
  const prompts = writingData?.prompts || [];
  const partMode = writingData?.writing_part_mode || "full";

  const part1Prompt = prompts.find((p: any) => p.task_part === 1) || prompts[0];
  const part2Prompt = prompts.find((p: any) => p.task_part === 2) || prompts[1];

  const [activePart, setActivePart] = useState<number>(
    partMode === "part2" ? 2 : 1
  );
  const [part1Text, setPart1Text] = useState<string>(part1Prompt?.saved_text || "");
  const [part2Text, setPart2Text] = useState<string>(part2Prompt?.saved_text || "");

  React.useEffect(() => {
    if (onDraftChange) {
      onDraftChange(part1Text, part2Text);
    }
  }, [part1Text, part2Text, onDraftChange]);

  const currentPrompt = activePart === 1 ? part1Prompt : part2Prompt;
  const currentText = activePart === 1 ? part1Text : part2Text;
  const wordCount = countWords(currentText);
  const minWords = currentPrompt?.minimum_words || (activePart === 1 ? 50 : 180);
  const belowMin = wordCount < minWords;

  if (isSubmitting) {
    return (
      <div
        id="writing-evaluating-state"
        className="rounded-lg border border-slate-300 bg-white p-12 text-center shadow-xs my-8 max-w-xl mx-auto space-y-4"
      >
        <Loader2 className="h-10 w-10 animate-spin text-blue-800 mx-auto" />
        <h2 className="text-lg font-bold text-slate-900">
          Evaluating your writing... / Mengevaluasi tulisan Anda...
        </h2>
        <p className="text-sm text-slate-600">
          AI Evaluator sedang menganalisis Communicative Achievement, Organisation, dan Language beserta saran perbaikan kalimat.
        </p>
        <p className="text-xs font-semibold text-amber-800 bg-amber-50 border border-amber-200 rounded px-3 py-1.5 inline-block">
          Do not close this page. / Jangan tutup halaman ini.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Part Selector Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-lg border border-slate-300 bg-white px-5 py-3.5 shadow-xs">
        <div className="flex items-center gap-2">
          <PenTool className="h-4 w-4 text-blue-900" />
          <span className="text-sm font-bold text-slate-900">
            Writing Module —{" "}
            {activePart === 1
              ? "Part 1: Email (Rekomendasi ~15 menit)"
              : "Part 2: Wider-Audience Writing (Rekomendasi ~30 menit)"}
          </span>
        </div>

        {partMode === "full" && (
          <div className="flex items-center gap-2">
            <button
              id="writing-tab-part1"
              type="button"
              onClick={() => setActivePart(1)}
              className={`rounded px-3.5 py-1.5 text-xs font-semibold transition cursor-pointer ${
                activePart === 1
                  ? "bg-blue-900 text-white"
                  : "bg-slate-100 text-slate-700 hover:bg-slate-200"
              }`}
            >
              Part 1 — Email ({countWords(part1Text)}/50 kata)
            </button>
            <button
              id="writing-tab-part2"
              type="button"
              onClick={() => setActivePart(2)}
              className={`rounded px-3.5 py-1.5 text-xs font-semibold transition cursor-pointer ${
                activePart === 2
                  ? "bg-blue-900 text-white"
                  : "bg-slate-100 text-slate-700 hover:bg-slate-200"
              }`}
            >
              Part 2 — {part2Prompt?.text_type || "Article"} ({countWords(part2Text)}/180 kata)
            </button>
          </div>
        )}
      </div>

      {/* Main Split Writing Layout (Prompt Left, Editor Right) */}
      {currentPrompt && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Prompt Instructions Card */}
          <div className="lg:col-span-5 rounded-lg border border-slate-300 bg-white p-6 shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <span className="rounded bg-blue-50 border border-blue-200 px-2.5 py-0.5 text-xs font-bold uppercase text-blue-900">
                Part {currentPrompt.task_part} — {currentPrompt.text_type}
              </span>
              <span className="text-xs font-medium text-slate-500">
                Rekomendasi waktu: ~{currentPrompt.recommended_minutes} menit
              </span>
            </div>

            <div className="text-xs text-slate-600">
              <strong>Target Pembaca (Audience):</strong> {currentPrompt.audience}
            </div>

            <div className="rounded-md bg-slate-50 border border-slate-200 p-4 text-sm whitespace-pre-line leading-relaxed text-slate-900">
              {currentPrompt.prompt_text}
            </div>

            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-2">
                Poin yang wajib dicakup (3 Bullet Points):
              </h3>
              <ul className="space-y-2 text-sm text-slate-800 list-disc pl-5">
                {(currentPrompt.bullet_points || []).map((bp: string, i: number) => (
                  <li key={i} className="leading-snug">
                    {bp}
                  </li>
                ))}
              </ul>
            </div>

            <div className="rounded bg-slate-100 px-3.5 py-2.5 text-xs text-slate-700">
              Write at least <strong>{minWords} words</strong>. / Tulislah minimal{" "}
              <strong>{minWords} kata</strong>.
            </div>
          </div>

          {/* Writing Textarea & Word Counter (PRD Section 12.4 & 12.5) */}
          <div className="lg:col-span-7 rounded-lg border border-slate-300 bg-white p-6 shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <label
                htmlFor="writing-response-editor"
                className="text-xs font-bold uppercase tracking-wider text-slate-700"
              >
                Lembar Menulis — Part {activePart}
              </label>
              <div className="flex items-center gap-4 text-xs font-semibold">
                <span
                  id="writing-word-counter"
                  className={belowMin ? "text-amber-700" : "text-emerald-700"}
                >
                  Jumlah kata: {wordCount}
                </span>
                <span className="text-slate-500">Minimum: {minWords}</span>
              </div>
            </div>

            <textarea
              id="writing-response-editor"
              rows={15}
              value={currentText}
              onChange={(e) => {
                if (activePart === 1) setPart1Text(e.target.value);
                else setPart2Text(e.target.value);
              }}
              placeholder={
                activePart === 1
                  ? "Dear ...,\n\nWrite your email response here..."
                  : "Write your article, review, or web post here..."
              }
              className="w-full rounded-md border border-slate-300 bg-slate-50/40 p-4 text-sm leading-relaxed text-slate-900 focus:border-blue-800 focus:bg-white font-sans resize-y"
            />

            {/* Optional non-blocking warning below minimum words (PRD Section 12.5) */}
            <div className="flex flex-wrap items-center justify-between gap-4 pt-2">
              <div className="text-xs">
                {belowMin ? (
                  <span className="inline-flex items-center gap-1.5 text-amber-700 font-medium">
                    <AlertTriangle className="h-4 w-4" />
                    Jumlah kata masih di bawah batas minimum ({wordCount}/{minWords} kata). Anda tetap dapat mengirim jawaban.
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 text-emerald-700 font-medium">
                    <CheckCircle2 className="h-4 w-4" />
                    Batas jumlah kata minimum ({minWords} kata) telah terpenuhi.
                  </span>
                )}
              </div>

              <div className="flex items-center gap-3">
                {partMode === "full" && activePart === 1 && (
                  <button
                    id="continue-to-part2-btn"
                    type="button"
                    onClick={() => setActivePart(2)}
                    className="inline-flex items-center gap-2 rounded-md bg-blue-900 hover:bg-blue-800 px-4 py-2.5 text-xs font-semibold text-white transition cursor-pointer"
                  >
                    <span>Lanjut ke Part 2</span>
                    <ArrowRight className="h-4 w-4" />
                  </button>
                )}

                {(partMode !== "full" || activePart === 2) && (
                  <button
                    id="submit-writing-module-btn"
                    type="button"
                    onClick={() => onSubmitWriting(part1Text, part2Text)}
                    className="inline-flex items-center gap-2 rounded-md bg-emerald-700 hover:bg-emerald-600 px-5 py-2.5 text-sm font-semibold text-white transition cursor-pointer"
                  >
                    <span>Kirim jawaban & Evaluasi Tulisan</span>
                    <ArrowRight className="h-4 w-4" />
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
