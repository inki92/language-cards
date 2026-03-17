(() => {
  const cardEl = document.getElementById("card");
  const cardFrontEl = document.getElementById("cardFront");
  const cardBackEl = document.getElementById("cardBack");
  const prevBtn = document.getElementById("prevBtn");
  const nextBtn = document.getElementById("nextBtn");
  const uploadBtn = document.getElementById("uploadBtn");
  const uploadDialog = document.getElementById("uploadDialog");
  const importUser = document.getElementById("importUser");
  const importPass = document.getElementById("importPass");
  const importText = document.getElementById("importText");
  const importBtn = document.getElementById("importBtn");
  const importResult = document.getElementById("importResult");

  let flipped = false;
  let currentCard = null;

  function setCard(pl, translation) {
    cardFrontEl.textContent = pl ?? "";
    cardBackEl.textContent = translation ?? "";
    setFlipped(false);
  }

  function setFlipped(v) {
    flipped = !!v;
    cardEl.classList.toggle("is-flipped", flipped);
  }

  function toggleFlip() {
    setFlipped(!flipped);
  }

  function shouldIgnoreKeyEvents(e) {
    const el = document.activeElement;
    if (!el) return false;
    const tag = el.tagName?.toLowerCase();
    if (tag === "textarea") return true;
    if (tag === "input") return true;
    if (tag === "select") return true;
    if (el.isContentEditable) return true;
    if (uploadDialog?.open) return true;
    return false;
  }

  cardEl.addEventListener("click", toggleFlip);

  function toBasicAuthHeader(user, pass) {
    const u = user ?? "";
    const p = pass ?? "";
    if (!u && !p) return null;
    return `Basic ${btoa(`${u}:${p}`)}`;
  }

  function loadSavedAuth() {
    try {
      const raw = localStorage.getItem("cards_import_auth");
      if (!raw) return { user: "", pass: "" };
      const obj = JSON.parse(raw);
      return {
        user: typeof obj?.user === "string" ? obj.user : "",
        pass: typeof obj?.pass === "string" ? obj.pass : "",
      };
    } catch {
      return { user: "", pass: "" };
    }
  }

  function saveAuth(user, pass) {
    try {
      localStorage.setItem("cards_import_auth", JSON.stringify({ user, pass }));
    } catch {
      // ignore
    }
  }

  async function apiPostJson(url, body, extraHeaders) {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...(extraHeaders ?? {}) },
      body: body ? JSON.stringify(body) : "{}",
    });
    const data = await res.json().catch(() => null);
    if (!res.ok) {
      const msg = data?.error ? String(data.error) : `${res.status}`;
      throw new Error(msg);
    }
    return data;
  }

  async function loadNext() {
    try {
      const data = await apiPostJson("/api/next");
      currentCard = data;
      setCard(data.pl, data.translation);
    } catch (e) {
      setCard("No cards yet", "Click Upload → Import to add word pairs");
    }
  }

  async function loadPrev() {
    try {
      const data = await apiPostJson("/api/prev");
      currentCard = data;
      setCard(data.pl, data.translation);
    } catch (e) {
      // If no history, keep current card
    }
  }

  uploadBtn.addEventListener("click", () => {
    importResult.textContent = "";
    const saved = loadSavedAuth();
    importUser.value = saved.user;
    importPass.value = saved.pass;
    uploadDialog.showModal();
    (importUser.value ? importPass : importUser).focus();
  });

  document.addEventListener("keydown", (e) => {
    if (shouldIgnoreKeyEvents(e)) return;

    if (e.code === "Space") {
      e.preventDefault();
      toggleFlip();
      return;
    }

    if (e.code === "ArrowRight") {
      e.preventDefault();
      loadNext();
      return;
    }

    if (e.code === "ArrowLeft") {
      e.preventDefault();
      loadPrev();
      return;
    }
  });

  prevBtn.addEventListener("click", () => {
    loadPrev();
  });
  nextBtn.addEventListener("click", () => {
    loadNext();
  });

  importBtn.addEventListener("click", async () => {
    const text = importText.value.trim();
    if (!text) {
      importResult.textContent = "Empty.";
      return;
    }

    importResult.textContent = "Importing...";
    try {
      const user = importUser.value.trim();
      const pass = importPass.value;
      const auth = toBasicAuthHeader(user, pass);
      const data = await apiPostJson(
        "/api/import",
        { text },
        auth ? { Authorization: auth } : null
      );
      const created = Number(data?.created ?? 0);
      const skipped = Number(data?.skipped ?? 0);
      const errCount = Array.isArray(data?.errors) ? data.errors.length : 0;
      importResult.textContent = `Created: ${created}, skipped: ${skipped}, errors: ${errCount}`;
      saveAuth(user, pass);
      if (!currentCard) {
        await loadNext();
      }
    } catch (e) {
      if (String(e?.message) === "unauthorized") {
        importResult.textContent = "Unauthorized. Check username/password.";
      } else {
        importResult.textContent = "Import failed.";
      }
    }
  });

  // Initial load
  loadNext();
})();
