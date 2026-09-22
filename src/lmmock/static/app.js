const $ = (id) => document.getElementById(id);
function savedLanguage() {
  try { return localStorage.getItem('lmmock-language') === 'zh' ? 'zh' : 'en'; }
  catch (_) { return 'en'; }
}
const state = {
  rules: [], groups: [], settings: null, activeRuleId: null, activeGroupId: null,
  language: savedLanguage(),
};
let toastTimer;

const messages = {
  en: {
    heroTitle: 'Shape the model response.', heroCopy: 'Create deterministic replies for OpenAI, Anthropic, and Gemini clients, then test the same application code without a model call.', copy: 'Copy', apiKey: 'API key',
    rules: 'Rules', rulesHelp: 'Rules are isolated inside behavior groups.', newRule: 'New rule', behaviorGroup: 'Behavior group', newGroup: 'New group', startTemplate: 'Start from a template', templateHelp: 'Choose one, adjust it, then save.', savedRules: 'Saved rules', editorHelp: 'Match a request and return a fixed result.', enabled: 'Enabled',
    name: 'Name', description: 'Description', namePlaceholder: 'Weather reply', ruleModels: 'Models', modelPatternPlaceholder: '* or gpt-*, deepseek-chat', scope: 'Scope', allEndpoints: 'All endpoints', priority: 'Priority', match: 'Match', everyRequest: 'Every request', contains: 'Contains', regex: 'Regex', text: 'Text', reply: 'Reply', jsonText: 'JSON text', randomData: 'Random data', randomSize: 'Data size (bytes)', randomHelp: 'Generates exact-size random ASCII data, up to 10 MB.', toolCall: 'Tool call', httpError: 'HTTP error', delay: 'Delay (ms)', content: 'Content', captureHelp: 'Regex captures can be inserted as ${city} or ${1}.', toolName: 'Tool name', arguments: 'Arguments (JSON)', status: 'Status', errorMessage: 'Error message', saveRule: 'Save rule', saveGroup: 'Save group', delete: 'Delete',
    playgroundHelp: 'Send one request through the selected model and its behavior groups.', endpoint: 'Endpoint', model: 'Model', input: 'Input', sendRequest: 'Send request', requestPreview: 'Request', responsePreview: 'Response', noRequestYet: 'No request yet.', recentRequests: 'Recent requests', recentHelp: 'Select one to inspect its request and response.', clear: 'Clear', configuration: 'CONFIGURATION', modelsInterfacesSecurity: 'Models, interfaces & API keys', configurationHelp: 'Each model owns its interface, key, and behavior groups.', configuredModels: 'Configured models', configuredModelsHelp: 'Keep the names already used by your application. Assign at least one behavior group to each model.', addModel: 'Add model', removeModel: 'Remove model', interfaceFormat: 'Interface', behaviorGroups: 'Behavior groups', apiKeyPlaceholder: 'Blank accepts any key', saveSettings: 'Save settings', requestDetail: 'REQUEST DETAIL', request: 'Request', response: 'Response',
    editRule: 'Edit rule', createGroup: 'Create behavior group', editGroup: 'Edit behavior group', noRules: 'No rules in this group yet. Pick a template or create a rule.', noRequests: 'Requests will appear here after your app or the Playground calls LMMock.', noMatch: 'No match', emptyInput: 'Empty input', ruleUpdated: 'Rule updated', ruleCreated: 'Rule created', invalidArguments: 'Tool arguments must be valid JSON', deleteConfirm: 'Delete this rule?', ruleDeleted: 'Rule deleted', groupCreated: 'Behavior group created', groupUpdated: 'Behavior group updated', groupDeleted: 'Behavior group deleted', groupDeleteConfirm: 'Delete this behavior group?', settingsSaved: 'Configuration saved', requestFailed: 'request failed', listCleared: 'Requests and token statistics cleared', copied: 'Base URL copied', templateLoaded: 'Template loaded — review it and save the rule.', estimatedUsage: 'Estimated token usage', totalRequests: 'Requests', inputTokens: 'Input tokens', outputTokens: 'Output tokens', totalTokens: 'Total tokens', byModel: 'By model',
    templateSimple: 'Simple text', templateSimpleHelp: 'Reply to a matching phrase.', templateRegex: 'Regex variables', templateRegexHelp: 'Reuse captured text in the reply.', templateFool: 'foolAI', templateFoolHelp: 'Turn a Chinese question into a confident first-person statement.', templateJson: 'JSON result', templateJsonHelp: 'Return structured JSON text.', templateRandom: 'Large random data', templateRandomHelp: 'Generate an exact-size random payload.', templateTool: 'Tool call', templateToolHelp: 'Ask the client to call a function.', templateRate: 'Rate limit', templateRateHelp: 'Test provider error handling.', templateSlow: 'Slow reply', templateSlowHelp: 'Test loading and timeout states.'
  },
  zh: {
    heroTitle: '定义你的模型回复。', heroCopy: '为 OpenAI、Anthropic 和 Gemini 客户端创建稳定可复现的回复，无需调用真实模型即可测试同一套应用代码。', copy: '复制', apiKey: 'API 密钥',
    rules: '规则', rulesHelp: '不同的行为组拥有相互隔离的规则。', newRule: '新建规则', behaviorGroup: '行为组', newGroup: '新建组', startTemplate: '从模板开始', templateHelp: '选择模板，按需修改，然后保存。', savedRules: '已保存规则', editorHelp: '匹配请求并返回固定结果。', enabled: '启用',
    name: '名称', description: '描述', namePlaceholder: '天气回复', ruleModels: '适用模型', modelPatternPlaceholder: '* 或 gpt-*、deepseek-chat', scope: '接口范围', allEndpoints: '全部接口', priority: '优先级', match: '匹配方式', everyRequest: '所有请求', contains: '包含文本', regex: '正则表达式', text: '文本', reply: '回复类型', jsonText: 'JSON 文本', randomData: '随机数据', randomSize: '数据大小（字节）', randomHelp: '生成指定大小的随机 ASCII 数据，最大 10 MB。', toolCall: '工具调用', httpError: 'HTTP 错误', delay: '延迟（毫秒）', content: '回复内容', captureHelp: '正则捕获内容可通过 ${city} 或 ${1} 插入回复。', toolName: '工具名称', arguments: '参数（JSON）', status: '状态码', errorMessage: '错误信息', saveRule: '保存规则', saveGroup: '保存行为组', delete: '删除',
    playgroundHelp: '使用选定模型及其绑定的行为组发送请求。', endpoint: '接口', model: '模型', input: '输入', sendRequest: '发送请求', requestPreview: '请求', responsePreview: '响应', noRequestYet: '还没有发送请求。', recentRequests: '最近请求', recentHelp: '点击任意请求查看请求体和响应体。', clear: '清空', configuration: '配置', modelsInterfacesSecurity: '模型、接口与 API 密钥', configurationHelp: '每个模型独立拥有接口格式、API Key 和行为组。', configuredModels: '已配置模型', configuredModelsHelp: '保留应用正在使用的模型名，并为每个模型至少绑定一个行为组。', addModel: '添加模型', removeModel: '删除模型', interfaceFormat: '接口格式', behaviorGroups: '行为组', apiKeyPlaceholder: '留空表示接受任意 Key', saveSettings: '保存配置', requestDetail: '请求详情', request: '请求', response: '响应',
    editRule: '编辑规则', createGroup: '新建行为组', editGroup: '编辑行为组', noRules: '这个行为组还没有规则。可以选择模板或新建规则。', noRequests: '你的应用或 Playground 调用 LMMock 后，请求会显示在这里。', noMatch: '未匹配', emptyInput: '空输入', ruleUpdated: '规则已更新', ruleCreated: '规则已创建', invalidArguments: '工具参数必须是有效的 JSON', deleteConfirm: '确定删除这条规则吗？', ruleDeleted: '规则已删除', groupCreated: '行为组已创建', groupUpdated: '行为组已更新', groupDeleted: '行为组已删除', groupDeleteConfirm: '确定删除这个行为组吗？', settingsSaved: '配置已保存', requestFailed: '请求失败', listCleared: '请求与 Token 统计已清空', copied: '基础 URL 已复制', templateLoaded: '模板已载入，请检查并保存规则。', estimatedUsage: 'Token 使用量（估算）', totalRequests: '请求数', inputTokens: '输入 Token', outputTokens: '输出 Token', totalTokens: '总 Token', byModel: '按模型',
    templateSimple: '简单文本', templateSimpleHelp: '命中指定短语后返回文本。', templateRegex: '正则变量', templateRegexHelp: '把捕获的内容复用到回复中。', templateFool: 'foolAI', templateFoolHelp: '把中文疑问句变成自信的第一人称肯定句。', templateJson: 'JSON 结果', templateJsonHelp: '返回结构化 JSON 文本。', templateRandom: '大体积随机数据', templateRandomHelp: '生成精确指定大小的随机数据。', templateTool: '工具调用', templateToolHelp: '让客户端调用指定函数。', templateRate: '限流错误', templateRateHelp: '测试应用的错误处理。', templateSlow: '慢速回复', templateSlowHelp: '测试加载和超时状态。'
  },
};

