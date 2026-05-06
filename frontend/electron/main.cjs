const { spawn } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");
const { pathToFileURL } = require("url");

let autoUpdater;

let app, BrowserWindow, ipcMain, dialog, net, protocol;

const BADGE_TIER_TO_INT = {
  Bronze: 1,
  Silver: 2,
  Gold: 3,
  HOF: 4,
  Legend: 5,
};

const TEMPLATE_ATTRIBUTE_ALIASES = {
  three_point: "three_point_shot",
  mid_range: "mid_range_shot",
  ball_control: "ball_handle",
  passing_perception: "pass_perception",
  passing_accuracy: "pass_accuracy",
  passing_iq: "pass_iq",
  passing_vision: "pass_vision",
  speed_with_ball: "speed_with_ball",
};

const TEMPLATE_TENDENCY_ALIASES = {
  block_tendency: "block",
  steal_tendency: "on_ball_steal",
  driving_dunk_tendency: "driving_dunk",
  driving_layup_tendency: "driving_layup",
  putback_dunk: "putback",
  post_shoot: "shoot_from_post",
  post_dropstep: "post_drop_step",
  shot_tendency: "shot",
  off_screen_shot_mid: "off_screen_shot_mid_range",
  off_screen_shot_three: "off_screen_3",
  spot_up_shot_mid: "spot_up_shot_mid_range",
  spot_up_shot_three: "spot_up_3",
  contested_jumper_mid: "contested_jumper_mid_range",
  contested_jumper_three: "contested_3",
  step_back_jumper_mid: "stepback_jumper_mid_range",
  stepback_jumper_three: "step_back_3",
  drive_pull_up_mid: "drive_pull_up_mid_range",
  drive_pull_up_three: "drive_pull_up_three",
  dribble_stepback: "driving_step_back",
  dribble_crossover: "driving_crossover",
  dribble_spin: "driving_spin",
  dribble_half_spin: "driving_half_spin",
  dribble_double_crossover: "driving_double_crossover",
  dribble_behind_the_back: "driving_behind_the_back",
};

const TEMPLATE_BADGE_ALIASES = {
  ankle_breaker: "ankle_assassin",
  high_flying_denier: "high_flying_denier",
  handles_for_days: "handles_for_days",
  off_ball_pest: "off_ball_pest",
  on_ball_menace: "on_ball_menace",
  slippery_off_ball: "slippery_off_ball",
};

let cachedTemplatePath = "";

const NON_GAMEPLAY_BADGE_KEYS = new Set([
  "marketability",
  "work_ethic",
]);

function getProjectRoot() {
  // In packaged mode, resources are in <app>/resources/data/
  // __dirname is <app>/resources/app/electron/
  if (app.isPackaged) {
    return path.join(process.resourcesPath, "data");
  }
  return path.resolve(__dirname, "..", "..");
}

function resolvePythonPath() {
  const envPath = String(process.env.NBA2K_PYTHON_PATH || "").trim();
  if (envPath) return envPath;

  if (app.isPackaged) {
    const pyRoot = path.join(process.resourcesPath, "python");
    if (process.platform === "win32") {
      return path.join(pyRoot, "python.exe");
    }
    // python-build-standalone layout on Mac
    for (const rel of ["bin/python3.12", "bin/python3", "python"]) {
      const p = path.join(pyRoot, rel);
      if (fs.existsSync(p)) return p;
    }
    return path.join(pyRoot, "bin", "python3.12");
  }

  if (process.platform === "win32") {
    // Use Python 3.12 venv (3.14 has extremely slow imports)
    const venv312 = path.join(getProjectRoot(), ".venv312", "Scripts", "python.exe");
    if (fs.existsSync(venv312)) return venv312;
    return path.join(getProjectRoot(), ".venv", "Scripts", "python.exe");
  } else {
    const venv = path.join(getProjectRoot(), ".venv312", "bin", "python");
    if (fs.existsSync(venv)) return venv;
    for (const bin of ["python3.12", "python3", "python"]) {
      try { require("child_process").execSync(`which ${bin}`, { stdio: "pipe" }); return bin; } catch {}
    }
    return "python3";
  }
}

function resolveGeneratorCliPath() {
  return path.join(getProjectRoot(), "nba2k26_generator", "generator_cli.py");
}

function resolveDatabaseDir() {
  return path.join(getProjectRoot(), "NBA Site data");
}

function resolvePlayerRolesDir() {
  return path.join(getProjectRoot(), "Player Roles");
}

function normalizeExportKey(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

function defaultTemplatePath() {
  const projectRoot = getProjectRoot();
  const preferred = path.join(projectRoot, "Player Roles", "export json.txt");
  if (fs.existsSync(preferred)) return preferred;
  return path.join(os.homedir(), "Downloads", "LaMelo_Ball_1630163_2024_2k.json");
}

async function resolveTemplatePath(explicitPath) {
  const provided = String(explicitPath || "").trim();
  if (provided && fs.existsSync(provided)) return provided;

  if (cachedTemplatePath && fs.existsSync(cachedTemplatePath)) {
    return cachedTemplatePath;
  }

  const auto = defaultTemplatePath();
  if (fs.existsSync(auto)) {
    cachedTemplatePath = auto;
    return auto;
  }

  const downloadsDir = path.join(os.homedir(), "Downloads");
  if (fs.existsSync(downloadsDir)) {
    const candidates = fs
      .readdirSync(downloadsDir)
      .filter((name) => /export|template|2k/i.test(name))
      .map((name) => path.join(downloadsDir, name))
      .filter((full) => fs.existsSync(full) && fs.statSync(full).isFile())
      .sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs);
    for (const candidate of candidates) {
      try {
        const parsed = JSON.parse(fs.readFileSync(candidate, "utf-8"));
        if (parsed && typeof parsed === "object" && parsed.categories) {
          cachedTemplatePath = candidate;
          return candidate;
        }
      } catch {
        // Continue scanning candidates.
      }
    }
  }

  const picked = await dialog.showOpenDialog({
    title: "Select 2K JSON Template",
    filters: [
      { name: "Template Files", extensions: ["json", "txt"] },
      { name: "All Files", extensions: ["*"] },
    ],
    properties: ["openFile"],
  });
  if (picked.canceled || !picked.filePaths?.[0]) return null;
  const selected = picked.filePaths[0];
  cachedTemplatePath = selected;
  return selected;
}

/* Old 2-file builders (buildAttributesJson / buildTendenciesJson) removed.
   All exports now use single-file template-based format via build2kExportFromTemplate. */

function flattenTendencyValues(profile) {
  const out = {};
  const groups = profile?.tendencyGroups || {};

  const tendencyKeyVariants = (key) => {
    const base = normalizeExportKey(key);
    if (!base) return [];
    const variants = new Set([base]);
    variants.add(base.replace(/_mid_range$/g, "_mid"));
    variants.add(base.replace(/_shot_mid_range$/g, "_mid"));
    variants.add(base.replace(/_three$/g, "_3"));
    variants.add(base.replace(/_3$/g, "_three"));
    variants.add(base.replace(/^driving_/g, "drive_"));
    variants.add(base.replace(/^drive_/g, "driving_"));
    variants.add(base.replace(/^stepback_/g, "step_back_"));
    variants.add(base.replace(/^step_back_/g, "stepback_"));
    variants.add(base.replace(/^setup_/g, "set_up_"));
    variants.add(base.replace(/^set_up_/g, "setup_"));
    return Array.from(variants);
  };

  Object.values(groups).forEach((items) => {
    (items || []).forEach((item) => {
      const value = Number(item?.value ?? 0);
      tendencyKeyVariants(item?.name || item?.key || "").forEach((key) => {
        out[key] = value;
      });
    });
  });
  return out;
}

function flattenBadgeValues(profile) {
  const out = {};
  const groups = profile?.badgeGroups || {};
  Object.values(groups).forEach((items) => {
    (items || []).forEach((item) => {
      const key = normalizeExportKey(item?.name || item?.key || "");
      if (!key) return;
      out[key] = String(item?.value || "");
    });
  });
  return out;
}

function build2kExportFromTemplate(templateJson, profile) {
  const out = JSON.parse(JSON.stringify(templateJson || {}));
  const categories = out.categories || {};
  const generatedAttrs = profile?.attributes || {};
  const generatedTendencies = flattenTendencyValues(profile);
  const generatedBadges = flattenBadgeValues(profile);

  if (categories.Attributes && typeof categories.Attributes === "object") {
    Object.keys(categories.Attributes).forEach((templateKey) => {
      const normalized = normalizeExportKey(templateKey);
      const alias = TEMPLATE_ATTRIBUTE_ALIASES[normalized] || normalized;
      if (Object.prototype.hasOwnProperty.call(generatedAttrs, alias)) {
        categories.Attributes[templateKey] = Number(generatedAttrs[alias]);
      }
    });
  }

  if (categories.Tendencies && typeof categories.Tendencies === "object") {
    Object.keys(categories.Tendencies).forEach((templateKey) => {
      const normalized = normalizeExportKey(templateKey);
      const alias = TEMPLATE_TENDENCY_ALIASES[normalized] || normalized;
      if (Object.prototype.hasOwnProperty.call(generatedTendencies, alias)) {
        categories.Tendencies[templateKey] = Number(generatedTendencies[alias]);
      }
    });
  }

  if (categories.Badges && typeof categories.Badges === "object") {
    Object.keys(categories.Badges).forEach((templateKey) => {
      const normalized = normalizeExportKey(templateKey);
      if (NON_GAMEPLAY_BADGE_KEYS.has(normalized)) {
        return;
      }
      const alias = TEMPLATE_BADGE_ALIASES[normalized] || normalized;
      const tier = generatedBadges[alias];
      if (tier) {
        categories.Badges[templateKey] = BADGE_TIER_TO_INT[tier] || 0;
        return;
      }
      // For gameplay badge slots that are not earned, write explicit 0.
      if (Object.prototype.hasOwnProperty.call(TEMPLATE_BADGE_ALIASES, normalized) || Object.prototype.hasOwnProperty.call(BADGE_TIER_TO_INT, String(categories.Badges[templateKey]))) {
        categories.Badges[templateKey] = 0;
      } else if (!NON_GAMEPLAY_BADGE_KEYS.has(normalized)) {
        categories.Badges[templateKey] = 0;
      }
    });
  }

  return out;
}

