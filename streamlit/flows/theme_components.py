"""Dara — custom HTML view components for the vibrant redesign.

These render the bespoke, mockup-matching pieces (heroes, cards, the match
reveal, the two-orb mediation motif, takeaways) that plain Streamlit widgets
can't express. They emit HTML via ``st.markdown(..., unsafe_allow_html=True)``.

Interactive controls (st.button, st.text_input, st.chat_input, st.chat_message)
stay native — HTML can't trigger Streamlit callbacks — so the pattern is:
render the visual with a component here, then place the native control beneath
it. The native widgets are already themed by ``flows.common._BRAND_CSS``.

All colours come from the redesign palette:
  rose #FF4D87 · iris #6D5EF6 · amber #FFB23E · mint #1FC8A9 · ink #1B1430
"""

from __future__ import annotations

import html as _html

import streamlit as st

ROSE, IRIS, AMBER, MINT, INK, MUTED = (
    "#FF4D87", "#6D5EF6", "#FFB23E", "#1FC8A9", "#1B1430", "#8C84A8",
)
GRAD = f"linear-gradient(105deg,{ROSE},{IRIS})"
_FR = "'Fraunces',Georgia,serif"
_HK = "'Hanken Grotesk',system-ui,sans-serif"


def _md(html_str: str) -> None:
    st.markdown(html_str, unsafe_allow_html=True)


def _esc(s) -> str:
    return _html.escape(str(s)) if s is not None else ""


def _gradient_text(text_html: str, size: str, weight: int = 900) -> str:
    return (
        f'<span style="font-family:{_FR};font-weight:{weight};font-size:{size};'
        f"line-height:1.02;letter-spacing:-.02em;background:{GRAD};"
        "-webkit-background-clip:text;background-clip:text;"
        f'-webkit-text-fill-color:transparent;color:transparent;">{text_html}</span>'
    )


def two_orbs(size: int = 26, gap: int = 8) -> str:
    """The signature mark: a rose orb and an iris orb meeting in the middle."""
    return (
        '<span style="display:inline-flex;vertical-align:middle;">'
        f'<span style="width:{size}px;height:{size}px;border-radius:50%;background:{ROSE};"></span>'
        f'<span style="width:{size}px;height:{size}px;border-radius:50%;background:{IRIS};'
        f'margin-left:-{gap}px;"></span></span>'
    )


def wordmark() -> str:
    return (
        '<span style="display:inline-flex;align-items:center;gap:10px;">'
        + two_orbs(16, 5)
        + f'<span style="font-family:{_HK};font-weight:800;letter-spacing:.4em;'
        f"font-size:13px;text-transform:uppercase;background:{GRAD};"
        "-webkit-background-clip:text;background-clip:text;"
        '-webkit-text-fill-color:transparent;color:transparent;">Dara</span></span>'
    )


def hero(title_html: str, subtitle: str = "", show_motif: bool = True) -> None:
    """Home / flow hero: wordmark, a floating two-orb motif, big Fraunces title."""
    motif = ""
    if show_motif:
        motif = (
            '<div style="position:relative;height:84px;margin:14px 0 4px;max-width:280px;">'
            f'<div style="position:absolute;left:14%;top:18px;width:48px;height:48px;border-radius:50%;'
            f"background:linear-gradient(135deg,#FF6F9C,{ROSE});box-shadow:0 12px 26px -8px rgba(255,77,135,.6);\"></div>"
            f'<div style="position:absolute;right:14%;top:18px;width:48px;height:48px;border-radius:50%;'
            f"background:linear-gradient(135deg,#8B7DF8,{IRIS});box-shadow:0 12px 26px -8px rgba(109,94,246,.6);\"></div>"
            f'<div style="position:absolute;left:50%;top:29px;transform:translateX(-50%);width:28px;height:28px;'
            f'border-radius:50%;background:{GRAD};box-shadow:0 0 0 6px rgba(255,255,255,.7);"></div></div>'
        )
    sub = (
        f'<p style="font-family:{_HK};color:{MUTED};font-size:18px;line-height:1.5;'
        f'margin:10px 0 0;max-width:560px;">{_esc(subtitle)}</p>'
        if subtitle else ""
    )
    _md(
        '<div style="margin:.2rem 0 1.2rem;">'
        f'<div style="margin-bottom:6px;">{wordmark()}</div>'
        f"{motif}"
        f'<h1 style="margin:.2rem 0 0;font-family:{_FR};font-weight:900;font-size:46px;'
        f'line-height:1.0;letter-spacing:-.02em;">{title_html}</h1>'
        f"{sub}</div>"
    )