const templates = [
  { icon: 'Aa', name: 'templateSimple', help: 'templateSimpleHelp', rule: { name: 'Hello reply', priority: 10, scopes: ['*'], match_type: 'contains', match_value: 'hello', reply_type: 'text', reply: { content: 'Hello from LMMock!' }, delay_ms: 0 } },
  { icon: '(.*)', name: 'templateRegex', help: 'templateRegexHelp', rule: { name: 'Weather by city', priority: 20, scopes: ['*'], match_type: 'regex', match_value: 'weather in (?P<city>.+)', reply_type: 'text', reply: { content: 'Weather in ${city}: sunny.' }, delay_ms: 0 } },
  { icon: '?!', name: 'templateFool', help: 'templateFoolHelp', rule: { name: 'foolAI', priority: 100, scopes: ['*'], match_type: 'regex', match_value: '(?:^|\\n)(?:user:\\s*)?(?P<question>[^\\n]+?)(?:[?？]+|[吗么嘛呢])(?:[\\"\'”’])?\\s*$', reply_type: 'text', reply: { content: '${question|foolAI}' }, delay_ms: 0 } },
  { icon: '{}', name: 'templateJson', help: 'templateJsonHelp', rule: { name: 'Classification JSON', priority: 30, scopes: ['*'], match_type: 'contains', match_value: 'classify', reply_type: 'json', reply: { content: '{\n  "category": "support",\n  "confidence": 0.98\n}' }, delay_ms: 0 } },
  { icon: '1M', name: 'templateRandom', help: 'templateRandomHelp', rule: { name: '1 MB random payload', priority: 35, scopes: ['*'], match_type: 'contains', match_value: 'large payload', reply_type: 'random', reply: { size: 1048576 }, delay_ms: 0 } },
  { icon: 'ƒ', name: 'templateTool', help: 'templateToolHelp', rule: { name: 'Weather tool', priority: 40, scopes: ['*'], match_type: 'contains', match_value: 'use weather tool', reply_type: 'tool', reply: { tool_name: 'get_weather', arguments: { city: 'Shanghai' } }, delay_ms: 0 } },
  { icon: '429', name: 'templateRate', help: 'templateRateHelp', rule: { name: 'Rate limit error', priority: 50, scopes: ['*'], match_type: 'contains', match_value: 'rate limit', reply_type: 'error', reply: { status_code: 429, message: 'Rate limit exceeded' }, delay_ms: 0 } },
  { icon: '…', name: 'templateSlow', help: 'templateSlowHelp', rule: { name: 'Slow response', priority: 60, scopes: ['*'], match_type: 'contains', match_value: 'slow', reply_type: 'text', reply: { content: 'This response arrived after a delay.' }, delay_ms: 1500 } },
];

