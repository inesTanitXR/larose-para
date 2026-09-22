# Carte Rose — registre (Cloudflare Worker, gratuit)

Une seule fois, sur le Mac (compte Cloudflare d'Ines) :

```bash
cd worker
npx wrangler login                      # ouvre le navigateur, autoriser
npx wrangler kv namespace create ROSE   # copier l'id affiché dans wrangler.toml (id = "...")
npx wrangler secret put ADMIN_PIN       # le code PIN de la caisse (4 à 6 chiffres)
npx wrangler deploy                     # affiche l'URL https://larose-rose.<compte>.workers.dev
```

Puis dans `config.py` : `WORKER_URL = "https://larose-rose.<compte>.workers.dev"` → `python3 build.py` → push.

Sans worker, le site fonctionne quand même : la rose est alors gardée seulement dans le navigateur du client
et la caisse est désactivée.
