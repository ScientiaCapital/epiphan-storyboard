# Epiphan Storyboard Project Context
Last Updated: 2026-05-05

## Current Sprint: Sales Methodology + Vertical Expansion

### Completed Today (2026-05-05)

#### Sprint 1: JTBD + Challenger + NSTTD Frameworks (c544c4b)
- [x] JTBD job statements for all 17 personas (Forces of Progress, frankenstack detection)
- [x] Challenger 6-step choreography for storyboard panel narrative
- [x] NSTTD tactical empathy for all email draft generation
- [x] AV Integrator persona (17th persona, CHANNEL type)
- [x] 8 production bundles (Pearl + EC20, ~25% off EC20 MSRP)
- [x] EC20 "rooms out of reach" scenario ($1,899 vs $5,700-$8,500 traditional)
- [x] Meeting recap endpoint (POST /storyboard/meeting-recap)
- [x] Quality gate (quality_gate.py — DA review)
- [x] Fixed 12 broken URLs (case studies + resources)
- [x] Updated EC20 specs from brochure (4K60, NDI|HX3, Dante, direct CMS/LMS)
- [x] Fixed stale pricing (Pearl-2 $8,999, Pearl Nexus $3,899)
- [x] Standardized naming: Epiphan Cloud → Epiphan Edge
- [x] CMS/LMS brand agnosticism enforced in all prompts

#### Sprint 2: Verticals + Styles + Artists (9930fad)
- [x] Broadcasting vertical (fleet mobilization, workflow automation, SRT contribution)
- [x] 2 broadcasting deployment scenarios
- [x] Blueprint visual style for technical audiences
- [x] Frida Kahlo artist style (MX/LATAM market)
- [x] Siqueiros artist style (Los Tres Grandes industrial muralism)

### Next Session Priority
- [ ] Courts vertical expansion — counties, jurisdictions, dedicated persona work
- [ ] Test meeting recap endpoint with real Clari transcript
- [ ] Verify storyboard output quality with new frameworks (manual test)

## Key Metrics
- Tests: 1,356 passing (up from 1,279)
- Personas: 17 | Verticals: 11 | Scenarios: 26 | Products: 16 | Styles: 9 | Artists: 9
- Sales frameworks: JTBD + Challenger + NSTTD embedded in all prompts
- Deployed: https://epiphan-storyboard.vercel.app

## Architecture
- FastAPI app at `src/api.py`, deployed on Vercel
- Storyboard generation: Gemini Flash
- Meeting recap: `src/tools/storyboard/meeting_recap.py`
- Quality gate: `src/tools/storyboard/quality_gate.py`
- ICP presets: 17 personas, 11 verticals, 8 bundles

## DA Validation Notes
- NDI|HX3 on EC20: confirmed by brochure (MCP KB says HX2, outdated)
- Dante on EC20: confirmed by Panopto Value Prop deck (not yet on website)
- EC20 direct CMS record: confirmed by Panopto Value Prop deck (Panopto only for now)
- Epiphan Connect: SRT extraction from Teams/Zoom (not fleet management)
- Broadcasting CRM category includes distribution (Broadfield, B&H)
