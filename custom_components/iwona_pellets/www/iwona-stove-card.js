/* Iwona Pellets stove card - built only from the entities the integration already
 * exposes (no extra register reads). Type: custom:iwona-stove-card
 * Entities are discovered automatically from the integration; override with
 *   entities: { room_temperature: sensor.xxx, ... }  (keys = translation keys). */
const TXT = {
  fr: { stop: "Arrêt", room: "Ambiance", target: "Consigne", boiler: "Habillage", exhaust: "Fumées",
        blow: "Soufflage Air Chaud", extract: "Extraction", start: "Marche/Arrêt",
        hours: "h de marche", ignitions: "allumages", fault: "Défaut", clear: "Effacer le défaut", askOn: "Voulez-vous mettre le poêle en marche ?", askOff: "Voulez-vous arrêter le poêle ?", yes: "OUI", no: "NON", prog: "Programme", fuel: "Combustible",
        none: "Poêle introuvable" },
  en: { stop: "Stopped", room: "Room", target: "Setpoint", boiler: "Boiler", exhaust: "Exhaust",
        blow: "Blower", extract: "Extractor", start: "Start/Stop",
        hours: "h running", ignitions: "ignitions", fault: "Fault", clear: "Clear fault", askOn: "Start the stove?", askOff: "Stop the stove?", yes: "YES", no: "NO", prog: "Program", fuel: "Fuel",
        none: "Stove not found" },
};
const ERRS = { fr: { boiler_sensor: "Sonde chaudière", feeder_sensor: "Sonde vis", exhaust_sensor: "Sonde fumées", stb_protection: "Protection STB",
  safety_input: "Entrée de sécurité", capacitive_unjamming: "Débourrage en cours", capacitive_critical: "Capteur capacitif (critique)", boiler_overheat: "Surchauffe chaudière",
  feeder_ignition: "Allumage vis", feeder_ignition_detected: "Allumage vis détecté", no_pellets: "Plus de pellets", no_wood: "Plus de bois", flame_vanished: "Flamme éteinte",
  buffer_sensor: "Sonde ballon", buffer_overheat: "Surchauffe ballon", fan_jammed: "Ventilateur bloqué", too_much_wood: "Trop de bois" } };
const LABELS = { fr: { pellet: "Pellet", wood: "Bois", wood_pellet: "Bois/Pellet", day: "Jour", night: "Nuit", off: "Off", prg1: "Prog 1", prg2: "Prog 2", prg3: "Prog 3" } };

class IwonaStoveCard extends HTMLElement {
  setConfig(config) { this._config = config || {}; if (this._root) this._render(); }
  getCardSize() { return 6; }
  static getStubConfig() { return {}; }

  set hass(hass) {
    this._hass = hass;
    if (!this._root) {
      this._root = this.attachShadow({ mode: "open" });
      this._build();
    }
    this._render();
  }

  _t(k) { const l = (this._hass.language || "en").slice(0, 2); return (TXT[l] || TXT.en)[k]; }

  _map() {
    const cfg = this._config.entities || {};
    const found = {};
    const reg = this._hass.entities || {};
    for (const [id, e] of Object.entries(reg)) {
      if (e.platform === "iwona_pellets" && e.translation_key) {
        const dom = id.split(".")[0];
        found[`${dom}:${e.translation_key}`] = id;
      }
    }
    return (dom, key) => cfg[key] || found[`${dom}:${key}`];
  }

  _st(id) { return id ? this._hass.states[id] : undefined; }
  _num(id) { const s = this._st(id); const v = s ? parseFloat(s.state) : NaN; return isNaN(v) ? null : v; }
  _call(domain, service, id, data = {}) { if (id) this._hass.callService(domain, service, { entity_id: id, ...data }); }

