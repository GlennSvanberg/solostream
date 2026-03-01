import { useState, useEffect, useRef, useCallback } from "react";
import { Volume2, VolumeX, SkipForward, RotateCcw, Play, Pause } from "lucide-react";
import { Slider } from "@/components/ui/slider";

const STORAGE_KEY = "solostream_playback";

function loadPlaybackState(segmentCount: number): { segmentIndex: number; currentTime: number } | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const { segmentIndex, currentTime } = JSON.parse(raw);
    if (typeof segmentIndex !== "number" || segmentIndex < 0 || segmentIndex >= segmentCount) return null;
    return { segmentIndex, currentTime: typeof currentTime === "number" ? currentTime : 0 };
  } catch {
    return null;
  }
}

function savePlaybackState(segmentIndex: number, currentTime: number) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ segmentIndex, currentTime }));
  } catch {
    /* ignore */
  }
}

export type Episode = { id: string; title: string; url: string; hosts?: string[]; guest?: string | null; };

export type HostSegment = {
  id: string;
  type: "host";
  episodeId: string;
  slot: "intro" | "outro";
  url: string;
  script?: string;
};

export type MusicTrack = { id: string; url: string; mood?: string; duration?: number };

export type Segment =
  | { type: "episode"; id: string; title: string; url: string; hosts?: string[]; guest?: string | null; }
  | { type: "host"; id: string; url: string; slot: "intro" | "outro"; script?: string; episodeId?: string }
  | { type: "music"; id: string; url: string; duration?: number; mood?: string };

function buildSegmentList(
  episodes: Episode[],
  hostSegments: HostSegment[],
  musicTracks: MusicTrack[]
): { segments: Segment[]; episodeStartIndices: number[] } {
  const segments: Segment[] = [];
  const episodeStartIndices: number[] = [];

  const introByEpisode = new Map<string, HostSegment>();
  const outroByEpisode = new Map<string, HostSegment>();
  for (const h of hostSegments) {
    if (h.slot === "intro") introByEpisode.set(h.episodeId, h);
    else outroByEpisode.set(h.episodeId, h);
  }

  let musicIndex = 0;

  for (let i = 0; i < episodes.length; i++) {
    const ep = episodes[i];
    const intro = introByEpisode.get(ep.id);
    const outro = outroByEpisode.get(ep.id);

    if (musicTracks.length > 0) {
      const track = musicTracks[musicIndex % musicTracks.length];
      musicIndex++;
      segments.push({
        type: "music",
        id: track.id,
        url: track.url,
        duration: track.duration,
        mood: track.mood,
      });
    }

    episodeStartIndices.push(segments.length);

    if (intro) {
      segments.push({
        type: "host",
        id: intro.id,
        url: intro.url,
        slot: "intro",
        script: intro.script,
        episodeId: ep.id,
      });
    }
    segments.push({ type: "episode", id: ep.id, title: ep.title, url: ep.url, hosts: ep.hosts, guest: ep.guest });
    if (outro) {
      segments.push({
        type: "host",
        id: outro.id,
        url: outro.url,
        slot: "outro",
        script: outro.script,
        episodeId: ep.id,
      });
    }
  }

  return { segments, episodeStartIndices };
}

function getSegmentTitle(seg: Segment): string {
  if (seg.type === "episode") return seg.title;
  if (seg.type === "music") return "Music";
  return seg.slot === "intro" ? "Coming up" : "Up next";
}

const WAVEFORM_BARS = 40;

const WaveformVisualizer = ({ isPlaying }: { isPlaying: boolean }) => (
  <div className="flex items-end justify-center gap-[2.5px] h-16 px-4">
    {Array.from({ length: WAVEFORM_BARS }).map((_, i) => {
      const center = WAVEFORM_BARS / 2;
      const dist = Math.abs(i - center) / center;
      const maxH = 1 - dist * 0.6;
      return (
        <div
          key={i}
          className="w-[2.5px] rounded-full origin-bottom transition-all duration-500"
          style={{
            height: `${maxH * 100}%`,
            background: isPlaying
              ? `linear-gradient(to top, hsl(0 72% 55% / ${0.5 - dist * 0.3}), hsl(220 10% 92% / ${0.6 - dist * 0.3}))`
              : `hsl(220 10% 92% / 0.12)`,
            animation: isPlaying
              ? `waveform-bar ${0.7 + Math.random() * 0.8}s ease-in-out ${i * 0.04}s infinite`
              : "none",
            transform: isPlaying ? undefined : `scaleY(${0.15 + Math.random() * 0.15})`,
          }}
        />
      );
    })}
  </div>
);