function sanitizeFileStem(value) {
  const raw = String(value || "").trim() || "player";
  return raw.replace(/[<>:"/\\|?*]+/g, "_").replace(/\s+/g, "_");
}

function compressDirectoryToZip(sourceDir, destinationZip) {
  return new Promise((resolve, reject) => {
    const command = `Compress-Archive -Path '${sourceDir}\\*' -DestinationPath '${destinationZip}' -Force`;
    const child = spawn("powershell.exe", ["-NoProfile", "-Command", command], {
      windowsHide: true,
      stdio: ["ignore", "pipe", "pipe"],
    });
    let stderr = "";
    child.stderr.on("data", (chunk) => {
      stderr += String(chunk);
    });
    child.on("error", (err) => reject(err));
    child.on("close", (code) => {
      if (code === 0) {
        resolve();
        return;
      }
      reject(new Error(stderr || `Compress-Archive failed (${code})`));
    });
  });
}

function runGenerator({ player, season, mode }) {
  return new Promise((resolve, reject) => {
    const pythonPath = resolvePythonPath();
    const cliPath = resolveGeneratorCliPath();

    if (!fs.existsSync(pythonPath)) {
      reject(new Error(`Python was not found at: ${pythonPath}`));
      return;
    }
    if (!fs.existsSync(cliPath)) {
      reject(new Error(`Generator CLI was not found at: ${cliPath}`));
      return;
    }

    const args = [
      cliPath,
      "--player",
      player,
      "--season",
      season,
      "--mode",
      mode,
      "--database-dir",
      resolveDatabaseDir(),
      "--player-roles-dir",
      resolvePlayerRolesDir(),
    ];

    const child = spawn(pythonPath, args, {
      cwd: getProjectRoot(),
      env: { ...process.env, PYTHONIOENCODING: "utf-8", PYTHONPATH: getProjectRoot() },
      windowsHide: true,
      stdio: ["ignore", "pipe", "pipe"],
    });

    let stdout = "";
    let stderr = "";

    child.stdout.on("data", (chunk) => {
      stdout += String(chunk);
    });

    child.stderr.on("data", (chunk) => {
      stderr += String(chunk);
    });

    child.on("error", (err) => {
      reject(err);
    });

    child.on("close", (code) => {
      if (code === 0) {
        resolve({ ok: true, stdout, stderr, exitCode: code });
        return;
      }
      resolve({ ok: false, stdout, stderr, exitCode: code });
    });
  });
}

function runTeamGenerator({ team, season, mode }) {
  return new Promise((resolve, reject) => {
    const pythonPath = resolvePythonPath();
    const cliPath = resolveGeneratorCliPath();

    if (!fs.existsSync(pythonPath)) {
      reject(new Error(`Python was not found at: ${pythonPath}`));
      return;
    }
    if (!fs.existsSync(cliPath)) {
      reject(new Error(`Generator CLI was not found at: ${cliPath}`));
      return;
    }

    const args = [
      cliPath,
      "--team",
      team,
      "--season",
      season,
      "--mode",
      mode,
      "--database-dir",
      resolveDatabaseDir(),
      "--player-roles-dir",
      resolvePlayerRolesDir(),
    ];

    const child = spawn(pythonPath, args, {
      cwd: getProjectRoot(),
      env: { ...process.env, PYTHONIOENCODING: "utf-8", PYTHONPATH: getProjectRoot() },
      windowsHide: true,
      stdio: ["ignore", "pipe", "pipe"],
    });

    let stdout = "";
    let stderr = "";

    child.stdout.on("data", (chunk) => {
      stdout += String(chunk);
    });

    child.stderr.on("data", (chunk) => {
      stderr += String(chunk);
    });

    child.on("error", (err) => {
      reject(err);
    });

    child.on("close", (code) => {
      if (code === 0) {
        resolve({ ok: true, stdout, stderr, exitCode: code });
        return;
      }
      resolve({ ok: false, stdout, stderr, exitCode: code });
    });
  });
}

function buildPlayerProfile({ player, season }) {
  return new Promise((resolve, reject) => {
    const pythonPath = resolvePythonPath();
    const projectRoot = getProjectRoot();
    const dbDir = resolveDatabaseDir();
    const rolesDir = resolvePlayerRolesDir();

    if (!fs.existsSync(pythonPath)) {
      reject(new Error(`Python was not found at: ${pythonPath}`));
      return;
    }

    const code = [
      "import json, os, re, sys",
      "player = (sys.argv[1] if len(sys.argv) > 1 else '').strip()",
      "season = (sys.argv[2] if len(sys.argv) > 2 else '').strip()",
      "project_root = sys.argv[3] if len(sys.argv) > 3 else ''",
      "db_dir = sys.argv[4] if len(sys.argv) > 4 else ''",
      "roles_dir = sys.argv[5] if len(sys.argv) > 5 else ''",
      "badges_txt = os.path.join(project_root, 'Badges', 'NBA 2K26 Badges.txt')",
      "sys.path.insert(0, os.path.join(project_root, 'nba2k26_generator'))",
      "from generator_cli import (",
      "  load_rows, select_player_season_row, compute_tendencies,",
      "  compute_attribute_family_averages, compute_overall_rating, compute_badge_groups, ATTRIBUTE_FAMILIES, THREE_POINT_RULES, MID_POST_RULES,",
      "  DRIBBLE_RULES, DEFENSE_RULES",
      ")",
      "from generator_cli_ml import compute_attributes_ml",
      "def as_float(v, default=0.0):",
      "    try:",
      "        return float(v)",
      "    except Exception:",
      "        return default",
      "def normalize_key(name):",
      "    return re.sub(r'[^a-z0-9]+', '_', str(name).strip().lower()).strip('_')",
      "def season_year(label):",
      "    m = re.match(r'^(\\d{4})', str(label or '').strip())",
      "    return int(m.group(1)) if m else -1",
      "def first_non_empty(*values):",
      "    for v in values:",
      "        if v is None:",
      "            continue",
      "        s = str(v).strip()",
      "        if s and s.lower() not in {'none', 'nan', 'na', 'n/a'}:",
      "            return s",
      "    return ''",
      "def repair_text(value):",
      "    text = str(value or '')",
      "    if not text:",
      "        return ''",
      "    def likely_mojibake(s):",
      "        hints = ('\\u00c3', '\\u00c2', '\\u00e2', '\\u00c4', '\\u00c5', '\\u00d0', '\\u00f0', '\\u2021')",
      "        return any(h in s for h in hints) or any(0x80 <= ord(ch) <= 0x9F for ch in s)",
      "    def to_bytes(s):",
      "        out = bytearray()",
      "        for ch in s:",
      "            code = ord(ch)",
      "            if code <= 0xFF:",
      "                out.append(code)",
      "                continue",
      "            try:",
      "                raw = ch.encode('cp1252')",
      "            except Exception:",
      "                return None",
      "            if len(raw) != 1:",
      "                return None",
      "            out.extend(raw)",
      "        return bytes(out)",
      "    fixed = text",
      "    for _ in range(2):",
      "        if not likely_mojibake(fixed):",
      "            break",
      "        raw = to_bytes(fixed)",
      "        if not raw:",
      "            break",
      "        try:",
      "            decoded = raw.decode('utf-8')",
      "        except Exception:",
      "            break",
      "        if not decoded or decoded == fixed:",
      "            break",
      "        fixed = decoded",
      "    return fixed or text",
      "def format_height(row):",
      "    explicit = first_non_empty(row.get('height'), row.get('height_without_shoes'))",
      "    if explicit:",
      "        return explicit",
      "    inches_raw = first_non_empty(row.get('player_info_ht_in_in'))",
      "    if not inches_raw:",
      "        return 'NA'",
      "    total = int(as_float(inches_raw, 0.0))",
      "    if total <= 0:",
      "        return 'NA'",
      "    feet = total // 12",
      "    inches = total % 12",
      "    return f\"{feet}'{inches}\\\"\"",
      "def build_headshot_url(row):",
      "    nba_id = first_non_empty(row.get('player_id'))",
      "    if nba_id and str(nba_id).strip().isdigit():",
      "        return f\"https://cdn.nba.com/headshots/nba/latest/1040x760/{str(nba_id).strip()}.png\"",
      "    espn_id = first_non_empty(row.get('espn_id'), row.get('espn_player_id'), row.get('player_info_espn_id'))",
      "    if espn_id and str(espn_id).isdigit():",
      "        return f\"https://a.espncdn.com/i/headshots/nba/players/full/{espn_id}.png\"",
      "    return ''",
      "def build_team_logo_url(row):",
      "    tid = first_non_empty(row.get('team_id'))",
      "    if tid and str(tid).strip().isdigit():",
      "        return f\"https://cdn.nba.com/logos/nba/{str(tid).strip()}/primary/L/logo.svg\"",
      "    return ''",
      "def find_action_photo(row, project_root):",
      "    import unicodedata, re",
      "    name = repair_text(row.get('player_name', '')).strip()",
      "    if not name:",
      "        return ''",
      "    photos_dir = os.path.join(project_root, 'Player Photos')",
      "    if not os.path.isdir(photos_dir):",
      "        return ''",
      "    # Try exact name match with common extensions",
      "    for ext in ('.jpg', '.jpeg', '.png', '.webp'):",
      "        candidate = os.path.join(photos_dir, name + ext)",
      "        if os.path.isfile(candidate):",
      "            return candidate",
      "    # Try case-insensitive + accent-stripped match",
      "    def strip_accents(s):",
      "        nfkd = unicodedata.normalize('NFKD', s)",
      "        return ''.join(c for c in nfkd if not unicodedata.combining(c))",
      "    name_lower = strip_accents(name).lower()",
      "    for f in os.listdir(photos_dir):",
      "        stem, ext = os.path.splitext(f)",
      "        if ext.lower() in ('.jpg', '.jpeg', '.png', '.webp'):",
      "            if strip_accents(stem).lower() == name_lower:",
      "                return os.path.join(photos_dir, f)",
      "    return ''",
      "def tendency_group(name):",
      "    if name in THREE_POINT_RULES:",
      "        return 'Shooting'",
      "    if name in MID_POST_RULES:",
      "        return 'Finishing'",
      "    if name in DRIBBLE_RULES:",
      "        return 'Playmaking'",
      "    if name in DEFENSE_RULES:",
      "        return 'Defense'",
      "    lower = str(name).lower()",
      "    if 'dunk' in lower or 'layup' in lower or 'post' in lower:",
      "        return 'Finishing'",
      "    if 'pass' in lower or 'iso' in lower or 'pick' in lower or 'dribble' in lower:",
      "        return 'Playmaking'",
      "    if 'three' in lower or 'shot' in lower or 'jumper' in lower:",
      "        return 'Shooting'",
      "    if 'defense' in lower or 'contest' in lower or 'steal' in lower or 'block' in lower:",
      "        return 'Defense'",
      "    return 'General'",
      "def preferred_row(rows):",
      "    if not rows:",
      "        return None",
      "    for r in rows:",
      "        if str(r.get('team_abbr', '')).upper() == '2TM':",
      "            return r",
      "    return max(rows, key=lambda r: as_float(r.get('totals_mp', 0.0)))",
      "def select_player_row_with_fallback(rows, player, season_label):",
      "    target_player = repair_text(player).strip().lower()",
      "    target_season = str(season_label or '').strip().lower()",
      "    season_matches = [",
      "        r for r in rows",
      "        if repair_text(r.get('player_name', '')).strip().lower() == target_player",
      "        and str(r.get('season_label', '')).strip().lower() == target_season",
      "    ]",
      "    chosen = preferred_row(season_matches)",
      "    if chosen is not None:",
      "        return chosen",
      "",
      "    start = season_year(target_season)",
      "    if start == 2025:",
      "        fallback_rows = [",
      "            r for r in rows",
      "            if repair_text(r.get('player_name', '')).strip().lower() == target_player",
      "            and season_year(r.get('season_label', '')) == 2024",
      "        ]",
      "        chosen = preferred_row(fallback_rows)",
      "        if chosen is not None:",
      "            return chosen",
      "",
      "    raise ValueError(f\"No records found for player='{player}' season='{season_label}'\")",
      "def stat_snapshot(r):",
      "    if not r:",
      "        return {'pts': 0.0, 'reb': 0.0, 'ast': 0.0, 'stl': 0.0, 'blk': 0.0, 'fgPct': 0.0, 'fg3Pct': 0.0, 'gp': 0}",
      "    g = max(as_float(r.get('per_game_g', r.get('advanced_g', r.get('totals_g', 0.0)))), 1.0)",
      "    pts = as_float(r.get('per_game_pts_per_game', r.get('per_game_pts', as_float(r.get('totals_pts', 0.0)) / g)))",
      "    reb = as_float(r.get('per_game_reb_per_game', r.get('per_game_trb', as_float(r.get('totals_trb', 0.0)) / g)))",
      "    ast = as_float(r.get('per_game_ast_per_game', r.get('per_game_ast', as_float(r.get('totals_ast', 0.0)) / g)))",
      "    stl = as_float(r.get('per_game_stl_per_game', r.get('per_game_stl', as_float(r.get('totals_stl', 0.0)) / g)))",
      "    blk = as_float(r.get('per_game_blk_per_game', r.get('per_game_blk', as_float(r.get('totals_blk', 0.0)) / g)))",
      "    fg_raw = first_non_empty(r.get('per_game_fg_percent'), r.get('per_game_fg_pct'), r.get('shooting_fg_percent'), r.get('shooting_fg_pct'), r.get('totals_fg_percent'), r.get('totals_fg_pct'), r.get('fg_percent'), r.get('fg_pct'))",
      "    fg = as_float(fg_raw, None) if fg_raw else None",
      "    if fg is None:",
      "        fgm = as_float(r.get('totals_fg', 0.0))",
      "        fga = max(as_float(r.get('totals_fga', 0.0)), 1.0)",
      "        fg = fgm / fga",
      "    fg3_raw = first_non_empty(r.get('per_game_x3p_percent'), r.get('per_game_fg3_pct'), r.get('shooting_fg_percent_from_x3p_range'), r.get('shooting_fg3_pct'), r.get('totals_x3p_percent'), r.get('totals_fg3_pct'), r.get('fg3_percent'), r.get('fg3_pct'))",
      "    fg3 = as_float(fg3_raw, None) if fg3_raw else None",
      "    if fg3 is None:",
      "        fg3m = as_float(r.get('totals_fg3', 0.0))",
      "        fg3a = max(as_float(r.get('totals_fg3a', 0.0)), 1.0)",
      "        fg3 = fg3m / fg3a",
      "    return {",
      "      'pts': round(pts, 1), 'reb': round(reb, 1), 'ast': round(ast, 1),",
      "      'stl': round(stl, 1), 'blk': round(blk, 1),",
      "      'fgPct': round(fg, 3), 'fg3Pct': round(fg3, 3),",
      "      'gp': int(as_float(r.get('per_game_g', r.get('advanced_g', r.get('totals_g', 0.0)))))",
      "    }",
      "rows = load_rows(db_dir)",
      "row = select_player_row_with_fallback(rows, player, season)",
      "player_name = repair_text(row.get('player_name', '')).strip().lower()",
      "current_year = season_year(row.get('season_label', ''))",
      "player_rows = [r for r in rows if repair_text(r.get('player_name', '')).strip().lower() == player_name]",
      "prev_rows = [r for r in player_rows if season_year(r.get('season_label', '')) == current_year - 1]",
      "prev_row = preferred_row(prev_rows)",
      "source_row = row",
      "if current_year == 2025 and prev_row is not None:",
      "    source_row = prev_row",
      "current_snapshot = stat_snapshot(row)",
      "previous_snapshot = stat_snapshot(prev_row)",
      "career_rows = [r for r in player_rows if season_year(r.get('season_label', '')) <= current_year]",
      "career_total_g = 0.0",
      "career_acc = {'pts': 0.0, 'reb': 0.0, 'ast': 0.0, 'stl': 0.0, 'blk': 0.0, 'fgPct': 0.0, 'fg3Pct': 0.0}",
      "for cr in career_rows:",
      "    s = stat_snapshot(cr)",
      "    g = max(float(s.get('gp', 0)), 1.0)",
      "    career_total_g += g",
      "    for k in ['pts', 'reb', 'ast', 'stl', 'blk', 'fgPct', 'fg3Pct']:",
      "        career_acc[k] += float(s.get(k, 0.0)) * g",
      "career_snapshot = {k: round((career_acc[k] / career_total_g) if career_total_g > 0 else 0.0, 3 if 'Pct' in k else 1) for k in career_acc}",
      "career_snapshot['gp'] = int(round(career_total_g))",
      "# Override career stats with dedicated all-time leaders CSV if available.",
      "_career_csv = os.path.join(project_root, 'NBA Site data', 'Carrer Stats', 'alltime_leaders_per_game_regular_season.csv')",
      "if os.path.isfile(_career_csv):",
      "    import csv as _csv",
      "    def _sf(v, d=0.0):",
      "        try:",
      "            f = float(str(v or '').strip())",
      "            return f if f == f else d",
      "        except Exception:",
      "            return d",
      "    with open(_career_csv, newline='', encoding='utf-8-sig') as _cf:",
      "        _career_all = list(_csv.DictReader(_cf))",
      "    _nba_pid = str(row.get('player_id', '')).strip()",
      "    _pname_lower = repair_text(row.get('player_name', '')).strip().lower()",
      "    _matched_career = None",
      "    if _nba_pid:",
      "        for _cr in _career_all:",
      "            if str(_cr.get('PLAYER_ID', '')).strip() == _nba_pid:",
      "                _matched_career = _cr",
      "                break",
      "    if _matched_career is None:",
      "        for _cr in _career_all:",
      "            if _cr.get('PLAYER_NAME', '').strip().lower() == _pname_lower:",
      "                _matched_career = _cr",
      "                break",
      "    if _matched_career is not None:",
      "        def _sfn(v):",
      "            s = str(v or '').strip()",
      "            if not s: return None",
      "            try:",
      "                f = float(s)",
      "                return f if f == f else None",
      "            except Exception: return None",
      "        career_snapshot = {",
      "            'pts': round(_sf(_matched_career.get('PTS')), 1),",
      "            'reb': round(_sf(_matched_career.get('REB')), 1),",
      "            'ast': round(_sf(_matched_career.get('AST')), 1),",
      "            'stl': round(_sf(_matched_career.get('STL')), 1),",
      "            'blk': round(_sf(_matched_career.get('BLK')), 1),",
      "            'fgPct': round(_sf(_matched_career.get('FG_PCT')), 3),",
      "            'fg3Pct': round(_sf(_matched_career.get('FG3_PCT')), 3),",
      "            'ftPct': None if _sfn(_matched_career.get('FT_PCT')) is None else round(_sfn(_matched_career.get('FT_PCT')), 3),",
      "            'gp': int(_sf(_matched_career.get('GP'))),",
      "        }",
      "tendency_results = compute_tendencies(source_row)",
      "# Ensure source_row carries the selected season so committee correction triggers.",
      "source_row['season_label'] = season",
      "attribute_bundle = compute_attributes_ml(source_row, tendency_results, roles_dir, rows)",
      "attrs = attribute_bundle.get('attributes', {})",
      "roles = attribute_bundle.get('roles', [])",
      "family_scores = compute_attribute_family_averages(attrs)",
      "ovr = attribute_bundle.get('ovr', compute_overall_rating(source_row.get('position', ''), attrs, family_scores))",
      "badge_groups = compute_badge_groups(source_row, attrs, tendency_results, family_scores, ovr, badges_txt)",
      "sorted_attrs = sorted(attrs.items(), key=lambda kv: kv[1], reverse=True)",
      "strengths = [k for k, _v in sorted_attrs[:6]]",
      "weaknesses = [k for k, _v in sorted(attrs.items(), key=lambda kv: kv[1])[:6]]",
      "attribute_group_order = [",
      "  ('Finishing', ['Driving Layup', 'Standing Dunk', 'Driving Dunk', 'Close Shot']),",
      "  ('Shooting', ['Mid-Range Shot', 'Three-Point Shot', 'Free Throw', 'Shot IQ']),",
      "  ('Post Game', ['Post Hook', 'Post Fade', 'Post Control']),",
      "  ('Playmaking', ['Draw Foul', 'Ball Handle', 'Speed with Ball', 'Hands', 'Pass Accuracy', 'Pass IQ', 'Pass Vision']),",
      "  ('Mental', ['Offensive Consistency', 'Defensive Consistency']),",
      "  ('Defense', ['Interior Defense', 'Perimeter Defense', 'Steal', 'Block', 'Help Defense IQ', 'Pass Perception']),",
      "  ('Rebounding', ['Offensive Rebound', 'Defensive Rebound']),",
      "  ('Physical', ['Speed', 'Agility', 'Strength', 'Vertical', 'Stamina']),",
      "  ('Meta', ['Intangibles', 'Hustle', 'Overall Durability', 'Potential']),",
      "]",
      "attribute_groups = {}",
      "for family_name, names in attribute_group_order:",
      "    attribute_groups[family_name] = [",
      "        {'key': normalize_key(n), 'name': n, 'value': int(attrs.get(n, 0))}",
      "        for n in names if n in attrs",
      "    ]",
      "tendency_by_name = {t.name: t for t in tendency_results}",
      "tendency_by_norm = {normalize_key(t.name): t for t in tendency_results}",
      "tendency_aliases = {",
      "  'step_through_shot': ['step_through'],",
      "  'shot_under_basket': ['shot_under'],",
      "  'touches': ['touch'],",
      "  'shot_mid_range': ['shot_mid'],",
      "  'shot_three': ['shot_3'],",
      "  'spot_up_shot_mid_range': ['spot_up_mid', 'spot_up_shot_mid'],",
      "  'spot_up_shot_three': ['spot_up_3'],",
      "  'off_screen_shot_mid_range': ['off_screen_mid', 'off_screen_shot_mid'],",
      "  'off_screen_shot_three': ['off_screen_3'],",
      "  'contested_jumper_mid_range': ['contested_mid'],",
      "  'contested_jumper_three': ['contested_3'],",
      "  'stepback_jumper_mid_range': ['step_back_mid', 'stepback_jumper_mid_range'],",
      "  'stepback_jumper_three': ['step_back_3', 'stepback_jumper_three'],",
      "  'drive_pull_up_mid_range': ['dribble_pull_up_mid', 'drive_pull_up_mid'],",
      "  'drive_pull_up_three': ['dribble_pull_up_3', 'drive_pull_up_3'],",
      "  'driving_layup': ['drive'],",
      "  'hop_step_layup': ['hop_step'],",
      "  'euro_step_layup': ['eurostep'],",
      "  'transition_pull_up_three': ['transition_pull_up_3'],",
      "  'transition_spot_up': ['spot_vs_cut'],",
      "  'driving_crossover': ['drive_crossover'],",
      "  'driving_spin': ['drive_spin'],",
      "  'driving_step_back': ['drive_step_back'],",
      "  'driving_half_spin': ['drive_half_spin'],",
      "  'driving_double_crossover': ['drive_double_crossover'],",
      "  'driving_behind_the_back': ['drive_behind_back'],",
      "  'driving_dribble_hesitation': ['drive_hesitation'],",
      "  'driving_in_and_out': ['drive_in_out'],",
      "  'attack_strong_on_drive': ['attack_strong_drive'],",
      "  'setup_with_sizeup': ['set_up_size_up'],",
      "  'setup_with_hesitation': ['set_up_hesitation'],",
      "  'dish_to_open_man': ['dish'],",
      "  'iso_vs_elite_defender': ['iso_vs_elite'],",
      "  'iso_vs_good_defender': ['iso_vs_good'],",
      "  'iso_vs_average_defender': ['iso_vs_average'],",
      "  'iso_vs_poor_defender': ['iso_vs_poor'],",
      "  'post_shimmy_shot': ['post_shimmy'],",
      "  'post_aggressive_backdown': ['post_aggressive_back_down'],",
      "  'post_step_back_shot': ['post_step_back'],",
      "  'post_up_and_under': ['post_up_under', 'post_up_and_under', 'post_up_&_under'],",
      "  'post_drop_step': ['post_drop_step'],",
      "  'post_hop_step': ['post_hop_shot'],",
      "  'block_shot': ['block'],",
      "  'on_ball_steal': ['on_ball_steal'],",
      "}",
      "def resolve_tendency(name):",
      "    t = tendency_by_name.get(name)",
      "    if t:",
      "        return t",
      "    norm = normalize_key(name)",
      "    t = tendency_by_norm.get(norm)",
      "    if t:",
      "        return t",
      "    for alias in tendency_aliases.get(norm, []):",
      "        t = tendency_by_norm.get(alias)",
      "        if t:",
      "            return t",
      "    return None",
      "tendency_group_order = [",
      "  ('finishing', ['Step Through Shot', 'Shot Under Basket', 'Shot Close', 'Use Glass', 'Driving Layup', 'Standing Dunk', 'Driving Dunk', 'Flashy Dunk', 'Alley-Oop', 'Putback', 'Crash', 'Spin Layup', 'Hop Step Layup', 'Euro Step Layup', 'Floater']),",
      "  ('sub_zone', ['Shot Close Left', 'Shot Close Middle', 'Shot Close Right', 'Shot Mid Left', 'Shot Mid Left-Center', 'Shot Mid Center', 'Shot Mid Right-Center', 'Shot Mid Right', 'Shot Three Left', 'Shot Three Left-Center', 'Shot Three Center', 'Shot Three Right-Center', 'Shot Three Right']),",
      "  ('shooting', ['Shot Mid-Range', 'Spot Up Shot Mid-Range', 'Off Screen Shot Mid-Range', 'Shot Three', 'Spot Up Shot Three', 'Off Screen Shot Three', 'Contested Jumper Three', 'Contested Jumper Mid-Range', 'Stepback Jumper Three', 'Stepback Jumper Mid-Range', 'Spin Jumper', 'Transition Pull Up Three', 'Drive Pull Up Three', 'Drive Pull Up Mid-Range']),",
      "  ('triple_threat', ['Triple Threat Pump Fake', 'Triple Threat Jab Step', 'Triple Threat Idle', 'Triple Threat Shoot']),",
      "  ('dribble_setup', ['Setup With Sizeup', 'Setup With Hesitation', 'No Setup Dribble']),",
      "  ('driving', ['Drive', 'Spot Up Drive', 'Off Screen Drive', 'Drive Right', 'Attack Strong On Drive']),",
      "  ('dribble_moves', ['Driving Crossover', 'Driving Spin', 'Driving Step Back', 'Driving Half Spin', 'Driving Double Crossover', 'Driving Behind The Back', 'Driving Dribble Hesitation', 'Driving In And Out', 'No Driving Dribble Move']),",
      "  ('passing', ['Dish To Open Man', 'Flashy Pass', 'Alley-Oop Pass']),",
      "  ('post', ['Post Up', 'Post Shimmy Shot', 'Post Face Up', 'Post Back Down', 'Post Aggressive Backdown', 'Shoot From Post', 'Post Hook Left', 'Post Hook Right', 'Post Fade Left', 'Post Fade Right', 'Post Up And Under', 'Post Hop Shot', 'Post Step Back Shot', 'Post Drive', 'Post Spin', 'Post Drop Step', 'Post Hop Step']),",
      "  ('core', ['Shot', 'Touches', 'Play Discipline']),",
      "  ('playstyle', ['Roll vs. Pop', 'Transition Spot Up']),",
      "  ('isolation', ['Iso vs. Elite Defender', 'Iso vs. Good Defender', 'Iso vs. Average Defender', 'Iso vs. Poor Defender']),",
      "  ('defense', ['Pass Interception', 'Take Charge', 'On-Ball Steal', 'Contest Shot', 'Block Shot']),",
      "  ('physical', ['Foul', 'Hard Foul']),",
      "]",
      "tendency_groups = {}",
      "for group_name, names in tendency_group_order:",
      "    rows = []",
      "    for n in names:",
      "        t = resolve_tendency(n)",
      "        rows.append({",
      "            'key': normalize_key(n),",
      "            'name': n,",
      "            'value': int(t.final) if t else 0,",
      "            'preCap': float(t.pre_cap) if t else 0.0,",
      "            'recommendedCap': int(t.recommended_cap) if t else 0,",
      "            'absoluteCap': int(t.absolute_cap) if t else 0,",
      "        })",
      "    tendency_groups[group_name] = rows",
      "# Keep tendency groups exactly as ordered above; unmatched tendencies are surfaced as zeros.",
      "top_tendencies = sorted(tendency_results, key=lambda x: x.final, reverse=True)",
      "play_style = [t.name for t in top_tendencies[:3]]",
      "draft_year_raw = first_non_empty(row.get('draft_year'), row.get('draft_season'))",
      "draft_round_raw = first_non_empty(row.get('draft_round'), '')",
      "draft_number_raw = first_non_empty(row.get('draft_number'), '')",
      "if draft_year_raw and str(draft_year_raw).strip().lower() not in ('undrafted', '', 'none', 'nan'):",
      "    draft_str = str(draft_year_raw).strip()",
      "    if draft_round_raw and str(draft_round_raw).strip().lower() not in ('undrafted', '', 'none', 'nan'):",
      "        draft_str += f' R{draft_round_raw}'",
      "    if draft_number_raw and str(draft_number_raw).strip().lower() not in ('undrafted', '', 'none', 'nan'):",
      "        draft_str += f' Pick {draft_number_raw}'",
      "    draft_year_num = int(as_float(draft_year_raw, current_year))",
      "else:",
      "    draft_str = 'Undrafted' if str(draft_year_raw).strip().lower() == 'undrafted' else 'NA'",
      "    draft_year_num = current_year",
      "years_pro = max(0, current_year - draft_year_num) if current_year > 0 else 0",
      "height_display = first_non_empty(row.get('height'), '') or format_height(row)",
      "weight_val = first_non_empty(row.get('weight'), row.get('weight_lbs'), row.get('player_info_wt')) or 'NA'",
      "school_val = first_non_empty(row.get('college'), row.get('school'), row.get('draft_college'), row.get('player_info_colleges')) or 'NA'",
      "country_val = first_non_empty(row.get('country'), '') or ''",
      "photo_url = build_headshot_url(row)",
      "team_logo_url = build_team_logo_url(row)",
      "action_photo_path = find_action_photo(row, project_root)",
      "action_photo_url = ''",
      "if action_photo_path:",
      "    from urllib.parse import quote",
      "    action_photo_url = 'player-photo://' + quote(os.path.basename(action_photo_path), safe='')",
      "nba_pid = str(row.get('player_id', '')).strip()",
      "payload = {",
      "  'info': {",
      "      'name': repair_text(row.get('player_name', '')),",
      "      'team': str(row.get('team_abbr', '')),",
      "      'position': str(row.get('position', row.get('pos', ''))),",
      "      'season': str(row.get('season_label', '')),",
      "      'age': float(row.get('age', 0) or 0),",
      "      'height': height_display,",
      "      'weight': weight_val,",
      "      'yearsPro': int(as_float(row.get('experience', years_pro))),",
      "      'draft': draft_str,",
      "      'school': school_val,",
      "      'country': country_val,",
      "      'photoUrl': photo_url,",
      "      'teamLogoUrl': team_logo_url,",
      "      'actionPhotoUrl': action_photo_url,",
      "      'nbaPlayerId': nba_pid,",
      "  },",
      "  'ovr': ovr,",
      "  'role': (roles[0] if roles else 'Core'),",
      "  'archetype': (roles[0] if roles else 'Core'),",
      "  'archetypes': roles,",
      "  'usage': roles,",
      "  'strengths': strengths,",
      "  'weaknesses': weaknesses,",
      "  'familyScores': family_scores,",
      "  'attributes': {normalize_key(k): int(v) for k, v in attrs.items()},",
      "  'attributeGroups': attribute_groups,",
      "  'tendencyGroups': tendency_groups,",
      "  'badgeGroups': badge_groups,",
      "  'playStylePriorities': play_style,",
      "  'statBlocks': {'current': current_snapshot, 'previous': previous_snapshot, 'career': career_snapshot}",
      "}",
      "print(json.dumps(payload))",
    ].join("\n");

    const child = spawn(
      pythonPath,
      ["-c", code, player, season, projectRoot, dbDir, rolesDir],
      {
        cwd: projectRoot,
        windowsHide: true,
        stdio: ["ignore", "pipe", "pipe"],
      },
    );

    let stdout = "";
    let stderr = "";

    child.stdout.on("data", (chunk) => {
      stdout += String(chunk);
    });

    child.stderr.on("data", (chunk) => {
      stderr += String(chunk);
    });

    child.on("error", (err) => reject(err));

    child.on("close", (code) => {
      if (code !== 0) {
        resolve({ ok: false, error: stderr || `Profile generation failed (${code}).` });
        return;
      }
      try {
        const parsed = JSON.parse(stdout || "{}");
        resolve({ ok: true, profile: parsed });
      } catch (err) {
        resolve({ ok: false, error: `Failed to parse profile payload: ${String(err)}` });
      }
    });
  });
}

function generateTeamBatch({ players, season }) {
  return new Promise(async (resolve, reject) => {
    const pythonPath = resolvePythonPath();
    const projectRoot = getProjectRoot();
    const dbDir = resolveDatabaseDir();
    const rolesDir = resolvePlayerRolesDir();

    if (!fs.existsSync(pythonPath)) {
      reject(new Error(`Python was not found at: ${pythonPath}`));
      return;
    }

    if (!players || !players.length) {
      resolve({ ok: false, error: "No players provided." });
      return;
    }

    const fastScript = resolveGeneratorCliPath();
    if (!fs.existsSync(fastScript)) {
      reject(new Error(`Generator CLI not found: ${fastScript}`));
      return;
    }

    const profiles = [];
    const concurrency = 4;
    let idx = 0;

    function generateOne(playerName) {
      return new Promise((res) => {
        const child = spawn(
          pythonPath,
          ["-m", "nba2k26_generator.generator_cli", "--player", playerName, "--season", season, "--database-dir", dbDir, "--player-roles-dir", rolesDir, "--json"],
          {
            cwd: projectRoot,
            env: { ...process.env, PYTHONIOENCODING: "utf-8", PYTHONPATH: projectRoot },
            windowsHide: true,
            stdio: ["ignore", "pipe", "pipe"],
            maxBuffer: 50 * 1024 * 1024,
          },
        );

        let stdout = "";
        child.stdout.on("data", (chunk) => { stdout += String(chunk); });
        child.stderr.on("data", () => {});
        child.on("error", () => res({ ok: false, player: playerName, error: "Process error" }));
child.on("close", (code) => {
      console.log('Python script exit code:', code);
      console.log('Python stdout length:', stdout.length);
      console.log('Python stdout (first 500 chars):', stdout.slice(0, 500));
      console.log('Python stdout lines count:', stdout.trim().split("\n").length);
      
      if (code !== 0) {
            res({ ok: false, player: playerName, error: `Generation failed (${code})` });
            return;
          }
          try {
            const lastLine = stdout.trim().split("\n").pop();
            const parsed = JSON.parse(lastLine);
            if (parsed.ok && parsed.profile) {
              res({ ok: true, player: playerName, profile: parsed.profile });
            } else {
              res({ ok: false, player: playerName, error: parsed.error || "No profile in output" });
            }
          } catch {
            res({ ok: false, player: playerName, error: "Failed to parse output" });
          }
        });
      });
    }

    async function runWorkers() {
      const results = [];
      const workers = [];

      async function worker() {
        while (idx < players.length) {
          const currentIdx = idx++;
          const playerName = players[currentIdx];
          const result = await generateOne(playerName);
          results.push(result);
        }
      }

      for (let i = 0; i < Math.min(concurrency, players.length); i++) {
        workers.push(worker());
      }

      await Promise.all(workers);
      return results;
    }

    try {
      const results = await runWorkers();
      resolve({ ok: true, profiles: results });
    } catch (err) {
      resolve({ ok: false, error: String(err?.message || err) });
    }
  });
}

function searchPlayers({ term, season }) {
  return new Promise((resolve, reject) => {
    const pythonPath = resolvePythonPath();
    const projectRoot = getProjectRoot();
    const dbDir = resolveDatabaseDir();

    if (!fs.existsSync(pythonPath)) {
      reject(new Error(`Python was not found at: ${pythonPath}`));
      return;
    }

    const code = [
      "import csv, json, os, re, sys, unicodedata",
      "term = (sys.argv[1] if len(sys.argv) > 1 else '').strip().lower()",
      "season = (sys.argv[2] if len(sys.argv) > 2 else '').strip()",
      "project_root = sys.argv[3] if len(sys.argv) > 3 else ''",
      "db_dir = sys.argv[4] if len(sys.argv) > 4 else ''",
      "def norm_text(v):",
      "    s = unicodedata.normalize('NFKD', str(v or ''))",
      "    s = ''.join(ch for ch in s if not unicodedata.combining(ch))",
      "    s = re.sub(r'[^a-z0-9 ]+', ' ', s.lower())",
      "    return re.sub(r'\\s+', ' ', s).strip()",
      "def matches_search(name, term_norm):",
      "    name_norm = norm_text(name)",
      "    if term_norm in name_norm:",
      "        return True",
      "    search_words = term_norm.split()",
      "    name_words = name_norm.split()",
      "    matched = 0",
      "    for sw in search_words:",
      "        for nw in name_words:",
      "            if len(sw) >= 2 and len(nw) >= 2:",
      "                if nw.startswith(sw) or sw.startswith(nw):",
      "                    matched += 1",
      "                    break",
      "    return matched == len(search_words)",
      "def search_bio_csv():",
      "    bio_path = os.path.join(project_root, 'NBA Site data', season, f'player_bio_{season}_regular_season.csv')",
      "    if not os.path.isfile(bio_path):",
      "        return None",
      "    term_norm = norm_text(term)",
      "    results = []",
      "    with open(bio_path, newline='', encoding='utf-8-sig') as f:",
      "        reader = csv.DictReader(f)",
      "        for row in reader:",
      "            name = row.get('PLAYER_NAME', '').strip()",
      "            if term_norm and not matches_search(name, term_norm):",
      "                continue",
      "            results.append({",
      "                'name': name,",
      "                'team': row.get('TEAM_ABBREVIATION', '').strip(),",
      "                'position': row.get('POSITION', '').strip(),",
      "                'season': season,",
      "            })",
      "    return sorted(results, key=lambda x: x['name'])[:40]",
      "out = search_bio_csv()",
      "if out is not None:",
      "    print(json.dumps(out))",
      "else:",
      "    sys.path.insert(0, os.path.join(project_root, 'nba2k26_generator'))",
      "    from generator_cli import load_rows, repair_mojibake_text",
      "    def to_float(v):",
      "        try:",
      "            return float(v)",
      "        except Exception:",
      "            return 0.0",
      "    rows = load_rows(db_dir)",
      "    term_norm = norm_text(term)",
      "    seen = {}",
      "    for r in rows:",
      "        name = repair_mojibake_text(r.get('player_name', '')).strip()",
      "        sl = str(r.get('season_label', '')).strip()",
      "        if not name or not sl:",
      "            continue",
      "        if season and not sl.lower().startswith(season.lower()):",
      "            continue",
      "        if term_norm and not matches_search(name, term_norm):",
      "            continue",
      "        team = str(r.get('team_abbr', '')).strip()",
      "        pos = str(r.get('pos', '')).strip()",
      "        mp = to_float(r.get('totals_mp', 0.0))",
      "        key = (name.lower(), sl.lower())",
      "        cur = seen.get(key)",
      "        if cur is None or team.upper() == '2TM' or mp > cur['_mp']:",
      "            seen[key] = {'name': name, 'team': team, 'position': pos, 'season': sl, '_mp': mp}",
      "    out = sorted(seen.values(), key=lambda x: x['name'])[:40]",
      "    for x in out:",
      "        x.pop('_mp', None)",
      "    print(json.dumps(out))",
    ].join("\n");

    const child = spawn(
      pythonPath,
      ["-c", code, String(term || ""), String(season || ""), projectRoot, dbDir],
      {
        cwd: projectRoot,
        windowsHide: true,
        stdio: ["ignore", "pipe", "pipe"],
      },
    );

    let stdout = "";
    let stderr = "";

    child.stdout.on("data", (chunk) => {
      stdout += String(chunk);
    });

    child.stderr.on("data", (chunk) => {
      stderr += String(chunk);
    });

    child.on("error", (err) => reject(err));

    child.on("close", (code) => {
      if (code !== 0) {
        resolve({ ok: false, error: stderr || `Search process failed (${code}).` });
        return;
      }
      try {
        const parsed = JSON.parse(stdout || "[]");
        resolve({ ok: true, results: Array.isArray(parsed) ? parsed : [] });
      } catch (err) {
        resolve({ ok: false, error: `Failed to parse search results: ${String(err)}` });
      }
    });
  });
}

function getTeamRoster({ team, season }) {
  return new Promise((resolve, reject) => {
    const pythonPath = resolvePythonPath();
    const projectRoot = getProjectRoot();
    const dbDir = resolveDatabaseDir();

    if (!fs.existsSync(pythonPath)) {
      reject(new Error(`Python was not found at: ${pythonPath}`));
      return;
    }

    const code = [
      "import json, os, sys",
      "team = (sys.argv[1] if len(sys.argv) > 1 else '').strip().upper()",
      "season = (sys.argv[2] if len(sys.argv) > 2 else '').strip().lower()",
      "project_root = sys.argv[3] if len(sys.argv) > 3 else ''",
      "db_dir = sys.argv[4] if len(sys.argv) > 4 else ''",
      "sys.path.insert(0, os.path.join(project_root, 'nba2k26_generator'))",
      "from generator_cli import load_rows, repair_mojibake_text, select_team_season_rows",
      "def to_float(v):",
      "    try:",
      "        return float(v)",
      "    except Exception:",
      "        return 0.0",
      "rows = load_rows(db_dir)",
      "team_rows = select_team_season_rows(rows, team, season)",
      "out = []",
      "for r in team_rows:",
      "    pos_raw = r.get('position', r.get('pos', r.get('player_info_pos', '')))",
      "    pos = str(pos_raw or '').strip()",
      "    if pos.lower() in {'none', 'nan', 'na', 'n/a', ''}:",
      "        pos = str(r.get('player_info_pos', '') or '').strip()",
      "    if pos.lower() in {'none', 'nan', 'na', 'n/a', ''}:",
      "        pos = 'N/A'",
      "    nba_id = str(r.get('player_id', '')).strip()",
      "    photo = f'https://cdn.nba.com/headshots/nba/latest/1040x760/{nba_id}.png' if nba_id and nba_id.isdigit() else ''",
      "    out.append({",
      "        'name': repair_mojibake_text(r.get('player_name', '')).strip(),",
      "        'team': team,",
      "        'sourceTeam': str(r.get('team_abbr', '')).strip().upper(),",
      "        'position': pos,",
      "        'playerId': nba_id,",
      "        'photoUrl': photo,",
      "    })",
      "out = sorted(out, key=lambda x: x['name'])",
      "print(json.dumps(out))",
    ].join("\n");

    const child = spawn(
      pythonPath,
      ["-c", code, String(team || ""), String(season || ""), projectRoot, dbDir],
      {
        cwd: projectRoot,
        windowsHide: true,
        stdio: ["ignore", "pipe", "pipe"],
      },
    );

    let stdout = "";
    let stderr = "";

    child.stdout.on("data", (chunk) => {
      stdout += String(chunk);
    });

    child.stderr.on("data", (chunk) => {
      stderr += String(chunk);
    });

    child.on("error", (err) => reject(err));

    child.on("close", (code) => {
      if (code !== 0) {
        resolve({ ok: false, error: stderr || `Team roster process failed (${code}).` });
        return;
      }
      try {
        const parsed = JSON.parse(stdout || "[]");
        resolve({ ok: true, players: Array.isArray(parsed) ? parsed : [] });
      } catch (err) {
        resolve({ ok: false, error: `Failed to parse team roster: ${String(err)}` });
      }
    });
  });
}

function createWindow() {
  /* ── Register player-photo:// protocol to safely serve local images ── */
  if (protocol && protocol.handle) {
    protocol.handle("player-photo", (request) => {
      const decoded = decodeURIComponent(request.url.replace("player-photo://", ""));
      const photosDir = path.join(getProjectRoot(), "Player Photos");
      const filePath = path.join(photosDir, decoded);
      const resolvedDir = path.resolve(photosDir);
      const resolvedFile = path.resolve(filePath);
      if (!resolvedFile.startsWith(resolvedDir)) {
        return new Response("Forbidden", { status: 403 });
      }
      return net.fetch(pathToFileURL(resolvedFile).toString());
    });
  }

  const win = new BrowserWindow({
    width: 1320,
    height: 900,
    minWidth: 1060,
    minHeight: 720,
    title: "NBA 2K26 Generator",
    backgroundColor: "#0a0f1f",
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      preload: path.join(__dirname, "preload.cjs"),
    },
  });

  win.loadFile(path.join(__dirname, "..", "ui", "index.html"));

  win.webContents.setWindowOpenHandler(() => ({ action: "deny" }));

  win.webContents.on("did-fail-load", (_e, code, desc) => {
    dialog.showErrorBox("App failed to load", `Error ${code}: ${desc}`);
  });
}

// ─── Electron bootstrap ───────────────────────────────────────────────────────
// require("electron") returns the npm binary-path string at module load time
// because Electron's built-in module registry isn't ready yet. We poll via
// setImmediate until the registry is ready (usually within a few ticks).
function _waitForElectron(cb, attempt) {
  attempt = attempt || 0;
  const e = require("electron");
  if (e && typeof e === "object" && e.app) {
    cb(e);
  } else if (attempt < 500) {
    setImmediate(() => _waitForElectron(cb, attempt + 1));
  } else {
    process.stderr.write("NBA2K26 Generator: Electron API unavailable after 500 ticks — giving up.\n");
    process.exit(1);
  }
}

_waitForElectron((e) => {
  ({ app, BrowserWindow, ipcMain, dialog, net, protocol } = e);

  // Set early so electron-updater and other systems see the right path
  app.setPath("userData", path.join(os.tmpdir(), "NBA2K26-Generator-Desktop"));

  if (protocol && protocol.registerSchemesAsPrivileged) {
    protocol.registerSchemesAsPrivileged([
      { scheme: "player-photo", privileges: { standard: true, supportFetchAPI: true, secure: true, corsEnabled: true } },
    ]);
  }

ipcMain.handle("generator:run", async (_event, payload) => {
  const player = String(payload?.player || "").trim();
  const season = String(payload?.season || "").trim();
  const mode = String(payload?.mode || "both").trim();

  if (!player) return { ok: false, error: "Player name is required." };
  if (!season) return { ok: false, error: "Season is required." };

  try {
    return await runGenerator({ player, season, mode });
  } catch (err) {
    return { ok: false, error: String(err?.message || err) };
  }
});

ipcMain.handle("generator:search", async (_event, payload) => {
  const term = String(payload?.term || "").trim();
  const season = String(payload?.season || "").trim();
  try {
    return await searchPlayers({ term, season });
  } catch (err) {
    return { ok: false, error: String(err?.message || err) };
  }
});

ipcMain.handle("generator:team", async (_event, payload) => {
  const team = String(payload?.team || "").trim().toUpperCase();
  const season = String(payload?.season || "").trim();
  const mode = String(payload?.mode || "both").trim();
  if (!team) return { ok: false, error: "Team is required." };
  if (!season) return { ok: false, error: "Season is required." };
  try {
    return await runTeamGenerator({ team, season, mode });
  } catch (err) {
    return { ok: false, error: String(err?.message || err) };
  }
});

ipcMain.handle("generator:team-roster", async (_event, payload) => {
  const team = String(payload?.team || "").trim().toUpperCase();
  const season = String(payload?.season || "").trim();
  if (!team) return { ok: false, error: "Team is required." };
  if (!season) return { ok: false, error: "Season is required." };
  try {
    return await getTeamRoster({ team, season });
  } catch (err) {
    return { ok: false, error: String(err?.message || err) };
  }
});

ipcMain.handle("generator:profile", async (_event, payload) => {
  const player = String(payload?.player || "").trim();
  const season = String(payload?.season || "").trim();
  if (!player) return { ok: false, error: "Player name is required." };
  if (!season) return { ok: false, error: "Season is required." };
  try {
    return await buildPlayerProfile({ player, season });
  } catch (err) {
    return { ok: false, error: String(err?.message || err) };
  }
});

ipcMain.handle("generator:team-batch", async (_event, payload) => {
  const players = payload?.players || [];
  const season = String(payload?.season || "").trim();
  if (!players.length) return { ok: false, error: "Players list is required." };
  if (!season) return { ok: false, error: "Season is required." };
  try {
    return await generateTeamBatch({ players, season });
  } catch (err) {
    return { ok: false, error: String(err?.message || err) };
  }
});



ipcMain.handle("generator:export-player-json", async (_event, payload) => {
  const profile = payload?.profile || null;
  if (!profile) return { ok: false, error: "Profile payload is required." };

  try {
    const templatePath = await resolveTemplatePath();
    if (!templatePath) return { ok: false, error: "No export template found. Place export json.txt in Player Roles folder." };
    const templateJson = JSON.parse(fs.readFileSync(templatePath, "utf-8"));

    const playerName = sanitizeFileStem(profile?.info?.name || "player");
    const season = sanitizeFileStem(profile?.info?.season || "season");

    const saveResult = await dialog.showSaveDialog({
      title: "Save 2K Player JSON",
      defaultPath: path.join(os.homedir(), "Downloads", `${playerName}_${season}_2k.json`),
      filters: [{ name: "JSON", extensions: ["json"] }],
    });
    if (saveResult.canceled || !saveResult.filePath) {
      return { ok: false, error: "Save was cancelled." };
    }

    const exportJson = build2kExportFromTemplate(templateJson, profile);
    fs.writeFileSync(saveResult.filePath, JSON.stringify(exportJson), "utf-8");

    return { ok: true, filePath: saveResult.filePath };
  } catch (err) {
    return { ok: false, error: String(err?.message || err) };
  }
});

ipcMain.handle("generator:export-team-zip", async (_event, payload) => {
  const entries = Array.isArray(payload?.entries) ? payload.entries : [];
  if (!entries.length) return { ok: false, error: "No team player profiles to export." };

  try {
    const templatePath = await resolveTemplatePath();
    if (!templatePath) return { ok: false, error: "No export template found. Place export json.txt in Player Roles folder." };
    const templateJson = JSON.parse(fs.readFileSync(templatePath, "utf-8"));

    const team = sanitizeFileStem(payload?.team || "TEAM");
    const season = sanitizeFileStem(payload?.season || "season");

    const saveResult = await dialog.showSaveDialog({
      title: "Save 2K Team ZIP",
      defaultPath: path.join(os.homedir(), "Downloads", `${team}_${season}_2k_team_export.zip`),
      filters: [{ name: "ZIP", extensions: ["zip"] }],
    });
    if (saveResult.canceled || !saveResult.filePath) {
      return { ok: false, error: "Save was cancelled." };
    }

    const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "nba2k26-team-export-"));
    try {
      entries.forEach((entry, index) => {
        const profile = entry?.profile || null;
        if (!profile) return;

        const exportJson = build2kExportFromTemplate(templateJson, profile);
        const playerName = sanitizeFileStem(profile?.info?.name || entry?.name || `player_${index + 1}`);
        const playerIndex = String(index + 1).padStart(2, "0");

        const fileName = `${playerIndex}_${playerName}.json`;
        fs.writeFileSync(path.join(tempDir, fileName), JSON.stringify(exportJson), "utf-8");
      });

      await compressDirectoryToZip(tempDir, saveResult.filePath);
    } finally {
      try {
        fs.rmSync(tempDir, { recursive: true, force: true });
      } catch {
        // Best-effort cleanup for temp export directory.
      }
    }

    return { ok: true, filePath: saveResult.filePath };
  } catch (err) {
    return { ok: false, error: String(err?.message || err) };
  }
});

ipcMain.handle("generator:export-team-excel", async (_event, payload) => {
  const entries = Array.isArray(payload?.entries) ? payload.entries : [];
  if (!entries.length) return { ok: false, error: "No team player profiles to export." };

  const team = String(payload?.team || "TEAM").trim().toUpperCase();
  const season = String(payload?.season || "season").trim();

  try {
    const saveResult = await dialog.showSaveDialog({
      title: "Save Team Excel Export",
      defaultPath: path.join(os.homedir(), "Downloads", `${sanitizeFileStem(team)}_${sanitizeFileStem(season)}_2k_team.xlsx`),
      filters: [{ name: "Excel Workbook", extensions: ["xlsx"] }],
    });
    if (saveResult.canceled || !saveResult.filePath) {
      return { ok: false, error: "Save was cancelled." };
    }

    const pythonPath = resolvePythonPath();
    const projectRoot = getProjectRoot();
    const tempDataFile = path.join(os.tmpdir(), `nba2k26_excel_${Date.now()}.json`);
    try {
      fs.writeFileSync(tempDataFile, JSON.stringify({ team, season, entries }), "utf-8");

      const pyCode = [
        "import json, sys, os, re",
        "try:",
        "    import openpyxl",
        "    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side",
        "    from openpyxl.utils import get_column_letter",
        "except ImportError:",
        "    sys.exit('openpyxl not installed')",
        "data_path = sys.argv[1]",
        "out_path = sys.argv[2]",
        "with open(data_path, encoding='utf-8') as f:",
        "    data = json.load(f)",
        "team = data['team']",
        "season = data['season']",
        "entries = data['entries']",
        // ── Team color mapping ──
        "TEAM_COLORS = {",
        "  'ATL': 'FFE14434', 'BOS': 'FF007A33', 'BKN': 'FF606060', 'CHA': 'FF1D1160',",
        "  'CHI': 'FFCE1141', 'CLE': 'FF860038', 'DAL': 'FF0053BC', 'DEN': 'FF0D2240',",
        "  'DET': 'FFC8102E', 'GSW': 'FF1D428A', 'HOU': 'FFCE1141', 'IND': 'FF002D62',",
        "  'LAC': 'FFC8102E', 'LAL': 'FF552582', 'MEM': 'FF5D76A9', 'MIA': 'FF98002E',",
        "  'MIL': 'FF00471B', 'MIN': 'FF0C2340', 'NOP': 'FF001641', 'NYK': 'FF006BB6',",
        "  'OKC': 'FF007DC3', 'ORL': 'FF007DC5', 'PHI': 'FF006BB6', 'PHX': 'FF1D1160',",
        "  'POR': 'FFE03A3E', 'SAC': 'FF5B2B82', 'SAS': 'FF606060', 'TOR': 'FFCE1141',",
        "  'UTA': 'FF002B5C', 'WAS': 'FF002B5C',",
        "}",
        "TEAM_FULL_NAMES = {",
        "  'ATL': 'Atlanta Hawks', 'BOS': 'Boston Celtics', 'BKN': 'Brooklyn Nets',",
        "  'CHA': 'Charlotte Hornets', 'CHI': 'Chicago Bulls', 'CLE': 'Cleveland Cavaliers',",
        "  'DAL': 'Dallas Mavericks', 'DEN': 'Denver Nuggets', 'DET': 'Detroit Pistons',",
        "  'GSW': 'Golden State Warriors', 'HOU': 'Houston Rockets', 'IND': 'Indiana Pacers',",
        "  'LAC': 'LA Clippers', 'LAL': 'Los Angeles Lakers', 'MEM': 'Memphis Grizzlies',",
        "  'MIA': 'Miami Heat', 'MIL': 'Milwaukee Bucks', 'MIN': 'Minnesota Timberwolves',",
        "  'NOP': 'New Orleans Pelicans', 'NYK': 'New York Knicks', 'OKC': 'Oklahoma City Thunder',",
        "  'ORL': 'Orlando Magic', 'PHI': 'Philadelphia 76ers', 'PHX': 'Phoenix Suns',",
        "  'POR': 'Portland Trail Blazers', 'SAC': 'Sacramento Kings', 'SAS': 'San Antonio Spurs',",
        "  'TOR': 'Toronto Raptors', 'UTA': 'Utah Jazz', 'WAS': 'Washington Wizards',",
        "}",
        "team_argb = TEAM_COLORS.get(team, 'FF1D428A')",
        "team_full = TEAM_FULL_NAMES.get(team, team)",
        "ATTR_ORDER = ['Driving Layup', 'Standing Dunk', 'Driving Dunk', 'Close Shot',",
        "  'Mid-Range Shot', 'Three-Point Shot', 'Free Throw', 'Post Hook', 'Post Fade',",
        "  'Post Control', 'Draw Foul', 'Shot IQ', 'Ball Handle', 'Speed with Ball', 'Hands',",
        "  'Pass Accuracy', 'Pass IQ', 'Pass Vision', 'Offensive Consistency',",
        "  'Interior Defense', 'Perimeter Defense', 'Steal', 'Block',",
        "  'Offensive Rebound', 'Defensive Rebound', 'Help Defense IQ', 'Pass Perception',",
        "  'Defensive Consistency', 'Speed', 'Agility', 'Strength', 'Vertical', 'Stamina',",
        "  'Intangibles', 'Hustle', 'Overall Durability', 'Potential']",
        "TEND_ORDER = ['Shot', 'Touches', 'Shot Close', 'Shot Under Basket',",
        "  'Shot Close Left', 'Shot Close Middle', 'Shot Close Right',",
        "  'Shot Mid-Range', 'Spot Up Shot Mid-Range', 'Off-Screen Shot Mid-Range',",
        "  'Shot Mid Left', 'Shot Mid Left-Center', 'Shot Mid Center', 'Shot Mid Right-Center', 'Shot Mid Right',",
        "  'Shot Three', 'Spot Up Shot Three', 'Off-Screen Shot Three',",
        "  'Shot Three Left', 'Shot Three Left-Center', 'Shot Three Center', 'Shot Three Right-Center', 'Shot Three Right',",
        "  'Contested Jumper Mid-Range', 'Contested Jumper Three',",
        "  'Stepback Jumper Mid-Range', 'Stepback Three Point Shot',",
        "  'Spin Jumper', 'Transition Pull-Up Three Point Shot',",
        "  'Drive Pull-Up Mid-Range', 'Drive Pull-Up Three',",
        "  'Drive', 'Spot Up Drive', 'Off-Screen Drive',",
        "  'Use Glass', 'Step Through Shot', 'Driving Layup', 'Spin Layup',",
        "  'Euro Step Layup', 'Hop Step Layup', 'Floater',",
        "  'Standing Dunk', 'Driving Dunk', 'Flashy Dunk', 'Alley-Oop', 'Putback', 'Crash',",
        "  'Drive Right', 'Triple Threat Pump Fake', 'Triple Threat Jab Step', 'Triple Threat Idle', 'Triple Threat Shoot',",
        "  'Setup With Sizeup', 'Setup With Hesitation', 'No Setup Dribble',",
        "  'Driving Crossover', 'Driving Double Crossover', 'Driving Spin', 'Driving Half Spin',",
        "  'Driving Stepback', 'Driving Behind the Back', 'Driving Dribble Hesitation', 'Driving In & Out', 'No Driving Dribble Move',",
        "  'Attack Strong on Drive', 'Dish to Open Man', 'Flashy Pass', 'Alley-Oop Pass',",
        "  'Roll vs Pop', 'Transition Spot Up vs Cut to the Basket',",
        "  'Iso vs Elite Defender', 'Iso vs Good Defender', 'Iso vs Average Defender', 'Iso vs Poor Defender',",
        "  'Play Discipline',",
        "  'Post Up', 'Post Back Down', 'Post Aggressive Backdown', 'Post Face Up',",
        "  'Post Spin', 'Post Drive', 'Post Drop Step', 'Shoot From Post',",
        "  'Post Hook Left', 'Post Hook Right', 'Post Fade Left', 'Post Fade Right',",
        "  'Post Shimmy Shot', 'Post Hop Step', 'Post Stepback Shot', 'Post Up & Under',",
        "  'Take Charge', 'Foul', 'Hard Foul', 'Pass Interception', 'On-Ball Steal', 'Block Shot', 'Contest Shot']",
        "BADGE_TIER_COLORS = {",
        "  'HOF': 'FF800080', 'Legend': 'FFFF6600',",
        "  'Gold': 'FFFFD700', 'Silver': 'FFA0A0A0', 'Bronze': 'FFCD7F32',",
        "}",
        "BADGE_TIER_FONT_COLORS = {",
        "  'HOF': 'FFFFFFFF', 'Legend': 'FFFFFFFF',",
        "  'Gold': 'FF1A1A1A', 'Silver': 'FF1A1A1A', 'Bronze': 'FFFFFFFF',",
        "}",
        "def nk(name):",
        "    return re.sub(r'[^a-z0-9]+', '_', str(name).strip().lower()).strip('_')",
        "# Explicit aliases: TEND_ORDER name (normalized) -> profile tendency name (normalized)",
        "TEND_EXPLICIT_ALIASES = {",
        "    'stepback_three_point_shot': 'stepback_jumper_three',",
        "    'transition_pull_up_three_point_shot': 'transition_pull_up_three',",
        "    'transition_spot_up_vs_cut_to_the_basket': 'transition_spot_up',",
        "    'driving_stepback': 'driving_step_back',",
        "}",
        "def tend_lookup(tend_groups, want_name):",
        "    wk = nk(want_name)",
        "    alias_wk = TEND_EXPLICIT_ALIASES.get(wk, wk)",
        "    # Direct lookup by normalized key in all groups (including aliases)",
        "    for group in tend_groups.values():",
        "        for item in group:",
        "            ik = nk(item.get('name',''))",
        "            ik2 = nk(item.get('key',''))",
        "            if ik == wk or ik2 == wk or ik == alias_wk or ik2 == alias_wk:",
        "                return item.get('value', 0)",
        "    # Partial match fallback (requires 2+ overlapping words for safety)",
        "    wwords = set(re.findall(r'[a-z0-9]+', alias_wk))",
        "    best_match, best_score = None, 0",
        "    for group in tend_groups.values():",
        "        for item in group:",
        "            iwords = set(re.findall(r'[a-z0-9]+', nk(item.get('name',''))))",
        "            overlap = len(wwords & iwords)",
        "            if overlap > best_score and overlap >= max(2, len(wwords)-1):",
        "                best_score, best_match = overlap, item.get('value', 0)",
        "    return best_match if best_match is not None else 0",
        "def attr_lookup(attr_groups, want_name):",
        "    # attrs is a flat dict {normalized_key: value}",
        "    flat_attrs = {}",
        "    for group in attr_groups.values():",
        "        for item in group:",
        "            flat_attrs[nk(item.get('name',''))] = item.get('value', 0)",
        "    return flat_attrs.get(nk(want_name), 0)",
        "def make_fill(argb):",
        "    return PatternFill(fill_type='solid', fgColor=argb)",
        "def header_align():",
        "    return Alignment(horizontal='center', vertical='center', wrap_text=True)",
        "def data_align():",
        "    return Alignment(horizontal='center', vertical='center', wrap_text=False)",
        "def name_align():",
        "    return Alignment(horizontal='left', vertical='center', wrap_text=False)",
        "THIN_SIDE = Side(border_style='thin', color='FF888888')",
        "THIN_BORDER = Border(top=THIN_SIDE, bottom=THIN_SIDE, left=THIN_SIDE, right=THIN_SIDE)",
        "BLACK_FILL = make_fill('FF000000')",
        "TEAM_FILL = make_fill(team_argb)",
        "WHITE_FONT = Font(bold=True, size=10, color='FFFFFFFF')",
        "HEADER_FONT = Font(bold=True, size=9, color='FF1A1A1A')",
        "wb = openpyxl.Workbook()",
        // ── ATTRIBUTES SHEET ──
        "ws_attr = wb.active",
        "ws_attr.title = 'Attributes'",
        "all_cols = [''] + ['Attributes\\n(In Order)'] + ATTR_ORDER",
        "# Row 1: headers",
        "ws_attr.row_dimensions[1].height = 38.25",
        "for ci, col_name in enumerate(all_cols, 1):",
        "    c = ws_attr.cell(row=1, column=ci, value=col_name if ci > 1 else None)",
        "    c.font = HEADER_FONT",
        "    c.alignment = header_align()",
        "    if ci >= 3:",
        "        c.border = THIN_BORDER",
        "# Row 2: black separator",
        "ws_attr.row_dimensions[2].height = 15.75",
        "for ci in range(1, len(all_cols)+1):",
        "    ws_attr.cell(row=2, column=ci).fill = BLACK_FILL",
        "# Row 3: spacer with team color",
        "ws_attr.row_dimensions[3].height = 15.75",
        "for ci in range(1, len(all_cols)+1):",
        "    ws_attr.cell(row=3, column=ci).fill = TEAM_FILL",
        "# Row 4: team name",
        "ws_attr.row_dimensions[4].height = 18.75",
        "ws_attr.cell(row=4, column=2, value=team_full).font = WHITE_FONT",
        "for ci in range(1, len(all_cols)+1):",
        "    ws_attr.cell(row=4, column=ci).fill = TEAM_FILL",
        "# Player rows from row 5",
        "for pi, entry in enumerate(entries):",
        "    row = 5 + pi",
        "    ws_attr.row_dimensions[row].height = 15.75",
        "    pname = str(entry.get('name', '')).upper()",
        "    ag = entry.get('profile', {}).get('attributeGroups', {})",
        "    name_c = ws_attr.cell(row=row, column=2, value=pname)",
        "    name_c.font = WHITE_FONT",
        "    name_c.alignment = name_align()",
        "    ws_attr.cell(row=row, column=1).fill = TEAM_FILL",
        "    ws_attr.cell(row=row, column=2).fill = TEAM_FILL",
        "    for ai, attr_name in enumerate(ATTR_ORDER):",
        "        val = attr_lookup(ag, attr_name)",
        "        c = ws_attr.cell(row=row, column=3+ai, value=val or None)",
        "        c.alignment = data_align()",
        "        c.border = THIN_BORDER",
        "# Column widths",
        "ws_attr.column_dimensions['A'].width = 3",
        "ws_attr.column_dimensions['B'].width = 22",
        "for ci in range(3, 3+len(ATTR_ORDER)):",
        "    ws_attr.column_dimensions[get_column_letter(ci)].width = 8",
        "ws_attr.freeze_panes = 'C5'",
        // ── TENDENCY SHEET ──
        "ws_tend = wb.create_sheet('Tendency')",
        "all_tend_cols = [''] + ['Tendency\\n(In Order)'] + TEND_ORDER",
        "# Row 1: headers",
        "ws_tend.row_dimensions[1].height = 27.0",
        "for ci, col_name in enumerate(all_tend_cols, 1):",
        "    c = ws_tend.cell(row=1, column=ci, value=col_name if ci > 1 else None)",
        "    c.font = HEADER_FONT",
        "    c.alignment = header_align()",
        "    if ci >= 3:",
        "        c.border = THIN_BORDER",
        "ws_tend.row_dimensions[2].height = 15.75",
        "for ci in range(1, len(all_tend_cols)+1):",
        "    ws_tend.cell(row=2, column=ci).fill = BLACK_FILL",
        "ws_tend.row_dimensions[3].height = 15.75",
        "for ci in range(1, len(all_tend_cols)+1):",
        "    ws_tend.cell(row=3, column=ci).fill = TEAM_FILL",
        "ws_tend.row_dimensions[4].height = 18.75",
        "ws_tend.cell(row=4, column=2, value=team_full).font = WHITE_FONT",
        "for ci in range(1, len(all_tend_cols)+1):",
        "    ws_tend.cell(row=4, column=ci).fill = TEAM_FILL",
        "for pi, entry in enumerate(entries):",
        "    row = 5 + pi",
        "    ws_tend.row_dimensions[row].height = 15.75",
        "    pname = str(entry.get('name', '')).upper()",
        "    tg = entry.get('profile', {}).get('tendencyGroups', {})",
        "    name_c = ws_tend.cell(row=row, column=2, value=pname)",
        "    name_c.font = WHITE_FONT",
        "    name_c.alignment = name_align()",
        "    ws_tend.cell(row=row, column=1).fill = TEAM_FILL",
        "    ws_tend.cell(row=row, column=2).fill = TEAM_FILL",
        "    for ti, tend_name in enumerate(TEND_ORDER):",
        "        val = tend_lookup(tg, tend_name)",
        "        c = ws_tend.cell(row=row, column=3+ti, value=val)",
        "        c.alignment = data_align()",
        "        c.border = THIN_BORDER",
        "ws_tend.column_dimensions['A'].width = 3",
        "ws_tend.column_dimensions['B'].width = 22",
        "for ci in range(3, 3+len(TEND_ORDER)):",
        "    ws_tend.column_dimensions[get_column_letter(ci)].width = 7",
        "ws_tend.freeze_panes = 'C5'",
        // ── BADGES SHEET ──
        "ws_badges = wb.create_sheet('Badges')",
        "# Collect all unique badge names across the team",
        "all_badge_names = []",
        "seen_badge_names = set()",
        "for entry in entries:",
        "    bg = entry.get('profile', {}).get('badgeGroups', {})",
        "    for section, items in bg.items():",
        "        for item in (items if isinstance(items, list) else []):",
        "            bname = str(item.get('name', '')).strip()",
        "            if bname and bname not in seen_badge_names:",
        "                seen_badge_names.add(bname)",
        "                all_badge_names.append(bname)",
        "TIER_ORDER = {'Legend': 6, 'HOF': 5, 'Gold': 4, 'Silver': 3, 'Bronze': 2, '': 0}",
        "def norm_tier(v):",
        "    t = str(v or '').strip().lower()",
        "    if t == 'legend': return 'Legend'",
        "    if t in ('hof', 'hall of fame'): return 'HOF'",
        "    if t == 'gold': return 'Gold'",
        "    if t == 'silver': return 'Silver'",
        "    return 'Bronze'",
        "all_badge_cols = [''] + ['Player'] + all_badge_names",
        "# Row 1: headers",
        "ws_badges.row_dimensions[1].height = 38.25",
        "for ci, col_name in enumerate(all_badge_cols, 1):",
        "    c = ws_badges.cell(row=1, column=ci, value=col_name if ci > 1 else None)",
        "    c.font = HEADER_FONT",
        "    c.alignment = header_align()",
        "    if ci >= 3:",
        "        c.border = THIN_BORDER",
        "# Separator and team rows",
        "ws_badges.row_dimensions[2].height = 15.75",
        "for ci in range(1, len(all_badge_cols)+1):",
        "    ws_badges.cell(row=2, column=ci).fill = BLACK_FILL",
        "ws_badges.row_dimensions[3].height = 15.75",
        "for ci in range(1, len(all_badge_cols)+1):",
        "    ws_badges.cell(row=3, column=ci).fill = TEAM_FILL",
        "ws_badges.row_dimensions[4].height = 18.75",
        "ws_badges.cell(row=4, column=2, value=team_full).font = WHITE_FONT",
        "for ci in range(1, len(all_badge_cols)+1):",
        "    ws_badges.cell(row=4, column=ci).fill = TEAM_FILL",
        "# Player rows",
        "for pi, entry in enumerate(entries):",
        "    row = 5 + pi",
        "    ws_badges.row_dimensions[row].height = 15.75",
        "    pname = str(entry.get('name', '')).upper()",
        "    bg = entry.get('profile', {}).get('badgeGroups', {})",
        "    player_badges = {}",
        "    for section, items in bg.items():",
        "        for item in (items if isinstance(items, list) else []):",
        "            bname = str(item.get('name', '')).strip()",
        "            tier = norm_tier(item.get('value', ''))",
        "            if bname and (bname not in player_badges or TIER_ORDER.get(tier,0) > TIER_ORDER.get(player_badges[bname],0)):",
        "                player_badges[bname] = tier",
        "    name_c = ws_badges.cell(row=row, column=2, value=pname)",
        "    name_c.font = WHITE_FONT",
        "    name_c.alignment = name_align()",
        "    ws_badges.cell(row=row, column=1).fill = TEAM_FILL",
        "    ws_badges.cell(row=row, column=2).fill = TEAM_FILL",
        "    for bi, badge_name in enumerate(all_badge_names):",
        "        tier = player_badges.get(badge_name)",
        "        if tier:",
        "            cell = ws_badges.cell(row=row, column=3+bi, value=tier)",
        "            cell.fill = make_fill(BADGE_TIER_COLORS[tier])",
        "            cell.font = Font(bold=True, size=8, color=BADGE_TIER_FONT_COLORS[tier])",
        "            cell.alignment = data_align()",
        "            cell.border = THIN_BORDER",
        "ws_badges.column_dimensions['A'].width = 3",
        "ws_badges.column_dimensions['B'].width = 22",
        "for ci in range(3, 3+len(all_badge_names)):",
        "    ws_badges.column_dimensions[get_column_letter(ci)].width = 11",
        "ws_badges.freeze_panes = 'C5'",
        "wb.save(out_path)",
        "print('ok')",
      ].join("\n");

      const result = await new Promise((resolve) => {
        const child = spawn(
          pythonPath,
          ["-c", pyCode, tempDataFile, saveResult.filePath],
          { cwd: projectRoot, windowsHide: true, stdio: ["ignore", "pipe", "pipe"] },
        );
        let stderr = "";
        child.stderr.on("data", (chunk) => { stderr += String(chunk); });
        child.on("close", (code) => {
          if (code === 0) resolve({ ok: true });
          else resolve({ ok: false, error: stderr || `Python exited with code ${code}` });
        });
        child.on("error", (err) => resolve({ ok: false, error: String(err?.message || err) }));
      });
      return result.ok ? { ok: true, filePath: saveResult.filePath } : { ok: false, error: result.error };
    } finally {
      try { fs.unlinkSync(tempDataFile); } catch { /* best-effort cleanup */ }
    }
  } catch (err) {
    return { ok: false, error: String(err?.message || err) };
  }
});

ipcMain.handle("playbook:plays", async (_event, payload) => {
  const pythonPath = resolvePythonPath();
  const projectRoot = getProjectRoot();
  const playbookScriptPath = path.join(projectRoot, "Playbook", "playbook_editor.py");

  if (!fs.existsSync(pythonPath)) {
    return { ok: false, error: `Python not found at: ${pythonPath}` };
  }
  if (!fs.existsSync(playbookScriptPath)) {
    return { ok: false, error: `playbook_editor.py not found at: ${playbookScriptPath}` };
  }

  const tempFile = path.join(os.tmpdir(), `playbook_plays_${Date.now()}.txt`);
  
  return await new Promise((resolve) => {
    const child = spawn(pythonPath, [playbookScriptPath, "--list"], {
      cwd: path.join(projectRoot, "Playbook"),
      env: { ...process.env, PYTHONIOENCODING: "utf-8", PYTHONPATH: projectRoot },
      windowsHide: true,
      stdio: ["ignore", "pipe", "pipe"],
    });

    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => { stdout += String(chunk); });
    child.stderr.on("data", (chunk) => { stderr += String(chunk); });

    child.on("close", (code) => {
      if (code !== 0 && stderr) {
        resolve({ ok: false, error: stderr.trim() });
      } else {
        const plays = {};
        const lines = stdout.trim().split("\n");
        for (const line of lines) {
          const match = line.match(/^(\d+):\s*(.+)$/);
          if (match) {
            plays[parseInt(match[1], 10)] = match[2].trim();
          }
        }
        resolve({ ok: true, plays });
      }
    });

    child.on("error", (err) => {
      resolve({ ok: false, error: String(err?.message || err) });
    });
  });
});