function t(key, values = {}) {
  let text = messages[state.language][key] || messages.en[key] || key;
  for (const [name, value] of Object.entries(values)) text = text.replace(`{${name}}`, value);
  return text;
}

function modelHeaders(model) {
  const config = state.settings?.model_configs.find((item) => item.name === model);
  if (!config?.api_key) return {};
  if (config.protocol === 'gemini') return { 'x-goog-api-key': config.api_key };
  return config.protocol === 'anthropic' ? { 'x-api-key': config.api_key } : { authorization: `Bearer ${config.api_key}` };
}

async function api(path, options = {}) {
  const response = await fetch(`/__lmmock/api${path}`, { ...options, headers: { 'content-type': 'application/json', ...(options.headers || {}) } });
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try {
      const data = await response.json();
      message = typeof data.error === 'string' ? data.error : data.error?.message || message;
    } catch (_) { /* keep status */ }
    const error = new Error(message); error.status = response.status; throw error;
  }
  return response.status === 204 ? null : response.json();
}

function toast(message) {
  clearTimeout(toastTimer); $('toast').textContent = message; $('toast').classList.add('show');
  toastTimer = setTimeout(() => $('toast').classList.remove('show'), 2400);
}

function applyLanguage() {
  document.documentElement.lang = state.language === 'zh' ? 'zh-CN' : 'en';
  document.querySelectorAll('[data-i18n]').forEach((node) => { node.textContent = t(node.dataset.i18n); });
  document.querySelectorAll('[data-i18n-placeholder]').forEach((node) => { node.placeholder = t(node.dataset.i18nPlaceholder); });
  $('language-toggle').textContent = state.language === 'en' ? 'EN' : 'ZH';
  $('language-toggle').setAttribute('aria-label', state.language === 'en' ? '切换到中文' : 'Switch to English');
  $('editor-title').textContent = state.activeRuleId ? t('editRule') : t('newRule');
  if (!$('playground-meta').textContent) $('playground-output').textContent = t('noRequestYet');
  renderTemplates(); renderRules();
}

