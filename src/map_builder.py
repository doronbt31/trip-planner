from typing import Any

import folium

LEG_CONFIG: dict[str, dict[str, str]] = {
    "copenhagen_pre": {"color": "blue", "icon": "home", "prefix": "fa"},
    "cruise": {"color": "orange", "icon": "ship", "prefix": "fa"},
    "austria_flachau": {"color": "green", "icon": "tree", "prefix": "fa"},
    "grossarl": {"color": "beige", "icon": "star", "prefix": "fa"},
}


def _popup(
    name: str,
    date: str | None = None,
    notes: str | None = None,
    stroller: bool | None = None,
    extra: str | None = None,
) -> folium.Popup:
    html = f"<b>{name}</b>"
    if date:
        html += f"<br><small style='color:#666'>{date}</small>"
    if notes:
        html += f"<br><span style='font-size:12px'>{notes}</span>"
    if stroller:
        html += "<br><span style='color:#2a9d8f;font-size:11px'>🍼 Stroller friendly</span>"
    if extra:
        html += f"<br><span style='font-size:11px'>{extra}</span>"
    return folium.Popup(html, max_width=260)


def _cruise_markers(leg: dict[str, Any], cfg: dict[str, str], m: folium.Map) -> list[list[float]]:
    coords_list: list[list[float]] = []
    for port in leg.get("itinerary", []):
        coords = port.get("coordinates")
        if not coords:
            continue  # skip "At sea" days
        lat, lon = coords
        coords_list.append([lat, lon])
        arrival = port.get("arrival") or "—"
        departure = port.get("departure") or "—"
        times = f"Arr: {arrival} · Dep: {departure}"
        folium.Marker(
            location=[lat, lon],
            popup=_popup(
                name=port["port"],
                date=str(port.get("date", "")),
                notes=port.get("notes"),
                extra=times,
            ),
            icon=folium.Icon(color=cfg["color"], icon=cfg["icon"], prefix=cfg["prefix"]),
        ).add_to(m)
    return coords_list


def _land_markers(leg: dict[str, Any], cfg: dict[str, str], m: folium.Map) -> list[list[float]]:
    coords_list: list[list[float]] = []
    for day in leg.get("days", []):
        date_label = str(day.get("date") or day.get("day_range", ""))
        for stop in day.get("stops", []):
            coords = stop.get("coordinates")
            if not coords:
                continue
            lat, lon = coords
            coords_list.append([lat, lon])
            folium.Marker(
                location=[lat, lon],
                popup=_popup(
                    name=stop["name"],
                    date=date_label,
                    notes=stop.get("notes"),
                    stroller=stop.get("stroller_friendly"),
                ),
                icon=folium.Icon(color=cfg["color"], icon=cfg["icon"], prefix=cfg["prefix"]),
            ).add_to(m)
    return coords_list


def _grossarl_marker(leg: dict[str, Any], cfg: dict[str, str], m: folium.Map) -> list[list[float]]:
    coords = leg.get("coordinates")
    if not coords:
        return []
    lat, lon = coords
    highlights = leg.get("highlights", [])
    extra = "<br>".join(f"• {h}" for h in highlights[:3])
    dates = leg.get("dates", {})
    folium.Marker(
        location=[lat, lon],
        popup=_popup(
            name=leg.get("name", "Großarl"),
            date=f"{dates.get('start', '')} → {dates.get('end', '')}",
            notes=leg.get("stay", {}).get("notes"),
            extra=extra,
        ),
        icon=folium.Icon(color=cfg["color"], icon=cfg["icon"], prefix=cfg["prefix"]),
    ).add_to(m)
    return [[lat, lon]]


def _arc_points(start: list[float], end: list[float], steps: int = 40) -> list[list[float]]:
    """Return interpolated points between two lat/lon pairs for a smooth arc."""
    return [
        [start[0] + (end[0] - start[0]) * i / steps,
         start[1] + (end[1] - start[1]) * i / steps]
        for i in range(steps + 1)
    ]


def _draw_flights(flights: list[dict[str, Any]], m: folium.Map) -> None:
    for flight in flights:
        from_c = flight.get("from_coords")
        to_c = flight.get("to_coords")
        if not from_c or not to_c:
            continue
        arc = _arc_points(from_c, to_c)
        folium.PolyLine(
            locations=arc,
            color="#2d3561",
            weight=3,
            opacity=0.55,
            dash_array="14 7",
            tooltip=f"✈️ {flight.get('label', '')}  ·  {flight.get('date', '')}",
        ).add_to(m)
        # Small plane marker at origin
        label = flight.get('label', '')
        folium.Marker(
            location=from_c,
            icon=folium.DivIcon(
                html=f'<div style="font-size:16px;line-height:1" title="{label}">✈️</div>',
                icon_size=(22, 22),
                icon_anchor=(11, 11),
            ),
            tooltip=f"✈️ {label}",
        ).add_to(m)


def build_map(trip_data: dict[str, Any]) -> str:
    m = folium.Map(location=[54, 10], zoom_start=4, tiles="CartoDB positron")

    for leg in trip_data.get("legs", []):
        leg_id = leg.get("id", "")
        cfg = LEG_CONFIG.get(leg_id, {"color": "gray", "icon": "info-sign", "prefix": "glyphicon"})

        if leg_id == "cruise":
            route_coords = _cruise_markers(leg, cfg, m)
        elif leg_id == "grossarl":
            route_coords = _grossarl_marker(leg, cfg, m)
        else:
            route_coords = _land_markers(leg, cfg, m)

        if len(route_coords) > 1:
            folium.PolyLine(
                locations=route_coords,
                color=cfg["color"],
                weight=2.5,
                opacity=0.8,
                dash_array="8",
                tooltip=leg.get("name", leg_id),
            ).add_to(m)

    # Draw flight routes
    flights = trip_data.get("logistics", {}).get("flights", [])
    if flights:
        _draw_flights(flights, m)

    return m._repr_html_()
