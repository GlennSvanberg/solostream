#!/usr/bin/env node
/**
 * Syncs episodes from solostream/episodes to web/public/episodes.
 * Copies *_postprocessed.mp3 files and generates episodes.json manifest.
 * Run from repo root: node scripts/sync-episodes.js
 */

import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import matter from "gray-matter";
import yaml from "js-yaml";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");
const EPISODES_SRC = path.join(ROOT, "episodes");
const EPISODES_DEST = path.join(ROOT, "web", "public", "episodes");
const TOPICS_DIR = path.join(ROOT, "topics");
const CHARACTERS_FILE = path.join(ROOT, "characters.yaml");

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

  // Load characters map
  let characterMap = new Map();
  if (fs.existsSync(CHARACTERS_FILE)) {
    const charsContent = fs.readFileSync(CHARACTERS_FILE, "utf-8");
    try {
      const charsYaml = yaml.load(charsContent);
      if (charsYaml && charsYaml.characters) {
        for (const char of charsYaml.characters) {
          if (char.id && char.name) {
            characterMap.set(char.id, char.name);
          }
        }
      }
    } catch (e) {
      console.error("Failed to parse characters.yaml", e);
    }
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

    // Parse topic file for hosts/guest
    let hosts = [];
    let guest = null;
    const topicPath = path.join(TOPICS_DIR, `${slug}.md`);
    
    if (fs.existsSync(topicPath)) {
      try {
        const topicContent = fs.readFileSync(topicPath, "utf-8");
        const parsed = matter(topicContent);
        if (parsed.data.hosts && Array.isArray(parsed.data.hosts)) {
          hosts = parsed.data.hosts.map(h => characterMap.get(h) || h);
        }
        if (parsed.data.guest) {
          guest = characterMap.get(parsed.data.guest) || parsed.data.guest;
        }
      } catch (e) {
        console.error(`Failed to parse topic frontmatter for ${slug}`, e);
      }
    }

    manifest.push({
      id: slug,
      title: slugToTitle(slug),
      url: `/episodes/${file}`,
      hosts,
      guest
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
