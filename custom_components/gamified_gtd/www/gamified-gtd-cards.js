import { LitElement, html, css } from "lit";

/* Gamified GTD — Pip-Boy style custom cards.
 *
 * Icons: original Fallout: New Vegas icons are copyrighted and NOT shipped.
 * Drop your own files into custom_components/gamified_gtd/www/gamified_gtd_icons/
 *   <kind>/<id>.png   e.g. special/strength.png, skill/guns.png, perk/swift_learner.png
 * The card loads them automatically and falls back to text glyphs otherwise.
 */

const DOMAIN = "gamified_gtd";
const STATIC = `/${DOMAIN}_static`;
const ICONS = `${STATIC}/gamified_gtd_icons`;

const SPECIAL = [
  { id: "strength", fb: "S" },
  { id: "perception", fb: "P" },
  { id: "endurance", fb: "E" },
  { id: "charisma", fb: "C" },
  { id: "intelligence", fb: "I" },
  { id: "agility", fb: "A" },
  { id: "luck", fb: "L" },
];

const SKILLS = [
  { id: "barter", fb: "Ba" }, { id: "energy_weapons", fb: "EW" },
  { id: "explosives", fb: "Ex" }, { id: "guns", fb: "Gu" },
  { id: "lockpick", fb: "Lo" }, { id: "medicine", fb: "Me" },
  { id: "melee_weapons", fb: "MW" }, { id: "repair", fb: "Re" },
  { id: "science", fb: "Sc" }, { id: "sneak", fb: "Sn" },
  { id: "speech", fb: "Sp" }, { id: "survival", fb: "Su" },
  { id: "unarmed", fb: "Un" },
];

const LISTS = {
  inbox: { entity: "todo.gtd_inbox", label: "INBOX" },
  next_actions: { entity: "todo.gtd_next_actions", label: "NEXT ACTIONS" },
  waiting_for: { entity: "todo.gtd_waiting_for", label: "WAITING FOR" },
  someday_maybe: { entity: "todo.gtd_someday_maybe", label: "SOMEDAY/MAYBE" },
};

function personName(person) {
  return (person || "").replace(/^person\./, "").replace(/\./g, "_");
}
function sensorId(person, suffix) {
  return `sensor.${personName(person)}_${suffix}`;
}
function mePerson(hass) {
  const uid = hass && hass.user && hass.user.id;
  if (!uid) return null;
  const p = Object.values(hass.states).find(
    (s) => s.entity_id.startsWith("person.") && s.attributes && s.attributes.user_id === uid
  );
  return p ? p.entity_id : null;
}

function icon(kind, id, fallback) {
  const src = `${ICONS}/${kind}/${id}.png`;
  return html`<span class="gicon"
    ><span class="gicon-fb">${fallback}</span
    ><img
      src="${src}"
      alt=""
      @error=${(e) => e.target.remove()}
      @load=${(e) => {
        const fb = e.target.previousElementSibling;
        if (fb) fb.remove();
      }}
  /></span>`;
}