function updateFields() {
  $('match-wrap').classList.toggle('hidden', $('match-type').value === 'all');
  const type = $('reply-type').value;
  $('content-wrap').classList.toggle('hidden', type === 'tool' || type === 'error' || type === 'random');
  $('random-wrap').classList.toggle('hidden', type !== 'random');
  $('tool-wrap').classList.toggle('hidden', type !== 'tool');
  $('error-wrap').classList.toggle('hidden', type !== 'error');
}

function fillGroupSelect(select, selected) {
  select.replaceChildren();
  for (const group of state.groups) {
    const option = document.createElement('option'); option.value = group.id; option.textContent = group.name; option.selected = Number(selected) === group.id; select.append(option);
  }
}

function renderGroups() {
  fillGroupSelect($('group-select'), state.activeGroupId);
  fillGroupSelect($('rule-group'), state.activeGroupId);
}

function setForm(rule = null) {
  state.activeRuleId = rule?.id || null; $('rule-id').value = rule?.id || ''; $('editor-title').textContent = rule?.id ? t('editRule') : t('newRule');
  $('name').value = rule?.name || ''; $('enabled').checked = rule?.enabled ?? true; $('priority').value = rule?.priority || 100; $('model-pattern').value = rule?.model_pattern || '*'; $('scope').value = rule?.scopes?.[0] || '*';
  $('rule-group').value = rule?.group_id || state.activeGroupId; $('match-type').value = rule?.match_type || 'all'; $('match-value').value = rule?.match_value || ''; $('reply-type').value = rule?.reply_type || 'text'; $('delay').value = rule?.delay_ms || 0;
  $('content').value = rule?.reply?.content || ''; $('tool-name').value = rule?.reply?.tool_name || ''; $('arguments').value = JSON.stringify(rule?.reply?.arguments || { city: 'Shanghai' }, null, 2);
  $('random-size').value = rule?.reply?.size ?? 4096; $('error-status').value = rule?.reply?.status_code || 500; $('error-message').value = rule?.reply?.message || 'Mock error'; $('delete-rule').classList.toggle('hidden', !rule?.id);
  updateFields(); renderRules();
}

function renderTemplates() {
  const node = $('templates'); node.replaceChildren();
  for (const template of templates) {
    const button = document.createElement('button'); button.type = 'button'; button.className = 'template-card';
    const icon = document.createElement('b'); icon.textContent = template.icon;
    const copy = document.createElement('span'); const name = document.createElement('strong'); name.textContent = t(template.name); const help = document.createElement('small'); help.textContent = t(template.help);
    copy.append(name, help); button.append(icon, copy);
    button.addEventListener('click', () => { setForm({ ...structuredClone(template.rule), enabled: true, group_id: state.activeGroupId }); toast(t('templateLoaded')); }); node.append(button);
  }
}