ipcMain.handle("playbook:get", async (_event, payload) => {
  const team = String(payload?.team || "").trim().toUpperCase();
  if (!team) return { ok: false, error: "Team is required." };

  const pythonPath = resolvePythonPath();
  const projectRoot = getProjectRoot();
  const playbookScriptPath = path.join(projectRoot, "Playbook", "playbook_editor.py");

  if (!fs.existsSync(pythonPath)) {
    return { ok: false, error: `Python not found at: ${pythonPath}` };
  }
  if (!fs.existsSync(playbookScriptPath)) {
    return { ok: false, error: `playbook_editor.py not found at: ${playbookScriptPath}` };
  }

  return await new Promise((resolve) => {
    const child = spawn(pythonPath, [playbookScriptPath, "--team", team, "--large"], {
      cwd: path.join(projectRoot, "Playbook"),
      env: { ...process.env, PYTHONIOENCODING: "utf-8", PYTHONPATH: projectRoot },
      windowsHide: true,
      stdio: ["ignore", "pipe", "pipe"],
    });

    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => { stdout += String(chunk); });
    child.stderr.on("data", (chunk) => { stderr += String(chunk); });

child.on("close", (code) => {
      if (code !== 0) {
        const errMsg = stderr.trim() || stdout.trim() || "Failed to load playbook";
        resolve({ ok: false, error: errMsg });
      } else {
        const lines = stdout.split("\n");
        const playIndices = [];
        const plays = [];
        
        for (const line of lines) {
          if (!line.trim()) continue;
          if (line.includes(':') && line.includes('=')) {
            const parts = line.split(':');
            const nums = parts[1].match(/\d+/g);
            if (nums && nums.length >= 2) {
              const playId = parseInt(nums[0], 10);
              const rest = parts.slice(1).join(':').replace('=', '').trim();
              playIndices.push(playId);
              plays.push({ index: playId, name: rest });
            }
          }
        }
        
        resolve({ ok: true, team, plays, playIndices });
      }
    });

    child.on("error", (err) => {
      resolve({ ok: false, error: String(err?.message || err) });
    });
  });
});