const pipCss = css`
  :host {
    --pip: #4aff4a;
    --pip-dim: #2a9e2e;
    --pip-dark: #0a1f0a;
  }
  ha-card {
    background: linear-gradient(180deg, #0c240c 0%, #071707 100%);
    color: var(--pip);
    font-family: "Courier New", ui-monospace, monospace;
    border: 1px solid var(--pip-dim);
    box-shadow: inset 0 0 24px rgba(74, 255, 74, 0.12);
    padding: 12px 14px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }
  .head {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    border-bottom: 1px solid var(--pip-dim);
    padding-bottom: 6px;
    margin-bottom: 8px;
  }
  .head .title { font-weight: bold; font-size: 1.05em; }
  .head .sub { color: var(--pip-dim); font-size: 0.8em; }
  .row { display: flex; align-items: center; gap: 8px; padding: 2px 0; }
  .lbl { width: 90px; color: var(--pip-dim); font-size: 0.85em; }
  .val { font-weight: bold; }
  .bar {
    flex: 1; height: 12px; border: 1px solid var(--pip-dim);
    background: var(--pip-dark); position: relative;
  }
  .bar > div { height: 100%; background: var(--pip); opacity: 0.85; }
  .bar > span {
    position: absolute; inset: 0; text-align: center;
    font-size: 0.7em; line-height: 12px; color: #04140a; font-weight: bold;
  }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 4px 10px; margin-top: 6px; }
  .cell { display: flex; align-items: center; gap: 6px; font-size: 0.85em; }
  .gicon { position: relative; display: inline-flex; width: 22px; height: 22px; align-items: center; justify-content: center; }
  .gicon img { position: absolute; inset: 0; width: 22px; height: 22px; object-fit: contain; filter: sepia(1) hue-rotate(70deg) saturate(4); }
  .gicon-fb { font-size: 0.75em; font-weight: bold; border: 1px solid var(--pip-dim); padding: 1px 3px; }
  button, .btn {
    font-family: inherit; text-transform: uppercase; letter-spacing: 0.04em;
    background: transparent; color: var(--pip); border: 1px solid var(--pip-dim);
    padding: 4px 10px; cursor: pointer; font-size: 0.85em;
  }
  button:hover:not(:disabled), .btn:hover { background: var(--pip); color: #04140a; }
  button:disabled { opacity: 0.35; cursor: default; }
  .btns { display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap; }
  .task { display: flex; align-items: center; gap: 8px; padding: 4px 0; border-bottom: 1px dashed rgba(74,255,74,0.2); }
  .task .t-title { flex: 1; }
  .task.done .t-title { text-decoration: line-through; opacity: 0.6; }
  .badge { border: 1px solid var(--pip-dim); padding: 0 5px; font-size: 0.72em; color: var(--pip-dim); }
  .checklist { margin: 6px 0; }
  .checklist .cl-ok { color: var(--pip); }
  .checklist .cl-no { color: #ff5f56; }
  .quest { border: 1px solid var(--pip-dim); padding: 6px 8px; margin-bottom: 6px; }
  .quest .q-name { font-weight: bold; }
  .quest .q-outcome { color: var(--pip-dim); font-size: 0.8em; text-transform: none; }
  ha-dialog { --mdc-dialog-min-width: 420px; }
  ha-dialog .dlg { color: var(--pip); font-family: "Courier New", ui-monospace, monospace; text-transform: uppercase; }
  ha-dialog label { display: block; margin: 8px 0 2px; color: var(--pip-dim); font-size: 0.8em; }
  ha-dialog input, ha-dialog select {
    width: 100%; background: var(--pip-dark); color: var(--pip);
    border: 1px solid var(--pip-dim); padding: 6px; font-family: inherit;
  }
  .seg { display: flex; flex-wrap: wrap; gap: 4px; margin: 6px 0; }
  .seg button.on { background: var(--pip); color: #04140a; }
  .empty { color: var(--pip-dim); font-style: italic; text-transform: none; }
`;

function svc(hass, service, data) {
  return hass.callService(DOMAIN, service, data);
}

/* ------------------------------------------------------------------ */
/* Stats card                                                          */
/* ------------------------------------------------------------------ */