function renderRules() {
  const node = $('rules'); node.replaceChildren();
  if (!state.rules.length) { const empty = document.createElement('div'); empty.className = 'empty'; empty.textContent = t('noRules'); node.append(empty); return; }
  for (const rule of state.rules) {
    const button = document.createElement('button'); button.type = 'button'; button.className = `rule${rule.enabled ? '' : ' off'}${rule.id === state.activeRuleId ? ' active' : ''}`;
    const name = document.createElement('span'); name.className = 'rule-name'; name.textContent = rule.name;
    const priority = document.createElement('span'); priority.className = 'rule-priority'; priority.textContent = `#${rule.priority}`;
    const meta = document.createElement('span'); meta.className = 'rule-meta'; meta.textContent = `${rule.reply_type} · ${rule.model_pattern || '*'} · ${rule.scopes.join(', ')} · ${rule.match_type}${rule.delay_ms ? ` · ${rule.delay_ms}ms` : ''}`;
    button.append(name, priority, meta); button.addEventListener('click', () => setForm(rule)); node.append(button);
  }
}

async function loadRules() { state.rules = await api(`/rules?group_id=${state.activeGroupId}`); renderRules(); }

function readModelConfigs() {
  return [...document.querySelectorAll('.model-config')].map((card) => ({
    name: card.querySelector('.model-name').value.trim(),
    protocol: card.querySelector('.model-protocol').value,
    api_key: card.querySelector('.model-api-key').value,
    group_ids: [...card.querySelectorAll('.model-group:checked')].map((input) => Number(input.value)),
  }));
}

function syncModelOptions(selected) {
  const configs = readModelConfigs();
  const models = configs.map((config) => config.name).filter(Boolean);
  const select = $('playground-model'); const current = select.value || selected || models[0];
  select.replaceChildren();
  for (const model of models) { const option = document.createElement('option'); option.value = model; option.textContent = model; option.selected = model === current; select.append(option); }
  syncPlaygroundProtocol();
}

function syncPlaygroundProtocol() {
  const config = readModelConfigs().find((item) => item.name === $('playground-model').value);
  const endpoints = { openai: ['chat', 'completions', 'responses'], anthropic: ['messages'], gemini: ['generateContent'] };
  const allowed = endpoints[config?.protocol || 'openai'];
  for (const option of $('playground-endpoint').options) option.disabled = !allowed.includes(option.value);
  if ($('playground-endpoint').selectedOptions[0]?.disabled) $('playground-endpoint').value = allowed[0];
  renderPlaygroundRequest();
}

function addModelConfig(config = {}) {
  const card = document.createElement('div'); card.className = 'model-config';
  const field = (key, control) => { const label = document.createElement('label'); const text = document.createElement('span'); text.dataset.i18n = key; text.textContent = t(key); label.append(text, control); return label; };
  const name = document.createElement('input'); name.className = 'model-name'; name.required = true; name.maxLength = 120; name.value = config.name || '';
  const protocol = document.createElement('select'); protocol.className = 'model-protocol';
  for (const [value, label] of [['openai', 'OpenAI-compatible'], ['anthropic', 'Anthropic'], ['gemini', 'Gemini']]) { const option = document.createElement('option'); option.value = value; option.textContent = label; option.selected = value === (config.protocol || 'openai'); protocol.append(option); }
  const key = document.createElement('input'); key.className = 'model-api-key'; key.type = 'text'; key.autocomplete = 'off'; key.value = config.api_key || ''; key.placeholder = t('apiKeyPlaceholder'); key.dataset.i18nPlaceholder = 'apiKeyPlaceholder';
  const groupsWrap = document.createElement('label'); groupsWrap.className = 'model-groups-wrap'; const groupsTitle = document.createElement('span'); groupsTitle.dataset.i18n = 'behaviorGroups'; groupsTitle.textContent = t('behaviorGroups'); const groups = document.createElement('div'); groups.className = 'model-groups';
  for (const group of state.groups) { const optionLabel = document.createElement('label'); const checkbox = document.createElement('input'); checkbox.type = 'checkbox'; checkbox.className = 'model-group'; checkbox.value = group.id; checkbox.checked = (config.group_ids || [state.activeGroupId || state.groups[0]?.id]).includes(group.id); optionLabel.append(checkbox, document.createTextNode(group.name)); groups.append(optionLabel); }
  groupsWrap.append(groupsTitle, groups);
  const remove = document.createElement('button'); remove.type = 'button'; remove.className = 'icon-button remove-model'; remove.textContent = '×'; remove.title = t('removeModel');
  remove.addEventListener('click', () => { card.remove(); syncModelOptions(); });
  for (const control of [name, protocol, key]) control.addEventListener('input', () => syncModelOptions());
  card.append(field('model', name), field('interfaceFormat', protocol), field('apiKey', key), groupsWrap, remove);
  $('model-configs').append(card);
  syncModelOptions(config.name);
}

