---
name: Notion Warm Workspace
colors:
  surface: '#fff8f5'
  surface-dim: '#e1d8d4'
  surface-bright: '#fff8f5'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#fbf2ee'
  surface-container: '#f5ece8'
  surface-container-high: '#efe6e2'
  surface-container-highest: '#e9e1dd'
  on-surface: '#1e1b19'
  on-surface-variant: '#414753'
  inverse-surface: '#34302d'
  inverse-on-surface: '#f8efeb'
  outline: '#717784'
  outline-variant: '#c1c6d5'
  surface-tint: '#5d5f5f'
  primary: '#5c5d5e'
  on-primary: '#ffffff'
  primary-container: '#747676'
  on-primary-container: '#fefefe'
  inverse-primary: '#c6c6c7'
  secondary: '#005eb4'
  on-secondary: '#ffffff'
  secondary-container: '#4093fe'
  on-secondary-container: '#002c5a'
  tertiary: '#5c5d5d'
  on-tertiary: '#ffffff'
  tertiary-container: '#757675'
  on-tertiary-container: '#fdfffe'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#e2e2e2'
  primary-fixed-dim: '#c6c6c7'
  on-primary-fixed: '#1a1c1c'
  on-primary-fixed-variant: '#454747'
  secondary-fixed: '#d5e3ff'
  secondary-fixed-dim: '#a8c8ff'
  on-secondary-fixed: '#001b3c'
  on-secondary-fixed-variant: '#00468a'
  tertiary-fixed: '#e3e2e1'
  tertiary-fixed-dim: '#c7c6c5'
  on-tertiary-fixed: '#1a1c1c'
  on-tertiary-fixed-variant: '#464746'
  background: '#fff8f5'
  on-background: '#1e1b19'
  surface-variant: '#e9e1dd'
typography:
  display-hero:
    fontFamily: Inter
    fontSize: clamp(2.5rem, 5vw, 4rem)
    fontWeight: '700'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  h1:
    fontFamily: Inter
    fontSize: 2.25rem
    fontWeight: '700'
    lineHeight: '1.2'
  h2:
    fontFamily: Inter
    fontSize: 1.5rem
    fontWeight: '600'
    lineHeight: '1.3'
  body-md:
    fontFamily: Inter
    fontSize: 1rem
    fontWeight: '400'
    lineHeight: '1.6'
  label-caps:
    fontFamily: Inter
    fontSize: 0.875rem
    fontWeight: '500'
    letterSpacing: 0.05em
  technical-mono:
    fontFamily: JetBrains Mono
    fontSize: 0.875rem
    fontWeight: '400'
    lineHeight: '1.5'
rounded:
  sm: 0.5rem
  DEFAULT: 1rem
  md: 1.5rem
  lg: 2rem
  xl: 3rem
  full: 9999px
spacing:
  base: 0.5rem
  section-gap: clamp(4rem, 8vw, 8rem)
  container-max: 1280px
  gutter: 1.5rem
---

## Overview

Notion-inspired warm workspace landing page. Ideal for ferramentas de produtividade, workspaces colaborativos, gestão de conhecimento, wikis. AI-ready template. Before Notion, productivity software lived in two camps: the cold precision of spreadsheets and the chaotic maximalism of project management tools drowning in color-coded labels. Notion quietly rejected both. They looked at Swiss design — the grids, the restraint, the typographic hierarchy — and asked what happens when you warm it up just enough to make a blank page feel like an invitation rather than an obligation.

The genius was in what they didn't do. No harsh dividers — just whisper borders that suggest structure without imprisoning content. No aggressive brand colors screaming for attention — just enough warmth in the neutrals to feel like paper rather than a screen. The rounded corners aren't decorative; they're psychological. They tell your brain this tool won't bite.

This approach fundamentally changed how we think about collaborative workspaces. Notion proved that productivity software doesn't need to look productive. It needs to look approachable. The warm minimalism became a permission slip: your workspace can be beautiful and functional, structured and human. Every team wiki and personal knowledge base built since owes something to that quiet revolution.

- Density: 3/10 — Airy
- Variance: 2/10 — Structured
- Motion: 4/10 — Subtle

- **Style:** Warm Minimalism, Whisper Borders, NotionInter, Blue Accent
- **Keywords:** notion, warm minimalism, whisper borders, warm neutrals, NotionInter, blue accent, multi-layer shadows, workspace aesthetic
- **Era:** 2024-2026 Warm Workspace
- **Light/Dark:** ✓ Full / ✗ Not Recommended

## Colors