def grad_word(text: str) -> str:
    """Inline gradient word for use inside a hero title (e.g. the name 'Dara')."""
    return _gradient_text(_esc(text), "inherit", 500).replace("font-weight:500", "font-weight:500;font-style:italic")


def section_label(text: str) -> None:
    _md(
        f'<div style="font-family:{_HK};font-weight:700;letter-spacing:.18em;'
        f"text-transform:uppercase;font-size:13px;color:{MUTED};margin:.4rem 0 .2rem;\">{_esc(text)}</div>"
    )


def flow_card(title: str, body: str, accent: str = ROSE, filled: bool = False) -> None:
    """A pickable flow card (Home). Place the native st.button right beneath it."""
    if filled:
        bg = f"linear-gradient(135deg,{accent},#FF7FA6)" if accent == ROSE else f"linear-gradient(135deg,{accent},#8B7DF8)"
        title_c, body_c, border = "#fff", "rgba(255,255,255,.92)", "transparent"
        shadow = f"0 18px 38px -16px {accent}99"
    else:
        bg, title_c, body_c, border, shadow = "#fff", accent, "#5A5478", "rgba(109,94,246,.16)", "0 16px 34px -24px rgba(31,22,51,.5)"
    _md(
        f'<div style="background:{bg};border:1px solid {border};border-radius:22px;padding:22px 24px;'
        f'box-shadow:{shadow};margin-bottom:10px;">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;">'
        f'<div style="font-family:{_FR};font-weight:700;font-size:24px;color:{title_c};">{_esc(title)}</div>'
        f'<div style="width:34px;height:34px;border-radius:50%;background:{"rgba(255,255,255,.22)" if filled else "rgba(109,94,246,.1)"};'
        f'display:flex;align-items:center;justify-content:center;font-size:18px;color:{title_c};">&#8594;</div></div>'
        f'<p style="font-family:{_HK};font-size:15px;line-height:1.5;margin:8px 0 0;color:{body_c};">{_esc(body)}</p></div>'
    )


def compat_ring(score: int, caption: str = "Compatibility") -> str:
    """A conic-gradient compatibility ring (returns HTML for inline use)."""
    s = max(0, min(100, int(score or 0)))
    return (
        f'<div style="position:relative;width:74px;height:74px;flex:none;border-radius:50%;'
        f"background:conic-gradient({ROSE} 0% {s}%,#EFE6F8 {s}% 100%);"
        'display:flex;align-items:center;justify-content:center;">'
        '<div style="width:56px;height:56px;border-radius:50%;background:#fff;display:flex;'
        'flex-direction:column;align-items:center;justify-content:center;">'
        f'<span style="font-family:{_FR};font-weight:900;font-size:21px;color:{INK};">{s}<span style="font-size:11px;">%</span></span>'
        "</div></div>"
    )


def _photo_block(photo_url, height: int, label: str = "photo") -> str:
    if photo_url:
        return (
            f'<div style="height:{height}px;background:#EBD9E4 center/cover no-repeat;'
            f"background-image:url('{_esc(photo_url)}');\"></div>"
        )
    return (
        f'<div style="height:{height}px;position:relative;'
        "background:repeating-linear-gradient(135deg,#EBD9E4,#EBD9E4 11px,#E3D2EC 11px,#E3D2EC 22px);\">"
        f'<div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;'
        f'font:600 12px ui-monospace,monospace;color:#A98FB0;letter-spacing:.08em;">[ {_esc(label)} ]</div></div>'
    )


