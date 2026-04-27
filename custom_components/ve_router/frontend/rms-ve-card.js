const BaseElement = customElements.get('ha-panel-lovelace')
  ? Object.getPrototypeOf(customElements.get('ha-panel-lovelace'))
  : HTMLElement;
const html = BaseElement.prototype.html || window.html;
const css = BaseElement.prototype.css || window.css;

const fireEvent = (node, type, detail, options) => {
  const event = new Event(type, {
    bubbles: options?.bubbles ?? true,
    cancelable: options?.cancelable ?? false,
    composed: options?.composed ?? true,
  });
  event.detail = detail;
  node.dispatchEvent(event);
  return event;
};

class RMSVECardEditor extends BaseElement {
  static properties = {
    hass: {},
    _config: { state: true },
    _devices: { state: true },
  };

  static styles = css`
    :host {
      display: block;
      padding: 8px 0 0;
    }
    .editor {
      display: grid;
      gap: 12px;
    }
    .section {
      border: 1px solid var(--divider-color);
      border-radius: 16px;
      padding: 14px;
    }
    .section-title {
      font-weight: 700;
      margin-bottom: 10px;
    }
    .toggles {
      display: grid;
      gap: 8px;
    }
    .hint {
      color: var(--secondary-text-color);
      font-size: 0.92rem;
    }
    .native-select {
      width: 100%;
      box-sizing: border-box;
      min-height: 56px;
      border-radius: 12px;
      border: 1px solid var(--divider-color);
      background: var(--card-background-color);
      color: var(--primary-text-color);
      padding: 0 14px;
      font: inherit;
    }
    .field-label {
      display: block;
      margin-bottom: 8px;
      font-weight: 500;
      color: var(--secondary-text-color);
    }
    .side-by-side {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
      align-items: start;
    }
    .extra-grid {
      display: grid;
      gap: 12px;
    }
    .extra-row-label {
      font-size: 0.9rem;
      font-weight: 700;
      color: var(--secondary-text-color);
      margin: 2px 0 6px;
    }
    .info-config-row {
      display: grid;
      grid-template-columns: minmax(180px, 0.75fr) minmax(0, 1fr);
      gap: 10px;
      align-items: start;
      padding: 10px;
      border-radius: 14px;
      border: 1px solid var(--divider-color);
      background: rgba(127,127,127,0.04);
    }
    .info-config-row.external {
      grid-template-columns: minmax(180px, 0.75fr) minmax(0, 1.3fr);
    }
    .external-entity-layout {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(120px, 0.55fr);
      gap: 10px;
      align-items: start;
      min-width: 0;
    }
    .external-entity-full {
      grid-column: 1 / -1;
      min-width: 0;
    }
    .compact-select {
      min-height: 56px;
    }
    .entity-field {
      min-width: 0;
    }
    .entity-field ha-selector,
    .entity-field ha-textfield {
      width: 100%;
      display: block;
    }
    .row-actions {
      display: flex;
      gap: 6px;
      justify-content: flex-end;
      margin-top: 8px;
    }
    .row-action-btn, .add-info-btn {
      min-height: 34px;
      border-radius: 10px;
      border: 1px solid var(--divider-color);
      background: var(--card-background-color);
      color: var(--primary-text-color);
      cursor: pointer;
      padding: 0 10px;
      font: inherit;
    }
    .add-info-btn {
      width: 100%;
      margin-top: 10px;
      color: var(--primary-color);
      font-weight: 700;
    }
    @media (max-width: 900px) {
      .info-config-row,
      .info-config-row.external,
      .external-entity-layout {
        grid-template-columns: 1fr;
      }
    }
  `;

  setConfig(config) {
    this._config = {
      title: 'RMS VE',
      show_title: true,
      show_header: true,
      show_manual_current: true,
      show_gauge: false,
      show_infos: true,
      compact_mode: true,
      info_items: [
        { type: 'power' },
        { type: 'energy' },
        { type: 'charge_time' },
        { type: 'current' },
      ],
      external_items: [],
      external_entity: '',
      external_entity_name: '',
      external_entity_icon: 'mdi:plus-circle-outline',
      show_vehicle_soc_section: true,
      ...config,
    };
    if ((!this._config.info_items || !this._config.info_items.length)) {
      const migrated = [];
      for (const key of ['power', 'energy', 'charge_time', 'current']) migrated.push({ type: key });
      if (this._config.external_entity) {
        migrated.push({
          type: 'external',
          entity: this._config.external_entity,
          name: this._config.external_entity_name || '',
          icon: this._config.external_entity_icon || 'mdi:plus-circle-outline',
        });
      }
      for (const item of (this._config.external_items || [])) {
        if (item?.entity) migrated.push({
          type: 'external',
          entity: item.entity,
          name: item.name || '',
          icon: item.icon || 'mdi:plus-circle-outline',
        });
      }
      this._config.info_items = migrated;
    }
  }

  connectedCallback() {
    super.connectedCallback();
    if (window.loadCardHelpers) {
      window.loadCardHelpers().catch(() => undefined);
    }
    this._loadDevices();
  }

  updated(changedProps) {
    if (changedProps.has('hass') && !this._devices?.length) {
      this._loadDevices();
    }
  }

  async _loadDevices() {
    if (!this.hass || this._loadingDevices) return;
    this._loadingDevices = true;
    try {
      const devices = await this.hass.callWS({ type: 'config/device_registry/list' });
      this._devices = devices.filter((d) =>
        (d.identifiers || []).some(([domain]) => domain === 've_router')
      );
    } catch (_err) {
      this._devices = [];
    } finally {
      this._loadingDevices = false;
    }
  }

  _updateConfig(changes) {
    const config = { type: 'custom:rms-ve-card', ...this._config, ...changes };
    Object.keys(config).forEach((key) => {
      if (config[key] === undefined) delete config[key];
    });
    this._config = config;
    fireEvent(this, 'config-changed', { config });
  }


  _onDeviceSelected(ev) {
    const value = String(ev?.target?.value ?? ev?.detail?.value ?? '').trim();
    this._updateConfig({ device_id: value || undefined });
  }

  _onValueChanged(ev) {
    const target = ev.target;
    const configValue = target.configValue;
    if (!configValue) return;
    const value = target.type === 'checkbox' ? target.checked : target.value;
    this._updateConfig({ [configValue]: value });
  }