function renderModelConfigs(configs) {
  $('model-configs').replaceChildren();
  for (const config of configs) addModelConfig(config);
}

async function loadSettings() {
  const settings = await api('/settings'); state.settings = settings;
  state.activeGroupId = state.activeGroupId || settings.active_group_id;
  renderModelConfigs(settings.model_configs); syncModelOptions(settings.model_configs[0]?.name);
}

function openRequest(request) {
  $('request-dialog-title').textContent = `${request.provider} · ${request.operation} · ${request.group || ''} · ${request.status}`;
  $('request-detail').textContent = JSON.stringify(request.request ?? {}, null, 2); $('response-detail').textContent = JSON.stringify(request.response ?? {}, null, 2); $('request-dialog').showModal();
}

function renderRequests(requests) {
  const node = $('requests'); node.replaceChildren();
  if (!requests.length) { const empty = document.createElement('div'); empty.className = 'empty'; empty.textContent = t('noRequests'); node.append(empty); return; }
  for (const request of requests) {
    const row = document.createElement('button'); row.type = 'button'; row.className = 'request';
    const provider = document.createElement('span'); provider.className = 'request-provider'; provider.textContent = request.provider;
    const main = document.createElement('span'); main.className = 'request-main'; const title = document.createElement('strong'); title.textContent = `${request.operation} · ${request.group || ''} · ${request.rule || t('noMatch')}`;
    const input = document.createElement('small'); input.textContent = request.input || t('emptyInput'); main.append(title, input);
    const timing = document.createElement('span'); timing.className = 'request-time'; timing.textContent = `${request.status} · ${request.duration_ms}ms · ${request.usage?.total_tokens ?? 0} tok  ›`;
    row.append(provider, main, timing); row.addEventListener('click', () => openRequest(request)); node.append(row);
  }
}

function formatNumber(value) { return new Intl.NumberFormat(state.language === 'zh' ? 'zh-CN' : 'en-US').format(value || 0); }

function renderStats(stats) {
  const node = $('token-stats'); node.replaceChildren();
  const values = [
    ['estimatedUsage', '≈'],
    ['totalRequests', stats.requests],
    ['inputTokens', stats.input_tokens],
    ['outputTokens', stats.output_tokens],
    ['totalTokens', stats.total_tokens],
  ];
  for (const [label, value] of values) {
    const card = document.createElement('div'); const name = document.createElement('small'); const amount = document.createElement('strong');
    name.textContent = t(label); amount.textContent = typeof value === 'number' ? formatNumber(value) : value; card.append(name, amount); node.append(card);
  }
  const models = $('model-token-stats'); models.replaceChildren();
  for (const [model, usage] of Object.entries(stats.by_model || {})) {
    const row = document.createElement('span'); row.textContent = `${model} · ${formatNumber(usage.total_tokens)} tok · ${formatNumber(usage.requests)} req`; models.append(row);
  }
}

async function loadRequests() {
  const [requests, stats] = await Promise.all([api('/requests'), api('/stats')]);
  renderRequests(requests); renderStats(stats);
}

function buildPlaygroundRequest() {
  const endpoint = $('playground-endpoint').value;
  const input = $('playground-input').value;
  const model = $('playground-model').value;
  const body = endpoint === 'chat'
    ? { model, messages: [{ role: 'user', content: input }] }
    : endpoint === 'completions'
      ? { model, prompt: input }
      : endpoint === 'responses'
        ? { model, input }
        : endpoint === 'generateContent'
          ? { contents: [{ role: 'user', parts: [{ text: input }] }] }
          : { model, max_tokens: 128, messages: [{ role: 'user', content: input }] };
  const paths = { chat: '/openai/v1/chat/completions', completions: '/openai/v1/completions', responses: '/openai/v1/responses', messages: '/anthropic/v1/messages', generateContent: `/gemini/v1beta/models/${encodeURIComponent(model)}:generateContent` };
  const headers = { 'content-type': 'application/json', ...modelHeaders(model) };
  const config = state.settings?.model_configs.find((item) => item.name === model);
  const behaviorGroups = state.groups.filter((group) => config?.group_ids.includes(group.id)).map((group) => group.name);
  return { path: paths[endpoint], body, preview: { method: 'POST', url: `${location.origin}${paths[endpoint]}`, headers, behavior_groups: behaviorGroups, body } };
}

