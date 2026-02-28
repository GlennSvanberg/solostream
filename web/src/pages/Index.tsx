import { useState, useEffect, useRef, useCallback } from "react";
import { Play, Pause, Volume2, VolumeX, SkipForward } from "lucide-react";
import { Slider } from "@/components/ui/slider";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";

export type Episode = { id: string; title: string; url: string };

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
  const [volume, setVolume] = useState([75]);
  const [episodes, setEpisodes] = useState<Episode[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [episodesOpen, setEpisodesOpen] = useState(false);
  const audioRef = useRef<HTMLAudioElement>(null);

  const currentEpisode = episodes[currentIndex] ?? null;

  // Fetch episode list
  useEffect(() => {
    fetch("/episodes.json")
      .then((r) => r.json())
      .then((data: { episodes: Episode[] }) => {
        setEpisodes(data.episodes ?? []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  // Wire audio element events (runs once when episodes available)
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio || episodes.length === 0) return;

    const onEnded = () => {
      setCurrentIndex((i) => (i + 1) % episodes.length);
      setIsPlaying(true);
    };
    const onPlay = () => setIsPlaying(true);
    const onPause = () => setIsPlaying(false);

    audio.addEventListener("ended", onEnded);
    audio.addEventListener("play", onPlay);
    audio.addEventListener("pause", onPause);

    return () => {
      audio.removeEventListener("ended", onEnded);
      audio.removeEventListener("play", onPlay);
      audio.removeEventListener("pause", onPause);
    };
  }, [episodes.length]);

  // Sync volume
  useEffect(() => {
    const audio = audioRef.current;
    if (audio) audio.volume = volume[0] / 100;
  }, [volume]);

  // Load episode when it changes
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio || !currentEpisode) return;

    audio.src = currentEpisode.url;
    if (isPlaying) {
      audio.play().catch(() => setIsPlaying(false));
    }
  }, [currentEpisode]);

  // Sync play/pause when isPlaying changes
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio || !currentEpisode) return;

    if (isPlaying) {
      audio.play().catch(() => setIsPlaying(false));
    } else {
      audio.pause();
    }
  }, [isPlaying, currentEpisode]);

  const togglePlay = useCallback(() => {
    const audio = audioRef.current;
    if (!audio || episodes.length === 0) return;
    if (isPlaying) {
      audio.pause();
    } else {
      audio.play().catch(() => {});
    }
  }, [isPlaying, episodes.length]);

  const goToNextEpisode = useCallback(() => {
    if (episodes.length === 0) return;
    setCurrentIndex((i) => (i + 1) % episodes.length);
  }, [episodes.length]);

  return (
    <div className="relative flex flex-col items-center justify-center h-full px-6 py-8 overflow-hidden selection:bg-accent/20">
      {/* Hidden audio element - must be in DOM for playback to work reliably */}
      {episodes.length > 0 && currentEpisode && (
        <audio ref={audioRef} style={{ display: "none" }} />
      )}
      {/* Film grain */}
      <div className="grain-overlay" />
      {/* Background gradient orbs */}
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

      {/* Header */}
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

      {/* Player */}
      <main className="relative flex items-start gap-4 w-full max-w-md">
        <div className="flex flex-col items-center gap-5 flex-1">
          {/* Waveform */}
          <WaveformVisualizer isPlaying={isPlaying} />

          {/* Play/Pause */}
          <div className="relative">
            {/* Outer ring */}
            <div
              className="absolute inset-[-8px] rounded-full border transition-all duration-700"
              style={{
                borderColor: isPlaying ? "hsl(220 10% 92% / 0.1)" : "hsl(220 10% 92% / 0.05)",
              }}
            />
            <button
              onClick={togglePlay}
              className="relative flex items-center justify-center w-[72px] h-[72px] rounded-full bg-foreground text-background transition-all duration-300 hover:scale-105 active:scale-95 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
              style={{
                animation: isPlaying ? "breathe 3s ease-in-out infinite" : "none",
              }}
              aria-label={isPlaying ? "Pause" : "Play"}
            >
              {isPlaying ? (
                <Pause className="w-7 h-7" strokeWidth={2.5} />
              ) : (
                <Play className="w-7 h-7 ml-0.5" strokeWidth={2.5} />
              )}
            </button>
          </div>

        {/* Listening label */}
        <p
          className={`text-xs tracking-[0.12em] uppercase font-medium transition-all duration-700 ${isPlaying ? "text-muted-foreground opacity-100 translate-y-0" : "opacity-0 translate-y-2"}`}
          style={{ animation: isPlaying ? "float 4s ease-in-out infinite" : "none" }}
        >
          You're listening live
        </p>

        {/* Volume */}
        <div className="flex items-center gap-3 w-full max-w-[180px] mt-2">
          {volume[0] === 0 ? (
            <VolumeX className="w-3.5 h-3.5 text-muted-foreground/60 shrink-0" />
          ) : (
            <Volume2 className="w-3.5 h-3.5 text-muted-foreground/60 shrink-0" />
          )}
          <Slider
            value={volume}
            onValueChange={setVolume}
            max={100}
            step={1}
            className="w-full"
          />
        </div>

          {/* Now Playing */}
          <section
            className={`flex flex-col items-center gap-2 pt-6 mt-2 w-full transition-all duration-700 ${isPlaying || currentEpisode ? "opacity-100 translate-y-0" : "opacity-30 translate-y-1"}`}
          >
          <div className="w-10 h-px bg-border mb-2" />
          <span className="text-[10px] font-semibold tracking-[0.25em] uppercase text-muted-foreground">
            Now Live
          </span>
          {loading ? (
            <p className="text-sm text-muted-foreground/80">Loading...</p>
          ) : currentEpisode ? (
            <>
              <h2
                className="text-2xl sm:text-3xl font-semibold text-foreground tracking-tight text-center px-2"
                style={{ fontFamily: "'Space Grotesk', sans-serif" }}
              >
                {currentEpisode.title}
              </h2>
              <p className="text-sm text-muted-foreground/80 text-center max-w-[260px] leading-relaxed font-light">
                {episodes.length} episode{episodes.length !== 1 ? "s" : ""} in rotation
              </p>
            </>
          ) : (
            <p className="text-sm text-muted-foreground/80">No episodes yet</p>
          )}
          </section>
        </div>
        
        {/* Next Episode Button */}
        {episodes.length > 1 && (
          <button
            onClick={goToNextEpisode}
            className="flex items-center justify-center w-8 h-8 rounded-full text-muted-foreground/40 hover:text-muted-foreground/70 hover:bg-muted/30 transition-all duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background mt-[36px]"
            aria-label="Next episode"
          >
            <SkipForward className="w-4 h-4" strokeWidth={2} />
          </button>
        )}
      </main>

      {/* Footer */}
      <footer className="relative mt-auto pt-6 pb-4 flex flex-col items-center gap-1.5">
        <p className="text-[11px] text-muted-foreground/40 tracking-wide">
          solostream · personal radio
        </p>
        <div className="flex items-center gap-2">
          <p className="text-[10px] text-muted-foreground/25 tracking-wider">
            Live audio · no rewinds
          </p>
          {episodes.length >= 1 && (
            <Popover open={episodesOpen} onOpenChange={setEpisodesOpen}>
              <PopoverTrigger asChild>
                <button
                  className="text-[10px] text-muted-foreground/40 tracking-wider hover:text-muted-foreground/70 transition-colors"
                  aria-label="Select episode"
                >
                  · Episodes
                </button>
              </PopoverTrigger>
              <PopoverContent
                side="top"
                align="center"
                className="w-64 max-h-[200px] overflow-y-auto p-2"
              >
                <ul className="space-y-0.5">
                  {episodes.map((ep, i) => (
                    <li key={ep.id}>
                      <button
                        onClick={() => {
                          setCurrentIndex(i);
                          setEpisodesOpen(false);
                        }}
                        className={`w-full text-left px-2 py-1.5 rounded text-xs transition-colors ${
                          i === currentIndex
                            ? "bg-accent/20 text-accent-foreground"
                            : "text-muted-foreground hover:bg-muted hover:text-foreground"
                        }`}
                      >
                        {ep.title}
                      </button>
                    </li>
                  ))}
                </ul>
              </PopoverContent>
            </Popover>
          )}
        </div>
      </footer>
    </div>
  );
};

export default Index;