  _build() {
    this._root.innerHTML = `
<style>
:host { display:block; }
ha-card { background:#222; color:#f4efe9; border-radius: 24px; padding:18px; overflow:hidden; --accent:#ff7a3c; font-family: var(--paper-font-body1_-_font-family, system-ui, sans-serif); }
.state { font-size:2.9cqw; line-height:1.15; font-weight:600; letter-spacing:.02em; display:flex; align-items:center; gap:8px; }
.dot { width:10px; height:10px; border-radius:50%; background:#777; box-shadow:0 0 0 0 transparent; }
.on .dot { background: var(--accent); animation: pulse 2s infinite; }
.badge { font-size:2.4cqw; padding:3px 10px; border-radius:99px; background:#d33; display:none; }
.fault .badge { display:block; }
.photo { position:relative; margin:-18px; aspect-ratio: 1320 / 2573; overflow:hidden; container-type:inline-size;
  background: var(--img) center / 100% 100% no-repeat; color:#2b2926; }
.abs { position:absolute; left:10%; right:10%; }
.top { top:22.6%; display:flex; justify-content:space-between; align-items:center; }
.state { font-size:3.4cqw; font-weight:600; display:flex; align-items:center; gap:1.5cqw; }
.dot { width:2.4cqw; height:2.4cqw; border-radius:50%; background:#777; }
.on .dot { background: var(--accent); animation: pulse 2s infinite; }
.info { top:27%; display:flex; justify-content:space-between; align-items:flex-start; }
.col { display:flex; flex-direction:column; gap:2.6cqw; width:27cqw; }
.col.r { align-items:flex-end; text-align:right; }
.metric .v { font-size:5.6cqw; font-weight:300; line-height:1; }
.metric .l { font-size:2.2cqw; opacity:.7; text-transform:uppercase; letter-spacing:.06em; margin-top:.6cqw; }
.mid { text-align:center; }
.mid .big { font-size:11cqw; font-weight:200; line-height:1; }
.fan { display:flex; align-items:center; gap:1.6cqw; }
.col.r .fan { flex-direction:row-reverse; }
.fan .metric .l { max-width:20cqw; line-height:1.1; }
.fan svg { width:5.5cqw; height:5.5cqw; fill:none; stroke:#2b2926; stroke-width:1.6; opacity:.4; flex:none; }
.fan.spin svg { opacity:.9; animation: spin var(--dur,1s) linear infinite; }
.rowc { display:flex; gap:1.4cqw; justify-content:center; flex-wrap:nowrap; }
.sels { top:2.6%; left:auto; right:3.5%; display:flex; flex-direction:column; align-items:stretch; gap:1.4cqw; width:24cqw; }
.sels label { display:flex; flex-direction:column; gap:.4cqw; font-size:1.9cqw; text-transform:uppercase; letter-spacing:.06em; color:#fff; text-shadow:0 1px 3px rgba(0,0,0,.75); }
.sels select { appearance:none; -webkit-appearance:none; font:inherit; font-size:2.7cqw; text-transform:none; letter-spacing:0; text-shadow:none; padding:.9cqw 5cqw .9cqw 2.4cqw;
  border-radius:99px; border:1px solid rgba(40,35,30,.35); color:#2b2926; cursor:pointer; width:100%;
  background: rgba(255,255,255,.55) url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8'%3E%3Cpath d='M1 1l5 5 5-5' fill='none' stroke='%232b2926' stroke-width='2'/%3E%3C/svg%3E") no-repeat right 2.2cqw center; }
.alert { position:absolute; bottom:2.2%; left:5%; right:5%; display:flex; align-items:center; justify-content:space-between; gap:2cqw;
  padding:1.6cqw 2.4cqw 1.6cqw 3.4cqw; border-radius:99px; background:rgba(190,30,30,.94); color:#fff; font-size:3cqw; font-weight:600;
  box-shadow:0 2px 10px rgba(0,0,0,.45); animation: alertin .3s ease-out; }
.alert .msg { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.alert button { flex:none; font:inherit; font-size:2.6cqw; font-weight:600; padding:1cqw 3cqw; border-radius:99px; border:0; background:#fff; color:#a01818; cursor:pointer; }
.confirm { position:absolute; inset:0; z-index:5; display:flex; align-items:center; justify-content:center; background:rgba(0,0,0,.55); }
.dlg { width:70%; padding:5cqw 4cqw; border-radius:4cqw; background:#f4efe9; color:#2b2926; text-align:center; font-size:3.6cqw; font-weight:600; box-shadow:0 6px 24px rgba(0,0,0,.5); }
.dlg .row { display:flex; gap:3cqw; justify-content:center; margin-top:4cqw; }
.dlg button { font:inherit; font-size:3.2cqw; padding:1.8cqw 6cqw; border-radius:99px; border:1px solid rgba(40,35,30,.35); background:#fff; color:#2b2926; cursor:pointer; }
.dlg button.yes { background:var(--accent); border-color:var(--accent); color:#1a0d05; }
.heater { position:absolute; left:41%; width:18%; top:75.6%; height:1.7%; opacity:.35; }
.heater svg { width:100%; height:100%; overflow:visible; }
.heater path { fill:none; stroke:#6b645c; stroke-width:2.2; stroke-linecap:round; stroke-linejoin:round; vector-effect:non-scaling-stroke; }
.heater.on { opacity:1; }
.heater.on path { stroke:#ff5a1c; filter: drop-shadow(0 0 3px #ff4a10) drop-shadow(0 0 8px rgba(255,90,20,.9)); animation: hot 1.6s ease-in-out infinite alternate; }
.chip { white-space:nowrap; padding:1.1cqw 2.4cqw; border-radius:99px; border:1px solid rgba(40,35,30,.35); background:rgba(255,255,255,.5);
  color:#2b2926; font-size:2.5cqw; cursor:pointer; backdrop-filter: blur(4px); }
.chip.sel { background: var(--accent); border-color: var(--accent); color:#1a0d05; font-weight:600; }
.chip.big { padding:2cqw 4.4cqw; font-size:3.1cqw; background: rgba(25,22,20,.72); color:#f4efe9; border-color: rgba(255,255,255,.25); }
.chip.big.sel { background:#f1ebe2; color:#1a1a18; }
.target .pm { background:rgba(255,255,255,.22); border-color:rgba(255,255,255,.45); color:#fff; width:8.2cqw; height:8.2cqw; font-size:4.8cqw; }
.target { left:50%; right:auto; transform:translateX(-50%); padding:.8cqw 2cqw; border-radius:99px; background:rgba(18,15,13,.86); color:#fff; white-space:nowrap; box-shadow:0 2px 10px rgba(0,0,0,.4); }
.pm { width:6.5cqw; height:6.5cqw; border-radius:50%; border:1px solid rgba(40,35,30,.4); background:rgba(255,255,255,.55);
  color:inherit; font-size:3.6cqw; cursor:pointer; padding:0; }
.target { top:14.6%; display:flex; justify-content:center; align-items:center; gap:2.4cqw; font-size:3.9cqw; font-weight:600; }
.pwr { position:absolute; left:8%; top:4.9%; width:12cqw; height:12cqw; border-radius:50%; padding:0; display:flex; align-items:center; justify-content:center; cursor:pointer;
  background:rgba(25,22,20,.78); color:#f4efe9; border:1px solid rgba(255,255,255,.3); box-shadow:0 2px 8px rgba(0,0,0,.4); }
.pwr svg { width:6.4cqw; height:6.4cqw; fill:none; stroke:currentColor; stroke-width:2.4; stroke-linecap:round; }
.pwr.sel { background:#f1ebe2; color:#d2410a; }
.fire { position:absolute; left:25.8%; top:57.9%; width:50.2%; height:17.2%; container-type:size; overflow:hidden;
  background: linear-gradient(#26211e,#0f0c0a); border-radius:1.2cqw; box-shadow: inset 0 0 6cqw rgba(0,0,0,.8); }
.glow { position:absolute; inset:0; background: radial-gradient(ellipse at 50% 100%, rgba(255,140,50,.9), transparent 70%);
  opacity: calc(var(--k,0) * .95); transition: opacity 1.2s; }
.flames { position:absolute; inset:0; opacity: min(1, calc(var(--k,0) * 12)); transition: opacity 1s; }
.flame { position:absolute; bottom:11cqh; transform-origin: 50% 100%; height: calc((22 + 60 * var(--k,0)) * 1cqh * var(--s,1));
  aspect-ratio: 46 / 100; transition: height 1.2s, opacity 1.2s; filter: blur(.6px); animation: flick var(--t,1s) ease-in-out var(--d,0s) infinite alternate; }
.flame svg { width:100%; height:100%; display:block; }
.grate { position:absolute; left:3%; right:3%; bottom:5cqh; height:7cqh; border-radius:3px; background:repeating-linear-gradient(90deg,#aaa 0 3cqw,#555 3cqw 4.5cqw); opacity:.9; }
.embers { position:absolute; left:6%; right:6%; bottom:11cqh; height:6cqh; border-radius:50%; background: radial-gradient(#ff7a2a, transparent 70%); opacity: var(--k,0); }
.missing { padding:20px; text-align:center; opacity:.8; }
@keyframes alertin { from { transform:translateY(100%); opacity:0; } to { transform:none; opacity:1; } }
@keyframes hot { from { opacity:.75; } to { opacity:1; } }
@keyframes spin { to { transform: rotate(360deg); } }
@keyframes pulse { 0% { box-shadow:0 0 0 0 rgba(255,122,60,.7);} 70% { box-shadow:0 0 0 9px rgba(255,122,60,0);} 100% { box-shadow:0 0 0 0 rgba(255,122,60,0);} }
@keyframes flick { from { transform: scale(1,.9) skewX(-4deg);} to { transform: scale(.92,1.06) skewX(4deg);} }
@media (prefers-reduced-motion: reduce) { .flame, .fan.spin svg, .on .dot, .alert, .heater.on path { animation:none; } }
</style>
<ha-card><div id="c"></div></ha-card>`;
    this._c = this._root.getElementById("c");
    this._c.addEventListener("change", (ev) => {
      const el = ev.target.closest("select[data-id]"); if (el) this._call("select", "select_option", el.dataset.id, { option: el.value });
    });
    this._c.addEventListener("click", (ev) => {
      const el = ev.target.closest("[data-a]"); if (!el) return;
      const a = el.dataset.a, id = el.dataset.id;
      if (a === "toggle") { this._confirm = id; this._render(); }
      else if (a === "no") { this._confirm = null; this._render(); }
      else if (a === "yes") { const on = this._st(id)?.state === "on"; this._confirm = null; this._call("switch", on ? "turn_off" : "turn_on", id); this._render(); }
      else if (a === "clear") this._call("button", "press", id);
      else if (a === "step") {
        const v = parseFloat(el.dataset.v);
        this._call("number", "set_value", id, { value: Math.round(v * 10) / 10 });
      }
    });
  }

