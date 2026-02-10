"use client";

import { useState, useRef, useCallback, useEffect } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type VoiceState = "idle" | "recording" | "transcribing" | "error";

interface UseVoiceOptions {
  onTranscript?: (text: string) => void;
  onError?: (error: string) => void;
  maxDuration?: number; // seconds, default 120
}

interface UseVoiceReturn {
  state: VoiceState;
  isRecording: boolean;
  isTranscribing: boolean;
  duration: number;
  error: string | null;
  isAvailable: boolean;
  startRecording: () => Promise<void>;
  stopRecording: () => void;
  cancelRecording: () => void;
}

export function useVoice(options: UseVoiceOptions = {}): UseVoiceReturn {
  const { onTranscript, onError, maxDuration = 120 } = options;

  const [state, setState] = useState<VoiceState>("idle");
  const [duration, setDuration] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [isAvailable, setIsAvailable] = useState(false);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startTimeRef = useRef<number>(0);
  const streamRef = useRef<MediaStream | null>(null);
  const recoveryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Check microphone availability
  useEffect(() => {
    const check = async () => {
      try {
        const available =
          typeof navigator !== "undefined" &&
          !!navigator.mediaDevices &&
          !!navigator.mediaDevices.getUserMedia;
        setIsAvailable(available);
      } catch {
        setIsAvailable(false);
      }
    };
    check();
  }, []);

  const cleanup = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (recoveryTimerRef.current) {
      clearTimeout(recoveryTimerRef.current);
      recoveryTimerRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    mediaRecorderRef.current = null;
    chunksRef.current = [];
  }, []);

  const cancelRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
    cleanup();
    setState("idle");
    setDuration(0);
    setError(null);
  }, [cleanup]);

  const transcribe = useCallback(
    async (blob: Blob) => {
      setState("transcribing");

      const formData = new FormData();
      formData.append("audio", blob, "recording.webm");

      const token = localStorage.getItem("jarvis_token");

      try {
        const response = await fetch(`${API_URL}/api/voice/transcribe`, {
          method: "POST",
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          body: formData,
        });

        if (!response.ok) {
          const body = await response.json().catch(() => ({ detail: response.statusText }));
          throw new Error(body.detail || `Transcription failed: ${response.status}`);
        }

        const data = await response.json();
        if (data.text) {
          onTranscript?.(data.text);
        } else {
          throw new Error("No text returned from transcription");
        }
        setState("idle");
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Transcription failed";
        setError(msg);
        setState("error");
        onError?.(msg);
        // Auto-recover after 3 seconds
        recoveryTimerRef.current = setTimeout(() => {
          setState("idle");
          setError(null);
        }, 3000);
      }
    },
    [onTranscript, onError]
  );

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      mediaRecorderRef.current.stop();
    }
  }, []);

  const startRecording = useCallback(async () => {
    setError(null);

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 16000,
        },
      });
      streamRef.current = stream;

      // Prefer webm/opus, fallback to other formats
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : MediaRecorder.isTypeSupported("audio/webm")
        ? "audio/webm"
        : MediaRecorder.isTypeSupported("audio/ogg;codecs=opus")
        ? "audio/ogg;codecs=opus"
        : "";

      const recorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: mimeType || recorder.mimeType });
        cleanup();
        if (blob.size > 0) {
          transcribe(blob);
        } else {
          setState("idle");
        }
      };

      recorder.onerror = () => {
        setError("Recording failed");
        setState("error");
        cleanup();
      };

      recorder.start(250); // collect data every 250ms
      setState("recording");
      startTimeRef.current = Date.now();
      setDuration(0);

      // Update duration every 100ms
      timerRef.current = setInterval(() => {
        const elapsed = (Date.now() - startTimeRef.current) / 1000;
        setDuration(elapsed);
        if (elapsed >= maxDuration) {
          stopRecording();
        }
      }, 100);
    } catch (err) {
      const msg =
        err instanceof Error && err.name === "NotAllowedError"
          ? "Microphone access denied. Please allow microphone access in browser settings."
          : err instanceof Error
          ? err.message
          : "Failed to start recording";
      setError(msg);
      setState("error");
      onError?.(msg);
      recoveryTimerRef.current = setTimeout(() => {
        setState("idle");
        setError(null);
      }, 3000);
    }
  }, [maxDuration, cleanup, stopRecording, transcribe, onError]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cancelRecording();
    };
  }, [cancelRecording]);

  return {
    state,
    isRecording: state === "recording",
    isTranscribing: state === "transcribing",
    duration,
    error,
    isAvailable,
    startRecording,
    stopRecording,
    cancelRecording,
  };
}