  render() {
    if (!this.hass || !this._config) return html``;

    return html`
      <div class="editor">
        <div class="section">
          <div class="section-title">Configuration principale</div>
          <ha-textfield
            label="Titre"
            .value=${this._config.title || ''}
            .configValue=${'title'}
            @input=${this._onValueChanged}
          ></ha-textfield>
          <div style="height: 10px"></div>
          ${this._toggle('show_title', 'Afficher le titre')}
          <div style="height: 12px"></div>
          <label class="field-label" for="rms-ve-device-select">Équipement RMS VE</label>
          <select
            id="rms-ve-device-select"
            class="native-select"
            .value=${this._config.device_id || ''}
            @change=${this._onDeviceSelected}
          >
            <option value="">Sélectionner un équipement</option>
            ${(this._devices || []).map(
              (device) => html`
                <option value=${device.id} ?selected=${(this._config.device_id || '') === device.id}>${device.name_by_user || device.name || device.id}</option>
              `
            )}
          </select>
          <div class="hint" style="margin-top:10px;">
            L'éditeur sélectionne directement le device RMS VE.
          </div>
        </div>

        <div class="section">
          <div class="section-title">Informations à afficher</div>
          <div class="hint" style="margin-bottom:10px;">
            Choisis les infos dans l'ordre voulu. La card affichera ces lignes de gauche à droite, puis ligne suivante.
          </div>
          <div class="extra-grid">
            ${(this._config.info_items || []).map((item, index) => this._infoRow(index, item))}
          </div>
          <button class="add-info-btn" type="button" @click=${() => this._addInfoItem()}>+ Ajouter une information</button>
        </div>

        <div class="section">
          <div class="section-title">SOC véhicule</div>
          ${this._toggle('show_vehicle_soc_section', 'Afficher la section SOC véhicule dans la carte')}
          <div class="hint" style="margin-top:10px;">
            Affiche le SOC de l'entité véhicule configurée dans l'intégration, le slider SOC cible et l'interrupteur d'utilisation de la limite.
          </div>
        </div>
      </div>
    `;
  }

  _infoOptions() {
    return [
      ['', '— Non affiché —'],
      ['power', 'Puissance'],
      ['energy', 'Énergie'],
      ['charge_time', 'Temps de charge'],
      ['current', 'Courant VE'],
      ['pwm', 'PWM'],
      ['auto_regulation', 'Régulation auto VE'],
      ['external', 'Entité externe'],
    ];
  }

  _infoRow(index, itemArg) {
    const item = itemArg || (this._config.info_items || [])[index] || {};
    const type = item.type || '';
    return html`
      <div>
        <div class="extra-row-label">Position ${index + 1}</div>
        <div class="info-config-row ${type === 'external' ? 'external' : ''}">
          <select
            class="native-select compact-select"
            .value=${type}
            @change=${(ev) => this._onInfoItemChanged(index, 'type', ev.target.value)}
          >
            ${this._infoOptions().map(([value, label]) => html`
              <option value=${value} ?selected=${type === value}>${label}</option>
            `)}
          </select>

          ${type === 'external' ? html`
            <div class="external-entity-layout">
              <ha-textfield
                label="Libellé"
                helper="Ex: Surplus EV"
                .value=${item.name || ''}
                @input=${(ev) => this._onInfoItemChanged(index, 'name', ev.target.value)}
              ></ha-textfield>
              <ha-textfield
                label="Icône"
                helper="mdi:solar-power"
                .value=${item.icon || ''}
                @input=${(ev) => this._onInfoItemChanged(index, 'icon', ev.target.value)}
              ></ha-textfield>
              <div class="entity-field external-entity-full">
                <div class="field-label">Entité</div>
                ${customElements.get('ha-selector') ? html`
                  <ha-selector
                    .hass=${this.hass}
                    .selector=${{ entity: {} }}
                    .value=${item.entity || ''}
                    @value-changed=${(ev) => this._onInfoItemChanged(index, 'entity', ev.detail.value)}
                  ></ha-selector>
                ` : html`
                  <ha-textfield
                    label="Entité"
                    helper="Ex: sensor.surplus_ev"
                    .value=${item.entity || ''}
                    @input=${(ev) => this._onInfoItemChanged(index, 'entity', ev.target.value)}
                  ></ha-textfield>
                `}
              </div>
            </div>
          ` : html`<div class="hint">${type ? 'Information RMS VE interne.' : 'Non affiché.'}</div>`}
        </div>
        <div class="row-actions">
          <button class="row-action-btn" type="button" @click=${() => this._moveInfoItem(index, -1)} ?disabled=${index === 0}>↑</button>
          <button class="row-action-btn" type="button" @click=${() => this._moveInfoItem(index, 1)} ?disabled=${index >= (this._config.info_items || []).length - 1}>↓</button>
          <button class="row-action-btn" type="button" @click=${() => this._removeInfoItem(index)}>Supprimer</button>
        </div>
      </div>
    `;
  }

  _onInfoItemChanged(index, key, value) {
    const items = [...(this._config.info_items || [])];
    const current = { ...(items[index] || {}) };

    if (key === 'type') {
      if (!value) {
        items.splice(index, 1);
      } else if (value === 'external') {
        items[index] = { type: 'external', entity: current.entity || '', name: current.name || '', icon: current.icon || 'mdi:plus-circle-outline' };
      } else {
        items[index] = { type: value };
      }
    } else {
      current.type = current.type || 'external';
      current[key] = value;
      items[index] = current;
    }

    this._updateConfig({ info_items: items.filter((item) => item && item.type) });
  }

  _addInfoItem() {
    const items = [...(this._config.info_items || [])];
    items.push({ type: 'external', entity: '', name: '', icon: 'mdi:plus-circle-outline' });
    this._updateConfig({ info_items: items });
  }

  _removeInfoItem(index) {
    const items = [...(this._config.info_items || [])];
    items.splice(index, 1);
    this._updateConfig({ info_items: items });
  }

  _moveInfoItem(index, direction) {
    const items = [...(this._config.info_items || [])];
    const target = index + direction;
    if (target < 0 || target >= items.length) return;
    [items[index], items[target]] = [items[target], items[index]];
    this._updateConfig({ info_items: items });
  }

  _toggle(key, label) {
    const checked = this._config[key] !== false && this._config[key] !== 'false';
    return html`
      <ha-formfield .label=${label}>
        <ha-switch
          .checked=${checked}
          @change=${(ev) => this._updateConfig({ [key]: Boolean(ev.target.checked) })}
        ></ha-switch>
      </ha-formfield>
    `;
  }
}

class RMSVECard extends BaseElement {
  static properties = {
    hass: {},
    _config: { state: true },
    _resolved: { state: true },
    _error: { state: true },
    _pendingManualCurrent: { state: true },
    _pendingTargetSoc: { state: true },
    _manualCommitTimer: { state: false },
  };

  static getStubConfig(hass) {
    const states = Object.values(hass?.states || {});
    const modeEntity = states.find((s) => s.entity_id.startsWith('select.') && /mode/i.test(s.entity_id));
    const deviceId = modeEntity?.attributes?.device_id;
    return { type: 'custom:rms-ve-card', title: 'RMS VE', ...(deviceId ? { device_id: deviceId } : {}) };
  }

  static async getConfigElement() {
    return document.createElement('rms-ve-card-editor');
  }

