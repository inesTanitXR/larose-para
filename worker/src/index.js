/* Carte Rose — registre de fidélité (Cloudflare Worker + KV).
   POST /order    {tel,name,amount,num,redeem,referral}   commande depuis le site
   POST /instore  {pin,tel,name,amount,redeem}            saisie en boutique (caisse.html)
   GET  /balance?tel=                                      solde d'un client (site)
   GET  /recent?pin=                                       dernières opérations (caisse)
*/
const H = (env) => ({ 'Access-Control-Allow-Origin': env.ALLOW_ORIGIN || '*', 'Access-Control-Allow-Headers': 'Content-Type',
  'Access-Control-Allow-Methods': 'GET,POST,OPTIONS', 'Content-Type': 'application/json; charset=utf-8' });
const norm = (t) => String(t || '').replace(/\D/g, '').replace(/^216/, '').slice(-8);
const json = (env, o, s = 200) => new Response(JSON.stringify(o), { status: s, headers: H(env) });

async function load(env, tel) {
  return (await env.ROSE.get('c:' + tel, 'json')) || { tel, name: '', petals: 0, used: 0, ops: [] };
}
function view(c, env) {
  const step = +env.STEP, bon = +env.BON;
  return { tel: c.tel, name: c.name, petals: c.petals, bons: Math.floor(c.petals / step), bon, step,
    orders: c.ops.filter(o => o.p > 0).length, used: c.used, ops: c.ops.slice(0, 20) };
}
async function credit(env, { tel, name, amount, redeem, src, num, referral }) {
  const step = +env.STEP;
  const c = await load(env, tel);
  if (name && !c.name) c.name = String(name).slice(0, 40);
  amount = Math.max(0, Math.floor(+amount || 0));
  const first = c.ops.length === 0;
  const d = new Date().toISOString().slice(0, 16).replace('T', ' ');
  if (redeem && c.petals >= step) { c.petals -= step; c.used += 1; c.ops.unshift({ d, p: -step, src, note: 'bon utilisé' }); }
  let p = amount;
  if (first && referral) p += 50;
  if (p > 0) { c.petals += p; c.ops.unshift({ d, a: amount, p, src, num: num || '' }); }
  c.ops = c.ops.slice(0, 60);
  await env.ROSE.put('c:' + tel, JSON.stringify(c));
  // parrain
  const ref = norm(referral);
  if (first && ref && ref !== tel) {
    const all = await env.ROSE.list({ prefix: 'c:' });
    for (const k of all.keys) if (k.name.slice(2).endsWith(ref.slice(-4))) {
      const r = await env.ROSE.get(k.name, 'json'); if (!r) continue;
      r.petals += 50; r.ops.unshift({ d, p: 50, src: 'parrainage', note: 'filleule ' + tel.slice(-4) }); await env.ROSE.put(k.name, JSON.stringify(r)); break;
    }
  }
  const log = (await env.ROSE.get('recent', 'json')) || [];
  log.unshift({ d, tel, name: c.name, a: amount, p, src, redeem: !!redeem, petals: c.petals });
  await env.ROSE.put('recent', JSON.stringify(log.slice(0, 100)));
  return { ...view(c, env), first };
}

export default {
  async fetch(req, env) {
    if (req.method === 'OPTIONS') return new Response(null, { headers: H(env) });
    const url = new URL(req.url), path = url.pathname.replace(/\/$/, '');
    try {
      if (req.method === 'GET' && path === '/balance') {
        const tel = norm(url.searchParams.get('tel')); if (tel.length < 8) return json(env, { error: 'tel' }, 400);
        return json(env, view(await load(env, tel), env));
      }
      if (req.method === 'GET' && path === '/recent') {
        if (url.searchParams.get('pin') !== env.ADMIN_PIN) return json(env, { error: 'pin' }, 403);
        return json(env, (await env.ROSE.get('recent', 'json')) || []);
      }
      if (req.method === 'POST' && (path === '/order' || path === '/instore')) {
        const b = await req.json();
        if (path === '/instore' && b.pin !== env.ADMIN_PIN) return json(env, { error: 'pin' }, 403);
        const tel = norm(b.tel); if (tel.length < 8) return json(env, { error: 'tel' }, 400);
        if (path === '/order' && (+b.amount > 5000)) return json(env, { error: 'amount' }, 400);
        return json(env, await credit(env, { tel, name: b.name, amount: b.amount, redeem: b.redeem, num: b.num,
          referral: b.referral, src: path === '/order' ? 'site' : 'boutique' }));
      }
      return json(env, { ok: true, service: 'larose-rose' });
    } catch (e) { return json(env, { error: String(e) }, 500); }
  }
};
