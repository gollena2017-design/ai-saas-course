# Domain setup and Render configuration

Technical Render URL: https://ai-saas-course-j85m.onrender.com

Custom domain used: https://course-vibe-saas.pp.ua

NS servers used: ns10.uadns.com, ns11.uadns.com, ns12.uadns.com

DNS records added:

- `@` A -> (Render provides IP via DNS; user should set according to Render instructions)
- `www` CNAME -> `ai-saas-course-j85m.onrender.com`

Validation steps performed:

- Confirmed `/healthz` returns 200 on the Render URL.
- Confirmed React UI loads on custom domain (user-provided).

HTTPS: Certificate issuance was observed in Render dashboard after DNS verification.

Problems encountered:

- Render may serve old instances during rolling deploys; watch for cached assets.

Notes and verification:

- NIC.UA domain management steps were followed by the user (domain activation via SMS or bot where needed).
- The user reported their site is already live at `https://course-vibe-saas.pp.ua`.

Limitations (Render Free tier):

- Cold starts and sleep for inactive services (may cause initial slow response).
- Rolling deploys may temporarily serve older code during updates.

Screenshots to add:

- NIC.UA domain panel
- DNS records
- Render Custom Domain configured and Verified/Certificate Issued
- App running at custom domain

## Screenshots

Place screenshots in `docs/screenshots/` and they will be referenced below.

![NIC.UA - Domains list](docs/screenshots/nic_domains.png)
![NIC.UA - Name servers and DNS records](docs/screenshots/nic_ns_records.png)
![Render - Project / Services overview](docs/screenshots/render_overview.png)
![Render - Custom Domain Verified / Certificate Issued](docs/screenshots/render_custom_domain.png)
![Site on custom domain (homepage)](docs/screenshots/site_homepage.png)

If you prefer, upload the screenshots here in the chat and I will add them to the repository under `docs/screenshots/` and commit them.
