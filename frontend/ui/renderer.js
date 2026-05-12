const dashboardPageEl = document.getElementById("dashboardPage");
const playerGenPageEl = document.getElementById("playerGenPage");
const teamPageEl = document.getElementById("teamPage");
const profilePageEl = document.getElementById("profilePage");
const comparePageEl = document.getElementById("comparePage");
const contractPageEl = document.getElementById("contractPage");
const gearPageEl     = document.getElementById("gearPage");

const playerSearchEl = document.getElementById("playerSearch");
const seasonEl = document.getElementById("season");
const runBtn = document.getElementById("runBtn");
const openTeamPageBtn = document.getElementById("openTeamPageBtn");
const teamGenerateBtn = document.getElementById("teamGenerateBtn");
const teamBackBtn = document.getElementById("teamBackBtn");
const teamSeasonEl = document.getElementById("teamSeason");
const teamSelectEl = document.getElementById("teamSelect");
const teamExportJsonBtn = document.getElementById("teamExportJsonBtn");
const teamExportExcelBtn = document.getElementById("teamExportExcelBtn");
const teamImportGameBtn = document.getElementById("teamImportGameBtn");
const teamCompareBtn = document.getElementById("teamCompareBtn");
const teamStatusEl = document.getElementById("teamStatus");
const teamResultsEl = document.getElementById("teamResults");
const teamProgressWrap = document.getElementById("teamProgressWrap");
const teamProgressFill = document.getElementById("teamProgressFill");
const teamProgressText = document.getElementById("teamProgressText");
const statusEl = document.getElementById("status");
const selectedPillEl = document.getElementById("selectedPill");
const clearSelectionBtn = document.getElementById("clearSelectionBtn");
const recentPlayersEl = document.getElementById("recentPlayers");
const recentListEl = document.getElementById("recentList");
const toastContainerEl = document.getElementById("toastContainer");
const searchResultsEl = document.getElementById("searchResults");
const outputEl = document.getElementById("output");
const teamLayerEl = document.getElementById("teamLayer");
const panelFilterEl = document.getElementById("panelFilter");

// Sidebar nav
const navDashboardBtn = document.getElementById("navDashboardBtn");
const openStatsBtn = document.getElementById("openStatsBtn");
const statsPageEl = document.getElementById("statsPage");
const shotChartPageEl    = document.getElementById("shotChartPage");
const progressionPageEl  = document.getElementById("progressionPage");

// Playbook Editor
const playbookPageEl = document.getElementById("playbookPage");
const playbookTeamSelectEl = document.getElementById("playbookTeamSelect");
const playbookListEl = document.getElementById("playbookList");
const playbookStatusEl = document.getElementById("playbookStatus");
const loadPlaybookBtn = document.getElementById("loadPlaybookBtn");
const savePlaybookBtn = document.getElementById("savePlaybookBtn");
const addPlayBtn = document.getElementById("addPlayBtn");
const removePlayBtn = document.getElementById("removePlayBtn");
const openPlaybookBtn = document.getElementById("openPlaybookBtn");
const playbookBackBtn = document.getElementById("playbookBackBtn");

let currentPlaybookTeam = null;
let currentPlaybookPlays = [];
let availablePlays = {};

const profileHeaderEl = document.getElementById("profileHeader");
const playerInfoListEl = document.getElementById("playerInfoList");
const playStyleListEl = document.getElementById("playStyleList");
const scoreRowEl = document.getElementById("scoreRow");
const strengthListEl = document.getElementById("strengthList");
const weaknessListEl = document.getElementById("weaknessList");
const currentLabelEl = document.getElementById("currentLabel");
const previousLabelEl = document.getElementById("previousLabel");
const statsCurrentEl = document.getElementById("statsCurrent");
const statsPreviousEl = document.getElementById("statsPrevious");
const statsCareerEl = document.getElementById("statsCareer");
const panelTitleEl = document.getElementById("panelTitle");
const panelGridEl = document.getElementById("panelGrid");
const tabAttributesEl = document.getElementById("tabAttributes");
const tabTendenciesEl = document.getElementById("tabTendencies");
const tabBadgesEl = document.getElementById("tabBadges");

const compareContentEl = document.getElementById("compareContent");
const compareFullContentEl = document.getElementById("compareFullContent");
const compareBackBtn = document.getElementById("compareBackBtn");
const compareExpandBtn = document.getElementById("compareExpandBtn");
const tabVsSheetEl = document.getElementById("tabVsSheet");

let selectedPlayer = null;
let searchTimer = null;
let currentProfile = null;
let activeTab = "attributes";
let lastSearchToken = 0;
let profileBackTarget = "dashboard";
let lastTeamExportPayload = null;
let searchFocusIndex = -1;
let panelFilterValue = "";
let compareCandidates = [];
let generatedProfiles = [];

const TEAM_THEME = {
  ATL: ["rgba(225, 68, 52, 0.24)", "rgba(253, 185, 39, 0.22)", "#e14434", "#fdb927"],
  BOS: ["rgba(0, 122, 51, 0.24)", "rgba(186, 149, 92, 0.2)", "#007a33", "#ba954c"],
  BKN: ["rgba(245, 245, 245, 0.12)", "rgba(138, 138, 138, 0.2)", "#c8c8c8", "#8a8a8a"],
  CHA: ["rgba(29, 17, 96, 0.24)", "rgba(0, 120, 140, 0.22)", "#1d1160", "#00788c"],
  CHI: ["rgba(206, 17, 65, 0.24)", "rgba(25, 25, 25, 0.2)", "#ce1141", "#191919"],
  CLE: ["rgba(134, 0, 56, 0.24)", "rgba(253, 187, 48, 0.2)", "#860038", "#fdbb30"],
  DAL: ["rgba(0, 83, 188, 0.24)", "rgba(0, 43, 92, 0.22)", "#0053bc", "#002b5c"],
  DEN: ["rgba(13, 34, 64, 0.24)", "rgba(254, 197, 47, 0.2)", "#0d2240", "#fec52f"],
  DET: ["rgba(200, 16, 46, 0.24)", "rgba(29, 66, 138, 0.22)", "#c8102e", "#1d428a"],
  GSW: ["rgba(29, 66, 138, 0.24)", "rgba(255, 199, 44, 0.2)", "#1d428a", "#ffc72c"],
  HOU: ["rgba(206, 17, 65, 0.24)", "rgba(196, 206, 211, 0.2)", "#ce1141", "#c4ced3"],
  IND: ["rgba(0, 45, 98, 0.24)", "rgba(253, 187, 48, 0.2)", "#002d62", "#fdbb30"],
  LAC: ["rgba(200, 16, 46, 0.24)", "rgba(29, 66, 148, 0.2)", "#c8102e", "#1d4294"],
  LAL: ["rgba(85, 37, 130, 0.24)", "rgba(253, 185, 39, 0.24)", "#552582", "#fdb927"],
  MEM: ["rgba(93, 118, 169, 0.24)", "rgba(18, 23, 63, 0.2)", "#5d76a9", "#12173f"],
  MIA: ["rgba(152, 0, 46, 0.24)", "rgba(249, 160, 27, 0.2)", "#98002e", "#f9a01b"],
  MIL: ["rgba(0, 71, 27, 0.24)", "rgba(240, 235, 210, 0.18)", "#00471b", "#eee1c6"],
  MIN: ["rgba(12, 35, 64, 0.24)", "rgba(120, 190, 32, 0.2)", "#0c2340", "#78be20"],
  NOP: ["rgba(0, 22, 65, 0.24)", "rgba(225, 58, 62, 0.2)", "#001641", "#e13a3e"],
  NYK: ["rgba(0, 107, 182, 0.24)", "rgba(245, 132, 38, 0.22)", "#006bb6", "#f58426"],
  OKC: ["rgba(0, 125, 195, 0.24)", "rgba(239, 59, 36, 0.2)", "#007dc3", "#ef3b24"],
  ORL: ["rgba(0, 125, 197, 0.24)", "rgba(196, 206, 211, 0.2)", "#007dc5", "#c4ced3"],
  PHI: ["rgba(0, 107, 182, 0.24)", "rgba(237, 23, 76, 0.2)", "#006bb6", "#ed174c"],
  PHX: ["rgba(29, 17, 96, 0.24)", "rgba(229, 96, 32, 0.22)", "#1d1160", "#e56020"],
  POR: ["rgba(224, 58, 62, 0.24)", "rgba(6, 25, 34, 0.2)", "#e03a3e", "#061922"],
  SAC: ["rgba(91, 43, 130, 0.24)", "rgba(99, 113, 122, 0.2)", "#5b2b82", "#63717a"],
  SAS: ["rgba(196, 206, 211, 0.2)", "rgba(0, 0, 0, 0.24)", "#c4ced3", "#000000"],
  TOR: ["rgba(206, 17, 65, 0.24)", "rgba(6, 25, 34, 0.2)", "#ce1141", "#061922"],
  UTA: ["rgba(0, 43, 92, 0.24)", "rgba(0, 71, 27, 0.2)", "#002b5c", "#00471b"],
  WAS: ["rgba(0, 43, 92, 0.24)", "rgba(227, 24, 55, 0.2)", "#002b5c", "#e31837"],
};

const ROLE_DEFINITIONS = {
  "T1": "Tier 1 — Primary playmaker, elite usage + passing",
  "T2": "Tier 2 — Secondary creator, high usage + passing",
  "T3": "Tier 3 — Tertiary creator, moderate playmaking",
  "S1": "Star 1 — Primary scorer, elite usage",
  "S2": "Star 2 — Secondary scorer, high usage",
  "S3": "Star 3 — Tertiary scorer",
  "CON": "Conductor — Elite passer, runs the offense",
  "ISO": "Isolation — High-usage isolation scorer",
  "CLO": "Closer — High IQ, clutch performer",
  "MIC": "Microwave — High usage off the bench",
  "SHO": "Shooter — Elite catch-and-shoot specialist",
  "SLH": "Slasher — Attacks the rim relentlessly",
  "PST": "Post Scorer — Dominant in the paint",
  "MID": "Mid-Range — Elite pull-up jumper",
  "3DN": "3&D — Three-point shooting + defense",
  "DRW": "Driver — Penetrates and finishes",
  "HUB": "Hub — Plays from the elbow/high post",
  "SCR": "Screener — Roll/pop threat off screens",
  "SWT": "Spot-Up — Catches and shoots from deep",
  "CUT": "Cutter — Off-ball slashing to the rim",
  "TRN": "Transition — Fast break finisher",
  "DEF": "Defender — Lockdown perimeter stopper",
  "ANC": "Anchor — Rim protector, paint presence",
  "SWI": "Switchable — Guards multiple positions",
  "ROB": "Robber — Elite steal/deflection threat",
  "BLK": "Shot Blocker — Elite rim protector",
  "DBD": "Defensive Big — Paint presence on D",
  "RBD": "Rebounder — Elite glass cleaner",
  "PST": "Post Defender — Locks down post scorers",
  "OBL": "Off-Ball — Cuts, screens, movement",
  "SPE": "Specialist — Niche role player",
  "IQ": "High IQ — Smart, efficient decisions",
  "UTL": "Utility — Versatile role player",
  "GLU": "Glue Guy — Does the little things",
};

function showToast(message, type = "info", duration = 4000) {
  if (!toastContainerEl) return;
  const icons = { success: "✓", error: "✕", info: "ℹ" };
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `<span class="toast-icon">${icons[type] || icons.info}</span><span>${message}</span><button class="toast-close" aria-label="Dismiss">&times;</button>`;
  toastContainerEl.appendChild(toast);
  const dismiss = () => {
    toast.classList.add("toast-out");
    toast.addEventListener("animationend", () => toast.remove(), { once: true });
    setTimeout(() => toast.remove(), 250);
  };
  toast.querySelector(".toast-close").addEventListener("click", dismiss);
  if (duration > 0) setTimeout(dismiss, duration);
}

function saveRecentPlayer(player) {
  if (!player?.name) return;
  try {
    const recent = JSON.parse(localStorage.getItem("nba2k26_recent_players") || "[]");
    const key = `${player.name.toLowerCase()}|${player.season || "unknown"}`;
    const filtered = recent.filter((r) => `${r.name.toLowerCase()}|${r.season || "unknown"}` !== key);
    filtered.unshift({ name: player.name, team: player.team || "", position: player.position || "", season: player.season || "" });
    localStorage.setItem("nba2k26_recent_players", JSON.stringify(filtered.slice(0, 5)));
  } catch {}
}

function loadRecentPlayers() {
  try {
    return JSON.parse(localStorage.getItem("nba2k26_recent_players") || "[]");
  } catch {
    return [];
  }
}

function renderRecentPlayers() {
  const recent = loadRecentPlayers();
  if (!recent.length) {
    recentPlayersEl.classList.add("hidden");
    return;
  }
  recentPlayersEl.classList.remove("hidden");
  recentListEl.innerHTML = recent.map((r) => {
    const meta = [r.team, r.position].filter(Boolean).join(" · ");
    return `<button class="recent-chip" data-name="${r.name}" data-season="${r.season || ""}"><span>${r.name}</span><span class="recent-team">${r.team}</span><span class="recent-pos">${r.position}</span></button>`;
  }).join("");
  recentListEl.querySelectorAll(".recent-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const name = chip.dataset.name;
      const season = chip.dataset.season;
      if (name) {
        playerSearchEl.value = name;
        if (season) {
          const opt = [...seasonEl.options].find((o) => o.value === season);
          if (opt) seasonEl.value = season;
        }
        runSearch(name);
      }
    });
  });
}

function updateTeamProgress(completed, total) {
  if (!teamProgressWrap) return;
  teamProgressWrap.classList.remove("hidden");
  const pct = total > 0 ? Math.round((completed / total) * 100) : 0;
  teamProgressFill.style.width = `${pct}%`;
  teamProgressText.textContent = `${completed} / ${total}`;
}

function resetTeamProgress() {
  if (!teamProgressWrap) return;
  teamProgressWrap.classList.add("hidden");
  teamProgressFill.style.width = "0%";
  teamProgressText.textContent = "0 / 0";
}

function applyTeamTheme(team) {
  const pair = TEAM_THEME[String(team || "").toUpperCase()] || ["rgba(83, 194, 255, 0.18)", "rgba(255, 106, 61, 0.18)", "#53c2ff", "#ff6a3d"];
  document.documentElement.style.setProperty("--team-a", pair[0]);
  document.documentElement.style.setProperty("--team-b", pair[1]);
  document.documentElement.style.setProperty("--team-primary", pair[2] || "#53c2ff");
  document.documentElement.style.setProperty("--team-secondary", pair[3] || "#ff6a3d");
  if (teamLayerEl) {
    teamLayerEl.animate([{ opacity: 0.25 }, { opacity: 1 }], { duration: 240, easing: "ease-out" });
  }
}

function setActiveNav(activeId) {
  [navDashboardBtn, document.getElementById("navPlayerGenBtn"), openTeamPageBtn, openPlaybookBtn, openStatsBtn,
   document.getElementById("openShotChartBtn"),
   document.getElementById("openProgressionBtn"),
   document.getElementById("navContractsBtn"),
   document.getElementById("openNotesBtn")].forEach(btn => {
    if (!btn) return;
    btn.classList.toggle("nav-active", btn.id === activeId);
  });
}

function _hideAllPages() {
  dashboardPageEl.classList.add("hidden");
  playerGenPageEl?.classList.add("hidden");
  teamPageEl.classList.add("hidden");
  profilePageEl.classList.add("hidden");
  playbookPageEl.classList.add("hidden");
  comparePageEl.classList.add("hidden");
  if (statsPageEl) statsPageEl.classList.add("hidden");
  if (shotChartPageEl)   shotChartPageEl.classList.add("hidden");
  if (progressionPageEl) progressionPageEl.classList.add("hidden");
  document.getElementById("notesPage")?.classList.add("hidden");
  document.getElementById("usersPage")?.classList.add("hidden");
  contractPageEl?.classList.add("hidden");
  gearPageEl?.classList.add("hidden");
}

function showDashboard() {
  _hideAllPages();
  dashboardPageEl.classList.remove("hidden");
  document.body.classList.remove("profile-open");
  setActiveNav("navDashboardBtn");
  renderDashboard();
}

function showPlayerGenPage() {
  _hideAllPages();
  playerGenPageEl.classList.remove("hidden");
  document.body.classList.remove("profile-open");
  setActiveNav("navPlayerGenBtn");
  loadDashboardTopPlayers();
  renderRecentPlayers();
}

// ── Dashboard render ───────────────────────────────────────────────────────

let _dbPlatform = "console";

let _dbInited = false;

function renderDashboard() {
  const recent = loadRecentPlayers();
  const genEl = document.getElementById("dbStatGeneratedVal");
  if (genEl) genEl.textContent = recent.length || "0";
  _dbRenderRecentActivity(recent);
  _dbFetchSnapshot(_dbPlatform);
  document.getElementById("dbPlatTabs")?.querySelectorAll(".db-plat-btn").forEach(btn => {
    btn.onclick = () => {
      document.querySelectorAll("#dbPlatTabs .db-plat-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      _dbPlatform = btn.dataset.plat;
      _dbFetchSnapshot(_dbPlatform);
    };
  });
  if (!_dbInited) { _dbInited = true; _dbInitChangelog(); }
}

async function _dbFetchSnapshot(platform) {
  const snapEl = document.getElementById("dbProgSnapshot");
  if (!snapEl) return;
  if (!_fireDb) { snapEl.innerHTML = '<div class="db-snap-loading">Not connected</div>'; return; }
  snapEl.innerHTML = '<div class="db-snap-loading">Loading…</div>';
  try {
    const doc = await _fireDb.collection("progression").doc(platform).get();
    _dbRenderSnapshot(doc.exists ? doc.data() : {});
  } catch {
    snapEl.innerHTML = '<div class="db-snap-loading">Failed to load</div>';
  }
}

function _dbRenderSnapshot(data) {
  const snapEl = document.getElementById("dbProgSnapshot");
  if (!snapEl) return;

  const teams = PROG_TEAMS.map(name => {
    const tk = progKey(name);
    const td = data[tk] || {};
    let done = 0, wo = 0, ir = 0;
    for (const c of PROG_CATS) {
      const st = td[c.key] || "ns";
      if (st === "done") done++;
      else if (st === "wo") wo++;
      else if (st === "ir") ir++;
    }
    return { name, pct: Math.round((done / PROG_CATS.length) * 100), done, active: wo + ir };
  });

  const totalCells = PROG_TEAMS.length * PROG_CATS.length;
  const totalDone = teams.reduce((s, t) => s + t.done, 0);
  const teamsComplete = teams.filter(t => t.done === PROG_CATS.length).length;
  let totalWip = 0;
  for (const tk of Object.keys(data)) {
    if (tk === "catPriorities" || tk === "workingOn") continue;
    const td = data[tk];
    if (typeof td !== "object" || td === null) continue;
    for (const ck of Object.keys(td)) {
      if (td[ck] === "wo" || td[ck] === "ir") totalWip++;
    }
  }
  const overallPct = Math.round((totalDone / totalCells) * 100);

  const ovEl = document.getElementById("dbStatOverallVal");
  const tcEl = document.getElementById("dbStatTeamsVal");
  const wipEl = document.getElementById("dbStatWipVal");
  if (ovEl) ovEl.textContent = overallPct + "%";
  if (tcEl) tcEl.textContent = `${teamsComplete} / ${PROG_TEAMS.length}`;
  if (wipEl) wipEl.textContent = totalWip;

  const sorted = [...teams].sort((a, b) => b.pct - a.pct);
  const top5 = sorted.slice(0, 5);
  const bot5 = sorted.slice(-5).reverse();
  const wip = data?.workingOn || [];
  const tc = (name) => PROG_TEAM_COLORS[name] || "#4da8ff";

  const teamRow = (t) => `
    <div class="db-snap-team-row">
      <span class="db-snap-team-dot" style="background:${tc(t.name)}"></span>
      <span class="db-snap-team-name">${t.name.split(" ").pop()}</span>
      <div class="db-snap-mini-bar"><div class="db-snap-mini-fill" style="width:${Math.max(t.pct, 2)}%;background:${tc(t.name)}"></div></div>
      <span class="db-snap-team-pct">${t.pct}%</span>
    </div>`;

  snapEl.innerHTML = `
    <div class="db-snap-overall">
      <div class="db-snap-bar-wrap">
        <div class="db-snap-bar-track"><div class="db-snap-bar-fill" style="width:${overallPct}%"></div></div>
        <span class="db-snap-pct">${overallPct}%</span>
      </div>
      <span class="db-snap-sublabel">${totalDone} / ${totalCells} cells complete</span>
    </div>
    <div class="db-snap-cols">
      <div class="db-snap-col">
        <div class="db-snap-col-label">Top Teams</div>
        ${top5.map(teamRow).join("")}
      </div>
      <div class="db-snap-col">
        <div class="db-snap-col-label">Need Attention</div>
        ${bot5.map(teamRow).join("")}
      </div>
    </div>
    ${wip.length ? `<div class="db-snap-wip"><div class="db-snap-col-label">Working On</div><div class="db-snap-wip-items">${
      wip.slice(0, 5).map(w => `<span class="db-snap-wip-chip">${w}</span>`).join("")
    }${wip.length > 5 ? `<span class="db-snap-wip-chip db-snap-wip-more">+${wip.length - 5}</span>` : ""}</div></div>` : ""}
  `;
}

function _dbRenderRecentActivity(recent) {
  const el = document.getElementById("dbRecentList");
  if (!el) return;
  if (!recent?.length) {
    el.innerHTML = '<div class="db-recent-empty">No players generated yet. Head to Player Gen to get started.</div>';
    return;
  }
  el.innerHTML = recent.map(p => `
    <div class="db-recent-row">
      <div class="db-recent-avatar">${(p.name || "?")[0].toUpperCase()}</div>
      <div class="db-recent-info">
        <span class="db-recent-name">${p.name}</span>
        <span class="db-recent-meta">${[p.team, p.position, p.season].filter(Boolean).join(" · ")}</span>
      </div>
    </div>
  `).join("");
}

// ── Changelog (What's New) ─────────────────────────────────────────────────

let _clUnsub = null;

function _dbInitChangelog() {
  const postBtn = document.getElementById("dbClPostBtn");
  const form    = document.getElementById("dbClForm");
  const cancelBtn = document.getElementById("dbClCancelBtn");
  const submitBtn = document.getElementById("dbClSubmitBtn");

  if (_currentRole === "head_admin") {
    postBtn?.classList.remove("hidden");
  }

  postBtn?.addEventListener("click", () => form?.classList.toggle("hidden"));
  cancelBtn?.addEventListener("click", () => {
    form?.classList.add("hidden");
    _dbClClearForm();
  });
  submitBtn?.addEventListener("click", _dbClSubmit);

  _dbSubscribeChangelog();
}

function _dbSubscribeChangelog() {
  if (!_fireDb) {
    document.getElementById("dbChangelogList").innerHTML = '<div class="db-snap-loading">Not connected</div>';
    return;
  }
  if (_clUnsub) return;
  _clUnsub = _fireDb.collection("meta").doc("changelog")
    .onSnapshot(snap => {
      const entries = (snap.exists ? snap.data()?.entries : null) || [];
      _dbRenderChangelog(entries);
    }, () => {
      document.getElementById("dbChangelogList").innerHTML = '<div class="db-snap-loading">Failed to load</div>';
    });
}

function _dbRenderChangelog(entries) {
  const el = document.getElementById("dbChangelogList");
  if (!el) return;
  if (!entries.length) {
    el.innerHTML = `
      <div class="db-cl-empty-state">
        <svg viewBox="0 0 48 48" fill="none" width="40" height="40" opacity=".25">
          <rect x="8" y="6" width="32" height="36" rx="4" stroke="currentColor" stroke-width="2"/>
          <path d="M16 16h16M16 22h16M16 28h10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        </svg>
        <p>No updates posted yet.</p>
      </div>`;
    return;
  }

  const sorted = [...entries].sort((a, b) => (b.date || "").localeCompare(a.date || ""));
  const now = Date.now();
  const isNew = (e) => e.date && (now - new Date(e.date).getTime()) < 7 * 86400000;

  const HERO_BG = {
    feature: "linear-gradient(135deg, rgba(77,168,255,0.16) 0%, rgba(77,168,255,0.04) 80%)",
    update:  "linear-gradient(135deg, rgba(167,139,250,0.16) 0%, rgba(167,139,250,0.04) 80%)",
    fix:     "linear-gradient(135deg, rgba(251,191,36,0.14) 0%, rgba(251,191,36,0.03) 80%)",
  };
  const HERO_GLOW = {
    feature: "rgba(77,168,255,0.22)",
    update:  "rgba(167,139,250,0.22)",
    fix:     "rgba(251,191,36,0.2)",
  };
  const TAG_LABEL = { feature: "Feature", update: "Update", fix: "Fix" };
  const fmtDate = (d) => d ? new Date(d).toLocaleDateString("en-US", { month: "short", day: "numeric" }) : "";

  const [hero, ...rest] = sorted;
  const hTag = hero.tag || "update";

  const heroHtml = `
    <div class="db-cl-hero" style="background:${HERO_BG[hTag] || HERO_BG.update};border-color:${HERO_GLOW[hTag] || HERO_GLOW.update}">
      <div class="db-cl-hero-top">
        <span class="db-cl-tag db-cl-tag-${hTag}">${TAG_LABEL[hTag] || hTag}</span>
        ${isNew(hero) ? '<span class="db-cl-new-badge">NEW</span>' : ""}
        <span class="db-cl-hero-meta">${fmtDate(hero.date)}${hero.author ? ` · ${safeHtml(hero.author)}` : ""}</span>
      </div>
      <div class="db-cl-hero-title">${safeHtml(hero.title)}</div>
      ${hero.desc ? `<div class="db-cl-hero-desc">${safeHtml(hero.desc)}</div>` : ""}
    </div>`;

  const timelineHtml = rest.length ? `
    <div class="db-cl-timeline">
      ${rest.map(e => {
        const tag = e.tag || "update";
        return `
          <div class="db-cl-tl-row">
            <div class="db-cl-tl-line">
              <div class="db-cl-tl-dot db-cl-tl-dot-${tag}"></div>
              <div class="db-cl-tl-track"></div>
            </div>
            <div class="db-cl-tl-body">
              <div class="db-cl-tl-top">
                <span class="db-cl-tag db-cl-tag-${tag}">${TAG_LABEL[tag] || tag}</span>
                ${isNew(e) ? '<span class="db-cl-new-badge">NEW</span>' : ""}
                <span class="db-cl-tl-date">${fmtDate(e.date)}</span>
              </div>
              <div class="db-cl-tl-title">${safeHtml(e.title)}</div>
              ${e.desc ? `<div class="db-cl-tl-desc">${safeHtml(e.desc)}</div>` : ""}
            </div>
          </div>`;
      }).join("")}
    </div>` : "";

  el.innerHTML = heroHtml + timelineHtml;
}

async function _dbClSubmit() {
  const title = document.getElementById("dbClTitle")?.value.trim();
  const desc  = document.getElementById("dbClDesc")?.value.trim();
  const tag   = document.getElementById("dbClTag")?.value || "update";
  if (!title) return;

  const submitBtn = document.getElementById("dbClSubmitBtn");
  submitBtn.disabled = true;
  submitBtn.textContent = "Posting…";

  try {
    const ref  = _fireDb.collection("meta").doc("changelog");
    const snap = await ref.get();
    const entries = snap.exists ? (snap.data()?.entries || []) : [];
    const newEntry = {
      id: Date.now().toString(),
      tag, title, desc,
      date: new Date().toISOString(),
      author: getDisplayName() || "—",
    };
    const updated = [newEntry, ...entries].slice(0, 50);
    await ref.set({ entries: updated }, { merge: true });
    document.getElementById("dbClForm")?.classList.add("hidden");
    _dbClClearForm();
  } catch (err) {
    console.error("Changelog post failed:", err);
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Post Update";
  }
}

function _dbClClearForm() {
  const t = document.getElementById("dbClTitle"); if (t) t.value = "";
  const d = document.getElementById("dbClDesc");  if (d) d.value = "";
  const s = document.getElementById("dbClTag");   if (s) s.value = "feature";
}

let _dashTopLoaded = false;
async function loadDashboardTopPlayers() {
  const el = document.getElementById("dashTopPlayers");
  if (!el) return;
  if (_dashTopLoaded) return;
  el.innerHTML = '<div class="dash-qs-loading">Loading…</div>';
  try {
    const result = await window.nba2kDesktop.fetchLeagueLeaders({
      season: "2025-26", seasonType: "Regular Season", perMode: "PerGame", category: "PTS",
    });
    if (!result?.ok || !result.data?.length) {
      el.innerHTML = '<div class="dash-qs-loading">No data available</div>';
      return;
    }
    const top3 = result.data.slice(0, 3);
    el.innerHTML = top3.map((row, i) => {
      const name = row.PLAYER || row.PLAYER_NAME || "—";
      const team = row.TEAM || row.TEAM_ABBREVIATION || "";
      const pts  = Number(row.PTS).toFixed(1);
      const playerId = row.PLAYER_ID;
      return `<button class="dash-top-row" data-name="${name}" data-pid="${playerId || ""}">
        <span class="dash-top-rank">${i + 1}</span>
        <span class="dash-top-name">${name}</span>
        <span class="dash-top-team">${team}</span>
        <span class="dash-top-pts">${pts} <span class="dash-top-cat">PTS</span></span>
      </button>`;
    }).join("");
    el.querySelectorAll(".dash-top-row").forEach((btn) => {
      btn.addEventListener("click", () => {
        const name = btn.dataset.name;
        const pid  = btn.dataset.pid;
        showStatsPage();
        if (name) openPlayerDetail(name, pid || null);
      });
    });
    _dashTopLoaded = true;
  } catch {
    el.innerHTML = '<div class="dash-qs-loading">Failed to load</div>';
  }
}

function showTeamPage() {
  _hideAllPages();
  teamPageEl.classList.remove("hidden");
  document.body.classList.add("profile-open");
  setActiveNav("openTeamPageBtn");
}

function showStatsPage() {
  _hideAllPages();
  statsPageEl.classList.remove("hidden");
  document.body.classList.add("profile-open");
  setActiveNav("openStatsBtn");
  statsInit();
}

function showProgressionPage() {
  if (!progressionPageEl) return;
  _hideAllPages();
  progressionPageEl.classList.remove("hidden");
  document.body.classList.add("profile-open");
  setActiveNav("openProgressionBtn");
  progressionPageInit();
}

function showShotChartPage() {
  if (!shotChartPageEl) return;
  _hideAllPages();
  shotChartPageEl.classList.remove("hidden");
  document.body.classList.add("profile-open");
  setActiveNav("openShotChartBtn");
  shotChartPageInit();
}

function showProfile() {
  _hideAllPages();
  profilePageEl.classList.remove("hidden");
  document.body.classList.add("profile-open");
}

function showComparePage() {
  _hideAllPages();
  comparePageEl.classList.remove("hidden");
  document.body.classList.add("profile-open");
}

async function showPlaybookPage() {
  _hideAllPages();
  playbookPageEl.classList.remove("hidden");
  document.body.classList.add("profile-open");
  setActiveNav("openPlaybookBtn");

  // Load play catalog and wait for it before allowing load
  await loadPlayCatalog();
}

async function loadPlayCatalog() {
  try {
    const result = await window.nba2kDesktop.getPlayCatalog({});
    console.log('Play catalog result:', result);
    if (result.ok) {
      availablePlays = result.plays || {};
      console.log('Loaded plays:', Object.keys(availablePlays).length);
      return;
    } else {
      console.warn('Catalog error:', result.error);
    }
  } catch (e) {
    console.error('Catalog load error:', e);
  }
  
  availablePlays = EMBEDDED_PLAYS;
}

async function loadTeamPlaybook() {
  const team = playbookTeamSelectEl.value;
  playbookStatusEl.textContent = `Loading ${team} playbook... (in game, go to ${team}'s playbook first)`;
  
  try {
    const result = await window.nba2kDesktop.getPlaybook({ team });
    console.log('Playbook result for', team, ':', result);
    if (result.ok) {
      currentPlaybookTeam = team;
      currentPlaybookPlays = result.plays || [];
      console.log('Loaded plays array:', currentPlaybookPlays);
      renderPlaybookList();
      playbookStatusEl.textContent = `${team} - ${currentPlaybookPlays.length} plays loaded`;
      savePlaybookBtn.disabled = false;
      addPlayBtn.disabled = false;
      removePlayBtn.disabled = false;
    } else {
      console.warn('Load playbook result:', result);
      playbookStatusEl.textContent = result.error || "Failed to load playbook";
    }
  } catch (e) {
    console.error('Load playbook error:', e);
    playbookStatusEl.textContent = 'Game not running: ' + (e?.message || e);
  }
}

async function saveTeamPlaybook() {
  if (!currentPlaybookTeam || currentPlaybookPlays.length === 0) return;
  
  playbookStatusEl.textContent = `Saving ${currentPlaybookTeam} playbook...`;
  
  try {
    const playIndices = currentPlaybookPlays.map(p => typeof p === 'object' ? p.index : p);
    const result = await window.nba2kDesktop.setPlaybook({ 
      team: currentPlaybookTeam, 
      playIndices 
    });
    
    if (result.ok) {
      playbookStatusEl.textContent = `${currentPlaybookTeam} playbook saved!`;
    } else {
      playbookStatusEl.textContent = result.error || 'Save failed';
    }
  } catch (e) {
    playbookStatusEl.textContent = 'Save failed - ensure game is running';
  }
}

// Embedded play catalog (subset - full catalog in separate file)
const EMBEDDED_PLAYS = {
  1: "FIST \"1-4\"", 2: "HIGH \"1-4\"", 3: "QUICK 42 \"1-4\"",
  6: "00 ISO BOX 3 QUICK", 7: "00 ISO RIP 3", 11: "00 PUNCH 15",
  25: "01 LAL ISO 2 QUICK DBL", 26: "01 LAL ISO 2 QUICK TRI", 27: "01 LAL ISO 2 SLIP",
  28: "01 LAL ISO 2 TRI", 53: "01 SAC HIGH PUNCH 4 QUICK", 117: "02 FIST 14 QUICK CURL DBL",
  126: "02 FIST 14 SIDE OUT"
};

function renderPlaybookList() {
  if (!playbookListEl) return;
  
  playbookListEl.innerHTML = '';
  
  // Clear any existing items 
  while (playbookListEl.firstChild) {
    playbookListEl.removeChild(playbookListEl.firstChild);
  }
  
  currentPlaybookPlays.forEach((play, i) => {
    const playIdx = typeof play === 'object' ? play.index : play;
    const playName = typeof play === 'object' ? play.name : (availablePlays[playIdx] || `Play ${playIdx}`);
    
    const item = document.createElement('div');
    item.className = 'playbook-item';
    item.dataset.index = i;
    item.innerHTML = `
      <span class="play-index">${i + 1}</span>
      <span class="play-name">${playName}</span>
    `;
    item.addEventListener('click', () => {
      document.querySelectorAll('.playbook-item').forEach(el => el.classList.remove('selected'));
      item.classList.add('selected');
    });
    playbookListEl.appendChild(item);
  });
}

function addPlayToPlaybook() {
  const playIdStr = prompt("Enter play ID(s) to add (comma separated, e.g., 17,865,895):");
  if (!playIdStr) return;
  
  const playIds = playIdStr.split(',').map(s => parseInt(s.trim(), 10)).filter(n => !isNaN(n) && n > 0);
  if (!playIds.length) {
    playbookStatusEl.textContent = 'Invalid play ID(s)';
    return;
  }
  
  currentPlaybookPlays = currentPlaybookPlays.concat(playIds.map(id => ({ index: id, name: availablePlays[id] || `Play ${id}` })));
  renderPlaybookList();
  
  if (savePlaybookBtn) savePlaybookBtn.disabled = false;
  if (addPlayBtn) addPlayBtn.disabled = false;
  if (removePlayBtn) removePlayBtn.disabled = false;
  
  playbookStatusEl.textContent = `Added ${playIds.length} play(s) - click Save to write to game`;
}

function removeSelectedPlay() {
  const selected = playbookListEl.querySelector('.playbook-item.selected');
  if (selected) {
    const idx = Array.from(playbookListEl.children).indexOf(selected);
    if (idx >= 0) {
      currentPlaybookPlays.splice(idx, 1);
      renderPlaybookList();
    }
  }
}

function buildAttrFullHtml(p1, p2, ratings1, ratings2) {
  const attrs1 = p1.attributeGroups || {};
  const attrs2 = p2.attributeGroups || {};
  const attrMap1 = {};
  Object.values(attrs1).forEach((items) => items.forEach((i) => { attrMap1[i.key || i.name] = Number(i.value ?? 0); }));
  const attrMap2 = {};
  Object.values(attrs2).forEach((items) => items.forEach((i) => { attrMap2[i.key || i.name] = Number(i.value ?? 0); }));
  const groups = {};
  Object.keys(attrs1).forEach((g) => { if (!groups[g]) groups[g] = []; (attrs1[g] || []).forEach((i) => { if (!groups[g].find((x) => (x.key || x.name) === (i.key || i.name))) groups[g].push(i); }); });
  Object.keys(attrs2).forEach((g) => { if (!groups[g]) groups[g] = []; (attrs2[g] || []).forEach((i) => { if (!groups[g].find((x) => (x.key || x.name) === (i.key || i.name))) groups[g].push(i); }); });

  const info1 = p1.info || {};
  const info2 = p2.info || {};

  return `
    <div class="compare-full-header">
      <span class="compare-full-label p1">${info1.name || "Player 1"}</span>
      <span class="compare-full-center">Attribute</span>
      <span class="compare-full-label p2">${info2.name || "Player 2"}</span>
    </div>
    ${Object.entries(groups).map(([title, items]) => {
      const rows = items.map((item) => {
        const key = item.key || item.name;
        const v1 = attrMap1[key] ?? 0;
        const v2 = attrMap2[key] ?? 0;
        const diff = v1 - v2;
        const c1Class = diff > 0 ? "better" : diff < 0 ? "worse" : "equal";
        const c2Class = diff < 0 ? "better" : diff > 0 ? "worse" : "equal";
        const pct1 = Math.round((Math.max(0, Math.min(99, v1)) / 99) * 100);
        const pct2 = Math.round((Math.max(0, Math.min(99, v2)) / 99) * 100);
        const color1 = attrBarColor(v1);
        const color2 = attrBarColor(v2);
        const diffLabel = diff === 0 ? "" : diff > 0 ? `+${diff}` : `${diff}`;
        return `
          <div class="compare-attr-row">
            <div class="compare-attr-side left">
              <span class="compare-attr-val ${c1Class}">${v1}</span>
              <div class="compare-attr-track left-track"><div class="compare-attr-fill ${c1Class}" style="width:${pct1}%;background:${color1}"></div></div>
            </div>
            <div class="compare-attr-center">
              <span class="compare-attr-label">${item.name || key}</span>
              ${diffLabel ? `<span class="compare-attr-diff ${c1Class}">${diffLabel}</span>` : ""}
            </div>
            <div class="compare-attr-side right">
              <div class="compare-attr-track right-track"><div class="compare-attr-fill ${c2Class}" style="width:${pct2}%;background:${color2}"></div></div>
              <span class="compare-attr-val ${c2Class}">${v2}</span>
            </div>
          </div>`;
      }).join("");
      return `<div class="compare-section"><h4 class="compare-section-title">${title}</h4>${rows}</div>`;
    }).join("")}`;
}

function renderComparison(p1, p2) {
  if (!compareContentEl) return;
  const info1 = p1.info || {};
  const info2 = p2.info || {};
  const ratings1 = computePositionAwareRatings(p1);
  const ratings2 = computePositionAwareRatings(p2);

  const ovrClass1 = ovrTierClass(ratings1.overall);
  const ovrClass2 = ovrTierClass(ratings2.overall);
  const ovrColor1 = ratings1.overall >= 90 ? "#f0b236" : ratings1.overall >= 80 ? "#2ba6ff" : "#31c7b2";
  const ovrColor2 = ratings2.overall >= 90 ? "#f0b236" : ratings2.overall >= 80 ? "#2ba6ff" : "#31c7b2";

  const initials1 = (info1.name || "P1").split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase();
  const initials2 = (info2.name || "P2").split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase();

  const photoHtml = (info, initials, color) => {
    if (info.photoUrl) {
      return `<img class="compare-hero-photo" src="${info.photoUrl}" alt="${info.name || ''}" onerror="this.outerHTML='<div class=\\'compare-hero-photo-fallback\\'>${initials}</div>'" />`;
    }
    return `<div class="compare-hero-photo-fallback" style="background:${color}22;border-color:${color}44">${initials}</div>`;
  };

  const ratingBadge = (label, val, variant = "") => `
    <div class="compare-rating-badge ${variant}">
      <span class="crb-label">${label}</span>
      <span class="crb-val">${val}</span>
    </div>`;

  compareContentEl.innerHTML = `
    <div class="compare-heroes">
      <div class="compare-hero-card p1-card">
        <div class="compare-hero-ovr" style="--ovr-color:${ovrColor1}">
          <svg viewBox="0 0 80 80" width="80" height="80">
            <circle cx="40" cy="40" r="34" fill="none" stroke="rgba(255,255,255,0.1)" stroke-width="4"/>
            <circle cx="40" cy="40" r="34" fill="none" stroke="${ovrColor1}" stroke-width="4" stroke-linecap="round"
              stroke-dasharray="${Math.round(ratings1.overall * 2.136)} 213.6" transform="rotate(-90 40 40)"/>
          </svg>
          <div class="compare-hero-ovr-inner">
            <span class="compare-hero-ovr-num">${ratings1.overall}</span>
            <span class="compare-hero-ovr-tier">${ovrTierLabel(ratings1.overall)}</span>
          </div>
        </div>
        <div class="compare-hero-photo-wrap">${photoHtml(info1, initials1, ovrColor1)}</div>
        <div class="compare-hero-info">
          <h2 class="compare-hero-name">${info1.name || "Player 1"}</h2>
          <p class="compare-hero-meta">${[info1.team, info1.position].filter(Boolean).join(" · ")}</p>
          <div class="compare-hero-season">${info1.season || ""}</div>
        </div>
        <div class="compare-hero-ratings">
          ${ratingBadge("OFF", ratings1.offense, "off")}
          ${ratingBadge("DEF", ratings1.defense, "def")}
          ${ratingBadge("PHY", ratings1.physical, "phy")}
        </div>
      </div>

      <div class="compare-vs-divider">
        <span class="compare-vs-text">VS</span>
      </div>

      <div class="compare-hero-card p2-card">
        <div class="compare-hero-ovr" style="--ovr-color:${ovrColor2}">
          <svg viewBox="0 0 80 80" width="80" height="80">
            <circle cx="40" cy="40" r="34" fill="none" stroke="rgba(255,255,255,0.1)" stroke-width="4"/>
            <circle cx="40" cy="40" r="34" fill="none" stroke="${ovrColor2}" stroke-width="4" stroke-linecap="round"
              stroke-dasharray="${Math.round(ratings2.overall * 2.136)} 213.6" transform="rotate(-90 40 40)"/>
          </svg>
          <div class="compare-hero-ovr-inner">
            <span class="compare-hero-ovr-num">${ratings2.overall}</span>
            <span class="compare-hero-ovr-tier">${ovrTierLabel(ratings2.overall)}</span>
          </div>
        </div>
        <div class="compare-hero-photo-wrap">${photoHtml(info2, initials2, ovrColor2)}</div>
        <div class="compare-hero-info">
          <h2 class="compare-hero-name">${info2.name || "Player 2"}</h2>
          <p class="compare-hero-meta">${[info2.team, info2.position].filter(Boolean).join(" · ")}</p>
          <div class="compare-hero-season">${info2.season || ""}</div>
        </div>
        <div class="compare-hero-ratings">
          ${ratingBadge("OFF", ratings2.offense, "off")}
          ${ratingBadge("DEF", ratings2.defense, "def")}
          ${ratingBadge("PHY", ratings2.physical, "phy")}
        </div>
      </div>
    </div>
  `;

  if (compareFullContentEl) {
    compareFullContentEl.innerHTML = buildAttrFullHtml(p1, p2, ratings1, ratings2);
    compareFullContentEl.classList.add("hidden");
  }
  if (compareExpandBtn) {
    compareExpandBtn.textContent = "Full Comparison";
    compareExpandBtn._expanded = false;
  }

  showComparePage();
}

function renderTeamDashboard(team, season, cards) {
  const el = document.getElementById("teamDashboard");
  if (!el) return;

  const validCards = cards.filter((c) => c.profile);
  if (validCards.length < 2) {
    el.classList.add("hidden");
    return;
  }

  el.classList.remove("hidden");
  const ratings = validCards.map((c) => computePositionAwareRatings(c.profile));
  const avgOvr = ratings.reduce((s, r) => s + r.overall, 0) / ratings.length;
  const avgOff = ratings.reduce((s, r) => s + r.offense, 0) / ratings.length;
  const avgDef = ratings.reduce((s, r) => s + r.defense, 0) / ratings.length;
  const avgPhy = ratings.reduce((s, r) => s + r.physical, 0) / ratings.length;

  const posCounts = { PG: 0, SG: 0, SF: 0, PF: 0, C: 0 };
  validCards.forEach((c) => {
    const pos = String(c.profile?.info?.position || "").toUpperCase();
    if (pos.includes("PG")) posCounts.PG++;
    else if (pos.includes("SG")) posCounts.SG++;
    else if (pos.includes("SF")) posCounts.SF++;
    else if (pos.includes("PF")) posCounts.PF++;
    else if (pos.includes("C")) posCounts.C++;
  });

  const totalPlayers = validCards.length;
  const posLabels = ["PG", "SG", "SF", "PF", "C"];
  const posSegments = posLabels.map((p) => {
    const pct = totalPlayers > 0 ? (posCounts[p] / totalPlayers) * 100 : 0;
    return pct > 4 ? `<div class="team-pos-segment ${p.toLowerCase()}" style="width:${pct}%">${posCounts[p]}</div>` : "";
  }).filter(Boolean).join("");

  const posLegend = posLabels.map((p) => {
    if (posCounts[p] === 0) return "";
    return `<span class="team-pos-legend-item"><span class="team-pos-legend-dot ${p.toLowerCase()}"></span>${p} ${posCounts[p]}</span>`;
  }).filter(Boolean).join("");

  const sorted = [...validCards].sort((a, b) => {
    const ra = computePositionAwareRatings(a.profile);
    const rb = computePositionAwareRatings(b.profile);
    return rb.overall - ra.overall;
  });
  const top3 = sorted.slice(0, 3);
  const topPills = top3.map((c) => {
    const info = c.profile.info || {};
    const r = computePositionAwareRatings(c.profile);
    return `<span class="team-top-pill" data-name="${info.name || ""}"><span class="star">★</span><span class="name">${info.name?.split(" ").pop() || ""}</span><span class="ovr">${r.overall}</span></span>`;
  }).join("");

  el.innerHTML = `
    <div class="team-dashboard-header">
      <div>
        <h3 class="team-dashboard-title">${team} ${season}</h3>
        <p class="team-dashboard-subtitle">${validCards.length} players generated</p>
      </div>
    </div>
    <div class="team-stat-cards">
      <div class="team-stat-card ovr">
        <span class="team-stat-label">Team OVR</span>
        <span class="team-stat-value">${Math.round(avgOvr)}</span>
        <div class="team-stat-bar"><div class="team-stat-fill" style="width:0%" data-target="${(avgOvr / 99) * 100}"></div></div>
      </div>
      <div class="team-stat-card off">
        <span class="team-stat-label">Offense</span>
        <span class="team-stat-value">${Math.round(avgOff)}</span>
        <div class="team-stat-bar"><div class="team-stat-fill" style="width:0%" data-target="${(avgOff / 99) * 100}"></div></div>
      </div>
      <div class="team-stat-card def">
        <span class="team-stat-label">Defense</span>
        <span class="team-stat-value">${Math.round(avgDef)}</span>
        <div class="team-stat-bar"><div class="team-stat-fill" style="width:0%" data-target="${(avgDef / 99) * 100}"></div></div>
      </div>
      <div class="team-stat-card phy">
        <span class="team-stat-label">Physical</span>
        <span class="team-stat-value">${Math.round(avgPhy)}</span>
        <div class="team-stat-bar"><div class="team-stat-fill" style="width:0%" data-target="${(avgPhy / 99) * 100}"></div></div>
      </div>
    </div>
    <div class="team-pos-dist">
      <div class="team-pos-dist-label">Position Distribution</div>
      <div class="team-pos-bar">${posSegments}</div>
      <div class="team-pos-legend">${posLegend}</div>
    </div>
    <div class="team-top-players">
      <span class="team-top-label">Top Players</span>
      <div class="team-top-list">${topPills}</div>
    </div>
  `;

  requestAnimationFrame(() => {
    el.querySelectorAll(".team-stat-fill[data-target]").forEach((fill) => {
      fill.style.width = `${fill.dataset.target}%`;
    });
  });

  el.querySelectorAll(".team-top-pill[data-name]").forEach((pill) => {
    pill.addEventListener("click", () => {
      const name = pill.dataset.name;
      const entry = validCards.find((c) => c.profile.info?.name === name);
      if (entry?.profile) {
        profileBackTarget = "team";
        renderProfile(entry.profile, { backTarget: "team" });
      }
    });
  });
}

function updateCompareSelectionUI() {
  const count = compareCandidates.length;
  if (teamCompareBtn) {
    teamCompareBtn.disabled = count < 2;
    teamCompareBtn.textContent = count === 2 ? `Compare (${count})` : count === 1 ? "Compare (1/2)" : "Compare";
  }
  // Refresh compare button states on roster cards
  teamResultsEl.querySelectorAll(".roster-card-compare-btn").forEach((btn) => {
    const name = btn.dataset.compareName;
    const isSelected = compareCandidates.some((c) => (c.profile?.info?.name || "") === name);
    btn.classList.toggle("compare-selected", isSelected);
    btn.setAttribute("aria-pressed", String(isSelected));
    btn.setAttribute("title", isSelected ? "Remove from comparison" : "Add to comparison");
  });
}

function renderCompactRoster(cards, failures) {
  compareCandidates = [];
  const sorted = [...cards].sort((a, b) => {
    if (!a.profile && !b.profile) return 0;
    if (!a.profile) return 1;
    if (!b.profile) return -1;
    return computePositionAwareRatings(b.profile).overall - computePositionAwareRatings(a.profile).overall;
  });

  const cardHtml = sorted.map((entry, idx) => {
    const profile = entry.profile || {};
    const info = profile.info || {};
    const displayName = info.name || entry.player?.name || "Player";
    const rawPos = entry.player?.position || info.position || "N/A";
    const displayPos = String(rawPos).trim().toLowerCase() === "none" ? "N/A" : rawPos;
    const ratingSummary = entry.profile ? computePositionAwareRatings(entry.profile) : null;
    const ovrText = ratingSummary ? String(ratingSummary.overall) : "--";
    const ovrClass = ratingSummary ? ovrTierClass(ratingSummary.overall) : "";
    const roleText = (profile.role || profile.archetype || "Core").toString();
    const posClass = getPosBadgeClass(displayPos);
    const posBadge = posClass ? `<span class="pos-badge ${posClass}">${displayPos.split("/")[0].trim()}</span>` : "";
    const initials = displayName.split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase();
    const compareBtn = entry.profile ? `
      <button class="roster-card-compare-btn" data-compare-idx="${idx}" data-compare-name="${displayName}" title="Add to comparison" aria-pressed="false">
        <svg viewBox="0 0 16 16" fill="none" width="12" height="12">
          <path d="M3 8h10M8 3l5 5-5 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>` : "";

    return `
      <article class="roster-card ${ovrClass}" data-idx="${idx}" style="animation-delay:${Math.min(idx * 20, 280)}ms">
        ${compareBtn}
        ${info.photoUrl
          ? `<img class="roster-card-headshot" src="${info.photoUrl}" alt="${displayName}" onerror="this.outerHTML='<div class=\\'roster-card-headshot-fallback\\'>${initials}</div>'" />`
          : `<div class="roster-card-headshot-fallback">${initials}</div>`}
        <div class="roster-ovr">${ovrText}</div>
        <div class="roster-name" title="${displayName}">${displayName}</div>
        <div class="roster-pos-row">${posBadge}</div>
        <div class="roster-role">${roleText}</div>
        ${entry.error ? `<div class="roster-card-error">${entry.error}</div>` : ""}
      </article>
    `;
  }).join("");

  teamResultsEl.innerHTML = `
    <div class="roster-section-title">Full Roster</div>
    <div class="roster-grid">${cardHtml}</div>
  `;

  const rosterCards = teamResultsEl.querySelectorAll(".roster-card[data-idx]");
  rosterCards.forEach((card) => {
    card.addEventListener("click", (e) => {
      if (e.target.closest(".roster-card-compare-btn")) return;
      const idx = Number(card.dataset.idx);
      const entry = sorted[idx];
      if (entry?.profile) {
        profileBackTarget = "team";
        renderProfile(entry.profile, { backTarget: "team" });
      }
    });
  });

  teamResultsEl.querySelectorAll(".roster-card-compare-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const idx = Number(btn.dataset.compareIdx);
      const entry = sorted[idx];
      if (!entry?.profile) return;
      const name = entry.profile?.info?.name || "";
      const existing = compareCandidates.findIndex((c) => (c.profile?.info?.name || "") === name);
      if (existing >= 0) {
        compareCandidates.splice(existing, 1);
      } else {
        if (compareCandidates.length >= 2) {
          showToast("Only 2 players can be compared at once. Deselect one first.", "info", 2500);
          return;
        }
        compareCandidates.push(entry);
      }
      updateCompareSelectionUI();
    });
  });

  updateCompareSelectionUI();
}

function getPosBadgeClass(position) {
  const pos = String(position || "").toUpperCase();
  if (pos.includes("PG")) return "pg";
  if (pos.includes("SG")) return "sg";
  if (pos.includes("SF")) return "sf";
  if (pos.includes("PF")) return "pf";
  if (pos.includes("C")) return "c";
  return "";
}

function setSelected(player) {
  selectedPlayer = player;
  if (!player) {
    selectedPillEl.textContent = "Selected: No player selected";
    applyTeamTheme("");
    if (clearSelectionBtn) clearSelectionBtn.classList.add("hidden");
    return;
  }
  const meta = [player.team, player.position].filter(Boolean).join(" · ");
  selectedPillEl.textContent = `Selected: ${player.name}${meta ? ` · ${meta}` : ""}`;
  applyTeamTheme(player.team);
  if (clearSelectionBtn) clearSelectionBtn.classList.remove("hidden");
}

function hideSearchResults() {
  searchResultsEl.classList.add("hidden");
  searchResultsEl.innerHTML = "";
  searchFocusIndex = -1;
}

function renderSearchResults(rows) {
  if (!rows.length) {
    searchResultsEl.innerHTML = '<div class="search-row"><span>No players found.</span></div>';
    searchResultsEl.classList.remove("hidden");
    return;
  }

  searchResultsEl.innerHTML = rows
    .map((row, i) => {
      const meta = [row.team, row.position].filter(Boolean).join(" · ");
      return `<button class="search-row" data-index="${i}" role="option" aria-selected="false"><span>${row.name}</span><span class="search-meta">${meta}</span></button>`;
    })
    .join("");
  searchResultsEl.classList.remove("hidden");
  searchFocusIndex = -1;

  const buttons = searchResultsEl.querySelectorAll(".search-row[data-index]");
  buttons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const idx = Number(btn.getAttribute("data-index"));
      const picked = rows[idx];
      if (!picked) return;
      setSelected(picked);
      playerSearchEl.value = picked.name;
      hideSearchResults();
    });
  });
}

function renderSearchResults(rows) {
  if (!rows.length) {
    searchResultsEl.innerHTML = '<div class="search-row"><span>No players found.</span></div>';
    searchResultsEl.classList.remove("hidden");
    return;
  }

  searchResultsEl.innerHTML = rows
    .map((row, i) => {
      const meta = [row.team, row.position].filter(Boolean).join(" · ");
      return `<button class="search-row" data-index="${i}"><span>${row.name}</span><span class="search-meta">${meta}</span></button>`;
    })
    .join("");
  searchResultsEl.classList.remove("hidden");

  const buttons = searchResultsEl.querySelectorAll(".search-row[data-index]");
  buttons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const idx = Number(btn.getAttribute("data-index"));
      const picked = rows[idx];
      if (!picked) return;
      setSelected(picked);
      playerSearchEl.value = picked.name;
      hideSearchResults();
    });
  });
}

async function runSearch(term) {
  const token = ++lastSearchToken;
  const season = seasonLabelFromYear(seasonEl.value);
  const result = await window.nba2kDesktop.searchPlayers({ term, season });
  if (token !== lastSearchToken) return;
  if (!result?.ok) {
    hideSearchResults();
    statusEl.textContent = "Search failed";
    return;
  }
  renderSearchResults(result.results || []);
  statusEl.textContent = "Idle";
}

function setBusy(isBusy) {
  runBtn.disabled = isBusy;
  if (teamGenerateBtn) teamGenerateBtn.disabled = isBusy;
  runBtn.textContent = isBusy ? "Generating..." : "Generate Player";
  if (teamGenerateBtn) teamGenerateBtn.textContent = isBusy ? "Generating..." : "Generate Team";
  statusEl.textContent = isBusy ? "Running generator" : "Idle";
}

function seasonLabelFromYear(yearText) {
  const y = Number(String(yearText || "").trim());
  if (!Number.isFinite(y)) return String(yearText || "").trim();
  const next = String((y + 1) % 100).padStart(2, "0");
  return `${y}-${next}`;
}

function average(values) {
  if (!values.length) return 0;
  return values.reduce((sum, x) => sum + Number(x || 0), 0) / values.length;
}

function clampScore(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return 25;
  return Math.max(25, Math.min(99, n));
}

function inferPositionBucket(positionText) {
  const pos = String(positionText || "").toUpperCase();
  if (pos.includes("C") || pos.includes("PF")) return "big";
  if (pos.includes("SF")) return "wing";
  return "guard";
}

function attrValue(attrMap, key) {
  const v = Number((attrMap || {})[key]);
  return Number.isFinite(v) ? v : 0;
}

function weightedScore(pairs) {
  const values = [];
  const weights = [];
  pairs.forEach(([val, weight]) => {
    const n = Number(val);
    const w = Number(weight);
    if (!Number.isFinite(n) || !Number.isFinite(w) || w <= 0) return;
    values.push(n * w);
    weights.push(w);
  });
  if (!weights.length) return 0;
  return values.reduce((a, b) => a + b, 0) / weights.reduce((a, b) => a + b, 0);
}

function computePositionAwareRatings(profile) {
  const family = profile?.familyScores || {};
  const attrs = profile?.attributes || {};
  const bucket = inferPositionBucket(profile?.info?.position || "");

  const finishing = Number(family.Finishing || 0);
  const shooting = Number(family.Shooting || 0);
  const playmaking = Number(family.Playmaking || 0);
  const defenseFamily = Number(family.Defense || 0);
  const physicalFamily = Number(family.Physical || 0);

  const spd = attrValue(attrs, "speed");
  const agi = attrValue(attrs, "agility");
  const str = attrValue(attrs, "strength");
  const vert = attrValue(attrs, "vertical");
  const stl = attrValue(attrs, "steal");
  const blk = attrValue(attrs, "block");
  const intDef = attrValue(attrs, "interior_defense");
  const perDef = attrValue(attrs, "perimeter_defense");
  const dreb = attrValue(attrs, "defensive_rebound");
  const passPerc = attrValue(attrs, "pass_perception");
  const passAcc = attrValue(attrs, "pass_accuracy");
  const passVision = attrValue(attrs, "pass_vision");
  const passIq = attrValue(attrs, "pass_iq");
  const shotIq = attrValue(attrs, "shot_iq");
  const helpDefIq = attrValue(attrs, "help_defense_iq");
  const defConsistency = attrValue(attrs, "defensive_consistency");
  const swb = attrValue(attrs, "speed_with_ball");
  const handle = attrValue(attrs, "ball_handle");
  const three = attrValue(attrs, "three_point_shot");
  const mid = attrValue(attrs, "mid_range_shot");
  const driveDunk = attrValue(attrs, "driving_dunk");
  const layup = attrValue(attrs, "driving_layup");
  const freeThrow = attrValue(attrs, "free_throw");

  let offenseRaw = 0;
  let defenseRaw = 0;
  let physicalRaw = 0;
  let offenseBonus = 0;
  let offenseFloor = 25;
  let defenseBonus = 0;
  let defenseFloor = 25;

  if (bucket === "guard") {
    offenseRaw = weightedScore([
      [playmaking, 0.3], [shooting, 0.27], [finishing, 0.13],
      [handle, 0.1], [swb, 0.1], [three, 0.1],
    ]);
    const creatorIndex = weightedScore([
      [playmaking, 0.3], [handle, 0.2], [swb, 0.12], [passVision, 0.14], [passAcc, 0.12], [shotIq, 0.12],
    ]);
    const scoringIndex = weightedScore([
      [shooting, 0.34], [three, 0.16], [mid, 0.12], [finishing, 0.18], [layup, 0.1], [freeThrow, 0.1],
    ]);
    offenseBonus = Math.min(
      8,
      Math.max(0, creatorIndex - 78) * 0.35 + Math.max(0, scoringIndex - 78) * 0.25,
    );
    offenseFloor = Math.max(playmaking - 1, creatorIndex - 2, scoringIndex - 3);
    defenseRaw = weightedScore([
      [defenseFamily, 0.45], [perDef, 0.2], [stl, 0.15], [passPerc, 0.1], [agi, 0.1],
    ]);
    defenseFloor = Math.max(defenseFamily - 1, weightedScore([[perDef, 0.4], [stl, 0.22], [passPerc, 0.2], [helpDefIq, 0.18]]) - 2);
    physicalRaw = weightedScore([
      [physicalFamily, 0.45], [spd, 0.2], [agi, 0.2], [staminaFromProfile(profile), 0.15],
    ]);
  } else if (bucket === "wing") {
    offenseRaw = weightedScore([
      [shooting, 0.24], [finishing, 0.2], [playmaking, 0.24],
      [mid, 0.09], [three, 0.09], [layup, 0.08], [shotIq, 0.06],
    ]);
    const wingCreator = weightedScore([
      [playmaking, 0.32], [handle, 0.14], [swb, 0.1], [passVision, 0.16], [passAcc, 0.12], [passIq, 0.08], [shotIq, 0.08],
    ]);
    const wingScoring = weightedScore([
      [shooting, 0.26], [finishing, 0.2], [mid, 0.12], [three, 0.12], [layup, 0.1], [freeThrow, 0.08], [shotIq, 0.12],
    ]);
    offenseBonus = Math.min(
      9,
      Math.max(0, wingScoring - 77) * 0.34 + Math.max(0, wingCreator - 78) * 0.33,
    );
    offenseFloor = Math.max(wingScoring - 1, wingCreator - 1, playmaking + 1, finishing - 1);
    defenseRaw = weightedScore([
      [defenseFamily, 0.3], [perDef, 0.18], [intDef, 0.14], [stl, 0.1], [blk, 0.08], [passPerc, 0.08], [helpDefIq, 0.07], [defConsistency, 0.05],
    ]);
    const wingDefenseIndex = weightedScore([
      [perDef, 0.24], [intDef, 0.2], [stl, 0.12], [blk, 0.08], [passPerc, 0.12], [helpDefIq, 0.14], [defConsistency, 0.1],
    ]);
    defenseBonus = Math.min(5, Math.max(0, wingDefenseIndex - 74) * 0.25 + Math.max(0, defConsistency - 75) * 0.12);
    const wingAwarenessFloor = weightedScore([
      [helpDefIq, 0.36], [defConsistency, 0.28], [perDef, 0.2], [passPerc, 0.16],
    ]) - 1;
    defenseFloor = Math.max(defenseFamily - 1, wingDefenseIndex - 1, wingAwarenessFloor);
    physicalRaw = weightedScore([
      [physicalFamily, 0.45], [spd, 0.15], [agi, 0.15], [str, 0.15], [vert, 0.1],
    ]);
  } else {
    offenseRaw = weightedScore([
      [finishing, 0.24], [shooting, 0.2], [playmaking, 0.18],
      [driveDunk, 0.1], [layup, 0.08], [attrValue(attrs, "post_control"), 0.1], [attrValue(attrs, "close_shot"), 0.1],
    ]);
    const postScoring = weightedScore([
      [finishing, 0.24], [attrValue(attrs, "post_control"), 0.15], [attrValue(attrs, "close_shot"), 0.14],
      [attrValue(attrs, "post_hook"), 0.1], [attrValue(attrs, "post_fade"), 0.08], [shotIq, 0.12],
      [shooting, 0.1], [playmaking, 0.07],
    ]);
    const bigCreator = weightedScore([
      [playmaking, 0.32], [passVision, 0.2], [passAcc, 0.16], [passIq, 0.12], [shotIq, 0.1], [handle, 0.1],
    ]);
    offenseBonus = Math.min(
      10,
      Math.max(0, postScoring - 77) * 0.28
      + Math.max(0, bigCreator - 79) * 0.34
      + Math.max(0, shooting - 78) * 0.24,
    );
    offenseFloor = Math.max(postScoring - 1, finishing - 1, bigCreator - 2, playmaking - 1, shooting - 2);
    defenseRaw = weightedScore([
      [defenseFamily, 0.42], [intDef, 0.17], [blk, 0.14], [dreb, 0.1], [perDef, 0.07], [passPerc, 0.1],
    ]);
    defenseFloor = Math.max(defenseFamily - 1, weightedScore([[intDef, 0.33], [blk, 0.22], [dreb, 0.18], [helpDefIq, 0.14], [defConsistency, 0.13]]) - 2);
    physicalRaw = weightedScore([
      [physicalFamily, 0.42], [str, 0.22], [vert, 0.12], [spd, 0.12], [agi, 0.12],
    ]);
  }

  // ── 2K-style scaling: boost raw composites to match 2K's higher rating range ──
  function twoKScale(raw) {
    if (raw >= 88) return Math.min(99, raw + 5 + Math.min(3, (raw - 88) * 0.4));
    if (raw >= 78) return raw + 5;
    if (raw >= 65) return raw + 4;
    if (raw >= 50) return raw + 3;
    return raw + 2;
  }

  const offenseBase = Math.round(clampScore(Math.max(offenseRaw + offenseBonus, offenseFloor)));
  const defenseBase = Math.round(clampScore(Math.max(defenseRaw + defenseBonus, defenseFloor)));
  const physicalBase = Math.round(clampScore(physicalRaw));

  const offense = Math.round(clampScore(twoKScale(offenseBase)));
  const defense = Math.round(clampScore(twoKScale(defenseBase)));
  const physical = Math.round(clampScore(twoKScale(physicalBase)));

  // ── Overall: position-weighted blend of scaled cards + impact bonus ──
  const overallRaw = bucket === "guard"
    ? weightedScore([[offense, 0.55], [defense, 0.12], [physical, 0.33]])
    : bucket === "wing"
      ? weightedScore([[offense, 0.40], [defense, 0.32], [physical, 0.28]])
      : weightedScore([[offense, 0.38], [defense, 0.34], [physical, 0.28]]);

  const impactBonus = bucket === "guard"
    ? Math.min(8, Math.max(0, offense - 88) * 0.7 + Math.max(0, physical - 82) * 0.3 + Math.max(0, offense - 93) * 0.5)
    : bucket === "wing"
      ? Math.min(8, Math.max(0, offense - 83) * 0.5 + Math.max(0, defense - 80) * 0.5 + Math.max(0, physical - 80) * 0.3)
      : Math.min(8, Math.max(0, offense - 80) * 0.55 + Math.max(0, defense - 78) * 0.5 + Math.max(0, physical - 78) * 0.35);

  const positionFloor = bucket === "guard"
    ? Math.max(offense - 2, playmaking - 2)
    : bucket === "wing"
      ? Math.max(offense - 2, defense - 3, physical - 3)
      : Math.max(offense - 2, defense - 3, physical - 3);

  const overallBoosted = overallRaw + impactBonus;
  const backendOvr = Number(profile?.ovr || 0);
  const stabilizedOverall = Math.max(overallBoosted, positionFloor, backendOvr || 0);

  return {
    offense,
    defense,
    physical,
    overall: Math.round(clampScore(stabilizedOverall)),
  };
}

function staminaFromProfile(profile) {
  return attrValue(profile?.attributes || {}, "stamina");
}

function gradeFromAverage(value) {
  if (value >= 94) return "A+";
  if (value >= 88) return "A";
  if (value >= 82) return "A-";
  if (value >= 76) return "B+";
  if (value >= 70) return "B";
  if (value >= 64) return "B-";
  if (value >= 58) return "C+";
  return "C";
}

function ovrTierClass(ovr) {
  if (ovr >= 95) return "ovr-elite";
  if (ovr >= 90) return "ovr-star";
  if (ovr >= 85) return "ovr-starter";
  if (ovr >= 78) return "ovr-rotation";
  if (ovr >= 70) return "ovr-bench";
  return "ovr-end";
}

function ovrTierLabel(ovr) {
  if (ovr >= 95) return "ELITE";
  if (ovr >= 90) return "ALL-STAR";
  if (ovr >= 85) return "STARTER";
  if (ovr >= 78) return "ROTATION";
  if (ovr >= 70) return "BENCH";
  return "END OF BENCH";
}

function attrBarColor(value) {
  if (value >= 90) return "var(--team-primary)";
  if (value >= 80) return "#6ee7b7";
  if (value >= 70) return "#89b4fa";
  if (value >= 60) return "#f0b236";
  if (value >= 50) return "#ffa089";
  return "#ff6b6b";
}

function byName(groupMap) {
  return Object.entries(groupMap || {}).map(([title, items]) => ({
    title,
    items: Array.isArray(items) ? items : [],
  }));
}

const BADGE_TIER_ORDER = ["Legend", "HOF", "Gold", "Silver", "Bronze"];

function normalizeBadgeTier(value) {
  const text = String(value || "").trim().toLowerCase();
  if (!text) return "Bronze";
  if (text === "legend") return "Legend";
  if (text === "hof" || text === "hall of fame") return "HOF";
  if (text === "gold") return "Gold";
  if (text === "silver") return "Silver";
  return "Bronze";
}

function badgeSlug(name) {
  return String(name || "")
    .toLowerCase()
    .replace(/&/g, " and ")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function badgeImagePath(name) {
  const slug = badgeSlug(name);
  const custom = {
    "boxout-beast": "nba-2k-boxout-beast-badge.jpg",
    "break-starter": "nba-2k-breakstarter-badge-1024x577.jpg",
    challenger: "nba-2k-challenger-badge.jpg",
    deadeye: "nba-2k-deadeye-badge.jpg",
    dimer: "nba-2k-dimer-badge.jpg",
    "float-game": "nba-2k-float-game-badge.jpg",
    "handles-for-days": "nba-2k-handles-for-days-badge.jpg",
    "high-flying-denier": "nba-2k-high-flying-denier-badge.jpg",
    "lightning-launch": "nba-2k-lightning-launch-badge.jpg",
    "limitless-range": "nba-2k-limitless-range-badge.jpg",
    "mini-marksman": "nba-2k-mini-marksman-badge.jpg",
    "paint-patroller": "nba-2k-paint-patroller-badge.jpg",
    "paint-prodigy": "nba-2k-paint-prodigy-badge.jpg",
    "pick-dodger": "nba-2k-pick-dodger-badge.jpg",
    "post-lockdown": "nba-2k-post-lockdown-badge.jpg",
    "post-powerhouse": "nba-2k-post-powerhouse-badge.jpg",
    "post-up-poet": "nba-2k-post-up-poet-badge.jpg",
    posterizer: "nba-2k-posterizer-badge.jpg",
    "rise-up": "nba-2k-rise-up-badge.jpg",
    "shifty-shooter": "nba-2k-shifty-shooter-badge.jpg",
    "slippery-off-ball": "nba-2k-slippery-off-ball-badge.jpg",
    "versatile-visionary": "nba-2k-versatile-visionary-badge.jpg",
  };
  const fileName = custom[slug] || `nba-2k-${slug}-badge-1024x577.jpg`;
  return `../../Badges/${encodeURIComponent(fileName)}`;
}

function flattenBadgesByTier(badgeGroups) {
  const grouped = {
    Bronze: [],
    Silver: [],
    Gold: [],
    HOF: [],
    Legend: [],
  };

  Object.entries(badgeGroups || {}).forEach(([section, items]) => {
    (Array.isArray(items) ? items : []).forEach((item) => {
      const tier = normalizeBadgeTier(item?.value);
      grouped[tier].push({
        ...item,
        section,
        tier,
      });
    });
  });

  BADGE_TIER_ORDER.forEach((tier) => {
    grouped[tier] = grouped[tier].sort((a, b) => Number(b?.score || 0) - Number(a?.score || 0));
  });

  return grouped;
}

function renderBadgesPanel() {
  const tiered = flattenBadgesByTier(currentProfile?.badgeGroups || {});
  panelTitleEl.textContent = "Badges";
  panelGridEl.classList.remove("single-column");
  panelGridEl.classList.add("badges-mode");

  const filter = panelFilterValue.toLowerCase();

  panelGridEl.innerHTML = BADGE_TIER_ORDER.map((tier) => {
    const tierKey = tier.toLowerCase();
    const badges = tiered[tier] || [];
    const filteredBadges = filter
      ? badges.filter((b) => (b.name || "").toLowerCase().includes(filter) || (b.section || "").toLowerCase().includes(filter) || (b.description || "").toLowerCase().includes(filter))
      : badges;
    const cards = filteredBadges.length
      ? filteredBadges.map((badge) => {
        const imagePath = badgeImagePath(badge.name || "badge");
        const badgeName = badge.name || "Badge";
        const description = badge.description || "";
        const section = badge.section || "General";
        const score = Number.isFinite(Number(badge.score)) ? Number(badge.score).toFixed(1) : "0.0";
        const displayName = filter ? highlightText(badgeName, filter) : badgeName;
        return `
          <article class="badge-card tier-${tierKey}" data-search="${(badgeName + " " + section + " " + description).toLowerCase()}">
            <div class="badge-image-wrap tier-${tierKey}">
              <img class="badge-image tier-${tierKey}" src="${imagePath}" alt="${badgeName} badge" onerror="this.classList.add('hidden'); this.nextElementSibling.classList.remove('hidden');" />
              <div class="badge-image-fallback hidden">${badgeName}</div>
            </div>
            <div class="badge-body">
              <h4>${displayName}</h4>
              <p>${section} · ${tier} · Score ${score}</p>
              <small>${description}</small>
            </div>
          </article>
        `;
      }).join("")
      : badges.length
        ? `<div class="badge-empty empty-state"><span class="empty-state-icon">🔍</span><span class="empty-state-text">No badges match "<strong>${filter}</strong>"</span></div>`
        : '<div class="badge-empty empty-state"><span class="empty-state-icon">🏅</span><span class="empty-state-text"><strong>No badges in this tier</strong></span><span class="empty-state-hint">This player hasn\'t earned any badges at this level yet.</span></div>';

    const hiddenClass = filter && filteredBadges.length === 0 && badges.length > 0 ? " filtered-out" : "";
    return `
      <article class="metric-card badge-tier-section tier-${tierKey}${hiddenClass}">
        <h3>${tier} <span>${filteredBadges.length} / ${badges.length}</span></h3>
        <div class="badge-grid">${cards}</div>
      </article>
    `;
  }).join("");
}

function renderPanelGrid() {
  if (!currentProfile) return;
  if (activeTab === "badges") {
    renderBadgesPanel();
    return;
  }

  const groups = activeTab === "attributes"
    ? byName(currentProfile.attributeGroups)
    : byName(currentProfile.tendencyGroups);
  const groupedFullWidthMode = activeTab === "tendencies" || activeTab === "attributes";

  panelGridEl.classList.remove("badges-mode");
  panelGridEl.classList.toggle("single-column", groupedFullWidthMode);

  panelTitleEl.textContent =
    activeTab === "attributes"
      ? "Attributes (Generated)"
      : "Tendencies (Generated)";

  const filter = panelFilterValue.toLowerCase();

  if (activeTab === "attributes") {
    panelGridEl.innerHTML = groups
      .map((group) => {
        const filteredItems = filter
          ? group.items.filter((item) => (item.name || item.key || "").toLowerCase().includes(filter))
          : group.items;
        const rows = filteredItems
          .map((item) => {
            const val = Number(item.value ?? 0);
            const pct = Math.round((Math.max(0, Math.min(99, val)) / 99) * 100);
            const color = attrBarColor(val);
            const displayName = filter ? highlightText(item.name || item.key || "Item", filter) : (item.name || item.key || "Item");
            return `
              <div class="attr-bar-row" data-search="${(item.name || item.key || "").toLowerCase()}">
                <span class="attr-bar-name">${displayName}</span>
                <div class="attr-bar-track">
                  <div class="attr-bar-fill" style="--bar-width:${pct}%;background:${color}"></div>
                </div>
                <strong class="attr-bar-value">${val}</strong>
              </div>`;
          })
          .join("");
        const hiddenClass = filter && filteredItems.length === 0 && group.items.length > 0 ? " filtered-out" : "";
        return `
          <article class="metric-card${hiddenClass}">
            <h3>${group.title}</h3>
            <div class="attr-bar-list">${rows || (group.items.length ? `<div class="metric-row"><span>No matches for "${panelFilterValue}"</span></div>` : '<div class="metric-row"><span>Empty</span><strong>0</strong></div>')}</div>
          </article>
        `;
      })
      .join("");
    requestAnimationFrame(() => {
      const fills = panelGridEl.querySelectorAll(".attr-bar-fill");
      fills.forEach((fill, i) => {
        setTimeout(() => fill.classList.add("animate-in"), i * 20);
      });
    });
  } else {
    panelGridEl.innerHTML = groups
      .map((group) => {
        const filteredItems = filter
          ? group.items.filter((item) => (item.name || item.key || "").toLowerCase().includes(filter))
          : group.items;
        const rows = filteredItems
          .map((item) => {
            const displayName = filter ? highlightText(item.name || item.key || "Item", filter) : (item.name || item.key || "Item");
            return `<div class="metric-row" data-search="${(item.name || item.key || "").toLowerCase()}"><span>${displayName}</span><strong>${item.value ?? 0}</strong></div>`;
          })
          .join("");
        const hiddenClass = filter && filteredItems.length === 0 && group.items.length > 0 ? " filtered-out" : "";
        return `
          <article class="metric-card tendency-card${hiddenClass}">
            <h3>${group.title}</h3>
            <div class="metric-list">${rows || (group.items.length ? `<div class="metric-row"><span>No matches for "${panelFilterValue}"</span></div>` : '<div class="metric-row"><span>Empty</span><strong>0</strong></div>')}</div>
          </article>
        `;
      })
      .join("");
  }
}

const META_ATTRS = new Set([
  "intangibles", "hustle", "potential", "overalldurability", "meta",
  "drawfoul", "hands", "offensiveconsistency", "defensiveconsistency",
]);

function normalizeAttrName(raw) {
  return String(raw || "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .replace(/\bIq\b/g, "IQ");
}

function dedupKey(raw) {
  return String(raw || "").toLowerCase().replace(/[_\s]+/g, "");
}

function renderVsSheet(profile, sheetAttrs, displayAttrs) {
  const generated = profile?.attributes || {};
  const displayMap = displayAttrs || {};

  const SHEET_TO_GENERATED = {
    "driving_layup": "driving_layup",
    "standing_dunk": "standing_dunk",
    "driving_dunk": "driving_dunk",
    "close_shot": "close_shot",
    "mid_range_shot": "mid_range_shot",
    "three_point_shot": "three_point_shot",
    "free_thow": "free_throw",
    "post_hook": "post_hook",
    "post_fade": "post_fade",
    "post_control": "post_control",
    "draw_foul": "draw_foul",
    "shot_iq": "shot_iq",
    "ball_handle": "ball_handle",
    "speed_with_ball": "speed_with_ball",
    "hands": "hands",
    "pass_accuracy": "pass_accuracy",
    "pass_iq": "pass_iq",
    "pass_vision": "pass_vision",
    "offensive_consistency": "offensive_consistency",
    "interior_defense": "interior_defense",
    "perimeter_defense": "perimeter_defense",
    "steal": "steal",
    "block": "block",
    "offensive_rebound": "offensive_rebound",
    "defensive_rebound": "defensive_rebound",
    "help_defense_iq": "help_defense_iq",
    "pass_perception": "pass_perception",
    "defensive_consistency": "defensive_consistency",
    "speed": "speed",
    "agility": "agility",
    "strength": "strength",
    "vertical": "vertical",
    "stamina": "stamina",
    "intangibles": "intangibles",
    "hustle": "hustle",
    "overall_durability": "overall_durability",
    "potential": "potential",
  };

  const DISPLAY_OVERRIDE = {
    "free_thow": "Free Throw",
  };

  const rows = Object.entries(sheetAttrs).map(([sheetKey, sheetVal]) => {
    const genKey = SHEET_TO_GENERATED[sheetKey] || sheetKey;
    const genVal = Number(generated[genKey] ?? generated[sheetKey] ?? 0);
    const sheetNum = Number(sheetVal);
    const diff = genVal - sheetNum;
    const diffClass = diff > 0 ? "vs-better" : diff < 0 ? "vs-worse" : "vs-equal";
    const diffLabel = diff === 0 ? "=" : diff > 0 ? `+${diff}` : `${diff}`;

    // Get display name: prefer original display key
    const displayName = Object.entries(displayMap).find(([k]) => {
      const norm = k.replace(/[^a-z0-9]/gi, "_").replace(/_+/g, "_").toLowerCase().replace(/^_|_$/g, "");
      return norm === sheetKey || norm === genKey;
    })?.[0] || DISPLAY_OVERRIDE[sheetKey] || normalizeAttrName(sheetKey);

    const genPct = Math.round((Math.max(0, Math.min(99, genVal)) / 99) * 100);
    const sheetPct = Math.round((Math.max(0, Math.min(99, sheetNum)) / 99) * 100);
    const genColor = attrBarColor(genVal);
    const sheetColor = attrBarColor(sheetNum);

    return `
      <div class="vs-sheet-row">
        <span class="vs-sheet-name">${displayName}</span>
        <div class="vs-sheet-bars">
          <div class="vs-sheet-bar-wrap">
            <div class="vs-sheet-bar gen-bar" style="--bar-w:${genPct}%;background:${genColor}"></div>
            <span class="vs-sheet-val gen-val">${genVal}</span>
          </div>
          <div class="vs-sheet-bar-wrap">
            <div class="vs-sheet-bar sheet-bar" style="--bar-w:${sheetPct}%;background:${sheetColor}"></div>
            <span class="vs-sheet-val sheet-val">${sheetNum}</span>
          </div>
        </div>
        <span class="vs-sheet-diff ${diffClass}">${diffLabel}</span>
      </div>`;
  }).join("");

  const totalDiff = Object.entries(sheetAttrs).reduce((sum, [sheetKey, sheetVal]) => {
    const genKey = SHEET_TO_GENERATED[sheetKey] || sheetKey;
    const genVal = Number(generated[genKey] ?? generated[sheetKey] ?? 0);
    return sum + Math.abs(genVal - Number(sheetVal));
  }, 0);
  const attrCount = Object.keys(sheetAttrs).length;
  const avgDiff = attrCount > 0 ? (totalDiff / attrCount).toFixed(1) : "0.0";

  panelTitleEl.textContent = "Generated vs Sheet";
  panelGridEl.innerHTML = `
    <div class="vs-sheet-legend">
      <span class="vs-legend-gen">Generated</span>
      <span class="vs-legend-sheet">Sheet</span>
      <span class="vs-legend-avg">Avg diff: ${avgDiff}</span>
    </div>
    <div class="vs-sheet-list">${rows}</div>`;
}

function filterStrengthsWeaknesses(items, maxLen = 6) {
  const seen = new Set();
  const result = [];
  for (const raw of items) {
    const key = dedupKey(raw);
    if (!key || seen.has(key) || META_ATTRS.has(key)) continue;
    seen.add(key);
    result.push(normalizeAttrName(raw));
    if (result.length >= maxLen) break;
  }
  return result;
}

function highlightText(text, term) {
  if (!term || !text) return text;
  const idx = text.toLowerCase().indexOf(term);
  if (idx === -1) return text;
  return text.slice(0, idx) + "<mark>" + text.slice(idx, idx + term.length) + "</mark>" + text.slice(idx + term.length);
}

function formatStatValue(key, value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return key === "GP" || key === "gp" ? "0" : "0.0";
  const upperKey = String(key).toUpperCase();
  if (upperKey === "FG%" || upperKey === "3PT%" || upperKey === "FT%") {
    const pct = n <= 1 ? n * 100 : n;
    return pct.toFixed(1);
  }
  if (upperKey === "GP") return String(Math.round(n));
  return n.toFixed(1);
}

function metricListHtml(snapshot) {
  const s = snapshot || {};
  const rows = [
    ["PTS", s.pts], ["REB", s.reb], ["AST", s.ast], ["STEAL", s.stl], ["BLK", s.blk],
    ["FG%", s.fgPct], ["3PT%", s.fg3Pct],
    ...(s.ftPct != null ? [["FT%", s.ftPct]] : []),
    ["GP", s.gp],
  ];
  return rows.map(([k, v]) => `<div class="mini-stat"><span>${k}</span><strong>${formatStatValue(k, v)}</strong></div>`).join("");
}

function renderProfile(profile, options = {}) {
  profileBackTarget = options.backTarget === "team" ? "team" : "dashboard";
  currentProfile = profile;
  activeTab = "attributes";
  panelFilterValue = "";
  if (panelFilterEl) panelFilterEl.value = "";

  const info = profile.info || {};
  applyTeamTheme(info.team || "");
  const cardRatings = computePositionAwareRatings(profile);
  const tier = ovrTierClass(cardRatings.overall);
  const tierLabel = ovrTierLabel(cardRatings.overall);

  const heroEl = document.getElementById("profileHero");
  const photoSrc = info.photoUrl || "";
  const initials = (info.name || "Player").split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase();
  const rolesHtml = (profile.roles || []).map((r) => {
    const code = String(r.code || r).trim();
    const def = ROLE_DEFINITIONS[code] || null;
    return def
      ? `<span class="profile-hero-role tooltip" data-tip="${def}">${code}</span>`
      : `<span class="profile-hero-role">${code}</span>`;
  }).join("");

  const ovrColor = cardRatings.overall >= 90 ? "#f0b236" : cardRatings.overall >= 80 ? "#2ba6ff" : "#31c7b2";

  heroEl.innerHTML = `
    <div class="profile-hero-bg"></div>
    <div class="profile-hero-content">
      <div class="profile-hero-photo-wrap">
        ${photoSrc
          ? `<img class="profile-hero-photo" src="${photoSrc}" alt="${info.name || "Player"}" onerror="this.outerHTML='<div class=\\'profile-hero-photo-fallback\\'>${initials}</div>'" />`
          : `<div class="profile-hero-photo-fallback">${initials}</div>`}
      </div>
      <div class="profile-hero-info">
        <h1 class="profile-hero-name">${info.name || "Player"}</h1>
        <div class="profile-hero-meta">
          <span class="profile-hero-team">${info.team || "N/A"}</span>
          <span class="profile-hero-pos">${info.position || "N/A"}${info.height ? ` · ${info.height}` : ""}${info.weight ? ` · ${info.weight} lbs` : ""}</span>
        </div>
        <div class="profile-hero-roles">${rolesHtml}</div>
      </div>
      <div class="profile-hero-scores">
        <div class="profile-hero-score off">
          <span class="profile-hero-score-label">OFF</span>
          <span class="profile-hero-score-value">${cardRatings.offense}</span>
        </div>
        <div class="profile-hero-score def">
          <span class="profile-hero-score-label">DEF</span>
          <span class="profile-hero-score-value">${cardRatings.defense}</span>
        </div>
        <div class="profile-hero-score phy">
          <span class="profile-hero-score-label">PHY</span>
          <span class="profile-hero-score-value">${cardRatings.physical}</span>
        </div>
        <div class="profile-hero-ovr">
          <svg viewBox="0 0 120 120">
            <circle cx="60" cy="60" r="52" fill="none" stroke="rgba(255,255,255,0.1)" stroke-width="5" />
            <circle cx="60" cy="60" r="52" fill="none" stroke="${ovrColor}" stroke-width="5" stroke-linecap="round"
              stroke-dasharray="${Math.round(cardRatings.overall * 3.267)} 326.7"
              transform="rotate(-90 60 60)" />
          </svg>
          <div class="profile-hero-ovr-inner">
            <span class="profile-hero-ovr-num">${cardRatings.overall}</span>
            <span class="profile-hero-ovr-tier">${tierLabel}</span>
          </div>
        </div>
      </div>
    </div>
  `;

  // Show "vs Sheet" tab only for 2025-26 season profiles
  if (tabVsSheetEl) {
    const season = String(info.season || "").trim();
    const is2526 = season === "2025-26" || season === "2025" || season.startsWith("2025");
    tabVsSheetEl.classList.toggle("hidden", !is2526);
  }

  const radarWrap = document.getElementById("radarChartWrap");
  const radarSvg = document.getElementById("radarChartSvg");
  renderRadarChart(radarSvg, profile, cardRatings);

  const statCompWrap = document.getElementById("statComparisonWrap");
  renderStatComparison(statCompWrap, profile);

  const swEl = document.getElementById("profileSW");
  const strengths = filterStrengthsWeaknesses(profile.strengths || [], 5);
  const weaknesses = filterStrengthsWeaknesses(profile.weaknesses || [], 5);
  const swItems = strengths.map((s, i) => `<div class="profile-sw-item" style="animation-delay:${i * 60}ms"><span class="profile-sw-icon">★</span><span>${s}</span></div>`).join("");
  const wkItems = weaknesses.map((w, i) => `<div class="profile-sw-item" style="animation-delay:${i * 60}ms"><span class="profile-sw-icon">△</span><span>${w}</span></div>`).join("");
  swEl.innerHTML = `
    <div class="profile-sw-card strengths">
      <h4>Strengths</h4>
      ${swItems}
    </div>
    <div class="profile-sw-card weaknesses">
      <h4>Weaknesses</h4>
      ${wkItems}
    </div>
  `;

  tabAttributesEl.classList.add("active");
  tabTendenciesEl.classList.remove("active");
  tabBadgesEl.classList.remove("active");
  if (tabVsSheetEl) tabVsSheetEl.classList.remove("active");
  renderPanelGrid();

  const backBtn = document.getElementById("backBtn");
  const jsonBtn = document.getElementById("jsonBtn");
  const excelBtn = document.getElementById("excelBtn");
  if (backBtn) {
    backBtn.textContent = profileBackTarget === "team" ? "← Back to Team" : "← Back to Dashboard";
    backBtn.onclick = () => {
      if (profileBackTarget === "team") showTeamPage();
      else showDashboard();
    };
  }

  if (jsonBtn) {
    jsonBtn.onclick = async () => {
      if (!currentProfile) return;
      statusEl.textContent = "Exporting 2K JSON";
      const result = await window.nba2kDesktop.exportPlayerJson({ profile: currentProfile });
      statusEl.textContent = result?.ok ? "Export completed" : `Export failed: ${result?.error || "Unknown error"}`;
    };
  }

  if (excelBtn) {
    excelBtn.onclick = () => {
      statusEl.textContent = "Excel export is not implemented yet.";
    };
  }

  if (document.getElementById("exportImgBtn")) {
    document.getElementById("exportImgBtn").onclick = exportProfileAsImage;
  }

  showProfile();
}

function renderRadarChart(svg, profile, ratings) {
  if (!svg) return;
  const families = profile.familyScores || {};
  const attrs = profile.attributes || {};

  const postAttrs = ["post_control", "post_hook", "post_fade", "close_shot", "standing_dunk"];
  const postValues = postAttrs.map((a) => Number(attrs[a] || 0)).filter((v) => v > 0);
  const postScore = postValues.length ? postValues.reduce((s, v) => s + v, 0) / postValues.length : 0;

  const axes = [
    { label: "FIN", value: Number(families.Finishing || 0), color: "#ff8453" },
    { label: "SHT", value: Number(families.Shooting || 0), color: "#ffa089" },
    { label: "PMK", value: Number(families.Playmaking || 0), color: "#f0b236" },
    { label: "DEF", value: Number(families.Defense || 0), color: "#2ba6ff" },
    { label: "PHY", value: Number(families.Physical || 0), color: "#31c7b2" },
    { label: "PST", value: Math.round(postScore), color: "#ba954c" },
  ];

  const cx = 140, cy = 140, r = 90;
  const n = axes.length;
  let svgContent = "";

  for (let level = 1; level <= 4; level++) {
    const lr = (r * level) / 4;
    const pts = [];
    for (let i = 0; i < n; i++) {
      const angle = (Math.PI * 2 * i) / n - Math.PI / 2;
      pts.push(`${cx + lr * Math.cos(angle)},${cy + lr * Math.sin(angle)}`);
    }
    svgContent += `<polygon class="radar-ring" points="${pts.join(" ")}" />`;
  }

  for (let i = 0; i < n; i++) {
    const angle = (Math.PI * 2 * i) / n - Math.PI / 2;
    const x = cx + r * Math.cos(angle);
    const y = cy + r * Math.sin(angle);
    svgContent += `<line class="radar-axis-line" x1="${cx}" y1="${cy}" x2="${x}" y2="${y}" />`;
    const lx = cx + (r + 18) * Math.cos(angle);
    const ly = cy + (r + 18) * Math.sin(angle);
    svgContent += `<text class="radar-label-text" x="${lx}" y="${ly}">${axes[i].label}</text>`;
    const vx = cx + (r + 34) * Math.cos(angle);
    const vy = cy + (r + 34) * Math.sin(angle);
    svgContent += `<text class="radar-value-text" x="${vx}" y="${vy}" fill="${axes[i].color}">${Math.round(axes[i].value)}</text>`;
  }

  const dataPts = axes.map((a, i) => {
    const angle = (Math.PI * 2 * i) / n - Math.PI / 2;
    const dr = (r * Math.min(a.value, 99)) / 99;
    return `${cx + dr * Math.cos(angle)},${cy + dr * Math.sin(angle)}`;
  }).join(" ");

  svgContent += `<polygon class="radar-fill-shape" points="${dataPts}" />`;

  svg.innerHTML = svgContent;
}

function renderStatComparison(wrap, profile) {
  if (!wrap) return;
  const blocks = profile.statBlocks || {};
  const current = blocks.current || {};
  const career = blocks.career || {};

  const stats = [
    { key: "pts", label: "Points" },
    { key: "reb", label: "Rebounds" },
    { key: "ast", label: "Assists" },
    { key: "stl", label: "Steals" },
    { key: "blk", label: "Blocks" },
  ];

  const maxVal = Math.max(
    ...stats.map((s) => Math.max(Number(current[s.key] || 0), Number(career[s.key] || 0))),
    1
  );

  const rows = stats.map((s) => {
    const cur = Number(current[s.key] || 0);
    const car = Number(career[s.key] || 0);
    const curPct = (cur / maxVal) * 100;
    const carPct = (car / maxVal) * 100;
    const curDisplay = formatStatValue(s.key.toUpperCase(), cur);
    const carDisplay = formatStatValue(s.key.toUpperCase(), car);
    return `
      <div class="stat-comp-row">
        <div class="stat-comp-header">
          <span class="stat-comp-name">${s.label}</span>
          <span class="stat-comp-values">
            <span class="stat-comp-current">${curDisplay}</span>
            <span class="stat-comp-career"> / ${carDisplay}</span>
          </span>
        </div>
        <div class="stat-comp-bar">
          <div class="stat-comp-bar-fill" style="width:0%" data-target="${curPct}"></div>
          <div class="stat-comp-bar-career" style="left:${carPct}%"></div>
        </div>
      </div>
    `;
  }).join("");

  wrap.innerHTML = `<h4>Season vs Career</h4>${rows}`;

  requestAnimationFrame(() => {
    wrap.querySelectorAll(".stat-comp-bar-fill[data-target]").forEach((fill) => {
      fill.style.width = `${fill.dataset.target}%`;
    });
  });
}

async function exportProfileAsImage() {
  if (!currentProfile) return;
  const info = currentProfile.info || {};
  const ratings = computePositionAwareRatings(currentProfile);
  const attrs = currentProfile.attributeGroups || {};
  const badgeGroups = currentProfile.badgeGroups || {};

  const canvas = document.createElement("canvas");
  const W = 800;
  const H = 1000;
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext("2d");

  ctx.fillStyle = "#090f1d";
  ctx.fillRect(0, 0, W, H);

  const team = String(info.team || "").toUpperCase();
  const colors = TEAM_THEME[team] || ["#53c2ff", "#ff6a3d"];
  ctx.fillStyle = colors[0] || "#53c2ff";
  ctx.fillRect(0, 0, W, 4);

  ctx.fillStyle = "#f4f8ff";
  ctx.font = "bold 14px Sora, sans-serif";
  ctx.fillText("ATD 2K APP — Generated Profile", 24, 30);

  ctx.fillStyle = "#f4f8ff";
  ctx.font = "bold 42px Bebas Neue, Sora, sans-serif";
  ctx.fillText(info.name || "Player", 24, 80);

  ctx.font = "16px Sora, sans-serif";
  ctx.fillStyle = "#9cb5dc";
  ctx.fillText(`${info.team || ""} · ${info.position || ""} · OVR ${ratings.overall}`, 24, 108);

  const scoreCards = [
    { label: "OFF", value: ratings.offense, color: "#ff8453" },
    { label: "DEF", value: ratings.defense, color: "#2ba6ff" },
    { label: "PHY", value: ratings.physical, color: "#31c7b2" },
  ];

  const cardW = 220;
  const gap = 20;
  const startX = 24;
  scoreCards.forEach((sc, i) => {
    const x = startX + i * (cardW + gap);
    const y = 130;
    ctx.fillStyle = "rgba(255,255,255,0.06)";
    ctx.beginPath();
    ctx.roundRect(x, y, cardW, 70, 12);
    ctx.fill();
    ctx.fillStyle = sc.color;
    ctx.font = "bold 36px Bebas Neue, Sora, sans-serif";
    ctx.fillText(String(sc.value), x + 16, y + 48);
    ctx.fillStyle = "#9cb5dc";
    ctx.font = "12px Sora, sans-serif";
    ctx.fillText(sc.label, x + 16, y + 22);
  });

  let y = 230;
  ctx.fillStyle = "#9ad7ff";
  ctx.font = "bold 11px Sora, sans-serif";
  ctx.fillText("ATTRIBUTES", 24, y);
  y += 16;

  Object.entries(attrs).forEach(([group, items]) => {
    ctx.fillStyle = "#9cb5dc";
    ctx.font = "bold 12px Sora, sans-serif";
    ctx.fillText(group, 24, y);
    y += 16;
    items.forEach((item) => {
      const val = Number(item.value ?? 0);
      const pct = Math.max(0, Math.min(1, (val - 25) / 70));
      ctx.fillStyle = "#c6d8f6";
      ctx.font = "12px Sora, sans-serif";
      ctx.fillText(`${item.name || item.key}`, 32, y);
      ctx.fillStyle = "rgba(171,199,255,0.08)";
      ctx.fillRect(240, y - 8, 300, 8);
      ctx.fillStyle = attrBarColor(val);
      ctx.fillRect(240, y - 8, 300 * pct, 8);
      ctx.fillStyle = "#f4f8ff";
      ctx.font = "bold 12px Sora, sans-serif";
      ctx.fillText(String(val), 550, y);
      y += 18;
    });
    y += 6;
  });

  const badgeCount = Object.values(badgeGroups).reduce((s, items) => s + (Array.isArray(items) ? items.length : 0), 0);
  if (badgeCount > 0) {
    y += 8;
    ctx.fillStyle = "#9ad7ff";
    ctx.font = "bold 11px Sora, sans-serif";
    ctx.fillText(`BADGES (${badgeCount})`, 24, y);
    y += 18;
    const badges = [];
    Object.entries(badgeGroups).forEach(([section, items]) => {
      (items || []).forEach((b) => badges.push({ ...b, section }));
    });
    badges.sort((a, b) => Number(b?.score || 0) - Number(a?.score || 0));
    badges.slice(0, 12).forEach((b) => {
      const tier = String(b.value || "").toLowerCase();
      const tierColor = tier === "legend" ? "#ff0000" : tier === "hof" ? "#7300ff" : tier === "gold" ? "#ffbb00" : tier === "silver" ? "#bfc9d6" : "#d08856";
      ctx.fillStyle = tierColor;
      ctx.font = "bold 12px Sora, sans-serif";
      ctx.fillText(`★ ${b.name || "Badge"} (${tier.toUpperCase()})`, 32, y);
      y += 16;
    });
  }

  ctx.fillStyle = "#555";
  ctx.font = "10px Sora, sans-serif";
  ctx.fillText("Generated by ATD 2K APP", 24, H - 16);

  canvas.toBlob((blob) => {
    if (!blob) return;
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${(info.name || "player").replace(/[^a-zA-Z0-9 ]/g, "")}_2K26_Profile.png`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast("Player card saved as PNG.", "success", 3000);
  }, "image/png");
}

async function runGenerator() {
  const player = (selectedPlayer?.name || playerSearchEl.value || "").trim();
  const season = seasonLabelFromYear(seasonEl.value);
  const modeEl = document.querySelector('input[name="genMode"]:checked');
  const mode = modeEl ? modeEl.value : "ml";

  if (!player) {
    showToast("Please search and select a player first.", "info", 3000);
    outputEl.textContent = "Please select a player first.";
    outputEl.classList.remove("hidden");
    return;
  }

  setBusy(true);
  outputEl.classList.add("hidden");
  outputEl.textContent = "Running...";

  try {
    const result = await window.nba2kDesktop.generateProfile({ player, season, mode });
    if (!result.ok) {
      outputEl.textContent = [
        "Generation failed.",
        result.error || "Unknown error",
        result.stderr || "",
        result.stdout || "",
      ].filter(Boolean).join("\n\n");
      statusEl.textContent = "Failed";
      return;
    }

    renderProfile(result.profile || {}, { backTarget: "dashboard" });
    outputEl.classList.add("hidden");
    statusEl.textContent = "Completed";
    const info = result.profile?.info || {};
    saveRecentPlayer({
      name: info.name || player,
      team: info.team || selectedPlayer?.team || "",
      position: info.position || selectedPlayer?.position || "",
      season: info.season || season,
    });
    renderRecentPlayers();
    showToast(`${info.name || player} profile generated successfully.`, "success", 3000);
  } catch (err) {
    outputEl.textContent = `Unexpected error:\n${String(err?.message || err)}`;
    statusEl.textContent = "Error";
  } finally {
    runBtn.disabled = false;
    runBtn.textContent = "Generate Player";
  }
}

async function runTeamGenerator() {
  const team = String(teamSelectEl?.value || "").trim().toUpperCase();
  const season = seasonLabelFromYear(teamSeasonEl.value);
  const modeEl = document.querySelector('input[name="genMode"]:checked');
  const mode = modeEl ? modeEl.value : "ml";

  if (!team) {
    teamStatusEl.textContent = "Please select a team.";
    return;
  }

  setBusy(true);
  applyTeamTheme(team);
  teamStatusEl.textContent = `Loading ${team} roster for ${season}...`;
  teamResultsEl.innerHTML = "";
  const dashboardEl = document.getElementById("teamDashboard");
  if (dashboardEl) dashboardEl.classList.add("hidden");

  try {
    lastTeamExportPayload = null;
    if (teamExportJsonBtn) teamExportJsonBtn.disabled = true;
    if (teamExportExcelBtn) teamExportExcelBtn.disabled = true;

    const roster = await window.nba2kDesktop.getTeamRoster({ team, season });
    if (!roster?.ok) {
      teamStatusEl.textContent = `Team generation failed: ${roster?.error || "Unknown error"}`;
      return;
    }

    const players = roster.players || [];
    if (!players.length) {
      teamStatusEl.textContent = `No players found for ${team} in ${season}.`;
      return;
    }

    resetTeamProgress();

    teamStatusEl.textContent = `Generating ${players.length} players...`;
    if (teamProgressWrap) {
      teamProgressWrap.classList.remove("hidden");
      teamProgressFill.style.width = "0%";
      teamProgressText.textContent = `0 / ${players.length}`;
    }

    const result = await window.nba2kDesktop.generateTeamBatch({
      players: players.map((p) => p.name),
      season,
    });

    if (!result?.ok || !result.profiles) {
      teamStatusEl.textContent = `Team generation failed: ${result?.error || "Unknown error"}`;
      return;
    }

    const profiles = result.profiles;
    const cards = new Array(players.length).fill(null);
    const failures = [];

    for (let i = 0; i < players.length; i++) {
      const p = players[i];
      const profile = profiles.find((pr) => pr.ok && pr.profile?.info?.name?.toLowerCase() === p.name.toLowerCase());
      if (profile) {
        cards[i] = { player: p, profile: profile.profile, error: null };
      } else {
        const errEntry = profiles.find((pr) => pr.player === p.name && !pr.ok);
        const error = errEntry?.error || "Unknown error";
        failures.push({ player: p.name, error });
        cards[i] = { player: p, profile: null, error };
      }
      updateTeamProgress(i + 1, players.length);
    }

    renderTeamProfiles(team, season, cards, failures, players.length);
    lastTeamExportPayload = {
      team,
      season,
      entries: cards.filter((c) => c.profile).map((c) => ({
        name: c.player?.name || c.profile?.info?.name || "Player",
        profile: c.profile,
      })),
    };
    if (teamExportJsonBtn) teamExportJsonBtn.disabled = !lastTeamExportPayload.entries.length;
    if (teamExportExcelBtn) teamExportExcelBtn.disabled = !lastTeamExportPayload.entries.length;
    if (teamImportGameBtn) teamImportGameBtn.disabled = !lastTeamExportPayload.entries.length;
    const successCount = cards.filter((c) => c.profile).length;
    teamStatusEl.textContent = failures.length
      ? `Generated ${successCount}/${players.length} player profiles. ${failures.length} failed.`
      : `Generated ${successCount}/${players.length} player profiles.`;
    if (!failures.length) {
      showToast(`${team} roster generated — ${successCount} players.`, "success", 3000);
    } else {
      showToast(`${successCount}/${players.length} players generated. ${failures.length} failed.`, "error", 5000);
    }
  } catch (err) {
    teamStatusEl.textContent = `Unexpected error: ${String(err?.message || err)}`;
  } finally {
    setBusy(false);
  }
}

function renderGroupList(groupMap) {
  const groups = byName(groupMap);
  return groups.map((group) => {
    const rows = group.items
      .map((item) => `<div class="metric-row"><span>${item.name || item.key || "Item"}</span><strong>${item.value ?? 0}</strong></div>`)
      .join("");
    return `
      <article class="metric-card">
        <h3>${group.title}</h3>
        <div class="metric-list">${rows || '<div class="metric-row"><span>Empty</span><strong>0</strong></div>'}</div>
      </article>
    `;
  }).join("");
}

function renderTeamProfiles(team, season, cards, failures, total) {
  renderTeamDashboard(team, season, cards);
  renderCompactRoster(cards, failures);
  generatedProfiles = cards.filter((c) => c.profile);
  // compareCandidates is reset inside renderCompactRoster; teamCompareBtn state is updated there too
}

function renderTeamEmptyState() {
  teamResultsEl.innerHTML = `
    <div class="empty-state">
      <span class="empty-state-icon">🏀</span>
      <span class="empty-state-text">
        <strong>No team generated yet</strong>
        Select a team and season, then click "Generate Team" to build full player profiles.
      </span>
      <span class="empty-state-hint">All 30 NBA teams are available with current rosters.</span>
    </div>
  `;
}

runBtn.addEventListener("click", runGenerator);
if (teamGenerateBtn) {
  teamGenerateBtn.addEventListener("click", runTeamGenerator);
}
if (navDashboardBtn) {
  navDashboardBtn.addEventListener("click", () => showDashboard());
}
document.getElementById("navPlayerGenBtn")?.addEventListener("click", () => showPlayerGenPage());
if (openTeamPageBtn) {
  openTeamPageBtn.addEventListener("click", () => {
    teamResultsEl.innerHTML = "";
    teamStatusEl.textContent = "Idle";
    lastTeamExportPayload = null;
    resetTeamProgress();
    if (teamExportJsonBtn) teamExportJsonBtn.disabled = true;
    if (teamExportExcelBtn) teamExportExcelBtn.disabled = true;
    if (teamImportGameBtn) teamImportGameBtn.disabled = true;
    showTeamPage();
    renderTeamEmptyState();
  });
}
if (teamBackBtn) {
  teamBackBtn.addEventListener("click", () => showDashboard());
}

// Playbook Editor buttons
if (openPlaybookBtn) {
  openPlaybookBtn.addEventListener("click", () => {
    showPlaybookPage();
  });
}
if (playbookBackBtn) {
  playbookBackBtn.addEventListener("click", () => showTeamPage());
}
if (loadPlaybookBtn) {
  loadPlaybookBtn.addEventListener("click", loadTeamPlaybook);
}
if (savePlaybookBtn) {
  savePlaybookBtn.addEventListener("click", saveTeamPlaybook);
}
if (addPlayBtn) {
  addPlayBtn.addEventListener("click", addPlayToPlaybook);
}
if (removePlayBtn) {
  removePlayBtn.addEventListener("click", removeSelectedPlay);
}

if (teamExportJsonBtn) {
  teamExportJsonBtn.addEventListener("click", async () => {
    if (!lastTeamExportPayload?.entries?.length) {
      teamStatusEl.textContent = "No generated team profiles to export.";
      return;
    }
    teamStatusEl.textContent = "Exporting 2K JSON ZIP...";
    const result = await window.nba2kDesktop.exportTeamZip(lastTeamExportPayload);
    teamStatusEl.textContent = result?.ok
      ? `Exported ZIP: ${result.filePath || "Done"}`
      : `Export failed: ${result?.error || "Unknown error"}`;
  });
}

if (teamExportExcelBtn) {
  teamExportExcelBtn.addEventListener("click", async () => {
    if (!lastTeamExportPayload?.entries?.length) {
      teamStatusEl.textContent = "No team data to export. Generate a team first.";
      return;
    }
    if (teamImportGameBtn) teamImportGameBtn.disabled = true;
    teamExportExcelBtn.disabled = true;
    teamStatusEl.textContent = "Generating Excel export...";
    try {
      const result = await window.nba2kDesktop.exportTeamExcel(lastTeamExportPayload);
      if (result?.ok) {
        teamStatusEl.textContent = `Excel exported: ${result.filePath}`;
      } else {
        teamStatusEl.textContent = `Excel export failed: ${result?.error || "Unknown error"}`;
      }
    } catch (err) {
      teamStatusEl.textContent = `Excel export error: ${String(err?.message || err)}`;
    } finally {
      teamExportExcelBtn.disabled = false;
      if (teamImportGameBtn && lastTeamExportPayload?.entries?.length) teamImportGameBtn.disabled = false;
    }
  });
}

if (teamImportGameBtn) {
  teamImportGameBtn.addEventListener("click", async () => {
    if (!lastTeamExportPayload?.entries?.length) {
      teamStatusEl.textContent = "Generate a team first before importing to game.";
      return;
    }
    teamImportGameBtn.disabled = true;
    teamStatusEl.textContent = "Connecting to ATD 2K APP and importing players...";
    try {
      const result = await window.nba2kDesktop.importToGame(lastTeamExportPayload);
      if (result?.ok) {
        const { totalPlayers, totalWritten, results: playerResults } = result;
        const succeeded = (playerResults || []).filter((r) => r.ok).length;
        const failed    = (playerResults || []).filter((r) => !r.ok);
        let msg = `Imported ${succeeded}/${totalPlayers} players (${totalWritten} fields written).`;
        if (failed.length) {
          msg += ` Not found: ${failed.map((r) => r.name).join(", ")}.`;
        }
        teamStatusEl.textContent = msg;
      } else {
        teamStatusEl.textContent = `Import failed: ${result?.error || "Unknown error"}`;
      }
    } catch (err) {
      teamStatusEl.textContent = `Import error: ${String(err?.message || err)}`;
    } finally {
      if (teamImportGameBtn && lastTeamExportPayload?.entries?.length) teamImportGameBtn.disabled = false;
    }
  });
}

playerSearchEl.addEventListener("input", () => {
  const term = playerSearchEl.value.trim();
  setSelected(null);

  if (searchTimer) clearTimeout(searchTimer);

  if (term.length < 2) {
    hideSearchResults();
    return;
  }

  statusEl.textContent = "Searching";
  searchTimer = setTimeout(() => {
    runSearch(term);
  }, 200);
});

seasonEl.addEventListener("change", () => {
  setSelected(null);
  hideSearchResults();
  lastSearchToken += 1;
});

document.addEventListener("click", (event) => {
  if (!searchResultsEl.contains(event.target) && event.target !== playerSearchEl) {
    hideSearchResults();
  }
});

playerSearchEl.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    if (selectedPlayer) runGenerator();
  }
});

tabAttributesEl.addEventListener("click", () => {
  activeTab = "attributes";
  tabAttributesEl.classList.add("active");
  tabTendenciesEl.classList.remove("active");
  tabBadgesEl.classList.remove("active");
  if (tabVsSheetEl) tabVsSheetEl.classList.remove("active");
  renderPanelGrid();
});

tabTendenciesEl.addEventListener("click", () => {
  activeTab = "tendencies";
  tabTendenciesEl.classList.add("active");
  tabAttributesEl.classList.remove("active");
  tabBadgesEl.classList.remove("active");
  if (tabVsSheetEl) tabVsSheetEl.classList.remove("active");
  renderPanelGrid();
});

tabBadgesEl.addEventListener("click", () => {
  activeTab = "badges";
  tabBadgesEl.classList.add("active");
  tabAttributesEl.classList.remove("active");
  tabTendenciesEl.classList.remove("active");
  if (tabVsSheetEl) tabVsSheetEl.classList.remove("active");
  panelFilterValue = "";
  if (panelFilterEl) panelFilterEl.value = "";
  renderPanelGrid();
});

if (tabVsSheetEl) {
  tabVsSheetEl.addEventListener("click", async () => {
    activeTab = "vssheet";
    tabVsSheetEl.classList.add("active");
    tabAttributesEl.classList.remove("active");
    tabTendenciesEl.classList.remove("active");
    tabBadgesEl.classList.remove("active");
    panelFilterValue = "";
    if (panelFilterEl) panelFilterEl.value = "";
    panelTitleEl.textContent = "Generated vs Sheet";
    panelGridEl.innerHTML = '<div class="metric-row"><span>Loading sheet data...</span></div>';
    const playerName = currentProfile?.info?.name || "";
    try {
      const result = await window.nba2kDesktop.sheetLookup({ player: playerName });
      if (!result?.ok) {
        panelGridEl.innerHTML = `<div class="metric-row"><span>${result?.error || "Not found in sheet"}</span></div>`;
        return;
      }
      renderVsSheet(currentProfile, result.attributes, result.display);
    } catch (err) {
      panelGridEl.innerHTML = `<div class="metric-row"><span>Error: ${String(err?.message || err)}</span></div>`;
    }
  });
}

if (clearSelectionBtn) {
  clearSelectionBtn.addEventListener("click", () => {
    setSelected(null);
    playerSearchEl.value = "";
    hideSearchResults();
    showToast("Selection cleared.", "info", 1500);
  });
}

playerSearchEl.addEventListener("keydown", (event) => {
  const btns = searchResultsEl.querySelectorAll(".search-row[data-index]");
  const count = btns.length;
  if (!count) {
    if (event.key === "Enter" && selectedPlayer) {
      event.preventDefault();
      runGenerator();
    }
    return;
  }

  if (event.key === "ArrowDown") {
    event.preventDefault();
    searchFocusIndex = Math.min(searchFocusIndex + 1, count - 1);
    updateSearchFocus(btns);
  } else if (event.key === "ArrowUp") {
    event.preventDefault();
    searchFocusIndex = Math.max(searchFocusIndex - 1, 0);
    updateSearchFocus(btns);
  } else if (event.key === "Enter") {
    event.preventDefault();
    if (searchFocusIndex >= 0 && searchFocusIndex < count) {
      btns[searchFocusIndex].click();
    } else if (selectedPlayer) {
      runGenerator();
    }
  } else if (event.key === "Escape") {
    hideSearchResults();
  }
});

function updateSearchFocus(btns) {
  btns.forEach((b, i) => {
    b.classList.toggle("focused", i === searchFocusIndex);
    b.setAttribute("aria-selected", i === searchFocusIndex ? "true" : "false");
  });
  if (searchFocusIndex >= 0 && btns[searchFocusIndex]) {
    btns[searchFocusIndex].scrollIntoView({ block: "nearest" });
  }
}

if (panelFilterEl) {
  panelFilterEl.addEventListener("input", () => {
    panelFilterValue = panelFilterEl.value.trim();
    renderPanelGrid();
  });
}

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !panelPageEl?.classList.contains("hidden")) {
    if (panelFilterEl && panelFilterEl.value) {
      panelFilterEl.value = "";
      panelFilterValue = "";
      renderPanelGrid();
    }
  }
});

if (compareBackBtn) {
  compareBackBtn.addEventListener("click", () => {
    if (profileBackTarget === "team") {
      showTeamPage();
    } else {
      showDashboard();
    }
  });
}

if (teamCompareBtn) {
  teamCompareBtn.addEventListener("click", () => {
    if (compareCandidates.length < 2) {
      showToast("Select 2 players using the compare buttons on their cards.", "info", 3000);
      return;
    }
    const p1 = compareCandidates[0].profile;
    const p2 = compareCandidates[1].profile;
    profileBackTarget = "team";
    renderComparison(p1, p2);
  });
}

if (compareExpandBtn) {
  compareExpandBtn.addEventListener("click", () => {
    if (!compareFullContentEl) return;
    const expanded = compareExpandBtn._expanded;
    compareExpandBtn._expanded = !expanded;
    compareExpandBtn.textContent = expanded ? "Full Comparison" : "Simple View";
    compareFullContentEl.classList.toggle("hidden", expanded);
  });
}

// ═══════════════════════════════════════════════════════════════
//  NBA STATS ENGINE
// ═══════════════════════════════════════════════════════════════

let statsState = {
  tab: "leaders",
  season: "2024-25",
  seasonType: "Regular Season",
  perMode: "PerGame",
  leaderCategory: "PTS",
  playerMeasure: "Base",
  teamMeasure: "Base",
  trackingMeasure: "Drives",
  playerSortCol: null, playerSortDir: "desc",
  teamSortCol: null, teamSortDir: "desc",
  leaderSortCol: null, leaderSortDir: "desc",
  trackingSortCol: null, trackingSortDir: "desc",
  hustleSortCol: null, hustleSortDir: "desc",
  playerFilter: "",
  playersData: null, teamsData: null, leadersData: null,
  trackingData: null, hustleData: null,
  initialized: false,
};

const _spd = {
  playerId: null, season: "2024-25", seasonType: "Regular Season",
  shots: null, view: "dots", loaded: false,
  zoneFilter: [], angleFilter: [],
  distMin: 0, distMax: 30,
  showMade: true, showMissed: true,
  dotSize: 4, dotOpacity: 75,
};

// ── Progression Tracker — constants ─────────────────────────────────────────

const PROG_TEAMS = [
  "Philadelphia 76ers","Milwaukee Bucks","Chicago Bulls","Cleveland Cavaliers",
  "Boston Celtics","LA Clippers","Memphis Grizzlies","Atlanta Hawks",
  "Miami Heat","Charlotte Hornets","Utah Jazz","Sacramento Kings",
  "New York Knicks","LA Lakers","Orlando Magic","Dallas Mavericks",
  "Brooklyn Nets","Denver Nuggets","Indiana Pacers","New Orleans Pelicans",
  "Detroit Pistons","Toronto Raptors","Houston Rockets","San Antonio Spurs",
  "Phoenix Suns","Oklahoma City Thunder","Minnesota Timberwolves",
  "Portland Trail Blazers","Golden State Warriors","Washington Wizards",
];

const PROG_CATS = [
  { key:"tends",       label:"Tendencies",         s:"Tendencies",    p:"high" },
  { key:"attrs",       label:"Attributes",         s:"Attributes",    p:"high" },
  { key:"sim",         label:"Sim Settings",       s:"Sim Settings",  p:"high" },
  { key:"boomBust",    label:"Boom vs Bust",       s:"Boom vs Bust",  p:"high" },
  { key:"body",        label:"Player Body",        s:"Player Body",   p:"mid"  },
  { key:"playbooks",   label:"Playbooks",          s:"Playbooks",     p:"mid"  },
  { key:"freeAgents",  label:"Free Agents",        s:"Free Agents",   p:"mid"  },
  { key:"gLeague",     label:"G-League",           s:"G-League",      p:"mid"  },
  { key:"sigEdits",    label:"Sig Edits",          s:"Sig Edits",     p:"mid"  },
  { key:"coachProf",   label:"Coaching Profiles",  s:"Coaching",      p:"mid"  },
  { key:"plyrPrio",    label:"Player Priorities",  s:"Plyr Prios",    p:"low"  },
  { key:"poes",        label:"POEs",               s:"POEs",          p:"low"  },
  { key:"coachAttrs",  label:"Coach Profile Attrs",s:"Coach Attrs",   p:"low"  },
  { key:"peakTiming",  label:"Peak Start / End",   s:"Peak Timing",   p:"low"  },
  { key:"injuries",    label:"Injuries",           s:"Injuries",      p:"low"  },
  { key:"accessories", label:"Accessories",        s:"Accessories",   p:"low"  },
  { key:"badges",      label:"Player Badges",      s:"Badges",        p:"low"  },
];

const PROG_STATUS_LABEL = {
  ns:   "Not Started",
  wo:   "Working On",
  ir:   "In Review",
  done: "Completed",
};

const PROG_CYCLE = ["ns", "wo", "ir", "done"];

function progKey(teamName) {
  return teamName.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");
}

// ── Progression Tracker — end constants ─────────────────────────────────────

const LEAGUE_AVG = {
  "Restricted Area":         { fgPct: 0.681, pts: 1.363 },
  "In The Paint (Non-RA)":   { fgPct: 0.441, pts: 0.882 },
  "Mid-Range":               { fgPct: 0.407, pts: 0.814 },
  "Left Corner 3":           { fgPct: 0.381, pts: 1.143 },
  "Right Corner 3":          { fgPct: 0.385, pts: 1.155 },
  "Above the Break 3":       { fgPct: 0.363, pts: 1.089 },
};

function getSpdShots() {
  if (!_spd.shots) return [];
  return _spd.shots.filter((s) => {
    if (!_spd.showMade && Number(s.SHOT_MADE_FLAG) === 1) return false;
    if (!_spd.showMissed && Number(s.SHOT_MADE_FLAG) === 0) return false;
    if (_spd.zoneFilter.length && !_spd.zoneFilter.includes(s.SHOT_ZONE_BASIC)) return false;
    if (_spd.angleFilter.length && !_spd.angleFilter.includes(s.SHOT_ZONE_AREA)) return false;
    const d = Number(s.SHOT_DISTANCE);
    if (!isNaN(d) && (d < _spd.distMin || d > _spd.distMax)) return false;
    return true;
  });
}

function getSpdShotsForTable() {
  // Zone filter excluded so all zones always show in the table
  if (!_spd.shots) return [];
  return _spd.shots.filter((s) => {
    if (!_spd.showMade && Number(s.SHOT_MADE_FLAG) === 1) return false;
    if (!_spd.showMissed && Number(s.SHOT_MADE_FLAG) === 0) return false;
    if (_spd.angleFilter.length && !_spd.angleFilter.includes(s.SHOT_ZONE_AREA)) return false;
    const d = Number(s.SHOT_DISTANCE);
    if (!isNaN(d) && (d < _spd.distMin || d > _spd.distMax)) return false;
    return true;
  });
}

function renderZoneStats() {
  const el = document.getElementById("spdZoneStats");
  if (!el) return;
  if (!_spd.shots) { el.innerHTML = ""; return; }

  const tableShots = getSpdShotsForTable();
  const ZONES = ["Restricted Area","In The Paint (Non-RA)","Mid-Range","Left Corner 3","Right Corner 3","Above the Break 3"];

  const rows = ZONES.map((zone) => {
    const zs = tableShots.filter((s) => s.SHOT_ZONE_BASIC === zone);
    if (!zs.length) return null;
    const fgm = zs.filter((s) => Number(s.SHOT_MADE_FLAG) === 1).length;
    const fga = zs.length;
    const fgPct = fgm / fga;
    const shotVal = zone.includes("3") ? 3 : 2;
    const pts = fgm * shotVal / fga;
    const lg = LEAGUE_AVG[zone];
    const excluded = _spd.zoneFilter.length > 0 && !_spd.zoneFilter.includes(zone);
    return { zone, fgm, fga, fgPct, pts, lgFgPct: lg?.fgPct, lgPts: lg?.pts, excluded };
  }).filter(Boolean);

  if (!rows.length) { el.innerHTML = ""; return; }

  const active = rows.filter((r) => !r.excluded);
  const totFgm = active.reduce((s, r) => s + r.fgm, 0);
  const totFga = active.reduce((s, r) => s + r.fga, 0);
  const totPts = active.reduce((s, r) => s + r.fgm * (r.zone.includes("3") ? 3 : 2), 0);
  const totFgPct = totFga ? totFgm / totFga : 0;
  const totPtsPerShot = totFga ? totPts / totFga : 0;

  const pct  = (v) => v != null ? (v * 100).toFixed(1) + "%" : "—";
  const dec2 = (v) => v != null ? v.toFixed(2) : "—";
  // FG% delta: percentage-point diff (×100), shown as "+X.X"
  const diffPct = (player, lg) => {
    if (player == null || lg == null) return "";
    const d = (player - lg) * 100;
    const cls = d >= 1 ? "spd-above-avg" : d <= -1 ? "spd-below-avg" : "";
    return cls ? `<span class="${cls}">${d >= 0 ? "+" : ""}${d.toFixed(1)}</span>` : "";
  };
  // Pts/Shot delta: raw difference, shown as "+X.XX"
  const diffPts = (player, lg) => {
    if (player == null || lg == null) return "";
    const d = player - lg;
    const cls = d >= 0.01 ? "spd-above-avg" : d <= -0.01 ? "spd-below-avg" : "";
    return cls ? `<span class="${cls}">${d >= 0 ? "+" : ""}${d.toFixed(2)}</span>` : "";
  };

  const hdr = `<thead><tr>
    <th class="th-name">Zone</th>
    <th class="th-stat">FGM</th><th class="th-stat">FGA</th>
    <th class="th-stat">FG%</th><th class="th-stat">Lg FG%</th>
    <th class="th-stat">Pts/Shot</th><th class="th-stat">Lg Pts</th>
  </tr></thead>`;

  const bdy = `<tbody>${rows.map((r) => `
    <tr class="stats-row${r.excluded ? " spd-zone-excluded" : ""}">
      <td class="td-name">${r.zone}</td>
      <td class="td-stat">${r.fgm}</td><td class="td-stat">${r.fga}</td>
      <td class="td-stat">${pct(r.fgPct)}${diffPct(r.fgPct, r.lgFgPct)}</td>
      <td class="td-stat spd-lg-cell">${pct(r.lgFgPct)}</td>
      <td class="td-stat">${dec2(r.pts)}${diffPts(r.pts, r.lgPts)}</td>
      <td class="td-stat spd-lg-cell">${dec2(r.lgPts)}</td>
    </tr>`).join("")}
    <tr class="stats-row spd-total-row">
      <td class="td-name">Overall</td>
      <td class="td-stat">${totFgm}</td><td class="td-stat">${totFga}</td>
      <td class="td-stat">${pct(totFgPct)}</td><td class="td-stat spd-lg-cell">—</td>
      <td class="td-stat">${dec2(totPtsPerShot)}</td><td class="td-stat spd-lg-cell">—</td>
    </tr>
  </tbody>`;

  el.innerHTML = `<div class="stats-table-scroll"><table class="stats-table">${hdr}${bdy}</table></div>`;
}

function refreshShotChart() {
  if (!_spd.loaded) return;
  renderCurrentShotView();
  renderZoneStats();
}

const PLAYER_COLS = {
  Base: [
    { key: "PTS", label: "PTS", fmt: "dec1" },
    { key: "REB", label: "REB", fmt: "dec1" },
    { key: "AST", label: "AST", fmt: "dec1" },
    { key: "STL", label: "STL", fmt: "dec1" },
    { key: "BLK", label: "BLK", fmt: "dec1" },
    { key: "TOV", label: "TOV", fmt: "dec1" },
    { key: "MIN", label: "MIN", fmt: "dec1" },
    { key: "GP", label: "GP", fmt: "int" },
    { key: "FGM", label: "FGM", fmt: "dec1" },
    { key: "FGA", label: "FGA", fmt: "dec1" },
    { key: "FG_PCT", label: "FG%", fmt: "pct" },
    { key: "FG3M", label: "3PM", fmt: "dec1" },
    { key: "FG3A", label: "3PA", fmt: "dec1" },
    { key: "FG3_PCT", label: "3P%", fmt: "pct" },
    { key: "FTM", label: "FTM", fmt: "dec1" },
    { key: "FTA", label: "FTA", fmt: "dec1" },
    { key: "FT_PCT", label: "FT%", fmt: "pct" },
    { key: "OREB", label: "OREB", fmt: "dec1" },
    { key: "DREB", label: "DREB", fmt: "dec1" },
    { key: "PLUS_MINUS", label: "+/-", fmt: "dec1" },
  ],
  Advanced: [
    { key: "MIN", label: "MIN", fmt: "dec1" },
    { key: "GP", label: "GP", fmt: "int" },
    { key: "OFF_RATING", label: "ORTG", fmt: "dec1" },
    { key: "DEF_RATING", label: "DRTG", fmt: "dec1" },
    { key: "NET_RATING", label: "NRTG", fmt: "dec1" },
    { key: "AST_PCT", label: "AST%", fmt: "pct1" },
    { key: "AST_TO", label: "AST/TO", fmt: "dec1" },
    { key: "OREB_PCT", label: "OREB%", fmt: "pct1" },
    { key: "DREB_PCT", label: "DREB%", fmt: "pct1" },
    { key: "REB_PCT", label: "REB%", fmt: "pct1" },
    { key: "EFG_PCT", label: "eFG%", fmt: "pct" },
    { key: "TS_PCT", label: "TS%", fmt: "pct" },
    { key: "USG_PCT", label: "USG%", fmt: "pct1" },
    { key: "PIE", label: "PIE", fmt: "pct" },
    { key: "PACE", label: "PACE", fmt: "dec1" },
  ],
  Scoring: [
    { key: "GP", label: "GP", fmt: "int" },
    { key: "MIN", label: "MIN", fmt: "dec1" },
    { key: "FGA", label: "FGA", fmt: "dec1" },
    { key: "FG_PCT", label: "FG%", fmt: "pct" },
    { key: "PCT_FGA_2PT", label: "%FGA 2PT", fmt: "pct" },
    { key: "PCT_FGA_3PT", label: "%FGA 3PT", fmt: "pct" },
    { key: "PCT_PTS_2PT", label: "%PTS 2PT", fmt: "pct" },
    { key: "PCT_PTS_3PT", label: "%PTS 3PT", fmt: "pct" },
    { key: "PCT_PTS_FT", label: "%PTS FT", fmt: "pct" },
    { key: "PCT_PTS_PAINT", label: "%PTS PAINT", fmt: "pct" },
    { key: "PCT_PTS_FB", label: "%PTS FB", fmt: "pct" },
    { key: "PCT_AST_FGM", label: "%AST FGM", fmt: "pct" },
    { key: "PCT_UAST_FGM", label: "%UAST FGM", fmt: "pct" },
  ],
  Misc: [
    { key: "GP", label: "GP", fmt: "int" },
    { key: "MIN", label: "MIN", fmt: "dec1" },
    { key: "PTS", label: "PTS", fmt: "dec1" },
    { key: "AST", label: "AST", fmt: "dec1" },
    { key: "REB", label: "REB", fmt: "dec1" },
    { key: "STL", label: "STL", fmt: "dec1" },
    { key: "BLK", label: "BLK", fmt: "dec1" },
    { key: "BLKA", label: "BLKA", fmt: "dec1" },
    { key: "TOV", label: "TOV", fmt: "dec1" },
    { key: "PF", label: "PF", fmt: "dec1" },
    { key: "PFD", label: "PFD", fmt: "dec1" },
    { key: "PLUS_MINUS", label: "+/-", fmt: "dec1" },
    { key: "DD2", label: "DD2", fmt: "int" },
    { key: "TD3", label: "TD3", fmt: "int" },
    { key: "NBA_FANTASY_PTS", label: "FPTS", fmt: "dec1" },
  ],
  Usage: [
    { key: "GP", label: "GP", fmt: "int" },
    { key: "MIN", label: "MIN", fmt: "dec1" },
    { key: "USG_PCT", label: "USG%", fmt: "pct1" },
    { key: "PCT_FGA", label: "%TM FGA", fmt: "pct1" },
    { key: "PCT_FG3A", label: "%TM 3PA", fmt: "pct1" },
    { key: "PCT_FTA", label: "%TM FTA", fmt: "pct1" },
    { key: "PCT_OREB", label: "%TM OREB", fmt: "pct1" },
    { key: "PCT_DREB", label: "%TM DREB", fmt: "pct1" },
    { key: "PCT_REB", label: "%TM REB", fmt: "pct1" },
    { key: "PCT_AST", label: "%TM AST", fmt: "pct1" },
    { key: "PCT_TOV", label: "%TM TOV", fmt: "pct1" },
    { key: "PCT_STL", label: "%TM STL", fmt: "pct1" },
    { key: "PCT_BLK", label: "%TM BLK", fmt: "pct1" },
    { key: "PCT_PTS", label: "%TM PTS", fmt: "pct1" },
  ],
  Defense: [
    { key: "GP", label: "GP", fmt: "int" },
    { key: "MIN", label: "MIN", fmt: "dec1" },
    { key: "DEF_RATING", label: "DRTG", fmt: "dec1" },
    { key: "DREB", label: "DREB", fmt: "dec1" },
    { key: "DREB_PCT", label: "DREB%", fmt: "pct1" },
    { key: "STL", label: "STL", fmt: "dec1" },
    { key: "BLK", label: "BLK", fmt: "dec1" },
    { key: "BLKA", label: "BLKA", fmt: "dec1" },
    { key: "PF", label: "PF", fmt: "dec1" },
    { key: "PFD", label: "PFD", fmt: "dec1" },
  ],
};

const TEAM_COLS = {
  Base: [
    { key: "W", label: "W", fmt: "int" },
    { key: "L", label: "L", fmt: "int" },
    { key: "W_PCT", label: "WIN%", fmt: "pct" },
    { key: "MIN", label: "MIN", fmt: "dec1" },
    { key: "PTS", label: "PTS", fmt: "dec1" },
    { key: "REB", label: "REB", fmt: "dec1" },
    { key: "AST", label: "AST", fmt: "dec1" },
    { key: "TOV", label: "TOV", fmt: "dec1" },
    { key: "STL", label: "STL", fmt: "dec1" },
    { key: "BLK", label: "BLK", fmt: "dec1" },
    { key: "FG_PCT", label: "FG%", fmt: "pct" },
    { key: "FG3_PCT", label: "3P%", fmt: "pct" },
    { key: "FT_PCT", label: "FT%", fmt: "pct" },
    { key: "OREB", label: "OREB", fmt: "dec1" },
    { key: "DREB", label: "DREB", fmt: "dec1" },
    { key: "PLUS_MINUS", label: "+/-", fmt: "dec1" },
  ],
  Advanced: [
    { key: "W", label: "W", fmt: "int" },
    { key: "L", label: "L", fmt: "int" },
    { key: "W_PCT", label: "WIN%", fmt: "pct" },
    { key: "OFF_RATING", label: "ORTG", fmt: "dec1" },
    { key: "DEF_RATING", label: "DRTG", fmt: "dec1" },
    { key: "NET_RATING", label: "NRTG", fmt: "dec1" },
    { key: "AST_PCT", label: "AST%", fmt: "pct1" },
    { key: "OREB_PCT", label: "OREB%", fmt: "pct1" },
    { key: "DREB_PCT", label: "DREB%", fmt: "pct1" },
    { key: "EFG_PCT", label: "eFG%", fmt: "pct" },
    { key: "TS_PCT", label: "TS%", fmt: "pct" },
    { key: "USG_PCT", label: "USG%", fmt: "pct1" },
    { key: "PACE", label: "PACE", fmt: "dec1" },
    { key: "PIE", label: "PIE", fmt: "pct" },
  ],
};

const TRACKING_COLS = {
  Drives: [
    { key: "GP", label: "GP", fmt: "int" }, { key: "MIN", label: "MIN", fmt: "dec1" },
    { key: "DRIVES", label: "DRIVES", fmt: "dec1" },
    { key: "DRIVE_FGM", label: "FGM", fmt: "dec1" }, { key: "DRIVE_FGA", label: "FGA", fmt: "dec1" }, { key: "DRIVE_FG_PCT", label: "FG%", fmt: "pct" },
    { key: "DRIVE_FTM", label: "FTM", fmt: "dec1" }, { key: "DRIVE_FTA", label: "FTA", fmt: "dec1" }, { key: "DRIVE_FT_PCT", label: "FT%", fmt: "pct" },
    { key: "DRIVE_PTS", label: "PTS", fmt: "dec1" }, { key: "DRIVE_PTS_PCT", label: "PTS%", fmt: "pct" },
    { key: "DRIVE_PASSES", label: "PASSES", fmt: "dec1" }, { key: "DRIVE_AST", label: "AST", fmt: "dec1" },
    { key: "DRIVE_TOV", label: "TOV", fmt: "dec1" }, { key: "DRIVE_PF", label: "PF", fmt: "dec1" },
  ],
  PullUpShot: [
    { key: "GP", label: "GP", fmt: "int" }, { key: "MIN", label: "MIN", fmt: "dec1" },
    { key: "PULL_UP_FGM", label: "FGM", fmt: "dec1" }, { key: "PULL_UP_FGA", label: "FGA", fmt: "dec1" }, { key: "PULL_UP_FG_PCT", label: "FG%", fmt: "pct" },
    { key: "PULL_UP_3PM", label: "3PM", fmt: "dec1" }, { key: "PULL_UP_3PA", label: "3PA", fmt: "dec1" }, { key: "PULL_UP_3P_PCT", label: "3P%", fmt: "pct" },
    { key: "PULL_UP_PTS", label: "PTS", fmt: "dec1" }, { key: "PULL_UP_EFG_PCT", label: "eFG%", fmt: "pct" },
  ],
  CatchShoot: [
    { key: "GP", label: "GP", fmt: "int" }, { key: "MIN", label: "MIN", fmt: "dec1" },
    { key: "CATCH_SHOOT_FGM", label: "FGM", fmt: "dec1" }, { key: "CATCH_SHOOT_FGA", label: "FGA", fmt: "dec1" }, { key: "CATCH_SHOOT_FG_PCT", label: "FG%", fmt: "pct" },
    { key: "CATCH_SHOOT_3PM", label: "3PM", fmt: "dec1" }, { key: "CATCH_SHOOT_3PA", label: "3PA", fmt: "dec1" }, { key: "CATCH_SHOOT_3P_PCT", label: "3P%", fmt: "pct" },
    { key: "CATCH_SHOOT_PTS", label: "PTS", fmt: "dec1" }, { key: "CATCH_SHOOT_EFG_PCT", label: "eFG%", fmt: "pct" },
  ],
  PostTouch: [
    { key: "GP", label: "GP", fmt: "int" }, { key: "MIN", label: "MIN", fmt: "dec1" },
    { key: "POST_TOUCHES", label: "TOUCHES", fmt: "dec1" },
    { key: "POST_FGM", label: "FGM", fmt: "dec1" }, { key: "POST_FGA", label: "FGA", fmt: "dec1" }, { key: "POST_FG_PCT", label: "FG%", fmt: "pct" },
    { key: "POST_FTM", label: "FTM", fmt: "dec1" }, { key: "POST_FTA", label: "FTA", fmt: "dec1" }, { key: "POST_FT_PCT", label: "FT%", fmt: "pct" },
    { key: "POST_PTS", label: "PTS", fmt: "dec1" }, { key: "POST_PTS_PCT", label: "PTS%", fmt: "pct" },
    { key: "POST_AST", label: "AST", fmt: "dec1" }, { key: "POST_TOV", label: "TOV", fmt: "dec1" }, { key: "POST_PF", label: "PF", fmt: "dec1" },
  ],
  ElbowTouch: [
    { key: "GP", label: "GP", fmt: "int" }, { key: "MIN", label: "MIN", fmt: "dec1" },
    { key: "ELBOW_TOUCHES", label: "TOUCHES", fmt: "dec1" },
    { key: "ELBOW_FGM", label: "FGM", fmt: "dec1" }, { key: "ELBOW_FGA", label: "FGA", fmt: "dec1" }, { key: "ELBOW_FG_PCT", label: "FG%", fmt: "pct" },
    { key: "ELBOW_FTM", label: "FTM", fmt: "dec1" }, { key: "ELBOW_FTA", label: "FTA", fmt: "dec1" }, { key: "ELBOW_FT_PCT", label: "FT%", fmt: "pct" },
    { key: "ELBOW_PTS", label: "PTS", fmt: "dec1" }, { key: "ELBOW_PTS_PCT", label: "PTS%", fmt: "pct" },
    { key: "ELBOW_AST", label: "AST", fmt: "dec1" }, { key: "ELBOW_TOV", label: "TOV", fmt: "dec1" }, { key: "ELBOW_PF", label: "PF", fmt: "dec1" },
  ],
  PaintTouch: [
    { key: "GP", label: "GP", fmt: "int" }, { key: "MIN", label: "MIN", fmt: "dec1" },
    { key: "PAINT_TOUCHES", label: "TOUCHES", fmt: "dec1" },
    { key: "PAINT_TOUCH_FGM", label: "FGM", fmt: "dec1" }, { key: "PAINT_TOUCH_FGA", label: "FGA", fmt: "dec1" }, { key: "PAINT_TOUCH_FG_PCT", label: "FG%", fmt: "pct" },
    { key: "PAINT_TOUCH_FTM", label: "FTM", fmt: "dec1" }, { key: "PAINT_TOUCH_FTA", label: "FTA", fmt: "dec1" }, { key: "PAINT_TOUCH_FT_PCT", label: "FT%", fmt: "pct" },
    { key: "PAINT_TOUCH_PTS", label: "PTS", fmt: "dec1" }, { key: "PAINT_TOUCH_PTS_PCT", label: "PTS%", fmt: "pct" },
    { key: "PAINT_TOUCH_AST", label: "AST", fmt: "dec1" }, { key: "PAINT_TOUCH_TOV", label: "TOV", fmt: "dec1" }, { key: "PAINT_TOUCH_PF", label: "PF", fmt: "dec1" },
  ],
  Passing: [
    { key: "GP", label: "GP", fmt: "int" }, { key: "MIN", label: "MIN", fmt: "dec1" },
    { key: "PASSES_MADE", label: "PASSES MADE", fmt: "dec1" },
    { key: "PASSES_RECEIVED", label: "PASSES REC", fmt: "dec1" },
    { key: "AST", label: "AST", fmt: "dec1" },
    { key: "SECONDARY_AST", label: "SEC AST", fmt: "dec1" },
    { key: "POTENTIAL_AST", label: "POT AST", fmt: "dec1" },
    { key: "AST_PTS_CREATED", label: "AST PTS", fmt: "dec1" },
    { key: "AST_ADJ", label: "ADJ AST", fmt: "dec1" },
    { key: "AST_TO_PASS_PCT", label: "AST%", fmt: "pct" },
    { key: "AST_TO_PASS_PCT_ADJ", label: "ADJ AST%", fmt: "pct" },
  ],
};

const HUSTLE_COLS = [
  { key: "GP", label: "GP", fmt: "int" }, { key: "MIN", label: "MIN", fmt: "dec1" },
  { key: "CONTESTED_SHOTS", label: "CONT SHOTS", fmt: "dec1" },
  { key: "CONTESTED_SHOTS_2PT", label: "CONT 2PT", fmt: "dec1" },
  { key: "CONTESTED_SHOTS_3PT", label: "CONT 3PT", fmt: "dec1" },
  { key: "DEFLECTIONS", label: "DEFLECTIONS", fmt: "dec1" },
  { key: "CHARGES_DRAWN", label: "CHARGES", fmt: "dec1" },
  { key: "SCREEN_ASSISTS", label: "SCR AST", fmt: "dec1" },
  { key: "SCREEN_AST_PTS", label: "SCR AST PTS", fmt: "dec1" },
  { key: "OFF_LOOSE_BALLS_RECOVERED", label: "OFF LOOSE", fmt: "dec1" },
  { key: "DEF_LOOSE_BALLS_RECOVERED", label: "DEF LOOSE", fmt: "dec1" },
  { key: "OFF_BOX_OUTS", label: "OFF BOX", fmt: "dec1" },
  { key: "DEF_BOX_OUTS", label: "DEF BOX", fmt: "dec1" },
  { key: "BOX_OUT_PLAYER_REBS", label: "BOX REB", fmt: "dec1" },
];

const LEADER_LABELS = {
  PTS: "Points", REB: "Rebounds", AST: "Assists", STL: "Steals",
  BLK: "Blocks", FG_PCT: "FG%", FG3_PCT: "3-Point%", FT_PCT: "FT%", MIN: "Minutes",
};

function statFmt(val, fmt) {
  const n = Number(val);
  if (val === null || val === undefined || isNaN(n)) return "-";
  switch (fmt) {
    case "int":   return String(Math.round(n));
    case "dec1":  return n.toFixed(1);
    case "pct":   return (n <= 1 ? n * 100 : n).toFixed(1);
    case "pct1":  return (n <= 1 ? n * 100 : n).toFixed(1);
    default:      return n.toFixed(1);
  }
}

function statColor(val, fmt, allVals) {
  if (!allVals || allVals.length < 5) return "";
  const nums = allVals.filter((v) => v !== null && !isNaN(Number(v))).map(Number);
  if (!nums.length) return "";
  const min = Math.min(...nums);
  const max = Math.max(...nums);
  if (max === min) return "";
  const n = Number(val);
  const pct = (n - min) / (max - min);
  if (pct >= 0.95) return "stat-elite";
  if (pct >= 0.80) return "stat-great";
  if (pct >= 0.60) return "stat-good";
  return "";
}

function statsGetFilters() {
  const s = document.getElementById("statsSeason");
  const st = document.getElementById("statsSeasonType");
  const pm = document.getElementById("statsPerMode");
  return {
    season: s?.value || "2024-25",
    seasonType: st?.value || "Regular Season",
    perMode: pm?.value || "PerGame",
  };
}

function statsShowLoading(containerId, msg = "Loading stats from NBA API…") {
  const el = document.getElementById(containerId);
  if (el) el.innerHTML = `
    <div class="stats-loading">
      <div class="stats-spinner"></div>
      <span>${msg}</span>
    </div>`;
}

function statsShowError(containerId, msg) {
  const el = document.getElementById(containerId);
  if (el) el.innerHTML = `<div class="stats-error"><span class="stats-error-icon">⚠</span><span>${msg}</span></div>`;
}

function buildSortableTable(rows, cols, nameKey, nameLabel, sortCol, sortDir, onSort, onNameClick) {
  if (!rows || !rows.length) return '<div class="stats-empty">No data available.</div>';

  const sorted = [...rows];
  if (sortCol) {
    sorted.sort((a, b) => {
      const av = Number(a[sortCol] ?? -Infinity);
      const bv = Number(b[sortCol] ?? -Infinity);
      return sortDir === "asc" ? av - bv : bv - av;
    });
  }

  const colVals = {};
  cols.forEach(({ key }) => { colVals[key] = sorted.map((r) => r[key]); });

  const arrow = (col) => {
    if (col !== sortCol) return '<span class="th-sort-icon">↕</span>';
    return `<span class="th-sort-icon active">${sortDir === "asc" ? "↑" : "↓"}</span>`;
  };

  const header = `
    <thead>
      <tr>
        <th class="th-rank">#</th>
        <th class="th-name">${nameLabel}</th>
        ${cols.map(({ key, label }) => `<th class="th-stat ${key === sortCol ? "th-active" : ""}" data-col="${key}">${label}${arrow(key)}</th>`).join("")}
      </tr>
    </thead>`;

  const body = `
    <tbody>
      ${sorted.map((row, i) => {
        const name = row[nameKey] || "-";
        const team = row.TEAM_ABBREVIATION || row.TEAM || "";
        const teamTheme = TEAM_THEME[String(team).toUpperCase()] || null;
        const teamColor = teamTheme ? teamTheme[2] : "var(--t2)";
        const cells = cols.map(({ key, fmt }) => {
          const v = row[key];
          const cls = statColor(v, fmt, colVals[key]);
          return `<td class="td-stat ${cls}" data-col="${key}">${statFmt(v, fmt)}</td>`;
        }).join("");
        const playerId = row.PLAYER_ID || row.PERSON_ID || "";
        return `
          <tr class="stats-row" data-name="${name}">
            <td class="td-rank">${i + 1}</td>
            <td class="td-name">
              <button class="stats-player-btn" data-player="${name}" data-player-id="${playerId}" title="View ${name}">
                <span class="stats-player-name">${name}</span>
                ${team ? `<span class="stats-player-team" style="color:${teamColor}">${team}</span>` : ""}
              </button>
            </td>
            ${cells}
          </tr>`;
      }).join("")}
    </tbody>`;

  return `
    <div class="stats-table-scroll">
      <table class="stats-table">
        ${header}
        ${body}
      </table>
    </div>
    <div class="stats-table-footer">
      <span>${sorted.length} ${nameLabel === "TEAM" ? "teams" : "players"}</span>
    </div>`;
}

function attachTableSortHandlers(wrapEl, onSort) {
  wrapEl.querySelectorAll("th.th-stat[data-col]").forEach((th) => {
    th.addEventListener("click", () => onSort(th.dataset.col));
  });
}

function attachPlayerClickHandlers(wrapEl) {
  wrapEl.querySelectorAll(".stats-player-btn[data-player]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const name = btn.dataset.player;
      const playerId = btn.dataset.playerId;
      if (!name) return;
      openPlayerDetail(name, playerId);
    });
  });
}

// ── Shot Chart ───────────────────────────────────────────────────────────────

function drawCourt(ctx, W, H, clearBg = true) {
  // NBA coordinate space: x ∈ [-250,250], y ∈ [-52,422] (basket at 0,0)
  const XMIN = -250, YMAX = 422, SW = 500, SH = 474;
  const tx = (x) => (x - XMIN) / SW * W;
  const ty = (y) => (YMAX - y) / SH * H;
  const srx = (r) => r / SW * W;
  const sry = (r) => r / SH * H;

  if (clearBg) {
    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = "#04070f";
    ctx.fillRect(0, 0, W, H);
  }

  // Paint fill
  ctx.fillStyle = "rgba(77,168,255,0.05)";
  ctx.fillRect(tx(-80), ty(142), srx(160), sry(142));

  const lc = "rgba(255,255,255,0.2)";
  const lw = 1.5;

  const seg = (x1, y1, x2, y2, color = lc, width = lw) => {
    ctx.beginPath(); ctx.strokeStyle = color; ctx.lineWidth = width;
    ctx.moveTo(tx(x1), ty(y1)); ctx.lineTo(tx(x2), ty(y2)); ctx.stroke();
  };

  const ell = (cx, cy, rx, ry, start, end, ccw = false, color = lc, width = lw) => {
    ctx.beginPath(); ctx.strokeStyle = color; ctx.lineWidth = width;
    ctx.ellipse(tx(cx), ty(cy), srx(rx), sry(ry), 0, start, end, ccw); ctx.stroke();
  };

  // Court border
  ctx.strokeStyle = lc; ctx.lineWidth = lw;
  ctx.strokeRect(0, 0, W, H);

  // Backboard
  seg(-30, -7.5, 30, -7.5, "rgba(255,255,255,0.55)", 2);

  // Rim (basket)
  ell(0, 0, 7.5, 7.5, 0, Math.PI * 2, false, "rgba(255,140,0,0.9)", 2);

  // Paint box
  seg(-80, -52, -80, 142); seg(80, -52, 80, 142); seg(-80, 142, 80, 142);

  // Restricted area (upper semicircle = toward halfcourt)
  ell(0, 0, 40, 40, Math.PI, 0, false);

  // Free throw circle — solid upper half
  ell(0, 142, 60, 60, Math.PI, 0, false);
  // Dashed lower half
  ctx.beginPath(); ctx.setLineDash([4, 5]); ctx.strokeStyle = lc; ctx.lineWidth = lw;
  ctx.ellipse(tx(0), ty(142), srx(60), sry(60), 0, 0, Math.PI, false);
  ctx.stroke(); ctx.setLineDash([]);

  // 3PT corner lines
  seg(-220, -52, -220, 89.5); seg(220, -52, 220, 89.5);

  // 3PT arc — angles computed in canvas space so scaling is correct
  const aR = Math.atan2(ty(89.5) - ty(0), tx(220) - tx(0));   // right corner angle
  const aL = Math.atan2(ty(89.5) - ty(0), tx(-220) - tx(0));  // left corner angle
  ell(0, 0, 237.5, 237.5, aR, aL, true); // ccw=true → goes through top of arc
}

function renderShotChart(shots, canvas, season) {
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const W = canvas.width, H = canvas.height;

  drawCourt(ctx, W, H);

  const XMIN = -250, YMAX = 422, SW = 500, SH = 474;
  const tx = (x) => (x - XMIN) / SW * W;
  const ty = (y) => (YMAX - y) / SH * H;
  const dotR = Math.max(2, _spd.dotSize);
  const base = _spd.dotOpacity / 100;
  const missAlpha = (base * 0.55).toFixed(2);
  const makeAlpha = (base * 0.92).toFixed(2);
  const makeStroke = Math.min(1, base * 1.1).toFixed(2);

  const made = [], missed = [];
  shots.forEach((s) => { (Number(s.SHOT_MADE_FLAG) === 1 ? made : missed).push(s); });

  const drawShots = (arr, fillColor, strokeColor) => {
    arr.forEach((s) => {
      const x = Number(s.LOC_X), y = Number(s.LOC_Y);
      if (isNaN(x) || isNaN(y)) return;
      ctx.beginPath();
      ctx.arc(tx(x), ty(y), dotR, 0, Math.PI * 2);
      ctx.fillStyle = fillColor;
      ctx.fill();
      if (strokeColor) { ctx.strokeStyle = strokeColor; ctx.lineWidth = 0.6; ctx.stroke(); }
    });
  };

  drawShots(missed, `rgba(255,82,82,${missAlpha})`, null);
  drawShots(made, `rgba(74,222,128,${makeAlpha})`, `rgba(74,222,128,${makeStroke})`);

  // Stats bar at bottom
  const fgPct = shots.length > 0 ? (made.length / shots.length * 100).toFixed(1) : "-";
  ctx.fillStyle = "rgba(4,7,15,0.78)";
  ctx.fillRect(0, H - 26, W, 26);
  ctx.font = `bold ${Math.max(10, Math.round(W / 44))}px monospace`;
  ctx.fillStyle = "rgba(255,255,255,0.65)";
  ctx.textAlign = "left";
  ctx.fillText(`${made.length}/${shots.length} FGA  ${fgPct}% FG`, 8, H - 8);
  if (season) {
    ctx.textAlign = "right";
    ctx.fillStyle = "rgba(255,255,255,0.3)";
    ctx.fillText(season, W - 8, H - 8);
  }
}

function heatColor(t) {
  // Inferno palette — near-black → purple → magenta → red → orange → yellow-white
  const stops = [
    [  0,   0,   4],
    [ 27,  12,  65],
    [ 74,  12, 107],
    [120,  28, 109],
    [165,  44,  96],
    [207,  68,  70],
    [232, 118,  44],
    [248, 209, 101],
    [252, 255, 164],
  ];
  const n = stops.length - 1;
  const i = Math.min(Math.floor(t * n), n - 1);
  const f = t * n - i;
  const [r1,g1,b1] = stops[i], [r2,g2,b2] = stops[i+1];
  return [Math.round(r1+(r2-r1)*f), Math.round(g1+(g2-g1)*f), Math.round(b1+(b2-b1)*f)];
}

function hexbinEffColor(t) {
  // Diverging: t=0 cold (below avg) → t=0.5 neutral → t=1 hot (above avg)
  const stops = [
    [ 50, 130, 220],  // blue
    [120, 170, 210],  // light blue
    [175, 160, 190],  // neutral purple-gray
    [240, 150,  60],  // orange
    [235,  70,  20],  // red-orange
    [255, 230,   0],  // yellow
  ];
  const n = stops.length - 1;
  const i = Math.min(Math.floor(t * n), n - 1);
  const f = t * n - i;
  const [r1,g1,b1] = stops[i], [r2,g2,b2] = stops[i+1];
  return [Math.round(r1+(r2-r1)*f), Math.round(g1+(g2-g1)*f), Math.round(b1+(b2-b1)*f)];
}

function renderHeatMap(shots, canvas) {
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const W = canvas.width, H = canvas.height;

  ctx.fillStyle = "#04070f";
  ctx.fillRect(0, 0, W, H);

  if (!shots || shots.length === 0) { drawCourt(ctx, W, H, false); return; }

  const XMIN = -250, YMAX = 422, SW = 500, SH = 474;

  // Gaussian KDE on a reduced grid then scale up — preserves peak brightness
  // (CSS blur approach dilutes peaks by ~85%; pixel-level KDE avoids this entirely)
  const KW = 100, KH = 94;
  const sigma = 2.8;           // kernel σ in KDE-grid units (≈14px in 500px canvas)
  const kR = Math.ceil(sigma * 3.2); // truncate kernel at 3.2σ
  const s2 = 2 * sigma * sigma;
  const density = new Float32Array(KW * KH);

  shots.forEach((s) => {
    const x = Number(s.LOC_X), y = Number(s.LOC_Y);
    if (isNaN(x) || isNaN(y)) return;
    const cx = (x - XMIN) / SW * KW;
    const cy = (YMAX - y) / SH * KH;
    const x0 = Math.max(0, Math.ceil(cx - kR));
    const x1 = Math.min(KW - 1, Math.floor(cx + kR));
    const y0 = Math.max(0, Math.ceil(cy - kR));
    const y1 = Math.min(KH - 1, Math.floor(cy + kR));
    for (let py = y0; py <= y1; py++) {
      for (let px = x0; px <= x1; px++) {
        const dx = px + 0.5 - cx, dy = py + 0.5 - cy;
        density[py * KW + px] += Math.exp(-(dx * dx + dy * dy) / s2);
      }
    }
  });

  let maxD = 0;
  for (let i = 0; i < density.length; i++) if (density[i] > maxD) maxD = density[i];
  if (maxD === 0) { drawCourt(ctx, W, H, false); return; }

  // Color each KDE pixel; sqrt scale lifts mid-range zones into visible range
  const imgData = new ImageData(KW, KH);
  const d = imgData.data;
  for (let i = 0; i < KW * KH; i++) {
    const t = Math.sqrt(density[i] / maxD);
    if (t < 0.03) continue;
    const [r, g, b] = heatColor(t);
    d[i * 4] = r; d[i * 4 + 1] = g; d[i * 4 + 2] = b;
    d[i * 4 + 3] = Math.min(255, Math.round(t * 290));
  }

  // Scale the small KDE canvas up to full resolution with bilinear smoothing
  const off = document.createElement("canvas");
  off.width = KW; off.height = KH;
  off.getContext("2d").putImageData(imgData, 0, 0);
  ctx.save();
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = "high";
  ctx.drawImage(off, 0, 0, KW, KH, 0, 0, W, H);
  ctx.restore();

  drawCourt(ctx, W, H, false);

  // Stats bar + frequency legend
  const made = shots.filter((s) => Number(s.SHOT_MADE_FLAG) === 1).length;
  const fgPct = shots.length > 0 ? (made / shots.length * 100).toFixed(1) : "-";
  ctx.fillStyle = "rgba(4,7,15,0.82)";
  ctx.fillRect(0, H - 26, W, 26);
  ctx.font = `bold ${Math.max(10, Math.round(W / 44))}px monospace`;
  ctx.fillStyle = "rgba(255,255,255,0.65)";
  ctx.textAlign = "left";
  ctx.fillText(`${made}/${shots.length} FGA  ${fgPct}% FG`, 8, H - 8);

  // Gradient frequency legend (right side of stats bar)
  const barW = Math.round(W * 0.22), barH = 6;
  const barX = W - barW - 8, barY = H - 17;
  const grad = ctx.createLinearGradient(barX, 0, barX + barW, 0);
  [0, 0.25, 0.5, 0.75, 1].forEach((t) => {
    const [r, g, b] = heatColor(t);
    grad.addColorStop(t, `rgba(${r},${g},${b},0.9)`);
  });
  ctx.fillStyle = grad;
  ctx.fillRect(barX, barY, barW, barH);
  ctx.font = `${Math.max(8, Math.round(W / 58))}px monospace`;
  ctx.fillStyle = "rgba(255,255,255,0.45)";
  ctx.textAlign = "right";
  ctx.fillText("lower", barX - 3, barY + barH);
  ctx.textAlign = "left";
  ctx.fillText("higher", barX + barW + 3, barY + barH);
}

function renderHexbin(shots, canvas) {
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const W = canvas.width, H = canvas.height;

  ctx.fillStyle = "#04070f";
  ctx.fillRect(0, 0, W, H);

  if (!shots || shots.length === 0) { drawCourt(ctx, W, H, false); return; }

  const XMIN = -250, YMAX = 422, SW = 500, SH = 474;
  const toX = (x) => (x - XMIN) / SW * W;
  const toY = (y) => (YMAX - y) / SH * H;

  // Pointy-top hex circumradius in canvas pixels
  const hexR = W / 22;

  // Convert canvas pixel (px,py) to cube hex key using canonical pointy-top formula
  const pixToKey = (px, py) => {
    const q = (Math.sqrt(3) / 3 * px - 1 / 3 * py) / hexR;
    const r = (2 / 3 * py) / hexR;
    const s = -q - r;
    let rq = Math.round(q), rr = Math.round(r), rs = Math.round(s);
    const dq = Math.abs(rq - q), dr = Math.abs(rr - r), ds = Math.abs(rs - s);
    if (dq > dr && dq > ds) rq = -rr - rs;
    else if (dr > ds) rr = -rq - rs;
    return `${rq},${rr}`;
  };

  // Convert cube hex key back to canvas pixel center
  const keyToCenter = (key) => {
    const [q, r] = key.split(",").map(Number);
    return { x: hexR * (Math.sqrt(3) * q + Math.sqrt(3) / 2 * r), y: hexR * (3 / 2 * r) };
  };

  // Bin shots into hexagons
  const bins = new Map();
  shots.forEach((s) => {
    const x = Number(s.LOC_X), y = Number(s.LOC_Y);
    if (isNaN(x) || isNaN(y)) return;
    const key = pixToKey(toX(x), toY(y));
    if (!bins.has(key)) bins.set(key, { count: 0, made: 0 });
    const b = bins.get(key);
    b.count++;
    if (Number(s.SHOT_MADE_FLAG) === 1) b.made++;
  });

  const totalMade = shots.filter((s) => Number(s.SHOT_MADE_FLAG) === 1).length;
  const avgFg = totalMade / shots.length;
  const maxCount = Math.max(...[...bins.values()].map((b) => b.count), 1);
  // Min shots scales with dataset size so sparse charts still show most hexes
  const minShots = Math.max(2, Math.floor(shots.length / 250));
  const MIN_FACTOR = 0.35; // smallest hex is 35% of base radius

  [...bins.entries()].forEach(([key, b]) => {
    if (b.count < minShots) return;
    const { x: cx, y: cy } = keyToCenter(key);

    // Log-scaled radius (ballr formula)
    const sz = MIN_FACTOR + (1 - MIN_FACTOR) * Math.log(b.count + 1) / Math.log(maxCount + 1);
    const r = hexR * sz * 0.94; // 0.94 leaves a thin gap between adjacent hexes

    // Efficiency color: FG% vs player average, clamped to ±15pp
    const fg = b.made / b.count;
    const t = Math.max(0, Math.min(1, (fg - avgFg + 0.15) / 0.30));
    const [red, grn, blu] = hexbinEffColor(t);

    // Pointy-top hexagon: vertices at 30°, 90°, 150°, 210°, 270°, 330°
    ctx.beginPath();
    for (let i = 0; i < 6; i++) {
      const a = Math.PI / 6 + i * Math.PI / 3;
      const vx = cx + r * Math.cos(a), vy = cy + r * Math.sin(a);
      i === 0 ? ctx.moveTo(vx, vy) : ctx.lineTo(vx, vy);
    }
    ctx.closePath();
    ctx.fillStyle = `rgba(${red},${grn},${blu},0.92)`;
    ctx.fill();
  });

  drawCourt(ctx, W, H, false);

  // Stats bar
  const fgPct = (avgFg * 100).toFixed(1);
  ctx.fillStyle = "rgba(4,7,15,0.85)";
  ctx.fillRect(0, H - 26, W, 26);
  const fs = Math.max(10, Math.round(W / 44));
  ctx.font = `bold ${fs}px monospace`;
  ctx.fillStyle = "rgba(255,255,255,0.65)";
  ctx.textAlign = "left";
  ctx.fillText(`${totalMade}/${shots.length} FGA  ${fgPct}% FG`, 8, H - 8);

  // Color legend: blue = below avg, yellow = above avg
  const barW = Math.round(W * 0.22), barH = 6;
  const barX = W - barW - 8, barY = H - 17;
  const grad = ctx.createLinearGradient(barX, 0, barX + barW, 0);
  [0, 0.25, 0.5, 0.75, 1].forEach((t) => {
    const [r, g, b] = hexbinEffColor(t);
    grad.addColorStop(t, `rgba(${r},${g},${b},0.9)`);
  });
  ctx.fillStyle = grad;
  ctx.fillRect(barX, barY, barW, barH);
  const lfs = Math.max(8, Math.round(W / 58));
  ctx.font = `${lfs}px monospace`;
  ctx.fillStyle = "rgba(255,255,255,0.45)";
  ctx.textAlign = "right";
  ctx.fillText("cold", barX - 3, barY + barH);
  ctx.textAlign = "left";
  ctx.fillText("hot", barX + barW + 3, barY + barH);
}

function renderCurrentShotView() {
  const canvas = document.getElementById("spdShotCanvas");
  if (!canvas || !_spd.shots) return;
  const shots = getSpdShots();
  const wrap = canvas.parentElement;
  if (wrap) {
    const displayW = wrap.clientWidth || 500;
    canvas.style.width = displayW + "px";
    canvas.style.height = Math.round(displayW * 470 / 500) + "px";
  }
  if (_spd.view === "heat") {
    renderHeatMap(shots, canvas);
  } else if (_spd.view === "hexbin") {
    renderHexbin(shots, canvas);
  } else {
    renderShotChart(shots, canvas, _spd.season);
  }
  const legend = document.getElementById("spdShotLegend");
  if (legend) legend.style.visibility = _spd.view === "dots" ? "" : "hidden";
}

async function loadShotChart(season) {
  const canvas = document.getElementById("spdShotCanvas");
  const msgEl = document.getElementById("spdShotMsg");
  const shotSeasonEl = document.getElementById("spdShotSeason");

  _spd.season = season;
  _spd.shots = null;
  _spd.loaded = false;

  if (msgEl) { msgEl.textContent = "Loading shot chart…"; msgEl.className = "spd-shot-msg spd-shot-loading-msg"; }
  if (canvas) {
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "#04070f"; ctx.fillRect(0, 0, canvas.width, canvas.height);
  }

  const result = await window.nba2kDesktop.fetchShotChart({ playerId: _spd.playerId, season, seasonType: _spd.seasonType });

  _spd.loaded = true;
  if (result?.ok && result.shots?.length > 0) {
    _spd.shots = result.shots;
    if (shotSeasonEl) shotSeasonEl.textContent = season;
    if (msgEl) { msgEl.textContent = ""; msgEl.className = "spd-shot-msg"; }
    renderCurrentShotView();
    renderZoneStats();
  } else {
    if (msgEl) {
      msgEl.textContent = result?.ok ? "No shot data for this season." : "Shot chart failed to load.";
      msgEl.className = "spd-shot-msg";
    }
    if (canvas) drawCourt(canvas.getContext("2d"), canvas.width, canvas.height);
  }
}

function toggleShotChartSection() {
  const body = document.getElementById("spdShotBody");
  const icon = document.getElementById("spdCollapseIcon");
  const header = document.getElementById("spdCollapseBtn");
  const controls = document.getElementById("spdShotControls");
  if (!body) return;
  const expanding = !body.classList.contains("expanded");
  body.classList.toggle("expanded", expanding);
  if (icon) icon.style.transform = expanding ? "rotate(90deg)" : "";
  if (header) header.setAttribute("aria-expanded", String(expanding));
  if (controls) controls.classList.toggle("hidden", !expanding);
  if (expanding && !_spd.loaded && _spd.playerId) {
    loadShotChart(_spd.season);
  } else if (expanding && _spd.shots) {
    renderCurrentShotView();
    renderZoneStats();
  }
}

// ── Player Detail Page ───────────────────────────────────────────────────────

function showStatsMainContent(show) {
  const hide = ["stats-page-header", "stats-subnav", "stats-view"].flatMap((cls) =>
    [...document.querySelectorAll(`#statsPage .${cls}`)]);
  hide.forEach((el) => el.classList.toggle("hidden", !show));
  const detail = document.getElementById("statsPlayerDetail");
  if (detail) detail.classList.toggle("hidden", show);
}

async function openPlayerDetail(name, playerId) {
  showStatsMainContent(false);
  const nameEl = document.getElementById("spdName");
  const metaEl = document.getElementById("spdMeta");
  const bioEl = document.getElementById("spdBioRow");
  const avgsEl = document.getElementById("spdSeasonAvgs");
  const photoEl = document.getElementById("spdPhoto");
  const fallbackEl = document.getElementById("spdPhotoFallback");
  const careerEl = document.getElementById("spdCareerTable");

  if (nameEl) nameEl.textContent = name;
  if (metaEl) metaEl.textContent = "Loading…";
  if (bioEl) bioEl.innerHTML = "";
  if (avgsEl) avgsEl.innerHTML = "";
  if (careerEl) careerEl.innerHTML = '<div class="stats-loading"><div class="stats-spinner"></div></div>';


  const initials = name.split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase();
  if (photoEl && playerId) {
    photoEl.src = `https://cdn.nba.com/headshots/nba/latest/1040x760/${playerId}.png`;
    photoEl.style.display = "";
    if (fallbackEl) fallbackEl.style.display = "none";
  } else if (fallbackEl) {
    if (photoEl) photoEl.style.display = "none";
    fallbackEl.textContent = initials;
    fallbackEl.style.display = "grid";
  }

  if (!playerId) {
    if (metaEl) metaEl.textContent = "No player ID — showing name only";
    if (careerEl) careerEl.innerHTML = '<div class="stats-empty">No player ID available for this row.</div>';
    return;
  }

  const [bioResult, careerResult] = await Promise.allSettled([
    window.nba2kDesktop.fetchPlayerBio({ playerId }),
    window.nba2kDesktop.fetchPlayerCareer({ playerId }),
  ]);

  const bio = bioResult.status === "fulfilled" && bioResult.value?.ok ? bioResult.value.data : null;
  const career = careerResult.status === "fulfilled" && careerResult.value?.ok ? careerResult.value.regular : null;

  if (bio) {
    const pos = bio.POSITION || ""; const jersey = bio.JERSEY || "";
    const team = bio.TEAM_ABBREVIATION || ""; const teamCity = bio.TEAM_CITY || "";
    if (metaEl) metaEl.textContent = [jersey ? `#${jersey}` : null, pos, teamCity ? `${teamCity} ${team}` : team].filter(Boolean).join("  ·  ");

    const pills = [
      bio.HEIGHT ? `<span class="spd-bio-pill"><span class="spd-bio-key">HT</span>${bio.HEIGHT}</span>` : null,
      bio.WEIGHT ? `<span class="spd-bio-pill"><span class="spd-bio-key">WT</span>${bio.WEIGHT} lbs</span>` : null,
      bio.COUNTRY ? `<span class="spd-bio-pill"><span class="spd-bio-key">FROM</span>${bio.COUNTRY}</span>` : null,
      bio.SEASON_EXP != null ? `<span class="spd-bio-pill"><span class="spd-bio-key">EXP</span>${bio.SEASON_EXP === 0 ? "Rookie" : `${bio.SEASON_EXP}Y`}</span>` : null,
      bio.DRAFT_YEAR && bio.DRAFT_YEAR !== "Undrafted" ? `<span class="spd-bio-pill"><span class="spd-bio-key">DRAFT</span>${bio.DRAFT_YEAR} R${bio.DRAFT_ROUND} #${bio.DRAFT_NUMBER}</span>` : null,
    ].filter(Boolean);
    if (bioEl) bioEl.innerHTML = pills.join("");
  } else {
    if (metaEl) metaEl.textContent = name;
  }

  if (career && career.length) {
    const latest = career[career.length - 1];
    const avgKeys = [
      { k: "PTS", l: "PTS" }, { k: "REB", l: "REB" }, { k: "AST", l: "AST" },
      { k: "STL", l: "STL" }, { k: "BLK", l: "BLK" }, { k: "FG_PCT", l: "FG%", pct: true },
      { k: "FG3_PCT", l: "3P%", pct: true }, { k: "FT_PCT", l: "FT%", pct: true },
    ];
    if (avgsEl) avgsEl.innerHTML = avgKeys.map(({ k, l, pct }) => {
      const v = latest[k];
      const disp = v != null ? (pct ? (v * 100).toFixed(1) : Number(v).toFixed(1)) : "-";
      return `<div class="spd-avg-chip"><span class="spd-avg-val">${disp}</span><span class="spd-avg-label">${l}</span></div>`;
    }).join("");

    const careerCols = [
      { key: "SEASON_ID", label: "SEASON" }, { key: "TEAM_ABBREVIATION", label: "TEAM" },
      { key: "GP", label: "GP", fmt: "int" }, { key: "GS", label: "GS", fmt: "int" },
      { key: "MIN", label: "MIN", fmt: "dec1" },
      { key: "PTS", label: "PTS", fmt: "dec1" }, { key: "REB", label: "REB", fmt: "dec1" },
      { key: "AST", label: "AST", fmt: "dec1" }, { key: "STL", label: "STL", fmt: "dec1" },
      { key: "BLK", label: "BLK", fmt: "dec1" }, { key: "TOV", label: "TOV", fmt: "dec1" },
      { key: "FGM", label: "FGM", fmt: "dec1" }, { key: "FGA", label: "FGA", fmt: "dec1" },
      { key: "FG_PCT", label: "FG%", fmt: "pct" },
      { key: "FG3M", label: "3PM", fmt: "dec1" }, { key: "FG3A", label: "3PA", fmt: "dec1" },
      { key: "FG3_PCT", label: "3P%", fmt: "pct" },
      { key: "FTM", label: "FTM", fmt: "dec1" }, { key: "FTA", label: "FTA", fmt: "dec1" },
      { key: "FT_PCT", label: "FT%", fmt: "pct" },
    ];
    const reversed = [...career].reverse();
    const header = `<thead><tr><th class="th-rank">#</th>${careerCols.map((c) => `<th class="${c.fmt ? "th-stat" : "th-name"}">${c.label}</th>`).join("")}</tr></thead>`;
    const body = `<tbody>${reversed.map((row, i) => {
      const cells = careerCols.map(({ key, fmt }) => {
        if (!fmt) return `<td class="td-name" style="font-weight:600;white-space:nowrap">${row[key] || "-"}</td>`;
        return `<td class="td-stat">${statFmt(row[key], fmt)}</td>`;
      }).join("");
      return `<tr class="stats-row">${`<td class="td-rank">${i + 1}</td>`}${cells}</tr>`;
    }).join("")}</tbody>`;
    if (careerEl) careerEl.innerHTML = `<div class="stats-table-scroll"><table class="stats-table">${header}${body}</table></div>`;
  } else {
    if (careerEl) careerEl.innerHTML = '<div class="stats-empty">Career data unavailable.</div>';
  }
}

// ── Leaders ─────────────────────────────────────────────────────────────────

async function loadLeaders(category) {
  statsState.leaderCategory = category;
  statsState.leadersData = null;
  statsShowLoading("statsLeaderCards", "Fetching leaders…");
  document.getElementById("statsLeaderTable").innerHTML = "";

  const { season, seasonType, perMode } = statsGetFilters();
  try {
    const result = await window.nba2kDesktop.fetchLeagueLeaders({ season, seasonType, perMode, category });
    if (!result?.ok) { statsShowError("statsLeaderCards", result?.error || "Failed to load"); return; }
    statsState.leadersData = result.data || [];
    renderLeaderCards(statsState.leadersData, category);
    renderLeaderTable(statsState.leadersData, category);
    updateCacheLabel(result.cached);
  } catch (err) {
    statsShowError("statsLeaderCards", String(err?.message || err));
  }
}

function renderLeaderCards(data, category) {
  const el = document.getElementById("statsLeaderCards");
  if (!el) return;
  const top5 = (data || []).slice(0, 5);
  const label = LEADER_LABELS[category] || category;
  const catCol = category === "FG_PCT" ? "FG_PCT" : category === "FG3_PCT" ? "FG3_PCT" : category === "FT_PCT" ? "FT_PCT" : category;
  const fmtCat = (v) => {
    const n = Number(v);
    if (isNaN(n)) return "-";
    if (["FG_PCT", "FG3_PCT", "FT_PCT"].includes(category)) return (n * 100).toFixed(1);
    return n.toFixed(1);
  };

  el.innerHTML = top5.map((row, i) => {
    const name = row.PLAYER || row.PLAYER_NAME || "-";
    const team = row.TEAM || row.TEAM_ABBREVIATION || "";
    const val = row[catCol];
    const theme = TEAM_THEME[String(team).toUpperCase()] || null;
    const teamColor = theme ? theme[2] : "var(--teal)";
    const glowColor = theme ? theme[2] + "33" : "rgba(0,229,181,0.15)";
    const photoId = row.PLAYER_ID;
    const photoUrl = photoId ? `https://cdn.nba.com/headshots/nba/latest/1040x760/${photoId}.png` : "";
    const initials = name.split(" ").map((w) => w[0] || "").join("").slice(0, 2).toUpperCase();
    const isTop = i === 0;
    return `
      <div class="leader-card ${isTop ? "leader-card-top" : ""}" style="--lc-color:${teamColor};--lc-glow:${glowColor}">
        <div class="leader-rank">${row.RANK || i + 1}</div>
        <div class="leader-photo-wrap">
          ${photoUrl
            ? `<img class="leader-photo" src="${photoUrl}" alt="${name}" onerror="this.outerHTML='<div class=\\'leader-photo-fallback\\'>${initials}</div>'" />`
            : `<div class="leader-photo-fallback">${initials}</div>`}
        </div>
        <div class="leader-info">
          <div class="leader-name">${name}</div>
          <div class="leader-team" style="color:${teamColor}">${team}</div>
        </div>
        <div class="leader-val">${fmtCat(val)}</div>
        <div class="leader-cat-label">${label}</div>
      </div>`;
  }).join("");
}

function renderLeaderTable(data, category) {
  const el = document.getElementById("statsLeaderTable");
  if (!el) return;

  const cols = [
    { key: "PLAYER", label: "PLAYER" },
    { key: "TEAM", label: "TEAM" },
    { key: "GP", label: "GP", fmt: "int" },
    { key: "MIN", label: "MIN", fmt: "dec1" },
    { key: "PTS", label: "PTS", fmt: "dec1" },
    { key: "REB", label: "REB", fmt: "dec1" },
    { key: "AST", label: "AST", fmt: "dec1" },
    { key: "STL", label: "STL", fmt: "dec1" },
    { key: "BLK", label: "BLK", fmt: "dec1" },
    { key: "TOV", label: "TOV", fmt: "dec1" },
    { key: "FGM", label: "FGM", fmt: "dec1" },
    { key: "FGA", label: "FGA", fmt: "dec1" },
    { key: "FG_PCT", label: "FG%", fmt: "pct" },
    { key: "FG3M", label: "3PM", fmt: "dec1" },
    { key: "FG3A", label: "3PA", fmt: "dec1" },
    { key: "FG3_PCT", label: "3P%", fmt: "pct" },
    { key: "FTM", label: "FTM", fmt: "dec1" },
    { key: "FTA", label: "FTA", fmt: "dec1" },
    { key: "FT_PCT", label: "FT%", fmt: "pct" },
    { key: "EFF", label: "EFF", fmt: "dec1" },
  ].filter(({ key }) => key !== category && key !== "PLAYER" && key !== "TEAM");

  // Add the main category col first
  const mainCol = { key: category, label: LEADER_LABELS[category] || category, fmt: ["FG_PCT","FG3_PCT","FT_PCT"].includes(category) ? "pct" : "dec1" };
  const statCols = [mainCol, ...cols];

  const sortCol = statsState.leaderSortCol || category;
  const sortDir = statsState.leaderSortDir;

  el.innerHTML = buildSortableTable(data, statCols, "PLAYER", "PLAYER", sortCol, sortDir,
    (col) => { statsState.leaderSortCol = col; statsState.leaderSortDir = statsState.leaderSortCol === col && statsState.leaderSortDir === "desc" ? "asc" : "desc"; statsState.leaderSortCol = col; renderLeaderTable(data, category); },
    null
  );
  attachTableSortHandlers(el, (col) => {
    if (statsState.leaderSortCol === col) statsState.leaderSortDir = statsState.leaderSortDir === "asc" ? "desc" : "asc";
    else { statsState.leaderSortCol = col; statsState.leaderSortDir = "desc"; }
    renderLeaderTable(statsState.leadersData, statsState.leaderCategory);
  });
  attachPlayerClickHandlers(el);
}

// ── Players ──────────────────────────────────────────────────────────────────

async function loadPlayers(measure) {
  statsState.playerMeasure = measure;
  statsState.playersData = null;
  statsShowLoading("statsPlayerTable", "Fetching player stats…");
  document.getElementById("statsRowCount").textContent = "";

  const { season, seasonType, perMode } = statsGetFilters();
  try {
    const result = await window.nba2kDesktop.fetchPlayerStats({ season, seasonType, perMode, measureType: measure });
    if (!result?.ok) { statsShowError("statsPlayerTable", result?.error || "Failed"); return; }
    statsState.playersData = result.data || [];
    const sortDefaults = { Base: "PTS", Advanced: "NET_RATING", Scoring: "PTS", Defense: "DEF_RATING", Misc: "PLUS_MINUS", Usage: "USG_PCT" };
    statsState.playerSortCol = sortDefaults[measure] || "PTS";
    statsState.playerSortDir = "desc";
    renderPlayerTable();
    updateCacheLabel(result.cached);
  } catch (err) {
    statsShowError("statsPlayerTable", String(err?.message || err));
  }
}

function renderPlayerTable() {
  const el = document.getElementById("statsPlayerTable");
  const countEl = document.getElementById("statsRowCount");
  if (!el || !statsState.playersData) return;

  const filter = statsState.playerFilter.toLowerCase();
  const rows = filter
    ? statsState.playersData.filter((r) => String(r.PLAYER_NAME || "").toLowerCase().includes(filter))
    : statsState.playersData;

  if (countEl) countEl.textContent = `${rows.length} players`;

  const cols = PLAYER_COLS[statsState.playerMeasure] || PLAYER_COLS.Base;
  el.innerHTML = buildSortableTable(rows, cols, "PLAYER_NAME", "PLAYER", statsState.playerSortCol, statsState.playerSortDir, null, null);

  attachTableSortHandlers(el, (col) => {
    if (statsState.playerSortCol === col) statsState.playerSortDir = statsState.playerSortDir === "asc" ? "desc" : "asc";
    else { statsState.playerSortCol = col; statsState.playerSortDir = "desc"; }
    renderPlayerTable();
  });
  attachPlayerClickHandlers(el);
}

// ── Teams ────────────────────────────────────────────────────────────────────

async function loadTeams(measure) {
  statsState.teamMeasure = measure;
  statsState.teamsData = null;
  statsShowLoading("statsTeamTable", "Fetching team stats…");

  const { season, seasonType, perMode } = statsGetFilters();
  try {
    const result = await window.nba2kDesktop.fetchTeamStats({ season, seasonType, perMode, measureType: measure });
    if (!result?.ok) { statsShowError("statsTeamTable", result?.error || "Failed"); return; }
    statsState.teamsData = result.data || [];
    statsState.teamSortCol = measure === "Base" ? "PTS" : "NET_RATING";
    statsState.teamSortDir = "desc";
    renderTeamTable();
    updateCacheLabel(result.cached);
  } catch (err) {
    statsShowError("statsTeamTable", String(err?.message || err));
  }
}

function renderTeamTable() {
  const el = document.getElementById("statsTeamTable");
  if (!el || !statsState.teamsData) return;
  const cols = TEAM_COLS[statsState.teamMeasure] || TEAM_COLS.Base;
  el.innerHTML = buildSortableTable(statsState.teamsData, cols, "TEAM_NAME", "TEAM", statsState.teamSortCol, statsState.teamSortDir, null, null);
  attachTableSortHandlers(el, (col) => {
    if (statsState.teamSortCol === col) statsState.teamSortDir = statsState.teamSortDir === "asc" ? "desc" : "asc";
    else { statsState.teamSortCol = col; statsState.teamSortDir = "desc"; }
    renderTeamTable();
  });
}

// ── Tracking ──────────────────────────────────────────────────────────────────

async function loadTracking(ptMeasureType) {
  statsState.trackingMeasure = ptMeasureType;
  statsState.trackingData = null;
  statsShowLoading("statsTrackingTable", "Fetching tracking data…");

  const { season, seasonType, perMode } = statsGetFilters();
  try {
    const result = await window.nba2kDesktop.fetchTrackingStats({ season, seasonType, perMode, ptMeasureType });
    if (!result?.ok) { statsShowError("statsTrackingTable", result?.error || "Failed"); return; }
    statsState.trackingData = result.data || [];
    const defaultSorts = { Drives: "DRIVES", PullUpShot: "PULL_UP_PTS", CatchShoot: "CATCH_SHOOT_PTS",
      PostTouch: "POST_TOUCHES", ElbowTouch: "ELBOW_TOUCHES", PaintTouch: "PAINT_TOUCHES", Passing: "PASSES_MADE" };
    statsState.trackingSortCol = defaultSorts[ptMeasureType] || "GP";
    statsState.trackingSortDir = "desc";
    renderTrackingTable();
    updateCacheLabel(result.cached);
  } catch (err) {
    statsShowError("statsTrackingTable", String(err?.message || err));
  }
}

function renderTrackingTable() {
  const el = document.getElementById("statsTrackingTable");
  if (!el || !statsState.trackingData) return;
  const cols = TRACKING_COLS[statsState.trackingMeasure] || TRACKING_COLS.Drives;
  el.innerHTML = buildSortableTable(statsState.trackingData, cols, "PLAYER_NAME", "PLAYER",
    statsState.trackingSortCol, statsState.trackingSortDir, null, null);
  attachTableSortHandlers(el, (col) => {
    if (statsState.trackingSortCol === col) statsState.trackingSortDir = statsState.trackingSortDir === "asc" ? "desc" : "asc";
    else { statsState.trackingSortCol = col; statsState.trackingSortDir = "desc"; }
    renderTrackingTable();
  });
  attachPlayerClickHandlers(el);
}

// ── Hustle ────────────────────────────────────────────────────────────────────

async function loadHustle() {
  statsState.hustleData = null;
  statsShowLoading("statsHustleTable", "Fetching hustle stats…");

  const { season, seasonType, perMode } = statsGetFilters();
  try {
    const result = await window.nba2kDesktop.fetchHustleStats({ season, seasonType, perMode });
    if (!result?.ok) { statsShowError("statsHustleTable", result?.error || "Failed"); return; }
    statsState.hustleData = result.data || [];
    statsState.hustleSortCol = "DEFLECTIONS";
    statsState.hustleSortDir = "desc";
    renderHustleTable();
    updateCacheLabel(result.cached);
  } catch (err) {
    statsShowError("statsHustleTable", String(err?.message || err));
  }
}

function renderHustleTable() {
  const el = document.getElementById("statsHustleTable");
  if (!el || !statsState.hustleData) return;
  el.innerHTML = buildSortableTable(statsState.hustleData, HUSTLE_COLS, "PLAYER_NAME", "PLAYER",
    statsState.hustleSortCol, statsState.hustleSortDir, null, null);
  attachTableSortHandlers(el, (col) => {
    if (statsState.hustleSortCol === col) statsState.hustleSortDir = statsState.hustleSortDir === "asc" ? "desc" : "asc";
    else { statsState.hustleSortCol = col; statsState.hustleSortDir = "desc"; }
    renderHustleTable();
  });
  attachPlayerClickHandlers(el);
}

function updateCacheLabel(cached) {
  const el = document.getElementById("statsCacheLabel");
  if (!el) return;
  el.textContent = cached ? "Cached" : "Live";
  el.className = "stats-cache-label " + (cached ? "cache-hit" : "cache-miss");
}

// ── Tab switching ─────────────────────────────────────────────────────────────

function switchStatsTab(tab) {
  showStatsMainContent(true);
  statsState.tab = tab;
  const ALL_TABS = ["leaders", "players", "teams", "tracking", "hustle"];
  ALL_TABS.forEach((t) => {
    const cap = t.charAt(0).toUpperCase() + t.slice(1);
    const view = document.getElementById(`stats${cap}View`);
    const btn = document.getElementById(`statsTab${cap}`);
    if (view) view.classList.toggle("hidden", t !== tab);
    if (btn) btn.classList.toggle("active", t === tab);
  });

  if (tab === "leaders" && !statsState.leadersData) loadLeaders(statsState.leaderCategory);
  if (tab === "players" && !statsState.playersData) loadPlayers(statsState.playerMeasure);
  if (tab === "teams" && !statsState.teamsData) loadTeams(statsState.teamMeasure);
  if (tab === "tracking" && !statsState.trackingData) loadTracking(statsState.trackingMeasure);
  if (tab === "hustle" && !statsState.hustleData) loadHustle();
}

// ── Init ──────────────────────────────────────────────────────────────────────

function statsInit() {
  if (!statsState.initialized) {
    statsState.initialized = true;

    // Tab buttons
    ["Leaders", "Players", "Teams", "Tracking", "Hustle"].forEach((name) => {
      const btn = document.getElementById(`statsTab${name}`);
      if (btn) btn.addEventListener("click", () => switchStatsTab(name.toLowerCase()));
    });

    // Tracking pills
    document.getElementById("trackingPills")?.querySelectorAll(".stat-pill").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.getElementById("trackingPills").querySelectorAll(".stat-pill").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        statsState.trackingData = null;
        loadTracking(btn.dataset.pt);
      });
    });

    // Back button from player detail
    document.getElementById("spdBackBtn")?.addEventListener("click", () => {
      showStatsMainContent(true);
      switchStatsTab(statsState.tab);
    });

    // Category pills (leaders)
    document.getElementById("statsCategoryPills")?.querySelectorAll(".stat-pill").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.getElementById("statsCategoryPills").querySelectorAll(".stat-pill").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        statsState.leaderSortCol = null;
        loadLeaders(btn.dataset.cat);
      });
    });

    // Measure pills (players)
    document.getElementById("statsMeasurePills")?.querySelectorAll(".stat-pill").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.getElementById("statsMeasurePills").querySelectorAll(".stat-pill").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        loadPlayers(btn.dataset.measure);
      });
    });

    // Measure pills (teams)
    document.getElementById("statsTeamMeasurePills")?.querySelectorAll(".stat-pill").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.getElementById("statsTeamMeasurePills").querySelectorAll(".stat-pill").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        loadTeams(btn.dataset.measure);
      });
    });

    // Filter inputs
    ["statsSeason", "statsSeasonType", "statsPerMode"].forEach((id) => {
      document.getElementById(id)?.addEventListener("change", () => {
        statsState.playersData = null; statsState.teamsData = null;
        statsState.leadersData = null; statsState.trackingData = null; statsState.hustleData = null;
        switchStatsTab(statsState.tab);
      });
    });

    // Refresh button
    document.getElementById("statsRefreshBtn")?.addEventListener("click", () => {
      statsState.playersData = null; statsState.teamsData = null;
      statsState.leadersData = null; statsState.trackingData = null; statsState.hustleData = null;
      switchStatsTab(statsState.tab);
    });

    // Player search filter
    document.getElementById("statsPlayerSearch")?.addEventListener("input", (e) => {
      statsState.playerFilter = e.target.value.trim();
      renderPlayerTable();
    });
  }

  // Load initial tab
  switchStatsTab(statsState.tab);
}

// Stats nav button
if (openStatsBtn) {
  openStatsBtn.addEventListener("click", () => showStatsPage());
}

// Shot Chart nav button
document.getElementById("openShotChartBtn")?.addEventListener("click", () => showShotChartPage());

// Progression nav button
document.getElementById("openProgressionBtn")?.addEventListener("click", () => showProgressionPage());

// ── Shot Chart Page ───────────────────────────────────────────────────────────

const _scPage = { inited: false, playerId: null, playerName: null, _cache: {}, _debounce: null };

function shotChartPageInit() {
  if (_scPage.inited) return;
  _scPage.inited = true;

  const searchInput = document.getElementById("scPlayerSearch");
  const resultsEl   = document.getElementById("scSearchResults");

  searchInput?.addEventListener("input", () => {
    clearTimeout(_scPage._debounce);
    const q = (searchInput.value || "").trim();
    if (q.length < 2) { resultsEl?.classList.add("hidden"); return; }
    _scPage._debounce = setTimeout(() => scSearchPlayers(q), 280);
  });

  // Close dropdown when clicking outside
  document.addEventListener("click", (e) => {
    if (!e.target.closest(".sc-search-wrap")) resultsEl?.classList.add("hidden");
  });

  document.getElementById("scClearBtn")?.addEventListener("click", () => {
    _scPage.playerId = null;
    _scPage.playerName = null;
    _spd.shots = null;
    _spd.loaded = false;
    document.getElementById("scPlayerHeader")?.classList.add("hidden");
    document.getElementById("scSearchResults")?.classList.add("hidden");
    const canvas = document.getElementById("spdShotCanvas");
    if (canvas) drawCourt(canvas.getContext("2d"), canvas.width, canvas.height);
    const msgEl = document.getElementById("spdShotMsg");
    if (msgEl) { msgEl.textContent = "Search a player to view their shot chart."; msgEl.className = "spd-shot-msg"; }
    if (document.getElementById("spdZoneStats")) document.getElementById("spdZoneStats").innerHTML = "";
  });

  document.getElementById("spdSeasonSelect")?.addEventListener("change", (e) => {
    _spd.season = e.target.value;
    _spd.loaded = false;
    if (_scPage.playerId) loadShotChart(e.target.value);
  });

  document.querySelectorAll(".spd-view-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".spd-view-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      _spd.view = btn.dataset.view;
      document.getElementById("spdDotControls")?.classList.toggle("hidden", _spd.view !== "dots");
      if (_spd.loaded && _spd.shots) renderCurrentShotView();
    });
  });

  document.querySelectorAll(".spd-stype-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".spd-stype-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      _spd.seasonType = btn.dataset.stype;
      _spd.loaded = false;
      if (_scPage.playerId) loadShotChart(_spd.season);
    });
  });

  document.getElementById("spdShowMade")?.addEventListener("click", function () {
    _spd.showMade = !_spd.showMade;
    this.classList.toggle("active", _spd.showMade);
    refreshShotChart();
  });
  document.getElementById("spdShowMissed")?.addEventListener("click", function () {
    _spd.showMissed = !_spd.showMissed;
    this.classList.toggle("active", _spd.showMissed);
    refreshShotChart();
  });

  document.getElementById("spdDotSize")?.addEventListener("input", function () {
    _spd.dotSize = Number(this.value);
    const v = document.getElementById("spdDotSizeVal");
    if (v) v.textContent = this.value;
    if (_spd.view === "dots") refreshShotChart();
  });

  document.getElementById("spdDotOpacity")?.addEventListener("input", function () {
    _spd.dotOpacity = Number(this.value);
    const v = document.getElementById("spdDotOpacityVal");
    if (v) v.textContent = this.value + "%";
    if (_spd.view === "dots") refreshShotChart();
  });

  document.getElementById("spdZonePills")?.querySelectorAll(".spd-zone-pill").forEach((btn) => {
    btn.addEventListener("click", () => {
      btn.classList.toggle("active");
      const allPills = [...document.getElementById("spdZonePills").querySelectorAll(".spd-zone-pill")];
      _spd.zoneFilter = allPills.filter((p) => p.classList.contains("active")).map((p) => p.dataset.zone);
      refreshShotChart();
    });
  });

  document.getElementById("spdAnglePills")?.querySelectorAll(".spd-zone-pill").forEach((btn) => {
    btn.addEventListener("click", () => {
      btn.classList.toggle("active");
      const allPills = [...document.getElementById("spdAnglePills").querySelectorAll(".spd-zone-pill")];
      _spd.angleFilter = allPills.filter((p) => p.classList.contains("active")).map((p) => p.dataset.angle);
      refreshShotChart();
    });
  });

  const updateDist = () => {
    _spd.distMin = Math.max(0, Math.min(35, Number(document.getElementById("spdDistMin")?.value || 0)));
    _spd.distMax = Math.max(_spd.distMin, Math.min(35, Number(document.getElementById("spdDistMax")?.value || 30)));
    refreshShotChart();
  };
  document.getElementById("spdDistMin")?.addEventListener("change", updateDist);
  document.getElementById("spdDistMax")?.addEventListener("change", updateDist);

  const canvas = document.getElementById("spdShotCanvas");
  if (canvas) drawCourt(canvas.getContext("2d"), canvas.width, canvas.height);
}

async function scSearchPlayers(query) {
  const season = document.getElementById("spdSeasonSelect")?.value || "2024-25";
  const resultsEl = document.getElementById("scSearchResults");
  if (!resultsEl) return;

  resultsEl.classList.remove("hidden");

  let players = _scPage._cache[season];
  if (!players) {
    resultsEl.innerHTML = '<div class="sc-search-loading">Searching…</div>';
    try {
      const result = await window.nba2kDesktop.fetchPlayerStats({ season, seasonType: "Regular Season", perMode: "PerGame", measureType: "Base" });
      if (!result?.ok || !result.data?.length) {
        resultsEl.innerHTML = '<div class="sc-search-empty">Could not load players.</div>';
        return;
      }
      players = result.data;
      _scPage._cache[season] = players;
    } catch {
      resultsEl.innerHTML = '<div class="sc-search-empty">Search failed. Try again.</div>';
      return;
    }
  }

  const lq = query.toLowerCase();
  const matches = players.filter((p) =>
    (p.PLAYER_NAME || p.PLAYER || "").toLowerCase().includes(lq)
  ).slice(0, 8);

  if (!matches.length) {
    resultsEl.innerHTML = `<div class="sc-search-empty">No players matching "${query}".</div>`;
    return;
  }

  resultsEl.innerHTML = matches.map((p) => {
    const name = p.PLAYER_NAME || p.PLAYER || "";
    const team = p.TEAM_ABBREVIATION || p.TEAM || "";
    const id   = p.PLAYER_ID || "";
    return `<button class="sc-result-btn" data-name="${name}" data-id="${id}">${name}<span class="sc-result-team">${team}</span></button>`;
  }).join("");

  resultsEl.querySelectorAll(".sc-result-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      scLoadChartForPlayer(btn.dataset.name, btn.dataset.id);
      resultsEl.classList.add("hidden");
      const inp = document.getElementById("scPlayerSearch");
      if (inp) inp.value = "";
    });
  });
}

function scLoadChartForPlayer(name, playerId) {
  _scPage.playerName = name;
  _scPage.playerId = playerId;

  const header = document.getElementById("scPlayerHeader");
  const nameEl = document.getElementById("scPlayerName");
  if (header) header.classList.remove("hidden");
  if (nameEl) nameEl.textContent = name;

  const useSeason = document.getElementById("spdSeasonSelect")?.value || "2024-25";
  _spd.playerId = playerId;
  _spd.season = useSeason;
  _spd.seasonType = "Regular Season";
  _spd.shots = null;
  _spd.loaded = false;
  _spd.view = "dots";
  _spd.zoneFilter = []; _spd.angleFilter = [];
  _spd.distMin = 0; _spd.distMax = 30;
  _spd.showMade = true; _spd.showMissed = true;
  _spd.dotSize = 4; _spd.dotOpacity = 75;

  const seasonSel = document.getElementById("spdSeasonSelect");
  if (seasonSel) seasonSel.value = useSeason;
  document.querySelectorAll(".spd-view-btn").forEach((b) => b.classList.toggle("active", b.dataset.view === "dots"));
  document.querySelectorAll(".spd-stype-btn").forEach((b) => b.classList.toggle("active", b.dataset.stype === "Regular Season"));
  document.getElementById("spdShowMade")?.classList.add("active");
  document.getElementById("spdShowMissed")?.classList.add("active");
  document.querySelectorAll(".spd-zone-pill").forEach((p) => p.classList.remove("active"));
  const dotSizeEl = document.getElementById("spdDotSize");
  if (dotSizeEl) { dotSizeEl.value = 4; const v = document.getElementById("spdDotSizeVal"); if (v) v.textContent = "4"; }
  const dotOpEl = document.getElementById("spdDotOpacity");
  if (dotOpEl) { dotOpEl.value = 75; const v = document.getElementById("spdDotOpacityVal"); if (v) v.textContent = "75%"; }
  const dMin = document.getElementById("spdDistMin"), dMax = document.getElementById("spdDistMax");
  if (dMin) dMin.value = 0; if (dMax) dMax.value = 30;
  document.getElementById("spdDotControls")?.classList.remove("hidden");
  if (document.getElementById("spdZoneStats")) document.getElementById("spdZoneStats").innerHTML = "";

  loadShotChart(useSeason);
}

// ═══════════════════════════════════════════════════════════════
// PROGRESSION TRACKER v2
// ═══════════════════════════════════════════════════════════════

const PROG_TEAM_COLORS = {
  "Philadelphia 76ers":    "#1a7ee0",
  "Milwaukee Bucks":       "#00b060",
  "Chicago Bulls":         "#d01433",
  "Cleveland Cavaliers":   "#9a1a3e",
  "Boston Celtics":        "#00a84a",
  "LA Clippers":           "#c8102e",
  "Memphis Grizzlies":     "#5d76a9",
  "Atlanta Hawks":         "#e03a3e",
  "Miami Heat":            "#e0303a",
  "Charlotte Hornets":     "#7b5fbf",
  "Utah Jazz":             "#3a80d2",
  "Sacramento Kings":      "#8452b0",
  "New York Knicks":       "#1a7ee0",
  "LA Lakers":             "#8040be",
  "Orlando Magic":         "#0077c0",
  "Dallas Mavericks":      "#0076b0",
  "Brooklyn Nets":         "#7080a0",
  "Denver Nuggets":        "#2a7aba",
  "Indiana Pacers":        "#d4a820",
  "New Orleans Pelicans":  "#1a5aaa",
  "Detroit Pistons":       "#c8102e",
  "Toronto Raptors":       "#ce1141",
  "Houston Rockets":       "#ce1141",
  "San Antonio Spurs":     "#8090a8",
  "Phoenix Suns":          "#5a3fa8",
  "Oklahoma City Thunder": "#007ac1",
  "Minnesota Timberwolves":"#1a6898",
  "Portland Trail Blazers":"#e03a3e",
  "Golden State Warriors": "#2055b8",
  "Washington Wizards":    "#1a4898",
};

const _pt = {
  inited: false,
  platform: "console",
  view: "grid",           // "grid" | "focus"
  data: { console: null, pc: null },
  unsub: { console: null, pc: null },
  catPrios: {},
  focusTeam: null,
  search: "",
  sort: "name",
  criticalDismissed: false,
  criticalFilter: false,
  sprint: {
    phase: "off",        // "off" | "select" | "active"
    cells: new Set(),    // "teamKey:catKey" — selected cells
  },
  _ddTarget: null,
};

// ── Helpers ──────────────────────────────────────────────────────────

function _ptCatPrio(key) {
  return _pt.catPrios[key] || PROG_CATS.find(c => c.key === key)?.p || "low";
}

function _ptTeamColor(name) {
  return PROG_TEAM_COLORS[name] || "#4da8ff";
}

function _ptTeamStats(teamData) {
  const cats = PROG_CATS;
  let done = 0, wo = 0, ir = 0, ns = 0;
  for (const c of cats) {
    const st = (teamData[c.key] || "ns");
    if (st === "done") done++;
    else if (st === "wo") wo++;
    else if (st === "ir") ir++;
    else ns++;
  }
  return { done, wo, ir, ns, total: cats.length, pct: Math.round(done / cats.length * 100) };
}

// ── Init ──────────────────────────────────────────────────────────────

function progressionPageInit() {
  const canEdit = _currentRole !== "viewer";

  if (!_pt.inited) {
    _pt.inited = true;

    // Platform tabs
    document.getElementById("ptTabConsole")?.addEventListener("click", () => {
      _pt.platform = "console";
      document.getElementById("ptTabConsole")?.classList.add("active");
      document.getElementById("ptTabPc")?.classList.remove("active");
      _ptSubscribe("console");
    });
    document.getElementById("ptTabPc")?.addEventListener("click", () => {
      _pt.platform = "pc";
      document.getElementById("ptTabPc")?.classList.add("active");
      document.getElementById("ptTabConsole")?.classList.remove("active");
      _ptSubscribe("pc");
    });

    // View switcher
    document.getElementById("progressionPage")?.addEventListener("click", async (e) => {
      const viewBtn = e.target.closest(".pt-view-btn");
      if (viewBtn) {
        _pt.view = viewBtn.dataset.view;
        document.querySelectorAll(".pt-view-btn").forEach(b => b.classList.toggle("active", b === viewBtn));
        if (_pt.view === "focus" && !_pt.focusTeam && PROG_TEAMS.length) {
          _pt.focusTeam = progKey(PROG_TEAMS[0]);
        }
        _ptRenderContent();
        return;
      }

      // Sort buttons
      const sortBtn = e.target.closest(".pt-sort-btn");
      if (sortBtn) {
        _pt.sort = sortBtn.dataset.sort;
        document.querySelectorAll(".pt-sort-btn").forEach(b => b.classList.toggle("active", b === sortBtn));
        _ptRenderSidebar();
        return;
      }

      // Team row in sidebar
      const teamRow = e.target.closest(".pt-team-row[data-team]");
      if (teamRow && !e.target.closest(".pt-sprint-check")) {
        const tk = teamRow.dataset.team;
        if (_pt.view === "focus") {
          _pt.focusTeam = tk;
          document.querySelectorAll(".pt-team-row").forEach(r => r.classList.toggle("active", r.dataset.team === tk));
          _ptRenderFocus();
        } else if (_pt.view === "grid") {
          // Scroll the grid to that team's row
          const row = document.querySelector(`.pt-grid-row[data-team="${tk}"]`);
          row?.scrollIntoView({ behavior: "smooth", block: "center" });
          document.querySelectorAll(".pt-team-row").forEach(r => r.classList.toggle("active", r.dataset.team === tk));
        }
        return;
      }

      // Grid cell click
      const gridCell = e.target.closest(".pt-grid-cell[data-team]");
      if (gridCell && canEdit) {
        if (_pt.sprint.phase === "select") {
          _ptSprintToggleCell(gridCell.dataset.team, gridCell.dataset.cat);
          return;
        }
        _ptShowDropdown(gridCell);
        return;
      }

      // Focus card click
      const focusCard = e.target.closest(".pt-focus-card[data-team]");
      if (focusCard && canEdit) {
        _ptShowDropdown(focusCard);
        return;
      }

      // Rev cell
      const revCell = e.target.closest(".pt-grid-rev-cell[data-team]");
      if (revCell && canEdit) {
        await _ptToggleRev(revCell.dataset.team);
        return;
      }

    });

    // Dropdown is a portal outside #progressionPage — needs its own listener
    document.getElementById("ptDropdown")?.addEventListener("click", async (e) => {
      const ddOpt = e.target.closest(".pt-dd-opt");
      if (ddOpt && _pt._ddTarget) {
        const { teamKey, catKey } = _pt._ddTarget;
        _ptHideDropdown();
        await _ptSetStatus(teamKey, catKey, ddOpt.dataset.st);
      }
    });

    // Outside click closes dropdown
    document.addEventListener("click", (e) => {
      if (!e.target.closest("#ptDropdown") && !e.target.closest("[data-team][data-cat]")) {
        _ptHideDropdown();
      }
    });

    // Search
    document.getElementById("ptSearch")?.addEventListener("input", (e) => {
      _pt.search = e.target.value.toLowerCase();
      _ptRenderSidebar();
      if (_pt.view === "grid") _ptRenderGrid();
    });

    // Sprint
    document.getElementById("ptSprintToggle")?.addEventListener("click", _ptSprintClickToggle);
    document.getElementById("ptSprintBar")?.addEventListener("click", (e) => {
      if (e.target.closest("#ptSprintStart"))  _ptSprintStart();
      if (e.target.closest("#ptSprintCancel")) _ptSprintOff();
      if (e.target.closest("#ptSprintEnd"))    _ptSprintOff();
    });

    // Critical banner
    document.getElementById("ptCriticalShow")?.addEventListener("click", () => {
      _pt.criticalFilter = true;
      _ptRenderContent();
      document.getElementById("ptCritical")?.classList.add("hidden");
    });
    document.getElementById("ptCriticalDismiss")?.addEventListener("click", () => {
      _pt.criticalDismissed = true;
      document.getElementById("ptCritical")?.classList.add("hidden");
    });

    // WIP
    document.getElementById("ptEditWipBtn")?.addEventListener("click", () => {
      const ta = document.getElementById("ptWipTextarea");
      if (ta) ta.value = (_pt.data[_pt.platform]?.workingOn || []).join("\n");
      document.getElementById("ptWipEditor")?.classList.remove("hidden");
      ta?.focus();
    });
    document.getElementById("ptWipSave")?.addEventListener("click", async () => {
      const ta = document.getElementById("ptWipTextarea");
      if (!ta || !_fireDb) return;
      const items = ta.value.split("\n").map(s => s.trim()).filter(Boolean);
      try {
        await _fireDb.collection("progression").doc(_pt.platform)
          .set({ workingOn: items }, { merge: true });
        document.getElementById("ptWipEditor")?.classList.add("hidden");
      } catch (e) { console.error("WIP save:", e); }
    });
    const wipClose = () => document.getElementById("ptWipEditor")?.classList.add("hidden");
    document.getElementById("ptWipCancel")?.addEventListener("click", wipClose);
    document.getElementById("ptWipCancel2")?.addEventListener("click", wipClose);
  }

  document.getElementById("ptEditWipBtn")?.classList.toggle("hidden", !canEdit);
  _ptSubscribe(_pt.platform);
  const existing = _pt.data[_pt.platform];
  _ptRenderWipStrip(existing?.workingOn || []);
}

// ── Firestore ─────────────────────────────────────────────────────────

function _ptSubscribe(platform) {
  if (!_fireDb || _pt.unsub[platform]) return;
  _pt.unsub[platform] = _fireDb.collection("progression").doc(platform)
    .onSnapshot(snap => {
      _pt.data[platform] = snap.exists ? snap.data() : {};
      if (_pt.platform === platform) _ptRender();
    }, err => console.error("Progression snapshot:", err));
}

// ── Main render ───────────────────────────────────────────────────────

function _ptRender() {
  const data = _pt.data[_pt.platform] || {};
  _pt.catPrios = data.catPriorities || {};
  _ptRenderHeader(data);
  _ptRenderSidebar();
  _ptRenderCritical(data);
  _ptRenderContent();
  if (_pt.sprint.phase === "active") _ptUpdateSprintBar();
}

// ── Header ────────────────────────────────────────────────────────────

function _ptRenderHeader(data) {
  let ns = 0, wo = 0, ir = 0, done = 0;
  const total = PROG_TEAMS.length * PROG_CATS.length;
  for (const team of PROG_TEAMS) {
    const tk = progKey(team);
    const td = data[tk] || {};
    for (const c of PROG_CATS) {
      const st = td[c.key] || "ns";
      if (st === "done") done++;
      else if (st === "wo") wo++;
      else if (st === "ir") ir++;
      else ns++;
    }
  }
  const pct = Math.round(done / total * 100);
  const circ = 2 * Math.PI * 32;
  const offset = circ - (pct / 100) * circ;

  const fill = document.getElementById("ptRingFill");
  if (fill) {
    fill.style.strokeDasharray = `${circ} ${circ}`;
    fill.style.strokeDashoffset = offset;
    const col = pct >= 80 ? "#4ade80" : pct >= 40 ? "#4da8ff" : "#f59e0b";
    fill.style.stroke = col;
  }
  const ptPct = document.getElementById("ptRingPct");
  if (ptPct) ptPct.textContent = pct + "%";
  const ptDone = document.getElementById("ptDoneCount");
  if (ptDone) ptDone.textContent = done;
  const ptTotal = document.getElementById("ptTotalCount");
  if (ptTotal) ptTotal.textContent = total;

  const bd = document.getElementById("ptBreakdown");
  if (bd) bd.innerHTML = [
    ["ns", ns, "NS"], ["wo", wo, "WO"], ["ir", ir, "IR"], ["done", done, "Done"]
  ].map(([k, v, l]) =>
    `<div class="pt-bd-item pt-bd-${k}"><span class="pt-bd-dot"></span>${v} ${l}</div>`
  ).join("");

  _ptRenderWipStrip(data.workingOn || []);
}

// ── WIP strip ────────────────────────────────────────────────────────

function _ptRenderWipStrip(items) {
  const strip = document.getElementById("ptWipStrip");
  const list  = document.getElementById("ptWipItems");
  if (!strip || !list) return;
  const canEdit = _currentRole !== "viewer";
  if (!items.length && !canEdit) {
    strip.classList.add("hidden");
    return;
  }
  list.innerHTML = items.length
    ? items.map(w => `<span class="pt-wip-item">${w}</span>`).join("")
    : `<span class="pt-wip-empty">Nothing logged yet</span>`;
  strip.classList.remove("hidden");
}

// ── Critical path ─────────────────────────────────────────────────────

function _ptRenderCritical(data) {
  if (_pt.criticalDismissed) return;
  const highCats = PROG_CATS.filter(c => (c.p === "high" || _pt.catPrios[c.key] === "high"));
  let blocked = 0;
  for (const team of PROG_TEAMS) {
    const td = data[progKey(team)] || {};
    for (const c of highCats) {
      if ((td[c.key] || "ns") === "ns") blocked++;
    }
  }
  const banner = document.getElementById("ptCritical");
  if (!banner) return;
  if (blocked > 0) {
    document.getElementById("ptCriticalText").textContent =
      `${blocked} high-priority cell${blocked !== 1 ? "s" : ""} not yet started`;
    banner.classList.remove("hidden");
  } else {
    banner.classList.add("hidden");
  }
}

// ── Sidebar ───────────────────────────────────────────────────────────

function _ptRenderSidebar() {
  const el = document.getElementById("ptTeamList");
  if (!el) return;
  const data = _pt.data[_pt.platform] || {};
  let teams = PROG_TEAMS.map(name => {
    const tk = progKey(name);
    const td = data[tk] || {};
    const stats = _ptTeamStats(td);
    return { name, tk, stats };
  });
  if (_pt.search) teams = teams.filter(t => t.name.toLowerCase().includes(_pt.search));
  if (_pt.sort === "pct")  teams.sort((a, b) => b.stats.pct - a.stats.pct);
  else if (_pt.sort === "done") teams.sort((a, b) => b.stats.done - a.stats.done);
  else teams.sort((a, b) => a.name.localeCompare(b.name));

  el.innerHTML = teams.map(({ name, tk, stats }) => {
    const color = _ptTeamColor(name);
    const circ = 2 * Math.PI * 10;
    const offset = circ - (stats.pct / 100) * circ;
    const ringColor = stats.pct >= 100 ? "#4ade80" : stats.pct >= 60 ? "#4da8ff" : stats.pct >= 30 ? "#f59e0b" : "#ef4444";
    const isFocus = _pt.view === "focus" && _pt.focusTeam === tk;
    const isComplete = stats.done === stats.total;
    return `<div class="pt-team-row${isFocus ? " active" : ""}${isComplete ? " pt-tr-complete" : ""}" data-team="${tk}">
      <div class="pt-mini-ring">
        <svg viewBox="0 0 24 24">
          <circle class="pt-mini-ring-track" cx="12" cy="12" r="10"/>
          <circle class="pt-mini-ring-fill" cx="12" cy="12" r="10"
            stroke="${ringColor}"
            stroke-dasharray="${circ} ${circ}"
            stroke-dashoffset="${offset}"
            stroke-linecap="round"
            transform="rotate(-90 12 12)"/>
        </svg>
        <div class="pt-mini-ring-label">${stats.pct}</div>
      </div>
      <div class="pt-team-info">
        <div class="pt-team-name-sb">${name.replace(" 76ers","").replace("Portland Trail ","PDX ").replace("Golden State ","GS ").replace("Oklahoma City ","OKC ").replace("Minnesota ","MIN ")}</div>
        <div class="pt-team-frac">${stats.done}/${stats.total}</div>
      </div>
      ${isComplete ? `<div class="pt-team-done-badge"><svg viewBox="0 0 10 10" fill="none"><path d="M2 5l2 2 4-4" stroke="#4ade80" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/></svg></div>` : ""}
    </div>`;
  }).join("");
}

// ── Content dispatcher ────────────────────────────────────────────────

function _ptRenderContent() {
  if (_pt.view === "grid") _ptRenderGrid();
  else if (_pt.view === "focus") _ptRenderFocus();
}

// ── GRID VIEW ─────────────────────────────────────────────────────────

function _ptRenderGrid() {
  const el = document.getElementById("ptContent");
  if (!el) return;
  const data = _pt.data[_pt.platform] || {};
  const canEdit = _currentRole !== "viewer";
  const highCats = new Set(PROG_CATS.filter(c => _ptCatPrio(c.key) === "high").map(c => c.key));

  let teams = PROG_TEAMS;
  if (_pt.search) teams = teams.filter(t => t.toLowerCase().includes(_pt.search));

  const visCats = PROG_CATS;

  const headerCells = visCats.map(c => {
    const prio = _ptCatPrio(c.key);
    return `<th class="pt-grid-cat-th">
      <div class="pt-cat-pip pt-pip-${prio}"></div>
      <div class="pt-cat-name">${c.s}</div>
    </th>`;
  }).join("");

  const rows = teams.map(team => {
    const tk = progKey(team);
    const td = data[tk] || {};
    const stats = _ptTeamStats(td);
    const isComplete = stats.done === stats.total;
    const dim = _pt.criticalFilter &&
      !visCats.some(c => _ptCatPrio(c.key) === "high" && (td[c.key] || "ns") === "ns")
      ? " pt-dim" : "";

    const cells = visCats.map(c => {
      const st = td[c.key] || "ns";
      const key = `${tk}:${c.key}`;
      const inSprint = _pt.sprint.cells.has(key);
      let sprintCls = "";
      if (_pt.sprint.phase === "select") sprintCls = inSprint ? " pt-sprint-sel" : "";
      else if (_pt.sprint.phase === "active") sprintCls = inSprint ? (st === "done" ? " pt-sprint-cell-done" : " pt-sprint-cell") : "";
      let inner = st === "ns"
        ? `<span class="pt-cell-dash">—</span>`
        : `<span class="pt-cell-pill">${PROG_STATUS_LABEL[st]}</span>`;
      if (_pt.sprint.phase === "select" && inSprint) inner += `<span class="pt-sprint-check-mark">✓</span>`;
      return `<td class="pt-grid-cell pt-st-${st}${sprintCls}"
        data-team="${tk}" data-cat="${c.key}">${inner}</td>`;
    }).join("");

    const rev = td.finalReview === true;
    const color = _ptTeamColor(team);
    return `<tr class="pt-grid-row${isComplete ? " pt-grid-row-complete" : ""}${dim}" data-team="${tk}">
      <td class="pt-grid-team-td">
        <div class="pt-team-td-inner" style="border-left-color:${isComplete ? "#4ade80" : color}20">
          <div class="pt-grid-team-name" style="border-left: 3px solid ${color}; padding-left:8px; margin-left:-8px; border-radius:1px">${team}</div>
          <div class="pt-grid-team-pct">${stats.pct}%</div>
        </div>
      </td>
      ${cells}
      <td class="pt-grid-rev-cell${rev ? " pt-rev-done-cell" : ""}" data-team="${tk}" data-rev="1">${rev ? "✓" : ""}</td>
    </tr>`;
  }).join("");

  const scroll = el.scrollTop;
  const scrollL = el.scrollLeft;
  el.innerHTML = `<div class="pt-grid-wrap"><table class="pt-grid-table">
    <thead><tr>
      <th class="pt-grid-team-th">Team</th>
      ${headerCells}
      <th class="pt-grid-rev-th">Rev</th>
    </tr></thead>
    <tbody>${rows}</tbody>
  </table></div>`;
  el.scrollTop = scroll;
  el.scrollLeft = scrollL;
}

// ── FOCUS VIEW ────────────────────────────────────────────────────────

function _ptRenderFocus() {
  const el = document.getElementById("ptContent");
  if (!el) return;
  const data = _pt.data[_pt.platform] || {};
  const canEdit = _currentRole !== "viewer";

  if (!_pt.focusTeam) {
    el.innerHTML = `<div class="pt-focus-placeholder">
      <svg viewBox="0 0 48 48" fill="none" width="48" height="48"><circle cx="24" cy="24" r="20" stroke="currentColor" stroke-width="2"/><circle cx="24" cy="24" r="8" fill="currentColor"/></svg>
      <span>Select a team from the sidebar to focus</span>
    </div>`;
    return;
  }

  const teamName = PROG_TEAMS.find(t => progKey(t) === _pt.focusTeam) || _pt.focusTeam;
  const td = data[_pt.focusTeam] || {};
  const stats = _ptTeamStats(td);
  const color = _ptTeamColor(teamName);

  const circ = 2 * Math.PI * 26;
  const offset = circ - (stats.pct / 100) * circ;
  const ringColor = stats.pct >= 100 ? "#4ade80" : stats.pct >= 60 ? "#4da8ff" : stats.pct >= 30 ? "#f59e0b" : "#ef4444";

  const priGroups = [
    { label: "High Priority", key: "high", cats: PROG_CATS.filter(c => _ptCatPrio(c.key) === "high") },
    { label: "Mid Priority",  key: "mid",  cats: PROG_CATS.filter(c => _ptCatPrio(c.key) === "mid")  },
    { label: "Low Priority",  key: "low",  cats: PROG_CATS.filter(c => _ptCatPrio(c.key) === "low")  },
  ].filter(g => g.cats.length > 0);

  const sections = priGroups.map(g => `
    <div class="pt-focus-prio-section">
      <div class="pt-focus-prio-label">${g.label}</div>
      <div class="pt-focus-cards">${
        g.cats.map(c => {
          const st = td[c.key] || "ns";
          return `<div class="pt-focus-card pt-fcs-${st}" data-team="${_pt.focusTeam}" data-cat="${c.key}">
            <div class="pt-focus-card-name">${c.label}</div>
            <div class="pt-focus-card-status">
              <span class="pt-focus-card-dot"></span>${PROG_STATUS_LABEL[st]}
            </div>
          </div>`;
        }).join("")
      }</div>
    </div>`).join("");

  el.innerHTML = `<div class="pt-focus">
    <div class="pt-focus-panel">
      <div class="pt-focus-hero" style="border-left-color:${color}; background: linear-gradient(135deg, ${color}08 0%, transparent 60%)">
        <div class="pt-focus-ring-wrap">
          <svg class="pt-focus-ring-svg" viewBox="0 0 56 56">
            <circle class="pt-focus-ring-track" cx="28" cy="28" r="23"/>
            <circle class="pt-focus-ring-fill" cx="28" cy="28" r="23"
              stroke="${ringColor}"
              stroke-dasharray="${circ} ${circ}"
              stroke-dashoffset="${offset}"
              stroke-linecap="round"
              transform="rotate(-90 28 28)"/>
          </svg>
          <div class="pt-focus-ring-inner">
            <span class="pt-focus-ring-pct">${stats.pct}%</span>
          </div>
        </div>
        <div class="pt-focus-hero-info">
          <div class="pt-focus-team-name">${teamName}</div>
          <div class="pt-focus-meta">
            <span><strong>${stats.done}</strong> done</span>
            <span><strong>${stats.wo}</strong> in progress</span>
            <span><strong>${stats.ns}</strong> not started</span>
            ${td.finalReview ? '<span style="color:#4ade80">✓ Final Review</span>' : ""}
          </div>
        </div>
      </div>
      ${sections}
    </div>
  </div>`;
}

// ── Dropdown ──────────────────────────────────────────────────────────

function _ptShowDropdown(cell) {
  const dd = document.getElementById("ptDropdown");
  if (!dd) return;
  const tk = cell.dataset.team;
  const ck = cell.dataset.cat;
  _pt._ddTarget = { teamKey: tk, catKey: ck };
  const curSt = ((_pt.data[_pt.platform] || {})[tk] || {})[ck] || "ns";
  dd.querySelectorAll(".pt-dd-opt").forEach(btn => {
    btn.classList.toggle("pt-dd-current", btn.dataset.st === curSt);
  });
  const rect = cell.getBoundingClientRect();
  const ddH = 180;
  const spaceBelow = window.innerHeight - rect.bottom;
  const top = spaceBelow > ddH
    ? rect.bottom + window.scrollY + 4
    : rect.top + window.scrollY - ddH - 4;
  dd.style.top  = top + "px";
  dd.style.left = Math.min(rect.left, window.innerWidth - 170) + "px";
  dd.classList.remove("hidden");
}

function _ptHideDropdown() {
  document.getElementById("ptDropdown")?.classList.add("hidden");
  _pt._ddTarget = null;
}

// ── Status write ──────────────────────────────────────────────────────

async function _ptSetStatus(teamKey, catKey, status) {
  if (!_fireDb) return;
  const from = ((_pt.data[_pt.platform] || {})[teamKey] || {})[catKey] || "ns";
  if (from === status) return;
  try {
    await _fireDb.collection("progression").doc(_pt.platform)
      .set({ [teamKey]: { [catKey]: status } }, { merge: true });
  } catch (e) { console.error("Progression update:", e); }
}

async function _ptSetCatPrio(catKey, prio) {
  if (!_fireDb) return;
  try {
    await _fireDb.collection("progression").doc(_pt.platform)
      .set({ catPriorities: { [catKey]: prio } }, { merge: true });
  } catch (e) { console.error("Cat priority:", e); }
}

async function _ptToggleRev(teamKey) {
  if (!_fireDb) return;
  const td = (_pt.data[_pt.platform] || {})[teamKey] || {};
  const next = !(td.finalReview === true);
  try {
    await _fireDb.collection("progression").doc(_pt.platform)
      .set({ [teamKey]: { finalReview: next } }, { merge: true });
  } catch (e) { console.error("Rev toggle:", e); }
}

// ── Sprint mode ───────────────────────────────────────────────────────

function _ptSprintClickToggle() {
  if (_pt.sprint.phase === "off") {
    // Enter selection mode
    _pt.sprint.phase = "select";
    _pt.sprint.cells.clear();
    document.getElementById("ptSprintToggle")?.classList.add("active");
    document.getElementById("ptSprintBar")?.classList.remove("hidden");
    _ptUpdateSprintBar();
    _ptRenderContent();
  } else {
    _ptSprintOff();
  }
}

function _ptSprintStart() {
  if (_pt.sprint.cells.size === 0) return;
  _pt.sprint.phase = "active";
  _ptUpdateSprintBar();
  _ptRenderContent();
}

function _ptSprintOff() {
  _pt.sprint.phase = "off";
  _pt.sprint.cells.clear();
  document.getElementById("ptSprintBar")?.classList.add("hidden");
  document.getElementById("ptSprintToggle")?.classList.remove("active");
  _ptRenderContent();
}

function _ptSprintToggleCell(teamKey, catKey) {
  const key = `${teamKey}:${catKey}`;
  if (_pt.sprint.cells.has(key)) _pt.sprint.cells.delete(key);
  else _pt.sprint.cells.add(key);
  _ptUpdateSprintBar();
  // Just update cell highlights without full re-render for speed
  _ptApplySprintHighlights();
}

function _ptUpdateSprintBar() {
  const bar = document.getElementById("ptSprintBar");
  if (!bar) return;
  const total = _pt.sprint.cells.size;
  const data  = _pt.data[_pt.platform] || {};

  if (_pt.sprint.phase === "select") {
    bar.innerHTML = `
      <svg viewBox="0 0 16 16" fill="none" width="13" height="13"><path d="M9 1L3 9h5l-1 6 6-8H8l1-6z" stroke="#fbbf24" stroke-width="1.3" stroke-linejoin="round"/></svg>
      <span class="pt-sprint-label">Select cells to sprint</span>
      <span class="pt-sprint-sel-count">${total} cell${total !== 1 ? "s" : ""} selected</span>
      <button id="ptSprintStart" class="pt-sprint-start-btn" ${total === 0 ? "disabled" : ""}>Start Sprint →</button>
      <button id="ptSprintCancel" class="pt-sprint-end">Cancel</button>`;
    return;
  }

  // Active phase
  let done = 0;
  for (const key of _pt.sprint.cells) {
    const [tk, ck] = key.split(":");
    if (((data[tk] || {})[ck] || "ns") === "done") done++;
  }
  const pct = total > 0 ? Math.round(done / total * 100) : 0;
  const allDone = done === total && total > 0;
  bar.innerHTML = `
    <svg viewBox="0 0 16 16" fill="none" width="13" height="13"><path d="M9 1L3 9h5l-1 6 6-8H8l1-6z" fill="#fbbf24" stroke="#fbbf24" stroke-width="0.5" stroke-linejoin="round"/></svg>
    <span class="pt-sprint-label">${allDone ? "Sprint Complete! 🎉" : "Sprint"}</span>
    <div class="pt-sprint-track"><div class="pt-sprint-fill" style="width:${pct}%"></div></div>
    <span class="pt-sprint-count">${done} / ${total} done</span>
    <button id="ptSprintEnd" class="pt-sprint-end">End Sprint</button>`;
}

function _ptApplySprintHighlights() {
  document.querySelectorAll(".pt-grid-cell[data-team]").forEach(cell => {
    const key = `${cell.dataset.team}:${cell.dataset.cat}`;
    const inSprint = _pt.sprint.cells.has(key);
    cell.classList.toggle("pt-sprint-sel", inSprint && _pt.sprint.phase === "select");
    if (_pt.sprint.phase === "active") {
      const data = _pt.data[_pt.platform] || {};
      const st = ((data[cell.dataset.team] || {})[cell.dataset.cat] || "ns");
      cell.classList.toggle("pt-sprint-cell", inSprint);
      cell.classList.toggle("pt-sprint-cell-done", inSprint && st === "done");
    }
  });
  _ptUpdateSprintBar();
}

// ── Legacy aliases used by old code paths (kept for safety) ──────────

function _progRender() { _ptRender(); }

// ── Stubs for old function names (no-ops, replaced above) ─────────────

function _progCatPrio(key) {
  return _ptCatPrio(key);
}

// ═══════════════════════════════════════════════════════════════
// FIREBASE — AUTH + FIRESTORE + NOTES + USERS
// ═══════════════════════════════════════════════════════════════

const FIREBASE_CONFIG = {
  apiKey: "AIzaSyA80qGfe5mDgUy06I1oM-ewyaV0ivja39U",
  authDomain: "atd-app-database.firebaseapp.com",
  projectId: "atd-app-database",
  storageBucket: "atd-app-database.firebasestorage.app",
  messagingSenderId: "979959368483",
  appId: "1:979959368483:web:cbdda2064b05cce4be1a96",
};

const ROLE_LABELS = { head_admin: "Head Admin", admin: "Admin", viewer: "Viewer" };

let _fireDb   = null;
let _fireAuth = null;
let _currentUser = null;
let _currentRole = null;
let _notesUnsub  = null;

function initFirebase() {
  if (typeof firebase === "undefined") return false;
  if (!firebase.apps.length) firebase.initializeApp(FIREBASE_CONFIG);
  if (!_fireDb)   _fireDb   = firebase.firestore();
  if (!_fireAuth) _fireAuth = firebase.auth();
  return true;
}

function safeHtml(str) {
  return String(str || "")
    .replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/\n/g, "<br>");
}

// Converts a username to a deterministic internal auth email.
// Using base64 of the lowercased username keeps it unique and valid.
function usernameToAuthEmail(username) {
  try {
    const encoded = btoa(unescape(encodeURIComponent(username.toLowerCase())))
      .replace(/\+/g, "-").replace(/\//g, "_").replace(/=/g, "");
    return `${encoded}@atd2k26.app`;
  } catch {
    const hex = Array.from(username.toLowerCase())
      .map(c => c.charCodeAt(0).toString(16).padStart(2, "0")).join("");
    return `${hex}@atd2k26.app`;
  }
}

function getDisplayName() {
  return localStorage.getItem("nba2k26_display_name") || "";
}

// ── Auth state ────────────────────────────────────────────────

function onLoggedIn(firestoreData) {
  const name = firestoreData.displayName || _currentUser.email;
  const role = _currentRole;
  localStorage.setItem("nba2k26_display_name", name);

  document.getElementById("sidebarUserName").textContent = name;
  document.getElementById("sidebarUserRole").textContent = ROLE_LABELS[role] || role;
  document.getElementById("sidebarAvatar").textContent   = name.slice(0, 2).toUpperCase();
  document.getElementById("authStatusDot")?.classList.add("status-dot-online");
  document.getElementById("authStatusLabel").textContent = "Connected";

  // Role-based nav visibility
  document.getElementById("openNotesBtn")?.classList.toggle("hidden", role === "viewer");
  document.getElementById("openUsersBtn")?.classList.toggle("hidden", role !== "head_admin");
  document.getElementById("openShotChartBtn")?.classList.toggle("hidden", role === "viewer");

  // Show app, hide login
  document.getElementById("loginPage").classList.add("hidden");
  document.querySelector(".app-shell").classList.remove("hidden");

  // Chat
  document.getElementById("chatBubble")?.classList.remove("hidden");
  subscribeToUnreadChats();

  renderRecentPlayers();
  showDashboard();
}

function onLoggedOut(message) {
  if (_notesUnsub) { _notesUnsub(); _notesUnsub = null; }
  if (_clUnsub)    { _clUnsub();    _clUnsub = null; _dbInited = false; }
  _currentUser = null;
  _currentRole = null;

  // Chat cleanup
  document.getElementById("chatBubble")?.classList.add("hidden");
  closeChatPanel();
  if (_C.unsubUnread) { _C.unsubUnread(); _C.unsubUnread = null; }

  document.querySelector(".app-shell").classList.add("hidden");
  const loginPage = document.getElementById("loginPage");
  loginPage.classList.remove("hidden");

  const errEl = document.getElementById("loginError");
  if (errEl) {
    errEl.textContent = message || "";
    errEl.classList.toggle("hidden", !message);
  }
  // Reset login form
  const btn = document.getElementById("loginBtn");
  if (btn) { btn.disabled = false; btn.textContent = "Sign In"; }
}

function startAuth() {
  if (!initFirebase()) {
    onLoggedOut("Firebase unavailable — check your connection.");
    return;
  }
  _fireAuth.onAuthStateChanged(async (user) => {
    if (!user) { onLoggedOut(); return; }
    try {
      const doc = await _fireDb.collection("users").doc(user.uid).get();
      if (!doc.exists) {
        await _fireAuth.signOut();
        onLoggedOut("Account not found. Contact your administrator.");
        return;
      }
      const data = doc.data();
      if (data.disabled) {
        await _fireAuth.signOut();
        onLoggedOut("Your account has been disabled.");
        return;
      }
      _currentUser = user;
      _currentRole = data.role || "viewer";
      if (data.requiresPasswordChange) {
        showSetPasswordPage(data);
      } else {
        onLoggedIn(data);
      }
    } catch (err) {
      onLoggedOut("Error loading account: " + err.message);
    }
  });
}

async function doLogin() {
  const username = (document.getElementById("loginUsername")?.value || "").trim();
  const password = document.getElementById("loginPassword")?.value || "";
  const errEl    = document.getElementById("loginError");
  const btn      = document.getElementById("loginBtn");
  if (!username || !password) return;
  if (btn) { btn.disabled = true; btn.textContent = "Signing in…"; }
  if (errEl) errEl.classList.add("hidden");
  try {
    const authEmail = usernameToAuthEmail(username);
    await _fireAuth.signInWithEmailAndPassword(authEmail, password);
    // onAuthStateChanged handles the rest
  } catch (err) {
    const badCreds = ["auth/wrong-password", "auth/user-not-found", "auth/invalid-credential", "auth/invalid-email"];
    const friendly = badCreds.includes(err.code)
      ? "Incorrect username or password."
      : err.message.replace("Firebase: ", "");
    if (errEl) { errEl.textContent = friendly; errEl.classList.remove("hidden"); }
    if (btn) { btn.disabled = false; btn.textContent = "Sign In"; }
  }
}

async function doLogout() {
  try { await _fireAuth.signOut(); } catch {}
}

document.getElementById("loginBtn")?.addEventListener("click", doLogin);
document.getElementById("loginUsername")?.addEventListener("keydown", (e) => { if (e.key === "Enter") document.getElementById("loginPassword")?.focus(); });
document.getElementById("loginPassword")?.addEventListener("keydown", (e) => { if (e.key === "Enter") doLogin(); });
document.getElementById("logoutBtn")?.addEventListener("click", doLogout);

// ── Forced password change ────────────────────────────────────

function showSetPasswordPage(firestoreData) {
  const overlay = document.getElementById("setPasswordPage");
  if (!overlay) return;
  const nameEl = document.getElementById("setPasswordName");
  if (nameEl) nameEl.textContent = firestoreData.displayName || _currentUser?.email || "there";
  overlay.classList.remove("hidden");
  document.getElementById("loginPage")?.classList.add("hidden");
  document.getElementById("newPassword")?.focus();
}

async function doSetPassword() {
  const newPwd     = document.getElementById("newPassword")?.value || "";
  const confirmPwd = document.getElementById("confirmPassword")?.value || "";
  const errEl      = document.getElementById("setPasswordError");
  const btn        = document.getElementById("setPasswordBtn");

  const showErr = (msg) => { if (errEl) { errEl.textContent = msg; errEl.classList.remove("hidden"); } };

  if (newPwd.length < 6)      { showErr("Password must be at least 6 characters."); return; }
  if (newPwd !== confirmPwd)  { showErr("Passwords do not match."); return; }
  errEl?.classList.add("hidden");
  if (btn) { btn.disabled = true; btn.textContent = "Updating…"; }

  try {
    await _fireAuth.currentUser.updatePassword(newPwd);
    await _fireDb.collection("users").doc(_currentUser.uid).update({ requiresPasswordChange: false });
    document.getElementById("setPasswordPage")?.classList.add("hidden");
    const doc = await _fireDb.collection("users").doc(_currentUser.uid).get();
    onLoggedIn(doc.data());
  } catch (err) {
    showErr(err.message.replace("Firebase: ", "").replace(/\s*\(.*?\)\.?/g, ""));
    if (btn) { btn.disabled = false; btn.textContent = "Set Password"; }
  }
}

document.getElementById("setPasswordBtn")?.addEventListener("click", doSetPassword);
document.getElementById("confirmPassword")?.addEventListener("keydown", (e) => { if (e.key === "Enter") doSetPassword(); });

// ── Notes ─────────────────────────────────────────────────────

const NOTE_TAGS = {
  "General":       "#4da8ff",
  "Player Update": "#4ade80",
  "Bug":           "#ff5252",
  "Question":      "#ffc337",
  "FYI":           "#00e5b5",
};
const NOTE_REACTIONS = ["👍","✅","🔥","⚡","❓"];

const _N = {
  allItems: [], allUsers: [],
  search: "", filterType: "all", filterTag: "all", filterAuthor: "all", sort: "newest",
  composeType: "note", composeTags: [], composeCheckItems: [],
  editingId: null, showArchive: false,
  openReplies: {},
  unsubNotes: null, unsubMeta: null,
  draftTimer: null, lastSeenMs: 0, unreadMentions: 0,
  mentionState: { active: false, start: 0 },
};

// ── Markdown renderer ──────────────────────────────────────────

function renderMd(raw) {
  const text = String(raw || "");
  const parts = [];
  const cbRe = /```([\s\S]*?)```/g;
  let last = 0, m;
  while ((m = cbRe.exec(text)) !== null) {
    if (m.index > last) parts.push({ t: "text", s: text.slice(last, m.index) });
    parts.push({ t: "code", s: m[1].trim() });
    last = m.index + m[0].length;
  }
  if (last < text.length) parts.push({ t: "text", s: text.slice(last) });
  return parts.map(p => p.t === "code"
    ? `<pre class="note-codeblock"><code>${p.s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")}</code></pre>`
    : renderMdInline(p.s)
  ).join("");
}

function renderMdInline(text) {
  let h = text.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
  h = h.replace(/`([^`\n]+)`/g, '<code class="note-code">$1</code>');
  h = h.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  h = h.replace(/\*([^*\n]+)\*/g, "<em>$1</em>");
  h = h.replace(/@([\w][\w .']{0,28})/g, '<span class="note-mention">@$1</span>');
  const lines = h.split("\n");
  const out = []; let inUl = false, inOl = false;
  const close = () => { if (inUl){out.push("</ul>");inUl=false;} if (inOl){out.push("</ol>");inOl=false;} };
  for (const ln of lines) {
    if (/^- /.test(ln)) { if(!inUl){close();out.push('<ul class="note-list">');inUl=true;} out.push(`<li>${ln.slice(2)}</li>`); }
    else if (/^\d+\. /.test(ln)) { if(!inOl){close();out.push('<ol class="note-list">');inOl=true;} out.push(`<li>${ln.replace(/^\d+\. /,"")}</li>`); }
    else { close(); out.push(ln ? `${ln}<br>` : "<br>"); }
  }
  close();
  return out.join("");
}

// ── Format toolbar ─────────────────────────────────────────────

function applyFmt(ta, fmt) {
  const s = ta.selectionStart, e = ta.selectionEnd, sel = ta.value.slice(s, e);
  const F = { bold:{pre:"**",post:"**",ph:"bold text"}, italic:{pre:"*",post:"*",ph:"italic"},
    code:{pre:"`",post:"`",ph:"code"}, bullet:{pre:"\n- ",post:"",ph:"list item"},
    number:{pre:"\n1. ",post:"",ph:"item"}, codeblock:{pre:"\n```\n",post:"\n```\n",ph:"code"} };
  const f = F[fmt]; if (!f) return;
  ta.setRangeText(f.pre + (sel || f.ph) + f.post, s, e, "end");
  ta.dispatchEvent(new Event("input")); ta.focus();
}

// ── @Mention system ────────────────────────────────────────────

function handleMentionInput(ta) {
  const before = ta.value.slice(0, ta.selectionStart);
  const atIdx  = before.lastIndexOf("@");
  if (atIdx === -1 || (atIdx > 0 && /\S/.test(before[atIdx - 1]))) { hideMention(); return; }
  const query = before.slice(atIdx + 1).toLowerCase();
  if (query.split(" ").length > 3) { hideMention(); return; }
  const matches = _N.allUsers.filter(u => u.displayName && u.displayName.toLowerCase().includes(query) && u.displayName !== getDisplayName()).slice(0, 6);
  if (!matches.length) { hideMention(); return; }
  _N.mentionState = { active: true, start: atIdx };
  const dd = document.getElementById("notesMentionDropdown");
  if (!dd) return;
  dd.innerHTML = matches.map(u => `<button class="mention-item" data-name="${safeHtml(u.displayName)}"><span class="mention-avatar">${u.displayName.slice(0,2).toUpperCase()}</span>${safeHtml(u.displayName)}</button>`).join("");
  dd.classList.remove("hidden");
  dd.querySelectorAll(".mention-item").forEach(btn => btn.addEventListener("mousedown", e => { e.preventDefault(); insertMention(ta, btn.dataset.name); }));
}

function hideMention() { document.getElementById("notesMentionDropdown")?.classList.add("hidden"); _N.mentionState.active = false; }

function insertMention(ta, name) {
  const { start } = _N.mentionState;
  const after = ta.value.slice(ta.selectionStart);
  ta.value = ta.value.slice(0, start) + "@" + name + " " + after;
  const pos = start + name.length + 2; ta.setSelectionRange(pos, pos);
  hideMention(); ta.focus();
}

// ── Draft ──────────────────────────────────────────────────────

function saveDraft() {
  const ta = document.getElementById("notesInput");
  if (!ta) return;
  localStorage.setItem("nba2k26_note_draft", JSON.stringify({ content: ta.value, type: _N.composeType, tags: _N.composeTags }));
}

function loadDraft() {
  try {
    const d = JSON.parse(localStorage.getItem("nba2k26_note_draft") || "null");
    if (!d) return;
    const ta = document.getElementById("notesInput");
    if (ta && d.content) ta.value = d.content;
    if (d.type) setComposeType(d.type);
    if (d.tags) { _N.composeTags = d.tags; renderComposeTags(); }
  } catch {}
}

function clearCompose() {
  _N.editingId = null; _N.composeType = "note"; _N.composeTags = []; _N.composeCheckItems = [];
  const ta = document.getElementById("notesInput"); if (ta) ta.value = "";
  const btn = document.getElementById("notesPostBtn"); if (btn) btn.textContent = "Post Note";
  setComposeType("note"); renderComposeTags(); renderChecklistBuilder();
  localStorage.removeItem("nba2k26_note_draft");
}

// ── Compose helpers ────────────────────────────────────────────

function setComposeType(type) {
  _N.composeType = type;
  document.querySelectorAll(".notes-type-btn").forEach(b => b.classList.toggle("active", b.dataset.type === type));
  document.getElementById("notesChecklistBuilder")?.classList.toggle("hidden", type !== "task");
}

function renderComposeTags() {
  const el = document.getElementById("notesComposeTags"); if (!el) return;
  el.innerHTML = Object.entries(NOTE_TAGS).map(([tag, color]) => {
    const on = _N.composeTags.includes(tag);
    return `<button class="note-tag-pill compose-tag${on?" active":""}" data-tag="${tag}"
      style="${on?`background:${color}22;border-color:${color};color:${color}`:""}">${tag}</button>`;
  }).join("");
  el.querySelectorAll(".compose-tag").forEach(b => b.addEventListener("click", () => {
    const i = _N.composeTags.indexOf(b.dataset.tag);
    i > -1 ? _N.composeTags.splice(i,1) : _N.composeTags.push(b.dataset.tag);
    renderComposeTags();
  }));
}

function renderChecklistBuilder() {
  const el = document.getElementById("notesChecklistItems"); if (!el) return;
  el.innerHTML = _N.composeCheckItems.map((item, i) =>
    `<div class="checklist-build-row">
      <input type="checkbox" disabled class="checklist-cb-preview"/>
      <input type="text" class="checklist-build-input" value="${safeHtml(item.text)}" placeholder="Item ${i+1}…" data-idx="${i}"/>
      <button class="checklist-build-remove" data-idx="${i}">×</button>
    </div>`).join("");
  el.querySelectorAll(".checklist-build-input").forEach(inp => inp.addEventListener("input", () => { _N.composeCheckItems[Number(inp.dataset.idx)].text = inp.value; }));
  el.querySelectorAll(".checklist-build-remove").forEach(btn => btn.addEventListener("click", () => { _N.composeCheckItems.splice(Number(btn.dataset.idx),1); renderChecklistBuilder(); }));
}

// ── Post / Edit / Archive ──────────────────────────────────────

async function postNote() {
  if (!_fireDb) return;
  if (_N.editingId) { await saveEdit(); return; }
  const ta = document.getElementById("notesInput");
  const content = (ta?.value || "").trim();
  if (!content && _N.composeType !== "task") return;
  if (_N.composeType === "task" && !content && !_N.composeCheckItems.length) return;
  const author = getDisplayName();
  const btn = document.getElementById("notesPostBtn");
  if (btn) { btn.disabled = true; btn.textContent = "Posting…"; }
  const mentions = [...new Set([...content.matchAll(/@([\w][\w .']{0,28})/g)].map(m => m[1].trim()))];
  try {
    await _fireDb.collection("notes").add({
      content, author, authorUid: _currentUser?.uid || "",
      type: _N.composeType, tags: [..._N.composeTags],
      pinned: _N.composeType === "announcement", archived: false,
      edited: false, editedAt: null,
      createdAt: firebase.firestore.FieldValue.serverTimestamp(),
      reactions: Object.fromEntries(NOTE_REACTIONS.map(e => [e, []])),
      replyCount: 0,
      checklistItems: _N.composeType === "task" ? _N.composeCheckItems.map(i => ({...i, done: false})) : [],
      mentions,
    });
    if (mentions.length) {
      const snap = await _fireDb.collection("users").get();
      for (const d of snap.docs) {
        if (d.id !== _currentUser?.uid && mentions.includes(d.data().displayName)) {
          _fireDb.collection("userMeta").doc(d.id).set({ unreadMentions: firebase.firestore.FieldValue.increment(1) }, { merge: true });
        }
      }
    }
    clearCompose();
  } catch (err) {
    showToast(`Failed to post: ${err.message}`, "error", 4000);
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = "Post Note"; }
  }
}

async function saveEdit() {
  if (!_N.editingId || !_fireDb) return;
  const content = (document.getElementById("notesInput")?.value || "").trim();
  if (!content) return;
  try {
    await _fireDb.collection("notes").doc(_N.editingId).update({ content, edited: true, editedAt: firebase.firestore.FieldValue.serverTimestamp() });
    clearCompose();
  } catch (err) {
    showToast(`Edit failed: ${err.message}`, "error", 4000);
  }
}

async function archiveNote(id, archive) {
  if (!_fireDb) return;
  try { await _fireDb.collection("notes").doc(id).update({ archived: archive }); } catch (err) { showToast(`Failed: ${err.message}`, "error"); }
}

// ── Reactions ──────────────────────────────────────────────────

async function toggleReaction(noteId, emoji) {
  if (!_fireDb || !_currentUser) return;
  const uid = _currentUser.uid;
  const ref = _fireDb.collection("notes").doc(noteId);
  const doc = await ref.get();
  const cur = (doc.data()?.reactions?.[emoji]) || [];
  await ref.update({ [`reactions.${emoji}`]: cur.includes(uid) ? firebase.firestore.FieldValue.arrayRemove(uid) : firebase.firestore.FieldValue.arrayUnion(uid) });
}

// ── Checklist toggle ───────────────────────────────────────────

async function toggleCheckItem(noteId, itemId, done) {
  const doc = await _fireDb.collection("notes").doc(noteId).get();
  const items = (doc.data()?.checklistItems || []).map(i => i.id === itemId ? {...i, done} : i);
  await _fireDb.collection("notes").doc(noteId).update({ checklistItems: items });
}

// ── Replies ────────────────────────────────────────────────────

function loadReplies(noteId) {
  const container = document.getElementById(`replies-${noteId}`); if (!container) return;
  if (_N.openReplies[noteId]?.unsub) _N.openReplies[noteId].unsub();
  container.innerHTML = '<div class="notes-loading">Loading…</div>';
  const me = getDisplayName();
  const unsub = _fireDb.collection("notes").doc(noteId).collection("replies")
    .orderBy("createdAt", "asc")
    .onSnapshot(snap => {
      const replyHtml = snap.docs.map(doc => {
        const d = doc.data(), isOwn = d.author === me;
        const time = (d.createdAt?.toDate ? d.createdAt.toDate() : new Date()).toLocaleDateString("en-US",{month:"short",day:"numeric",hour:"2-digit",minute:"2-digit"});
        return `<div class="reply-card${isOwn?" reply-own":""}">
          <div class="reply-header">
            <div class="note-avatar reply-avatar">${(d.author||"?").slice(0,2).toUpperCase()}</div>
            <span class="note-author">${safeHtml(d.author||"?")}</span>
            <span class="note-time">${time}${d.edited?" (edited)":""}</span>
            ${isOwn?`<button class="reply-del-btn" data-note="${noteId}" data-id="${doc.id}">×</button>`:""}
          </div>
          <div class="note-body">${renderMd(d.content)}</div>
        </div>`;
      }).join("") || '<div class="notes-empty" style="padding:10px 0;font-size:12px">No replies yet.</div>';

      container.innerHTML = `${replyHtml}
        <div class="reply-compose">
          <textarea class="reply-input" placeholder="Reply… (Ctrl+Enter to post)" rows="2"></textarea>
          <div class="reply-compose-footer">
            <button class="reply-post-btn btn-primary btn-sm" data-note="${noteId}">Reply</button>
          </div>
        </div>`;

      container.querySelectorAll(".reply-del-btn").forEach(btn => btn.addEventListener("click", () => deleteReply(btn.dataset.note, btn.dataset.id)));

      const rInput = container.querySelector(".reply-input");
      const rBtn   = container.querySelector(".reply-post-btn");
      const doReply = async () => {
        const txt = (rInput?.value||"").trim(); if (!txt) return;
        rBtn.disabled = true;
        try {
          await _fireDb.collection("notes").doc(noteId).collection("replies").add({
            content: txt, author: me, authorUid: _currentUser?.uid||"",
            createdAt: firebase.firestore.FieldValue.serverTimestamp(), edited: false,
          });
          await _fireDb.collection("notes").doc(noteId).update({ replyCount: firebase.firestore.FieldValue.increment(1) });
          if (rInput) rInput.value = "";
        } catch (err) { showToast(`Failed: ${err.message}`, "error", 3000); }
        finally { rBtn.disabled = false; }
      };
      rBtn?.addEventListener("click", doReply);
      rInput?.addEventListener("keydown", e => { if (e.key==="Enter"&&(e.ctrlKey||e.metaKey)) doReply(); });
    });
  _N.openReplies[noteId] = { unsub };
}

async function deleteReply(noteId, replyId) {
  try {
    await _fireDb.collection("notes").doc(noteId).collection("replies").doc(replyId).delete();
    await _fireDb.collection("notes").doc(noteId).update({ replyCount: firebase.firestore.FieldValue.increment(-1) });
  } catch (err) { showToast(`Failed: ${err.message}`, "error", 3000); }
}

// ── Feed rendering ─────────────────────────────────────────────

function getFilteredNotes() {
  let items = _N.allItems.filter(n => !!n.archived === _N.showArchive);
  if (_N.search) { const q = _N.search.toLowerCase(); items = items.filter(n => n.content.toLowerCase().includes(q) || n.author.toLowerCase().includes(q)); }
  if (_N.filterType !== "all") items = items.filter(n => n.type === _N.filterType);
  if (_N.filterTag  !== "all") items = items.filter(n => (n.tags||[]).includes(_N.filterTag));
  if (_N.filterAuthor !== "all") items = items.filter(n => n.author === _N.filterAuthor);
  if (_N.sort === "oldest") items.sort((a,b) => (a.createdAt?.toMillis?.()||0)-(b.createdAt?.toMillis?.()||0));
  else if (_N.sort === "reactions") items.sort((a,b) => { const ra=Object.values(a.reactions||{}).reduce((s,a)=>s+a.length,0); const rb=Object.values(b.reactions||{}).reduce((s,a)=>s+a.length,0); return rb-ra; });
  else items.sort((a,b) => { if(a.pinned&&!b.pinned)return -1; if(!a.pinned&&b.pinned)return 1; return (b.createdAt?.toMillis?.()||0)-(a.createdAt?.toMillis?.()||0); });
  return items;
}

function renderNoteCard(n) {
  const id = n.id, uid = _currentUser?.uid||"", me = getDisplayName();
  const isOwn = n.authorUid === uid || n.author === me;
  const isAdmin = _currentRole === "head_admin" || _currentRole === "admin";
  const ts = n.createdAt?.toDate ? n.createdAt.toDate() : new Date();
  const time = ts.toLocaleDateString("en-US",{month:"short",day:"numeric",year:"numeric",hour:"2-digit",minute:"2-digit"});
  const isNew = (n.createdAt?.toMillis?.()||0) > _N.lastSeenMs && n.author !== me;

  const typeStyle = { announcement:{cls:"note-announcement",badge:"📢 Announcement",border:"var(--orange)"}, task:{cls:"note-task",badge:"✅ Task",border:"var(--teal)"}, note:{cls:"",badge:"",border:""} };
  const tm = typeStyle[n.type] || typeStyle.note;

  const tagHtml = (n.tags||[]).map(t => { const c=NOTE_TAGS[t]||"#888"; return `<span class="note-tag-pill" style="background:${c}22;border-color:${c};color:${c}">${t}</span>`; }).join("");

  const reactionHtml = NOTE_REACTIONS.map(e => {
    const uids = n.reactions?.[e]||[], cnt = uids.length, mine = uids.includes(uid);
    const who = uids.map(u => (_N.allUsers.find(x=>x.uid===u)||{}).displayName||"Someone").join(", ");
    return `<button class="reaction-btn${mine?" mine":""}" data-note="${id}" data-emoji="${e}" title="${safeHtml(who||e)}">${e}${cnt?`<span class="reaction-count">${cnt}</span>`:"" }</button>`;
  }).join("");

  let checklistHtml = "";
  if (n.type==="task" && n.checklistItems?.length) {
    const done=n.checklistItems.filter(i=>i.done).length, total=n.checklistItems.length;
    checklistHtml = `<div class="note-checklist">
      <div class="checklist-progress-wrap"><div class="checklist-progress-bar" style="width:${Math.round(done/total*100)}%"></div></div>
      <div class="checklist-label">${done}/${total} completed</div>
      ${n.checklistItems.map(item=>`<label class="checklist-item${item.done?" done":""}"><input type="checkbox" class="checklist-cb" ${item.done?"checked":""} data-note="${id}" data-item="${item.id}"><span>${safeHtml(item.text)}</span></label>`).join("")}
    </div>`;
  }

  const isLong = (n.content||"").length > 320;
  const bodyHtml = isLong
    ? `<div class="note-body note-body-clamped" id="nb-${id}">${renderMd(n.content)}</div><button class="note-expand-btn" data-id="${id}">Show more ▾</button>`
    : `<div class="note-body">${renderMd(n.content)}</div>`;

  const canEdit    = isOwn;
  const canArchive = isOwn || _currentRole === "head_admin";

  return `<div class="note-card ${tm.cls}${n.pinned?" note-pinned":""}${isNew?" note-new":""}" id="nc-${id}" style="${tm.border?`border-left:3px solid ${tm.border}`:""}">
    <div class="note-header">
      <div class="note-avatar${isOwn?" own-av":""}">${(n.author||"?").slice(0,2).toUpperCase()}</div>
      <div class="note-meta">
        <div class="note-author">${safeHtml(n.author||"Anonymous")}${n.pinned?'<span class="note-pin">📌</span>':""}</div>
        <div class="note-time">${time}${n.edited?'<span class="note-edited"> · edited</span>':""}</div>
      </div>
      <div class="note-badges">
        ${tm.badge?`<span class="note-type-badge">${tm.badge}</span>`:""}
        ${isNew?'<span class="note-new-badge">New</span>':""}
        ${tagHtml}
      </div>
    </div>
    ${bodyHtml}
    ${checklistHtml}
    <div class="note-footer">
      <div class="note-reactions">${reactionHtml}</div>
      <div class="note-actions">
        <button class="note-reply-btn" data-id="${id}">💬${n.replyCount>0?` ${n.replyCount}`:""} Reply</button>
        ${canEdit?`<button class="note-act-btn" data-action="edit" data-id="${id}" data-content="${safeHtml(n.content)}">Edit</button>`:""}
        ${canArchive&&!n.archived?`<button class="note-act-btn" data-action="archive" data-id="${id}">Archive</button>`:""}
        ${canArchive&&n.archived?`<button class="note-act-btn" data-action="unarchive" data-id="${id}">Restore</button>`:""}
      </div>
    </div>
    <div class="note-replies hidden" id="replies-${id}"></div>
  </div>`;
}

function renderFeed() {
  const feedEl = document.getElementById("notesFeed"); if (!feedEl) return;
  const items = getFilteredNotes();
  if (!items.length) { feedEl.innerHTML = `<div class="notes-empty">${_N.showArchive?"No archived notes.":"No notes match your filters."}</div>`; return; }
  feedEl.innerHTML = items.map(renderNoteCard).join("");

  feedEl.querySelectorAll(".reaction-btn").forEach(btn => btn.addEventListener("click", () => toggleReaction(btn.dataset.note, btn.dataset.emoji)));
  feedEl.querySelectorAll(".note-reply-btn").forEach(btn => btn.addEventListener("click", () => {
    const id = btn.dataset.id, cont = document.getElementById(`replies-${id}`); if (!cont) return;
    const open = !cont.classList.contains("hidden");
    cont.classList.toggle("hidden", open);
    if (!open) loadReplies(id);
    else if (_N.openReplies[id]?.unsub) { _N.openReplies[id].unsub(); delete _N.openReplies[id]; }
  }));
  feedEl.querySelectorAll(".note-act-btn").forEach(btn => {
    const { action, id } = btn.dataset;
    if (action === "edit") btn.addEventListener("click", () => {
      _N.editingId = id;
      const ta = document.getElementById("notesInput"); if (ta) { ta.value = btn.dataset.content||""; ta.focus(); }
      const pb = document.getElementById("notesPostBtn"); if (pb) pb.textContent = "Save Edit";
      document.getElementById("notesComposeCard")?.scrollIntoView({ behavior:"smooth" });
    });
    else if (action === "archive")   btn.addEventListener("click", () => archiveNote(id, true));
    else if (action === "unarchive") btn.addEventListener("click", () => archiveNote(id, false));
  });
  feedEl.querySelectorAll(".note-expand-btn").forEach(btn => btn.addEventListener("click", () => {
    const body = document.getElementById(`nb-${btn.dataset.id}`);
    body?.classList.toggle("note-body-clamped");
    btn.textContent = body?.classList.contains("note-body-clamped") ? "Show more ▾" : "Show less ▴";
  }));
  feedEl.querySelectorAll(".checklist-cb").forEach(cb => cb.addEventListener("change", () => toggleCheckItem(cb.dataset.note, cb.dataset.item, cb.checked)));
}

function updateFilterOptions() {
  const tagSel = document.getElementById("notesFilterTag");
  if (tagSel) { const cur=tagSel.value; tagSel.innerHTML = `<option value="all">All tags</option>${[...new Set(_N.allItems.flatMap(n=>n.tags||[]))].map(t=>`<option value="${t}"${t===cur?" selected":""}>${t}</option>`).join("")}`; }
  const authSel = document.getElementById("notesFilterAuthor");
  if (authSel) { const cur=authSel.value; authSel.innerHTML = `<option value="all">All authors</option>${[...new Set(_N.allItems.map(n=>n.author).filter(Boolean))].map(a=>`<option value="${a}"${a===cur?" selected":""}>${a}</option>`).join("")}`; }
}

// ── Unread badge ───────────────────────────────────────────────

function subscribeToUnread() {
  if (!_fireDb || !_currentUser) return;
  if (_N.unsubMeta) { _N.unsubMeta(); _N.unsubMeta = null; }
  _N.unsubMeta = _fireDb.collection("userMeta").doc(_currentUser.uid).onSnapshot(doc => {
    const data = doc.data() || {};
    _N.lastSeenMs      = data.lastSeenNotes?.toMillis?.() || 0;
    _N.unreadMentions  = data.unreadMentions || 0;
    updateUnreadBadge();
  });
}

function updateUnreadBadge() {
  const btn = document.getElementById("openNotesBtn"); if (!btn) return;
  const me = getDisplayName();
  const unreadNotes = _N.allItems.filter(n => !n.archived && (n.createdAt?.toMillis?.()||0) > _N.lastSeenMs && n.author !== me).length;
  const total = unreadNotes + _N.unreadMentions;
  let badge = btn.querySelector(".notes-unread-badge");
  if (total > 0) {
    if (!badge) { badge = document.createElement("span"); badge.className = "notes-unread-badge"; btn.appendChild(badge); }
    badge.textContent = total > 99 ? "99+" : String(total);
  } else badge?.remove();
}

async function markNotesSeen() {
  if (!_fireDb || !_currentUser) return;
  try { await _fireDb.collection("userMeta").doc(_currentUser.uid).set({ lastSeenNotes: firebase.firestore.FieldValue.serverTimestamp(), unreadMentions: 0 }, { merge: true }); } catch {}
}

// ── Subscribe ──────────────────────────────────────────────────

function subscribeToNotes() {
  if (!_fireDb) return;
  const feedEl = document.getElementById("notesFeed"); if (!feedEl) return;
  if (_N.unsubNotes) { _N.unsubNotes(); _N.unsubNotes = null; }
  feedEl.innerHTML = '<div class="notes-loading">Loading notes…</div>';
  _N.unsubNotes = _fireDb.collection("notes").orderBy("createdAt","desc").onSnapshot(snap => {
    _N.allItems = snap.docs.map(d => ({ id:d.id, ...d.data() }));
    updateFilterOptions(); renderFeed(); updateUnreadBadge();
  }, err => { feedEl.innerHTML = `<div class="notes-empty">Error: ${err.message}</div>`; });
}

async function loadNotesUsers() {
  if (!_fireDb) return;
  try { const snap = await _fireDb.collection("users").get(); _N.allUsers = snap.docs.map(d=>({uid:d.id,...d.data()})); } catch {}
}

// ── Page ───────────────────────────────────────────────────────

function showNotesPage() {
  if (_currentRole === "viewer") return;
  _hideAllPages();
  document.getElementById("notesPage")?.classList.remove("hidden");
  document.body.classList.remove("profile-open");
  setActiveNav("openNotesBtn");
  const label = document.getElementById("notesAuthorLabel"); if (label) label.textContent = getDisplayName()||"Anonymous";
  document.getElementById("notesTypeAnnouncement")?.classList.toggle("hidden", _currentRole === "admin" ? false : _currentRole === "viewer");
  setComposeType("note"); renderComposeTags(); loadDraft(); loadNotesUsers();
  subscribeToNotes(); subscribeToUnread(); markNotesSeen();
}

// ── Compose init ───────────────────────────────────────────────

(function initNotesListeners() {
  document.querySelectorAll(".notes-type-btn").forEach(btn => btn.addEventListener("click", () => setComposeType(btn.dataset.type)));
  document.querySelectorAll(".notes-fmt-btn").forEach(btn => btn.addEventListener("click", () => { const ta=document.getElementById("notesInput"); if(ta) applyFmt(ta,btn.dataset.fmt); }));

  const ta = document.getElementById("notesInput");
  if (ta) {
    ta.addEventListener("input", () => { handleMentionInput(ta); clearTimeout(_N.draftTimer); _N.draftTimer = setTimeout(saveDraft, 2000); });
    ta.addEventListener("keydown", e => {
      if (e.key==="Escape") { hideMention(); if(_N.editingId){clearCompose();} }
      if (e.key==="Enter"&&(e.ctrlKey||e.metaKey)) { e.preventDefault(); postNote(); }
    });
    ta.addEventListener("blur", () => setTimeout(hideMention, 150));
  }

  document.getElementById("notesPostBtn")?.addEventListener("click", postNote);
  document.getElementById("notesClearBtn")?.addEventListener("click", clearCompose);
  document.getElementById("notesAddCheckItem")?.addEventListener("click", () => { _N.composeCheckItems.push({id:Date.now().toString(),text:"",done:false}); renderChecklistBuilder(); });

  ["notesSearch","notesFilterType","notesFilterTag","notesFilterAuthor"].forEach(id => document.getElementById(id)?.addEventListener("input", e => { if(id==="notesSearch")_N.search=e.target.value; else if(id==="notesFilterType")_N.filterType=e.target.value; else if(id==="notesFilterTag")_N.filterTag=e.target.value; else _N.filterAuthor=e.target.value; renderFeed(); }));
  document.getElementById("notesFilterType")?.addEventListener("change",   e => { _N.filterType=e.target.value;   renderFeed(); });
  document.getElementById("notesFilterTag")?.addEventListener("change",    e => { _N.filterTag=e.target.value;    renderFeed(); });
  document.getElementById("notesFilterAuthor")?.addEventListener("change", e => { _N.filterAuthor=e.target.value; renderFeed(); });
  document.getElementById("notesSort")?.addEventListener("change",         e => { _N.sort=e.target.value;         renderFeed(); });
  document.getElementById("notesShowArchive")?.addEventListener("click", () => {
    _N.showArchive = !_N.showArchive;
    document.getElementById("notesShowArchive").textContent = _N.showArchive ? "Hide Archive" : "Show Archive";
    renderFeed();
  });

  document.addEventListener("keydown", e => {
    if (e.ctrlKey && e.key==="n" && !document.getElementById("notesPage")?.classList.contains("hidden")) {
      e.preventDefault(); document.getElementById("notesInput")?.focus();
    }
  });
})();

document.getElementById("openNotesBtn")?.addEventListener("click", showNotesPage);

// ── Users management (Head Admin only) ────────────────────────

async function loadUsersList() {
  const el = document.getElementById("usersList");
  if (!el) return;
  el.innerHTML = '<div class="users-loading">Loading users…</div>';
  try {
    const snap = await _fireDb.collection("users").orderBy("createdAt", "asc").get();
    if (snap.empty) { el.innerHTML = '<div class="users-loading">No users found.</div>'; return; }
    el.innerHTML = `<div class="stats-table-scroll"><table class="stats-table">
      <thead><tr>
        <th class="th-name">Username</th>
        <th class="th-stat">Role</th>
        <th class="th-stat">Actions</th>
      </tr></thead>
      <tbody>${snap.docs.map((doc) => {
        const d = doc.data();
        const isSelf = doc.id === _currentUser?.uid;
        return `<tr class="stats-row${isSelf ? " users-self-row" : ""}">
          <td class="td-name">${safeHtml(d.displayName || "—")}</td>
          <td class="td-stat">
            <select class="select-sm users-role-select" data-uid="${doc.id}"${isSelf ? " disabled" : ""}>
              <option value="viewer"     ${d.role === "viewer"     ? "selected" : ""}>Viewer</option>
              <option value="admin"      ${d.role === "admin"      ? "selected" : ""}>Admin</option>
              <option value="head_admin" ${d.role === "head_admin" ? "selected" : ""}>Head Admin</option>
            </select>
          </td>
          <td class="td-stat">
            ${isSelf
              ? '<span class="users-self-tag">You</span>'
              : `<button class="users-remove-btn" data-uid="${doc.id}" data-name="${safeHtml(d.displayName)}">Remove</button>`}
          </td>
        </tr>`;
      }).join("")}</tbody>
    </table></div>`;

    el.querySelectorAll(".users-role-select").forEach((sel) => {
      sel.addEventListener("change", async () => {
        try {
          await _fireDb.collection("users").doc(sel.dataset.uid).update({ role: sel.value });
          showToast("Role updated.", "success", 2000);
        } catch (err) {
          showToast("Failed to update role: " + err.message, "error");
        }
      });
    });

    el.querySelectorAll(".users-remove-btn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        if (!confirm(`Remove ${btn.dataset.name}? They will lose access immediately.`)) return;
        try {
          await _fireDb.collection("users").doc(btn.dataset.uid).delete();
          showToast(`${btn.dataset.name} removed.`, "success", 2500);
          loadUsersList();
        } catch (err) {
          showToast("Failed to remove: " + err.message, "error");
        }
      });
    });
  } catch (err) {
    el.innerHTML = `<div class="users-loading">Error: ${err.message}</div>`;
  }
}

async function addUser() {
  const name     = (document.getElementById("newUserName")?.value     || "").trim();
  const password = (document.getElementById("newUserPassword")?.value || "");
  const role     = document.getElementById("newUserRole")?.value || "viewer";
  const statusEl = document.getElementById("addUserStatus");
  const btn      = document.getElementById("addUserBtn");

  const setStatus = (msg, isError) => {
    if (!statusEl) return;
    statusEl.textContent = msg;
    statusEl.className = `users-add-status${isError ? " error" : " success"}`;
    statusEl.classList.remove("hidden");
  };

  if (!name || !password) { setStatus("Username and password are required.", true); return; }
  if (password.length < 6) { setStatus("Password must be at least 6 characters.", true); return; }
  if (btn) btn.disabled = true;
  setStatus("Creating account…", false);

  try {
    // Check username is not already taken
    const existing = await _fireDb.collection("users").where("username", "==", name.toLowerCase()).limit(1).get();
    if (!existing.empty) throw new Error(`Username "${name}" is already taken.`);

    const authEmail = usernameToAuthEmail(name);

    // Create Auth account via REST API — does not sign out the current admin
    const res  = await fetch(
      `https://identitytoolkit.googleapis.com/v1/accounts:signUp?key=${FIREBASE_CONFIG.apiKey}`,
      { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: authEmail, password, displayName: name, returnSecureToken: false }) }
    );
    const data = await res.json();
    if (data.error) {
      if (data.error.message === "EMAIL_EXISTS") {
        throw new Error(
          `The username "${name}" was previously deleted but its auth account still exists. ` +
          `Go to Firebase Console → Authentication → Users and delete the account with email: ${authEmail} — then try again.`
        );
      }
      throw new Error(data.error.message);
    }

    await _fireDb.collection("users").doc(data.localId).set({
      displayName: name, username: name.toLowerCase(), role,
      requiresPasswordChange: true,
      createdAt: firebase.firestore.FieldValue.serverTimestamp(),
    });

    setStatus(`${name} added successfully.`, false);
    document.getElementById("newUserName").value = "";
    document.getElementById("newUserPassword").value = "";
    loadUsersList();
  } catch (err) {
    setStatus(err.message.replace("Firebase: ", ""), true);
  } finally {
    if (btn) btn.disabled = false;
  }
}

function showUsersPage() {
  if (_currentRole !== "head_admin") return;
  _hideAllPages();
  document.getElementById("usersPage")?.classList.remove("hidden");
  document.body.classList.remove("profile-open");
  setActiveNav("openUsersBtn");
  loadUsersList();
}

document.getElementById("openUsersBtn")?.addEventListener("click", showUsersPage);
document.getElementById("addUserBtn")?.addEventListener("click", addUser);

// ═══════════════════════════════════════════════════════════════
// CHAT
// ═══════════════════════════════════════════════════════════════

const _C = {
  allUsers: [],
  activeChatId: null,
  activePeerUid: null,
  activePeerName: null,
  messages: [],
  unsubChat: null,
  unsubUnread: null,
  panelOpen: false,
  totalUnread: 0,
};

function getChatId(uid1, uid2) {
  return [uid1, uid2].sort().join("_");
}

function toggleChatPanel() {
  _C.panelOpen = !_C.panelOpen;
  const panel = document.getElementById("chatPanel");
  if (!panel) return;
  if (_C.panelOpen) {
    panel.classList.remove("hidden");
    renderChatHub();
  } else {
    panel.classList.add("hidden");
    cleanupActiveChat();
  }
}

function closeChatPanel() {
  _C.panelOpen = false;
  const panel = document.getElementById("chatPanel");
  if (panel) { panel.classList.add("hidden"); panel.innerHTML = ""; }
  cleanupActiveChat();
}

function cleanupActiveChat() {
  if (_C.unsubChat) { _C.unsubChat(); _C.unsubChat = null; }
  _C.activeChatId = null;
  _C.activePeerUid = null;
  _C.activePeerName = null;
  _C.messages = [];
}

async function loadChatUsers() {
  if (!_fireDb) return;
  try {
    const snap = await _fireDb.collection("users").get();
    _C.allUsers = snap.docs
      .map(d => ({ uid: d.id, ...d.data() }))
      .filter(u => u.uid !== _currentUser?.uid);
  } catch {}
}

async function getUnreadMap() {
  if (!_fireDb || !_currentUser) return {};
  try {
    const snap = await _fireDb.collection("chats")
      .where("participants", "array-contains", _currentUser.uid)
      .get();
    const map = {};
    for (const doc of snap.docs) {
      const d = doc.data();
      const peerUid = (d.participants || []).find(p => p !== _currentUser.uid);
      if (peerUid) map[peerUid] = d.unread?.[_currentUser.uid] || 0;
    }
    return map;
  } catch { return {}; }
}

async function renderChatHub() {
  const panel = document.getElementById("chatPanel");
  if (!panel) return;

  panel.innerHTML = `<div class="chat-panel-header">
    <span class="chat-panel-title">Messages</span>
    <button class="chat-close-btn" id="chatCloseBtn">×</button>
  </div>
  <div class="chat-hub-body"><div class="chat-loading">Loading…</div></div>`;

  document.getElementById("chatCloseBtn")?.addEventListener("click", closeChatPanel);

  await loadChatUsers();
  const unreadMap = await getUnreadMap();

  const hubBody = panel.querySelector(".chat-hub-body");
  if (!hubBody) return;

  if (!_C.allUsers.length) {
    hubBody.innerHTML = '<div class="chat-empty">No other users yet.</div>';
    return;
  }

  hubBody.innerHTML = _C.allUsers.map(u => {
    const unread = unreadMap[u.uid] || 0;
    const initials = (u.displayName || u.email || "?").slice(0, 2).toUpperCase();
    return `<button class="chat-user-row" data-uid="${u.uid}" data-name="${safeHtml(u.displayName || u.email || "User")}">
      <div class="chat-user-avatar">${initials}</div>
      <div class="chat-user-info">
        <span class="chat-user-name">${safeHtml(u.displayName || u.email || "Unknown")}</span>
        <span class="chat-user-role">${ROLE_LABELS[u.role] || u.role || ""}</span>
      </div>
      ${unread > 0 ? `<span class="chat-unread-dot">${unread}</span>` : ""}
    </button>`;
  }).join("");

  hubBody.querySelectorAll(".chat-user-row").forEach(btn => {
    btn.addEventListener("click", () => openChatWith(btn.dataset.uid, btn.dataset.name));
  });
}

async function openChatWith(peerUid, peerName) {
  if (!_fireDb || !_currentUser) return;
  _C.activeChatId = getChatId(_currentUser.uid, peerUid);
  _C.activePeerUid = peerUid;
  _C.activePeerName = peerName;
  clearChatUnread(_C.activeChatId);
  renderChatWindow();
  subscribeToChat(_C.activeChatId);
}

function renderChatWindow() {
  const panel = document.getElementById("chatPanel");
  if (!panel) return;
  const initials = (_C.activePeerName || "?").slice(0, 2).toUpperCase();

  panel.innerHTML = `<div class="chat-panel-header">
    <button class="chat-back-btn" id="chatBackBtn">
      <svg viewBox="0 0 16 16" fill="none" width="14" height="14">
        <path d="M10 3L5 8l5 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </button>
    <div class="chat-peer-avatar">${initials}</div>
    <span class="chat-panel-title">${safeHtml(_C.activePeerName || "Chat")}</span>
    <button class="chat-close-btn" id="chatCloseBtn">×</button>
  </div>
  <div class="chat-messages-list" id="chatMessagesList">
    <div class="chat-loading">Loading messages…</div>
  </div>
  <div class="chat-input-row">
    <textarea class="chat-input" id="chatInput" placeholder="Message… (Enter to send)" rows="1"></textarea>
    <button class="chat-send-btn" id="chatSendBtn">
      <svg viewBox="0 0 20 20" fill="none" width="15" height="15">
        <path d="M3 10L17 3l-4.5 14-2.5-6L3 10z" fill="currentColor"/>
      </svg>
    </button>
  </div>`;

  document.getElementById("chatBackBtn")?.addEventListener("click", () => {
    cleanupActiveChat();
    renderChatHub();
  });
  document.getElementById("chatCloseBtn")?.addEventListener("click", closeChatPanel);

  const chatInput = document.getElementById("chatInput");
  const chatSendBtn = document.getElementById("chatSendBtn");

  const doSend = () => {
    const text = (chatInput?.value || "").trim();
    if (!text || !_C.activeChatId) return;
    chatInput.value = "";
    chatInput.style.height = "auto";
    sendChatMessage(_C.activeChatId, text);
  };

  chatInput?.addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); doSend(); }
  });
  chatInput?.addEventListener("input", () => {
    chatInput.style.height = "auto";
    chatInput.style.height = Math.min(chatInput.scrollHeight, 80) + "px";
  });
  chatSendBtn?.addEventListener("click", doSend);
  chatInput?.focus();
}

function subscribeToChat(chatId) {
  if (_C.unsubChat) { _C.unsubChat(); _C.unsubChat = null; }
  _C.unsubChat = _fireDb.collection("chats").doc(chatId).collection("messages")
    .orderBy("createdAt", "asc")
    .onSnapshot(snap => {
      _C.messages = snap.docs.map(d => ({ id: d.id, ...d.data() }));
      renderChatMessages();
    }, err => {
      const el = document.getElementById("chatMessagesList");
      if (el) el.innerHTML = `<div class="chat-empty">Error: ${err.message}</div>`;
    });
}

function renderChatMessages() {
  const el = document.getElementById("chatMessagesList");
  if (!el) return;
  const myUid = _currentUser?.uid;

  if (!_C.messages.length) {
    el.innerHTML = '<div class="chat-empty">No messages yet. Say hello!</div>';
    return;
  }

  const items = [];
  let lastDay = "";

  for (let i = 0; i < _C.messages.length; i++) {
    const msg = _C.messages[i];
    const isMe = msg.senderUid === myUid;
    const d = msg.createdAt?.toDate ? msg.createdAt.toDate() : new Date();
    const dayKey = d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
    const time = d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });

    if (dayKey !== lastDay) {
      const label = dayKey === new Date().toLocaleDateString("en-US", { month: "short", day: "numeric" }) ? "Today" : dayKey;
      items.push(`<div class="chat-date-sep">${label}</div>`);
      lastDay = dayKey;
    }

    const prevMsg = i > 0 ? _C.messages[i - 1] : null;
    const showAvatar = !isMe && (!prevMsg || prevMsg.senderUid !== msg.senderUid);
    const escapedText = String(msg.text || "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");

    items.push(`<div class="chat-msg${isMe ? " chat-msg-me" : ""}">
      ${!isMe ? `<div class="chat-msg-avatar${showAvatar ? "" : " chat-msg-avatar-hidden"}">${(msg.senderName||"?").slice(0,2).toUpperCase()}</div>` : ""}
      <div class="chat-msg-bubble">
        <div class="chat-msg-text">${escapedText}</div>
        <div class="chat-msg-time">${time}</div>
      </div>
    </div>`);
  }

  el.innerHTML = items.join("");
  el.scrollTop = el.scrollHeight;
}

async function sendChatMessage(chatId, text) {
  if (!_fireDb || !_currentUser) return;
  const senderName = getDisplayName();
  const peerUid = _C.activePeerUid;
  const chatRef = _fireDb.collection("chats").doc(chatId);

  try {
    await chatRef.collection("messages").add({
      text, senderUid: _currentUser.uid, senderName,
      createdAt: firebase.firestore.FieldValue.serverTimestamp(),
    });

    await chatRef.set({
      participants: [_currentUser.uid, peerUid],
      participantNames: { [_currentUser.uid]: senderName, [peerUid]: _C.activePeerName || "" },
      lastMessage: text.length > 60 ? text.slice(0, 60) + "…" : text,
      lastAt: firebase.firestore.FieldValue.serverTimestamp(),
    }, { merge: true });

    await chatRef.update({ [`unread.${peerUid}`]: firebase.firestore.FieldValue.increment(1) });
  } catch (err) {
    showToast(`Failed to send: ${err.message}`, "error", 3000);
  }
}

async function clearChatUnread(chatId) {
  if (!_fireDb || !_currentUser) return;
  try {
    const ref = _fireDb.collection("chats").doc(chatId);
    const doc = await ref.get();
    if (doc.exists) await ref.update({ [`unread.${_currentUser.uid}`]: 0 });
  } catch {}
}

function subscribeToUnreadChats() {
  if (!_fireDb || !_currentUser) return;
  if (_C.unsubUnread) { _C.unsubUnread(); _C.unsubUnread = null; }
  _C.unsubUnread = _fireDb.collection("chats")
    .where("participants", "array-contains", _currentUser.uid)
    .onSnapshot(snap => {
      let total = 0;
      for (const doc of snap.docs) total += doc.data().unread?.[_currentUser.uid] || 0;
      _C.totalUnread = total;
      updateChatBadge();
    });
}

function updateChatBadge() {
  const btn = document.getElementById("chatBubble");
  if (!btn) return;
  let badge = btn.querySelector(".chat-bubble-badge");
  if (_C.totalUnread > 0) {
    if (!badge) { badge = document.createElement("span"); badge.className = "chat-bubble-badge"; btn.appendChild(badge); }
    badge.textContent = _C.totalUnread > 99 ? "99+" : String(_C.totalUnread);
  } else badge?.remove();
}

document.getElementById("chatBubble")?.addEventListener("click", toggleChatPanel);

// ══════════════════════════════════════════════════════════════
// CONTRACT EXPLORER
// ══════════════════════════════════════════════════════════════

const CT_TEAM_ABBR = {
  "Atlanta Hawks": "ATL", "Boston Celtics": "BOS", "Brooklyn Nets": "BKN",
  "Charlotte Hornets": "CHA", "Chicago Bulls": "CHI", "Cleveland Cavaliers": "CLE",
  "Dallas Mavericks": "DAL", "Denver Nuggets": "DEN", "Detroit Pistons": "DET",
  "Golden State Warriors": "GSW", "Houston Rockets": "HOU", "Indiana Pacers": "IND",
  "Los Angeles Clippers": "LAC", "Los Angeles Lakers": "LAL", "Memphis Grizzlies": "MEM",
  "Miami Heat": "MIA", "Milwaukee Bucks": "MIL", "Minnesota Timberwolves": "MIN",
  "New Orleans Pelicans": "NOP", "New York Knicks": "NYK", "Oklahoma City Thunder": "OKC",
  "Orlando Magic": "ORL", "Philadelphia 76ers": "PHI", "Phoenix Suns": "PHX",
  "Portland Trail Blazers": "POR", "Sacramento Kings": "SAC", "San Antonio Spurs": "SAS",
  "Toronto Raptors": "TOR", "Utah Jazz": "UTA", "Washington Wizards": "WAS",
};

const CT_CAP_BY_YEAR = {
  "2024-25": 141000000, "2025-26": 149500000, "2026-27": 156000000,
  "2027-28": 163000000, "2028-29": 170000000,
};
const CT_TAX_BY_YEAR = {
  "2024-25": 171315000, "2025-26": 181070000, "2026-27": 189060000,
  "2027-28": 197000000, "2028-29": 205000000,
};

const _ct = {
  data: null,
  view: "players",
  search: "",
  teamFilter: "all",
  year: "2025-26",
  sortBy: "salary",
  sortDir: 1,
  loading: false,
  inited: false,
};

function _ctFmt(n) {
  if (!n || n === 0) return "—";
  if (n >= 1000000) return "$" + (n / 1000000).toFixed(1) + "M";
  if (n >= 1000) return "$" + (n / 1000).toFixed(0) + "K";
  return "$" + n;
}

function _ctFAYear(player) {
  const years = Object.keys(player.salaries || {}).sort();
  if (!years.length) return null;
  return parseInt(years[years.length - 1].split("-")[0]) + 1;
}

function _ctYearsLeft(player, fromYear) {
  const all = Object.keys(player.salaries || {}).sort();
  const idx = all.indexOf(fromYear);
  return idx >= 0 ? all.length - idx : 0;
}

function _ctOptLabel(opt) {
  if (!opt) return null;
  const map = { "Team Option": "TO", "TO": "TO", "Player Option": "PO", "PO": "PO",
    "Early Termination": "ETO", "ETO": "ETO", "Two-Way": "2W" };
  return map[opt] || opt.slice(0, 3).toUpperCase();
}

function contractPageInit() {
  if (!_ct.inited) {
    _ctBindEvents();
    _ct.inited = true;
  }
  if (!_ct.data && !_ct.loading) {
    _ctLoad(false);
  } else if (_ct.data) {
    _ctRender();
  }
}

function _ctBindEvents() {
  _ctBindModalClose();
  document.querySelectorAll(".ct-view-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      _ct.view = btn.dataset.view;
      document.querySelectorAll(".ct-view-btn").forEach(b => b.classList.toggle("active", b === btn));
      _ctRender();
    });
  });
  document.getElementById("ctSearch")?.addEventListener("input", (e) => {
    _ct.search = e.target.value.toLowerCase().trim();
    _ctRender();
  });
  document.getElementById("ctTeamFilter")?.addEventListener("change", (e) => {
    _ct.teamFilter = e.target.value;
    _ctRender();
  });
  document.getElementById("ctYearSelect")?.addEventListener("change", (e) => {
    _ct.year = e.target.value;
    _ctRender();
  });
  document.getElementById("ctRefreshBtn")?.addEventListener("click", () => _ctLoad(true));
}

async function _ctLoad(force) {
  _ct.loading = true;
  const el = document.getElementById("ctContent");
  if (el) el.innerHTML = `<div class="ct-loading"><svg class="ct-spinner" viewBox="0 0 24 24" fill="none" width="24" height="24"><circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="2" opacity=".2"/><path d="M12 3a9 9 0 0 1 9 9" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/></svg>${force ? "Refreshing from HoopsHype…" : "Loading contract data…"}</div>`;
  try {
    const result = await window.nba2kDesktop.fetchContracts({ force: Boolean(force) });
    if (!result?.ok) throw new Error(result?.error || "Unknown error");
    _ct.data = result;
    _ctPopulateTeamFilter(result.players);
    _ctRender();
    if (result.cached) {
      const age = Math.round((Date.now() / 1000 - result.fetched_at) / 3600);
      showToast(`Contract data loaded (cached ${age}h ago)`, "info", 3000);
    } else {
      showToast(`Loaded ${result.players?.length || 0} player contracts from ${result.team_count || 30} teams`, "success", 3000);
    }
  } catch (err) {
    const el2 = document.getElementById("ctContent");
    if (el2) el2.innerHTML = `<div class="ct-error"><svg viewBox="0 0 20 20" fill="none" width="18" height="18"><path d="M10 3L2 17h16L10 3z" stroke="#f87171" stroke-width="1.4" stroke-linejoin="round"/><path d="M10 9v4M10 14.5v.5" stroke="#f87171" stroke-width="1.4" stroke-linecap="round"/></svg><span>Failed to load: ${err.message}</span><button class="btn-ghost btn-sm" onclick="_ctLoad(true)">Retry</button></div>`;
  }
  _ct.loading = false;
}

function _ctPopulateTeamFilter(players) {
  const el = document.getElementById("ctTeamFilter");
  if (!el) return;
  const teams = [...new Set((players || []).map(p => p.team))].sort();
  el.innerHTML = '<option value="all">All Teams</option>' +
    teams.map(t => `<option value="${t}">${CT_TEAM_ABBR[t] || t}</option>`).join("");
  el.value = _ct.teamFilter;
}

function _ctRender() {
  if (!_ct.data) return;
  if (_ct.view === "players") _ctRenderPlayers();
  else if (_ct.view === "cap") _ctRenderCap();
  else if (_ct.view === "fa") _ctRenderFA();
}

function _ctFiltered() {
  let players = _ct.data?.players || [];
  if (_ct.teamFilter !== "all") players = players.filter(p => p.team === _ct.teamFilter);
  if (_ct.search) players = players.filter(p =>
    p.name.toLowerCase().includes(_ct.search) ||
    p.team.toLowerCase().includes(_ct.search) ||
    (CT_TEAM_ABBR[p.team] || "").toLowerCase().includes(_ct.search)
  );
  return players;
}

function _ctSorted(players) {
  const yr = _ct.year;
  const d = _ct.sortDir;
  return [...players].sort((a, b) => {
    if (_ct.sortBy === "name") return d * a.name.localeCompare(b.name);
    if (_ct.sortBy === "team") {
      const tc = a.team.localeCompare(b.team);
      if (tc !== 0) return tc;
      return d * ((b.salaries?.[yr] || 0) - (a.salaries?.[yr] || 0));
    }
    if (_ct.sortBy === "years") return d * (_ctYearsLeft(b, yr) - _ctYearsLeft(a, yr));
    return d * ((b.salaries?.[yr] || 0) - (a.salaries?.[yr] || 0));
  });
}

function _ctTeamHeaderHtml(teamName, players) {
  const yr = _ct.year;
  const cap = CT_CAP_BY_YEAR[yr] || 149500000;
  const tax = CT_TAX_BY_YEAR[yr] || 181070000;
  const color = PROG_TEAM_COLORS[teamName] || "#4da8ff";

  const totalPayroll = players.reduce((sum, p) => sum + (p.salaries?.[yr] || 0), 0);

  let statusCls, statusText;
  if (totalPayroll > tax) { statusCls = "ct-status-tax"; statusText = "Over Tax"; }
  else if (totalPayroll > cap) { statusCls = "ct-status-cap"; statusText = "Over Cap"; }
  else { statusCls = "ct-status-ok"; statusText = "Under Cap"; }

  const maxBar = tax * 1.35;
  const capPct = Math.round(cap / maxBar * 100);
  const taxPct = Math.round(tax / maxBar * 100);
  const fillPct = Math.min(Math.round(totalPayroll / maxBar * 100), 100);
  const fillCls = totalPayroll > tax ? "ct-bar-over-tax" : totalPayroll > cap ? "ct-bar-over-cap" : "ct-bar-ok";

  const diff = totalPayroll - cap;
  const diffAmt = Math.abs(diff);
  const diffHtml = diff > 0
    ? `<span class="ct-thdr-over">$${(diffAmt / 1e6).toFixed(1)}M over cap</span>`
    : `<span class="ct-thdr-space">$${(diffAmt / 1e6).toFixed(1)}M cap space</span>`;
  const fmtM = n => `$${(n / 1e6).toFixed(1)}M`;

  return `<div class="ct-team-hdr">
    <div class="ct-thdr-main">
      <div class="ct-thdr-accent" style="background:${color}"></div>
      <div class="ct-thdr-body">
        <div class="ct-thdr-top-row">
          <div class="ct-thdr-nameblock">
            <span class="ct-thdr-name">${teamName}</span>
            <span class="ct-thdr-meta">${players.length} players &middot; ${yr}</span>
          </div>
          <span class="ct-status-badge ${statusCls}">${statusText}</span>
          <div class="ct-thdr-nums">
            <span class="ct-thdr-payroll">${_ctFmt(totalPayroll)}</span>
            <span class="ct-thdr-diff">${diffHtml}</span>
          </div>
        </div>
        <div class="ct-gauge-wrap">
          <div class="ct-gauge-track">
            <div class="ct-gauge-fill ${fillCls}" style="width:${fillPct}%"></div>
            <div class="ct-gauge-line ct-gauge-cap-line" style="left:${capPct}%"></div>
            <div class="ct-gauge-line ct-gauge-tax-line" style="left:${taxPct}%"></div>
          </div>
          <div class="ct-gauge-refs">
            <span class="ct-gauge-ref-cap" style="left:${capPct}%"><span class="ct-gauge-dot cap-dot"></span>${fmtM(cap)} Cap</span>
            <span class="ct-gauge-ref-tax" style="left:${taxPct}%"><span class="ct-gauge-dot tax-dot"></span>${fmtM(tax)} Tax</span>
          </div>
        </div>
      </div>
    </div>
  </div>`;
}

function _ctRenderPlayers() {
  const allFiltered = _ctSorted(_ctFiltered());
  const el = document.getElementById("ctContent");
  if (!el) return;

  const isTeamView = _ct.teamFilter !== "all";
  const isAllTeams = !isTeamView && !_ct.search;
  const showTeamCol = !isTeamView;
  const LEAGUE_LIMIT = 50;
  const players = isAllTeams ? allFiltered.slice(0, LEAGUE_LIMIT) : allFiltered;
  const truncated = isAllTeams && allFiltered.length > LEAGUE_LIMIT;

  const allYears = new Set();
  players.forEach(p => Object.keys(p.salaries || {}).forEach(y => allYears.add(y)));
  const sortedYears = [...allYears].sort();
  const yi = sortedYears.indexOf(_ct.year);
  const displayYears = yi >= 0 ? sortedYears.slice(yi, yi + 3) : sortedYears.slice(0, 3);

  const arrow = (col) => {
    if (_ct.sortBy !== col) return '<span class="ct-sort-arrow">↕</span>';
    return `<span class="ct-sort-arrow active">${_ct.sortDir === -1 ? "↓" : "↑"}</span>`;
  };

  const countLabel = truncated
    ? `Top ${LEAGUE_LIMIT} earners of ${allFiltered.length} total`
    : `${players.length} player${players.length !== 1 ? "s" : ""}`;

  let html = `<div class="ct-table-wrap">`;

  if (isTeamView) {
    html += _ctTeamHeaderHtml(_ct.teamFilter, players);
  } else if (isAllTeams) {
    html += `<div class="ct-league-hint">
      <svg viewBox="0 0 16 16" fill="none" width="13" height="13"><circle cx="8" cy="8" r="6.5" stroke="currentColor" stroke-width="1.3" opacity=".6"/><path d="M8 5v4M8 10.5v.5" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/></svg>
      Select a team above to see their full roster — showing top ${LEAGUE_LIMIT} earners league-wide
    </div>`;
  }

  html += `<div class="ct-legend">
    <span class="ct-legend-item"><span class="ct-opt-badge ct-opt-po">PO</span>Player Option</span>
    <span class="ct-legend-item"><span class="ct-opt-badge ct-opt-to">TO</span>Team Option</span>
    <span class="ct-legend-item"><span class="ct-opt-badge ct-opt-qo">QO</span>Qualifying Offer</span>
    <span class="ct-legend-item"><span class="ct-opt-badge ct-opt-2w">2W</span>Two-Way</span>
  </div>`;

  html += `
    <div class="ct-count-bar">${countLabel}</div>
    <table class="ct-table">
      <thead>
        <tr class="ct-tr ct-tr-head">
          <th class="ct-th ct-th-rank">#</th>
          <th class="ct-th ct-th-name" data-sort="name">Player${arrow("name")}</th>
          ${showTeamCol ? `<th class="ct-th ct-th-team" data-sort="team">Team${arrow("team")}</th>` : ""}
          ${displayYears.map(y => `<th class="ct-th ct-th-sal${y === _ct.year ? " ct-th-primary" : ""}" data-sort="salary">${y}${y === _ct.year ? arrow("salary") : ""}</th>`).join("")}
          <th class="ct-th ct-th-yrs" data-sort="years">Yrs${arrow("years")}</th>
          <th class="ct-th ct-th-type">Type</th>
        </tr>
      </thead>
      <tbody>
  `;

  players.forEach((p, i) => {
    const abbr = CT_TEAM_ABBR[p.team] || "—";
    const color = PROG_TEAM_COLORS[p.team] || "#4da8ff";
    const yrsLeft = _ctYearsLeft(p, _ct.year);
    const lastYear = Object.keys(p.salaries || {}).sort().pop();
    const lastOptLabel = _ctOptLabel(p.options?.[lastYear]);
    const salCells = displayYears.map(y => {
      const s = p.salaries?.[y];
      const optL = _ctOptLabel(p.options?.[y]);
      const isPrimary = y === _ct.year;
      return `<td class="ct-td ct-td-sal${isPrimary ? " ct-sal-primary" : ""}">
        <span class="ct-sal-inner">
          <span class="ct-sal-amt${isPrimary ? " ct-sal-amt-primary" : ""}">${s ? _ctFmt(s) : '<span class="ct-no-sal">—</span>'}</span>
          ${optL ? `<span class="ct-opt-badge ct-opt-${optL.toLowerCase()}">${optL}</span>` : ""}
        </span>
      </td>`;
    }).join("");

    const pSlug = p.player_slug || p.name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
    html += `<tr class="ct-tr ct-tr-player">
      <td class="ct-td ct-td-rank">${i + 1}</td>
      <td class="ct-td ct-td-name"><span class="ct-player-link" data-slug="${pSlug}" data-id="${p.player_id || ""}" data-name="${p.name}" data-team="${p.team}">${p.name}</span></td>
      ${showTeamCol ? `<td class="ct-td ct-td-team"><span class="ct-team-dot" style="background:${color}"></span><span class="ct-team-abbr">${abbr}</span></td>` : ""}
      ${salCells}
      <td class="ct-td ct-td-yrs">${yrsLeft > 0 ? yrsLeft : "—"}</td>
      <td class="ct-td ct-td-type">${lastOptLabel ? `<span class="ct-opt-badge ct-opt-${lastOptLabel.toLowerCase()}">${lastOptLabel}</span>` : '<span class="ct-type-ufa">UFA</span>'}</td>
    </tr>`;
  });

  if (!isAllTeams && players.length > 0) {
    const labelCols = showTeamCol ? 3 : 2;
    const totCells = displayYears.map(y => {
      const tot = players.reduce((s, p) => s + (p.salaries?.[y] || 0), 0);
      const isPrimary = y === _ct.year;
      return `<td class="ct-td ct-td-sal ct-td-total${isPrimary ? " ct-sal-primary" : ""}">${tot > 0 ? _ctFmt(tot) : "—"}</td>`;
    }).join("");
    html += `<tr class="ct-tr ct-tr-total">
      <td class="ct-td ct-td-total-lbl" colspan="${labelCols}">TOTAL PAYROLL</td>
      ${totCells}
      <td class="ct-td ct-td-total" colspan="2"></td>
    </tr>`;
  }

  if (!players.length) html += `<tr><td colspan="${4 + displayYears.length + (showTeamCol ? 1 : 0)}" class="ct-empty">No players match your filters</td></tr>`;
  html += `</tbody></table></div>`;
  el.innerHTML = html;

  el.querySelectorAll("th[data-sort]").forEach(th => {
    th.style.cursor = "pointer";
    th.addEventListener("click", () => {
      const col = th.dataset.sort;
      if (_ct.sortBy === col) _ct.sortDir *= -1;
      else { _ct.sortBy = col; _ct.sortDir = -1; }
      _ctRenderPlayers();
    });
  });

  el.querySelectorAll(".ct-player-link").forEach(link => {
    link.addEventListener("click", () => {
      _ctOpenPlayerModal(link.dataset.slug, link.dataset.id, link.dataset.name, link.dataset.team);
    });
  });
}

function _ctCloseDrawer() {
  const drawer = document.getElementById("ctPlayerDrawer");
  if (drawer) drawer.classList.remove("ct-drawer-open");
}

async function _ctOpenPlayerModal(playerSlug, playerId, playerName, team) {
  const drawer = document.getElementById("ctPlayerDrawer");
  const body = document.getElementById("ctDrawerBody");
  if (!drawer || !body) return;

  const color = PROG_TEAM_COLORS[team] || "#4da8ff";
  const accent = drawer.querySelector(".ct-drawer-accent");
  const nameEl = drawer.querySelector(".ct-drawer-player-name");
  const teamEl = drawer.querySelector(".ct-drawer-player-team");

  if (accent) accent.style.background = color;
  if (nameEl) nameEl.textContent = playerName;
  if (teamEl) teamEl.textContent = team;

  drawer.classList.add("ct-drawer-open");
  body.innerHTML = `<div class="ct-drawer-loading">
    <svg class="ct-spinner" viewBox="0 0 24 24" fill="none" width="18" height="18">
      <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="2" opacity=".2"/>
      <path d="M12 3a9 9 0 0 1 9 9" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/>
    </svg>Loading…</div>`;

  try {
    const result = await window.nba2kDesktop.fetchPlayerHistory({ playerSlug, playerId });
    if (!result?.ok) throw new Error(result?.error || "Unknown error");
    _ctRenderDrawer(result, color);
  } catch (err) {
    if (body) body.innerHTML = `<div class="ct-drawer-err">${err.message}</div>`;
  }
}

function _ctRenderDrawer(data, color) {
  const body = document.getElementById("ctDrawerBody");
  if (!body) return;

  const currentYear = _ct.year;
  const nowStartYear = parseInt(currentYear.split("-")[0]);
  const seasons = (data.seasons || []).slice().sort((a, b) => a.year.localeCompare(b.year));

  if (!seasons.length) {
    body.innerHTML = `<div class="ct-drawer-empty">No salary data found.</div>`;
    return;
  }

  const totalCareer = seasons.reduce((s, r) => s + (r.salary || 0), 0);
  const careerMax = Math.max(...seasons.map(r => r.salary || 0));
  const peakSeason = seasons.find(r => r.salary === careerMax);

  // Summary cards
  const currentSeason = seasons.find(r => r.year === currentYear);
  const summary = `<div class="ct-drawer-stats">
    <div class="ct-drawer-stat">
      <div class="ct-drawer-stat-val">${currentSeason ? _ctFmt(currentSeason.salary) : "—"}</div>
      <div class="ct-drawer-stat-lbl">This Season</div>
    </div>
    <div class="ct-drawer-stat">
      <div class="ct-drawer-stat-val">${_ctFmt(careerMax)}</div>
      <div class="ct-drawer-stat-lbl">Career High ${peakSeason ? `<span class="ct-drawer-peak-yr">${peakSeason.year}</span>` : ""}</div>
    </div>
    <div class="ct-drawer-stat">
      <div class="ct-drawer-stat-val">${_ctFmt(totalCareer)}</div>
      <div class="ct-drawer-stat-lbl">Career Earnings</div>
    </div>
  </div>`;

  const rows = seasons.map(r => {
    const yr = parseInt(r.year.split("-")[0]);
    const isCurrent = r.year === currentYear;
    const isPast = yr < nowStartYear;
    const isFuture = yr > nowStartYear;
    const optL = r.option ? _ctOptLabel(r.option) : null;
    const barPct = careerMax > 0 ? Math.round((r.salary || 0) / careerMax * 100) : 0;
    const barColor = isCurrent ? color : isPast ? "rgba(255,255,255,0.14)" : "rgba(255,255,255,0.26)";
    return `<div class="ct-drow${isCurrent ? " ct-drow-current" : isPast ? " ct-drow-past" : " ct-drow-future"}">
      <div class="ct-drow-year">${r.year}${isCurrent ? `<span class="ct-cur-tag" style="background:${color}22;color:${color}">NOW</span>` : ""}</div>
      <div class="ct-drow-bar-wrap">
        <div class="ct-drow-bar-track">
          <div class="ct-drow-bar-fill" style="width:${barPct}%;background:${barColor}"></div>
        </div>
      </div>
      <div class="ct-drow-right">
        <span class="ct-drow-sal${isCurrent ? " ct-drow-sal-cur" : ""}" style="${isCurrent ? `color:${color}` : ""}">${r.salary ? _ctFmt(r.salary) : '<span class="ct-no-sal">—</span>'}</span>
        ${optL ? `<span class="ct-opt-badge ct-opt-${optL.toLowerCase()}">${optL}</span>` : ""}
      </div>
    </div>`;
  }).join("");

  body.innerHTML = summary + `<div class="ct-drawer-divider"></div><div class="ct-drawer-rows">${rows}</div>`;

  // Scroll current season into view inside the drawer
  requestAnimationFrame(() => {
    const cur = body.querySelector(".ct-drow-current");
    if (cur) cur.scrollIntoView({ block: "center", behavior: "smooth" });
  });
}

function _ctBindModalClose() {
  document.getElementById("ctDrawerClose")?.addEventListener("click", _ctCloseDrawer);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") _ctCloseDrawer();
  });
}

function _ctRenderCap() {
  const el = document.getElementById("ctContent");
  if (!el) return;
  const yr = _ct.year;
  const cap = CT_CAP_BY_YEAR[yr] || 141000000;
  const tax = CT_TAX_BY_YEAR[yr] || 171000000;

  const teamTotals = {};
  (_ct.data?.players || []).forEach(p => {
    const s = p.salaries?.[yr] || 0;
    if (s > 0) teamTotals[p.team] = (teamTotals[p.team] || 0) + s;
  });

  const sorted = Object.entries(teamTotals).sort((a, b) => b[1] - a[1]);
  const maxSal = sorted.length ? sorted[0][1] * 1.08 : 250000000;
  const capPct = (cap / maxSal * 100).toFixed(1);
  const taxPct = (tax / maxSal * 100).toFixed(1);

  let overTax = 0, overCap = 0, underCap = 0;
  sorted.forEach(([, s]) => { if (s > tax) overTax++; else if (s > cap) overCap++; else underCap++; });

  let html = `
    <div class="ct-cap-summary">
      <div class="ct-cap-stat"><span class="ct-cap-stat-val ct-over-tax">${overTax}</span><span class="ct-cap-stat-lbl">Over Tax</span></div>
      <div class="ct-cap-stat"><span class="ct-cap-stat-val ct-over-cap">${overCap}</span><span class="ct-cap-stat-lbl">Over Cap</span></div>
      <div class="ct-cap-stat"><span class="ct-cap-stat-val ct-under-cap">${underCap}</span><span class="ct-cap-stat-lbl">Under Cap</span></div>
      <div class="ct-cap-meta">
        <span class="ct-cap-meta-line"><span class="ct-ref-dot ct-ref-cap"></span>Cap: ${_ctFmt(cap)}</span>
        <span class="ct-cap-meta-line"><span class="ct-ref-dot ct-ref-tax"></span>Tax: ${_ctFmt(tax)}</span>
      </div>
    </div>
    <div class="ct-cap-chart-wrap">
      <div class="ct-cap-chart" style="--cap-pct:${capPct}%;--tax-pct:${taxPct}%">
        <div class="ct-ref-line ct-ref-cap-line"></div>
        <div class="ct-ref-line ct-ref-tax-line"></div>
  `;

  sorted.forEach(([team, total]) => {
    const pct = (total / maxSal * 100).toFixed(1);
    const abbr = CT_TEAM_ABBR[team] || team.slice(0, 3).toUpperCase();
    const color = PROG_TEAM_COLORS[team] || "#4da8ff";
    const barCls = total > tax ? "ct-bar-over-tax" : total > cap ? "ct-bar-over-cap" : "ct-bar-ok";
    html += `<div class="ct-cap-row">
      <span class="ct-cap-team"><span class="ct-team-dot" style="background:${color}"></span>${abbr}</span>
      <div class="ct-bar-track"><div class="ct-bar-fill ${barCls}" style="width:${pct}%"></div></div>
      <span class="ct-cap-val">${_ctFmt(total)}</span>
    </div>`;
  });

  if (!sorted.length) html += `<div class="ct-empty">No salary data for ${yr}</div>`;
  html += `</div></div>`;
  el.innerHTML = html;
}

function _ctRenderFA() {
  const el = document.getElementById("ctContent");
  if (!el) return;
  const players = _ctFiltered();

  const groups = {};
  players.forEach(p => {
    const yr = _ctFAYear(p);
    if (!yr) return;
    if (!groups[yr]) groups[yr] = [];
    groups[yr].push(p);
  });
  Object.values(groups).forEach(arr => arr.sort((a, b) => {
    const aS = Object.values(a.salaries || {}).reduce((x, y) => x + y, 0);
    const bS = Object.values(b.salaries || {}).reduce((x, y) => x + y, 0);
    return bS - aS;
  }));

  const thisYear = new Date().getFullYear(); // 2026
  // Only show FA classes from this offseason onwards — past years are already resolved
  const sortedYears = Object.keys(groups).map(Number).sort().filter(yr => yr >= thisYear);
  if (!sortedYears.length) { el.innerHTML = `<div class="ct-empty">No upcoming free agents found</div>`; return; }

  let html = `<div class="ct-fa-wrap">`;

  sortedYears.forEach(yr => {
    const group = groups[yr];
    const isCurrent = yr === thisYear;
    const label = isCurrent ? `${yr} Free Agents — This Offseason` : `${yr} Free Agent Class`;
    html += `<div class="ct-fa-group">
      <div class="ct-fa-group-hdr">
        <span class="ct-fa-year-badge">${yr}</span>
        <span class="ct-fa-group-title">${label}</span>
        <span class="ct-fa-count">${group.length} players</span>
      </div>
      <div class="ct-fa-grid">`;

    group.forEach(p => {
      const allYrs = Object.keys(p.salaries || {}).sort();
      const lastYr = allYrs[allYrs.length - 1];
      const lastSal = lastYr ? p.salaries[lastYr] : null;
      const optL = _ctOptLabel(p.options?.[lastYr]);
      const color = PROG_TEAM_COLORS[p.team] || "#4da8ff";
      const abbr = CT_TEAM_ABBR[p.team] || "—";
      const typeCls = optL === "TO" ? "ct-fa-to" : optL === "PO" ? "ct-fa-po" : optL === "ETO" ? "ct-fa-eto" : "ct-fa-ufa";
      const typeLabel = optL === "TO" ? "Team Option" : optL === "PO" ? "Player Option" : optL === "ETO" ? "Early Term." : "UFA";
      html += `<div class="ct-fa-card ${typeCls}">
        <div class="ct-fa-card-top">
          <span class="ct-fa-name">${p.name}</span>
          <span class="ct-fa-type-badge">${typeLabel}</span>
        </div>
        <div class="ct-fa-card-bot">
          <span class="ct-fa-team-badge" style="border-color:${color}40"><span class="ct-team-dot" style="background:${color}"></span>${abbr}</span>
          <span class="ct-fa-last-sal">${lastSal ? _ctFmt(lastSal) : "—"}</span>
        </div>
      </div>`;
    });

    html += `</div></div>`;
  });

  html += `</div>`;
  el.innerHTML = html;
}

function showContractPage() {
  _hideAllPages();
  contractPageEl.classList.remove("hidden");
  document.body.classList.add("profile-open");
  setActiveNav("navContractsBtn");
  contractPageInit();
}

document.getElementById("navContractsBtn")?.addEventListener("click", () => showContractPage());

// ─────────────────────────────────────────────────────────────────────────────
// Gear Explorer
// ─────────────────────────────────────────────────────────────────────────────

const _GR_BRAND_COLOR = {
  "nike":          "#e5e5e5",
  "jordan":        "#CF1F2E",
  "jordan brand":  "#CF1F2E",
  "adidas":        "#4169E1",
  "new balance":   "#FF6B35",
  "puma":          "#a855f7",
  "under armour":  "#22D3EE",
  "li-ning":       "#ef4444",
  "li ning":       "#ef4444",
  "anta":          "#16a34a",
  "peak":          "#f59e0b",
  "converse":      "#f97316",
  "reebok":        "#0ea5e9",
};

function _grBrandColor(brand) {
  return _GR_BRAND_COLOR[(brand || "").toLowerCase().trim()] || "#6b7280";
}

const _gr = {
  playerList:   null,
  listLoading:  false,
  selectedSlug: null,
  gearData:     null,
  gearLoading:  false,
  season:       "all",
  view:         "game-log",
  inited:       false,
};

// ── Init ──────────────────────────────────────────────────────

function gearPageInit() {
  if (!_gr.inited) {
    _gr.inited = true;
    _grBindEvents();
  }
  if (!_gr.playerList && !_gr.listLoading) _grLoadPlayerList();
  _grRender();
}

async function _grLoadPlayerList(force) {
  _gr.listLoading = true;
  _grUpdateSearchPlaceholder();
  const r = await window.nba2kDesktop.fetchGearPlayers({ force: !!force });
  _gr.listLoading = false;
  if (r?.ok && r.players?.length) {
    _gr.playerList = r.players;
    // Build season options from any existing data
  } else {
    _gr.playerList = [];
  }
  _grUpdateSearchPlaceholder();
}

function _grUpdateSearchPlaceholder() {
  const inp = document.getElementById("gearSearchInput");
  if (!inp) return;
  if (_gr.listLoading) {
    inp.placeholder = "Loading players…";
    inp.disabled = true;
  } else {
    inp.placeholder = "Search player…";
    inp.disabled = false;
  }
}

// ── Events ────────────────────────────────────────────────────

function _grBindEvents() {
  const inp = document.getElementById("gearSearchInput");
  const wrap = document.getElementById("gearSearchWrap");

  inp?.addEventListener("input", () => {
    const term = inp.value.trim();
    if (term.length < 1) { _grCloseDropdown(); return; }
    _grShowDropdown(term);
  });

  inp?.addEventListener("keydown", (e) => {
    if (e.key === "Escape") _grCloseDropdown();
    if (e.key === "ArrowDown") {
      const first = document.querySelector(".gr-dd-item");
      first?.focus();
    }
  });

  document.addEventListener("click", (e) => {
    if (!wrap?.contains(e.target)) _grCloseDropdown();
  });

  document.getElementById("gearSeasonFilter")?.addEventListener("change", (e) => {
    _gr.season = e.target.value;
    _grRenderShoeView();
  });

  document.getElementById("grViewTabs")?.addEventListener("click", (e) => {
    const btn = e.target.closest(".gr-view-btn");
    if (!btn) return;
    document.querySelectorAll(".gr-view-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    _gr.view = btn.dataset.view;
    _grRenderShoeView();
  });

  document.getElementById("gearRefreshBtn")?.addEventListener("click", async () => {
    _gr.playerList = null;
    await _grLoadPlayerList(true);
    if (_gr.selectedSlug) {
      _gr.gearData = null;
      _gr.gearLoading = true;
      _grRender();
      const r = await window.nba2kDesktop.fetchGearPlayer({ name: _gr.selectedSlug, force: true });
      _gr.gearLoading = false;
      _gr.gearData = r?.ok ? r : null;
      _grRender();
    }
  });
}

// ── Search dropdown ───────────────────────────────────────────

function _grShowDropdown(term) {
  const dd = document.getElementById("gearSearchDropdown");
  if (!dd) return;
  if (!_gr.playerList?.length) {
    dd.classList.add("hidden");
    return;
  }
  const tl = term.toLowerCase();
  const hits = _gr.playerList
    .filter(p => p.name.toLowerCase().includes(tl))
    .slice(0, 12);

  if (!hits.length) { dd.classList.add("hidden"); return; }

  dd.innerHTML = hits.map(p => `
    <button class="gr-dd-item" data-name="${p.name}">
      <span class="gr-dd-name">${p.name}</span>
    </button>
  `).join("");

  dd.querySelectorAll(".gr-dd-item").forEach(btn => {
    btn.addEventListener("click", () => {
      _grSelectPlayer(btn.dataset.name);
    });
    btn.addEventListener("keydown", (e) => {
      if (e.key === "Enter") _grSelectPlayer(btn.dataset.name);
      if (e.key === "ArrowDown") btn.nextElementSibling?.focus();
      if (e.key === "ArrowUp") btn.previousElementSibling?.focus();
    });
  });

  dd.classList.remove("hidden");
}

function _grCloseDropdown() {
  document.getElementById("gearSearchDropdown")?.classList.add("hidden");
}

// ── Load player gear ──────────────────────────────────────────

async function _grSelectPlayer(name) {
  const inp = document.getElementById("gearSearchInput");
  if (inp) inp.value = name;
  _grCloseDropdown();

  _gr.selectedSlug = name;
  _gr.gearData     = null;
  _gr.gearLoading  = true;
  _grRender();

  const r = await window.nba2kDesktop.fetchGearPlayer({ name });
  _gr.gearLoading = false;

  if (r?.ok && r.shoes?.length) {
    _gr.gearData = r;
    _grPopulateSeasons(r.shoes);
  } else {
    _gr.gearData = null;
    const msg = document.getElementById("gearEmptyMsg");
    if (msg) msg.textContent = r?.error || "No shoe data found for this player.";
  }
  _grRender();
}

function _grPopulateSeasons(shoes) {
  const sel = document.getElementById("gearSeasonFilter");
  if (!sel) return;
  const seasons = [...new Set(shoes.map(s => s.season).filter(Boolean))].sort().reverse();
  const cur = sel.value;
  sel.innerHTML = `<option value="all">All Seasons</option>` +
    seasons.map(s => `<option value="${s}">${s}</option>`).join("");
  if (seasons.includes(cur)) sel.value = cur;
  else sel.value = "all";
  _gr.season = sel.value;
}

// ── Render orchestration ──────────────────────────────────────

function _grRender() {
  const empty   = document.getElementById("gearEmpty");
  const loading = document.getElementById("gearLoading");
  const content = document.getElementById("gearContent");
  if (!empty || !loading || !content) return;

  if (_gr.gearLoading) {
    empty.classList.add("hidden");
    loading.classList.remove("hidden");
    content.classList.add("hidden");
    return;
  }
  if (!_gr.gearData) {
    empty.classList.remove("hidden");
    loading.classList.add("hidden");
    content.classList.add("hidden");
    return;
  }
  empty.classList.add("hidden");
  loading.classList.add("hidden");
  content.classList.remove("hidden");

  _grRenderPlayerHdr(_gr.gearData);
  _grRenderSummary(_gr.gearData);
  _grRenderBrandBar(_gr.gearData);
  _grRenderShoeView();
}

// ── Player header ─────────────────────────────────────────────

function _grRenderPlayerHdr(data) {
  const el = document.getElementById("gearPlayerHdr");
  if (!el) return;

  const recent = data.shoes?.[0];
  const color  = _grBrandColor(recent?.brand);
  const img    = recent?.image_url || "";
  const info   = data.player_info || {};

  el.innerHTML = `
    <div class="gr-phdr-left">
      <div class="gr-phdr-name">${data.player_name || "—"}</div>
      <div class="gr-phdr-meta">
        ${info.team ? `<span class="gr-phdr-team">${info.team}</span>` : ""}
        ${info.position ? `<span class="gr-phdr-pos">${info.position}</span>` : ""}
      </div>
    </div>
    <div class="gr-phdr-shoe-card">
      <div class="gr-phdr-shoe-label">Current Shoe</div>
      <div class="gr-phdr-shoe-inner">
        ${img
          ? `<div class="gr-phdr-img-wrap"><img class="gr-phdr-img" src="${img}" alt="" onerror="this.parentElement.style.display='none'"/></div>`
          : `<div class="gr-phdr-img-placeholder" style="background:${color}22"><svg viewBox="0 0 40 30" fill="none" width="40" height="30" opacity=".35"><path d="M4 20c0-4 3-7 7-7h2l2-6h10l2 6h2c4 0 7 3 7 7v2H4v-2z" stroke="currentColor" stroke-width="1.5"/></svg></div>`
        }
        <div class="gr-phdr-shoe-info">
          <div class="gr-phdr-shoe-model">${recent ? `${recent.brand} ${recent.model}`.trim() : "—"}</div>
          ${recent?.colorway ? `<div class="gr-phdr-shoe-cw">${recent.colorway}</div>` : ""}
          ${recent?.date ? `<div class="gr-phdr-shoe-date">Last worn ${recent.date}</div>` : ""}
        </div>
        <div class="gr-brand-dot" style="background:${color}"></div>
      </div>
    </div>
  `;
}

// ── Summary cards ─────────────────────────────────────────────

function _grRenderSummary(data) {
  const el = document.getElementById("gearSummaryRow");
  if (!el) return;
  const s    = data.summary || {};
  const mc   = s.model_counts || {};
  const topN = s.top_shoe_count || (s.top_shoe ? (mc[s.top_shoe] || 0) : 0);
  const topC = _grBrandColor(s.top_brand);

  // Current season: find most recent season in shoes
  const seasons = [...new Set((data.shoes || []).map(sh => sh.season).filter(Boolean))].sort().reverse();
  const curSeason = seasons[0] || "";
  const curCount  = curSeason
    ? (data.shoes || []).filter(sh => sh.season === curSeason).length
    : 0;

  el.innerHTML = `
    <div class="gr-stat-card">
      <div class="gr-stat-val">${s.total_games ?? 0}</div>
      <div class="gr-stat-lbl">Games Tracked</div>
    </div>
    <div class="gr-stat-card">
      <div class="gr-stat-val" style="color:${topC}">${s.top_brand || "—"}</div>
      <div class="gr-stat-lbl">Top Brand</div>
    </div>
    <div class="gr-stat-card gr-stat-card-wide">
      <div class="gr-stat-val gr-stat-shoe">${s.top_shoe || "—"}</div>
      <div class="gr-stat-lbl">Most Worn Shoe${topN > 0 ? ` · ${topN}g` : ""}</div>
    </div>
    <div class="gr-stat-card">
      <div class="gr-stat-val">${curCount}</div>
      <div class="gr-stat-lbl">${curSeason || "This Season"}</div>
    </div>
  `;
}

// ── Brand distribution bar ────────────────────────────────────

function _grRenderBrandBar(data) {
  const el = document.getElementById("gearBrandBar");
  if (!el) return;
  const bc = data.summary?.brand_counts || {};
  const total = Object.values(bc).reduce((a, b) => a + b, 0);
  if (!total) { el.innerHTML = ""; return; }

  const sorted = Object.entries(bc).sort((a, b) => b[1] - a[1]);
  const segments = sorted.map(([brand, count]) => {
    const pct = (count / total * 100).toFixed(1);
    const c   = _grBrandColor(brand);
    return `<div class="gr-bar-seg" style="width:${pct}%;background:${c}" title="${brand}: ${count} games (${pct}%)"></div>`;
  }).join("");

  const legend = sorted.map(([brand, count]) => {
    const pct = (count / total * 100).toFixed(0);
    const c   = _grBrandColor(brand);
    return `<div class="gr-bar-legend-item">
      <span class="gr-bar-dot" style="background:${c}"></span>
      <span class="gr-bar-brand">${brand}</span>
      <span class="gr-bar-count">${count}g · ${pct}%</span>
    </div>`;
  }).join("");

  el.innerHTML = `
    <div class="gr-bar-label">Brand Distribution</div>
    <div class="gr-bar-track">${segments}</div>
    <div class="gr-bar-legend">${legend}</div>
  `;
}

// ── Shoe view (game-log / by-shoe) ────────────────────────────

function _grFilteredShoes(shoes) {
  if (_gr.season === "all") return shoes;
  return shoes.filter(s => s.season === _gr.season);
}

function _grRenderShoeView() {
  if (!_gr.gearData) return;
  if (_gr.view === "by-shoe") _grRenderByShoe(_gr.gearData);
  else _grRenderGameLog(_gr.gearData);
}

// Game log view
function _grRenderGameLog(data) {
  const el = document.getElementById("gearShoeView");
  if (!el) return;
  const shoes = _grFilteredShoes(data.shoes || []);
  if (!shoes.length) {
    el.innerHTML = `<div class="gr-empty-view">No games for this filter.</div>`;
    return;
  }

  // Group by season
  const bySeason = {};
  for (const s of shoes) {
    const key = s.season || "Unknown Season";
    if (!bySeason[key]) bySeason[key] = [];
    bySeason[key].push(s);
  }
  const seasonKeys = Object.keys(bySeason).sort().reverse();

  let html = `<div class="gr-game-log">`;
  for (const season of seasonKeys) {
    const rows = bySeason[season];
    html += `<div class="gr-season-group">
      <div class="gr-season-lbl">${season} <span class="gr-season-count">${rows.length} games</span></div>
      <div class="gr-log-table">
        <div class="gr-log-hdr">
          <span>Date</span><span>Opponent</span><span>Shoe</span><span>Colorway</span>
          <span class="gr-col-stat">PTS</span><span class="gr-col-stat">REB</span><span class="gr-col-stat">AST</span>
        </div>`;
    for (const s of rows) {
      const bc = _grBrandColor(s.brand);
      const shoe = `${s.brand} ${s.model}`.trim() || "—";
      html += `<div class="gr-log-row">
        <span class="gr-log-date">${s.date || "—"}</span>
        <span class="gr-log-opp">${s.opponent || "—"}</span>
        <span class="gr-log-shoe">
          <span class="gr-brand-pip" style="background:${bc}"></span>
          <span>${shoe}</span>
        </span>
        <span class="gr-log-cw">${s.colorway || "—"}</span>
        <span class="gr-col-stat gr-stat-pts">${s.pts ?? "—"}</span>
        <span class="gr-col-stat">${s.reb ?? "—"}</span>
        <span class="gr-col-stat">${s.ast ?? "—"}</span>
      </div>`;
    }
    html += `</div></div>`;
  }
  html += `</div>`;
  el.innerHTML = html;
}

// By-shoe view
function _grRenderByShoe(data) {
  const el = document.getElementById("gearShoeView");
  if (!el) return;
  const shoes = _grFilteredShoes(data.shoes || []);

  // Group by full shoe name
  const byShoe = {};
  for (const s of shoes) {
    const key = `${s.brand} ${s.model}`.trim() || "Unknown";
    if (!byShoe[key]) byShoe[key] = { brand: s.brand, model: s.model, image_url: s.image_url, games: [] };
    byShoe[key].games.push(s);
  }
  const entries = Object.entries(byShoe).sort((a, b) => b[1].games.length - a[1].games.length);

  if (!entries.length) {
    el.innerHTML = `<div class="gr-empty-view">No shoes for this filter.</div>`;
    return;
  }

  const cards = entries.map(([name, info]) => {
    const bc   = _grBrandColor(info.brand);
    const cnt  = info.games.length;
    const avg  = (arr, key) => arr.length ? (arr.reduce((s, g) => s + (g[key] || 0), 0) / arr.length).toFixed(1) : "—";
    const img  = info.image_url;
    return `<div class="gr-shoe-card">
      <div class="gr-shoe-card-img" style="border-top-color:${bc}">
        ${img
          ? `<img src="${img}" alt="${name}" onerror="this.parentElement.innerHTML='<div class=gr-shoe-placeholder></div>'"/>`
          : `<div class="gr-shoe-placeholder"></div>`
        }
      </div>
      <div class="gr-shoe-card-body">
        <div class="gr-shoe-card-brand" style="color:${bc}">${info.brand || "—"}</div>
        <div class="gr-shoe-card-model">${info.model || "—"}</div>
        <div class="gr-shoe-card-stats">
          <span class="gr-shoe-games">${cnt}g</span>
          <span class="gr-shoe-avg">${avg(info.games, "pts")} PTS · ${avg(info.games, "reb")} REB · ${avg(info.games, "ast")} AST</span>
        </div>
      </div>
    </div>`;
  }).join("");

  el.innerHTML = `<div class="gr-shoe-grid">${cards}</div>`;
}

// ── Show page ─────────────────────────────────────────────────

function showGearPage() {
  _hideAllPages();
  gearPageEl.classList.remove("hidden");
  document.body.classList.add("profile-open");
  setActiveNav("navGearBtn");
  gearPageInit();
}

document.getElementById("navGearBtn")?.addEventListener("click", () => showGearPage());

// ── Boot ──────────────────────────────────────────────────────

startAuth();
