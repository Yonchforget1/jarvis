# Agent Skills Evaluation for Jarvis

**Source**: https://agentskills.io / https://github.com/anthropics/skills
**Date**: 2026-02-09
**Evaluator**: Claude Opus 4.6
**Criteria**: Score 1-10 on value to Jarvis as a commercial AI agent ($497/mo SaaS). Only 9-10 selected for integration.

**Scoring factors**:
- Does it add a genuinely NEW capability Jarvis doesn't have?
- Is it a high-frequency use case for the target market (business professionals)?
- Does it include real tools/scripts, not just guidance?
- Is it technically feasible to integrate with Jarvis's architecture?

---

## Complete Skill Catalog (16 skills reviewed)

### 1. algorithmic-art — Score: 4/10
**What it does**: Creates generative art with p5.js. Outputs an "algorithmic philosophy" document + interactive HTML with seeded randomness, parameter controls, and seed navigation.

**Why not selected**: Niche creative tool with Anthropic-specific branding (Poppins/Lora fonts, Anthropic color scheme). Requires p5.js and a specific viewer template. Cool demo, but not a capability business users are paying $497/mo for. Jarvis already has gamedev tools for creative work.

---

### 2. brand-guidelines — Score: 2/10
**What it does**: Applies Anthropic's official brand colors and typography to artifacts. Defines Anthropic's hex colors, font pairings (Poppins/Lora), and shape accent cycling.

**Why not selected**: This is Anthropic's internal branding skill. Completely irrelevant for Jarvis — our users have their own brands. Zero transferable value.

---

### 3. canvas-design — Score: 4/10
**What it does**: Creates high-quality static visual designs (posters, art prints, canvas compositions) at "museum quality." Includes 54 bundled TTF fonts and a design philosophy workflow.

**Why not selected**: Requires a PDF/PNG rendering pipeline that Jarvis doesn't have. The 54 fonts (81 files) add 10+ MB of bloat. The design philosophy is subjective and Anthropic-flavored ("meticulously crafted" wording requirements). Not a core business capability.

---

### 4. doc-coauthoring — Score: 7/10
**What it does**: A structured 3-stage workflow for collaboratively writing documents (PRDs, design docs, RFCs, proposals). Stage 1: context gathering with clarifying questions. Stage 2: section-by-section refinement with brainstorm-curate-draft loops. Stage 3: reader testing with fresh-context verification.

**Why not selected**: Excellent process guidance — genuinely well-designed workflow. But it's purely instructional: no scripts, no tools, no assets, just a single SKILL.md. Jarvis could benefit from this methodology, but it doesn't add a new *capability*. The process could be incorporated into Jarvis's identity prompt more simply. Close but not 9-level.

---

### 5. docx — Score: 9/10 *** SELECTED ***
**What it does**: Complete Word document lifecycle: reading (pandoc extraction), creating (docx-js/JavaScript), and editing (unpack ZIP → edit XML → repack). Handles tracked changes, comments, smart quotes, schema compliance.

**Why selected**: Word documents are the #1 business document format. Jarvis currently outputs plain text — being able to produce properly formatted .docx files with tracked changes, comments, and professional formatting is a massive capability upgrade. The pack/unpack scripts enable XML-level editing of existing documents. This is what turns Jarvis from "text generator" into "document automation platform."

**Key assets**: `scripts/office/pack.py`, `unpack.py`, `validate.py`, `accept_changes.py`, `comment.py`, ISO OOXML schemas for validation. Shares the `office/` module with pptx and xlsx.

---

### 6. frontend-design — Score: 5/10
**What it does**: Design philosophy for creating distinctive web interfaces that avoid "AI slop." Covers typography (avoid Inter/Roboto), color strategy, motion/animation, spatial composition. Purely instructional.

**Why not selected**: No tools, no scripts, no assets — just design opinions. Some good principles but nothing that adds a capability. Jarvis already builds web interfaces.

---

### 7. internal-comms — Score: 3/10
**What it does**: Templates for Anthropic's internal communications: 3P updates (Progress/Plans/Problems), company newsletters, FAQ responses. Includes 4 example template files.