class GamifiedGTDStatsCard extends LitElement {
  static get properties() {
    return { hass: {}, config: {}, _dlg: {} };
  }
  static getStubConfig() {
    return { person: "person.example", title: "PIP-BOY" };
  }
  setConfig(config) {
    if (!config.person) throw new Error("person is required");
    this.config = config;
  }
  getCardSize() {
    return 6;
  }
  _s(suffix) {
    return this.hass.states[sensorId(this.config.person, suffix)];
  }
  render() {
    const level = this._s("level");
    if (!level) return html`<ha-card><div class="empty">sensor not found for ${this.config.person}</div></ha-card>`;
    const a = level.attributes;
    const special = this._s("special");
    const skills = this._s("skills");
    const karma = this._s("karma");
    const caps = this._s("caps");
    const hp = this._s("hp");
    const perks = this._s("perks");
    const xpPct = Math.min(100, Math.round((100 * (a.xp_in_level || 0)) / (a.xp_level_span || 1)));
    return html`
      <ha-card>
        <div class="head">
          <span class="title">${this.config.title || "PIP-BOY 3000"}</span>
          <span class="sub">${this.config.person}</span>
        </div>
        <div class="row"><span class="lbl">LEVEL</span><span class="val">${level.state}</span>
          <div class="bar"><div style="width:${xpPct}%"></div><span>XP ${a.xp} / -${a.xp_to_next}</span></div>
        </div>
        <div class="row"><span class="lbl">HP</span><span class="val">${hp ? hp.state : "?"}</span>
          <span class="lbl" style="width:auto">KARMA</span><span class="val">${karma ? karma.state : "?"} (${karma ? karma.attributes.karma : 0})</span>
          <span class="lbl" style="width:auto">CAPS</span><span class="val">${caps ? caps.state : 0}</span>
        </div>
        <div class="grid">
          ${SPECIAL.map((s) => html`
            <div class="cell">${icon("special", s.id, s.fb)}<span class="lbl" style="width:auto">${s.id}</span>
              <span class="val">${special ? special.attributes[s.id] : "?"}</span></div>`)}
        </div>
        <div class="grid" style="grid-template-columns:repeat(auto-fill,minmax(150px,1fr))">
          ${SKILLS.map((s) => html`
            <div class="cell">${icon("skill", s.id, s.fb)}<span class="lbl" style="width:auto">${s.id.replace(/_/g, " ")}</span>
              <span class="val">${skills ? skills.attributes[s.id] : "?"}</span></div>`)}
        </div>
        <div class="row" style="margin-top:8px"><span class="lbl">PERKS</span>
          <span>${(perks && perks.attributes.perk_names) ? Object.values(perks.attributes.perk_names).join(", ") || "—" : "—"}</span>
        </div>
        <div class="btns">
          <button ?disabled=${!(a.skill_points_available > 0)} @click=${() => (this._dlg = "skills")}>Skill points (${a.skill_points_available})</button>
          <button ?disabled=${!a.perk_choice_pending} @click=${() => (this._dlg = "perk")}>Choose perk</button>
        </div>
        ${this._renderSkillDialog(a)}
        ${this._renderPerkDialog(a)}
      </ha-card>`;
  }
  _renderSkillDialog(a) {
    if (this._dlg !== "skills") return "";
    return html`<ha-dialog .open=${true} @closed=${() => (this._dlg = null)} .heading="ALLOCATE SKILL POINTS">
      <div class="dlg">
        <label>Skill</label>
        <select id="dlg-skill">${SKILLS.map((s) => html`<option value="${s.id}">${s.id.replace(/_/g, " ")}</option>`)}</select>
        <label>Points (available: ${a.skill_points_available})</label>
        <input id="dlg-points" type="number" min="1" max="${a.skill_points_available}" value="1" />
        <div class="btns">
          <button @click=${async () => {
            await svc(this.hass, "allocate_skill_points", {
              person: this.config.person,
              skill: this.shadowRoot.querySelector("#dlg-skill").value,
              points: Number(this.shadowRoot.querySelector("#dlg-points").value),
            });
            this._dlg = null;
          }}>Allocate</button>
          <button @click=${() => (this._dlg = null)}>Cancel</button>
        </div>
      </div>
    </ha-dialog>`;
  }
  _renderPerkDialog(a) {
    if (this._dlg !== "perk") return "";
    const perks = a.available_perks || [];
    return html`<ha-dialog .open=${true} @closed=${() => (this._dlg = null)} .heading="CHOOSE PERK">
      <div class="dlg">
        ${perks.length === 0 ? html`<div class="empty">No perks available at this level.</div>` : ""}
        ${perks.map((p) => html`
          <div class="quest">
            <div class="q-name">${icon("perk", p.id, p.name[0])}${p.name}</div>
            <div class="q-outcome">${p.description}</div>
            <div class="btns">
              ${p.id === "intense_training" ? html`<select id="dlg-stat-${p.id}">${SPECIAL.map((s) => html`<option value="${s.id}">${s.id}</option>`)}</select>` : ""}
              ${p.id === "tag" ? html`<select id="dlg-skill-${p.id}">${SKILLS.map((s) => html`<option value="${s.id}">${s.id}</option>`)}</select>` : ""}
              <button @click=${async () => {
                const data = { person: this.config.person, perk: p.id };
                const stat = this.shadowRoot.querySelector(`#dlg-stat-${p.id}`);
                const skill = this.shadowRoot.querySelector(`#dlg-skill-${p.id}`);
                if (stat) data.special_stat = stat.value;
                if (skill) data.skill = skill.value;
                await svc(this.hass, "choose_perk", data);
                this._dlg = null;
              }}>Choose</button>
            </div>
          </div>`)}
        <div class="btns"><button @click=${() => (this._dlg = null)}>Cancel</button></div>
      </div>
    </ha-dialog>`;
  }
  static get styles() {
    return pipCss;
  }
}
customElements.define("gamified-gtd-stats", GamifiedGTDStatsCard);