function renderPlaygroundRequest() {
  const preview = JSON.stringify(buildPlaygroundRequest().preview, null, 2);
  if ($('playground-request').textContent !== preview) {
    $('playground-output').textContent = t('noRequestYet');
    $('playground-meta').textContent = '';
  }
  $('playground-request').textContent = preview;
}

async function initialize() {
  try {
    state.groups = await api('/groups'); await loadSettings();
    if (!state.groups.some((group) => group.id === state.activeGroupId)) state.activeGroupId = state.groups[0].id;
    renderGroups(); renderPlaygroundRequest(); await Promise.all([loadRules(), loadRequests()]);
  } catch (error) { toast(error.message); }
}

$('language-toggle').addEventListener('click', () => {
  state.language = state.language === 'en' ? 'zh' : 'en';
  try { localStorage.setItem('lmmock-language', state.language); } catch (_) { /* Storage may be disabled. */ }
  applyLanguage(); loadRequests().catch(() => {});
});
$('add-model').addEventListener('click', () => addModelConfig({ protocol: 'openai', group_ids: [state.activeGroupId] }));

$('group-select').addEventListener('change', async () => {
  state.activeGroupId = Number($('group-select').value); state.activeRuleId = null; renderGroups(); renderPlaygroundRequest(); setForm();
  try { await api('/settings', { method: 'PUT', body: JSON.stringify({ active_group_id: state.activeGroupId }) }); await loadRules(); } catch (error) { toast(error.message); }
});
$('new-group').addEventListener('click', () => { $('group-id').value = ''; $('group-name').value = ''; $('group-description').value = ''; $('group-dialog-title').textContent = t('createGroup'); $('delete-group').classList.add('hidden'); $('group-dialog').showModal(); });
$('edit-group').addEventListener('click', () => { const group = state.groups.find((item) => item.id === state.activeGroupId); $('group-id').value = group.id; $('group-name').value = group.name; $('group-description').value = group.description; $('group-dialog-title').textContent = t('editGroup'); $('delete-group').classList.remove('hidden'); $('group-dialog').showModal(); });
$('close-group-dialog').addEventListener('click', () => $('group-dialog').close());
$('group-form').addEventListener('submit', async (event) => {
  event.preventDefault(); const id = $('group-id').value;
  try {
    const saved = await api(id ? `/groups/${id}` : '/groups', { method: id ? 'PUT' : 'POST', body: JSON.stringify({ name: $('group-name').value, description: $('group-description').value }) });
    state.groups = await api('/groups'); state.activeGroupId = saved.id; renderGroups(); renderModelConfigs(state.settings.model_configs); renderPlaygroundRequest(); await api('/settings', { method: 'PUT', body: JSON.stringify({ active_group_id: saved.id }) }); await loadRules(); $('group-dialog').close(); toast(t(id ? 'groupUpdated' : 'groupCreated'));
  } catch (error) { toast(error.message); }
});
$('delete-group').addEventListener('click', async () => {
  const id = Number($('group-id').value); if (!id || !window.confirm(t('groupDeleteConfirm'))) return;
  try { await api(`/groups/${id}`, { method: 'DELETE' }); state.groups = await api('/groups'); state.activeGroupId = state.groups[0].id; renderGroups(); renderModelConfigs(state.settings.model_configs); renderPlaygroundRequest(); await api('/settings', { method: 'PUT', body: JSON.stringify({ active_group_id: state.activeGroupId }) }); await loadRules(); $('group-dialog').close(); toast(t('groupDeleted')); } catch (error) { toast(error.message); }
});

