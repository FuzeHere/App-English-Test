"use client";

import React, { useEffect, useState } from "react";
import {
  Settings,
  Cpu,
  Volume2,
  Trash2,
  ShieldAlert,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Info,
} from "lucide-react";
import { api, API_BASE_URL } from "@/lib/api";

interface SettingsAndAboutProps {
  mode: "settings" | "about";
  onHistoryCleared?: () => void;
}

export default function SettingsAndAboutView({
  mode,
  onHistoryCleared,
}: SettingsAndAboutProps) {
  const [settingsData, setSettingsData] = useState<any>(null);
  const [providersStatus, setProvidersStatus] = useState<any>({});
  const [voices, setVoices] = useState<any[]>([]);
  const [recentLogs, setRecentLogs] = useState<any[]>([]);

  const [defaultProv, setDefaultProv] = useState<string>("lm_studio");
  const [writingProv, setWritingProv] = useState<string>("lm_studio");
  const [genModel, setGenModel] = useState<string>("local-model");
  const [writingModel, setWritingModel] = useState<string>("local-model");
  const [lmStudioUrl, setLmStudioUrl] = useState<string>("http://127.0.0.1:1234/v1");
  const [ttsVoice, setTtsVoice] = useState<string>("en_voice_01");

  const [testingConn, setTestingConn] = useState<boolean>(false);
  const [previewAudioUrl, setPreviewAudioUrl] = useState<string | null>(null);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);
  const [confirmClearHistory, setConfirmClearHistory] = useState<boolean>(false);

  const loadSettings = async () => {
    try {
      const data = await api.getSettingsAI();
      setSettingsData(data.settings);
      setProvidersStatus(data.providers_status || {});
      setVoices(data.available_voices || []);
      setRecentLogs(data.recent_logs || []);

      if (data.settings) {
        setDefaultProv(data.settings.ai_default_provider || "lm_studio");
        setWritingProv(data.settings.writing_default_provider || "lm_studio");
        setGenModel(data.settings.generation_model || "local-model");
        setWritingModel(data.settings.writing_evaluation_model || "local-model");
        setLmStudioUrl(data.settings.lm_studio_base_url || "http://127.0.0.1:1234/v1");
        setTtsVoice(data.settings.tts_voice || "en_voice_01");
      }
    } catch (e: any) {
      setStatusMsg(`Gagal memuat pengaturan: ${e.message}`);
    }
  };

  useEffect(() => {
    if (mode === "settings") {
      loadSettings();
    }
  }, [mode]);

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.updateSettingsAI({
        ai_default_provider: defaultProv,
        writing_default_provider: writingProv,
        generation_model: genModel,
        writing_evaluation_model: writingModel,
        lm_studio_base_url: lmStudioUrl,
        tts_voice: ttsVoice,
      });
      setStatusMsg("Pengaturan AI Provider dan TTS berhasil disimpan.");
      await loadSettings();
    } catch (err: any) {
      setStatusMsg(`Gagal menyimpan pengaturan: ${err.message}`);
    }
  };

  const handleTestConnections = async () => {
    setTestingConn(true);
    try {
      const res = await api.testAIConnections();
      setProvidersStatus(res.providers_status || {});
      setStatusMsg("Pemeriksaan koneksi ke seluruh AI Provider selesai.");
    } catch (err: any) {
      setStatusMsg(`Error: ${err.message}`);
    } finally {
      setTestingConn(false);
    }
  };

  const handlePreviewVoice = async () => {
    try {
      const res = await api.previewTTS(ttsVoice);
      const url = `${API_BASE_URL}${res.file_path}?t=${Date.now()}`;
      setPreviewAudioUrl(url);
      const audio = new Audio(url);
      audio.play().catch(() => {});
    } catch (err: any) {
      setStatusMsg(`Gagal memutar preview TTS: ${err.message}`);
    }
  };

  const handleDeleteAllHistory = async () => {
    try {
      const res = await api.deleteAllHistory();
      setConfirmClearHistory(false);
      setStatusMsg(
        `Seluruh riwayat sesi berhasil dihapus (${res.deleted_sessions} sesi). Question Bank yang telah disetujui tetap aman.`
      );
      if (onHistoryCleared) onHistoryCleared();
    } catch (err: any) {
      setStatusMsg(`Error: ${err.message}`);
    }
  };

  if (mode === "about") {
    return (
      <div className="max-w-4xl space-y-6">
        <div className="rounded-lg border border-slate-300 bg-white p-6 shadow-xs space-y-4">
          <div className="flex items-center gap-2.5 border-b border-slate-200 pb-3">
            <Info className="h-5 w-5 text-blue-900" />
            <h1 className="text-xl font-extrabold text-slate-900">
              Tentang & Disclaimer Resmi — CEST Practice Simulator
            </h1>
          </div>

          <div className="rounded-md border-l-4 border-blue-900 bg-blue-50/70 p-4 text-xs leading-relaxed text-slate-800 space-y-2">
            <p className="font-bold text-slate-900">
              Posisi Produk & Hukum (Important Product / Legal Positioning):
            </p>
            <p>
              Proyek ini adalah <strong>simulator latihan pribadi (practice simulator)</strong> yang terinspirasi oleh struktur publik, tipe tugas, batas waktu, dan konstruk penilaian dari{" "}
              <em>Cambridge English Skills Test (CEST) General</em>. Aplikasi ini{" "}
              <strong>bukan produk resmi Cambridge</strong>, tidak mereproduksi bank soal milik Cambridge, tidak menggunakan soal ujian resmi, dan tidak mengklaim bahwa skor yang dihasilkan adalah skor resmi Cambridge atau <em>Cambridge English Scale</em>.
            </p>
            <p>
              Seluruh teks bacaan, naskah audio, grafik/pengumuman, serta prompt menulis dibuat secara orisinal untuk latihan mandiri.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2 text-xs">
            <div className="rounded border border-slate-200 bg-slate-50 p-4 space-y-2">
              <h2 className="font-bold uppercase tracking-wider text-slate-900">
                Mesin Adaptif 1PL IRT (Rasch) + EAP
              </h2>
              <p className="text-slate-700 leading-relaxed">
                Modul Reading dan Listening menggunakan model psikometrik{" "}
                <strong>1-Parameter Logistic Item Response Theory (Rasch)</strong> dengan estimator{" "}
                <em>Expected A Posteriori (EAP)</em>. Setiap butir soal dipilih berdasarkan informasi Fisher maksimum pada estimasi kemampuan (θ) saat ini, dilengkapi aturan keseimbangan tipe tugas dan topik.
              </p>
            </div>

            <div className="rounded border border-slate-200 bg-slate-50 p-4 space-y-2">
              <h2 className="font-bold uppercase tracking-wider text-slate-900">
                Evaluasi Writing & Arsitektur AI Lokal
              </h2>
              <p className="text-slate-700 leading-relaxed">
                Modul Writing terdiri atas Part 1 (Email, min. 50 kata, ~15 menit) dan Part 2 (Wider-audience text, min. 180 kata, ~30 menit) dengan total waktu 45 menit. Penilaian dilakukan oleh penyedia AI pilihan Anda (LM Studio lokal, OpenAI, atau Gemini) pada tiga dimensi utama: <em>Communicative Achievement, Organisation,</em> dan <em>Language</em>.
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const isCloudSelected =
    defaultProv === "openai" ||
    defaultProv === "gemini" ||
    writingProv === "openai" ||
    writingProv === "gemini";

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h1 className="text-2xl font-extrabold text-slate-900">
          Pengaturan Sistem (Settings)
        </h1>
        <p className="text-xs text-slate-600 mt-0.5">
          Konfigurasi AI Provider (LM Studio, OpenAI, Gemini), sintesis suara TTS lokal, parameter waktu ujian, dan manajemen penyimpanan.
        </p>
      </div>

      {statusMsg && (
        <div className="rounded-lg border border-blue-300 bg-blue-50 px-4 py-3 text-xs font-medium text-blue-950 flex items-center justify-between">
          <span>{statusMsg}</span>
          <button
            type="button"
            onClick={() => setStatusMsg(null)}
            className="font-bold text-blue-900 ml-4 cursor-pointer"
          >
            ✕
          </button>
        </div>
      )}

      {/* Privacy Notice for Cloud AI Mode (PRD Section 32.3) */}
      {isCloudSelected && (
        <div className="rounded-lg border border-amber-300 bg-amber-50 p-4 text-xs text-amber-950 flex items-start gap-3">
          <ShieldAlert className="h-5 w-5 text-amber-700 shrink-0 mt-0.5" />
          <div>
            <strong className="block font-bold">Pemberitahuan Privasi (Cloud AI Mode):</strong>
            Cloud AI mode sends your writing or generation prompts to the selected provider. Use LM Studio for local-only AI processing.
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* AI Provider Configuration Form (PRD Section 35.1) */}
        <form
          onSubmit={handleSaveSettings}
          className="lg:col-span-7 rounded-lg border border-slate-300 bg-white p-6 shadow-xs space-y-4"
        >
          <div className="flex items-center justify-between border-b border-slate-200 pb-3">
            <div className="flex items-center gap-2">
              <Cpu className="h-4 w-4 text-blue-900" />
              <h2 className="text-sm font-extrabold uppercase tracking-wider text-slate-900">
                AI Provider & Model Configuration
              </h2>
            </div>
            <button
              id="test-ai-connections-btn"
              type="button"
              disabled={testingConn}
              onClick={handleTestConnections}
              className="inline-flex items-center gap-1.5 rounded border border-slate-300 bg-slate-50 hover:bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-800 cursor-pointer"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${testingConn ? "animate-spin" : ""}`} />
              <span>Test connections</span>
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Default AI Provider (Generation)
              </label>
              <select
                id="settings-default-provider"
                value={defaultProv}
                onChange={(e) => setDefaultProv(e.target.value)}
                className="w-full rounded border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900"
              >
                <option value="lm_studio">LM Studio (Local Host)</option>
                <option value="openai">OpenAI API</option>
                <option value="gemini">Gemini API</option>
                <option value="local_heuristic">Built-in Local Engine</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Writing Evaluation Provider
              </label>
              <select
                id="settings-writing-provider"
                value={writingProv}
                onChange={(e) => setWritingProv(e.target.value)}
                className="w-full rounded border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900"
              >
                <option value="lm_studio">LM Studio (Local Host)</option>
                <option value="openai">OpenAI API</option>
                <option value="gemini">Gemini API</option>
                <option value="local_heuristic">Built-in Local Rubric Engine</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Generation Model ID
              </label>
              <input
                type="text"
                value={genModel}
                onChange={(e) => setGenModel(e.target.value)}
                className="w-full rounded border border-slate-300 px-3 py-1.5 text-sm text-slate-900"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Writing Evaluation Model ID
              </label>
              <input
                type="text"
                value={writingModel}
                onChange={(e) => setWritingModel(e.target.value)}
                className="w-full rounded border border-slate-300 px-3 py-1.5 text-sm text-slate-900"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1">
              LM Studio Base URL (Host / Docker Bridge)
            </label>
            <input
              type="text"
              value={lmStudioUrl}
              onChange={(e) => setLmStudioUrl(e.target.value)}
              className="w-full rounded border border-slate-300 px-3 py-1.5 text-xs font-mono text-slate-800"
            />
          </div>

          {/* Connection Status Indicators */}
          <div className="rounded bg-slate-50 border border-slate-200 p-3.5 space-y-2 text-xs">
            <div className="font-bold text-slate-700 uppercase tracking-wider text-[11px]">
              Status Koneksi Provider:
            </div>
            {["lm_studio", "openai", "gemini", "local_heuristic"].map((key) => {
              const st = providersStatus[key] || {};
              return (
                <div key={key} className="flex items-center justify-between">
                  <span className="font-semibold text-slate-800 uppercase">{key}:</span>
                  <span
                    className={`inline-flex items-center gap-1 font-medium ${
                      st.connected ? "text-emerald-700" : "text-slate-500"
                    }`}
                  >
                    {st.connected ? (
                      <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
                    ) : (
                      <XCircle className="h-3.5 w-3.5 text-slate-400" />
                    )}
                    {st.status || "Unknown"}
                  </span>
                </div>
              );
            })}
          </div>

          <button
            id="save-ai-settings-btn"
            type="submit"
            className="rounded-md bg-blue-900 hover:bg-blue-800 px-5 py-2 text-xs font-semibold text-white cursor-pointer"
          >
            Simpan Pengaturan
          </button>
        </form>

        {/* Right Column: TTS Settings, Exam Timings, and Storage / History Deletion */}
        <div className="lg:col-span-5 space-y-6">
          {/* TTS Settings (PRD Section 35.2) */}
          <div className="rounded-lg border border-slate-300 bg-white p-5 shadow-xs space-y-4">
            <div className="flex items-center gap-2 border-b border-slate-200 pb-2.5">
              <Volume2 className="h-4 w-4 text-blue-900" />
              <h2 className="text-sm font-extrabold uppercase tracking-wider text-slate-900">
                TTS / Audio Settings
              </h2>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block font-bold text-slate-700 mb-1">TTS Provider</label>
                <input
                  type="text"
                  disabled
                  value="Local TTS Adapter (Offline WAV Synthesizer)"
                  className="w-full rounded border border-slate-200 bg-slate-100 px-3 py-1.5 text-slate-700"
                />
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Voice Profile</label>
                <select
                  value={ttsVoice}
                  onChange={(e) => setTtsVoice(e.target.value)}
                  className="w-full rounded border border-slate-300 bg-white px-3 py-1.5 text-slate-900"
                >
                  {voices.map((v: any) => (
                    <option key={v.id} value={v.id}>
                      {v.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex items-center gap-3 pt-1">
                <button
                  id="tts-preview-play-btn"
                  type="button"
                  onClick={handlePreviewVoice}
                  className="inline-flex items-center gap-1.5 rounded bg-slate-800 hover:bg-slate-700 px-3.5 py-2 text-xs font-semibold text-white cursor-pointer"
                >
                  <Volume2 className="h-3.5 w-3.5" /> Play Preview
                </button>
                {previewAudioUrl && (
                  <span className="text-[11px] text-emerald-700 font-medium">
                    ✓ Sampel audio lokal berhasil diputar
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Exam Defaults (PRD Section 35.3) */}
          <div className="rounded-lg border border-slate-300 bg-white p-5 shadow-xs space-y-3">
            <h2 className="text-sm font-extrabold uppercase tracking-wider text-slate-900 border-b border-slate-200 pb-2">
              Parameter Ujian Standar (Locked Construct)
            </h2>
            <div className="space-y-1.5 text-xs text-slate-700">
              <div className="flex justify-between">
                <span>Reading max time:</span>
                <strong>59 min (Adaptive 1PL IRT)</strong>
              </div>
              <div className="flex justify-between">
                <span>Listening max time:</span>
                <strong>59 min (Auto-play 2x)</strong>
              </div>
              <div className="flex justify-between">
                <span>Writing total time:</span>
                <strong>45 min (Part 1: ~15m, Part 2: ~30m)</strong>
              </div>
              <div className="flex justify-between">
                <span>Practice explanations:</span>
                <strong className="text-emerald-700">ON</strong>
              </div>
            </div>
          </div>

          {/* Storage & History Management (PRD Section 19.4) */}
          <div className="rounded-lg border border-rose-200 bg-white p-5 shadow-xs space-y-3">
            <div className="flex items-center gap-2 border-b border-slate-200 pb-2">
              <Trash2 className="h-4 w-4 text-rose-700" />
              <h2 className="text-sm font-extrabold uppercase tracking-wider text-slate-900">
                Manajemen Riwayat & Penyimpanan
              </h2>
            </div>
            <p className="text-xs text-slate-600">
              Menghapus seluruh riwayat sesi ujian tidak akan menghapus Question Bank yang telah disetujui (APPROVED).
            </p>
            {!confirmClearHistory ? (
              <button
                id="delete-all-history-btn"
                type="button"
                onClick={() => setConfirmClearHistory(true)}
                className="inline-flex items-center gap-1.5 rounded border border-rose-300 bg-rose-50 hover:bg-rose-100 px-3.5 py-2 text-xs font-semibold text-rose-800 cursor-pointer"
              >
                <Trash2 className="h-3.5 w-3.5" /> Delete all history (Hapus Semua Riwayat)
              </button>
            ) : (
              <div className="flex items-center gap-2">
                <button
                  id="confirm-delete-all-history-btn"
                  type="button"
                  onClick={handleDeleteAllHistory}
                  className="rounded bg-rose-700 hover:bg-rose-600 px-3.5 py-1.5 text-xs font-semibold text-white cursor-pointer"
                >
                  Ya, Hapus Semua Riwayat
                </button>
                <button
                  type="button"
                  onClick={() => setConfirmClearHistory(false)}
                  className="rounded border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-700 cursor-pointer"
                >
                  Batal
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
