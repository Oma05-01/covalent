# 🏛️ Civic Incident Intake Taxonomy & SLA Mapping

This document outlines the two-tier hierarchical categorization system (`category` -> `subcategory`) and dynamic Service Level Agreement (SLA) mapping used by the AI extraction engine and Matrix Routing service.

---

## 📊 Summary Matrix

| Parent Category (`category`) | Valid Subcategories (`subcategory`) | Default SLA Tier |
| :--- | :--- | :--- |
| **`roads_infrastructure`** | `pothole_crater`, `drainage_flooding`, `bridge_walkway`, `street_lighting` | 24 Hours (1440m) |
| **`traffic_transport`** | `gridlock_obstruction`, `traffic_signal_fault`, `illegal_park_stop` | Mixed (120m / 1440m) |
| **`waste_environment`** | `refuse_dumping`, `noise_pollution`, `air_water_pollution`, `fallen_tree_hazard` | 24 Hours (1440m) |
| **`utilities_public`** | `transformer_fault`, `high_tension_hazard`, `public_pipe_burst` | Urgent / Critical |
| **`emergency_safety`** | `fire_outbreak`, `building_collapse`, `security_threat`, `road_accident` | **5 Minutes (Critical)** |
| **`greeting`** *(Non-Issue)* | `general_chat`, `inquiry`, `none` | N/A |

---

## 🔍 Detailed Category Breakdown

### 1. Roads & Infrastructure (`roads_infrastructure`)
Handles physical defects and structural maintenance of public roads, pedestrian pathways, and drainage systems.

* **`pothole_crater`** (SLA: `1440` mins / 24 hours)
  * *Scope:* Road surface damage, asphalt erosion, sinkholes, and unpaved road deterioration.
* **`drainage_flooding`** (SLA: `1440` mins / 24 hours)
  * *Scope:* Blocked gutters, overflowing street canals, and stormwater stagnation.
* **`bridge_walkway`** (SLA: `1440` mins / 24 hours)
  * *Scope:* Structural damage to pedestrian bridges, missing manhole covers, and broken sidewalks.
* **`street_lighting`** (SLA: `1440` mins / 24 hours)
  * *Scope:* Dead, flickering, or damaged municipal street lamps and solar poles.

---

### 2. Traffic & Transportation (`traffic_transport`)
Handles vehicular flow disruptions, transit infrastructure faults, and traffic law violations on public roads.

* **`gridlock_obstruction`** (SLA: `120` mins / 2 hours)
  * *Scope:* Severe vehicular congestion caused by broken-down vehicles, road blocks, or illegal checkpoints.
* **`traffic_signal_fault`** (SLA: `1440` mins / 24 hours)
  * *Scope:* Malfunctioning, dead, or misaligned automated traffic lights.
* **`illegal_park_stop`** (SLA: `1440` mins / 24 hours)
  * *Scope:* Unauthorized commercial parking, bus stops blocking walkways, or abandoned vehicles.

---

### 3. Waste & Environment (`waste_environment`)
Handles sanitation hazards, ecological pollution, and public space cleanliness.

* **`refuse_dumping`** (SLA: `1440` mins / 24 hours)
  * *Scope:* Illegal street trash heaps, overflowing municipal bins, and uncollected waste.
* **`noise_pollution`** (SLA: `1440` mins / 24 hours)
  * *Scope:* Excessive public decibel levels from religious centers, clubs, or industrial generators.
* **`air_water_pollution`** (SLA: `1440` mins / 24 hours)
  * *Scope:* Chemical dumping in public canals, industrial smoke emissions, and open burning.
* **`fallen_tree_hazard`** (SLA: `1440` mins / 24 hours)
  * *Scope:* Trees or large branches blocking roads, walkways, or resting on non-electrical structures.

---

### 4. Public Utilities (`utilities_public`)
Handles municipal grid power, water distribution infrastructure, and high-voltage electrical assets.

* **`transformer_fault`** (SLA: `120` mins / 2 hours)
  * *Scope:* Exploded, smoking, or vandalized community distribution transformers and feeder pillars.
* **`high_tension_hazard`** (SLA: **`5` mins / Emergency**)
  * *Scope:* Fallen high-voltage power lines, sparking poles, or live cables touching buildings/roads.
* **`public_pipe_burst`** (SLA: `120` mins / 2 hours)
  * *Scope:* Ruptured municipal water mains, flooding from public plumbing, or broken fire hydrants.

---

### 5. Emergency & Safety (`emergency_safety`)
**🚨 CRITICAL TIER:** Active threats to human life, physical safety, or catastrophic structural failures.

* **`fire_outbreak`** (SLA: **`5` mins / Emergency**)
  * *Scope:* Active fires in public buildings, markets, residential blocks, or fuel tankers.
* **`building_collapse`** (SLA: **`5` mins / Emergency**)
  * *Scope:* Active structural collapse of bridges, residential buildings, or commercial scaffolding.
* **`security_threat`** (SLA: **`5` mins / Emergency**)
  * *Scope:* Active robbery, communal clashes, cultist unrest, or violent civil disturbance.
* **`road_accident`** (SLA: **`5` mins / Emergency**)
  * *Scope:* Vehicular collisions involving injuries, trapped passengers, or hazardous material spills.

---

### 6. System / Non-Issue (`greeting`)
Used by the LLM guardrail to trap conversational banter, system inquiries, and non-actionable messages.

* **`general_chat`**: Casual greetings ("Hello", "Good morning", "How are you").
* **`inquiry`**: General questions about what the bot does or how to report an issue.
* **`none`**: Messages that contain text but no identifiable civic issue or intent.

---

## 🛡️ Guardrail Rules & Extensions

1. **Private Domain Rejection:** Any issue occurring strictly *within* a private residence or compound (e.g., indoor plumbing leaks, private generator faults) is flagged as `is_public_domain: false` and rejected before database routing occurs.
2. **Dynamic Fallback Catch-All:** If an incident falls under a valid Parent Category but does not match any existing subcategory, the AI extracts it under the closest semantic fit, or the backend Matrix Router defaults to `subcategory: null` to route to the general departmental desk.