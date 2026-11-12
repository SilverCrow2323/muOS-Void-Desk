(() => {
  "use strict";
  const menuButton = document.querySelector("[data-menu-toggle]");
  const nav = document.getElementById("primary-nav");
  if (menuButton && nav) {
    menuButton.addEventListener("click", () => {
      const open = menuButton.getAttribute("aria-expanded") !== "true";
      menuButton.setAttribute("aria-expanded", String(open));
      nav.classList.toggle("open", open);
    });
    nav.addEventListener("click", event => {
      if (event.target.closest("a")) {
        nav.classList.remove("open");
        menuButton.setAttribute("aria-expanded", "false");
      }
    });
  }

  const search = document.getElementById("library-search");
  const library = document.getElementById("library-grid");
  const count = document.getElementById("library-count");
  const noResults = document.getElementById("no-results");
  if (search && library) {
    const items = Array.from(library.querySelectorAll("[data-search-item]"));
    const update = () => {
      const query = search.value.trim().toLocaleLowerCase();
      let visible = 0;
      items.forEach(item => {
        const haystack = (item.textContent + " " + (item.dataset.search || "")).toLocaleLowerCase();
        const match = !query || haystack.includes(query);
        item.hidden = !match;
        if (match) visible += 1;
      });
      if (count) count.textContent = String(visible).padStart(2, "0") + " GUIDES";
      if (noResults) noResults.hidden = visible !== 0;
    };
    search.addEventListener("input", update);
    document.addEventListener("keydown", event => {
      if (event.key === "/" && !["INPUT", "TEXTAREA"].includes(document.activeElement.tagName)) {
        event.preventDefault();
        search.focus();
      }
      if (event.key === "Escape" && document.activeElement === search) {
        search.value = "";
        update();
        search.blur();
      }
    });
    update();
  }
  document.querySelectorAll("[data-year]").forEach(node => { node.textContent = new Date().getFullYear(); });

  // Interactive asset atlas: category filters, search, lightbox and source-path copy.
  const atlasRoot = document.querySelector("[data-asset-atlas]");
  if (atlasRoot) {
    const cards = Array.from(atlasRoot.querySelectorAll("[data-asset-card]"));
    const filters = Array.from(atlasRoot.querySelectorAll("[data-asset-filter]"));
    const searchInput = document.getElementById("asset-search");
    const counter = document.getElementById("asset-count");
    const emptyState = document.getElementById("asset-no-results");
    const feedback = atlasRoot.querySelector("[data-asset-feedback]");
    let activeGroup = "all";
    const refreshAtlas = () => {
      const query = (searchInput?.value || "").trim().toLocaleLowerCase();
      let visible = 0;
      cards.forEach(card => {
        const matchesGroup = activeGroup === "all" || card.dataset.group === activeGroup;
        const haystack = (card.textContent + " " + (card.dataset.search || "")).toLocaleLowerCase();
        const matchesQuery = !query || haystack.includes(query);
        const show = matchesGroup && matchesQuery;
        card.hidden = !show;
        if (show) visible += 1;
      });
      if (counter) counter.textContent = String(visible).padStart(2, "0") + " / " + String(cards.length).padStart(2, "0") + " ASSETS";
      if (emptyState) emptyState.hidden = visible !== 0;
    };
    filters.forEach(button => button.addEventListener("click", () => {
      activeGroup = button.dataset.assetFilter || "all";
      filters.forEach(item => item.setAttribute("aria-pressed", String(item === button)));
      refreshAtlas();
    }));
    searchInput?.addEventListener("input", refreshAtlas);
    document.addEventListener("keydown", event => {
      if (event.key === "/" && searchInput && !["INPUT", "TEXTAREA"].includes(document.activeElement.tagName)) {
        event.preventDefault();
        searchInput.focus();
      }
      if (event.key === "Escape" && document.activeElement === searchInput) {
        searchInput.value = "";
        refreshAtlas();
        searchInput.blur();
      }
    });
    refreshAtlas();

    const dialog = document.getElementById("asset-dialog");
    const dialogImage = document.getElementById("asset-dialog-image");
    const dialogTitle = document.getElementById("asset-dialog-title");
    document.querySelectorAll("[data-preview]").forEach(trigger => trigger.addEventListener("click", () => {
      if (!dialog || !dialogImage || typeof dialog.showModal !== "function") return;
      dialogImage.src = trigger.dataset.preview || "";
      dialogImage.alt = trigger.querySelector("img")?.alt || trigger.dataset.title || "Asset preview";
      if (dialogTitle) dialogTitle.textContent = trigger.dataset.title || "Asset preview";
      dialog.showModal();
    }));

    const fallbackCopy = value => {
      const helper = document.createElement("textarea");
      helper.value = value;
      helper.setAttribute("readonly", "");
      helper.style.position = "fixed";
      helper.style.opacity = "0";
      document.body.appendChild(helper);
      helper.select();
      let copied = false;
      try { copied = document.execCommand("copy"); } catch (_) { copied = false; }
      helper.remove();
      return copied;
    };
    document.querySelectorAll("[data-copy-asset]").forEach(button => button.addEventListener("click", async () => {
      const value = button.dataset.copyAsset || "";
      let copied = false;
      try {
        if (navigator.clipboard?.writeText) {
          await navigator.clipboard.writeText(value);
          copied = true;
        } else {
          copied = fallbackCopy(value);
        }
      } catch (_) {
        copied = fallbackCopy(value);
      }
      if (feedback) feedback.textContent = copied ? "COPIED TO CLIPBOARD — " + value : "COPY UNAVAILABLE — " + value;
      button.textContent = copied ? "Copied ✓" : "Select path";
    }));
  }


  // Global Ctrl/Cmd+K command palette, available on every portal page.
  const commandDialog = document.getElementById("command-dialog");
  const commandInput = document.getElementById("command-search-input");
  const commandResults = document.getElementById("command-results");
  const commandItems = [
    {title:"Overview",group:"HOME",href:"index.html",detail:"Project status, portals and reading paths"},
    {title:"System architecture",group:"ENGINEERING",href:"architecture.html",detail:"Host firmware, application, services and contracts"},
    {title:"Field manual",group:"OPERATIONS",href:"field-manual.html",detail:"Installation, firmware notes and practical guidance"},
    {title:"Install on muOS",group:"OPERATIONS",href:"field-manual.html#installation",detail:"Published package and handheld installation steps"},
    {title:"Firmware compatibility",group:"DEVICE",href:"field-manual.html#compatibility",detail:"Andromeda target, legacy families and safe fallback"},
    {title:"Asset atlas",group:"VISUALS",href:"asset-atlas.html",detail:"Ten navigation icons and the real THE FORGE screen"},
    {title:"NEXUS v12 blueprint",group:"ROADMAP",href:"blueprint.html",detail:"Proposed destinations, Workshop satellites and gates"},
    {title:"GitHub Releases",group:"DOWNLOADS",href:"https://github.com/SilverCrow2323/Void-Desk-Project/releases",detail:"Published application packages"},
    {title:"Repository source",group:"DEVELOPMENT",href:"https://github.com/SilverCrow2323/Void-Desk-Project",detail:"Code, issues, pull requests and project history"}
  ];
  const renderCommands = () => {
    if (!commandResults) return;
    const query = (commandInput?.value || "").trim().toLocaleLowerCase();
    const matches = commandItems.filter(item => (item.title+" "+item.group+" "+item.detail).toLocaleLowerCase().includes(query));
    commandResults.replaceChildren();
    if (!matches.length) {
      const empty = document.createElement("p");
      empty.className = "command-empty";
      empty.textContent = "No matching destination. Try another term.";
      commandResults.append(empty);
      return;
    }
    matches.forEach(item => {
      const link = document.createElement("a");
      link.className = "command-result";
      link.href = item.href;
      const copy = document.createElement("span");
      const title = document.createElement("strong");
      title.textContent = item.title;
      const detail = document.createElement("small");
      detail.textContent = item.detail;
      copy.append(title,detail);
      const group = document.createElement("em");
      group.textContent = item.group;
      link.append(copy,group);
      if (item.href.startsWith("https://")) {
        link.target = "_blank";
        link.rel = "noreferrer";
      }
      commandResults.append(link);
    });
  };
  const openCommandPalette = () => {
    if (!commandDialog || typeof commandDialog.showModal !== "function") return;
    if (!commandDialog.open) commandDialog.showModal();
    if (commandInput) {
      commandInput.value = "";
      renderCommands();
      commandInput.focus();
    }
  };
  document.querySelectorAll("[data-command-open]").forEach(button => button.addEventListener("click", openCommandPalette));
  commandInput?.addEventListener("input", renderCommands);
  commandInput?.addEventListener("keydown", event => {
    const links = Array.from(commandResults?.querySelectorAll("a") || []);
    const current = links.indexOf(document.activeElement);
    if (event.key === "ArrowDown" && links.length) {
      event.preventDefault();
      links[Math.min(current + 1, links.length - 1)].focus();
    } else if (event.key === "ArrowUp" && links.length) {
      event.preventDefault();
      if (current <= 0) commandInput.focus();
      else links[current - 1].focus();
    }
  });
  commandResults?.addEventListener("keydown", event => {
    const links = Array.from(commandResults.querySelectorAll("a"));
    const current = links.indexOf(document.activeElement);
    if (event.key === "ArrowDown" && links.length) {
      event.preventDefault();
      links[Math.min(current + 1, links.length - 1)].focus();
    } else if (event.key === "ArrowUp" && links.length) {
      event.preventDefault();
      if (current <= 0) commandInput?.focus();
      else links[current - 1].focus();
    }
  });
  commandDialog?.addEventListener("click", event => {
    if (event.target === commandDialog) commandDialog.close();
  });
  document.addEventListener("keydown", event => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLocaleLowerCase() === "k") {
      event.preventDefault();
      openCommandPalette();
    }
  });

})();