  static styles = css`
    :host {
      display: block;
    }
    ha-card {
      padding: 4px 10px 8px;
      border-radius: 24px;
    }
    .stack {
      display: grid;
      gap: 10px;
    }
    .card-title {
      text-align: center;
      font-size: 1.45rem;
      font-weight: 500;
      line-height: 1.15;
      margin: 4px 0 6px;
      color: var(--primary-text-color);
    }
    .status {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(126px, 38%);
      grid-template-areas:
        "main gauge";
      align-items: center;
      gap: 10px 12px;
      padding: 12px 14px;
      border-radius: 20px;
      background: rgba(var(--rgb-primary-color), 0.08);
      border: 1px solid rgba(var(--rgb-primary-color), 0.18);
      transition: border-color 180ms ease, box-shadow 180ms ease, background 180ms ease;
    }
    .status.charging {
      border-color: rgba(80, 220, 120, 0.42);
      box-shadow: 0 10px 24px rgba(80, 220, 120, 0.08);
      background: linear-gradient(180deg, rgba(38, 68, 46, 0.28), rgba(var(--rgb-primary-color), 0.06));
    }
    .status.auto {
      border-color: rgba(74, 163, 255, 0.38);
      box-shadow: 0 10px 24px rgba(74, 163, 255, 0.07);
      background: linear-gradient(180deg, rgba(35, 52, 78, 0.28), rgba(var(--rgb-primary-color), 0.06));
    }
    .status.fault {
      border-color: rgba(255, 90, 90, 0.44);
      box-shadow: 0 10px 24px rgba(255, 90, 90, 0.06);
    }
    .status.connected,
    .status.idle {
      border-color: rgba(245, 166, 35, 0.34);
      box-shadow: 0 10px 24px rgba(245, 166, 35, 0.05);
      background: linear-gradient(180deg, rgba(70, 50, 22, 0.22), rgba(var(--rgb-primary-color), 0.06));
    }
    .status-main {
      grid-area: main;
      display: flex;
      align-items: flex-start;
      gap: 12px;
      min-width: 0;
    }
    .status-badge {
      width: 14px;
      height: 14px;
      border-radius: 50%;
      flex: 0 0 14px;
      transition: background 180ms ease, box-shadow 180ms ease;
    }
    .status-badge.charging {
      animation: rmsve-status-pulse 1.8s ease-out infinite;
    }
    @keyframes rmsve-status-pulse {
      0% { box-shadow: 0 0 0 0 rgba(76, 175, 80, 0.45); }
      70% { box-shadow: 0 0 0 9px rgba(76, 175, 80, 0); }
      100% { box-shadow: 0 0 0 0 rgba(76, 175, 80, 0); }
    }
    .status-text {
      font-size: 1.02rem;
      font-weight: 700;
    }
    .status-pill {
      margin-top: 4px;
      display: inline-flex;
      align-items: center;
      width: fit-content;
      padding: 2px 7px;
      border-radius: 999px;
      font-size: 0.66rem;
      font-weight: 700;
      letter-spacing: 0.04em;
      color: var(--primary-text-color);
      background: rgba(255,255,255,0.07);
      opacity: 0.82;
    }
    .status-mini-gauge {
      grid-area: gauge;
      min-width: 126px;
      max-width: 190px;
      width: 100%;
      justify-self: end;
      padding: 0;
      display: grid;
      place-items: center;
    }
    .status-mini-gauge.clickable {
      cursor: pointer;
      border-radius: 16px;
      transition: background 140ms ease, transform 120ms ease;
    }
    .status-mini-gauge.clickable:hover {
      background: rgba(var(--rgb-primary-text-color), 0.04);
    }
    .status-mini-gauge.clickable:active {
      transform: scale(0.985);
    }
    .status-mini-semi {
      position: relative;
      width: 100%;
      max-width: 210px;
      aspect-ratio: 1.75 / 1;
      filter: drop-shadow(0 10px 18px rgba(0,0,0,0.18));
    }
    .status-mini-semi svg {
      width: 100%;
      height: 100%;
      overflow: visible;
    }
    .status-mini-track {
      opacity: 0.9;
    }
    .status-mini-progress {
      transition: stroke-dasharray 220ms ease, stroke 220ms ease;
    }
    .status-mini-value {
      position: absolute;
      left: 50%;
      top: 60%;
      transform: translate(-50%, -50%);
      display: flex;
      align-items: baseline;
      gap: 4px;
      font-weight: 700;
      white-space: nowrap;
    }
    .status-mini-value-main {
      font-size: 1.18rem;
      line-height: 1;
      letter-spacing: -0.02em;
    }
    .status-mini-value-unit {
      font-size: 0.8rem;
      line-height: 1;
      color: var(--secondary-text-color);
      font-weight: 600;
    }
    .mode-panel {
      border-radius: 22px;
      padding: 8px 10px;
      border: 1px solid var(--divider-color);
      background: rgba(var(--rgb-primary-text-color), 0.02);
    }
    .mode-grid {
      display: flex !important;
      flex-direction: row !important;
      flex-wrap: nowrap !important;
      align-items: stretch;
      justify-content: space-between;
      gap: 4px;
      width: 100%;
    }
    .mode-btn {
      cursor: pointer;
      border: 0;
      border-radius: 12px;
      padding: 8px 6px;
      text-align: center;
      background: transparent;
      transition: 160ms ease;
      user-select: none;
      color: var(--primary-text-color);
      flex: 1 1 0;
      min-width: 0;
      white-space: nowrap;
      overflow: hidden;
    }
    .mode-btn[disabled] {
      opacity: 0.5;
      pointer-events: none;
    }
    .mode-icon {
      display: grid;
      place-items: center;
      width: 40px;
      height: 40px;
      margin: 0 auto 6px auto;
      border-radius: 12px;
      background: rgba(var(--rgb-primary-text-color), 0.05);
      border: 1px solid rgba(var(--rgb-primary-text-color), 0.08);
      color: var(--primary-text-color);
      --mdc-icon-size: 28px;
    }
    .mode-btn.active .mode-icon {
      box-shadow: 0 0 18px rgba(var(--rgb-primary-color), 0.10);
    }
    .mode-btn.active.mode-stop .mode-icon {
      background: rgba(211, 47, 47, 0.18);
      border-color: rgba(211, 47, 47, 0.34);
      color: #ef5350;
      box-shadow: 0 0 16px rgba(211, 47, 47, 0.20);
    }
    .mode-btn.active.mode-auto .mode-icon {
      background: rgba(46, 125, 50, 0.18);
      border-color: rgba(46, 125, 50, 0.34);
      color: #66bb6a;
      box-shadow: 0 0 16px rgba(46, 125, 50, 0.20);
    }
    .mode-btn.active.mode-semi .mode-icon {
      background: rgba(21, 101, 192, 0.18);
      border-color: rgba(21, 101, 192, 0.34);
      color: #42a5f5;
      box-shadow: 0 0 16px rgba(21, 101, 192, 0.20);
    }
    .mode-btn.active.mode-manual .mode-icon {
      background: rgba(79, 195, 247, 0.18);
      border-color: rgba(79, 195, 247, 0.34);
      color: #81d4fa;
      box-shadow: 0 0 16px rgba(79, 195, 247, 0.20);
    }
    .panel {
      border-radius: 20px;
      padding: 7px 9px;
      border: 1px solid var(--divider-color);
      background: rgba(var(--rgb-primary-text-color), 0.02);
    }
    .soc-panel {
      border-radius: 20px;
      padding: 10px 12px;
      border: 1px solid var(--divider-color);
      background: rgba(var(--rgb-primary-text-color), 0.02);
    }
    .soc-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }
    .soc-tile {
      min-width: 0;
      border-radius: 16px;
      padding: 10px;
      border: 1px solid rgba(var(--rgb-primary-text-color), 0.08);
      background: rgba(var(--rgb-primary-text-color), 0.025);
    }
    .soc-tile.clickable {
      cursor: pointer;
    }
    .soc-tile-label {
      display: flex;
      align-items: center;
      gap: 6px;
      min-width: 0;
      color: var(--secondary-text-color);
      font-size: 0.78rem;
      line-height: 1.15;
      margin-bottom: 6px;
    }
    .soc-tile-label ha-icon {
      --mdc-icon-size: 16px;
      flex: 0 0 auto;
    }
    .soc-tile-value {
      color: var(--primary-text-color);
      font-size: 1.18rem;
      font-weight: 800;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .soc-tile-value.disconnected {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      color: var(--secondary-text-color);
      font-size: 0.86rem;
      font-weight: 650;
    }
    .soc-tile-value.disconnected ha-icon {
      --mdc-icon-size: 20px;
    }
    .soc-switch-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-top: 10px;
      padding-top: 8px;
      border-top: 1px solid rgba(var(--rgb-primary-text-color), 0.08);
    }

    .status-manual-line {
      margin-top: 8px;
      display: inline-flex;
      align-items: baseline;
      gap: 8px;
      color: var(--secondary-text-color);
      font-size: 0.84rem;
      cursor: pointer;
      user-select: none;
    }
    .status-manual-line strong {
      color: var(--primary-color);
      font-size: 1.06rem;
      font-weight: 800;
      white-space: nowrap;
    }
    .status-manual-controls {
      grid-area: manual;
      padding-top: 8px;
      border-top: 1px solid rgba(var(--rgb-primary-text-color), 0.08);
    }

    .manual-head {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
      margin-bottom: 8px;
    }
    .manual-head-left {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .icon-bubble {
      width: 34px;
      height: 34px;
      border-radius: 14px;
      display: grid;
      place-items: center;
      background: rgba(var(--rgb-primary-color), 0.16);
      color: var(--primary-color);
      border: 1px solid rgba(var(--rgb-primary-color), 0.22);
      flex: 0 0 34px;
    }
    .manual-title {
      font-size: 0.86rem;
      color: var(--secondary-text-color);
    }
    .manual-value {
      font-size: 1.18rem;
      font-weight: 750;
      white-space: nowrap;
    }
    .manual-controls {
      display: grid;
      grid-template-columns: 40px 1fr 40px;
      gap: 7px;
      align-items: center;
    }
    .icon-btn {
      width: 40px;
      height: 40px;
      border-radius: 15px;
      border: 1px solid var(--divider-color);
      background: var(--ha-card-background, var(--card-background-color));
      color: var(--primary-text-color);
      font-size: 1.5rem;
      cursor: pointer;
    }
    .icon-btn[disabled] {
      opacity: 0.45;
      cursor: default;
    }
    input[type="range"] {
      width: 100%;
    }
    .range-labels {
      display: flex;
      justify-content: space-between;
      margin-top: 5px;
      color: var(--secondary-text-color);
      font-size: 0.78rem;
    }
    .gauge-wrap {
      display: grid;
      place-items: center;
      padding: 8px 0 0;
    }
    .gauge {
      position: relative;
      width: min(100%, 360px);
      aspect-ratio: 2 / 1.15;
    }
    .gauge svg {
      width: 100%;
      height: 100%;
      overflow: visible;
    }
    .gauge-value {
      position: absolute;
      left: 50%;
      top: 58%;
      transform: translate(-50%, -50%);
      font-size: 2.6rem;
      font-weight: 700;
      line-height: 1;
    }
    .gauge-label {
      margin-top: -4px;
      text-align: center;
      font-size: 1rem;
      color: var(--secondary-text-color);
    }
    .gauge-minmax {
      width: min(100%, 360px);
      display: flex;
      justify-content: space-between;
      color: var(--secondary-text-color);
      margin: -8px auto 0;
      font-size: 0.95rem;
    }
    .metrics-card,
    .extras-card {
      border-radius: 22px;
      padding: 0;
      border: 1px solid var(--divider-color);
      background: rgba(var(--rgb-primary-text-color), 0.02);
      overflow: hidden;
    }
    .metrics-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
    .metric-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 16px 18px;
      min-width: 0;
    }
    .metric-item.metric-row-2,
    .metric-item.metric-col-2,
    .metric-item.metric-col-3 {
      border: 0;
    }
    .metric-icon {
      width: 36px;
      height: 36px;
      display: grid;
      place-items: center;
      flex: 0 0 36px;
      --mdc-icon-size: 32px;
    }
    .metric-body {
      min-width: 0;
    }
    .metric-name {
      font-size: 0.9rem;
      color: var(--secondary-text-color);
      line-height: 1.1;
      margin-bottom: 3px;
    }
    .metric-value {
      font-size: 0.98rem;
      font-weight: 700;
      line-height: 1.15;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .metric-item.clickable,
    .extra-item.clickable {
      cursor: pointer;
      transition: background 120ms ease, transform 120ms ease;
    }
    .metric-item.clickable:hover,
    .extra-item.clickable:hover {
      background: rgba(var(--rgb-primary-text-color), 0.055);
    }
    .metric-item.clickable:active,
    .extra-item.clickable:active {
      transform: scale(0.99);
    }
    .extras-head {
      display: none;
    }
    .extras-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }
    .extra-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 16px 18px;
      min-width: 0;
    }
    .extra-item + .extra-item {
      border-left: 0;
    }
    .extra-icon {
      width: 34px;
      height: 34px;
      display: grid;
      place-items: center;
      flex: 0 0 34px;
      --mdc-icon-size: 30px;
    }
    .extra-body {
      min-width: 0;
    }
    .extra-name {
      font-size: 0.88rem;
      color: var(--secondary-text-color);
      line-height: 1.1;
      margin-bottom: 3px;
    }
    .extra-value {
      font-size: 0.98rem;
      font-weight: 700;
      line-height: 1.15;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .footer {
      display: flex;
      justify-content: flex-start;
      align-items: center;
      gap: 12px;
      color: var(--secondary-text-color);
      font-size: 0.8rem;
      padding: 0 4px;
    }
    .hint, .error {
      padding: 14px;
      border-radius: 16px;
      background: rgba(var(--rgb-primary-text-color), 0.04);
      color: var(--secondary-text-color);
    }
    .error {
      color: var(--error-color);
    }
    .spacious {
      gap: 16px;
    }
    .spacious .mode-panel,
    .spacious .panel {
      padding: 16px;
    }
    .spacious .mode-grid {
      gap: 8px;
    }
    .spacious .mode-btn {
      padding: 12px 8px;
    }
    .spacious .mode-icon {
      width: 54px;
      height: 54px;
      margin-bottom: 10px;
    }
    .spacious .manual-controls {
      grid-template-columns: 52px 1fr 52px;
      gap: 10px;
    }
    .spacious .icon-btn {
      width: 52px;
      height: 52px;
    }
    .spacious .gauge-value {
      font-size: 3.2rem;
    }
    @media (max-width: 640px) {
      .status {
        align-items: stretch;
      }
      .status-mini-gauge {
        width: 42%;
        min-width: 126px;
      }
      .mode-grid {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 2px;
      }
      .mode-panel {
        padding: 6px 6px;
      }
      .mode-btn {
        padding: 6px 2px;
        font-size: 0.82rem;
      }
      .mode-icon {
        width: 34px;
        height: 34px;
        margin-bottom: 4px;
        --mdc-icon-size: 24px;
      }
      .metrics-grid,
      .extras-grid {
        grid-template-columns: 1fr;
      }
      .metric-item.metric-col-2,
      .metric-item.metric-col-3,
      .extra-item + .extra-item {
        border-left: 0;
      }
      .metric-item.metric-row-1-mobile,
      .metric-item.metric-row-2,
      .extra-item + .extra-item {
        border-top: 1px solid rgba(var(--rgb-primary-text-color), 0.08);
      }
      .gauge-value {
        font-size: 2.4rem;
      }
      .spacious .gauge-value {
        font-size: 2.8rem;
      }
    }
  

    /* v0.5.1 - mobile: conserve les 4 boutons sur une seule ligne */
    @media (max-width: 420px) {
      .status {
        grid-template-columns: minmax(0, 1fr) minmax(112px, 42%);
        gap: 8px 10px;
      }
      .status-mini-gauge {
        min-width: 112px;
      }
      .mode-grid {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 1px;
      }
      .mode-btn {
        padding: 5px 0;
        font-size: 0.70rem;
        min-width: 0;
      }
      .mode-icon {
        width: 28px;
        height: 28px;
        border-radius: 9px;
        --mdc-icon-size: 20px;
        margin-bottom: 3px;
      }
    }

    /* v0.4.8 - version premium : zone infos compacte, sans carrelage sombre */
    .metrics-card {
      border-radius: 24px;
      padding: 10px 12px;
      border: 1px solid rgba(var(--rgb-primary-text-color), 0.08);
      background:
        radial-gradient(circle at 20% 0%, rgba(var(--rgb-primary-color), 0.055), transparent 34%),
        linear-gradient(180deg, rgba(var(--rgb-primary-text-color), 0.018), rgba(var(--rgb-primary-text-color), 0.008));
      overflow: hidden;
      box-shadow:
        inset 0 1px 0 rgba(255,255,255,0.035),
        0 8px 22px rgba(0,0,0,0.10);
    }
    .metrics-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 6px 8px;
    }
    .metric-item {
      border: 0 !important;
      border-radius: 18px;
      background: transparent;
      padding: 7px 9px;
      min-height: 48px;
      gap: 9px;
      transition: background 140ms ease, transform 120ms ease, box-shadow 140ms ease;
    }
    .metric-item.clickable:hover {
      background: rgba(var(--rgb-primary-text-color), 0.045);
      box-shadow: inset 0 0 0 1px rgba(var(--rgb-primary-text-color), 0.045);
    }
    .metric-item.clickable:active {
      transform: scale(0.985);
    }
    .metric-icon {
      width: 28px;
      height: 28px;
      --mdc-icon-size: 28px;
      filter: drop-shadow(0 0 8px rgba(0,0,0,0.18));
    }
    .metric-body {
      min-width: 0;
    }
    .metric-name {
      font-size: 0.78rem;
      line-height: 1.05;
      color: rgba(var(--rgb-primary-text-color), 0.66);
    }
    .metric-value {
      margin-top: 3px;
      font-size: 0.98rem;
      line-height: 1.05;
      font-weight: 750;
      color: rgba(var(--rgb-primary-text-color), 0.96);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    @media (max-width: 520px) {
      .metrics-card {
        padding: 9px;
      }
      .metrics-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 6px;
      }
      .metric-item {
        padding: 7px 8px;
        min-height: 46px;
        gap: 7px;
      }
      .metric-icon {
        width: 24px;
        height: 24px;
        --mdc-icon-size: 24px;
      }
      .metric-name {
        font-size: 0.72rem;
      }
      .metric-value {
        font-size: 0.88rem;
      }
    }

    /* v0.5.5 - réglages demandés: titre centré, panel A compact, boutons mobile plus grands */
    @media (max-width: 520px) {
      ha-card {
        padding: 4px 8px 8px;
      }
      .card-title {
        font-size: 1.35rem;
        margin: 2px 0 5px;
        text-align: center;
      }
      .stack {
        gap: 9px;
      }
      .mode-panel {
        padding: 7px 7px;
      }
      .mode-grid {
        flex-wrap: nowrap !important;
        gap: 4px !important;
      }
      .mode-btn {
        padding: 7px 1px !important;
        font-size: 0.74rem !important;
      }
      .mode-icon {
        width: 34px !important;
        height: 34px !important;
        border-radius: 11px !important;
        --mdc-icon-size: 24px !important;
        margin-bottom: 4px !important;
      }
      .panel {
        padding: 7px 9px;
        border-radius: 20px;
      }
      .status-manual-line {
      margin-top: 8px;
      display: flex;
      align-items: baseline;
      gap: 8px;
      color: var(--secondary-text-color);
      font-size: 0.84rem;
    }
    .status-manual-line strong {
      color: var(--primary-color);
      font-size: 1.06rem;
      font-weight: 800;
      white-space: nowrap;
    }
    .status-manual-controls {
      grid-area: manual;
      padding-top: 8px;
      border-top: 1px solid rgba(var(--rgb-primary-text-color), 0.08);
    }

    .manual-head {
        margin-bottom: 7px;
      }
      .icon-bubble {
        width: 32px;
        height: 32px;
        flex-basis: 32px;
        border-radius: 13px;
      }
      .manual-title {
        font-size: 0.82rem;
      }
      .manual-value {
        font-size: 1.12rem;
      }
      .manual-controls {
        grid-template-columns: 38px 1fr 38px;
        gap: 7px;
      }
      .icon-btn {
        width: 38px;
        height: 38px;
        border-radius: 14px;
      }
    }
`;