ipcMain.handle("playbook:set", async (_event, payload) => {
  const team = String(payload?.team || "").trim().toUpperCase();
  const playIndices = Array.isArray(payload?.playIndices) ? payload.playIndices : [];
  
  if (!team) return { ok: false, error: "Team is required." };
  if (!playIndices.length) return { ok: false, error: "No plays provided." };

  const pythonPath = resolvePythonPath();
  const projectRoot = getProjectRoot();
  const playbookScriptPath = path.join(projectRoot, "Playbook", "playbook_editor.py");

  if (!fs.existsSync(pythonPath)) {
    return { ok: false, error: `Python not found at: ${pythonPath}` };
  }
  if (!fs.existsSync(playbookScriptPath)) {
    return { ok: false, error: `playbook_editor.py not found at: ${playbookScriptPath}` };
  }

  return await new Promise((resolve) => {
    const args = [playbookScriptPath, "--set", ...playIndices.map(String)];
    
    const child = spawn(pythonPath, args, {
      cwd: path.join(projectRoot, "Playbook"),
      env: { ...process.env, PYTHONIOENCODING: "utf-8", PYTHONPATH: projectRoot },
      windowsHide: true,
      stdio: ["ignore", "pipe", "pipe"],
    });

    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => { stdout += String(chunk); });
    child.stderr.on("data", (chunk) => { stderr += String(chunk); });

    child.on("close", (code) => {
      if (code !== 0) {
        resolve({ ok: false, error: stderr.trim() || "Failed to save playbook" });
      } else {
        resolve({ ok: true, team, playIndices, count: playIndices.length });
      }
    });

child.on("error", (err) => {
      resolve({ ok: false, error: String(err?.message || err) });
    });
  });
});

