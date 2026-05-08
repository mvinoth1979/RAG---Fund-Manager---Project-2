---
name: Premium Financial Assistant
colors:
  surface: '#f8f9ff'
  surface-dim: '#cbdbf5'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff4ff'
  surface-container: '#e5eeff'
  surface-container-high: '#dce9ff'
  surface-container-highest: '#d3e4fe'
  on-surface: '#0b1c30'
  on-surface-variant: '#45464d'
  inverse-surface: '#213145'
  inverse-on-surface: '#eaf1ff'
  outline: '#76777d'
  outline-variant: '#c6c6cd'
  surface-tint: '#565e74'
  primary: '#000000'
  on-primary: '#ffffff'
  primary-container: '#131b2e'
  on-primary-container: '#7c839b'
  inverse-primary: '#bec6e0'
  secondary: '#006c49'
  on-secondary: '#ffffff'
  secondary-container: '#6cf8bb'
  on-secondary-container: '#00714d'
  tertiary: '#000000'
  on-tertiary: '#ffffff'
  tertiary-container: '#2a1700'
  on-tertiary-container: '#b87500'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dae2fd'
  primary-fixed-dim: '#bec6e0'
  on-primary-fixed: '#131b2e'
  on-primary-fixed-variant: '#3f465c'
  secondary-fixed: '#6ffbbe'
  secondary-fixed-dim: '#4edea3'
  on-secondary-fixed: '#002113'
  on-secondary-fixed-variant: '#005236'
  tertiary-fixed: '#ffddb8'
  tertiary-fixed-dim: '#ffb95f'
  on-tertiary-fixed: '#2a1700'
  on-tertiary-fixed-variant: '#653e00'
  background: '#f8f9ff'
  on-background: '#0b1c30'
  surface-variant: '#d3e4fe'
typography:
  display-lg:
    fontFamily: Outfit
    fontSize: 48px
    fontWeight: '700'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Outfit
    fontSize: 32px
    fontWeight: '700'
    lineHeight: '1.2'
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Outfit
    fontSize: 24px
    fontWeight: '700'
    lineHeight: '1.3'
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.5'
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.5'
  label-caps:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: '1'
    letterSpacing: 0.05em
  caption:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: '1.4'
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 4px
  xs: 0.5rem
  sm: 1rem
  md: 1.5rem
  lg: 2rem
  xl: 3rem
  gutter: 1.5rem
  container-max: 1200px
---

## Brand & Style
The design system is engineered to evoke institutional stability and modern technological precision. It targets a sophisticated investor audience that demands both the reliability of traditional finance and the agility of digital-first platforms.

The aesthetic follows a **Premium Minimalist** approach fused with **Subtle Glassmorphism**. By prioritizing high-density whitespace and refined transparency, the UI avoids the "clutter" typical of financial dashboards, instead offering a calm, focused environment for complex data consumption. The emotional response is one of clarity, security, and growth.

## Colors
The palette is anchored by **Deep Navy (#0F172A)** to establish authority and trust. **Emerald (#10B981)** is utilized strategically as an "Action & Growth" accent, representing positive financial momentum.

**Surface Strategy:**
- **Primary Background:** A soft Slate-50 gradient that transitions subtly to white to prevent eye fatigue.
- **System States:** Warning (Amber) and Error (Red) are used with high-saturation for immediate recognition but reserved for critical compliance or validation messaging.
- **Glass Surfaces:** White with 70% to 85% opacity, utilizing `backdrop-filter: blur(12px)` to maintain legibility against background gradients.

## Typography
This design system employs a dual-font strategy to balance character with utility. 

- **Outfit** is the display face, providing a geometric, modern confidence to headers and key metrics. 
- **Inter** handles all functional text, chosen for its exceptional legibility in data-dense financial contexts and its neutral, systematic tone.

**Compliance Text:** All legal disclaimers and citations must use the `caption` or `body-sm` styles to remain unobtrusive yet fully accessible, adhering to a minimum contrast ratio of 4.5:1.

## Layout & Spacing
The layout follows a **Fixed-Width Centered Grid** for the desktop experience to maintain a "white-glove" premium feel, while transitioning to a **Fluid Grid** for mobile devices.

- **The Chat Interface:** Constrained to a 768px central column to ensure optimal line lengths for reading complex financial advice.
- **Rhythm:** A 4px baseline grid ensures vertical consistency. 
- **Margins:** Generous `xl` (48px) top and bottom margins provide the "Trust-First" minimalist breathing room required for a premium experience.

## Elevation & Depth
Depth is communicated through **Translucent Layering** rather than heavy shadows.

- **Level 0 (Base):** Slate-50 background with a very subtle radial gradient (#F8FAFC to #F1F5F9).
- **Level 1 (Cards/Bubbles):** Glassmorphic surfaces. White at 80% opacity with a 1px solid white border at 20% opacity. This creates a "frosted edge" effect.
- **Level 2 (Active/Floating):** Subtle, highly-diffused ambient shadows (Color: #0F172A, Opacity: 4%, Blur: 20px) are reserved for active input fields or triggered modals to provide a sense of "lifting" off the glass.

## Shapes
The shape language is sophisticated and approachable. 
- **Standard Radius:** 0.5rem (8px) for small components like inputs and buttons.
- **Container Radius:** 1rem (16px) for chat bubbles and main content cards.
- **Interactive Elements:** Buttons utilize the `rounded-lg` (1rem) setting to feel tactile and modern without becoming overly playful or "bubbly."

## Components

### Chat Bubbles
- **Assistant:** Level 1 Glassmorphic surface (White 80% opacity). Border-left: 4px solid #10B981 to signify "Growth/Advice."
- **User:** Primary Color (#0F172A) with white text. High contrast to distinguish from assistant responses.

### Buttons
- **Primary:** Deep Navy background, white text, 16px radius.
- **Secondary:** Transparent background, 1px Deep Navy border.
- **Ghost/Action:** Emerald text with no border, used for "View Citation" or "Explore Fund."

### Compliance & Citations
- **Disclaimer Box:** Located at the footer of the chat or pinned to the bottom of the screen. Uses a subtle Slate-100 background, 12px radius, and `caption` typography.
- **Citation Tags:** Small pills (8px radius) using #F1F5F9 background with #475569 text. They appear inline or at the end of a response.

### Input Fields
- Chat input is a large, Level 1 Glassmorphic bar with a persistent shadow on focus. It includes a clear "Send" icon in Emerald when text is present.

### Cards (Fund Selection/FAQ)
- High-contrast headers using Outfit. Metrics (e.g., Expense Ratio, YTD Return) should be displayed in a clear tabular format within the card using Inter.