  constructor() {
    super();
    this._config = {};
    this._resolved = null;
    this._error = '';
    this._pendingManualCurrent = null;
    this._pendingTargetSoc = null;
    this._manualCommitTimer = null;
  }

  setConfig(config) {
    this._config = {
      title: 'RMS VE',
      show_title: true,
      show_header: true,
      show_manual_current: true,
      show_gauge: false,
      show_infos: true,
      compact_mode: true,
      info_items: [
        { type: 'power' },
        { type: 'energy' },
        { type: 'charge_time' },
        { type: 'current' },
      ],
      external_items: [],
      external_entity: '',
      external_entity_name: '',
      external_entity_icon: 'mdi:plus-circle-outline',
      show_vehicle_soc_section: true,
      ...config,
    };
    if ((!this._config.info_items || !this._config.info_items.length)) {
      const migrated = [];
      for (const key of ['power', 'energy', 'charge_time', 'current']) migrated.push({ type: key });
      if (this._config.external_entity) {
        migrated.push({
          type: 'external',
          entity: this._config.external_entity,
          name: this._config.external_entity_name || '',
          icon: this._config.external_entity_icon || 'mdi:plus-circle-outline',
        });
      }
      for (const item of (this._config.external_items || [])) {
        if (item?.entity) migrated.push({
          type: 'external',
          entity: item.entity,
          name: item.name || '',
          icon: item.icon || 'mdi:plus-circle-outline',
        });
      }
      this._config.info_items = migrated;
    }
    this._resolved = null;
    this._error = '';
    this._pendingManualCurrent = null;
    this._pendingTargetSoc = null;
    this._manualCommitTimer = null;
  }