def match_reveal(name, meta="", score=0, verdict="", reasons=None, photo_url=None) -> None:
    """The full match-reveal card: photo header, compatibility ring, reasons."""
    reasons = reasons or []
    dots = [ROSE, IRIS, AMBER]
    reason_html = "".join(
        f'<div style="display:flex;gap:9px;margin-bottom:7px;">'
        f'<span style="color:{dots[i % 3]};font-weight:800;">&#8226;</span>'
        f'<span style="color:#4A4364;">{_esc(r)}</span></div>'
        for i, r in enumerate(reasons)
    )
    name_meta = (
        f'<div style="position:absolute;left:22px;bottom:16px;color:#fff;text-shadow:0 2px 10px rgba(0,0,0,.45);">'
        f'<div style="font-family:{_FR};font-weight:700;font-size:26px;">{_esc(name)}</div>'
        + (f'<div style="font-family:{_HK};font-size:14px;opacity:.92;">{_esc(meta)}</div>' if meta else "")
        + "</div>"
    )
    verdict_html = (
        f'<div style="font-family:{_FR};font-weight:700;font-style:italic;font-size:17px;'
        f'line-height:1.25;color:{INK};">{_esc(verdict)}</div>'
        if verdict else ""
    )
    _md(
        f'<div style="border:1px solid rgba(109,94,246,.14);border-radius:22px;overflow:hidden;'
        f'background:#fff;box-shadow:0 22px 54px -32px rgba(31,22,51,.45);margin-bottom:14px;">'
        f'<div style="position:relative;">{_photo_block(photo_url, 240, "their photos")}'
        '<div style="position:absolute;left:0;right:0;bottom:0;height:90px;'
        'background:linear-gradient(to top,rgba(27,20,48,.6),transparent);"></div>'
        f"{name_meta}</div>"
        '<div style="padding:18px 20px;">'
        '<div style="display:flex;align-items:center;gap:14px;">'
        f"{compat_ring(score)}"
        f'<div><div style="font-family:{_HK};font-size:12px;font-weight:700;letter-spacing:.08em;'
        f'text-transform:uppercase;color:{MUTED};">Dara\'s verdict</div>{verdict_html}</div></div>'
        + (f'<div style="font-family:{_HK};font-size:14px;line-height:1.5;margin-top:14px;">{reason_html}</div>' if reason_html else "")
        + "</div></div>"
    )


def match_list_card(name, meta="", score=None, photo_url=None) -> None:
    """Compact match/suggestion row. Put native action buttons beneath it."""
    score_html = (
        f'<div style="font-family:{_HK};font-size:12px;color:{IRIS};font-weight:700;margin-top:2px;">{int(score)}% compatible</div>'
        if score is not None else ""
    )
    avatar = (
        f"background:#EBD9E4 center/cover no-repeat;background-image:url('{_esc(photo_url)}');"
        if photo_url else
        "background:repeating-linear-gradient(135deg,#EBD9E4,#EBD9E4 7px,#E3D2EC 7px,#E3D2EC 14px);"
    )
    _md(
        '<div style="background:#fff;border:1px solid rgba(109,94,246,.12);border-radius:18px;padding:13px;'
        'display:flex;gap:13px;align-items:center;box-shadow:0 12px 30px -26px rgba(31,22,51,.5);margin-bottom:8px;">'
        f'<div style="width:54px;height:54px;border-radius:14px;flex:none;{avatar}"></div>'
        f'<div style="flex:1;"><div style="font-family:{_HK};font-weight:700;font-size:16px;color:{INK};">{_esc(name)}'
        + (f' <span style="font-weight:500;color:{MUTED};">&middot; {_esc(meta)}</span>' if meta else "")
        + f"</div>{score_html}</div></div>"
    )