/* ------------------------------------------------------------------ */
/* Quests card                                                         */
/* ------------------------------------------------------------------ */

class GamifiedGTDQuestsCard extends LitElement {
  static get properties() {
    return { hass: {}, config: {}, _dlg: {} };
  }
  static getStubConfig() {
    return { title: "QUEST LOG" };
  }
  setConfig(config) {
    this.config = config;
  }
  getCardSize() {
    return 4;
  }
  render() {
    const log = this.hass.states["sensor.gtd_quest_log"];
    const quests = log ? Object.entries(log.attributes.quests || {}) : [];
    const active = quests.filter(([, q]) => q.status === "active");
    const done = quests.filter(([, q]) => q.status !== "active");
    return html`
      <ha-card>
        <div class="head"><span class="title">${this.config.title || "QUEST LOG"}</span>
          <span class="sub">${active.length} active</span></div>
        ${active.length === 0 ? html`<div class="empty">No active quests.</div>` : ""}
        ${active.map(([id, q]) => {
          const [d, t] = (q.progress || "0/0").split("/").map(Number);
          const pct = t > 0 ? Math.round((100 * d) / t) : 0;
          return html`<div class="quest">
            <div class="q-name">${icon("quest", id, "?")}${q.name}</div>
            <div class="q-outcome">${q.desired_outcome || ""}</div>
            <div class="row"><div class="bar"><div style="width:${pct}%"></div><span>${q.progress}</span></div>
              ${q.due ? html`<span class="badge">due ${q.due}</span>` : ""}
              <button @click=${() => svc(this.hass, "complete_project", { project_id: id })}>Complete</button>
            </div>
          </div>`;
        })}
        ${done.length ? html`<div class="head" style="margin-top:8px"><span class="sub">COMPLETED</span></div>
          ${done.map(([, q]) => html`<div class="row"><span class="badge">✓</span><span>${q.name}</span><span class="badge">${q.progress}</span></div>`)}` : ""}
        <div class="btns"><button @click=${() => (this._dlg = "new")}>New quest</button></div>
        ${this._renderNewDialog()}
      </ha-card>`;
  }
  _renderNewDialog() {
    if (this._dlg !== "new") return "";
    return html`<ha-dialog .open=${true} @closed=${() => (this._dlg = null)} .heading="NEW QUEST">
      <div class="dlg">
        <label>Name</label><input id="nq-name" type="text" />
        <label>Desired outcome</label><input id="nq-outcome" type="text" />
        <label>Deadline (optional)</label><input id="nq-due" type="date" />
        <div class="btns">
          <button @click=${async () => {
            await svc(this.hass, "create_project", {
              name: this.shadowRoot.querySelector("#nq-name").value,
              desired_outcome: this.shadowRoot.querySelector("#nq-outcome").value,
              due: this.shadowRoot.querySelector("#nq-due").value || undefined,
            });
            this._dlg = null;
          }}>Create</button>
          <button @click=${() => (this._dlg = null)}>Cancel</button>
        </div>
      </div>
    </ha-dialog>`;
  }
  static get styles() {
    return pipCss;
  }
}
customElements.define("gamified-gtd-quests", GamifiedGTDQuestsCard);

