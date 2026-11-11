"use strict";

const CANVAS = { width: 1920, height: 1080 };
const PRELOAD = 2;
const SWIPE_PX = 50;
const PRESENTER = new URLSearchParams(location.search).has("presenter");
const PRESENTER_WINDOW = "mechanica-presenter";

const els = Object.fromEntries(["viewport", "stage", "prev", "next", "counter", "contents", "toggle-contents", "fullscreen",
  "open-presenter", "presenter", "presenter-counter", "presenter-timer", "presenter-clock", "next-viewport", "next-stage"]
  .map((id) => [id, document.getElementById(id)]));
const slides = [...document.querySelectorAll("#stage > .slide")];
const state = { index: -1, startedAt: Date.now() };
// Keeps the main window and the presenter window on the same slide.
const channel = "BroadcastChannel" in window ? new BroadcastChannel("mechanica-deck") : null;

const clamp = (x, low, high) => Math.min(Math.max(x, low), high);

function scaleInto(container, stage) {
  const scale = Math.min(container.clientWidth / CANVAS.width, container.clientHeight / CANVAS.height);
  stage.style.transform = `translate(-50%, -50%) scale(${scale})`;
}

function fit() {
  scaleInto(els.viewport, els.stage);
  if (PRESENTER) scaleInto(els["next-viewport"], els["next-stage"]);
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

/* ---------- presenter window ---------- */
function previewOf(slide) {
  if (!slide) return Object.assign(document.createElement("p"), { className: "end", textContent: "Ende" });
  const copy = slide.cloneNode(true);
  copy.removeAttribute("id");
  copy.classList.add("current");
  return copy;
}

function renderPresenter() {
  els["presenter-counter"].textContent = `${state.index + 1} / ${slides.length}`;
  els["next-stage"].replaceChildren(previewOf(slides[state.index + 1]));
}

const twoDigits = (n) => String(n).padStart(2, "0");

function tickClock() {
  const elapsed = Math.floor((Date.now() - state.startedAt) / 1000);
  els["presenter-timer"].textContent = `${Math.floor(elapsed / 60)}:${twoDigits(elapsed % 60)}`;
  const now = new Date();
  els["presenter-clock"].textContent = `${twoDigits(now.getHours())}:${twoDigits(now.getMinutes())}`;
}

function openPresenter() {
  const url = `${location.pathname}?presenter#slide-${state.index + 1}`;
  window.open(url, PRESENTER_WINDOW, "popup,width=1200,height=800");
}

/* ---------- navigation ---------- */
function show(index, { broadcast = true } = {}) {
  const next = clamp(index, 0, slides.length - 1);
  if (next === state.index) return;
  stopMedia(slides[state.index]);
  slides[state.index]?.classList.remove("current");
  state.index = next;
  slides.slice(Math.max(0, next - 1), next + PRELOAD + 1).forEach(load);
  slides[next].classList.add("current");
  els.counter.textContent = `${next + 1} / ${slides.length}`;
  els.prev.disabled = next === 0;
  els.next.disabled = next === slides.length - 1;
  const hash = `#slide-${next + 1}`;
  if (location.hash !== hash) history.replaceState(null, "", hash);
  if (PRESENTER) renderPresenter();
  if (broadcast) channel?.postMessage({ index: next });
}

const indexOfHash = () => {
  const match = /^#slide-(\d+)$/.exec(location.hash);
  return match ? Number(match[1]) - 1 : 0;
};

function toggleContents(open = els.contents.hidden) {
  els.contents.hidden = !open;
  els["toggle-contents"].setAttribute("aria-expanded", String(open));
}

function toggleFullscreen() {
  const request = document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen();
  request?.catch(() => {});
}

const KEYS = {
  ArrowRight: () => show(state.index + 1), ArrowDown: () => show(state.index + 1), PageDown: () => show(state.index + 1), " ": () => show(state.index + 1),
  ArrowLeft: () => show(state.index - 1), ArrowUp: () => show(state.index - 1), PageUp: () => show(state.index - 1),
  Home: () => show(0), End: () => show(slides.length - 1),
  i: () => toggleContents(), f: toggleFullscreen, s: openPresenter, Escape: () => toggleContents(false),
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

// Clips play in the main window only, so the presenter window stays silent.
function bindMedia() {
  els.stage.addEventListener("click", (event) => {
    if (PRESENTER) return;
    const clip = event.target.closest("img[data-video]");
    const youtube = event.target.closest("img[data-youtube]");
    if (clip) playVideo(clip);
    if (youtube) playYoutube(youtube);
  });
}

function startPresenter() {
  document.body.classList.add("presenter");
  document.title = `Referentenansicht – ${document.title}`;
  els.presenter.hidden = false;
  els["presenter-timer"].addEventListener("click", () => { state.startedAt = Date.now(); tickClock(); });
  tickClock();
  setInterval(tickClock, 1000);
}

function start() {
  document.querySelectorAll(".slide img[data-crop]").forEach(cropped);
  bindMedia();
  els.prev.addEventListener("click", () => show(state.index - 1));
  els.next.addEventListener("click", () => show(state.index + 1));
  els["toggle-contents"].addEventListener("click", () => toggleContents());
  els.contents.addEventListener("click", (event) => { if (event.target.closest("a")) toggleContents(false); });
  els.fullscreen.addEventListener("click", toggleFullscreen);
  els["open-presenter"].addEventListener("click", openPresenter);
  document.addEventListener("keydown", (event) => {
    if (event.metaKey || event.ctrlKey || event.altKey || event.target.closest("input, textarea, select")) return;
    const action = KEYS[event.key] ?? KEYS[event.key.toLowerCase()];
    if (!action) return;
    event.preventDefault();
    action();
  });
  channel?.addEventListener("message", (event) => show(event.data.index, { broadcast: false }));
  window.addEventListener("hashchange", () => show(indexOfHash()));
  window.addEventListener("resize", fit);
  if (PRESENTER) startPresenter();
  bindSwipe();
  fit();
  show(indexOfHash());
}

start();