ipcMain.handle("playbook:add", async (_event, payload) => {
  const team = String(payload?.team || "").trim().toUpperCase();
  const playIndices = Array.isArray(payload?.playIndices) ? payload.playIndices : [];
  
  if (!team) return { ok: false, error: "Team is required." };
  if (!playIndices.length) return { ok: false, error: "No plays provided." };

  const pythonPath = resolvePythonPath();
  const projectRoot = getProjectRoot();
  const playbookScriptPath = path.join(projectRoot, "Playbook", "playbook_editor.py");

  if (!fs.existsSync(pythonPath)) {
    return { ok: false, error: `Python not found at: ${pythonPath}` };
  }
  if (!fs.existsSync(playbookScriptPath)) {
    return { ok: false, error: `playbook_editor.py not found at: ${playbookScriptPath}` };
  }

  return await new Promise((resolve) => {
    const args = [playbookScriptPath, "--add", ...playIndices.map(String)];
    
    const child = spawn(pythonPath, args, {
      cwd: path.join(projectRoot, "Playbook"),
      env: { ...process.env, PYTHONIOENCODING: "utf-8", PYTHONPATH: projectRoot },
      windowsHide: true,
      stdio: ["ignore", "pipe", "pipe"],
    });

    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => { stdout += String(chunk); });
    child.stderr.on("data", (chunk) => { stderr += String(chunk); });

    child.on("close", (code) => {
      if (code !== 0) {
        resolve({ ok: false, error: stderr.trim() || "Failed to add plays" });
      } else {
        resolve({ ok: true, team, playIndices, count: playIndices.length });
      }
    });

    child.on("error", (err) => {
      resolve({ ok: false, error: String(err?.message || err) });
    });
  });
});

