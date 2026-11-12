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
    {title:"QWASAR Studio",group:"LAB",href:"studio.html",detail:"Layout Designer, Module Forge, Release Composer and Library"},
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


  // QWASAR Studio local prototype interactions.
  const studioRoot = document.querySelector("[data-studio]");
  if (studioRoot) {
    const tabs = Array.from(studioRoot.querySelectorAll("[data-studio-tab]"));
    const panels = Array.from(studioRoot.querySelectorAll("[data-studio-panel]"));
    const contextLabel = document.getElementById("studio-context-label");
    const tabContexts = {layout:"LAYOUT / NEXUS HOME",modules:"MODULE FORGE / MANIFEST",release:"RELEASE COMPOSER / PLAN",library:"COMMUNITY LIBRARY / SAMPLE"};
    const activateTab = name => {
      tabs.forEach(tab => {
        const active = tab.dataset.studioTab === name;
        tab.classList.toggle("is-active", active);
        tab.setAttribute("aria-selected", String(active));
        tab.tabIndex = active ? 0 : -1;
      });
      panels.forEach(panel => {
        const active = panel.dataset.studioPanel === name;
        panel.hidden = !active;
        panel.classList.toggle("is-active", active);
      });
      if (contextLabel) contextLabel.textContent = tabContexts[name] || "LOCAL WORKSPACE";
    };
    tabs.forEach((tab,index) => {
      tab.addEventListener("click", () => activateTab(tab.dataset.studioTab));
      tab.addEventListener("keydown", event => {
        if (!["ArrowLeft","ArrowRight"].includes(event.key)) return;
        event.preventDefault();
        const next = (index + (event.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length;
        tabs[next].focus();
        activateTab(tabs[next].dataset.studioTab);
      });
    });

    const canvas = document.getElementById("layout-canvas");
    const feedback = studioRoot.querySelector("[data-studio-feedback]");
    const inspector = {
      name: document.getElementById("inspector-name"),
      id: document.getElementById("inspector-id"),
      type: document.getElementById("inspector-type"),
      route: document.getElementById("inspector-route")
    };
    let selectedNode = "start-session";
    const typeLabels = {tile:"Menu tile",section:"Section",widget:"Status widget",region:"Region"};
    const nodeSpecs = {
      section:{label:"New section",symbol:"▤",route:"",hint:"User-defined group"},
      tile:{label:"New menu tile",symbol:"▦",route:"",hint:"Registered destination only"},
      widget:{label:"Status widget",symbol:"◫",route:"",hint:"Read-only information"},
      region:{label:"New region",symbol:"◇",route:"",hint:"Layout placement slot"}
    };
    const selectNode = node => {
      if (!node || !inspector.name) return;
      canvas?.querySelectorAll("[data-layout-node]").forEach(item => item.classList.toggle("is-selected",item === node));
      selectedNode = node.dataset.nodeId;
      inspector.name.textContent = (node.dataset.nodeLabel || "UNTITLED").toLocaleUpperCase();
      inspector.id.textContent = node.dataset.nodeId || "local-node";
      inspector.type.textContent = typeLabels[node.dataset.nodeType] || "Component";
      inspector.route.textContent = node.dataset.nodeRoute || "none / no action";
    };
    const updateCanvasCount = () => {
      const count = canvas?.querySelectorAll("[data-layout-node]").length || 0;
      const label = document.getElementById("layout-count");
      if (label) label.textContent = String(count).padStart(2,"0")+" NODES IN CANVAS";
      const sectionCount = canvas?.querySelectorAll("[data-layout-node]").length || 0;
      const hint = canvas?.querySelector(".canvas-section-label small");
      if (hint) hint.textContent = "ORDERED / "+String(sectionCount).padStart(2,"0")+" ITEMS";
    };
    const createNode = type => {
      const spec = nodeSpecs[type];
      if (!spec || !canvas) return;
      const id = type+"-"+Date.now().toString(36)+"-"+Math.floor(Math.random()*1000).toString(36);
      const article = document.createElement("article");
      article.className = "layout-node";
      article.tabIndex = 0;
      article.dataset.layoutNode = "";
      article.dataset.nodeId = id;
      article.dataset.nodeLabel = spec.label;
      article.dataset.nodeType = type;
      article.dataset.nodeRoute = spec.route;
      const grip = document.createElement("span"); grip.className="node-grip"; grip.textContent="⠿";
      const symbol = document.createElement("span"); symbol.className="node-symbol"; symbol.textContent=spec.symbol;
      const copy = document.createElement("span"); copy.className="node-copy";
      const title = document.createElement("b"); title.textContent=spec.label.toLocaleUpperCase();
      const subtitle = document.createElement("small"); subtitle.textContent=spec.hint;
      copy.append(title,subtitle);
      const tag=document.createElement("span");tag.className="node-tag";tag.textContent=type.toLocaleUpperCase();
      const controls=document.createElement("span");controls.className="node-controls";
      const up=document.createElement("button");up.type="button";up.dataset.nodeMove="-1";up.setAttribute("aria-label","Move "+spec.label+" up");up.textContent="↑";
      const down=document.createElement("button");down.type="button";down.dataset.nodeMove="1";down.setAttribute("aria-label","Move "+spec.label+" down");down.textContent="↓";
      controls.append(up,down);article.append(grip,symbol,copy,tag,controls);
      canvas.append(article);
      selectNode(article);updateCanvasCount();
      if(feedback)feedback.textContent="Added "+typeLabels[type]+". It is a local layout item with no executable action.";
    };
    canvas?.addEventListener("click",event=>{
      const moveButton=event.target.closest("[data-node-move]");
      if(moveButton){
        const node=moveButton.closest("[data-layout-node]");
        const direction=Number(moveButton.dataset.nodeMove);
        if(node && direction<0 && node.previousElementSibling?.matches("[data-layout-node]")) canvas.insertBefore(node,node.previousElementSibling);
        else if(node && direction>0 && node.nextElementSibling?.matches("[data-layout-node]")) canvas.insertBefore(node.nextElementSibling,node);
        if(node)selectNode(node);
        updateCanvasCount();
        return;
      }
      const node=event.target.closest("[data-layout-node]");
      if(node)selectNode(node);
    });
    canvas?.addEventListener("keydown",event=>{
      if(event.key==="Enter"||event.key===" "){
        const node=event.target.closest("[data-layout-node]");
        if(node){event.preventDefault();selectNode(node);}
      }
    });
    studioRoot.querySelectorAll("[data-add-layout]").forEach(button=>button.addEventListener("click",()=>createNode(button.dataset.addLayout)));
    studioRoot.querySelector("[data-reset-layout]")?.addEventListener("click",()=>{
      if(!canvas)return;
      const original=[
        {id:"start-session",label:"Start Session",type:"tile",route:"session.launch.xfce",symbol:"▶",hint:"session.launch / registered route"},
        {id:"the-forge",label:"THE FORGE",type:"tile",route:"route.forge.apt",symbol:"⌘",hint:"forge.home / registered route"},
        {id:"media-vault",label:"MEDIA VAULT",type:"tile",route:"route.media.library",symbol:"▣",hint:"media.home / registered route"}
      ];
      canvas.querySelectorAll("[data-layout-node]").forEach(n=>n.remove());
      original.forEach(spec=>{
        const node=document.createElement("article");node.className="layout-node";node.tabIndex=0;node.dataset.layoutNode="";node.dataset.nodeId=spec.id;node.dataset.nodeLabel=spec.label;node.dataset.nodeType=spec.type;node.dataset.nodeRoute=spec.route;
        node.innerHTML='<span class="node-grip">⠿</span><span class="node-symbol"></span><span class="node-copy"><b></b><small></small></span><span class="node-tag">TILE</span><span class="node-controls"><button type="button" data-node-move="-1" aria-label="Move item up">↑</button><button type="button" data-node-move="1" aria-label="Move item down">↓</button></span>';
        node.querySelector(".node-symbol").textContent=spec.symbol;node.querySelector(".node-copy b").textContent=spec.label.toLocaleUpperCase();node.querySelector(".node-copy small").textContent=spec.hint;canvas.append(node);
      });
      selectNode(canvas.querySelector("[data-layout-node]"));updateCanvasCount();
      if(feedback)feedback.textContent="Sample layout restored.";
    });
    studioRoot.querySelector("[data-export-profile]")?.addEventListener("click",()=>{
      const nodes=Array.from(canvas?.querySelectorAll("[data-layout-node]")||[]).map(node=>{
        const entry={id:node.dataset.nodeId,label:node.dataset.nodeLabel,component:node.dataset.nodeType};
        if(node.dataset.nodeRoute)entry.route=node.dataset.nodeRoute;
        return entry;
      });
      const profile={
        schema:"qwasar.profile/v1",id:"voiddesk-studio-local-demo",name:"Studio local composition",
        compatibility:{minimumVoidDeskVersion:"10.2.0"},
        enginePreference:"pygame",
        composition:{workspace:"nexus-home",nodes},
        metadata:{origin:"QWASAR Studio browser concept",executableContent:false}
      };
      const blob=new Blob([JSON.stringify(profile,null,2)+"\n"],{type:"application/json"});
      const url=URL.createObjectURL(blob);const link=document.createElement("a");link.href=url;link.download="voiddesk-studio-sample.qprofile";document.body.append(link);link.click();link.remove();URL.revokeObjectURL(url);
      if(feedback)feedback.textContent="Exported a declarative .qprofile sample. No scripts, shell commands or executable modules were included.";
    });
    updateCanvasCount();
    selectNode(canvas?.querySelector("[data-layout-node]"));

    const manifestSamples={
      widget:{label:"WIDGET TEMPLATE / DRAFT",json:{schema:"qwasar.module/v1",id:"sample.status-widget",kind:"widget",version:"0.1.0",entry:{slot:"home.right",component:"StatusCard"},capabilities:[],permissions:[],trust:"local-draft"}},
      menu:{label:"MENU TILE / DRAFT",json:{schema:"qwasar.module/v1",id:"sample.menu-tile",kind:"menu_tile",version:"0.1.0",entry:{slot:"nexus.destinations",component:"MenuEntry",route:"registered.route.id"},capabilities:[],permissions:[],trust:"local-draft"}},
      panel:{label:"HUB PANEL / DRAFT",json:{schema:"qwasar.module/v1",id:"sample.hub-panel",kind:"hub_panel",version:"0.1.0",entry:{slot:"workspace.main",component:"Panel"},capabilities:[],permissions:[],trust:"local-draft"}},
      theme:{label:"THEME PACK / DRAFT",json:{schema:"qwasar.module/v1",id:"sample.theme-pack",kind:"theme",version:"0.1.0",tokens:{accent:"#F0525F",focus:"#55D5DF"},capabilities:[],permissions:[],trust:"local-draft"}}
    };
    const manifestCode=document.getElementById("manifest-code");
    const manifestLabel=document.getElementById("manifest-template-label");
    studioRoot.querySelectorAll("[data-module-template]").forEach(button=>button.addEventListener("click",()=>{
      const sample=manifestSamples[button.dataset.moduleTemplate];
      if(!sample||!manifestCode)return;
      studioRoot.querySelectorAll("[data-module-template]").forEach(item=>item.classList.toggle("is-selected",item===button));
      manifestCode.textContent=JSON.stringify(sample.json,null,2);
      if(manifestLabel)manifestLabel.textContent=sample.label;
    }));
    studioRoot.querySelector("[data-copy-manifest]")?.addEventListener("click",async()=>{
      const value=manifestCode?.textContent||"";
      let copied=false;
      try{if(navigator.clipboard?.writeText){await navigator.clipboard.writeText(value);copied=true;}}catch(_){copied=false;}
      if(!copied){const helper=document.createElement("textarea");helper.value=value;document.body.append(helper);helper.select();try{copied=document.execCommand("copy");}catch(_){copied=false;}helper.remove();}
      const button=studioRoot.querySelector("[data-copy-manifest]");
      if(button)button.textContent=copied?"Copied ✓":"Copy unavailable";
    });

    const flavour=document.getElementById("release-flavour");
    const engine=document.getElementById("release-engine");
    const flavourLabel=document.getElementById("release-summary-flavour");
    const engineLabel=document.getElementById("release-summary-engine");
    const description=document.getElementById("release-summary-description");
    const flavourDescriptions={
      Full:"A complete first-party package plan, subject to the real build pipeline and module compatibility checks.",
      Essential:"A core-first package plan prioritising the required handheld experience and supported essentials.",
      Slim:"A minimal package plan that still requires dependency closure and runtime validation.",
      Custom:"A user-defined allowlist. Every selected contribution must pass compatibility and dependency checks."
    };
    const updateRelease=()=>{
      if(flavourLabel)flavourLabel.textContent=(flavour?.value||"Full").toLocaleUpperCase();
      if(engineLabel)engineLabel.textContent=engine?.value==="love"?"LÖVE · experimental frontend":"Pygame · reference frontend";
      if(description)description.textContent=flavourDescriptions[flavour?.value||"Full"];
    };
    flavour?.addEventListener("change",updateRelease);engine?.addEventListener("change",updateRelease);updateRelease();
    studioRoot.querySelector("[data-export-release]")?.addEventListener("click",()=>{
      const manifest={schema:"qwasar.release-manifest/v1",flavour:flavour?.value||"Full",target:{frontend:engine?.value||"pygame"},include:["voiddesk-core","nexus-shell"],exclude:["community-executable-modules"],signing:{status:"not-issued"},build:{status:"not-started",requiresMaintainerPipeline:true},metadata:{generatedBy:"QWASAR Studio local concept",isBuildArtifact:false}};
      const blob=new Blob([JSON.stringify(manifest,null,2)+"\n"],{type:"application/json"});const url=URL.createObjectURL(blob);const link=document.createElement("a");link.href=url;link.download="qwasar-release-plan.json";document.body.append(link);link.click();link.remove();URL.revokeObjectURL(url);
      if(description)description.textContent="Manifest exported. No package was built and no signature was issued.";
    });
  }

  // Theme Lab preview changes only the local Studio design sample.
  const themeLab=document.querySelector("[data-theme-lab]");
  if(themeLab){
    const preview=document.getElementById("theme-preview");
    const accentValue=document.getElementById("theme-accent-value");
    const focusValue=document.getElementById("theme-focus-value");
    const presets={
      megastructure:{accent:"#F0525F",focus:"#55D5DF"},
      polar:{accent:"#8AAEE8",focus:"#C7E9E8"},
      ember:{accent:"#DA824D",focus:"#EFD1A5"}
    };
    themeLab.querySelectorAll("[data-theme-preset]").forEach(button=>button.addEventListener("click",()=>{
      const name=button.dataset.themePreset;const palette=presets[name];if(!palette||!preview)return;
      preview.dataset.theme=name;
      themeLab.querySelectorAll("[data-theme-preset]").forEach(item=>{const active=item===button;item.classList.toggle("is-active",active);item.setAttribute("aria-pressed",String(active));});
      if(accentValue)accentValue.textContent=palette.accent;
      if(focusValue)focusValue.textContent=palette.focus;
    }));
  }


  // Scroll progress and reveal-on-scroll. Reduced-motion users see all content immediately.
  const reducedMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches;
  const progress = document.createElement("div");
  progress.className = "scroll-progress";
  progress.setAttribute("aria-hidden","true");
  progress.innerHTML = "<span></span>";
  document.body.append(progress);
  const progressBar = progress.firstElementChild;
  let scrollTicking = false;
  const updateProgress = () => {
    const total = document.documentElement.scrollHeight - window.innerHeight;
    const amount = total > 0 ? Math.min(1,Math.max(0,window.scrollY / total)) : 0;
    if(progressBar)progressBar.style.transform = "scaleX("+amount+")";
    scrollTicking = false;
  };
  window.addEventListener("scroll",() => {
    if(!scrollTicking){scrollTicking=true;window.requestAnimationFrame(updateProgress);}
  },{passive:true});
  updateProgress();

  if(!reducedMotion && "IntersectionObserver" in window){
    const revealTargets = document.querySelectorAll(
      "main > section:not(.studio-panel), .status-card, .portal-card, .layer-card, .engine-card, .destination-grid > article, .gate-list > div, .satellite-panels > article, .icon-library figure, [data-asset-card], .studio-principles > article"
    );
    const revealObserver = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if(entry.isIntersecting){
          entry.target.classList.add("is-visible");
          revealObserver.unobserve(entry.target);
        }
      });
    },{threshold:0.12,rootMargin:"0px 0px -36px 0px"});
    revealTargets.forEach((element,index) => {
      if(element.closest("[hidden]"))return;
      element.setAttribute("data-reveal","");
      const delay=index%4;
      if(delay)element.setAttribute("data-reveal-delay",String(delay));
      revealObserver.observe(element);
    });
  }

})();