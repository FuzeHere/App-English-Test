"use client";

import React, { useEffect, useRef, useState } from "react";
import { Volume2, Play, Pause, RotateCcw, Lock, CheckCircle2, Clock } from "lucide-react";
import { API_BASE_URL } from "@/lib/api";

export type ListeningExamState =
  | "PREVIEW"
  | "PLAYBACK_1"
  | "SHORT_TRANSITION"
  | "PLAYBACK_2"
  | "ANSWER";

interface ListeningPlayerProps {
  questionId: string;
  audioUrl: string;
  durationSeconds: number;
  isSimulation: boolean;
  prelisteningSeconds: number;
  onPlaybackCycleComplete: (canProceed: boolean) => void;
}

export default function ListeningPlayer({
  questionId,
  audioUrl,
  durationSeconds,
  isSimulation,
  prelisteningSeconds,
  onPlaybackCycleComplete,
}: ListeningPlayerProps) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [machineState, setMachineState] = useState<ListeningExamState>("PREVIEW");
  const [countdown, setCountdown] = useState<number>(prelisteningSeconds || 8);
  const [volume, setVolume] = useState<number>(0.9);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [audioError, setAudioError] = useState<string | null>(null);
  const [playCount, setPlayCount] = useState<number>(0);

  const fullUrl = audioUrl.startsWith("http") ? audioUrl : `${API_BASE_URL}${audioUrl}`;

  // Reset state machine when questionId changes
  useEffect(() => {
    setAudioError(null);
    setCurrentTime(0);
    setPlayCount(0);

    if (isSimulation) {
      const preSec = Math.max(3, Math.min(12, prelisteningSeconds || 8));
      setCountdown(preSec);
      setMachineState("PREVIEW");
      onPlaybackCycleComplete(false);
    } else {
      setMachineState("ANSWER");
      onPlaybackCycleComplete(true);
    }
  }, [questionId, isSimulation, prelisteningSeconds]);

  // Countdown timer for PREVIEW and SHORT_TRANSITION in Full Test Simulation
  useEffect(() => {
    if (!isSimulation) return;

    if (machineState === "PREVIEW") {
      if (countdown <= 0) {
        setMachineState("PLAYBACK_1");
        triggerAudioPlay();
        return;
      }
      const t = setTimeout(() => setCountdown((c) => c - 1), 1000);
      return () => clearTimeout(t);
    }

    if (machineState === "SHORT_TRANSITION") {
      if (countdown <= 0) {
        setMachineState("PLAYBACK_2");
        triggerAudioPlay();
        return;
      }
      const t = setTimeout(() => setCountdown((c) => c - 1), 1000);
      return () => clearTimeout(t);
    }
  }, [machineState, countdown, isSimulation]);

  const triggerAudioPlay = () => {
    const el = audioRef.current;
    if (!el) return;
    el.currentTime = 0;
    el.volume = volume;
    el.play()
      .then(() => {
        setIsPlaying(true);
        setAudioError(null);
      })
      .catch(() => {
        // Fallback if browser autoplay policy requires interaction
        setAudioError("Klik tombol 'Mulai Audio' untuk memulai pemutaran otomatis.");
      });
  };

  const handleAudioEnded = () => {
    setIsPlaying(false);
    const nextCount = playCount + 1;
    setPlayCount(nextCount);

    if (isSimulation) {
      if (machineState === "PLAYBACK_1") {
        setCountdown(2);
        setMachineState("SHORT_TRANSITION");
      } else if (machineState === "PLAYBACK_2") {
        setMachineState("ANSWER");
        onPlaybackCycleComplete(true);
      }
    } else {
      setMachineState("ANSWER");
      onPlaybackCycleComplete(true);
    }
  };

  const handleVolumeChange = (val: number) => {
    setVolume(val);
    if (audioRef.current) {
      audioRef.current.volume = val;
    }
  };

  // Practice mode controls
  const togglePracticePlayPause = () => {
    if (isSimulation || !audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      audioRef.current.play().then(() => setIsPlaying(true)).catch(() => {});
    }
  };

  const replayPractice = () => {
    if (isSimulation || !audioRef.current) return;
    audioRef.current.currentTime = 0;
    audioRef.current.play().then(() => setIsPlaying(true)).catch(() => {});
  };

  const handleSeekPractice = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (isSimulation || !audioRef.current) return;
    const t = parseFloat(e.target.value);
    audioRef.current.currentTime = t;
    setCurrentTime(t);
  };

  return (
    <div
      id="listening-player-card"
      className="rounded-lg border border-slate-300 bg-slate-900 text-white p-5 shadow-sm"
    >
      <audio
        ref={audioRef}
        src={fullUrl}
        preload="auto"
        onTimeUpdate={() => {
          if (audioRef.current) setCurrentTime(audioRef.current.currentTime);
        }}
        onEnded={handleAudioEnded}
        onError={() => {
          setAudioError("Gagal memuat berkas audio lokal. Silakan klik Coba Lagi.");
        }}
      />

      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-700 pb-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-md bg-blue-600 text-white">
            <Volume2 className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-blue-300">
                {isSimulation ? "Simulasi Ujian — Pemutaran Ketat (2x)" : "Mode Latihan — Kontrol Audio Bebas"}
              </span>
              {isSimulation && (
                <span className="inline-flex items-center gap-1 rounded bg-slate-800 px-2 py-0.5 text-[11px] text-slate-300 border border-slate-700">
                  <Lock className="h-3 w-3" /> Tanpa Jeda / Putar Ulang
                </span>
              )}
            </div>
            <p className="text-sm font-medium text-slate-100 mt-0.5">
              {machineState === "PREVIEW" &&
                `Waktu baca soal sebelum audio dimulai: ${countdown} detik`}
              {machineState === "PLAYBACK_1" && "Sedang memutar rekaman — Putaran 1 dari 2..."}
              {machineState === "SHORT_TRANSITION" &&
                `Jeda singkat sebelum putaran kedua: ${countdown} detik...`}
              {machineState === "PLAYBACK_2" && "Sedang memutar rekaman — Putaran 2 dari 2..."}
              {machineState === "ANSWER" &&
                (isSimulation
                  ? "Siklus pemutaran selesai (2/2). Anda dapat mengirim jawaban dan melanjutkan."
                  : "Audio siap diputar. Anda dapat menjeda, menggeser waktu, atau memutar ulang.")}
            </p>
          </div>
        </div>

        {/* Volume Control (Always allowed per PRD Section 11.5) */}
        <div className="flex items-center gap-2 bg-slate-800 px-3 py-1.5 rounded border border-slate-700">
          <Volume2 className="h-4 w-4 text-slate-300" />
          <label htmlFor="audio-volume-slider" className="text-xs text-slate-300">
            Volume
          </label>
          <input
            id="audio-volume-slider"
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={volume}
            onChange={(e) => handleVolumeChange(parseFloat(e.target.value))}
            className="w-20 accent-blue-400 cursor-pointer"
          />
        </div>
      </div>

      {/* State Progress Steps for Full Test Simulation */}
      {isSimulation ? (
        <div className="mt-4">
          <div className="grid grid-cols-4 gap-2 text-xs">
            <div
              className={`rounded px-3 py-2 border ${
                machineState === "PREVIEW"
                  ? "bg-blue-950 border-blue-400 text-blue-200 font-semibold"
                  : "bg-slate-800/70 border-slate-700 text-slate-400"
              }`}
            >
              1. Baca Soal ({prelisteningSeconds}d)
            </div>
            <div
              className={`rounded px-3 py-2 border ${
                machineState === "PLAYBACK_1"
                  ? "bg-blue-950 border-blue-400 text-blue-200 font-semibold"
                  : "bg-slate-800/70 border-slate-700 text-slate-400"
              }`}
            >
              2. Putaran Pertama
            </div>
            <div
              className={`rounded px-3 py-2 border ${
                machineState === "PLAYBACK_2" || machineState === "SHORT_TRANSITION"
                  ? "bg-blue-950 border-blue-400 text-blue-200 font-semibold"
                  : "bg-slate-800/70 border-slate-700 text-slate-400"
              }`}
            >
              3. Putaran Kedua
            </div>
            <div
              className={`rounded px-3 py-2 border flex items-center gap-1.5 ${
                machineState === "ANSWER"
                  ? "bg-emerald-950 border-emerald-500 text-emerald-200 font-semibold"
                  : "bg-slate-800/70 border-slate-700 text-slate-400"
              }`}
            >
              <CheckCircle2 className="h-3.5 w-3.5" /> 4. Siap Lanjut
            </div>
          </div>

          {/* Non-interactive progress bar */}
          <div className="mt-3 flex items-center gap-3">
            <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-800">
              <div
                className="h-full bg-blue-500 transition-all duration-200"
                style={{
                  width: `${Math.min(100, (currentTime / Math.max(1, durationSeconds)) * 100)}%`,
                }}
              />
            </div>
            <span className="font-mono text-xs text-slate-300">
              {Math.floor(currentTime)}s / {Math.ceil(durationSeconds)}s
            </span>
            {machineState === "PREVIEW" && (
              <button
                id="skip-prelistening-btn"
                type="button"
                onClick={() => setCountdown(0)}
                className="rounded bg-slate-800 hover:bg-slate-700 px-2.5 py-1 text-xs text-slate-200 border border-slate-600 cursor-pointer"
              >
                Mulai Putar Sekarang
              </button>
            )}
          </div>
        </div>
      ) : (
        /* Practice Mode Full Interactive Controls (Pause, Replay, Seek allowed per PRD Section 11.5) */
        <div className="mt-4 flex flex-wrap items-center gap-4">
          <button
            id="practice-audio-play-pause"
            type="button"
            onClick={togglePracticePlayPause}
            className="inline-flex items-center gap-2 rounded-md bg-blue-600 hover:bg-blue-500 px-4 py-2 text-xs font-semibold text-white cursor-pointer"
          >
            {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
            {isPlaying ? "Jeda Audio" : "Putar Audio"}
          </button>

          <button
            id="practice-audio-replay"
            type="button"
            onClick={replayPractice}
            className="inline-flex items-center gap-1.5 rounded-md bg-slate-800 hover:bg-slate-700 border border-slate-600 px-3 py-2 text-xs font-medium text-slate-200 cursor-pointer"
          >
            <RotateCcw className="h-3.5 w-3.5" /> Putar Ulang
          </button>

          <div className="flex flex-1 items-center gap-3 min-w-[200px]">
            <input
              id="practice-audio-seek"
              type="range"
              min={0}
              max={Math.max(1, durationSeconds)}
              step={0.2}
              value={Math.min(currentTime, durationSeconds)}
              onChange={handleSeekPractice}
              className="w-full accent-blue-400 cursor-pointer"
            />
            <span className="font-mono text-xs text-slate-300 whitespace-nowrap">
              {Math.floor(currentTime)}s / {Math.ceil(durationSeconds)}s
            </span>
          </div>
        </div>
      )}

      {/* Controlled Audio Error Recovery Action per PRD Section 38.3 */}
      {audioError && (
        <div className="mt-3 flex items-center justify-between rounded bg-amber-950/90 border border-amber-600 px-3 py-2 text-xs text-amber-200">
          <span>{audioError}</span>
          <button
            id="audio-recovery-btn"
            type="button"
            onClick={() => {
              if (machineState === "PREVIEW") {
                setMachineState("PLAYBACK_1");
              }
              triggerAudioPlay();
            }}
            className="rounded bg-amber-600 hover:bg-amber-500 px-3 py-1 font-semibold text-white cursor-pointer"
          >
            Mulai Audio
          </button>
        </div>
      )}
    </div>
  );
}