  getCardSize() {
    return 8;
  }

  connectedCallback() {
    super.connectedCallback();
    this._resolveEntities();
  }

  updated(changedProps) {
    if (changedProps.has('hass') && !this._resolved) {
      this._resolveEntities();
    }
  }

  async _resolveEntities() {
    if (!this.hass || this._resolved || this._resolving) return;
    this._resolving = true;
    try {
      if (this._config.entities) {
        this._resolved = this._config.entities;
        this._error = '';
        return;
      }
      if (!this._config.device_id) {
        this._error = 'Aucun device_id fourni.';
        return;
      }
      const [devices, entities] = await Promise.all([
        this.hass.callWS({ type: 'config/device_registry/list' }),
        this.hass.callWS({ type: 'config/entity_registry/list' }),
      ]);
      const device = devices.find((d) => d.id === this._config.device_id);
      if (!device) {
        this._error = `Device introuvable: ${this._config.device_id}`;
        return;
      }
      const byDevice = entities.filter((e) => e.device_id === device.id);
      const findByUniqueSuffix = (...suffixes) => {
        for (const suffix of suffixes) {
          const match = byDevice.find((e) => (e.unique_id || '').endsWith(suffix));
          if (match) return match.entity_id;
        }
        return undefined;
      };
      const findByName = (...names) => {
        const lowered = names.map((n) => n.toLowerCase());
        const match = byDevice.find((e) => lowered.includes(String(e.original_name || e.name || '').toLowerCase()));
        return match?.entity_id;
      };
      const findByContains = (...parts) => {
        const lowered = parts.map((p) => p.toLowerCase());
        const match = byDevice.find((e) => {
          const name = String(e.original_name || e.name || '').toLowerCase();
          return lowered.every((part) => name.includes(part));
        });
        return match?.entity_id;
      };

      this._resolved = {
        mode: findByUniqueSuffix('_mode_select') || findByName('Mode de fonctionnement'),
        manual_current: findByUniqueSuffix('_manual_current') || findByName('I charge manual') || findByContains('charge', 'manual'),
        current: findByUniqueSuffix('_I_charge') || findByName('Courant de charge VE') || findByContains('courant', 'charge'),
        liaison: findByUniqueSuffix('_state_text') || findByName('État de la liaison', 'Etat de la liaison') || findByContains('liaison'),
        auto_regulation: findByUniqueSuffix('_enab') || findByName('Régulation auto VE disponible') || findByContains('régulation', 'disponible') || findByContains('regulation', 'disponible'),
        cumulative_wh: findByUniqueSuffix('_EnergieCharge_Wh') || findByName('Recharge cumulée VE') || findByContains('recharge', 'cumul'),
        charge_time: findByUniqueSuffix('_TempsCharge_ms') || findByName('Temps de charge VE') || findByContains('temps', 'charge'),
        power_kw: findByUniqueSuffix('_Puissance_charge_kW') || findByName('Puissance de charge') || findByContains('puissance', 'charge'),
        pwm: findByUniqueSuffix('_PWM') || findByUniqueSuffix('_pwm') || findByName('PWM', 'PWM borne VE') || findByContains('pwm'),
        vehicle_soc_entity: findByUniqueSuffix('_vehicle_soc_entity') || findByName('Entité SOC véhicule') || findByContains('entité', 'soc') || findByContains('entite', 'soc'),
        target_soc: findByUniqueSuffix('_target_soc') || findByName('SOC véhicule cible') || findByContains('soc', 'cible'),
        soc_limit_enabled: findByUniqueSuffix('_soc_limit_enabled') || findByName('Utiliser SOC véhicule cible') || findByContains('utiliser', 'soc'),
      };

      if (!this._resolved.mode || !this._resolved.current) {
        this._error = 'Entités RMS VE non détectées automatiquement. Passe les entités dans config.entities.';
      }
    } catch (err) {
      this._error = err?.message || String(err);
    } finally {
      this._resolving = false;
    }
  }