- **Branco** (#ffffff) — Light surface, primary background
- **Azul Notion** (#0075de) — Accent highlight, links and focus states
- **Branco Quente** (#f6f5f4) — Tertiary surface, section backgrounds
- **Quase Preto** (#0f0c0a) — Primary text color, high-contrast ink
- **Navy** (#001d36) — Extended palette, decorative use or container text
- **Cinza Quente** (#454749) — Secondary text, muted elements
- **Cinza Claro** (#c5c7c9) — Borders, disabled states
- **Borda** (rgba(0,0,0,0.1)) — Extended palette, decorative use


## Typography

- **Display / Hero:** Inter — Weight 700, tight tracking, used for headline impact
- **Body:** Inter — Weight 400, 16px/1.6 line-height, max 72ch per line
- **UI Labels / Captions:** Inter — 0.875rem, weight 500, slight letter-spacing
- **Monospace:** JetBrains Mono — Used for code, metadata, and technical values

Scale:
- Hero: clamp(2.5rem, 5vw, 4rem)
- H1: 2.25rem
- H2: 1.5rem
- Body: 1rem / 1.6
- Small: 0.875rem


## Layout

- **Grid:** CSS Grid primary. Max-width containment: 1280px centered with 1.5rem side padding.
- **Spacing rhythm:** Balanced. Base unit: 0.5rem (8px).
- **Section vertical gaps:** clamp(4rem, 8vw, 8rem).
- **Hero layout:** Split-screen (text left, visual right).
- **Feature sections:** Zig-zag alternating text+image rows. No 3-equal-columns.
- **Mobile collapse:** All multi-column layouts collapse below 768px. No horizontal overflow.
- **z-index contract:** base (0) / sticky-nav (100) / overlay (200) / modal (300) / toast (500).


## Elevation & Depth

Canvas branco (#ffffff) com texto off-black (#0f0c0a). Paleta de cinzas quentes com subtom sofisticado (#f6f5f4, #454749). Bordas whisper: 1px solid rgba(0,0,0,0.1) ultra-finas. Sombras multi-camada com opacidade sub-0.05 para profundidade sutil. Azul Notion (#0075de) como único acento para CTAs. Seções alternando branco e branco quente (#f6f5f4). Pill badges (9999px) com fundo azul tintado.

- **Physics:** Ease-out curves, 200-300ms duration. Smooth and predictable.
- **Entry animations:** Fade + translate-Y (16px → 0) over 420ms ease-out. Staggered cascades for lists: 80ms between items.
- **Hover states:** Subtle color shift + shadow adjustment over 200ms.
- **Page transitions:** Fade only (200ms).
- **Performance:** Only transform and opacity animated. No layout-triggering properties.


## Shapes

Base corner radius: 1rem (16px). High roundedness (Pill-shaped style). See rounded tokens in front matter for the full scale.


## Components

- **Primary Button:** Pill-shaped (9999px) shape. Accent color fill (#0075de). Hover: 8% darken + subtle lift shadow. Active: -1px translate tactile press. Font weight 600. No outer glows.
- **Secondary / Ghost Button:** Outline variant. 1.5px border in muted color. Text in neutral color. Hover: subtle background fill.
- **Cards:** Pill-shaped (2rem/32px) corners for large containers. Surface background. Subtle shadow (0 2px 12px rgba(0,0,0,0.06)). 1px border stroke.
- **Inputs:** Label above input. 1px border stroke. Focus ring: 2px accent color offset 2px. Error text below in semantic red. No floating labels.
- **Navigation:** Primary surface background. Active item: accent color indicator. Font weight 500 when active.
- **Skeletons:** Shimmer animation matching component dimensions. No circular spinners.
- **Empty States:** Icon-based composition with descriptive text and action button.


## Do's and Don'ts

- No emojis in UI — use icon system only (Lucide, Heroicons)
- No decorative gradients — flat color only
- No shadows heavier than 0 2px 8px rgba(0,0,0,0.08)
- No pure black (#000000) — use #0f0c0a for high-contrast text
- No oversaturated accent colors (saturation cap: 80%)
- No 3-column equal-width feature layouts — use zig-zag or asymmetric grid
- No `h-screen` — use `min-h-[100dvh]`
- No AI copywriting clichés: "Elevate", "Seamless", "Unleash", "Next-Gen"
- No broken external image links — use picsum.photos or inline SVG
- No generic lorem ipsum in demos

- Do Canvas branco com texto #0f0c0a
- Do Cinzas quentes com subtom neutro
- Do Bordas whisper rgba(0,0,0,0.1)
- Do Sombras multi-camada sub-0.05
- Do Azul #0075de único acento
- Do Alternância branco/branco quente
- Do Responsivo


## Use Case

Tools de produtividade, Workspaces colaborativos, Gestão de conhecimento, Wikis