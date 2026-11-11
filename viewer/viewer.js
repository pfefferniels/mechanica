"use strict";

const CANVAS = { width: 1920, height: 1080 };
const PRELOAD = 2;
const SWIPE_PX = 50;

const els = Object.fromEntries(["viewport", "stage", "prev", "next", "counter", "notes", "contents", "toggle-notes",
  "toggle-contents", "fullscreen"].map((id) => [id, document.getElementById(id)]));
const slides = [...document.querySelectorAll(".slide")];
const state = { index: -1 };

const clamp = (x, low, high) => Math.min(Math.max(x, low), high);

function fit() {
  const scale = Math.min(els.viewport.clientWidth / CANVAS.width, els.viewport.clientHeight / CANVAS.height);
  els.stage.style.transform = `translate(-50%, -50%) scale(${scale})`;
}

/* ---------- media ---------- */
// The slide format's crop: ZOOM over a cover fit, X% Y% placed as object-position.
function placeCrop(img, box, [zoom, x, y]) {
  const base = Math.max(box.width / img.naturalWidth, box.height / img.naturalHeight) * zoom;
  const width = img.naturalWidth * base;
  const height = img.naturalHeight * base;
  img.style.cssText = `position:absolute; max-width:none; width:${width}px; height:${height}px; `
    + `left:${(box.width - width) * x / 100}px; top:${(box.height - height) * y / 100}px`;
}

function cropped(img) {
  const crop = img.dataset.crop.split(/\s+/).map(parseFloat);
  const box = { width: parseFloat(img.style.width), height: parseFloat(img.style.height) };
  const frame = Object.assign(document.createElement("div"), { className: "crop" });
  frame.style.cssText = img.style.cssText;
  if (!frame.style.position) frame.style.position = "relative";
  img.replaceWith(frame);
  frame.append(img);
  img.addEventListener("load", () => placeCrop(img, box, crop), { once: true });
}

function load(slide) {
  slide.querySelectorAll("img[data-src]").forEach((img) => {
    img.src = img.dataset.src;
    img.removeAttribute("data-src");
  });
}

function playVideo(img) {
  const video = document.createElement("video");
  Object.assign(video, { src: img.dataset.video, poster: img.src, controls: true, playsInline: true, muted: img.dataset.videoSound === "off" });
  video.style.cssText = img.style.cssText;
  video.setAttribute("aria-label", img.alt);
  img.replaceWith(video);
  video.play().catch(() => {});
}

function youtubeUrl(img) {
  const query = new URLSearchParams({ autoplay: "1", rel: "0", start: img.dataset.start ?? "0", ...(img.dataset.end ? { end: img.dataset.end } : {}) });
  return `https://www.youtube-nocookie.com/embed/${img.dataset.youtube}?${query}`;
}

function playYoutube(img) {
  const player = Object.assign(document.createElement("iframe"), { src: youtubeUrl(img), title: img.alt, allowFullscreen: true });
  player.allow = "autoplay; encrypted-media; picture-in-picture; fullscreen";
  player.style.cssText = `${img.style.cssText}; border:0`;
  player.poster = img;
  img.replaceWith(player);
}

// Leaving a slide stops its clips: videos pause, YouTube players give way to their poster again.
function stopMedia(slide) {
  slide?.querySelectorAll("video").forEach((video) => video.pause());
  slide?.querySelectorAll("iframe").forEach((player) => player.replaceWith(player.poster));
}

/* ---------- navigation ---------- */
function notesOf(slide) {
  const aside = slide.querySelector("aside");
  return aside ? aside.textContent.trim() : "Keine Notizen zu dieser Folie.";
}

function show(index) {
  const next = clamp(index, 0, slides.length - 1);
  if (next === state.index) return;
  stopMedia(slides[state.index]);
  slides[state.index]?.classList.remove("current");
  state.index = next;
  slides.slice(Math.max(0, next - 1), next + PRELOAD + 1).forEach(load);
  slides[next].classList.add("current");
  els.counter.textContent = `${next + 1} / ${slides.length}`;
  els.notes.textContent = notesOf(slides[next]);
  els.prev.disabled = next === 0;
  els.next.disabled = next === slides.length - 1;
  const hash = `#slide-${next + 1}`;
  if (location.hash !== hash) history.replaceState(null, "", hash);
}

const indexOfHash = () => {
  const match = /^#slide-(\d+)$/.exec(location.hash);
  return match ? Number(match[1]) - 1 : 0;
};

function togglePanel(panel, button, open = panel.hidden) {
  [[els.notes, els["toggle-notes"]], [els.contents, els["toggle-contents"]]]
    .forEach(([other, otherButton]) => { other.hidden = true; otherButton.setAttribute("aria-expanded", "false"); });
  panel.hidden = !open;
  button.setAttribute("aria-expanded", String(open));
}

function toggleFullscreen() {
  const request = document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen();
  request?.catch(() => {});
}

const KEYS = {
  ArrowRight: () => show(state.index + 1), ArrowDown: () => show(state.index + 1), PageDown: () => show(state.index + 1), " ": () => show(state.index + 1),
  ArrowLeft: () => show(state.index - 1), ArrowUp: () => show(state.index - 1), PageUp: () => show(state.index - 1),
  Home: () => show(0), End: () => show(slides.length - 1),
  n: () => togglePanel(els.notes, els["toggle-notes"]), i: () => togglePanel(els.contents, els["toggle-contents"]),
  f: toggleFullscreen, Escape: () => togglePanel(els.notes, els["toggle-notes"], false),
};

function bindSwipe() {
  const start = { x: 0, y: 0 };
  els.viewport.addEventListener("pointerdown", (event) => Object.assign(start, { x: event.clientX, y: event.clientY }));
  els.viewport.addEventListener("pointerup", (event) => {
    if (event.pointerType !== "touch") return;
    const dx = event.clientX - start.x;
    if (Math.abs(dx) > SWIPE_PX && Math.abs(dx) > Math.abs(event.clientY - start.y)) show(state.index + (dx < 0 ? 1 : -1));
  });
}

function start() {
  document.querySelectorAll(".slide img[data-crop]").forEach(cropped);
  els.stage.addEventListener("click", (event) => {
    const clip = event.target.closest("img[data-video]");
    const youtube = event.target.closest("img[data-youtube]");
    if (clip) playVideo(clip);
    if (youtube) playYoutube(youtube);
  });
  els.prev.addEventListener("click", () => show(state.index - 1));
  els.next.addEventListener("click", () => show(state.index + 1));
  els["toggle-notes"].addEventListener("click", () => togglePanel(els.notes, els["toggle-notes"]));
  els["toggle-contents"].addEventListener("click", () => togglePanel(els.contents, els["toggle-contents"]));
  els.contents.addEventListener("click", (event) => { if (event.target.closest("a")) togglePanel(els.contents, els["toggle-contents"], false); });
  els.fullscreen.addEventListener("click", toggleFullscreen);
  document.addEventListener("keydown", (event) => {
    if (event.metaKey || event.ctrlKey || event.altKey || event.target.closest("input, textarea, select")) return;
    const action = KEYS[event.key] ?? KEYS[event.key.toLowerCase()];
    if (!action) return;
    event.preventDefault();
    action();
  });
  window.addEventListener("hashchange", () => show(indexOfHash()));
  window.addEventListener("resize", fit);
  bindSwipe();
  fit();
  show(indexOfHash());
}

start();
