"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { FILM, PLAY_FILM_EVENT } from "@/lib/film";

const SEEN_KEY = "agrobo:film-seen";

/**
 * Homepage film. If the visitor stays at the top of the page without scrolling, clicking
 * or typing for FILM.idleMs, the film fades in over the whole window and plays muted
 * (browsers block autoplay with sound). Any scroll, click or key hands the page back.
 * It auto-plays once per browser session; the hero button replays it with sound.
 */
export function IdleFilm() {
  const video = useRef<HTMLVideoElement>(null);
  const [open, setOpen] = useState(false);
  const [visible, setVisible] = useState(false);
  const [muted, setMuted] = useState(true);
  const [progress, setProgress] = useState(0);
  const openedAt = useRef(0);

  const close = useCallback(() => {
    setVisible(false);
    video.current?.pause();
    try {
      sessionStorage.setItem(SEEN_KEY, "1");
    } catch {}
    if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
    setTimeout(() => setOpen(false), 600);
  }, []);

  const start = useCallback((withSound: boolean) => {
    const v = video.current;
    if (!v) return;
    openedAt.current = Date.now();
    setOpen(true);
    requestAnimationFrame(() => setVisible(true));
    v.currentTime = 0;
    v.muted = !withSound;
    setMuted(!withSound);
    v.play().catch(() => {
      // sound refused without a gesture: fall back to muted playback
      v.muted = true;
      setMuted(true);
      v.play().catch(() => {});
    });
  }, []);

  // Idle trigger: only at the top of the homepage, once per session, never for reduced motion.
  useEffect(() => {
    let seen = false;
    try {
      seen = sessionStorage.getItem(SEEN_KEY) === "1";
    } catch {}
    if (seen || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let done = false;
    const arm = () => {
      clearTimeout(timer);
      if (done || window.scrollY > 40) return;
      timer = setTimeout(() => {
        if (window.scrollY > 40 || document.hidden) return arm();
        done = true;
        start(false);
      }, FILM.idleMs);
    };
    const events = ["scroll", "wheel", "pointerdown", "keydown", "touchstart"] as const;
    events.forEach((e) => window.addEventListener(e, arm, { passive: true }));
    arm();
    return () => {
      clearTimeout(timer);
      events.forEach((e) => window.removeEventListener(e, arm));
    };
  }, [start]);

  // Explicit "watch the film" from the hero: a real gesture, so play with sound.
  useEffect(() => {
    const onPlay = () => start(true);
    window.addEventListener(PLAY_FILM_EVENT, onPlay);
    return () => window.removeEventListener(PLAY_FILM_EVENT, onPlay);
  }, [start]);

  // While open, any scroll or key hands the page back (Space/M toggle sound instead).
  useEffect(() => {
    if (!open) return;
    const grace = () => Date.now() - openedAt.current < 400;
    const onScroll = () => !grace() && close();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "m" || e.key === "M") {
        const v = video.current;
        if (v) {
          v.muted = !v.muted;
          setMuted(v.muted);
        }
        return;
      }
      if (e.key === "Tab") return;
      close();
    };
    window.addEventListener("wheel", onScroll, { passive: true });
    window.addEventListener("touchmove", onScroll, { passive: true });
    window.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("wheel", onScroll);
      window.removeEventListener("touchmove", onScroll);
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [open, close]);

  const toggleSound = (e: React.MouseEvent) => {
    e.stopPropagation();
    const v = video.current;
    if (!v) return;
    v.muted = !v.muted;
    setMuted(v.muted);
    if (v.paused) v.play().catch(() => {});
  };

  const fullscreen = (e: React.MouseEvent) => {
    e.stopPropagation();
    const el = video.current?.parentElement;
    if (!el) return;
    if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
    else el.requestFullscreen?.().catch(() => {});
  };

  return (
    <div
      role="dialog"
      aria-modal={open}
      aria-label="Agrobo film"
      aria-hidden={!open}
      onClick={close}
      className={`fixed inset-0 z-[100] bg-black transition-opacity duration-700 ${
        open ? "" : "pointer-events-none invisible"
      } ${visible ? "opacity-100" : "opacity-0"}`}
    >
      <video
        ref={video}
        poster={FILM.poster}
        preload="metadata"
        playsInline
        muted
        onEnded={close}
        onTimeUpdate={(e) => {
          const v = e.currentTarget;
          if (v.duration) setProgress(v.currentTime / v.duration);
        }}
        className="h-full w-full object-contain [@media(min-aspect-ratio:7/5)]:object-cover"
      >
        {FILM.sources.map((s) => (
          <source key={s.src} src={s.src} type={s.type} />
        ))}
      </video>
      <div className="pointer-events-none absolute inset-x-0 top-0 flex items-center justify-between bg-gradient-to-b from-black/60 to-transparent p-4 md:p-6">
        <span className="hidden font-mono text-[11px] uppercase tracking-[0.12em] text-white/60 sm:block">Agrobo · the film</span>
        <span className="sm:hidden" />
        <div className="pointer-events-auto flex items-center gap-2">
          <button
            onClick={toggleSound}
            className="whitespace-nowrap rounded-full border border-white/25 bg-black/40 px-4 py-2 text-[13px] font-medium text-white backdrop-blur hover:bg-white/15"
          >
            {muted ? "Tap for sound" : "Mute"}
          </button>
          <button
            onClick={fullscreen}
            aria-label="Full screen"
            className="hidden rounded-full border border-white/25 bg-black/40 p-2 text-white backdrop-blur hover:bg-white/15 md:block"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5" />
            </svg>
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              close();
            }}
            className="whitespace-nowrap rounded-full bg-white px-4 py-2 text-[13px] font-medium text-black hover:bg-lime"
          >
            Skip to site ↓
          </button>
        </div>
      </div>
      <div className="pointer-events-none absolute inset-x-0 bottom-0 p-4 md:p-6">
        <div className="mb-3 text-center text-[12px] text-white/50">
          <span className="hidden md:inline">Scroll, click or press any key to return to the page</span>
          <span className="md:hidden">Swipe or tap to return to the page</span>
        </div>
        <div className="h-[3px] w-full overflow-hidden rounded-full bg-white/15">
          <div className="h-full bg-lime transition-[width] duration-200" style={{ width: `${progress * 100}%` }} />
        </div>
      </div>
    </div>
  );
}

export function WatchFilmButton({ className = "" }: { className?: string }) {
  return (
    <button
      onClick={() => window.dispatchEvent(new Event(PLAY_FILM_EVENT))}
      className={`group inline-flex items-center gap-3 text-[14px] text-[#c9d3cd] hover:text-white ${className}`}
    >
      <span className="flex h-9 w-9 items-center justify-center rounded-full border border-night-line bg-night-2 transition group-hover:border-lime group-hover:bg-lime group-hover:text-ink">
        <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor" aria-hidden>
          <path d="M2 1.2v9.6L10.5 6z" />
        </svg>
      </span>
      Watch the film <span className="text-[#6f8479]">{FILM.durationLabel}</span>
    </button>
  );
}