ipcMain.handle("generator:import-to-game", async (_event, payload) => {
  const entries = Array.isArray(payload?.entries) ? payload.entries : [];
  if (!entries.length) return { ok: false, error: "No player entries to import." };

  const pythonPath = resolvePythonPath();
  const projectRoot = getProjectRoot();
  const importScriptPath = path.join(getProjectRoot(), "nba2k26_generator", "live_import.py");

  if (!fs.existsSync(pythonPath)) {
    return { ok: false, error: `Python not found at: ${pythonPath}` };
  }
  if (!fs.existsSync(importScriptPath)) {
    return { ok: false, error: `live_import.py not found at: ${importScriptPath}` };
  }

  // Write the payload to a temp file so we can stream it into the script
  const tempFile = path.join(os.tmpdir(), `nba2k26_import_${Date.now()}.json`);
  try {
    fs.writeFileSync(tempFile, JSON.stringify(payload), "utf-8");

    // Auto-detect offsets path (prefer bundled copy next to the script)
    const offsetCandidates = [
      path.join(getProjectRoot(), "nba2k26_generator", "2k26_offsets.json"),
      path.join(os.homedir(), "Downloads", "New folder", "2k26_offsets.json"),
      path.join(os.homedir(), "Downloads", "2k26_offsets.json"),
    ];
    const offsetPath = offsetCandidates.find((p) => fs.existsSync(p)) || null;

    const args = [importScriptPath, "--input", tempFile];
    if (offsetPath) args.push("--offsets", offsetPath);

    return await new Promise((resolve) => {
      const child = spawn(pythonPath, args, {
        cwd: projectRoot,
        env: { ...process.env, PYTHONIOENCODING: "utf-8", PYTHONPATH: projectRoot },
        windowsHide: true,
        stdio: ["ignore", "pipe", "pipe"],
      });

      let stdout = "";
      let stderr = "";
      child.stdout.on("data", (chunk) => { stdout += String(chunk); });
      child.stderr.on("data", (chunk) => { stderr += String(chunk); });

      child.on("error", (err) => {
        resolve({ ok: false, error: String(err?.message || err) });
      });

      child.on("close", (code) => {
        try {
          const parsed = JSON.parse(stdout.trim() || "{}");
          resolve(parsed);
        } catch {
          resolve({
            ok: false,
            error: stderr || `Import process exited with code ${code}`,
            stdout,
          });
        }
      });
    });
  } finally {
    try { fs.unlinkSync(tempFile); } catch { /* best-effort */ }
  }
});

