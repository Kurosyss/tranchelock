import math
import os
from playwright.sync_api import sync_playwright

def build_svg():
    # -------------------------------------------------------------
    # 1. Axonometric Geometry for the Vault Monolith
    # -------------------------------------------------------------
    angle_u = math.radians(23)
    angle_v = math.radians(157)
    dx_u, dy_u = math.cos(angle_u), math.sin(angle_u)
    dx_v, dy_v = math.cos(angle_v), math.sin(angle_v)

    L = 175.0   # length of slab along u
    D = 120.0   # depth of slab along v
    H = 20.0    # vertical plate thickness

    def slab_svg(x0, y0, top_col, left_col, right_col, stroke_col, is_released=False):
        p0 = (x0, y0)
        p1 = (x0 + L * dx_u, y0 + L * dy_u)
        p2 = (x0 + L * dx_u + D * dx_v, y0 + L * dy_u + D * dy_v)
        p3 = (x0 + D * dx_v, y0 + D * dy_v)

        p1_b = (p1[0], p1[1] + H)
        p2_b = (p2[0], p2[1] + H)
        p3_b = (p3[0], p3[1] + H)

        top_d = f"M {p0[0]:.1f},{p0[1]:.1f} L {p1[0]:.1f},{p1[1]:.1f} L {p2[0]:.1f},{p2[1]:.1f} L {p3[0]:.1f},{p3[1]:.1f} Z"
        left_d = f"M {p3[0]:.1f},{p3[1]:.1f} L {p2[0]:.1f},{p2[1]:.1f} L {p2_b[0]:.1f},{p2_b[1]:.1f} L {p3_b[0]:.1f},{p3_b[1]:.1f} Z"
        right_d = f"M {p2[0]:.1f},{p2[1]:.1f} L {p1[0]:.1f},{p1[1]:.1f} L {p1_b[0]:.1f},{p1_b[1]:.1f} L {p2_b[0]:.1f},{p2_b[1]:.1f} Z"

        filter_attr = 'filter="url(#emeraldDropShadow)"' if is_released else ''

        text_content = ""
        if is_released:
            mid_top_x = (p0[0] + p2[0]) / 2.0
            mid_top_y = (p0[1] + p2[1]) / 2.0
            text_content = f"""
            <!-- Released plate top markings -->
            <g transform="translate({mid_top_x:.1f}, {mid_top_y:.1f}) rotate(23)">
              <text x="-78" y="3" font-family="'SF Mono', Menlo, Monaco, monospace" font-size="10" font-weight="700" fill="#ffffff" letter-spacing="0.08em">TRANCHE 01 // UNLOCKED &amp; SETTLED</text>
            </g>
            """

        return f"""
        <g {filter_attr}>
          <path d="{left_d}" fill="{left_col}" stroke="{stroke_col}" stroke-width="1" stroke-linejoin="round" />
          <path d="{right_d}" fill="{right_col}" stroke="{stroke_col}" stroke-width="1" stroke-linejoin="round" />
          <path d="{top_d}" fill="{top_col}" stroke="{stroke_col}" stroke-width="1.25" stroke-linejoin="round" />
          {text_content}
        </g>
        """

    # Monolith origin
    x_base = 880.0
    y_base = 86.0

    # Vacated cradle on monolith top
    p0_c = (x_base, y_base)
    p1_c = (x_base + L * dx_u, y_base + L * dy_u)
    p2_c = (x_base + L * dx_u + D * dx_v, y_base + L * dy_u + D * dy_v)
    p3_c = (x_base + D * dx_v, y_base + D * dy_v)

    cradle_svg = f"""
    <!-- Vacated cradle chamber on the master monolith -->
    <path d="M {p0_c[0]:.1f},{p0_c[1]:.1f} L {p1_c[0]:.1f},{p1_c[1]:.1f} L {p2_c[0]:.1f},{p2_c[1]:.1f} L {p3_c[0]:.1f},{p3_c[1]:.1f} Z" 
          fill="none" stroke="#10b981" stroke-width="1.2" stroke-dasharray="4 3" opacity="0.75" />
    <line x1="{p0_c[0]:.1f}" y1="{p0_c[1]:.1f}" x2="{p2_c[0]:.1f}" y2="{p2_c[1]:.1f}" stroke="#10b981" stroke-width="0.75" stroke-dasharray="2 4" opacity="0.35" />
    <text x="{(p0_c[0]+p2_c[0])/2 - 58:.1f}" y="{(p0_c[1]+p2_c[1])/2 + 2:.1f}" transform="rotate(23, {(p0_c[0]+p2_c[0])/2:.1f}, {(p0_c[1]+p2_c[1])/2:.1f})" 
          font-family="'Geist Mono', 'SF Mono', Menlo, monospace" font-size="8.5" font-weight="600" fill="#10b981" letter-spacing="0.1em" opacity="0.9">VACATED CHAMBER // PROOF VERIFIED</text>
    """

    # 3 Locked Slabs (Bottom to Top in the Chassis)
    slab_4 = slab_svg(x_base, y_base + 66, "#181816", "#11110f", "#20201d", "#333330")
    slab_3 = slab_svg(x_base, y_base + 44, "#1e1e1b", "#141412", "#262623", "#3a3a35")
    slab_2 = slab_svg(x_base, y_base + 22, "#242421", "#191917", "#2d2d29", "#44443e")

    # The Released Slab (Displaced along u by +68px, and slightly upward/forward)
    disp = 68.0
    x_rel = x_base + disp * dx_u
    y_rel = y_base + disp * dy_u - 6.0
    slab_1_released = slab_svg(x_rel, y_rel, "#10b981", "#047857", "#059669", "#34d399", is_released=True)

    # Trajectory Guides
    disp_guides = f"""
    <line x1="{p0_c[0]:.1f}" y1="{p0_c[1]:.1f}" x2="{x_rel:.1f}" y2="{y_rel:.1f}" stroke="#10b981" stroke-width="1.2" stroke-dasharray="3 3" />
    <line x1="{p1_c[0]:.1f}" y1="{p1_c[1]:.1f}" x2="{p1_c[0] + disp * dx_u:.1f}" y2="{p1_c[1] + disp * dy_u - 6.0:.1f}" stroke="#10b981" stroke-width="1.2" stroke-dasharray="3 3" />
    <line x1="{p2_c[0]:.1f}" y1="{p2_c[1]:.1f}" x2="{p2_c[0] + disp * dx_u:.1f}" y2="{p2_c[1] + disp * dy_u - 6.0:.1f}" stroke="#10b981" stroke-width="1.2" stroke-dasharray="3 3" />
    <line x1="{p3_c[0]:.1f}" y1="{p3_c[1]:.1f}" x2="{p3_c[0] + disp * dx_u:.1f}" y2="{p3_c[1] + disp * dy_u - 6.0:.1f}" stroke="#10b981" stroke-width="1.2" stroke-dasharray="3 3" />
    """

    # -------------------------------------------------------------
    # 2. Bespoke Display Typography for "TRANCHELOCK"
    # -------------------------------------------------------------
    # Sliced architectural lettering: height 64px, stem 12px
    def render_T(ox, oy):
        return f"""
        <g transform="translate({ox}, {oy})">
          <polygon points="4,0 38,0 38,11 25,11 25,32 13,32 13,11 0,11 0,4" fill="#121212" />
          <polygon points="14,34 26,34 26,64 14,64" fill="#121212" />
        </g>
        """

    def render_R(ox, oy):
        return f"""
        <g transform="translate({ox}, {oy})">
          <path d="M 0,0 L 26,0 C 35,0 38,4 38,16 C 38,26 33,32 24,32 L 0,32 Z M 12,10 L 12,22 L 23,22 C 25,22 27,20 27,16 C 27,12 25,10 23,10 Z" fill="#121212" />
          <polygon points="0,34 12,34 12,64 0,64" fill="#121212" />
          <polygon points="16,34 24,34 38,64 26,64" fill="#121212" />
        </g>
        """

    def render_A(ox, oy):
        return f"""
        <g transform="translate({ox}, {oy})">
          <polygon points="14,0 26,0 34,32 23,32 20,18 17,32 6,32" fill="#121212" />
          <polygon points="7,34 18,34 12,64 0,64" fill="#121212" />
          <polygon points="22,34 33,34 39,64 27,64" fill="#121212" />
        </g>
        """

    def render_N(ox, oy):
        return f"""
        <g transform="translate({ox}, {oy})">
          <polygon points="0,0 12,0 12,32 0,32" fill="#121212" />
          <polygon points="26,0 38,0 38,32 26,32" fill="#121212" />
          <polygon points="12,0 24,32 14,32" fill="#121212" />
          <polygon points="0,34 12,34 12,64 0,64" fill="#121212" />
          <polygon points="26,34 38,34 38,64 26,64" fill="#121212" />
          <polygon points="15,34 25,34 37,64 27,64" fill="#121212" />
        </g>
        """

    def render_C(ox, oy):
        return f"""
        <g transform="translate({ox}, {oy})">
          <path d="M 36,10 L 36,0 L 14,0 C 4,0 0,6 0,20 L 0,32 L 12,32 L 12,18 C 12,12 14,10 22,10 L 36,10 Z" fill="#121212" />
          <path d="M 0,34 L 0,44 C 0,58 4,64 14,64 L 36,64 L 36,54 L 22,54 C 14,54 12,52 12,46 L 12,34 Z" fill="#121212" />
        </g>
        """

    def render_H(ox, oy):
        return f"""
        <g transform="translate({ox}, {oy})">
          <polygon points="0,0 12,0 12,32 0,32" fill="#121212" />
          <polygon points="26,0 38,0 38,32 26,32" fill="#121212" />
          <polygon points="12,23 26,23 26,32 12,32" fill="#121212" />
          <polygon points="0,34 12,34 12,64 0,64" fill="#121212" />
          <polygon points="26,34 38,34 38,64 26,64" fill="#121212" />
          <polygon points="12,34 26,34 26,43 12,43" fill="#121212" />
        </g>
        """

    def render_E(ox, oy):
        return f"""
        <g transform="translate({ox}, {oy})">
          <polygon points="0,0 34,0 34,10 12,10 12,23 28,23 28,32 0,32" fill="#121212" />
          <polygon points="0,34 28,34 28,42 12,42 12,54 34,54 34,64 0,64" fill="#121212" />
        </g>
        """

    def render_L(ox, oy):
        return f"""
        <g transform="translate({ox}, {oy})">
          <polygon points="0,0 12,0 12,32 0,32" fill="#121212" />
          <polygon points="0,34 12,34 12,54 34,54 34,64 0,64" fill="#121212" />
        </g>
        """

    def render_sovereign_O(ox, oy):
        # The Approved TrancheLock Mark serving as the letter 'O'
        # With signature emerald chevron
        return f"""
        <g transform="translate({ox}, {oy})">
          <!-- Squircle badge -->
          <rect x="0" y="0" width="64" height="64" rx="14" fill="#121212" />
          <!-- Inner frame -->
          <rect x="11" y="11" width="42" height="42" rx="7" fill="none" stroke="#ffffff" stroke-width="4.5" stroke-linejoin="round" />
          <!-- Horizontal vault rail -->
          <line x1="11" y1="24" x2="53" y2="24" stroke="#ffffff" stroke-width="4.5" stroke-linecap="square" />
          <!-- Emerald Lock Chevron / Wedge -->
          <polyline points="15,29 32,41 49,29" fill="none" stroke="#10b981" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round" />
        </g>
        """

    def render_K(ox, oy):
        return f"""
        <g transform="translate({ox}, {oy})">
          <polygon points="0,0 12,0 12,32 0,32" fill="#121212" />
          <polygon points="12,28 32,0 42,0 18,32" fill="#121212" />
          <polygon points="0,34 12,34 12,64 0,64" fill="#121212" />
          <polygon points="16,34 24,34 42,64 30,64 12,38" fill="#121212" />
        </g>
        """

    # Assemble wordmark with tight, intentional architectural kerning
    # x ranges from 68 to ~536
    x_c = 68
    y_c = 114
    
    t_svg = render_T(x_c, y_c); x_c += 40
    r_svg = render_R(x_c, y_c); x_c += 40
    a_svg = render_A(x_c, y_c); x_c += 41
    n_svg = render_N(x_c, y_c); x_c += 40
    c1_svg = render_C(x_c, y_c); x_c += 38
    h_svg = render_H(x_c, y_c); x_c += 40
    e_svg = render_E(x_c, y_c); x_c += 41  # gap between TRANCHE and LOCK is optical 7px
    l_svg = render_L(x_c, y_c); x_c += 36
    o_svg = render_sovereign_O(x_c, y_c); x_c += 68
    c2_svg = render_C(x_c, y_c); x_c += 38
    k_svg = render_K(x_c, y_c)

    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 360" width="1200" height="360">
  <defs>
    <style>
      .bg {{ fill: #fbfbfa; }}
      .outer-frame {{ stroke: #e3e3df; stroke-width: 1.5; fill: none; }}
      .divider {{ stroke: #ebebeb; stroke-width: 1; stroke-dasharray: 4 4; }}
      .sub-kicker {{ font-family: 'SF Mono', Menlo, Monaco, Consolas, monospace; font-size: 10.5px; font-weight: 600; fill: #787873; letter-spacing: 0.16em; }}
      .proposition {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif; font-size: 20px; font-weight: 600; fill: #171717; letter-spacing: -0.03em; }}
      .subtext {{ font-family: 'SF Mono', Menlo, Monaco, Consolas, monospace; font-size: 11.5px; font-weight: 400; fill: #6e6e68; letter-spacing: 0.01em; }}
      .spec-rule {{ font-family: 'SF Mono', Menlo, Monaco, Consolas, monospace; font-size: 9px; font-weight: 600; fill: #999990; letter-spacing: 0.08em; }}
      .datum-mark {{ stroke: #999990; stroke-width: 1; fill: none; }}
      .axis-label {{ font-family: 'SF Mono', Menlo, Monaco, Consolas, monospace; font-size: 9px; font-weight: 600; fill: #787873; letter-spacing: 0.1em; }}
    </style>

    <!-- Emerald Glow for Released Tranche -->
    <filter id="emeraldDropShadow" x="-10%" y="-15%" width="125%" height="145%">
      <feDropShadow dx="0" dy="6" stdDeviation="10" flood-color="#10b981" flood-opacity="0.22" />
      <feDropShadow dx="0" dy="1" stdDeviation="3" flood-color="#000000" flood-opacity="0.08" />
    </filter>
  </defs>

  <!-- Canvas Background -->
  <rect width="1200" height="360" class="bg" />

  <!-- Outer Architectural Border Frame -->
  <rect x="16" y="16" width="1168" height="328" rx="10" class="outer-frame" />

  <!-- Precision Corner Datum Crops -->
  <path d="M 12 28 L 24 28 M 28 12 L 28 24" class="datum-mark" />
  <path d="M 1172 28 L 1184 28 M 1172 12 L 1172 24" class="datum-mark" />
  <path d="M 12 332 L 24 332 M 28 336 L 28 348" class="datum-mark" />
  <path d="M 1172 332 L 1184 332 M 1172 336 L 1172 348" class="datum-mark" />

  <!-- Asymmetric Structural Spine Divider -->
  <line x1="600" y1="28" x2="600" y2="332" class="divider" />

  <!-- ============================================================ -->
  <!-- LEFT: BESPOKE TYPOGRAPHIC BRAND ART                          -->
  <!-- ============================================================ -->
  <g transform="translate(0, 0)">
    <!-- Kicker -->
    <text x="68" y="74" class="sub-kicker">SOLANA // VERIFIED EXECUTION // PROGRAMMATIC SETTLEMENT</text>

    <!-- Custom Vectorized Graphic Wordmark -->
    {t_svg}
    {r_svg}
    {a_svg}
    {n_svg}
    {c1_svg}
    {h_svg}
    {e_svg}
    {l_svg}
    {o_svg}
    {c2_svg}
    {k_svg}

    <!-- High-Impact Proposition Statement -->
    <text x="68" y="222" class="proposition">Milestone-gated capital for autonomous coding agents.</text>

    <!-- Architectural Subtext -->
    <text x="68" y="254" class="subtext">Non-custodial escrow vaults governed by Ed25519 instruction introspection.</text>
    <text x="68" y="274" class="subtext">Capital unlocks tranche by tranche upon cryptographic proof of verified work.</text>

    <!-- Bottom Mechanical Spec Rule -->
    <g transform="translate(68, 312)">
      <line x1="0" y1="0" x2="480" y2="0" stroke="#e3e3df" stroke-width="1" />
      <text x="0" y="16" class="spec-rule">SPECIFICATION: 153-BYTE CANONICAL ATTESTATION · SOLANA DEVNET</text>
    </g>
  </g>

  <!-- ============================================================ -->
  <!-- RIGHT: MONUMENTAL AXONOMETRIC TRANCHE VAULT APPARATUS        -->
  <!-- ============================================================ -->
  <g transform="translate(0, 0)">
    <!-- Right Header Annotation -->
    <g transform="translate(640, 52)">
      <text x="0" y="0" class="axis-label">AXONOMETRIC VAULT SCHEMATIC // TRANCHE DISBURSEMENT REGISTER</text>
      <line x1="0" y1="10" x2="490" y2="10" stroke="#e3e3df" stroke-width="1" />
    </g>

    <!-- Monolith Slabs & Displacement Geometry -->
    {cradle_svg}
    {disp_guides}
    {slab_4}
    {slab_3}
    {slab_2}
    {slab_1_released}

    <!-- Displacement Callout Annotation -->
    <g transform="translate(1015, 88)">
      <line x1="0" y1="0" x2="60" y2="0" stroke="#10b981" stroke-width="1" />
      <circle cx="0" cy="0" r="2.5" fill="#10b981" />
      <text x="5" y="-6" font-family="'SF Mono', Menlo, Monaco, monospace" font-size="8.5" font-weight="700" fill="#10b981" letter-spacing="0.08em">VECTOR +68MM</text>
      <text x="5" y="14" font-family="'SF Mono', Menlo, Monaco, monospace" font-size="8" font-weight="500" fill="#787873">RELEASE TRAJECTORY</text>
    </g>

    <!-- Chassis Locked Status Indicator -->
    <g transform="translate(640, 248)">
      <line x1="0" y1="0" x2="36" y2="0" stroke="#787873" stroke-width="1" />
      <text x="44" y="3" font-family="'SF Mono', Menlo, Monaco, monospace" font-size="8.5" font-weight="600" fill="#787873" letter-spacing="0.06em">CHASSIS // TRANCHES 02–04 LOCKED IN ESCROW</text>
    </g>

    <!-- Monolith Foundation Datum Line -->
    <g transform="translate(640, 312)">
      <line x1="0" y1="0" x2="490" y2="0" stroke="#e3e3df" stroke-width="1" />
      <text x="0" y="16" class="spec-rule">DATUM A-01: NON-CUSTODIAL VAULT PDA</text>
      <text x="355" y="16" class="spec-rule">STATE: TRANCHE 01 UNLOCKED</text>
    </g>
  </g>
</svg>
"""
    return svg_content

if __name__ == "__main__":
    svg = build_svg()
    out_svg = "docs/assets/banner-final-candidate.svg"
    out_png = "docs/assets/banner-final-preview.png"

    with open(out_svg, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Saved: {out_svg}")

    # Render Preview via Playwright
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ background-color: #ffffff; width: 1200px; height: 360px; overflow: hidden; }}
  svg {{ width: 1200px; height: 360px; display: block; }}
</style>
</head>
<body>
{svg}
</body>
</html>"""

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1200, "height": 360}, device_scale_factor=2)
        page.set_content(html, wait_until="networkidle")
        page.wait_for_timeout(400)
        page.screenshot(path=out_png)
        browser.close()

    print(f"Saved: {out_png}")