def mediation_orbs(a_name="Their Dara", b_name="Your Dara", topic="") -> None:
    """The two-Daras-meeting motif used on the mediation screen."""
    topic_html = (
        f'<div style="text-align:center;margin-bottom:10px;"><span style="display:inline-block;'
        f"font-family:{_HK};font-size:13px;font-weight:700;color:#0E9E84;background:#D6F2EA;"
        f'padding:6px 14px;border-radius:999px;">Topic &middot; {_esc(topic)}</span></div>'
        if topic else ""
    )
    _md(
        f"{topic_html}"
        '<div style="position:relative;height:96px;max-width:420px;margin:0 auto 6px;">'
        f'<div style="position:absolute;left:16%;top:16px;text-align:center;">'
        f"<div style=\"width:56px;height:56px;border-radius:50%;background:linear-gradient(135deg,#FF6F9C,{ROSE});"
        'box-shadow:0 12px 26px -8px rgba(255,77,135,.6);"></div>'
        f'<div style="font:700 11px {_HK};margin-top:6px;color:{MUTED};">{_esc(a_name)}</div></div>'
        f'<div style="position:absolute;right:16%;top:16px;text-align:center;">'
        f"<div style=\"width:56px;height:56px;border-radius:50%;background:linear-gradient(135deg,#8B7DF8,{IRIS});"
        'box-shadow:0 12px 26px -8px rgba(109,94,246,.6);"></div>'
        f'<div style="font:700 11px {_HK};margin-top:6px;color:{MUTED};">{_esc(b_name)}</div></div>'
        f'<div style="position:absolute;left:50%;top:30px;transform:translateX(-50%);width:24px;height:24px;'
        f'border-radius:50%;background:{GRAD};box-shadow:0 0 0 7px rgba(255,255,255,.7);"></div></div>'
    )


def takeaway(text: str, title: str = "Your takeaway") -> None:
    _md(
        f'<div style="background:linear-gradient(135deg,{MINT},#15A98E);border-radius:20px;padding:20px 22px;'
        'color:#fff;box-shadow:0 20px 40px -18px rgba(31,200,169,.55);margin:8px 0;">'
        f'<div style="font-family:{_HK};font-size:12px;font-weight:700;letter-spacing:.1em;'
        f'text-transform:uppercase;opacity:.85;margin-bottom:7px;">{_esc(title)}</div>'
        f'<div style="font-family:{_FR};font-weight:500;font-style:italic;font-size:18px;line-height:1.4;">{_esc(text)}</div></div>'
    )


def browse_card(name, meta="", bio="", prompts=None, photo_url=None, badge="") -> None:
    """Large browse profile card: photo header, name overlay, bio, prompt Q&As."""
    prompts = prompts or []
    badge_html = (
        f'<div style="position:absolute;right:14px;top:14px;background:rgba(255,255,255,.18);'
        "backdrop-filter:blur(6px);border:1px solid rgba(255,255,255,.4);border-radius:999px;"
        f'padding:5px 12px;color:#fff;font-size:12px;font-weight:700;">{_esc(badge)}</div>'
        if badge else ""
    )
    name_meta = (
        f'<div style="position:absolute;left:22px;bottom:16px;color:#fff;text-shadow:0 2px 10px rgba(0,0,0,.45);">'
        f'<div style="font-family:{_FR};font-weight:700;font-size:28px;">{_esc(name)}</div>'
        + (f'<div style="font-family:{_HK};font-size:14px;opacity:.92;">{_esc(meta)}</div>' if meta else "")
        + "</div>"
    )
    prompt_html = ""
    for pr in prompts:
        q, a = pr.get("prompt", ""), pr.get("answer", "")
        if not a:
            continue
        prompt_html += (
            '<div style="border-top:1px solid rgba(109,94,246,.1);padding:12px 0 0;margin-top:12px;">'
            f'<div style="font-family:{_HK};font-size:12px;font-weight:700;letter-spacing:.04em;'
            f'text-transform:uppercase;color:{IRIS};margin-bottom:3px;">{_esc(q)}</div>'
            f'<div style="font-family:{_FR};font-weight:500;font-size:18px;line-height:1.35;color:{INK};">{_esc(a)}</div></div>'
        )
    bio_html = (
        f'<p style="font-family:{_HK};font-size:15px;line-height:1.55;color:#4A4364;margin:0;">{_esc(bio)}</p>'
        if bio else ""
    )
    _md(
        '<div style="border:1px solid rgba(109,94,246,.14);border-radius:22px;overflow:hidden;'
        'background:#fff;box-shadow:0 22px 54px -32px rgba(31,22,51,.45);margin-bottom:12px;">'
        f'<div style="position:relative;">{_photo_block(photo_url, 300, "their photos")}'
        '<div style="position:absolute;left:0;right:0;bottom:0;height:110px;'
        'background:linear-gradient(to top,rgba(27,20,48,.66),transparent);"></div>'
        f"{badge_html}{name_meta}</div>"
        f'<div style="padding:18px 20px;">{bio_html}{prompt_html}</div></div>'
    )