**Why not selected**: Anthropic-specific communication templates. The 3P update format is a niche convention, not a universal business need. Templates are trivial to create on demand. No tools or scripts.

---

### 8. mcp-builder — Score: 7/10
**What it does**: Comprehensive guide for building MCP (Model Context Protocol) servers. Four-phase workflow: research, implementation, testing, evaluation creation. Includes reference docs on best practices, TypeScript/Python patterns, and evaluation scripts.

**Why not selected**: Excellent technical reference but it's a meta-development skill — teaches how to build MCP servers, which is a developer task. Jarvis's target market is business users, not MCP developers. The reference material is valuable for the Jarvis development team but not for end-user capabilities. Close to 8 but not 9.

---

### 9. pdf — Score: 9/10 *** SELECTED ***
**What it does**: Complete PDF processing: read/extract text+tables (pypdf, pdfplumber), create new PDFs (reportlab), merge/split/rotate (qpdf/pdftk), OCR scanned documents (pytesseract), fill PDF forms, extract images, add watermarks, encrypt/decrypt. Includes 8 helper scripts.

**Why selected**: PDF manipulation is one of the most requested automation tasks globally. Business users constantly need to: extract data from PDFs, fill forms, merge documents, create reports. Jarvis having this capability means users can say "extract all the tables from this PDF and put them in a spreadsheet" or "fill out this government form" and Jarvis can actually do it. The scripts for form filling, field extraction, and bounding box validation are battle-tested.

**Key assets**: `scripts/fill_fillable_fields.py`, `check_fillable_fields.py`, `extract_form_structure.py`, `convert_pdf_to_images.py`, `forms.md` (form filling guide), `reference.md` (advanced features).

---

### 10. pptx — Score: 9/10 *** SELECTED ***
**What it does**: Full PowerPoint lifecycle: read existing presentations (markitdown), edit via XML unpacking workflow, create from scratch with PptxGenJS. Includes extensive design guidance (color palettes, typography, layout variety), mandatory QA verification loops, and scripts for pack/unpack/validate/thumbnails.

**Why selected**: "Make me a presentation" is one of the highest-value tasks an AI agent can handle. Consultants, executives, and sales teams spend hours creating decks. Jarvis being able to produce professional, well-designed PowerPoint presentations — with proper color strategy, varied layouts, and visual QA — is a $497/mo feature all by itself. The design guidance specifically combats the "AI slop" problem (bland layouts, centered text, default blue palettes). The QA verification loop (generate → convert to images → inspect → fix) ensures quality.

**Key assets**: `scripts/office/pack.py`, `unpack.py`, `validate.py`, `add_slide.py`, `clean.py`, `thumbnail.py`, `editing.md`, `pptxgenjs.md` (creation guide with PptxGenJS).

---

### 11. skill-creator — Score: 7/10
**What it does**: Meta-skill that teaches how to create Agent Skills. Covers skill architecture, progressive disclosure design, file organization, and provides init/package/validate scripts.

**Why not selected**: Useful for development but Jarvis has its own tool system (ToolDef pattern), not Agent Skills format. The principles (concise is key, appropriate degrees of freedom, progressive disclosure) are good design thinking but don't add end-user capabilities. The scripts create .skill files which aren't consumed by Jarvis.

---

### 12. slack-gif-creator — Score: 3/10
**What it does**: Creates animated GIFs optimized for Slack (128x128 emoji or 480x480 message size). Includes a GIF builder, validators, easing functions, and frame helpers using PIL.

**Why not selected**: Extremely niche. Creating Slack GIFs is a fun party trick but not a serious business capability. The utility functions (easing, frame composition) are simple enough to recreate on demand.

---

### 13. theme-factory — Score: 5/10
**What it does**: 10 curated visual themes (Ocean Depths, Midnight Galaxy, etc.) with color palettes and font pairings. Can be applied to slides, docs, reports, or HTML. Includes a PDF showcase of all themes.

**Why not selected**: Complementary to pptx/docx but not independently valuable. The theme definitions are just hex codes and font names in markdown files. Useful reference material but doesn't add a capability — it enhances one. Could be incorporated later as a supplement to the pptx skill.

