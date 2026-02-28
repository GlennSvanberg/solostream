#!/usr/bin/env node
/**
 * Syncs episodes from solostream/episodes to web/public/episodes.
 * Copies *_postprocessed.mp3 files and generates episodes.json manifest.
 * Run from repo root: node scripts/sync-episodes.js
 */

import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");
const EPISODES_SRC = path.join(ROOT, "episodes");
const EPISODES_DEST = path.join(ROOT, "web", "public", "episodes");

function slugToTitle(slug) {
  // "2026-02-28-voice-stack-2026-top-tts-tools-and-implications" -> "Voice stack 2026 top TTS tools and implications"
  const withoutDate = slug.replace(/^\d{4}-\d{2}-\d{2}-/, "");
  return withoutDate
    .split("-")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

function main() {
  if (!fs.existsSync(EPISODES_SRC)) {
    console.warn("episodes/ directory not found, skipping sync");
    return;
  }

  fs.mkdirSync(EPISODES_DEST, { recursive: true });

  const files = fs.readdirSync(EPISODES_SRC);
  const postprocessed = files.filter((f) => f.endsWith("_postprocessed.mp3"));

  const manifest = [];

  for (const file of postprocessed) {
    const src = path.join(EPISODES_SRC, file);
    const dest = path.join(EPISODES_DEST, file);
    fs.copyFileSync(src, dest);
    const slug = file.replace(/_postprocessed\.mp3$/, "");
    manifest.push({
      id: slug,
      title: slugToTitle(slug),
      url: `/episodes/${file}`,
    });
  }

  // Sort by date (newest first)
  manifest.sort((a, b) => b.id.localeCompare(a.id));

  fs.writeFileSync(
    path.join(EPISODES_DEST, "..", "episodes.json"),
    JSON.stringify({ episodes: manifest }, null, 2)
  );

  console.log(`Synced ${manifest.length} episode(s) to web/public/episodes/`);
}

main();