def plan_card(name, price, blurb, perks=None, current=False, highlight=False) -> str:
    """Pricing tier card (returns HTML — render a column of these). The native
    upgrade button goes beneath it."""
    perks = perks or []
    if highlight:
        bg, title_c, body_c, perk_c, border = GRAD, "#fff", "rgba(255,255,255,.9)", "rgba(255,255,255,.95)", "transparent"
        shadow = "0 26px 56px -24px rgba(124,80,180,.6)"
    elif current:
        bg, title_c, body_c, perk_c, border = "#fff", INK, MUTED, "#4A4364", IRIS
        shadow = "0 16px 40px -28px rgba(31,22,51,.5)"
    else:
        bg, title_c, body_c, perk_c, border = "#fff", INK, MUTED, "#4A4364", "rgba(109,94,246,.14)"
        shadow = "0 16px 40px -28px rgba(31,22,51,.5)"
    perks_html = "".join(
        f'<div style="display:flex;gap:8px;margin-bottom:6px;font-family:{_HK};font-size:14px;'
        f'line-height:1.45;color:{perk_c};"><span style="color:{MINT if not highlight else "#fff"};'
        f'font-weight:800;">&#10003;</span><span>{_esc(p)}</span></div>'
        for p in perks
    )
    tag = (
        '<div style="position:absolute;right:14px;top:14px;font-family:'
        f'{_HK};font-size:10px;font-weight:800;letter-spacing:.08em;text-transform:uppercase;'
        'background:rgba(255,255,255,.22);color:#fff;padding:4px 9px;border-radius:999px;">Popular</div>'
        if highlight else ""
    )
    return (
        f'<div style="position:relative;background:{bg};border:1px solid {border};border-radius:20px;'
        f'padding:24px 22px;box-shadow:{shadow};height:100%;">'
        f"{tag}"
        f'<div style="font-family:{_HK};font-weight:800;font-size:14px;letter-spacing:.04em;'
        f'text-transform:uppercase;color:{title_c};opacity:.85;">{_esc(name)}</div>'
        f'<div style="font-family:{_FR};font-weight:900;font-size:42px;color:{title_c};margin:6px 0 2px;">{_esc(price)}</div>'
        f'<div style="font-family:{_HK};font-size:13px;color:{body_c};margin-bottom:16px;">{_esc(blurb)}</div>'
        f"{perks_html}</div>"
    )


def info_note(text: str, accent: str = MINT) -> None:
    _md(
        f'<div style="background:#fff;border:1px solid {accent}44;border-left:4px solid {accent};'
        'border-radius:12px;padding:13px 16px;margin:6px 0;">'
        f'<span style="font-family:{_HK};font-size:14px;line-height:1.5;color:#4A4364;">{text}</span></div>'
    )