/* ------------------------------------------------------------------ */
/* Tasks card (with Clarify dialog for the inbox)                      */
/* ------------------------------------------------------------------ */

class GamifiedGTDTasksCard extends LitElement {
  static get properties() {
    return { hass: {}, config: {}, _dlg: {}, _task: {} };
  }
  static getStubConfig() {
    return { title: "NEXT ACTIONS", list: "next_actions", assigned: "all" };
  }
  setConfig(config) {
    this.config = { assigned: "all", list: "all", show_completed: false, ...config };
  }
  getCardSize() {
    return 5;
  }
  _items() {
    const listKeys = this.config.list === "all" ? Object.keys(LISTS) : [this.config.list];
    let items = [];
    for (const key of listKeys) {
      const st = this.hass.states[LISTS[key].entity];
      if (!st) continue;
      const meta = st.attributes.tasks || {};
      for (const it of st.attributes.todo_items || []) {
        items.push({ ...it, list: key, meta: meta[it.uid] || {} });
      }
    }
    const assigned = this.config.assigned;
    if (assigned === "me") {
      const me = mePerson(this.hass);
      items = items.filter((i) => i.meta.assigned_to === me || !i.meta.assigned_to);
    } else if (assigned && assigned !== "all") {
      items = items.filter((i) => i.meta.assigned_to === assigned);
    }
    if (!this.config.show_completed) items = items.filter((i) => i.status !== "completed");
    return items;
  }
  render() {
    const items = this._items();
    return html`
      <ha-card>
        <div class="head"><span class="title">${this.config.title || "TASKS"}</span>
          <span class="sub">${LISTS[this.config.list] ? LISTS[this.config.list].label : "ALL LISTS"}</span></div>
        ${items.length === 0 ? html`<div class="empty">Nothing here. War never changes… but this list is empty.</div>` : ""}
        ${items.map((i) => html`
          <div class="task ${i.status === "completed" ? "done" : ""}">
            <input type="checkbox" .checked=${i.status === "completed"}
              @change=${() => svc(this.hass, "complete_task", { task_id: i.uid })} />
            <span class="t-title">${i.summary}</span>
            ${i.meta.priority ? html`<span class="badge">P${i.meta.priority}</span>` : ""}
            ${i.meta.context ? html`<span class="badge">${i.meta.context}</span>` : ""}
            ${i.due ? html`<span class="badge">${i.due}</span>` : ""}
            ${i.meta.assigned_to ? html`<span class="badge">${i.meta.assigned_to.replace("person.", "")}</span>` : ""}
            ${i.list === "inbox" ? html`<button @click=${() => { this._task = i; this._dlg = "clarify"; }}>Clarify</button>` : ""}
            <button @click=${() => { this._task = i; this._dlg = "edit"; }}>Edit</button>
            <button @click=${() => svc(this.hass, "remove_task", { task_id: i.uid })}>✕</button>
          </div>`)}
        <div class="btns"><button @click=${() => { this._task = null; this._dlg = "add"; }}>+ Add task</button></div>
        ${this._renderTaskDialog()}
        ${this._renderClarifyDialog()}
      </ha-card>`;
  }
  _taskFields() {
    return html`
      <label>Title</label><input id="td-title" type="text" .value=${this._task ? this._task.summary : ""} />
      <label>Priority (1-5)</label><input id="td-priority" type="number" min="1" max="5" .value=${this._task?.meta?.priority || 3} />
      <label>Due</label><input id="td-due" type="date" .value=${this._task?.due || ""} />
      <label>Time estimate (min)</label><input id="td-time" type="number" min="0" .value=${this._task?.meta?.time_estimate || ""} />
      <label>Energy (1-5)</label><input id="td-energy" type="number" min="1" max="5" .value=${this._task?.meta?.energy || 3} />
      <label>Context</label><input id="td-context" type="text" placeholder="@home" .value=${this._task?.meta?.context || ""} />`;
  }
  _renderTaskDialog() {
    if (this._dlg !== "add" && this._dlg !== "edit") return "";
    const isAdd = this._dlg === "add";
    return html`<ha-dialog .open=${true} @closed=${() => (this._dlg = null)} .heading=${isAdd ? "ADD TASK" : "EDIT TASK"}>
      <div class="dlg">
        ${this._taskFields()}
        <div class="btns">
          <button @click=${async () => {
            const q = (id) => this.shadowRoot.querySelector(id).value;
            const data = {
              title: q("#td-title"),
              priority: Number(q("#td-priority")) || 3,
              due: q("#td-due") || undefined,
              time_estimate: q("#td-time") ? Number(q("#td-time")) : undefined,
              energy: Number(q("#td-energy")) || 3,
              context: q("#td-context") || undefined,
            };
            if (isAdd) {
              data.list = this.config.list === "all" ? "inbox" : this.config.list;
              await svc(this.hass, "add_to_inbox", data);
            } else {
              await svc(this.hass, "update_task", { task_id: this._task.uid, ...data });
            }
            this._dlg = null;
          }}>${isAdd ? "Add" : "Save"}</button>
          <button @click=${() => (this._dlg = null)}>Cancel</button>
        </div>
      </div>
    </ha-dialog>`;
  }
  _renderClarifyDialog() {
    if (this._dlg !== "clarify" || !this._task) return "";
    const log = this.hass.states["sensor.gtd_quest_log"];
    const projects = log ? Object.entries(log.attributes.quests || {}).filter(([, q]) => q.status === "active") : [];
    return html`<ha-dialog .open=${true} @closed=${() => (this._dlg = null)} .heading=${`CLARIFY: ${this._task.summary}`}>
      <div class="dlg">
        <div class="seg" id="cl-decision">
          ${["next_action", "project", "waiting_for", "someday", "done"].map((d, i) =>
            html`<button class=${i === 0 ? "on" : ""} data-v=${d} @click=${(e) => {
              this.shadowRoot.querySelectorAll("#cl-decision button").forEach((b) => b.classList.remove("on"));
              e.target.classList.add("on");
            }}>${d.replace(/_/g, " ")}</button>`)}
        </div>
        <label>Context (for next action)</label><input id="cl-context" type="text" placeholder="@home" />
        <label>Existing project</label>
        <select id="cl-project"><option value="">— new project —</option>
          ${projects.map(([id, q]) => html`<option value="${id}">${q.name}</option>`)}</select>
        <label>New project name / desired outcome</label>
        <input id="cl-projname" type="text" placeholder="Project name" />
        <input id="cl-outcome" type="text" placeholder="Desired outcome" />
        <div class="btns">
          <button @click=${async () => {
            const decision = this.shadowRoot.querySelector("#cl-decision button.on").dataset.v;
            const data = { task_id: this._task.uid, decision };
            const ctx = this.shadowRoot.querySelector("#cl-context").value;
            const proj = this.shadowRoot.querySelector("#cl-project").value;
            const pname = this.shadowRoot.querySelector("#cl-projname").value;
            if (ctx) data.context = ctx;
            if (proj) data.project_id = proj;
            if (pname) data.project_name = pname;
            const out = this.shadowRoot.querySelector("#cl-outcome").value;
            if (out) data.desired_outcome = out;
            await svc(this.hass, "clarify", data);
            this._dlg = null;
          }}>Clarify</button>
          <button @click=${() => (this._dlg = null)}>Cancel</button>
        </div>
      </div>
    </ha-dialog>`;
  }
  static get styles() {
    return pipCss;
  }
}
customElements.define("gamified-gtd-tasks", GamifiedGTDTasksCard);

