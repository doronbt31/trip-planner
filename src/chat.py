"""AI trip assistant — system prompt builder and chat function."""
import os
from typing import Any

import anthropic

MODEL = "claude-opus-4-6"
MAX_TOKENS = 1024


def build_system_prompt(trip_data: dict[str, Any]) -> str:
    """Build a rich but concise system prompt from trip.yaml data."""
    trip_name = trip_data.get("name", "Family Trip")
    travelers = trip_data.get("travelers", [])
    legs = trip_data.get("legs", [])

    # Family summary
    family_lines = []
    for t in travelers:
        age = t.get("age_during_trip")
        role = t.get("role", "")
        line = f"- {t['name']} ({role}{', age ' + str(age) if age else ''})"
        family_lines.append(line)

    # Legs summary
    leg_lines = []
    for leg in legs:
        dates = leg.get("dates", {})
        date_str = f"{dates.get('start', '?')} → {dates.get('end', '?')}"
        leg_lines.append(f"- {leg.get('name', leg.get('id'))}: {date_str}")

        # Key booking info
        if leg.get("booking"):
            b = leg["booking"]
            leg_lines.append(f"  Cruise booking: #{b.get('number')}, cabin {b.get('cabin')}, {b.get('category')}")
            if b.get("balance_due"):
                leg_lines.append(f"  Balance due: ${b['balance_due']} by {b.get('balance_due_date')}")

        if leg.get("id") == "austria_flachau":
            flight = leg.get("logistics", {}).get("flight", {})
            if flight:
                leg_lines.append(f"  Flight: {flight.get('from')} → {flight.get('to')}, {flight.get('date')} {flight.get('departure')}–{flight.get('arrival')}, order {flight.get('order')}")
            car = leg.get("logistics", {}).get("car_rental", {})
            if car:
                leg_lines.append(f"  Car rental pickup/dropoff: {car.get('pickup')} — {car.get('notes', '')}")

    # Cruise itinerary
    cruise_leg = next((l for l in legs if l.get("id") == "cruise"), None)
    cruise_ports = []
    if cruise_leg:
        for port in cruise_leg.get("itinerary", []):
            if port.get("port") != "At sea" and port.get("coordinates"):
                arr = port.get("arrival") or "—"
                dep = port.get("departure") or "—"
                notes = f" ({port['notes']})" if port.get("notes") else ""
                cruise_ports.append(f"  {port['date']}: {port['port']} arr {arr} dep {dep}{notes}")

    # Stops with stroller info
    stop_lines = []
    for leg in legs:
        for day in leg.get("days", []):
            for stop in day.get("stops", []):
                stroller = " 🍼 stroller-friendly" if stop.get("stroller_friendly") else (" ⚠️ NOT stroller-friendly" if stop.get("stroller_friendly") is False else "")
                notes = f" — {stop['notes']}" if stop.get("notes") else ""
                stop_lines.append(f"- {stop['name']} [{stop.get('type', '')}]{stroller}{notes}")

    # Return/logistics
    return_info = trip_data.get("logistics", {}).get("return", {})
    return_str = ""
    if return_info:
        return_str = f"\nReturn: {return_info.get('date')}, {return_info.get('route')}, airport TBD ({return_info.get('departure_airport')})"

    prompt = f"""You are the personal trip assistant for the {trip_name}.

## Family
{chr(10).join(family_lines)}

## Trip Legs
{chr(10).join(leg_lines)}

## Cruise Ports
{chr(10).join(cruise_ports) if cruise_ports else "See cruise leg above."}

## All Stops (with stroller/accessibility notes)
{chr(10).join(stop_lines[:40])}
{return_str}

## Your Role
- Answer questions about this specific trip — dates, bookings, logistics, activities
- Give practical family travel advice (3 kids: 1yo, 6yo, 9yo)
- Flag stroller-friendly vs non-stroller-friendly when relevant
- Be concise — use bullet points over paragraphs
- Reference real booking numbers and dates from the trip data above
- When asked about packing, tailor advice to the actual destinations and season (August)
- The youngest child (Jordan, 1yo) needs: stroller access, baby food options, nap schedules considered
"""
    return prompt


def get_client() -> anthropic.Anthropic | None:
    """Return Anthropic client if API key is configured."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    return anthropic.Anthropic(api_key=api_key)


def chat(message: str, history: list[dict[str, str]], trip_data: dict[str, Any]) -> str:
    """Send a message and return the assistant reply."""
    client = get_client()
    if client is None:
        raise ValueError("ANTHROPIC_API_KEY not configured")

    system = build_system_prompt(trip_data)
    messages = history + [{"role": "user", "content": message}]

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=system,
        messages=messages,
    )
    return response.content[0].text
