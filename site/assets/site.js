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
})();