/* ------------------------------------------------------------------ */
/* Review card                                                         */
/* ------------------------------------------------------------------ */

class GamifiedGTDReviewCard extends LitElement {
  static get properties() {
    return { hass: {}, config: {} };
  }
  static getStubConfig() {
    return { person: "person.example", title: "WEEKLY REVIEW" };
  }
  setConfig(config) {
    if (!config.person) throw new Error("person is required");
    this.config = config;
  }
  getCardSize() {
    return 3;
  }
  render() {
    const level = this.hass.states[sensorId(this.config.person, "level")];
    if (!level) return html`<ha-card><div class="empty">sensor not found</div></ha-card>`;
    const a = level.attributes;
    const checklist = a.review_checklist || {};
    const due = a.days_since_review === null || a.days_since_review === undefined ? true : a.days_since_review >= 7;
    return html`
      <ha-card>
        <div class="head"><span class="title">${this.config.title || "WEEKLY REVIEW"}</span>
          <span class="sub">streak ${a.review_streak || 0}</span></div>
        <div class="row"><span class="lbl">STATUS</span>
          <span class="val">${due ? "REVIEW DUE" : `due in ${7 - (a.days_since_review || 0)}d`}</span></div>
        <div class="checklist">
          ${Object.entries(checklist).map(([k, v]) => html`
            <div class="row ${v ? "cl-ok" : "cl-no"}">${v ? "☑" : "☐"} ${k.replace(/_/g, " ")}</div>`)}
        </div>
        <div class="btns">
          <button @click=${() => svc(this.hass, "start_review", { person: this.config.person })}>Start review</button>
          <button @click=${() => svc(this.hass, "complete_review", { person: this.config.person })}>Complete review</button>
        </div>
      </ha-card>`;
  }
  static get styles() {
    return pipCss;
  }
}
customElements.define("gamified-gtd-review", GamifiedGTDReviewCard);