function runStatsScript(pythonPath, projectRoot, endpoint, args) {
  return new Promise((resolve) => {
    const code = [
      "import sys, json, os",
      "sys.path.insert(0, os.path.join(sys.argv[1], 'nba2k26_generator'))",
      "from nba_stats_api import fetch_player_stats, fetch_team_stats, fetch_league_leaders",
      "try:",
      `    ep = sys.argv[2]`,
      "    season = sys.argv[3]; stype = sys.argv[4]; pmode = sys.argv[5]; mtype = sys.argv[6]",
      "    if ep == 'players': r = fetch_player_stats(season, stype, pmode, mtype)",
      "    elif ep == 'teams': r = fetch_team_stats(season, stype, pmode, mtype)",
      "    else: r = fetch_league_leaders(season, stype, pmode, mtype)",
      "    print(json.dumps(r))",
      "except Exception as e:",
      "    print(json.dumps({'ok': False, 'error': str(e)}))",
    ].join("\n");
    const allArgs = ["-c", code, projectRoot, endpoint, ...args];
    const child = spawn(pythonPath, allArgs, {
      windowsHide: true,
      env: { ...process.env, PYTHONIOENCODING: "utf-8" },
      stdio: ["ignore", "pipe", "pipe"],
    });
    let stdout = "", stderr = "";
    child.stdout.on("data", (d) => { stdout += d; });
    child.stderr.on("data", (d) => { stderr += d; });
    child.on("close", () => {
      try { resolve(JSON.parse(stdout.trim() || "{}")); }
      catch { resolve({ ok: false, error: stderr.slice(0, 400) || "Parse error" }); }
    });
    child.on("error", (err) => resolve({ ok: false, error: String(err.message) }));
  });
}

