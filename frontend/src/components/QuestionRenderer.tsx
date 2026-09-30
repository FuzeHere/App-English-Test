"use client";

import React, { useEffect, useState } from "react";
import { CheckCircle2, XCircle, HelpCircle, FileText, ArrowRight, AlertCircle } from "lucide-react";
import ListeningPlayer from "./ListeningPlayer";

interface QuestionRendererProps {
  question: any;
  isSimulation: boolean;
  isSubmitting: boolean;
  practiceFeedback: any | null;
  onSubmitAnswer: (answerPayload: any, responseTimeSeconds: number) => void;
  onProceedNextPractice: () => void;
}

export default function QuestionRenderer({
  question,
  isSimulation,
  isSubmitting,
  practiceFeedback,
  onSubmitAnswer,
  onProceedNextPractice,
}: QuestionRendererProps) {
  const [selectedOption, setSelectedOption] = useState<string>("");
  const [answersMap, setAnswersMap] = useState<Record<string, string>>({});
  const [canProceedListening, setCanProceedListening] = useState<boolean>(true);
  const [startTimeMs, setStartTimeMs] = useState<number>(Date.now());
  const [confirmBlank, setConfirmBlank] = useState<boolean>(false);

  const content = question?.content || {};
  const qType = content.type || "mcq";
  const isListening = question?.skill === "listening";

  useEffect(() => {
    setSelectedOption("");
    setAnswersMap({});
    setConfirmBlank(false);
    setStartTimeMs(Date.now());
    if (isListening && isSimulation) {
      setCanProceedListening(false);
    } else {
      setCanProceedListening(true);
    }
  }, [question?.question_id, isListening, isSimulation]);

  const setSubAnswer = (key: string, val: string) => {
    if (practiceFeedback) return;
    setAnswersMap((prev) => ({ ...prev, [key]: val }));
    setConfirmBlank(false);
  };

  const isFullyAnswered = (): boolean => {
    if (qType === "open_cloze" || qType === "mcq_cloze") {
      const gaps = content.gaps || [];
      return gaps.every((g: any) => (answersMap[g.id] || "").trim().length > 0);
    }
    if (qType === "gapped_text_sentences" || qType === "gapped_text_paragraphs") {
      const gaps = content.gaps || [];
      return gaps.every((g: any) => {
        const gid = typeof g === "string" ? g : g.id;
        return (answersMap[gid] || "").trim().length > 0;
      });
    }
    if (qType === "cross_text_matching" || qType === "multi_mcq") {
      const qs = content.questions || [];
      return qs.every((q: any) => (answersMap[q.id] || "").trim().length > 0);
    }
    return selectedOption.trim().length > 0;
  };

  const handlePrimarySubmit = () => {
    if (!isFullyAnswered() && !confirmBlank) {
      setConfirmBlank(true);
      return;
    }
    const elapsedSec = Math.max(1, Math.round((Date.now() - startTimeMs) / 1000));
    onSubmitAnswer(
      {
        selected_option_id: selectedOption,
        answers: answersMap,
      },
      elapsedSec
    );
  };

  // Render passage with [gap1] placeholders highlighted for Gapped Text tasks (RT-06 / RT-07)
  const renderGappedPassage = (baseText: string, gaps: string[]) => {
    const parts = baseText.split(/(\[gap\d+\])/g);
    return (
      <div className="exam-passage space-y-3 text-slate-800">
        {parts.map((part, idx) => {
          const match = part.match(/^\[(gap\d+)\]$/);
          if (match) {
            const gid = match[1];
            const val = answersMap[gid] || "";
            return (
              <span
                key={idx}
                className={`inline-flex items-center gap-1.5 mx-1 px-2.5 py-0.5 rounded border text-sm font-semibold ${
                  val
                    ? "bg-blue-50 border-blue-500 text-blue-900"
                    : "bg-amber-50 border-amber-400 text-amber-900"
                }`}
              >
                <span>[{gid.replace("gap", "Gap ")}]</span>
                <select
                  aria-label={`Select option for ${gid}`}
                  disabled={!!practiceFeedback}
                  value={val}
                  onChange={(e) => setSubAnswer(gid, e.target.value)}
                  className="bg-transparent font-bold text-blue-900 focus:outline-none cursor-pointer"
                >
                  <option value="">— Pilih —</option>
                  {(content.options || []).map((opt: any) => (
                    <option key={opt.id} value={opt.id}>
                      {opt.id}
                    </option>
                  ))}
                </select>
              </span>
            );
          }
          return (
            <span key={idx} className="whitespace-pre-line">
              {part}
            </span>
          );
        })}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Listening Player Header when skill === listening */}
      {isListening && question.audio && (
        <ListeningPlayer
          questionId={question.question_id}
          audioUrl={question.audio.url}
          durationSeconds={question.audio.duration_seconds}
          isSimulation={isSimulation}
          prelisteningSeconds={question.playback_rules?.prelistening_seconds || 10}
          onPlaybackCycleComplete={(ready) => setCanProceedListening(ready)}
        />
      )}

      {/* Main Split-Pane or Single-Pane Exam Card (PRD Section 10.4) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* LEFT PANE: Reading Passage / Graphic / Multi-Text / Cloze Context */}
        <div className="lg:col-span-7 rounded-lg border border-slate-300 bg-white p-6 shadow-xs">
          <div className="flex items-center justify-between border-b border-slate-200 pb-3 mb-4">
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-slate-600" />
              <span className="text-xs font-bold uppercase tracking-wider text-slate-600">
                {question.task_type} — {question.task_type_label}
              </span>
            </div>
            <span className="rounded bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700 capitalize">
              Topik: {question.primary_topic?.replace("_", " ")}
            </span>
          </div>

          {content.title && (
            <h2 className="text-lg font-bold text-slate-900 mb-3">{content.title}</h2>
          )}
          {content.instructions && (
            <p className="text-xs font-medium text-slate-600 bg-slate-100 border-l-4 border-slate-500 px-3 py-2 mb-4 rounded-r">
              {content.instructions}
            </p>
          )}

          {/* RT-01: Open Cloze Inline Text Segments */}
          {qType === "open_cloze" && (
            <div className="exam-passage leading-9 text-slate-800">
              {(content.text_segments || []).map((seg: any, i: number) => {
                if (seg.gap_id) {
                  const gid = seg.gap_id;
                  return (
                    <span key={i} className="inline-flex items-center mx-1.5">
                      <span className="text-xs font-bold text-slate-500 mr-1">
                        ({seg.number || gid})
                      </span>
                      <input
                        id={`open-cloze-${gid}`}
                        type="text"
                        disabled={!!practiceFeedback}
                        placeholder="..."
                        value={answersMap[gid] || ""}
                        onChange={(e) => setSubAnswer(gid, e.target.value)}
                        className="w-28 rounded border border-slate-400 bg-slate-50 px-2.5 py-1 text-sm font-semibold text-blue-950 focus:border-blue-600 focus:bg-white"
                      />
                    </span>
                  );
                }
                return <span key={i}>{seg.text}</span>;
              })}
            </div>
          )}

          {/* RT-02: Multiple-choice Cloze Passage */}
          {qType === "mcq_cloze" && (
            <div className="exam-passage whitespace-pre-line text-slate-800">
              {content.passage}
            </div>
          )}

          {/* RT-03: Cross Text Matching (4 labelled texts A-D) */}
          {qType === "cross_text_matching" && (
            <div className="space-y-4 max-h-[540px] overflow-y-auto pr-2">
              {(content.texts || []).map((t: any) => (
                <div
                  key={t.id}
                  className="rounded-md border border-slate-200 bg-slate-50/70 p-4"
                >
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className="inline-flex h-6 w-6 items-center justify-center rounded bg-slate-900 text-xs font-bold text-white">
                      {t.id}
                    </span>
                    <h3 className="text-sm font-bold text-slate-900">{t.author}</h3>
                  </div>
                  <p className="text-sm leading-relaxed text-slate-800">{t.content}</p>
                </div>
              ))}
            </div>
          )}

          {/* RT-04: Discrete Cloze or LT-01 Single MCQ Stem */}
          {(qType === "discrete_cloze" || qType === "mcq") && (
            <div className="py-4">
              <p className="text-base font-medium leading-relaxed text-slate-900 bg-slate-50 border border-slate-200 rounded-lg p-5">
                {content.stem}
              </p>
              {isListening && (
                <p className="mt-3 text-xs text-slate-500">
                  Dengarkan rekaman audio dengan saksama, lalu pilih jawaban yang paling tepat pada panel di sebelah kanan.
                </p>
              )}
            </div>
          )}

          {/* RT-05: Discrete with a Graphic (Notice / Message / Email card) */}
          {qType === "discrete_graphic" && content.graphic && (
            <div className="my-2 rounded-lg border-2 border-slate-800 bg-amber-50/40 p-5 shadow-xs">
              <div className="border-b border-slate-300 pb-2 mb-3 flex items-center justify-between">
                <span className="text-xs font-extrabold uppercase tracking-wider text-slate-900">
                  {content.graphic.header}
                </span>
                <span className="text-xs font-medium text-slate-600">
                  {content.graphic.subtext}
                </span>
              </div>
              <p className="whitespace-pre-line text-sm font-medium leading-relaxed text-slate-900">
                {content.graphic.body}
              </p>
              {content.graphic.footer && (
                <div className="mt-3 pt-2 border-t border-slate-200 text-xs italic text-slate-500">
                  {content.graphic.footer}
                </div>
              )}
            </div>
          )}

          {/* RT-06 & RT-07: Gapped Text Sentences / Paragraphs */}
          {(qType === "gapped_text_sentences" || qType === "gapped_text_paragraphs") && (
            <div className="max-h-[540px] overflow-y-auto pr-2">
              {renderGappedPassage(content.base_text || "", content.gaps || [])}
            </div>
          )}

          {/* RT-08, RT-09, LT-02, LT-03: Multi-item Comprehension */}
          {qType === "multi_mcq" && (
            <div className="max-h-[540px] overflow-y-auto pr-2">
              {content.passage ? (
                <div className="exam-passage whitespace-pre-line text-slate-800">
                  {content.passage}
                </div>
              ) : (
                <div className="rounded-md bg-slate-50 border border-slate-200 p-4 text-sm text-slate-700">
                  <p className="font-semibold text-slate-900 mb-1">
                    Tugas Pemahaman Mendengarkan ({ (content.questions || []).length } Pertanyaan)
                  </p>
                  <p>
                    Bacalah pertanyaan dan pilihan jawaban di panel sebelah kanan. Dengarkan audio untuk menjawab seluruh pertanyaan sebelum menekan tombol Berikutnya.
                  </p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* RIGHT PANE: Answer Controls */}
        <div className="lg:col-span-5 rounded-lg border border-slate-300 bg-white p-6 shadow-xs space-y-5">
          <div className="border-b border-slate-200 pb-3 flex items-center justify-between">
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-800">
              Lembar Jawaban
            </h3>
            <span className="text-xs text-slate-500">
              {question.sub_item_count} {question.sub_item_count > 1 ? "butir soal" : "butir soal"}
            </span>
          </div>

          {/* 1. Single MCQ options (RT-04, RT-05, LT-01) */}
          {(qType === "mcq" || qType === "discrete_cloze" || qType === "discrete_graphic") && (
            <div className="space-y-3">
              {qType === "discrete_graphic" && (
                <p className="text-sm font-semibold text-slate-900 mb-2">{content.stem}</p>
              )}
              {(content.options || []).map((opt: any) => {
                const active = selectedOption === opt.id;
                return (
                  <label
                    key={opt.id}
                    className={`flex items-start gap-3 rounded-md border p-3.5 transition cursor-pointer ${
                      active
                        ? "border-blue-700 bg-blue-50/80 ring-1 ring-blue-700"
                        : "border-slate-200 hover:border-slate-300 hover:bg-slate-50"
                    } ${practiceFeedback ? "pointer-events-none" : ""}`}
                  >
                    <input
                      type="radio"
                      name={`mcq-${question.question_id}`}
                      value={opt.id}
                      checked={active}
                      disabled={!!practiceFeedback}
                      onChange={() => {
                        setSelectedOption(opt.id);
                        setConfirmBlank(false);
                      }}
                      className="mt-1 h-4 w-4 accent-blue-800"
                    />
                    <div className="text-sm">
                      <span className="font-bold text-slate-900 mr-2">{opt.id}.</span>
                      <span className="text-slate-800">{opt.text}</span>
                    </div>
                  </label>
                );
              })}
            </div>
          )}

          {/* 2. Open Cloze Summary Inputs (RT-01) */}
          {qType === "open_cloze" && (
            <div className="space-y-3">
              <p className="text-xs text-slate-600">
                Ketik tepat <strong>satu kata</strong> tata bahasa untuk masing-masing rumpang (1–5):
              </p>
              {(content.gaps || []).map((g: any, idx: number) => (
                <div key={g.id} className="flex items-center gap-3">
                  <label
                    htmlFor={`panel-cloze-${g.id}`}
                    className="w-20 text-xs font-bold uppercase text-slate-700"
                  >
                    Rumpang {idx + 1}:
                  </label>
                  <input
                    id={`panel-cloze-${g.id}`}
                    type="text"
                    disabled={!!practiceFeedback}
                    value={answersMap[g.id] || ""}
                    onChange={(e) => setSubAnswer(g.id, e.target.value)}
                    placeholder="Ketik 1 kata..."
                    className="flex-1 rounded border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-900 focus:border-blue-700"
                  />
                </div>
              ))}
            </div>
          )}

          {/* 3. Multiple-choice Cloze (RT-02) */}
          {qType === "mcq_cloze" && (
            <div className="space-y-4 max-h-[440px] overflow-y-auto pr-1">
              {(content.gaps || []).map((g: any, idx: number) => (
                <div key={g.id} className="rounded-md border border-slate-200 p-3 bg-slate-50/50">
                  <div className="text-xs font-bold text-slate-700 mb-2">
                    Rumpang ({g.number || idx + 1})
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    {(g.options || []).map((opt: any) => {
                      const active = answersMap[g.id] === opt.id;
                      return (
                        <button
                          key={opt.id}
                          type="button"
                          disabled={!!practiceFeedback}
                          onClick={() => setSubAnswer(g.id, opt.id)}
                          className={`flex items-center gap-2 rounded border px-3 py-2 text-left text-xs font-medium transition cursor-pointer ${
                            active
                              ? "border-blue-700 bg-blue-900 text-white"
                              : "border-slate-300 bg-white text-slate-800 hover:bg-slate-100"
                          }`}
                        >
                          <span className="font-bold">{opt.id}.</span>
                          <span>{opt.text}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* 4. Gapped Text Sentences / Paragraphs Options Bank (RT-06, RT-07) */}
          {(qType === "gapped_text_sentences" || qType === "gapped_text_paragraphs") && (
            <div className="space-y-3 max-h-[460px] overflow-y-auto pr-1">
              <p className="text-xs text-slate-600">
                Pilih kalimat/paragraf yang tepat untuk setiap rumpang pada teks di sebelah kiri:
              </p>
              <div className="grid grid-cols-5 gap-2 mb-3">
                {(content.gaps || []).map((g: any, idx: number) => {
                  const gid = typeof g === "string" ? g : g.id;
                  return (
                    <div key={gid} className="rounded border border-slate-300 bg-slate-50 p-2 text-center">
                      <div className="text-[11px] font-bold text-slate-600">Gap {idx + 1}</div>
                      <select
                        disabled={!!practiceFeedback}
                        value={answersMap[gid] || ""}
                        onChange={(e) => setSubAnswer(gid, e.target.value)}
                        className="mt-1 w-full rounded border border-slate-300 bg-white px-1 py-1 text-xs font-bold text-blue-900"
                      >
                        <option value="">-</option>
                        {(content.options || []).map((o: any) => (
                          <option key={o.id} value={o.id}>
                            {o.id}
                          </option>
                        ))}
                      </select>
                    </div>
                  );
                })}
              </div>
              <div className="space-y-2">
                {(content.options || []).map((opt: any) => {
                  const isUsed = Object.values(answersMap).includes(opt.id);
                  return (
                    <div
                      key={opt.id}
                      className={`rounded border p-2.5 text-xs leading-relaxed ${
                        isUsed
                          ? "border-blue-300 bg-blue-50/50 text-slate-600"
                          : "border-slate-200 bg-white text-slate-800"
                      }`}
                    >
                      <span className="font-bold text-slate-900 mr-1.5">{opt.id}.</span>
                      <span>{opt.text}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* 5. Cross Text Matching & Multi-MCQ (RT-03, RT-08, RT-09, LT-02, LT-03) */}
          {(qType === "cross_text_matching" || qType === "multi_mcq") && (
            <div className="space-y-4 max-h-[480px] overflow-y-auto pr-1">
              {(content.questions || []).map((qItem: any, idx: number) => (
                <div
                  key={qItem.id}
                  className="rounded-md border border-slate-200 bg-slate-50/40 p-3.5 space-y-2.5"
                >
                  <p className="text-xs font-bold text-slate-900 leading-snug">
                    {idx + 1}. {qItem.stem}
                  </p>
                  <div
                    className={
                      qType === "cross_text_matching"
                        ? "grid grid-cols-4 gap-2"
                        : "space-y-1.5"
                    }
                  >
                    {(qItem.options || []).map((opt: any) => {
                      const active = answersMap[qItem.id] === opt.id;
                      return (
                        <button
                          key={opt.id}
                          type="button"
                          disabled={!!practiceFeedback}
                          onClick={() => setSubAnswer(qItem.id, opt.id)}
                          className={`w-full flex items-start gap-2 rounded border px-3 py-2 text-left text-xs transition cursor-pointer ${
                            active
                              ? "border-blue-700 bg-blue-900 text-white font-semibold"
                              : "border-slate-300 bg-white text-slate-800 hover:bg-slate-100"
                          }`}
                        >
                          <span className="font-bold">{opt.id}.</span>
                          <span className="flex-1">{opt.text}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Explicit Leave Blank Confirmation per PRD Section 10.5 */}
          {confirmBlank && !practiceFeedback && (
            <div className="rounded-md border border-amber-300 bg-amber-50 p-3 text-xs text-amber-900 flex items-start gap-2">
              <AlertCircle className="h-4 w-4 text-amber-700 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold">Belum semua kolom jawaban terisi.</p>
                <p className="mt-0.5">
                  Klik tombol sekali lagi jika Anda yakin ingin mengosongkan jawaban dan melanjutkan.
                </p>
              </div>
            </div>
          )}

          {/* Action Bar: Submit / Next */}
          <div className="pt-2 border-t border-slate-200 flex items-center justify-between">
            {!practiceFeedback ? (
              <>
                <span className="text-xs text-slate-500">
                  {isSimulation
                    ? "Jawaban tidak dapat diubah setelah dikirim."
                    : "Mode Latihan: Penjelasan ditampilkan setelah kirim."}
                </span>
                <button
                  id="submit-question-btn"
                  type="button"
                  disabled={isSubmitting || (isListening && isSimulation && !canProceedListening)}
                  onClick={handlePrimarySubmit}
                  className="inline-flex items-center gap-2 rounded-md bg-blue-900 hover:bg-blue-800 disabled:bg-slate-300 disabled:text-slate-500 px-5 py-2.5 text-sm font-semibold text-white transition cursor-pointer"
                >
                  <span>
                    {isSubmitting
                      ? "Memproses..."
                      : confirmBlank
                      ? "Tetap Kirim (Kosong)"
                      : isSimulation
                      ? "Berikutnya"
                      : "Kirim jawaban"}
                  </span>
                  <ArrowRight className="h-4 w-4" />
                </button>
              </>
            ) : (
              <button
                id="next-practice-item-btn"
                type="button"
                onClick={onProceedNextPractice}
                className="w-full inline-flex items-center justify-center gap-2 rounded-md bg-emerald-700 hover:bg-emerald-600 px-5 py-2.5 text-sm font-semibold text-white transition cursor-pointer"
              >
                <span>Berikutnya</span>
                <ArrowRight className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Practice Mode Immediate Explanation & Transcript Drawer (PRD Section 6.1 & 16) */}
      {practiceFeedback && (
        <div
          id="practice-feedback-panel"
          className={`rounded-lg border p-5 shadow-xs ${
            practiceFeedback.is_correct
              ? "border-emerald-300 bg-emerald-50/70"
              : "border-amber-300 bg-amber-50/70"
          }`}
        >
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200/80 pb-3">
            <div className="flex items-center gap-2.5">
              {practiceFeedback.is_correct ? (
                <CheckCircle2 className="h-5 w-5 text-emerald-700" />
              ) : (
                <XCircle className="h-5 w-5 text-amber-700" />
              )}
              <span className="text-sm font-bold text-slate-900">
                {practiceFeedback.is_correct
                  ? "Jawaban Tepat!"
                  : `Skor Butir: ${practiceFeedback.correct_sub_items} / ${practiceFeedback.sub_item_count} benar`}
              </span>
              <span className="rounded bg-white px-2.5 py-0.5 text-xs font-semibold text-slate-700 border border-slate-200">
                Target Soal: {practiceFeedback.cefr_target}
              </span>
            </div>
            <div className="text-xs font-medium text-slate-700">
              Perkiraan level sementara:{" "}
              <strong className="font-bold text-blue-950">
                {practiceFeedback.updated_cefr_estimate}
              </strong>{" "}
              (θ = {practiceFeedback.updated_theta})
            </div>
          </div>

          <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-1">
                Jawaban benar
              </h4>
              <div className="rounded bg-white p-3 border border-slate-200 text-xs font-mono text-slate-800 space-y-1">
                {Object.entries(practiceFeedback.correct_answer_summary || {}).map(
                  ([k, v]) => {
                    const label =
                      k === "main"
                        ? "Jawaban"
                        : k.startsWith("gap")
                        ? k.replace("gap", "Gap ")
                        : k.startsWith("g")
                        ? k.replace("g", "Rumpang ")
                        : k.startsWith("q")
                        ? k.replace("q", "Soal ")
                        : k;
                    return (
                      <div key={k}>
                        <span className="font-bold">{label}:</span> {String(v)}
                      </div>
                    );
                  }
                )}
              </div>
            </div>
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-1">
                Penjelasan
              </h4>
              <p className="rounded bg-white p-3 border border-slate-200 text-xs leading-relaxed text-slate-800">
                {practiceFeedback.explanation}
              </p>
            </div>
          </div>

          {practiceFeedback.transcript && (
            <div className="mt-4 pt-3 border-t border-slate-200">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
                Transkrip Audio (Listening Transcript)
              </h4>
              <p className="rounded bg-white p-3.5 border border-slate-200 text-xs whitespace-pre-line leading-relaxed text-slate-700">
                {practiceFeedback.transcript}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