---

### 14. web-artifacts-builder — Score: 3/10
**What it does**: Build toolchain for creating complex React + TypeScript + shadcn/ui web artifacts for display within claude.ai conversations. Scaffolds a full project, then bundles into a single HTML file.

**Why not selected**: Designed specifically for claude.ai's artifact system, not for general use. Jarvis is a standalone agent, not a claude.ai extension. The scaffolding scripts (init-artifact.sh, bundle-artifact.sh) produce claude.ai-specific output. The shadcn/ui components tarball is 40+ pre-packaged components — overkill and wrong target.

---

### 15. webapp-testing — Score: 7/10
**What it does**: Tests local web applications using Python Playwright scripts. Core value: `with_server.py` helper that manages server lifecycle (start servers, wait for ready, run tests, shutdown). Supports multiple concurrent servers.

**Why not selected**: Jarvis already has 11 Playwright browser tools (open_browser, navigate_to, click_element, etc.) and can run Python/shell commands. The `with_server.py` helper adds convenience but not a new capability. The "reconnaissance-then-action" pattern (screenshot before interaction) is already in Jarvis's Computer Use Workflow prompt. Close to 8 but redundant with existing tools.

---

### 16. xlsx — Score: 9/10 *** SELECTED ***
**What it does**: Professional Excel/spreadsheet skill: create, read, edit .xlsx/.xlsm/.csv/.tsv files. Enforces financial modeling standards: industry-standard color coding (blue=inputs, black=formulas, green=links), Excel formulas (never hardcoded values), mandatory recalculation verification. Scripts for recalc, pack/unpack/validate.

**Why selected**: Spreadsheet work is the most common office automation task. Business users live in Excel. Jarvis being able to create financial models with proper formula chains, professional color coding, and verified calculations is enormously valuable. The recalculation verification script (`recalc.py`) ensures formulas actually work — this is the kind of quality assurance that separates a $497/mo tool from a free chatbot. The emphasis on "dynamic spreadsheets that remain updateable" is exactly right.

**Key assets**: `scripts/recalc.py`, `scripts/office/pack.py`, `unpack.py`, `validate.py`, `soffice.py` (LibreOffice integration).

---

## Summary

| Skill | Score | Selected? | Reason |
|-------|-------|-----------|--------|
| algorithmic-art | 4 | No | Niche creative, Anthropic-branded |
| brand-guidelines | 2 | No | Anthropic-specific branding |
| canvas-design | 4 | No | Niche, needs rendering pipeline |
| doc-coauthoring | 7 | No | Good process, no tools |
| **docx** | **9** | **Yes** | **Word document automation — #1 business format** |
| frontend-design | 5 | No | Philosophy only, no tools |
| internal-comms | 3 | No | Anthropic-specific templates |
| mcp-builder | 7 | No | Meta-development, not end-user |
| **pdf** | **9** | **Yes** | **PDF processing — most requested automation task** |
| **pptx** | **9** | **Yes** | **Presentation creation — killer business feature** |
| skill-creator | 7 | No | Meta-skill, wrong tool system |
| slack-gif-creator | 3 | No | Too niche |
| theme-factory | 5 | No | Complementary only |
| web-artifacts-builder | 3 | No | claude.ai specific |
| webapp-testing | 7 | No | Redundant with existing Playwright tools |
| **xlsx** | **9** | **Yes** | **Spreadsheet automation — most common office task** |

**Selected**: 4 skills (pdf, pptx, xlsx, docx) — the complete Office Automation Suite.

**Why these 4 together**: They form a cohesive document automation platform. They share the same `office/` module (pack/unpack/validate/soffice). They cover the 4 most common business document formats. Combined with Jarvis's existing capabilities (filesystem, shell, web, computer use, browser automation), they transform Jarvis from an AI chatbot into a full-stack business automation agent.

**Combined capability**: "Take this PDF contract, extract the key terms into a spreadsheet, create a summary presentation for the board, and draft a Word memo for legal review." That's a $497/mo workflow.
