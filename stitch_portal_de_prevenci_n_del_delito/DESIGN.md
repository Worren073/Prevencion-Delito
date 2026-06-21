---
name: Civic Guardian
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
  secondary: '#5c5f61'
  on-secondary: '#ffffff'
  secondary-container: '#e0e3e5'
  on-secondary-container: '#626567'
  tertiary: '#000000'
  on-tertiary: '#ffffff'
  tertiary-container: '#1a1c1c'
  on-tertiary-container: '#838484'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dae2fd'
  primary-fixed-dim: '#bec6e0'
  on-primary-fixed: '#131b2e'
  on-primary-fixed-variant: '#3f465c'
  secondary-fixed: '#e0e3e5'
  secondary-fixed-dim: '#c4c7c9'
  on-secondary-fixed: '#191c1e'
  on-secondary-fixed-variant: '#444749'
  tertiary-fixed: '#e2e2e2'
  tertiary-fixed-dim: '#c6c6c7'
  on-tertiary-fixed: '#1a1c1c'
  on-tertiary-fixed-variant: '#454747'
  background: '#f8f9ff'
  on-background: '#0b1c30'
  surface-variant: '#d3e4fe'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  display-lg-mobile:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
    letterSpacing: 0.01em
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  base: 8px
  container-max: 1280px
  gutter: 24px
  margin-mobile: 16px
  margin-desktop: 40px
  stack-sm: 8px
  stack-md: 16px
  stack-lg: 32px
---

## Brand & Style
The design system is engineered to project **institutional authority, unwavering reliability, and modern transparency**. It serves a dual purpose: acting as a credible portal for government-level crime prevention data while remaining accessible and legible for the general public. 

The aesthetic is **Corporate Modern**, characterized by a rigorous adherence to structure, clarity, and precision. It avoids unnecessary decorative elements, favoring a functionalist approach where every visual cue serves to guide the user toward critical information or action. The emotional response should be one of "safety through order"—users should feel that the information is official, secure, and easy to navigate. High-quality whitespace and a logical card-based architecture are the primary drivers of this professional atmosphere.

## Colors
The palette is anchored in **Deep Institutional Blue**, providing the weight and seriousness required for a government entity. This is contrasted against a "Paper White" and "Mist Grey" background system to ensure the UI feels airy and modern rather than bureaucratic or heavy.

- **Primary (Deep Blue):** Used for navigation bars, headers, and high-level structural elements to establish authority.
- **Secondary (Light Grey):** Used for background surfaces and subtle containment to differentiate sections without creating visual noise.
- **Accent (Electric Blue):** Reserved exclusively for interactive elements, primary Calls-to-Action (CTAs), and highlighting critical status updates. This color provides the "modern" energy within the professional framework.
- **Semantic Colors:** Success (Green), Warning (Amber), and Error (Red) must be used in muted, professional tones that align with the primary palette's saturation levels.

## Typography
The system utilizes **Inter** for all roles to leverage its exceptional legibility and systematic, utilitarian feel. The typographic hierarchy is strictly enforced to ensure information density remains manageable.

- **Headlines:** Use tighter letter-spacing and heavier weights to command attention and establish a clear content structure.
- **Body Text:** Optimized for long-form reading of reports and guidelines, utilizing generous line-heights (1.5x) to reduce cognitive load.
- **Labels:** Used for metadata, tags, and small UI hints. Captions and small labels may use uppercase styling to differentiate them from body text without increasing font size.

## Layout & Spacing
This design system utilizes a **Fixed Grid** model for desktop to maintain an institutional "columnar" feel, transitioning to a fluid model for mobile devices.

- **Desktop (1280px+):** 12-column grid with 24px gutters. Content is centered to prevent scanning fatigue on ultra-wide monitors.
- **Tablet:** 8-column grid with 20px gutters. 
- **Mobile:** 4-column grid with 16px margins. 
- **Spacing Logic:** All spacing is based on an 8px baseline. Vertical rhythms (stacking) should prioritize large gaps (32px+) between major sections to emphasize the "clean" and "accessible" nature of the brand.

## Elevation & Depth
Elevation is handled via **Tonal Layers** and **Low-Contrast Outlines** rather than aggressive shadows. This maintains a flat, modern appearance that feels integrated with the screen.

- **Surface Level 0 (Background):** Light Grey (`#F8FAFC`).
- **Surface Level 1 (Cards/Containers):** Pure White (`#FFFFFF`) with a 1px border in a very light neutral tone. 
- **Interactive Depth:** Only the primary buttons and "active" cards use a subtle, highly-diffused ambient shadow (4px blur, 5% opacity) to indicate pressability.
- **Dividers:** Used sparingly. Instead of lines, use background color shifts to define distinct content areas.

## Shapes
The shape language is **Soft (Level 1)**. This subtle rounding of corners (4px for small elements, 8px for cards) softens the "sharpness" of government data, making the platform feel more approachable and modern without losing its professional edge. 

- **Small elements (Inputs, Buttons):** 4px radius.
- **Large elements (Cards, Modals):** 8px-12px radius.
- **Icons:** Use a consistent stroke-based style (2px weight) with slightly rounded terminals to match the UI's geometry.

## Components
Consistent component behavior is vital for maintaining the "authoritative" feel of the system.

- **Buttons:** Primary buttons use the Electric Blue accent with white text. Secondary buttons use a Deep Blue outline. All buttons have a fixed height (44px or 48px) to ensure touch-target accessibility.
- **Cards:** These are the primary vessel for information. They feature white backgrounds, subtle borders, and consistent 24px internal padding. Information is organized with clear headline-body-action hierarchies.
- **Input Fields:** Use a light grey fill and a 1px border that shifts to Electric Blue on focus. Labels are always positioned above the field for maximum legibility.
- **Status Chips:** Used for "Risk Levels" or "Report Status." These use a desaturated background of the semantic color (e.g., light red) with high-contrast text for accessibility.
- **Iconography:** Icons must be literal and descriptive. Avoid abstract metaphors. Use a consistent 24px bounding box for all UI icons.
- **Data Tables:** High density but with clear row stripping and ample horizontal padding to ensure complex prevention statistics remain readable.