  _stateObj(entityId) {
    return entityId ? this.hass?.states?.[entityId] : undefined;
  }

  _state(entityId, fallback = '—') {
    const st = this._stateObj(entityId);
    if (!st || st.state === 'unknown' || st.state === 'unavailable') return fallback;
    return st.state;
  }

  _num(entityId, fallback = 0) {
    const raw = this._state(entityId, fallback);
    const n = Number(raw);
    return Number.isFinite(n) ? n : fallback;
  }

  _fmtNumber(value, digits = 1) {
    return Number(value || 0).toLocaleString('fr-FR', {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    });
  }

  _fmtBool(entityId, onLabel = 'Activée', offLabel = 'Désactivée') {
    const st = this._state(entityId, 'off');
    return st === 'on' ? onLabel : offLabel;
  }

  _statusSummary() {
    const liaison = this._state(this._resolved?.liaison, 'Inconnu');
    const current = this._num(this._resolved?.current, 0);

    // Logique UX stricte :
    // rouge fixe = déconnecté / erreur liaison
    // vert pulse = charge en cours
    // orange fixe = connecté mais en attente
    if (/défaut|defaut|fault|error|erreur|déconnect|deconnect|disconnect|offline/i.test(liaison)) {
      return {
        kind: 'fault',
        label: 'Déconnecté',
        color: 'var(--error-color, #ff4d4f)',
      };
    }

    if (/charge/i.test(liaison) || current > 0.2) {
      return {
        kind: 'charging',
        label: 'Charge en cours',
        color: 'var(--success-color, #4caf50)',
      };
    }

    return {
      kind: 'connected',
      label: /connect/i.test(liaison) ? 'Véhicule connecté' : 'En attente',
      color: 'var(--warning-color, #f5a623)',
    };
  }

  async _setMode(option) {
    const entity = this._resolved?.mode;
    if (!entity) return;
    await this.hass.callService('select', 'select_option', { entity_id: entity, option });
  }

  async _setManualCurrent(value) {
    const entity = this._resolved?.manual_current;
    if (!entity) return;
    await this.hass.callService('number', 'set_value', { entity_id: entity, value: Number(value) });
  }

  _queueManualCurrent(value) {
    this._pendingManualCurrent = Number(value);
    if (this._manualCommitTimer) clearTimeout(this._manualCommitTimer);
    this._manualCommitTimer = setTimeout(() => {
      const commitValue = this._pendingManualCurrent;
      this._setManualCurrent(commitValue).catch(() => {});
      this._manualCommitTimer = null;
    }, 120);
  }

  _displayManualCurrent(manualState) {
    if (this._pendingManualCurrent !== null && this._pendingManualCurrent !== undefined) return Number(this._pendingManualCurrent);
    return Number(manualState?.state || 0);
  }

  _syncPendingManualCurrent(manualState) {
    if (!manualState || this._pendingManualCurrent === null || this._pendingManualCurrent === undefined) return;
    const current = Number(manualState.state);
    if (Number.isFinite(current) && Math.abs(current - this._pendingManualCurrent) < 0.001) {
      this._pendingManualCurrent = null;
    }
  }

  _onSliderInput(ev) {
    this._pendingManualCurrent = Number(ev.target.value);
  }

  _onSliderChange(ev) {
    this._queueManualCurrent(Number(ev.target.value));
  }

  _commitPendingNow() {
    if (this._pendingManualCurrent === null || this._pendingManualCurrent === undefined) return;
    if (this._manualCommitTimer) clearTimeout(this._manualCommitTimer);
    const commitValue = this._pendingManualCurrent;
    this._setManualCurrent(commitValue).catch(() => {});
    this._manualCommitTimer = null;
  }

