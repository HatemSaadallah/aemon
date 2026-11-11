# Company profiles in the Strategy Lab (2026-11-10)

A single reusable profile system for every company in the app. It is UI only: nothing here is read by the agent, its
tools or its evaluation, and the frozen research data in `data/dossier/` is only read.

## What exists, and where
| Data | Source | Notes |
|---|---|---|
| Companies in the app | `WORKSPACES` in `app/server.py`: Hellberg Safety, Neumann, Jotun, Tanita, John Deere | The development companies. Training companies trained V1; test companies are frozen. Neither is in the app. |
| Name, one-line description, case date | the company's base case (`data/dossier/cases.json`) | Tanita is set in 1993, Deere in mid-1962, Jotun in mid-2024; Hellberg and Neumann are present day. |
| Source library | that case's dossier records | title, URL, publication date, origin, kind, topic, excerpt, limitation, "does not establish" |
| Investigations | per-user history (`app/store.py`) | |
| Example questions, what-if scenarios | `EXAMPLES` and the case scenarios in `app/server.py` | |
| Industry, headquarters, founding, owner, website, products, timeline, markets, positioning | **new:** `app/profiles/company_profiles.json` | Curated from the dossier. Every fact cites dossier record ids, and `basis: company` marks facts that rest only on the company's own words. |
| Logos, brand colours, hero images | **none** | See below. |

## Profile data model (`app/profiles/company_profiles.json`, `profiles-v1`)
`display_name`, `legal_name`, `tagline`. Then:
- **cited facts:** `industry`, `headquarters`, `founded`, `parent`, `website`, each as `{text, sources}`;
- **case context:** `case_context: {set_in, note}`;
- **lists:** `about`, `products`, `customers`, `markets`, `timeline`, `positioning`, `context_companies`, each item
  `{…, sources, basis?}`;
- **logo**, optional: `logo: {file, source_url, retrieved, licence_note}`.

`app/companies.py` validates every citation against the company's own dossier, and `app/test_companies.py` fails if
one does not exist. The curation was done by an AI assistant from the dossier excerpts, including the Japanese, Polish
and Norwegian ones. It was checked by the validator, a word-overlap screen and spot reads. One current-website
market-share claim was removed from the 1993 Tanita profile.

### Coverage ("—" means the records do not support it, so the page says "Not in the records")
| Company | Industry | HQ | Founded | Owner | Website | About | Products | Timeline | Markets | Positioning | Other orgs |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Hellberg Safety | yes | yes | yes | yes | yes | 5 | 2 | 3 | 3 | 5 | 17 |
| Neumann | yes | — | — | yes | yes | 5 | 3 | 2 | 2 | 5 | 0 |
| Jotun | yes | yes | — | — | yes | 5 | 6 | 7 | 4 | 5 | 0 |
| Tanita | yes | — | — | — | yes | 4 | 3 | 7 | 1 | 5 | 0 |
| John Deere | yes | — | — | — | — | 5 | 3 | 6 | 1 | 5 | 0 |

## Logos and branding
No logo, brand colour or image is bundled or fetched. Logos are trademarks with usage conditions we have not checked,
and no official asset with a recorded licence exists in the repository. Every company shows a monogram instead.

To add an official logo:
1. download it from the company's own press or media page;
2. store it under `app/web/public/logos/`;
3. record `file`, `source_url`, `retrieved` and `licence_note` in the profile.

The card and hero then show it. The accent colour of each company is chosen from a neutral palette for distinction; it
is not the company's brand colour.

## Pages
- **`#/companies`, the directory:** monogram, name, industry, one-liner, headquarters and the case period. Real counts
  of sources, independent sources and investigations. Search; filter by industry, present-day or historical case, and
  whether there are investigations.
- **`#/companies/<id>`, the profile:** one template for every company. Opening it makes that company the active
  workspace. It has:
  - a breadcrumb and a hero with the website, case period and source counts;
  - the **Investigate this company** button;
  - tabs:
    - **Overview:** About, with citations and company-claim marks; At a glance; possible questions, each starting an
      investigation with that question;
    - **Products:** products and customers;
    - **Background:** a dated timeline, with events after the case date marked;
    - **Market:** markets and channels, positioning as stated in the records, and other organisations in the dossier
      with what the records say about them. They are never called competitors.
    - **Evidence:** searchable, filtered by origin. Each source is expandable to its quote, publisher, the dossier's
      evidence kind (flagged as about 80% reliable), the case author's "does not establish" note and its limitation.
      Sources published after a historical case's year are marked, and undated ones say so. A filter shows only
      sources dated by the case year.
    - **Investigations:** the company's runs, and its what-if scenarios.

  Citation chips open the cited source in the Evidence tab.

## Limitations
- Five companies. Adding one needs a workspace entry and, for a full profile, a curated entry. Without a curated entry
  the page falls back to the case brief and shows empty states.
- Profiles describe the company from sources published up to today. Historical cases show a notice saying so, and each
  fact shows its source's publication year.
- No product images, hero images or logos, for the reasons above.

Screenshots: `docs/figures/ui/companies/`.
