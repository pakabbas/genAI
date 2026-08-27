(() => {
  const APP_ROOT = document.querySelector('meta[name="app-root"]')?.content || "";

  function withRoot(path) {
    return `${APP_ROOT}${path}`;
  }

  const state = {
    contentType: "website",
    lastPrompt: "",
    generatedHtml: "",
    isGenerating: false,
  };

  const els = {
    apiStatus: document.getElementById("apiStatus"),
    panelToggle: document.getElementById("panelToggle"),
    creationPanel: document.getElementById("creationPanel"),
    typeCards: document.querySelectorAll(".type-card"),
    promptInput: document.getElementById("promptInput"),
    charCount: document.getElementById("charCount"),
    generateBtn: document.getElementById("generateBtn"),
    sampleBtn: document.getElementById("sampleBtn"),
    clearBtn: document.getElementById("clearBtn"),
    refreshBtn: document.getElementById("refreshBtn"),
    fullscreenBtn: document.getElementById("fullscreenBtn"),
    downloadBtn: document.getElementById("downloadBtn"),
    downloadDropdown: document.getElementById("downloadDropdown"),
    downloadMenu: document.getElementById("downloadMenu"),
    downloadMenuItems: document.querySelectorAll(".download-menu-item"),
    printBtn: document.getElementById("printBtn"),
    canvasBadge: document.getElementById("canvasBadge"),
    canvasTypeLabel: document.getElementById("canvasTypeLabel"),
    canvasEmpty: document.getElementById("canvasEmpty"),
    canvasLoading: document.getElementById("canvasLoading"),
    previewFrame: document.getElementById("previewFrame"),
    canvasWrap: document.getElementById("canvasWrap"),
    toastContainer: document.getElementById("toastContainer"),
  };

  function showToast(message, type = "info") {
    const toast = document.createElement("div");
    toast.className = `toast${type === "error" ? " is-error" : type === "success" ? " is-success" : ""}`;
    toast.textContent = message;
    els.toastContainer.appendChild(toast);
    setTimeout(() => toast.remove(), 4200);
  }

  function setGenerating(isGenerating) {
    state.isGenerating = isGenerating;
    els.generateBtn.disabled = isGenerating;
    els.generateBtn.classList.toggle("is-loading", isGenerating);
    els.generateBtn.querySelector(".btn-spinner").hidden = !isGenerating;
    els.canvasLoading.hidden = !isGenerating;

    if (isGenerating) {
      els.canvasEmpty.hidden = true;
      els.previewFrame.hidden = true;
    } else if (state.generatedHtml) {
      els.canvasEmpty.hidden = true;
      els.previewFrame.hidden = false;
    } else {
      els.canvasEmpty.hidden = false;
      els.previewFrame.hidden = true;
    }

    els.canvasBadge.textContent = isGenerating ? "Generating" : state.generatedHtml ? "Live" : "Ready";
    els.canvasBadge.classList.toggle("is-loading", isGenerating);
    els.canvasBadge.classList.toggle("is-live", !isGenerating && Boolean(state.generatedHtml));
  }

  function initCanvasView() {
    els.canvasLoading.hidden = true;
    els.previewFrame.hidden = true;
    els.canvasEmpty.hidden = false;
    setCanvasActionsEnabled(false);
  }

  function setCanvasActionsEnabled(enabled) {
    [els.refreshBtn, els.fullscreenBtn, els.downloadBtn, els.printBtn].forEach((btn) => {
      btn.disabled = !enabled;
    });
  }

  function updateCharCount() {
    const len = els.promptInput.value.length;
    els.charCount.textContent = `${len} / 8000`;
  }

  function selectContentType(type) {
    state.contentType = type;
    els.typeCards.forEach((card) => {
      const selected = card.dataset.type === type;
      card.classList.toggle("is-selected", selected);
      card.setAttribute("aria-checked", selected ? "true" : "false");
    });
  }

  function renderPreview(html) {
    state.generatedHtml = html;
    els.previewFrame.hidden = false;
    els.canvasEmpty.hidden = true;
    els.previewFrame.srcdoc = html;
    setCanvasActionsEnabled(true);
    els.canvasBadge.classList.add("is-live");
    els.canvasBadge.textContent = "Live";
  }

  function clearCanvas() {
    state.generatedHtml = "";
    els.previewFrame.srcdoc = "";
    els.previewFrame.hidden = true;
    els.canvasEmpty.hidden = false;
    els.canvasBadge.textContent = "Ready";
    els.canvasBadge.classList.remove("is-live", "is-loading");
    els.canvasTypeLabel.textContent = "No creation yet";
    closeDownloadMenu();
    setCanvasActionsEnabled(false);
  }

  async function checkHealth() {
    try {
      const res = await fetch(withRoot("/api/health"));
      const data = await res.json();
      if (data.api_key_configured) {
        els.apiStatus.classList.add("is-ready");
        els.apiStatus.innerHTML = '<span class="status-dot"></span> Gemini ready';
      } else {
        els.apiStatus.classList.add("is-error");
        els.apiStatus.innerHTML = '<span class="status-dot"></span> API key missing';
        showToast("Set GEMINI_API_KEY in .env to enable generation.", "error");
      }
    } catch {
      els.apiStatus.classList.add("is-error");
      els.apiStatus.innerHTML = '<span class="status-dot"></span> Offline';
    }
  }

  async function generate() {
    const prompt = els.promptInput.value.trim();
    if (prompt.length < 3) {
      showToast("Please enter a description (at least 3 characters).", "error");
      els.promptInput.focus();
      return;
    }

    state.lastPrompt = prompt;
    setGenerating(true);

    if (window.matchMedia("(max-width: 960px)").matches) {
      els.creationPanel.classList.add("is-collapsed");
      els.panelToggle.setAttribute("aria-expanded", "false");
    }

    try {
      const res = await fetch(withRoot("/api/generate"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt,
          content_type: state.contentType,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        const detail = typeof data.detail === "string" ? data.detail : "Generation failed.";
        if (/api key/i.test(detail)) {
          throw new Error(
            "Gemini API key is invalid. Add a valid key from Google AI Studio to .env as GEMINI_API_KEY.",
          );
        }
        throw new Error(detail);
      }

      renderPreview(data.html);
      els.canvasTypeLabel.textContent = data.content_type_label;
      showToast("Your creation is ready on the canvas.", "success");
    } catch (err) {
      showToast(err.message || "Something went wrong.", "error");
    } finally {
      setGenerating(false);
    }
  }

  function exportBaseName() {
    return `genai-creation-${state.contentType}-${Date.now()}`;
  }

  function closeDownloadMenu() {
    els.downloadMenu.hidden = true;
    els.downloadBtn.classList.remove("is-open");
    els.downloadBtn.setAttribute("aria-expanded", "false");
  }

  function toggleDownloadMenu() {
    if (els.downloadBtn.disabled) return;
    const willOpen = els.downloadMenu.hidden;
    if (willOpen) {
      els.downloadMenu.hidden = false;
      els.downloadBtn.classList.add("is-open");
      els.downloadBtn.setAttribute("aria-expanded", "true");
    } else {
      closeDownloadMenu();
    }
  }

  function downloadHtml() {
    if (!state.generatedHtml) return;
    closeDownloadMenu();
    const blob = new Blob([state.generatedHtml], { type: "text/html;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${exportBaseName()}.html`;
    a.click();
    URL.revokeObjectURL(url);
    showToast("HTML file downloaded.", "success");
  }

  async function downloadPdf() {
    if (!state.generatedHtml) return;
    closeDownloadMenu();

    if (typeof html2pdf === "undefined") {
      showToast("PDF library failed to load. Try Print → Save as PDF.", "error");
      return;
    }

    const frameDoc = els.previewFrame.contentDocument;
    if (!frameDoc?.documentElement) {
      showToast("Preview not ready for PDF export.", "error");
      return;
    }

    const isDiagram = state.contentType === "use_case_diagram";
    const previousLabel = els.downloadBtn.querySelector(".btn-text")?.textContent;
    els.downloadBtn.disabled = true;
    if (els.downloadBtn.querySelector(".btn-text")) {
      els.downloadBtn.querySelector(".btn-text").textContent = "Exporting…";
    }

    try {
      await html2pdf()
        .set({
          margin: [0.4, 0.4, 0.4, 0.4],
          filename: `${exportBaseName()}.pdf`,
          image: { type: "jpeg", quality: 0.95 },
          html2canvas: {
            scale: 2,
            useCORS: true,
            logging: false,
            windowWidth: frameDoc.documentElement.scrollWidth,
            windowHeight: frameDoc.documentElement.scrollHeight,
          },
          jsPDF: {
            unit: "in",
            format: "a4",
            orientation: isDiagram ? "landscape" : "portrait",
          },
          pagebreak: { mode: ["css", "legacy"] },
        })
        .from(frameDoc.documentElement)
        .save();
      showToast("PDF downloaded.", "success");
    } catch {
      showToast("PDF export failed. Try Print → Save as PDF.", "error");
    } finally {
      els.downloadBtn.disabled = false;
      if (els.downloadBtn.querySelector(".btn-text") && previousLabel) {
        els.downloadBtn.querySelector(".btn-text").textContent = previousLabel;
      }
    }
  }

  function handleDownloadFormat(format) {
    if (format === "html") downloadHtml();
    else if (format === "pdf") downloadPdf();
  }

  function printPreview() {
    if (!state.generatedHtml) return;
    const printWindow = window.open("", "_blank");
    if (!printWindow) {
      showToast("Allow pop-ups to print or save as PDF.", "error");
      return;
    }
    printWindow.document.write(state.generatedHtml);
    printWindow.document.close();
    printWindow.focus();
    printWindow.onload = () => printWindow.print();
  }

  function toggleFullscreen() {
    const target = els.canvasWrap;
    if (!document.fullscreenElement) {
      target.requestFullscreen?.().catch(() => showToast("Fullscreen is not supported here.", "error"));
    } else {
      document.exitFullscreen?.();
    }
  }

  async function loadSample() {
    try {
      const res = await fetch(withRoot("/static/samples/use_case_example.html"));
      const html = await res.text();
      renderPreview(html);
      els.canvasTypeLabel.textContent = "Use Case Diagram (Example)";
      showToast("Sample loaded on canvas. Connect a valid Gemini key to generate custom output.", "success");
    } catch {
      showToast("Could not load the sample preview.", "error");
    }
  }

  els.typeCards.forEach((card) => {
    card.addEventListener("click", () => selectContentType(card.dataset.type));
  });

  els.promptInput.addEventListener("input", updateCharCount);
  els.generateBtn.addEventListener("click", generate);
  els.sampleBtn.addEventListener("click", loadSample);
  els.clearBtn.addEventListener("click", clearCanvas);
  els.refreshBtn.addEventListener("click", () => {
    if (state.lastPrompt) {
      els.promptInput.value = state.lastPrompt;
      generate();
    }
  });
  els.downloadBtn.addEventListener("click", (event) => {
    event.stopPropagation();
    toggleDownloadMenu();
  });
  els.downloadMenuItems.forEach((item) => {
    item.addEventListener("click", () => handleDownloadFormat(item.dataset.format));
  });
  document.addEventListener("click", (event) => {
    if (!els.downloadDropdown.contains(event.target)) {
      closeDownloadMenu();
    }
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeDownloadMenu();
  });
  els.printBtn.addEventListener("click", printPreview);
  els.fullscreenBtn.addEventListener("click", toggleFullscreen);

  els.panelToggle.addEventListener("click", () => {
    const collapsed = els.creationPanel.classList.toggle("is-collapsed");
    els.panelToggle.setAttribute("aria-expanded", collapsed ? "false" : "true");
  });

  updateCharCount();
  initCanvasView();
  checkHealth();
})();