  async _stepCurrent(delta) {
    const entity = this._resolved?.manual_current;
    const state = this._stateObj(entity);
    if (!entity || !state) return;
    const current = Number(state.state);
    const min = Number(state.attributes.min ?? 1);
    const max = Number(state.attributes.max ?? 32);
    const step = Number(state.attributes.step ?? 1);
    const base = this._pendingManualCurrent ?? current;
    const next = Math.min(max, Math.max(min, base + delta * step));
    this._queueManualCurrent(next);
  }

  _vehicleSocEntityId() {
    const configuredEntity = this._state(this._resolved?.vehicle_soc_entity, '').trim();
    return configuredEntity || '';
  }

  _vehicleSocValue() {
    const entityId = this._vehicleSocEntityId();
    if (!entityId) return { label: 'Pas de véhicule connecté', value: 0, entityId: '', connected: false };
    const stateObj = this._stateObj(entityId);
    if (!stateObj || stateObj.state === 'unknown' || stateObj.state === 'unavailable') {
      return { label: 'Pas de véhicule connecté', value: 0, entityId, connected: false };
    }
    const value = Number(String(stateObj.state).replace(',', '.'));
    if (!Number.isFinite(value) || value <= 0) {
      return { label: 'Pas de véhicule connecté', value: 0, entityId, connected: false };
    }
    const unit = stateObj.attributes?.unit_of_measurement || '%';
    return { label: `${this._fmtNumber(value, 0)} ${unit}`, value, entityId, connected: true };
  }

  _displayTargetSoc(targetState) {
    if (this._pendingTargetSoc !== null && this._pendingTargetSoc !== undefined) return Number(this._pendingTargetSoc);
    return Number(targetState?.state || 80);
  }

  _syncPendingTargetSoc(targetState) {
    if (!targetState || this._pendingTargetSoc === null || this._pendingTargetSoc === undefined) return;
    const current = Number(targetState.state);
    if (Number.isFinite(current) && Math.abs(current - this._pendingTargetSoc) < 0.001) {
      this._pendingTargetSoc = null;
    }
  }

  async _setTargetSoc(value) {
    const entity = this._resolved?.target_soc;
    if (!entity) return;
    await this.hass.callService('number', 'set_value', { entity_id: entity, value: Number(value) });
  }

  _onTargetSocInput(ev) {
    this._pendingTargetSoc = Number(ev.target.value);
  }

  _onTargetSocChange(ev) {
    const value = Number(ev.target.value);
    this._pendingTargetSoc = value;
    this._setTargetSoc(value).catch(() => {});
  }

  async _setSocLimitEnabled(enabled) {
    const entity = this._resolved?.soc_limit_enabled;
    if (!entity) return;
    await this.hass.callService('switch', enabled ? 'turn_on' : 'turn_off', { entity_id: entity });
  }

  _showMoreInfo(entityId) {
    if (!entityId) return;
    fireEvent(this, 'hass-more-info', { entityId });
  }


  _defaultInfoItems() {
    const base = [
      { type: 'power' },
      { type: 'energy' },
      { type: 'charge_time' },
      { type: 'current' },
    ];
    const extras = [];
    if (this._config.external_entity) {
      extras.push({
        type: 'external',
        entity: this._config.external_entity,
        name: this._config.external_entity_name || '',
        icon: this._config.external_entity_icon || 'mdi:plus-circle-outline',
      });
    }
    for (const item of (this._config.external_items || [])) {
      if (item?.entity) extras.push({
        type: 'external',
        entity: item.entity,
        name: item.name || '',
        icon: item.icon || 'mdi:plus-circle-outline',
      });
    }
    return [...base, ...extras];
  }

  _builtinInfoDefinition(type, current) {
    const defs = {
      power: ['mdi:flash', 'Puissance', `${this._fmtNumber(this._num(this._resolved.power_kw, 0), 1)} kW`, '#f6c453', this._resolved.power_kw],
      energy: ['mdi:battery-charging', 'Énergie', `${Math.round(this._num(this._resolved.cumulative_wh, 0)).toLocaleString('fr-FR')} Wh`, '#b37cff', this._resolved.cumulative_wh],
      charge_time: ['mdi:timer-outline', 'Temps de charge', this._state(this._resolved.charge_time), '#9ccc57', this._resolved.charge_time],
      current: ['mdi:sine-wave', 'Courant VE', `${this._fmtNumber(current, 1)} A`, '#4aa3ff', this._resolved.current],
      pwm: ['mdi:percent-outline', 'PWM', this._resolved.pwm ? this._state(this._resolved.pwm) : '—', '#00bcd4', this._resolved.pwm],
      auto_regulation: ['mdi:sync-circle', 'Régulation auto VE', this._resolved.auto_regulation ? this._state(this._resolved.auto_regulation) : '—', '#4aa3ff', this._resolved.auto_regulation],
    };
    return defs[type] || null;
  }

  _resolveInfoItems(current) {
    const configured = (this._config.info_items && this._config.info_items.length)
      ? this._config.info_items
      : this._defaultInfoItems();

    const out = [];
    for (const item of configured) {
      if (!item?.type) continue;

      if (item.type === 'external') {
        if (!item.entity) continue;
        const externalStateObj = this._stateObj(item.entity);
        if (!externalStateObj) continue;
        const extName = item.name || externalStateObj.attributes.friendly_name || item.entity;
        const unit = externalStateObj.attributes.unit_of_measurement ? ` ${externalStateObj.attributes.unit_of_measurement}` : '';
        out.push([
          item.icon || 'mdi:plus-circle-outline',
          extName,
          `${externalStateObj.state}${unit}`,
          'var(--primary-color)',
          item.entity,
        ]);
        continue;
      }

      const builtIn = this._builtinInfoDefinition(item.type, current);
      if (builtIn) out.push(builtIn);
    }
    return out;
  }