$('new-rule').addEventListener('click', () => setForm()); $('match-type').addEventListener('change', updateFields); $('reply-type').addEventListener('change', updateFields);
$('rule-form').addEventListener('submit', async (event) => {
  event.preventDefault(); const submit = event.submitter; submit.disabled = true;
  try {
    const type = $('reply-type').value; let reply;
    if (type === 'tool') reply = { tool_name: $('tool-name').value, arguments: JSON.parse($('arguments').value || '{}') };
    else if (type === 'error') reply = { status_code: Number($('error-status').value), message: $('error-message').value };
    else if (type === 'random') reply = { size: Number($('random-size').value) };
    else reply = { content: $('content').value };
    const payload = { name: $('name').value, enabled: $('enabled').checked, priority: Number($('priority').value), model_pattern: $('model-pattern').value, group_id: Number($('rule-group').value), scopes: [$('scope').value], match_type: $('match-type').value, match_value: $('match-value').value, reply_type: type, reply, delay_ms: Number($('delay').value) };
    const id = $('rule-id').value; const saved = await api(id ? `/rules/${id}` : '/rules', { method: id ? 'PUT' : 'POST', body: JSON.stringify(payload) });
    if (saved.group_id !== state.activeGroupId) { state.activeGroupId = saved.group_id; renderGroups(); }
    await loadRules(); setForm(state.rules.find((rule) => rule.id === saved.id) || null); toast(t(id ? 'ruleUpdated' : 'ruleCreated'));
  } catch (error) { toast(error instanceof SyntaxError ? t('invalidArguments') : error.message); } finally { submit.disabled = false; }
});
$('delete-rule').addEventListener('click', async () => { const id = $('rule-id').value; if (!id || !window.confirm(t('deleteConfirm'))) return; try { await api(`/rules/${id}`, { method: 'DELETE' }); await loadRules(); setForm(); toast(t('ruleDeleted')); } catch (error) { toast(error.message); } });

$('playground-endpoint').addEventListener('change', renderPlaygroundRequest);
$('playground-model').addEventListener('change', syncPlaygroundProtocol);
$('playground-input').addEventListener('input', renderPlaygroundRequest);
$('settings-form').addEventListener('submit', async (event) => {
  event.preventDefault(); const submit = event.submitter; submit.disabled = true;
  try {
    const modelConfigs = readModelConfigs();
    await api('/settings', { method: 'PUT', body: JSON.stringify({ model_configs: modelConfigs }) });
    await loadSettings(); toast(t('settingsSaved'));
  } catch (error) { toast(error.message); } finally { submit.disabled = false; }
});

$('playground-send').addEventListener('click', async () => {
  const button = $('playground-send'); button.disabled = true; const started = performance.now();
  let preview;
  try {
    const request = buildPlaygroundRequest(); renderPlaygroundRequest();
    preview = $('playground-request').textContent;
    const response = await fetch(request.path, { method: 'POST', headers: request.preview.headers, body: JSON.stringify(request.body) });
    const data = await response.json(); const duration = Math.round(performance.now() - started);
    if ($('playground-request').textContent === preview) {
      $('playground-output').textContent = JSON.stringify({ status: response.status, duration_ms: duration, body: data }, null, 2); $('playground-meta').textContent = `${response.status} · ${duration}ms`;
    }
    await loadRequests();
  } catch (error) {
    if ($('playground-request').textContent === preview) {
      $('playground-output').textContent = JSON.stringify({ error: error.message }, null, 2); $('playground-meta').textContent = t('requestFailed');
    }
  } finally { button.disabled = false; }
});

$('refresh-requests').addEventListener('click', () => loadRequests().catch((error) => toast(error.message)));
$('clear-requests').addEventListener('click', async () => { try { await api('/requests', { method: 'DELETE' }); await loadRequests(); toast(t('listCleared')); } catch (error) { toast(error.message); } });
$('close-request-dialog').addEventListener('click', () => $('request-dialog').close());
$('request-dialog').addEventListener('click', (event) => { if (event.target === $('request-dialog')) $('request-dialog').close(); });
for (const button of document.querySelectorAll('[data-copy]')) {
  const path = new URL(button.dataset.copy).pathname;
  button.dataset.copy = `${location.origin}${path}`;
  button.querySelector('code').textContent = `${location.host}${path}`;
  button.addEventListener('click', async () => { try { await navigator.clipboard.writeText(button.dataset.copy); toast(t('copied')); } catch (_) { toast(button.dataset.copy); } });
}

setForm(); applyLanguage(); initialize();
setInterval(() => loadRequests().catch(() => {}), 5000);
