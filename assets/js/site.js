document.querySelectorAll("[data-tabs]").forEach((root) => {
  const buttons = root.querySelectorAll("[data-tab]");
  const panels = root.querySelectorAll("[data-panel]");
  buttons.forEach((button) => {
    button.addEventListener("click", () => {
      const id = button.getAttribute("data-tab");
      buttons.forEach((item) => item.classList.toggle("active", item === button));
      panels.forEach((panel) => panel.classList.toggle("active", panel.getAttribute("data-panel") === id));
    });
  });
});

document.querySelectorAll("[data-menu]").forEach((menu) => {
  const button = menu.querySelector("button");
  button.addEventListener("click", (event) => {
    event.stopPropagation();
    const open = menu.classList.contains("open");
    document.querySelectorAll("[data-menu].open").forEach((item) => item.classList.remove("open"));
    menu.classList.toggle("open", !open);
  });
});

document.addEventListener("click", (event) => {
  if (event.target.closest("[data-menu]")) return;
  document.querySelectorAll("[data-menu].open").forEach((item) => item.classList.remove("open"));
});

document.querySelectorAll("[data-author]").forEach((button) => {
  button.addEventListener("click", () => {
    const panel = button.parentElement.nextElementSibling;
    panel.classList.toggle("open");
    button.setAttribute("aria-expanded", panel.classList.contains("open") ? "true" : "false");
  });
});

const article = document.querySelector(".article");
const pct = document.querySelector("[data-pct]");
let size = 100;
function applySize() {
  if (!article) return;
  article.style.fontSize = size === 100 ? "" : (size / 100) * 16 + "px";
  if (pct) pct.textContent = size + "%";
}
document.querySelector("[data-font='up']")?.addEventListener("click", () => {
  size = Math.min(140, size + 10);
  applySize();
});
document.querySelector("[data-font='down']")?.addEventListener("click", () => {
  size = Math.max(80, size - 10);
  applySize();
});
document.querySelector("[data-alt]")?.addEventListener("change", (event) => {
  document.body.classList.toggle("alt-display", event.target.checked);
});
