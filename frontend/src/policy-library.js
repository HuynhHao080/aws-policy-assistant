const MAX_SAVED = 30;
const validId = id => typeof id === 'string' && /^[A-Za-z0-9_-]{1,80}$/.test(id);

export function policyLinkRoute(value) {
  const id = typeof value === 'string' && value.startsWith('policy/') ? value.slice(7) : '';
  return validId(id) ? id : null;
}

export class SavedPolicies {
  constructor(storage) {
    this.storage = storage;
    this.key = null;
    this.items = [];
  }

  selectAccount(owner) {
    this.key = owner ? `policy-assistant:saved-policies:${owner}` : null;
    this.items = [];
    if (!this.key) return;
    try {
      const saved = JSON.parse(this.storage.getItem(this.key) || '[]');
      if (!Array.isArray(saved)) return;
      const unique = new Map();
      for (const entry of saved.slice(0, MAX_SAVED)) {
        if (validId(entry?.policy_id) && typeof entry.title === 'string') {
          unique.set(entry.policy_id, {policy_id:entry.policy_id, title:entry.title.slice(0, 180)});
        }
      }
      this.items = [...unique.values()];
    } catch { /* Storage can be unavailable in private browsing. */ }
  }

  has(id) {
    return this.items.some(item => item.policy_id === id);
  }

  toggle(policy) {
    if (!this.key || !validId(policy?.policy_id)) throw new Error('Chưa thể lưu chính sách này.');
    const saved = this.has(policy.policy_id);
    if (!saved && this.items.length >= MAX_SAVED) throw new Error('Bạn đã lưu 30 chính sách. Bỏ lưu một mục trước khi thêm.');
    const next = saved ? this.items.filter(item => item.policy_id !== policy.policy_id)
      : [{policy_id:policy.policy_id, title:String(policy.title || policy.policy_id).slice(0, 180)}, ...this.items];
    this.storage.setItem(this.key, JSON.stringify(next));
    this.items = next;
    return !saved;
  }

  removeAccount() {
    if (this.key) this.storage.removeItem(this.key);
    this.selectAccount(null);
  }
}