  _render() {
    const h = this._hass, m = this._map();
    const id = {
      proc: m("sensor", "process_state"), room: m("sensor", "room_temperature"),
      boiler: m("sensor", "boiler_temperature"), exh: m("sensor", "exhaust_temperature"),
      fanE: m("sensor", "exhaust_fan_power"), fanB: m("sensor", "blow_in_fan_power"),
      hours: m("sensor", "burner_hours"), ign: m("sensor", "ignition_count"),
      flame: m("binary_sensor", "flame"), prob: m("binary_sensor", "problem"),
      feeder: m("binary_sensor", "feeder"), igniter: m("binary_sensor", "ignition"),
      pump: m("binary_sensor", "heating_pump"),
      sw: m("switch", "stove"), clear: m("button", "clear_errors"),
      tRoom: m("number", "target_room_temperature_day"), tBoiler: m("number", "target_boiler_temperature"),
      prog: m("select", "program_mode"), fuel: m("select", "fuel_mode"),
    };
    const proc = this._st(id.proc);
    if (!proc) { this._html = null; this._c.innerHTML = `<div class="missing">${this._t("none")}</div>`; return; }
    const fmt = (s) => (h.formatEntityState ? h.formatEntityState(s) : s.state);
    const code = parseInt(proc.attributes.code ?? -1, 10);
    // flame height follows the exhaust temperature, 20 C (cold) -> 300 C (full)
    const exhT = this._num(id.exh);
    const k = exhT == null ? 0 : Math.min(1, Math.max(0, (exhT - 20) / 280));
    const running = k > 0 || (this._st(id.sw)?.state === "on");
    const fault = this._st(id.prob)?.state === "on";
    const room = this._num(id.room), boiler = this._num(id.boiler), exh = this._num(id.exh);
    const pelletOnly = this._st(id.fuel)?.state === "pellet";
    const fe = this._num(id.fanE) || 0, fb = this._num(id.fanB) || 0;
    const tR = this._num(id.tRoom);
    const fx = (v, d = 0) => (v == null ? "–" : v.toFixed(d));
    const fanIcon = `<svg viewBox="0 0 32 32"><circle cx="16" cy="16" r="2.5"/><path d="M16 13.5C16 6 21 4 22 8s-3 6-6 5.5M18.5 16c7.5 0 9.500 5 5.500 6s-6-3-5.500-6M16 18.5C16 26 11 28 10 24s3-6 6-5.500M13.500 16C6 16 4 11 8 10s6 3 5.500 6"/></svg>`;
    const dur = (p) => (p > 0 ? Math.max(.25, 2.2 - p * .019) : 0);
    const sel = (eid, lab) => {
      const s = this._st(eid); if (!s) return "";
      const lang = (h.language || "en").slice(0, 2);
      const opts = (s.attributes.options || []).map((o) => {
        const t = (LABELS[lang] || {})[o] || (h.formatEntityState ? h.formatEntityState({ ...s, state: o }) : o);
        return `<option value="${o}" ${o === s.state ? "selected" : ""}>${t}</option>`;
      }).join("");
      return `<label>${lab}<select data-id="${eid}">${opts}</select></label>`;
    };
    // state label without the fuel in brackets: "Allumage (bois)" -> "Allumage"
    const stateText = fmt(proc).replace(/\s*\([^)]*\)/g, "");
    const errs = (this._st(id.prob)?.attributes.errors || []).filter((e) => e !== "power_loss");
    const errLang = ERRS[(h.language || "en").slice(0, 2)] || {};
    const faultText = errs.map((e) => errLang[e] || e.replace(/_/g, " ")).join(", ") || this._t("fault");
    // [left %, size, flicker s, delay s, appears above k]
    const defs = pelletOnly ? [[50, 1.25, 1.2, 0, 0]] :
      [[50, 1.15, 1.25, 0, 0], [36, .9, 1.1, -.5, .25], [64, .9, 1.0, -.7, .25], [22, .7, .9, -.2, .5], [78, .7, .85, -.3, .5]];
    const flames = defs.map(([x, sz, t, d, th]) => {
      const o = Math.min(1, Math.max(0, (k - th) / .2));
      return `<div class="flame" style="left:${x}%;margin-left:-4.6cqw;--s:${sz};--t:${t}s;--d:${d}s;opacity:${o}"><svg viewBox="0 0 46 100" preserveAspectRatio="none"><path d="M23 0C36 28 46 48 40 80C36 100 10 100 6 80C0 48 14 28 23 0Z" fill="url(#fg)"/></svg></div>`;
    }).join("");
    const sw = this._st(id.sw);
    if (this._confirm && !this._st(this._confirm)) this._confirm = null;
    this._c.parentElement.className = `${running ? "on" : ""} ${fault ? "fault" : ""}`;
    const html = `
<div class="photo" style="--img:url('${this._config.image || "/iwona_pellets/stove.jpg"}')">
  <div class="fire" style="--k:${k}"><div class="glow"></div>
    <svg width="0" height="0" style="position:absolute"><defs><linearGradient id="fg" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#ff5a14"/><stop offset=".55" stop-color="#ffb347"/><stop offset="1" stop-color="#fff1b8"/></linearGradient></defs></svg>
    <div class="embers"></div><div class="flames">${flames}</div><div class="grate"></div></div>
  <div class="abs top"><div class="state"><span class="dot"></span>${stateText}</div></div>
  <div class="abs info">
    <div class="col">
      <div class="metric"><div class="v">${fx(boiler)}°</div><div class="l">${this._t("boiler")}</div></div>
      <div class="metric"><div class="v">${fx(exh)}°</div><div class="l">${this._t("exhaust")}</div></div>
    </div>
    <div class="mid"><div class="big">${fx(room, 1)}°</div><div class="metric"><div class="l">${this._t("room")}</div></div></div>
    <div class="col r">
      <div class="fan ${fb > 0 ? "spin" : ""}" style="--dur:${dur(fb)}s">${fanIcon}<div class="metric"><div class="v">${fx(fb)}%</div><div class="l">${this._t("blow")}</div></div></div>
      <div class="fan ${fe > 0 ? "spin" : ""}" style="--dur:${dur(fe)}s">${fanIcon}<div class="metric"><div class="v">${fx(fe)}%</div><div class="l">${this._t("extract")}</div></div></div>
    </div>
  </div>
  <div class="abs sels">${sel(id.prog, this._t("prog"))}${sel(id.fuel, this._t("fuel"))}</div>
  <div class="abs target">${tR == null ? "" : `<button class="pm" data-a="step" data-id="${id.tRoom}" data-v="${tR - 0.5}">−</button>
    <span>${this._t("target")} ${fx(tR, 1)}°</span><button class="pm" data-a="step" data-id="${id.tRoom}" data-v="${tR + 0.5}">+</button>`}</div>
  ${sw ? `<button class="pwr ${sw.state === "on" ? "sel" : ""}" data-a="toggle" data-id="${id.sw}" title="${this._t("start")}" aria-label="${this._t("start")}"><svg viewBox="0 0 24 24"><path d="M12 3v9M6.3 6.5a8 8 0 1 0 11.4 0"/></svg></button>` : ""}
  ${this._st(id.igniter) ? `<div class="heater ${this._st(id.igniter).state === "on" ? "on" : ""}"><svg viewBox="0 0 100 10" preserveAspectRatio="none"><path d="M0 5H8L12 0L20 10L28 0L36 10L44 0L52 10L60 0L68 10L76 0L84 10L88 5H100"/></svg></div>` : ""}
  ${this._confirm ? `<div class="confirm"><div class="dlg">${this._t(this._st(this._confirm).state === "on" ? "askOff" : "askOn")}<div class="row"><button data-a="no">${this._t("no")}</button><button class="yes" data-a="yes" data-id="${this._confirm}">${this._t("yes")}</button></div></div></div>` : ""}
  ${fault ? `<div class="alert"><span class="msg">⚠ ${faultText}</span>${this._st(id.clear) ? `<button data-a="clear" data-id="${id.clear}">${this._t("clear")}</button>` : ""}</div>` : ""}
</div>
`;
    if (html !== this._html) { this._html = html; this._c.innerHTML = html; }
  }
}
customElements.define("iwona-stove-card", IwonaStoveCard);
window.customCards = window.customCards || [];
window.customCards.push({ type: "iwona-stove-card", name: "Iwona Pellets", description: "Animated stove card" });