/* ------------------------------------------------------------------ */
/* Rewards card                                                        */
/* ------------------------------------------------------------------ */

class GamifiedGTDRewardsCard extends LitElement {
  static get properties() {
    return { hass: {}, config: {} };
  }
  static getStubConfig() {
    return { person: "person.example", title: "REWARDS" };
  }
  setConfig(config) {
    if (!config.person) throw new Error("person is required");
    this.config = config;
  }
  getCardSize() {
    return 3;
  }
  render() {
    const caps = this.hass.states[sensorId(this.config.person, "caps")];
    const rewards = this.hass.states["sensor.gtd_rewards"];
    const balance = caps ? Number(caps.state) : 0;
    const list = rewards ? rewards.attributes.rewards || [] : [];
    return html`
      <ha-card>
        <div class="head"><span class="title">${this.config.title || "REWARDS"}</span>
          <span class="sub">CAPS: ${balance}</span></div>
        ${list.length === 0 ? html`<div class="empty">No rewards configured.</div>` : ""}
        ${list.map((r) => html`
          <div class="task">
            <span class="t-title">${r.name}<br /><span class="badge">${r.description || ""}</span></span>
            <span class="badge">${r.cost} caps</span>
            <button ?disabled=${balance < r.cost} @click=${() => svc(this.hass, "redeem_reward", { person: this.config.person, reward: r.id })}>Redeem</button>
          </div>`)}
      </ha-card>`;
  }
  static get styles() {
    return pipCss;
  }
}
customElements.define("gamified-gtd-rewards", GamifiedGTDRewardsCard);

/* ------------------------------------------------------------------ */

window.customCards = window.customCards || [];
for (const c of [
  { type: "gamified-gtd-stats", name: "Gamified GTD — Stats (Pip-Boy)", description: "Level, XP, HP, karma, caps, SPECIAL, skills, perks. Config: person." },
  { type: "gamified-gtd-quests", name: "Gamified GTD — Quest Log", description: "Projects as quests with progress. Config: title." },
  { type: "gamified-gtd-tasks", name: "Gamified GTD — Tasks", description: "GTD lists with clarify dialog. Config: list, assigned, title." },
  { type: "gamified-gtd-review", name: "Gamified GTD — Weekly Review", description: "Auto-checked review checklist. Config: person." },
  { type: "gamified-gtd-rewards", name: "Gamified GTD — Rewards", description: "Caps reward shop. Config: person." },
]) {
  window.customCards.push(c);
}
