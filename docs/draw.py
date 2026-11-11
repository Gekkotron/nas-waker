#!/usr/bin/env python3
"""Draw docs/wiring.svg (Dupont jumpers ESP32 -> Pi) and docs/schematic.svg.

    python3 docs/draw.py

No dependencies. Edit WIRES to change the wiring.
"""
from pathlib import Path

OUT = Path(__file__).resolve().parent
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"

# Raspberry Pi 4 header, physical pin -> signal name (rows 1-6 are labelled).
PI_PINS = {
    1: "3V3", 2: "5V", 3: "GPIO2", 4: "5V", 5: "GPIO3", 6: "GND",
    7: "GPIO4", 8: "GPIO14", 9: "GND", 10: "GPIO15", 11: "GPIO17", 12: "GPIO18",
}
# ESP32 DevKit V1 (30 pins), USB at the bottom, top to bottom.
ESP_LEFT = ["EN", "VP", "VN", "D34", "D35", "D32", "D33", "D25", "D26", "D27",
            "D14", "D12", "D13", "GND", "VIN"]
ESP_RIGHT = ["D23", "D22", "TX0", "RX0", "D21", "D19", "D18", "D5", "TX2", "RX2",
             "D4", "D2", "D15", "GND", "3V3"]

GREY = "#5c6370"
# (pi pin, esp pin, colour, name, role, tag position along the wire 0..1)
WIRES = [
    (2, "VIN", "#e5484d", "5V", "power: Pi 5 V → ESP32 regulator", 0.62),
    (6, "GND", GREY, "GND", "common ground", 0.80),
    (5, "D25", "#f5c518", "WAKE", "pulse low = wake the Pi from halt", 0.43),
    (11, "D26", "#3e8bff", "SHUTDOWN", "pulse low = clean shutdown", 0.50),
]


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text(x, y, s, size=12, fill="#c9d1d9", anchor="start", weight=400, family=SANS, extra=""):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{family}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}" font-weight="{weight}" {extra}>{esc(s)}</text>')


DEFS = """
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#111827"/><stop offset="1" stop-color="#0b1020"/>
    </linearGradient>
    <linearGradient id="pcbGreen" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#2f8a4c"/><stop offset="1" stop-color="#1d6136"/>
    </linearGradient>
    <linearGradient id="pcbBlack" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#26292f"/><stop offset="1" stop-color="#15171b"/>
    </linearGradient>
    <linearGradient id="metal" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#e3e6ea"/><stop offset="0.5" stop-color="#b9bec6"/>
      <stop offset="1" stop-color="#9097a1"/>
    </linearGradient>
    <linearGradient id="gold" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#f6d77a"/><stop offset="1" stop-color="#b8892b"/>
    </linearGradient>
    <filter id="shadow" x="-10%" y="-10%" width="120%" height="130%">
      <feDropShadow dx="0" dy="6" stdDeviation="8" flood-color="#000" flood-opacity="0.45"/>
    </filter>
    <filter id="wireShadow" x="-5%" y="-5%" width="110%" height="110%">
      <feDropShadow dx="0" dy="3" stdDeviation="2.5" flood-color="#000" flood-opacity="0.55"/>
    </filter>
    <marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0,0 L10,5 L0,10 z" fill="#c9d1d9"/></marker>
    <marker id="arrY" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M0,0 L10,5 L0,10 z" fill="#f5c518"/></marker>
    <marker id="arrB" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M0,0 L10,5 L0,10 z" fill="#3e8bff"/></marker>
    <marker id="arrR" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0,0 L10,5 L0,10 z" fill="#e5484d"/></marker>
  </defs>"""


def bezier(p0, p1, p2, p3, t):
    u = 1 - t
    return tuple(u**3 * a + 3 * u * u * t * b + 3 * u * t * t * c + t**3 * d
                 for a, b, c, d in zip(p0, p1, p2, p3))