const OnAirBadge = ({ isPlaying }: { isPlaying: boolean }) => (
  <div className="flex items-center gap-2.5 px-4 py-1.5 rounded-full bg-secondary/60 backdrop-blur-sm border border-border/50">
    <span className="relative flex h-2 w-2">
      {isPlaying && (
        <span
          className="absolute inline-flex h-full w-full rounded-full bg-accent"
          style={{ animation: "pulse-glow 2s cubic-bezier(0.4,0,0.6,1) infinite" }}
        />
      )}
      <span className={`relative inline-flex rounded-full h-2 w-2 transition-colors duration-500 ${isPlaying ? "bg-accent" : "bg-muted-foreground/30"}`} />
      </span>
    <span className={`text-[10px] font-semibold tracking-[0.25em] uppercase transition-colors duration-500 ${isPlaying ? "text-foreground" : "text-muted-foreground"}`}>
      On Air
    </span>
  </div>
);

const Index = () => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [hasStarted, setHasStarted] = useState(false);
  const [volume, setVolume] = useState([75]);
  const [isMuted, setIsMuted] = useState(false);
  const [segments, setSegments] = useState<Segment[]>([]);
  const [episodes, setEpisodes] = useState<Episode[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const audioRef = useRef<HTMLAudioElement>(null);
  const savedRestoreTimeRef = useRef<number | null>(null);
  const currentIndexRef = useRef(0);
  currentIndexRef.current = currentIndex;

  const currentSegment = segments[currentIndex] ?? null;
  const nextSegment = segments[(currentIndex + 1) % segments.length] ?? null;

  // Fetch episodes, host segments, and music, build segment list
  useEffect(() => {
    Promise.all([
      fetch("/episodes.json").then((r) => r.json()),
      fetch("/host_segments.json").then((r) => r.json()).catch(() => ({ segments: [] })),
      fetch("/music.json").then((r) => r.json()).catch(() => ({ tracks: [] })),
    ])
      .then(([epData, hostData, musicData]) => {
        const eps = epData.episodes ?? [];
        const hostSegs = hostData.segments ?? [];
        const musicTracks = musicData.tracks ?? [];
        setEpisodes(eps);

        if (eps.length === 0) {
          setSegments([]);
        } else {
          const { segments: segs } = buildSegmentList(
            eps,
            hostSegs,
            musicTracks
          );
          setSegments(segs);
          const saved = loadPlaybackState(segs.length);
          if (saved) {
            setCurrentIndex(saved.segmentIndex);
            savedRestoreTimeRef.current = saved.currentTime;
          }
        }
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  // Wire audio element events
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio || segments.length === 0) return;

    const onEnded = () => {
      setCurrentIndex((i) => {
        const next = (i + 1) % segments.length;
        savePlaybackState(next, 0);
        return next;
      });
      setIsPlaying(true);
    };
    const onPlay = () => {
      setIsPlaying(true);
      setHasStarted(true);
    };
    const onPause = () => setIsPlaying(false);

    let lastSave = 0;
    const onTimeUpdate = () => {
      if (audio.currentTime > 0 && segments.length > 0 && Date.now() - lastSave > 3000) {
        lastSave = Date.now();
        savePlaybackState(currentIndexRef.current, audio.currentTime);
      }
    };

    audio.addEventListener("ended", onEnded);
    audio.addEventListener("play", onPlay);
    audio.addEventListener("pause", onPause);
    audio.addEventListener("timeupdate", onTimeUpdate);

    return () => {
      audio.removeEventListener("ended", onEnded);
      audio.removeEventListener("play", onPlay);
      audio.removeEventListener("pause", onPause);
      audio.removeEventListener("timeupdate", onTimeUpdate);
    };
  }, [segments.length]);

  // Sync volume (mute = 0 but stream keeps playing; unmute restores slider level)
  useEffect(() => {
    const audio = audioRef.current;
    if (audio) audio.volume = isMuted ? 0 : volume[0] / 100;
  }, [volume, isMuted]);

  // Load segment and play (restore position from localStorage when resuming)
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio || !currentSegment) return;

    audio.src = currentSegment.url;
    const restoreTime = savedRestoreTimeRef.current;
    savedRestoreTimeRef.current = null;

    if (restoreTime !== null) {
      if (restoreTime > 0) {
        const onLoaded = () => {
          audio.currentTime = Math.min(restoreTime, audio.duration);
          audio.play().catch(() => setIsPlaying(false));
        };
        audio.addEventListener("loadedmetadata", onLoaded, { once: true });
      } else {
        audio.play().catch(() => setIsPlaying(false));
      }
    } else if (isPlaying) {
      audio.play().catch(() => setIsPlaying(false));
    }
  }, [currentSegment]);

  const tuneIn = useCallback(() => {
    const audio = audioRef.current;
    if (!audio || segments.length === 0) return;
    audio.play().catch(() => {});
  }, [segments.length]);

  const togglePlayPause = useCallback(() => {
    const audio = audioRef.current;
    if (!audio || segments.length === 0) return;
    if (isPlaying) {
      audio.pause();
    } else {
      audio.play().catch(() => {});
    }
  }, [isPlaying, segments.length]);

  const goToNextSegment = useCallback(() => {
    if (segments.length === 0) return;
    setCurrentIndex((i) => {
      const next = (i + 1) % segments.length;
      savePlaybackState(next, 0);
      return next;
    });
    setIsPlaying(true);
  }, [segments.length]);

  const rewind30 = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.currentTime = Math.max(0, audio.currentTime - 30);
  }, []);

  return (
    <div className="relative flex flex-col items-center justify-center h-full px-6 py-8 overflow-hidden selection:bg-accent/20">
      {segments.length > 0 && currentSegment && (
        <audio ref={audioRef} style={{ display: "none" }} />
      )}
      <div className="grain-overlay" />
      <div className="pointer-events-none fixed inset-0">
        <div
          className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full transition-opacity duration-1000"
          style={{
            background: "radial-gradient(circle, hsl(0 72% 55% / 0.04) 0%, transparent 70%)",
            opacity: isPlaying ? 1 : 0,
          }}
        />
        <div
          className="absolute bottom-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px]"
          style={{
            background: "radial-gradient(ellipse at bottom, hsl(240 6% 12% / 0.8) 0%, transparent 70%)",
          }}
        />
      </div>

      <header className="relative flex flex-col items-center gap-3 mb-8">
        <OnAirBadge isPlaying={isPlaying} />
        <h1
          className="text-5xl sm:text-7xl font-bold tracking-[-0.04em] text-foreground"
          style={{ fontFamily: "'Space Grotesk', sans-serif" }}
        >
          solostream
        </h1>
        <p className="text-muted-foreground text-sm tracking-[0.15em] uppercase font-light">
          Live. Right now.
        </p>
      </header>

      <main className="relative flex flex-col items-center w-full max-w-md">
        <div className="flex flex-col items-center gap-5 w-full">
          <WaveformVisualizer isPlaying={isPlaying} />

          {segments.length > 0 && (
            <div className="relative mt-4 flex items-center justify-center gap-3">
              {!hasStarted ? (
                <button
                  onClick={tuneIn}
                  className="relative px-8 py-3 rounded-full text-sm font-medium tracking-[0.15em] uppercase bg-foreground text-background hover:scale-105 active:scale-95 transition-all duration-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
                  style={{ animation: "pulse-glow 2s cubic-bezier(0.4,0,0.6,1) infinite" }}
                  aria-label="Tune in"
                >
                  Tune In
                </button>
              ) : (
                <button
                  onClick={togglePlayPause}
                  className="relative flex items-center justify-center w-14 h-14 rounded-full bg-foreground text-background hover:scale-105 active:scale-95 transition-all duration-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
                  style={{ animation: isPlaying ? "breathe 3s ease-in-out infinite" : "none" }}
                  aria-label={isPlaying ? "Pause" : "Play"}
                >
                  {isPlaying ? (
                    <Pause className="w-6 h-6" strokeWidth={2.5} />
                  ) : (
                    <Play className="w-6 h-6 ml-0.5" strokeWidth={2.5} />
                  )}
                </button>
              )}
            </div>
          )}

          <p
            className={`text-xs tracking-[0.12em] uppercase font-medium transition-all duration-700 ${isPlaying ? "text-muted-foreground opacity-100 translate-y-0" : "opacity-0 translate-y-2"}`}
            style={{ animation: isPlaying ? "float 4s ease-in-out infinite" : "none", marginTop: "-0.5rem" }}
          >
            You're listening live
          </p>

          <div className="flex items-center gap-3 w-full max-w-[180px]">
            <button
              onClick={() => setIsMuted(!isMuted)}
              className="shrink-0 p-1 rounded text-muted-foreground/60 hover:text-muted-foreground/90 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
              aria-label={isMuted ? "Unmute" : "Mute"}
              title={isMuted ? "Unmute (stream keeps playing)" : "Mute (stream keeps playing, you miss content)"}
            >
              {isMuted ? (
                <VolumeX className="w-3.5 h-3.5" />
              ) : (
                <Volume2 className="w-3.5 h-3.5" />
              )}
            </button>
            <Slider
              value={volume}
              onValueChange={setVolume}
              max={100}
              step={1}
              className="w-full"
            />
          </div>

          <div className="flex items-center justify-center gap-3 -mt-2">
            {segments.length > 0 && currentSegment && (
              <button
                onClick={rewind30}
                className="flex items-center justify-center gap-2 px-3 py-1.5 rounded-full text-[10px] uppercase tracking-widest text-muted-foreground/40 hover:text-muted-foreground/80 hover:bg-muted/30 transition-all duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
                aria-label="Rewind 30 seconds"
                title="Rewind 30 seconds"
              >
                <RotateCcw className="w-3 h-3" strokeWidth={2} />
                <span>30s</span>
              </button>
            )}
            {segments.length > 1 && (
              <button
                onClick={goToNextSegment}
                className="flex items-center justify-center gap-2 px-3 py-1.5 rounded-full text-[10px] uppercase tracking-widest text-muted-foreground/40 hover:text-muted-foreground/80 hover:bg-muted/30 transition-all duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
                aria-label="Change station"
                title="Change station"
              >
                <span>Change Station</span>
                <SkipForward className="w-3 h-3" strokeWidth={2} />
              </button>
            )}
          </div>

          <section
            className={`flex flex-col items-center gap-2 pt-6 mt-2 w-full transition-all duration-700 ${isPlaying || currentSegment ? "opacity-100 translate-y-0" : "opacity-30 translate-y-1"}`}
          >
            <div className="w-10 h-px bg-border mb-2" />
            <span className="text-[10px] font-semibold tracking-[0.25em] uppercase text-muted-foreground">
              Now Playing
            </span>
            {loading ? (
              <p className="text-sm text-muted-foreground/80">Loading...</p>
            ) : currentSegment ? (
              <>
                <h2
                  className="text-2xl sm:text-3xl font-semibold text-foreground tracking-tight text-center px-2"
                  style={{ fontFamily: "'Space Grotesk', sans-serif" }}
                >
                  {getSegmentTitle(currentSegment)}
                </h2>
                {currentSegment.type === "episode" && (
                  <p className="text-sm text-muted-foreground text-center max-w-[260px] leading-relaxed font-light mt-1">
                    {currentSegment.hosts && currentSegment.hosts.length > 0 ? (
                      <>
                        With {currentSegment.hosts.join(" and ")}
                        {currentSegment.guest ? ` and ${currentSegment.guest}` : ""}
                      </>
                    ) : (
                      "Solo stream"
                    )}
                  </p>
                )}
                {currentSegment.type === "host" && currentSegment.slot === "intro" && (
                  <div className="flex flex-col items-center">
                    <p className="text-sm text-muted-foreground/80 text-center max-w-[320px] leading-relaxed font-light line-clamp-2">
                      {episodes.find((e) => e.id === currentSegment.episodeId)?.title}
                    </p>
                    {(() => {
                      const ep = episodes.find((e) => e.id === currentSegment.episodeId);
                      if (!ep) return null;
                      const hasHosts = ep.hosts && ep.hosts.length > 0;
                      if (!hasHosts) return null;
                      return (
                        <span className="block text-xs mt-1 text-muted-foreground/60">
                          With {ep.hosts?.join(" and ")}
                          {ep.guest ? ` and ${ep.guest}` : ""}
                        </span>
                      );
                    })()}
                  </div>
                )}
                {currentSegment.type === "host" && currentSegment.slot === "outro" && (
                  <p className="text-sm text-muted-foreground/80 text-center max-w-[320px] leading-relaxed font-light line-clamp-2">
                    {nextSegment?.type === "episode" ? nextSegment.title : "Coming up"}
                  </p>
                )}
                {currentSegment.type === "music" && (
                  <p className="text-sm text-muted-foreground/80 text-center max-w-[260px] leading-relaxed font-light">
                    {currentSegment.mood ? `${currentSegment.mood} · transition` : "Transition"}
                  </p>
                )}
                
                {nextSegment && (
                  <>
                    <div className="w-8 h-px bg-border/50 my-4" />
                    <span className="text-[10px] font-semibold tracking-[0.25em] uppercase text-muted-foreground/60 mb-1">
                      Up Next
                    </span>
                    <p className="text-sm text-muted-foreground/80 text-center max-w-[260px] leading-relaxed font-light truncate">
                      {getSegmentTitle(nextSegment)}
                    </p>
                  </>
                )}
              </>
            ) : (
              <p className="text-sm text-muted-foreground/80">No episodes yet</p>
            )}
          </section>
        </div>
      </main>

      <footer className="relative mt-auto pt-6 pb-4 flex flex-col items-center gap-1.5">
        <p className="text-[11px] text-muted-foreground/40 tracking-wide">
          solostream · personal radio
        </p>
        <div className="flex items-center gap-2">
          <p className="text-[10px] text-muted-foreground/25 tracking-wider">
            Live audio · mute = you miss it
          </p>
        </div>
      </footer>
    </div>
  );
};

export default Index;