  render() {
    if (!this.hass) return html``;
    if (this._error) {
      return html`<ha-card header="RMS VE"><div class="error">${this._error}</div></ha-card>`;
    }
    if (!this._resolved) {
      return html`<ha-card header="RMS VE"><div class="hint">Chargement des entités RMS VE…</div></ha-card>`;
    }

    const status = this._statusSummary();
    const mode = this._state(this._resolved.mode, '—');
    const currentState = this._stateObj(this._resolved.current);
    const current = Number(currentState?.state || 0);
    const manualState = this._stateObj(this._resolved.manual_current);
    this._syncPendingManualCurrent(manualState);
    const manualValue = this._displayManualCurrent(manualState);
    const targetSocState = this._stateObj(this._resolved?.target_soc);
    this._syncPendingTargetSoc(targetSocState);
    const targetSocValue = this._displayTargetSoc(targetSocState);
    const targetSocMin = Number(targetSocState?.attributes?.min ?? 20);
    const targetSocMax = Number(targetSocState?.attributes?.max ?? 100);
    const socLimitState = this._stateObj(this._resolved?.soc_limit_enabled);
    const socLimitEnabled = socLimitState?.state === 'on';
    const vehicleSoc = this._vehicleSocValue();
    const manualMin = Number(manualState?.attributes?.min ?? 1);
    const manualMax = Number(manualState?.attributes?.max ?? 32);
    const gaugePercent = manualMax > 0 ? Math.max(0, Math.min(100, (current / manualMax) * 100)) : 0;
    const arcLength = 282.7433388230814;
    const dash = (gaugePercent / 100) * arcLength;

    const infoMetrics = this._resolveInfoItems(current);

    return html`
      <ha-card>
        <div class="stack ${this._config.compact_mode !== false ? 'compact' : 'spacious'}">
          ${(this._config.show_title !== false && this._config.show_title !== 'false') ? html`<div class="card-title">${this._config.title || 'RMS VE'}</div>` : ''}
          <div class="mode-panel">
            <div class="mode-grid" style="display:flex;flex-direction:row;flex-wrap:nowrap;width:100%;">
              ${this._modeButton('Arrêt', 'mdi:stop-circle', mode)}
              ${this._modeButton('Auto', 'mdi:flash', mode)}
              ${this._modeButton('Semi-auto', 'mdi:sync', mode)}
              ${this._modeButton('Manuel', 'mdi:hand-back-right', mode)}
            </div>
          </div>

          <div class="status ${status.kind}">
            <div class="status-main">
              <div class="status-badge ${status.kind}" style="background:${status.color}"></div>
              <div>
                <div class="status-text">${status.label}</div>
                ${this._config.show_manual_current ? html`
                  <div
                    class="status-manual-line clickable"
                    title="Modifier le reglage manuel"
                    @click=${() => this._showMoreInfo(this._resolved.manual_current)}
                  >
                    <span>Réglage manuel</span>
                    <strong>${this._fmtNumber(manualValue, 0)} A</strong>
                  </div>
                ` : ''}
              </div>
            </div>
            <div
              class="status-mini-gauge clickable"
              aria-label="Courant VE"
              title="Afficher l'historique du courant"
              @click=${() => this._showMoreInfo(this._resolved.current)}
            >
              <div class="status-mini-semi">
                <svg viewBox="0 0 240 140" aria-hidden="true">
                  <defs>
                    <linearGradient id="rmsveGaugeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                      <stop offset="0%" stop-color="#4fc3f7"></stop>
                      <stop offset="55%" stop-color="#42a5f5"></stop>
                      <stop offset="100%" stop-color="#66bb6a"></stop>
                    </linearGradient>
                  </defs>
                  <path class="status-mini-track" d="M 30 120 A 90 90 0 0 1 210 120" fill="none" stroke="rgba(127,127,127,0.20)" stroke-width="16" stroke-linecap="round"></path>
                  <path class="status-mini-progress" d="M 30 120 A 90 90 0 0 1 210 120" fill="none" stroke="url(#rmsveGaugeGradient)" stroke-width="16" stroke-linecap="round" stroke-dasharray="${dash} ${arcLength}"></path>
                </svg>
                <div class="status-mini-value"><span class="status-mini-value-main">${this._fmtNumber(current, 1)}</span><span class="status-mini-value-unit">A</span></div>
              </div>
            </div>
          </div>

          ${this._config.show_vehicle_soc_section !== false && this._config.show_vehicle_soc_section !== 'false' ? html`
            <div class="soc-panel">
              <div class="soc-grid">
                <div class="soc-tile clickable" @click=${() => this._showMoreInfo(this._resolved?.target_soc)}>
                  <div class="soc-tile-label"><ha-icon icon="mdi:target"></ha-icon><span>SOC cible</span></div>
                  <div class="soc-tile-value">${this._fmtNumber(targetSocValue, 0)} %</div>
                </div>
                <div class="soc-tile ${vehicleSoc.connected ? 'clickable' : ''}" @click=${() => vehicleSoc.connected ? this._showMoreInfo(vehicleSoc.entityId) : null}>
                  <div class="soc-tile-label"><ha-icon icon="mdi:car-electric"></ha-icon><span>SOC véhicule</span></div>
                  ${vehicleSoc.connected ? html`
                    <div class="soc-tile-value">${vehicleSoc.label}</div>
                  ` : html`
                    <div class="soc-tile-value disconnected"><ha-icon icon="mdi:power-plug-off"></ha-icon><span>Non connecté</span></div>
                  `}
                </div>
              </div>
              <div class="soc-switch-row">
                <span>Utiliser le SOC cible</span>
                <ha-switch
                  .checked=${socLimitEnabled}
                  ?disabled=${!this._resolved?.soc_limit_enabled}
                  @change=${(ev) => this._setSocLimitEnabled(Boolean(ev.target.checked))}
                ></ha-switch>
              </div>
            </div>
          ` : ''}

          ${this._config.show_gauge ? html`
            <div class="panel">
              <div class="gauge-wrap">
                <div class="gauge">
                  <svg viewBox="0 0 240 140" aria-hidden="true">
                    <path d="M 30 120 A 90 90 0 0 1 210 120" fill="none" stroke="rgba(127,127,127,0.18)" stroke-width="22" stroke-linecap="round"></path>
                    <path d="M 30 120 A 90 90 0 0 1 210 120" fill="none" stroke="var(--primary-color)" stroke-width="22" stroke-linecap="round" stroke-dasharray="${dash} ${arcLength}"></path>
                  </svg>
                  <div class="gauge-value">${this._fmtNumber(current, 1)} A</div>
                </div>
                <div class="gauge-minmax"><span>0</span><span>${manualMax}</span></div>
                <div class="gauge-label">Courant de charge VE</div>
              </div>
            </div>
          ` : ''}

          ${this._config.show_infos && infoMetrics.length ? html`
            <div class="metrics-card">
              <div class="metrics-grid">
                ${infoMetrics.map(([icon, name, value, color, entity]) => html`
                  <div
                    class="metric-item clickable"
                    @click=${() => this._showMoreInfo(entity)}
                    title="Afficher l'historique"
                  >
                    <ha-icon class="metric-icon" style="color:${color}" .icon=${icon}></ha-icon>
                    <div class="metric-body">
                      <div class="metric-name">${name}</div>
                      <div class="metric-value">${value}</div>
                    </div>
                  </div>
                `)}
              </div>
            </div>
          ` : ''}

          <div class="footer">
            <span>Carte RMS VE V0.7.0</span>
          </div>
        </div>
      </ha-card>
    `;
  }

  _modeButton(label, icon, currentMode) {
    const active = currentMode === label;
    const modeClass = label === 'Arrêt'
      ? 'mode-stop'
      : label === 'Auto'
        ? 'mode-auto'
        : label === 'Semi-auto'
          ? 'mode-semi'
          : 'mode-manual';
    return html`
      <button class="mode-btn ${modeClass} ${active ? 'active' : ''}" @click=${() => this._setMode(label)}>
        <ha-icon class="mode-icon" .icon=${icon}></ha-icon>
        <div>${label}</div>
      </button>
    `;
  }
  disconnectedCallback() {
    if (super.disconnectedCallback) super.disconnectedCallback();
    if (this._manualCommitTimer) clearTimeout(this._manualCommitTimer);
  }
}

customElements.define('rms-ve-card-editor', RMSVECardEditor);
customElements.define('rms-ve-card', RMSVECard);
window.customCards = window.customCards || [];
window.customCards.push({
  type: 'rms-ve-card',
  name: 'RMS VE Card',
  description: 'Carte RMS VE avec éditeur visuel, sélection du device et pilotage intégré.',
  preview: true,
});