ipcMain.handle("stats:players", async (_event, p) => {
  const season = String(p?.season || "2024-25");
  const seasonType = String(p?.seasonType || "Regular Season");
  const perMode = String(p?.perMode || "PerGame");
  const measureType = String(p?.measureType || "Base");
  return runStatsScript(resolvePythonPath(), getProjectRoot(), "players", [season, seasonType, perMode, measureType]);
});

ipcMain.handle("stats:teams", async (_event, p) => {
  const season = String(p?.season || "2024-25");
  const seasonType = String(p?.seasonType || "Regular Season");
  const perMode = String(p?.perMode || "PerGame");
  const measureType = String(p?.measureType || "Base");
  return runStatsScript(resolvePythonPath(), getProjectRoot(), "teams", [season, seasonType, perMode, measureType]);
});

ipcMain.handle("stats:leaders", async (_event, p) => {
  const season = String(p?.season || "2024-25");
  const seasonType = String(p?.seasonType || "Regular Season");
  const perMode = String(p?.perMode || "PerGame");
  const category = String(p?.category || "PTS");
  return runStatsScript(resolvePythonPath(), getProjectRoot(), "leaders", [season, seasonType, category, perMode]);
});

function runStatsCall(pythonPath, projectRoot, params) {
  return new Promise((resolve) => {
    const code = [
      "import sys, json, os",
      "sys.path.insert(0, os.path.join(sys.argv[1], 'nba2k26_generator'))",
      "from nba_stats_api import fetch_tracking_stats, fetch_hustle_stats, fetch_player_bio, fetch_player_career, fetch_shot_chart",
      "try:",
      "    p = json.loads(sys.argv[2])",
      "    fn = p.pop('fn')",
      "    fns = {'tracking': fetch_tracking_stats, 'hustle': fetch_hustle_stats, 'player_bio': fetch_player_bio, 'player_career': fetch_player_career, 'shot_chart': fetch_shot_chart}",
      "    r = fns[fn](**p)",
      "    print(json.dumps(r))",
      "except Exception as e:",
      "    import traceback; print(json.dumps({'ok': False, 'error': str(e), 'trace': traceback.format_exc()[-400:]}))",
    ].join("\n");
    const payload = JSON.stringify(params);
    const child = spawn(pythonPath, ["-c", code, projectRoot, payload], {
      windowsHide: true,
      env: { ...process.env, PYTHONIOENCODING: "utf-8" },
      stdio: ["ignore", "pipe", "pipe"],
    });
    let stdout = "", stderr = "";
    child.stdout.on("data", (d) => { stdout += d; });
    child.stderr.on("data", (d) => { stderr += d; });
    child.on("close", () => {
      try { resolve(JSON.parse(stdout.trim() || "{}")); }
      catch { resolve({ ok: false, error: stderr.slice(0, 400) || "Parse error" }); }
    });
    child.on("error", (err) => resolve({ ok: false, error: String(err.message) }));
  });
}

ipcMain.handle("stats:tracking", async (_event, p) => {
  return runStatsCall(resolvePythonPath(), getProjectRoot(), {
    fn: "tracking",
    season: String(p?.season || "2024-25"),
    season_type: String(p?.seasonType || "Regular Season"),
    pt_measure_type: String(p?.ptMeasureType || "Drives"),
    per_mode: String(p?.perMode || "PerGame"),
  });
});

ipcMain.handle("stats:hustle", async (_event, p) => {
  return runStatsCall(resolvePythonPath(), getProjectRoot(), {
    fn: "hustle",
    season: String(p?.season || "2024-25"),
    season_type: String(p?.seasonType || "Regular Season"),
    per_mode: String(p?.perMode || "PerGame"),
  });
});

ipcMain.handle("stats:player-bio", async (_event, p) => {
  return runStatsCall(resolvePythonPath(), getProjectRoot(), {
    fn: "player_bio",
    player_id: Number(p?.playerId),
  });
});

ipcMain.handle("stats:player-career", async (_event, p) => {
  return runStatsCall(resolvePythonPath(), getProjectRoot(), {
    fn: "player_career",
    player_id: Number(p?.playerId),
  });
});

ipcMain.handle("stats:shot-chart", async (_event, p) => {
  return runStatsCall(resolvePythonPath(), getProjectRoot(), {
    fn: "shot_chart",
    player_id: Number(p?.playerId),
    season: String(p?.season || "2024-25"),
    season_type: String(p?.seasonType || "Regular Season"),
  });
});

ipcMain.handle("generator:sheet-lookup", async (_event, payload) => {
  const playerName = String(payload?.player || "").trim();
  if (!playerName) return { ok: false, error: "Player name required." };

  const projectRoot = getProjectRoot();
  const pythonPath = resolvePythonPath();

  if (!fs.existsSync(pythonPath)) {
    return { ok: false, error: "Python not found." };
  }

  const code = `
import json, sys, pandas as pd, os, unicodedata, re

def strip_accents(s):
    nfkd = unicodedata.normalize('NFKD', str(s))
    return ''.join(c for c in nfkd if not unicodedata.combining(c))

def normalize_name(s):
    return strip_accents(s).strip().upper()

def normalize_key(s):
    s = re.sub(r'[^a-z0-9]+', '_', str(s).strip().lower())
    return s.strip('_')

player_target = normalize_name(sys.argv[1])
project_root = sys.argv[2]

sheet_paths = [
    os.path.join(project_root, 'Player Roles', 'Attributes one.xlsx'),
    os.path.join(project_root, 'Player Roles', 'attributes two.xlsx'),
]

result = None
for sheet_path in sheet_paths:
    if not os.path.isfile(sheet_path):
        continue
    try:
        df = pd.read_excel(sheet_path, header=None)
    except Exception:
        continue
    # Header is row 4
    if len(df) <= 4:
        continue
    headers = [str(v).strip() for v in df.iloc[4].values]
    name_col = 1
    attr_cols = {normalize_key(h): i for i, h in enumerate(headers) if h and h != 'nan' and i > 1}
    for i in range(7, len(df)):
        row = df.iloc[i]
        name_val = str(row.iloc[name_col]).strip()
        if not name_val or name_val == 'nan':
            continue
        non_nan = sum(1 for v in row.values[2:] if str(v) != 'nan')
        if non_nan < 3:
            continue
        if normalize_name(name_val) == player_target:
            attrs = {}
            for key, col_idx in attr_cols.items():
                val = row.iloc[col_idx]
                if str(val) != 'nan':
                    try:
                        attrs[key] = int(float(val))
                    except Exception:
                        pass
            # Also store original header names for display
            display_attrs = {}
            for i2, h in enumerate(headers):
                if h and h != 'nan' and i2 > 1:
                    val = row.iloc[i2]
                    if str(val) != 'nan':
                        try:
                            display_attrs[h.strip()] = int(float(val))
                        except Exception:
                            pass
            result = {'ok': True, 'attributes': attrs, 'display': display_attrs, 'name': name_val}
            break
    if result:
        break

if result is None:
    print(json.dumps({'ok': False, 'error': f'Player not found in sheet: {sys.argv[1]}'}))
else:
    print(json.dumps(result))
`.trim();

  return new Promise((resolve) => {
    const child = spawn(pythonPath, ["-c", code, playerName, projectRoot], {
      windowsHide: true,
      stdio: ["ignore", "pipe", "pipe"],
    });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (d) => { stdout += d; });
    child.stderr.on("data", (d) => { stderr += d; });
    child.on("close", () => {
      try {
        resolve(JSON.parse(stdout.trim() || "{}"));
      } catch {
        resolve({ ok: false, error: stderr || "Failed to read sheet." });
      }
    });
    child.on("error", (err) => resolve({ ok: false, error: String(err?.message || err) }));
  });
});

  app.whenReady().then(() => {
    createWindow();
    _setupAutoUpdater();
  });

  app.on("window-all-closed", () => {
    if (process.platform !== "darwin") app.quit();
  });
}); // end _waitForElectron bootstrapElectronApp

function _setupAutoUpdater() {
  if (!app.isPackaged) return;
  try {
    ({ autoUpdater } = require("electron-updater"));
    autoUpdater.autoDownload = true;
    autoUpdater.autoInstallOnAppQuit = true;

    autoUpdater.on("update-available", (info) => {
      dialog.showMessageBox({
        type: "info",
        title: "Update Available",
        message: `Version ${info.version} is available and will download in the background.`,
        buttons: ["OK"],
      });
    });

    autoUpdater.on("update-downloaded", () => {
      dialog.showMessageBox({
        type: "info",
        title: "Update Ready",
        message: "A new version has been downloaded. Restart now to install it.",
        buttons: ["Restart Now", "Later"],
        defaultId: 0,
      }).then((result) => {
        if (result.response === 0) autoUpdater.quitAndInstall();
      });
    });

    autoUpdater.on("error", (err) => {
      process.stderr.write(`Auto-updater error: ${err?.message || err}\n`);
    });

    autoUpdater.checkForUpdates().catch(() => {});
  } catch (err) {
    process.stderr.write(`Auto-updater init failed: ${err?.message || err}\n`);
  }
}