# --------------------------------------------------------------------------- wiring.svg
def wiring():
    W, H = 1120, 930
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">', DEFS,
         f'<rect width="{W}" height="{H}" rx="22" fill="url(#bg)"/>',
         text(48, 62, "NAS waker · wiring", 28, "#f0f3f6", weight=700),
         text(48, 92, "4 female–female Dupont jumpers · ESP32 DevKit V1 (30-pin) → Raspberry Pi 4", 15, "#8b949e")]

    # ---- Raspberry Pi 4, header on the right edge, pin 1 at the top (SD-card end)
    px, py, pw, ph = 60, 150, 350, 560
    o.append(f'<g filter="url(#shadow)"><rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="18" '
             f'fill="url(#pcbGreen)" stroke="#145028" stroke-width="2"/></g>')
    for hx, hy in [(px + 24, py + 24), (px + pw - 24, py + 24), (px + 24, py + ph - 96)]:
        o.append(f'<circle cx="{hx}" cy="{hy}" r="9" fill="#0b1020" stroke="url(#gold)" stroke-width="4"/>')
    o.append(f'<rect x="{px+110}" y="{py+110}" width="64" height="70" rx="4" fill="url(#metal)" stroke="#6b7280"/>')
    o.append(text(px + 142, py + 150, "Wi-Fi", 10, "#374151", "middle", 700, MONO))
    o.append(f'<rect x="{px+110}" y="{py+230}" width="92" height="92" rx="6" fill="url(#metal)" stroke="#6b7280"/>')
    o.append(text(px + 156, py + 280, "BCM2711", 11, "#374151", "middle", 700, MONO))
    o.append(f'<rect x="{px+118}" y="{py+346}" width="76" height="56" rx="4" fill="#111" stroke="#333"/>')
    o.append(text(px + 156, py + 379, "RAM", 11, "#9ca3af", "middle", 600, MONO))
    for x0, w, lab in [(px + 30, 80, "ETH"), (px + 130, 64, "USB 2"), (px + 214, 64, "USB 3")]:
        o.append(f'<rect x="{x0}" y="{py+ph-62}" width="{w}" height="80" rx="4" fill="url(#metal)" stroke="#6b7280"/>')
        o.append(text(x0 + w / 2, py + ph + 6, lab, 11, "#374151", "middle", 700, MONO))
    for i, lab in enumerate(["USB-C", "HDMI0", "HDMI1"]):
        y0 = py + 110 + i * 70
        o.append(f'<rect x="{px-14}" y="{y0}" width="40" height="44" rx="4" fill="url(#metal)" stroke="#6b7280"/>')
        o.append(text(px + 6, y0 + 26, lab, 9, "#374151", "middle", 700, MONO,
                      f'transform="rotate(-90 {px+6} {y0+26})"'))
    o.append(f'<rect x="{px+40}" y="{py-8}" width="70" height="16" rx="3" fill="#9097a1"/>')
    o.append(text(px + 75, py - 14, "SD card", 10, "#8b949e", "middle", 600))
    o.append(text(px + 30, py + ph - 116, "Raspberry Pi 4 Model B", 15, "#e6f4ea", weight=700))
    o.append(text(px + 48, py + ph - 96, "circled numbers = physical pins,", 11, "#b7dfc4"))
    o.append(text(px + 48, py + ph - 81, "not GPIO names", 11, "#b7dfc4"))

    pitch, r = 24, 10
    hx_odd, hx_even = px + pw - 62, px + pw - 36
    hy0 = py + 52
    o.append(f'<rect x="{hx_odd-15}" y="{hy0-15}" width="56" height="{19*pitch+30}" rx="5" fill="#0f1115"/>')
    pin_xy = {n: (hx_odd if n % 2 else hx_even, hy0 + ((n - 1) // 2) * pitch) for n in range(1, 41)}
    wired_pi = {w[0]: w for w in WIRES}

    def pi_pin(n):
        x, y = pin_xy[n]
        shape = (f'<rect x="{x-r}" y="{y-r}" width="{2*r}" height="{2*r}" rx="2" fill="url(#gold)"/>' if n == 1
                 else f'<circle cx="{x}" cy="{y}" r="{r}" fill="url(#gold)"/>')
        return shape + text(x, y + 3.5, str(n), 9, "#3b2a05", "middle", 700, MONO)

    for n, lab in PI_PINS.items():
        if n % 2:
            x, y = pin_xy[n]
            w = wired_pi.get(n)
            col = (w[2] if w[2] != GREY else "#ffffff") if w else "#cfe8d6"
            o.append(text(x - r - 10, y + 4, lab, 12, col, "end", 700 if w else 500, MONO))
    o.append(text(hx_odd - 16, hy0 - 22, "SD-card end · pin 1 ▸", 10, "#cfe8d6", "end", 600))

    # ---- ESP32 DevKit V1
    ex, ey, ew, eh = 760, 110, 250, 752
    o.append(f'<g filter="url(#shadow)"><rect x="{ex}" y="{ey}" width="{ew}" height="{eh}" rx="16" '
             f'fill="url(#pcbBlack)" stroke="#3a3f4b" stroke-width="2"/></g>')
    mx, my, mw = ex + 50, ey + 18, ew - 100
    o.append(f'<rect x="{mx}" y="{my}" width="{mw}" height="192" rx="6" fill="#1b2a3a" stroke="#31465c"/>')
    ant = " ".join(f"{'M' if i == 0 else 'L'}{mx+14+i*14},{my+(14 if i % 2 == 0 else 44)}" for i in range(10))
    o.append(f'<path d="{ant}" fill="none" stroke="url(#gold)" stroke-width="4" stroke-linejoin="round"/>')
    o.append(f'<rect x="{mx+12}" y="{my+62}" width="{mw-24}" height="118" rx="5" fill="url(#metal)" stroke="#6b7280"/>')
    o.append(text(mx + mw / 2, my + 118, "ESP32-WROOM-32", 12, "#374151", "middle", 700, MONO))
    o.append(text(mx + mw / 2, my + 138, "Wi-Fi · MQTT", 11, "#4b5563", "middle", 500, MONO))
    epitch, ey0 = 28, ey + 250
    esp_xy = {}
    wired_esp = {w[1]: w for w in WIRES}
    for i, (lft, rgt) in enumerate(zip(ESP_LEFT, ESP_RIGHT)):
        y = ey0 + i * epitch
        esp_xy[lft] = (ex + 22, y)
        for x in (ex + 22, ex + ew - 22):
            o.append(f'<circle cx="{x}" cy="{y}" r="7" fill="#0f1115" stroke="url(#gold)" stroke-width="3.5"/>')
        w = wired_esp.get(lft)
        col = (w[2] if w[2] != GREY else "#ffffff") if w else "#8b949e"
        o.append(text(ex + 40, y + 4, lft, 12, col, "start", 700 if w else 500, MONO))
        o.append(text(ex + ew - 40, y + 4, rgt, 12, "#8b949e", "end", 500, MONO))
    vin_y = esp_xy["VIN"][1]
    rx_, ry_ = ex + 92, vin_y - 88
    o.append(f'<rect x="{rx_}" y="{ry_}" width="66" height="40" rx="3" fill="#1f2328" stroke="#e5484d" stroke-opacity="0.7"/>')
    o.append(f'<rect x="{rx_+14}" y="{ry_-10}" width="38" height="10" fill="#9097a1"/>')
    o.append(text(rx_ + 33, ry_ + 18, "AMS1117", 10, "#d0d7de", "middle", 700, MONO))
    o.append(text(rx_ + 33, ry_ + 32, "5V→3.3V", 9, "#ff8f92", "middle", 600, MONO))
    o.append(f'<rect x="{ex+ew/2-22}" y="{ey+eh-92}" width="44" height="36" rx="3" fill="#1f2328" stroke="#5c6370"/>')
    o.append(text(ex + ew / 2, ey + eh - 70, "CP2102", 9, "#8b949e", "middle", 600, MONO))
    for bx, lab in ((ex + 50, "EN"), (ex + ew - 80, "BOOT")):
        o.append(f'<rect x="{bx}" y="{ey+eh-48}" width="30" height="24" rx="4" fill="#d0d7de"/>'
                 f'<circle cx="{bx+15}" cy="{ey+eh-36}" r="7" fill="#30363d"/>')
        o.append(text(bx + 15, ey + eh - 54, lab, 9, "#8b949e", "middle", 600, MONO))
    o.append(f'<rect x="{ex+ew/2-26}" y="{ey+eh-26}" width="52" height="40" rx="5" fill="url(#metal)" stroke="#6b7280"/>')
    o.append(text(ex + ew / 2, ey + eh + 36, "micro-USB · first flash only", 11, "#8b949e", "middle", 500))
    o.append(text(ex + ew / 2, ey - 14, "ESP32 DevKit V1", 15, "#f0f3f6", "middle", 700))

    # ---- wires, then the header pins on top, then housings and tags
    curves = []
    for pin, epin, colour, name, role, tpos in WIRES:
        p0 = pin_xy[pin]
        p3 = esp_xy[epin]
        p1 = (p0[0] + 180, p0[1] - (18 if pin % 2 else 0))
        p2 = (p3[0] - 200, p3[1])
        curves.append((p0, p1, p2, p3))
        d = f"M{p0[0]},{p0[1]} C{p1[0]},{p1[1]} {p2[0]},{p2[1]} {p3[0]},{p3[1]}"
        edge = "#9aa1ab" if colour == GREY else "#000000"
        o.append(f'<g filter="url(#wireShadow)">'
                 f'<path d="{d}" fill="none" stroke="{edge}" stroke-opacity="0.6" stroke-width="10" stroke-linecap="round"/>'
                 f'<path d="{d}" fill="none" stroke="{colour}" stroke-width="7" stroke-linecap="round"/>'
                 f'<path d="{d}" fill="none" stroke="#ffffff" stroke-opacity="0.22" stroke-width="2" '
                 f'stroke-linecap="round" transform="translate(-1.5,-1.5)"/></g>')
    for n in range(1, 41):
        if n not in wired_pi:
            o.append(pi_pin(n))
    for (pin, epin, colour, name, role, tpos), (p0, p1, p2, p3) in zip(WIRES, curves):
        ring = "#9aa1ab" if colour == GREY else colour
        x, y = p0  # Dupont housing on the Pi pin, pin number on it
        o.append(f'<rect x="{x-12}" y="{y-12}" width="24" height="24" rx="3" fill="#15171b" stroke="{ring}" stroke-width="3"/>')
        o.append(text(x, y + 4, str(pin), 11, "#ffffff", "middle", 700, MONO))
        x, y = p3  # housing on the ESP32 pin
        o.append(f'<rect x="{x-10}" y="{y-10}" width="20" height="20" rx="3" fill="#15171b" stroke="{ring}" stroke-width="3"/>'
                 f'<rect x="{x-3}" y="{y-3}" width="6" height="6" fill="#30363d"/>')
    for (pin, epin, colour, name, role, tpos), c in zip(WIRES, curves):
        bx, by = bezier(*c, tpos)
        label = f"{name} · pin {pin} ({PI_PINS[pin]}) → {epin}"
        w = len(label) * 7.1 + 26
        fill = GREY if colour == GREY else colour
        fg = "#111827" if colour == "#f5c518" else "#ffffff"
        o.append(f'<g filter="url(#wireShadow)"><rect x="{bx-w/2:.1f}" y="{by-15:.1f}" width="{w:.1f}" height="30" rx="15" '
                 f'fill="{fill}" stroke="#0b1020" stroke-width="2"/></g>')
        o.append(text(bx, by + 4.5, label, 11.5, fg, "middle", 700, MONO))

    # ---- legend under the Pi
    ly = py + ph + 62
    o.append(text(60, ly, "Jumpers (female–female)", 13, "#f0f3f6", weight=700))
    for i, (pin, epin, colour, name, role, _) in enumerate(WIRES):
        y = ly + 26 + i * 24
        o.append(f'<rect x="60" y="{y-9}" width="30" height="9" rx="4.5" fill="{colour}"/>')
        o.append(text(102, y, f"ESP32 {epin:<4} → Pi pin {pin:<2} {'(' + PI_PINS[pin] + ')':<9} {role}", 12.5,
                      "#c9d1d9", family=MONO, extra='xml:space="preserve"'))
    o.append("</svg>")
    return "\n".join(o)


# ------------------------------------------------------------------------- schematic.svg
def schematic():
    W, H = 1120, 780
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">', DEFS,
         f'<rect width="{W}" height="{H}" rx="22" fill="url(#bg)"/>',
         text(48, 62, "NAS waker · schematic", 28, "#f0f3f6", weight=700),
         text(48, 92, "Power path and the two open-drain signal lines", 15, "#8b949e")]

    def box(x, y, w, h, title, sub="", stroke="#3a3f4b"):
        o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="#161b22" stroke="{stroke}" stroke-width="2"/>')
        o.append(text(x + 14, y + 25, title, 14, "#f0f3f6", weight=700))
        for i, line in enumerate(sub.split("\n") if sub else []):
            o.append(text(x + 14, y + 46 + i * 17, line, 12, "#8b949e"))

    def wire(d, colour="#c9d1d9", width=3, dash="", marker="arr"):
        da = f'stroke-dasharray="{dash}"' if dash else ""
        mk = f'marker-end="url(#{marker})"' if marker else ""
        o.append(f'<path d="{d}" fill="none" stroke="{colour}" stroke-width="{width}" {da} {mk} stroke-linecap="round"/>')

    # board outlines
    o.append('<rect x="210" y="128" width="410" height="472" rx="18" fill="#10261a" stroke="#2f8a4c" stroke-width="2"/>')
    o.append(text(230, 156, "Raspberry Pi 4", 16, "#8fe3a8", weight=700))
    o.append('<rect x="736" y="128" width="344" height="472" rx="18" fill="#161a22" stroke="#5c6370" stroke-width="2"/>')
    o.append(text(756, 156, "ESP32 DevKit V1", 16, "#d0d7de", weight=700))

    box(40, 182, 140, 84, "Power supply", "USB-C\n5.1 V · 3 A")
    box(236, 176, 170, 98, "5 V rail", "pins 2 & 4, straight\nfrom USB-C: live\nwhile the Pi is halted", "#e5484d")
    box(236, 316, 170, 98, "3.3 V rail (PMIC)", "SoC I/O, SD card,\nWi-Fi chip\npins 1 & 17", "#9ca3af")
    box(440, 316, 160, 98, "Bootloader", "WAKE_ON_GPIO=1\nwatches GPIO3 (pin 5)\n1.8 kΩ pull-up", "#f5c518")
    box(440, 458, 160, 98, "gpio-shutdown", "GPIO17 (pin 11) low\n→ power key →\nsystemd poweroff", "#3e8bff")
    box(760, 176, 150, 98, "VIN", "5 V in", "#e5484d")
    box(760, 316, 150, 98, "AMS1117 LDO", "5 V → 3.3 V\n~0.15 W as heat", "#e5484d")
    box(930, 316, 130, 98, "ESP32", "3.3 V logic\nWi-Fi · MQTT\nSNTP clock")
    box(760, 458, 300, 98, "GPIO25 · GPIO26  (open-drain)", "on  = pull the Pi pin to GND\noff = released, the Pi pull-up wins\nnever drives 3.3 V into the Pi",
        "#c9d1d9")

    wire("M180,224 L234,224", "#e5484d", 4, marker="arrR")
    wire("M406,224 L758,224", "#e5484d", 5, marker="arrR")
    o.append(text(582, 212, "red jumper · pin 2 → VIN", 12, "#ff8f92", "middle", 700, MONO))
    wire("M320,274 L320,314", "#9ca3af", 3)
    wire("M835,274 L835,314", "#e5484d", 4, marker="arrR")
    wire("M910,365 L928,365", "#e5484d", 3, marker="arrR")
    # the path we do NOT use
    wire("M406,342 C520,342 560,290 664,290 L758,290", "#e5484d", 2.5, "7 7", marker="")
    o.append('<g transform="translate(700,290)"><circle r="13" fill="#0b1020" stroke="#e5484d" stroke-width="2.5"/>'
             '<path d="M-6,-6 L6,6 M6,-6 L-6,6" stroke="#e5484d" stroke-width="3" stroke-linecap="round"/></g>')
    o.append(text(560, 272, "not used: Pi 3.3 V → ESP32 3V3", 12, "#ff8f92", "middle", 700, MONO))

    wire("M758,494 C700,494 670,365 604,365", "#f5c518", 4, marker="arrY")
    o.append('<rect x="646" y="424" width="66" height="38" rx="6" fill="#0b1020" fill-opacity="0.9"/>')
    o.append(text(678, 438, "D25", 12, "#f5c518", "middle", 700, MONO))
    o.append(text(678, 454, "→ pin 5", 12, "#f5c518", "middle", 700, MONO))
    wire("M758,522 C700,522 670,507 604,507", "#3e8bff", 4, marker="arrB")
    o.append('<rect x="642" y="534" width="74" height="38" rx="6" fill="#0b1020" fill-opacity="0.9"/>')
    o.append(text(678, 548, "D26", 12, "#79b0ff", "middle", 700, MONO))
    o.append(text(678, 564, "→ pin 11", 12, "#79b0ff", "middle", 700, MONO))

    wire("M320,600 L320,632 L910,632 L910,600", "#9aa1ab", 3, marker="")
    o.append(text(615, 624, "black jumper · GND pin 6 ↔ GND (common ground)", 12, "#c9d1d9", "middle", 700, MONO))

    notes = [("Why VIN and not 3.3 V", "#ffb3b5", 700),
             ("Wi-Fi bursts (~300 mA) stay off the Pi's 3.3 V rail, which feeds the SD card.", "#c9d1d9", 400),
             ("The 5 V pins are the raw input: the ESP32 keeps running while the Pi is halted.", "#c9d1d9", 400),
             ("The regulator only turns ~0.15 W into heat (≈ 1.5 kWh a year).", "#c9d1d9", 400)]
    y = 672
    o.append(f'<rect x="40" y="{y-22}" width="1040" height="104" rx="12" fill="#1a1410" stroke="#e5484d" stroke-opacity="0.5"/>')
    o.append(text(60, y + 2, notes[0][0], 13, notes[0][1], weight=700))
    for i, n in enumerate(notes[1:]):
        o.append(text(60, y + 24 + i * 19, "• " + n[0], 12.5, "#c9d1d9"))
    o.append("</svg>")
    return "\n".join(o)


if __name__ == "__main__":
    (OUT / "wiring.svg").write_text(wiring(), encoding="utf-8")
    (OUT / "schematic.svg").write_text(schematic(), encoding="utf-8")
    print("wrote", OUT / "wiring.svg", "and", OUT / "schematic.svg")
