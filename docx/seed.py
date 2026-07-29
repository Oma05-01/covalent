from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

def create_taxonomy_docx():
    doc = Document()
    
    # Title & Subtitle
    title = doc.add_heading('Civic Incident Intake Taxonomy & SLA Mapping', 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    doc.add_paragraph(
        'This document outlines the two-tier hierarchical categorization system '
        '(category -> subcategory) and dynamic Service Level Agreement (SLA) mapping '
        'used by the AI extraction engine and Matrix Routing service.'
    )
    
    # Section 1: Summary Table
    doc.add_heading('Summary Matrix', level=1)
    
    table_data = [
        ("Parent Category", "Valid Subcategories", "Default SLA Tier"),
        ("roads_infrastructure", "pothole_crater, drainage_flooding, bridge_walkway, street_lighting", "24 Hours (1440m)"),
        ("traffic_transport", "gridlock_obstruction, traffic_signal_fault, illegal_park_stop", "Mixed (120m / 1440m)"),
        ("waste_environment", "refuse_dumping, noise_pollution, air_water_pollution, fallen_tree_hazard", "24 Hours (1440m)"),
        ("utilities_public", "transformer_fault, high_tension_hazard, public_pipe_burst", "Urgent / Critical"),
        ("emergency_safety", "fire_outbreak, building_collapse, security_threat, road_accident", "5 Minutes (Critical)"),
        ("greeting (Non-Issue)", "general_chat, inquiry, none", "N/A")
    ]
    
    table = doc.add_table(rows=len(table_data), cols=3)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = 'Table Grid'
    
    for row_idx, row_data in enumerate(table_data):
        row = table.rows[row_idx]
        for col_idx, text in enumerate(row_data):
            cell = row.cells[col_idx]
            cell.text = text
            if row_idx == 0:
                for run in cell.paragraphs[0].runs:
                    run.font.bold = True
                    
    doc.add_paragraph() # Spacing
    
    # Section 2: Detailed Breakdown
    doc.add_heading('Detailed Category Breakdown', level=1)
    
    categories = [
        ("1. Roads & Infrastructure (roads_infrastructure)", 
         "Handles physical defects and structural maintenance of public roads, pedestrian pathways, and drainage systems.",
         [
             ("pothole_crater", "1440 mins / 24 hours", "Road surface damage, asphalt erosion, sinkholes, and unpaved road deterioration."),
             ("drainage_flooding", "1440 mins / 24 hours", "Blocked gutters, overflowing street canals, and stormwater stagnation."),
             ("bridge_walkway", "1440 mins / 24 hours", "Structural damage to pedestrian bridges, missing manhole covers, and broken sidewalks."),
             ("street_lighting", "1440 mins / 24 hours", "Dead, flickering, or damaged municipal street lamps and solar poles.")
         ]),
        ("2. Traffic & Transportation (traffic_transport)",
         "Handles vehicular flow disruptions, transit infrastructure faults, and traffic law violations on public roads.",
         [
             ("gridlock_obstruction", "120 mins / 2 hours", "Severe vehicular congestion caused by broken-down vehicles, road blocks, or illegal checkpoints."),
             ("traffic_signal_fault", "1440 mins / 24 hours", "Malfunctioning, dead, or misaligned automated traffic lights."),
             ("illegal_park_stop", "1440 mins / 24 hours", "Unauthorized commercial parking, bus stops blocking walkways, or abandoned vehicles.")
         ]),
        ("3. Waste & Environment (waste_environment)",
         "Handles sanitation hazards, ecological pollution, and public space cleanliness.",
         [
             ("refuse_dumping", "1440 mins / 24 hours", "Illegal street trash heaps, overflowing municipal bins, and uncollected waste."),
             ("noise_pollution", "1440 mins / 24 hours", "Excessive public decibel levels from religious centers, clubs, or industrial generators."),
             ("air_water_pollution", "1440 mins / 24 hours", "Chemical dumping in public canals, industrial smoke emissions, and open burning."),
             ("fallen_tree_hazard", "1440 mins / 24 hours", "Trees or large branches blocking roads, walkways, or resting on non-electrical structures.")
         ]),
        ("4. Public Utilities (utilities_public)",
         "Handles municipal grid power, water distribution infrastructure, and high-voltage electrical assets.",
         [
             ("transformer_fault", "120 mins / 2 hours", "Exploded, smoking, or vandalized community distribution transformers and feeder pillars."),
             ("high_tension_hazard", "5 mins / Emergency", "Fallen high-voltage power lines, sparking poles, or live cables touching buildings/roads."),
             ("public_pipe_burst", "120 mins / 2 hours", "Ruptured municipal water mains, flooding from public plumbing, or broken fire hydrants.")
         ]),
        ("5. Emergency & Safety (emergency_safety)",
         "CRITICAL TIER: Active threats to human life, physical safety, or catastrophic structural failures.",
         [
             ("fire_outbreak", "5 mins / Emergency", "Active fires in public buildings, markets, residential blocks, or fuel tankers."),
             ("building_collapse", "5 mins / Emergency", "Active structural collapse of bridges, residential buildings, or commercial scaffolding."),
             ("security_threat", "5 mins / Emergency", "Active robbery, communal clashes, cultist unrest, or violent civil disturbance."),
             ("road_accident", "5 mins / Emergency", "Vehicular collisions involving injuries, trapped passengers, or hazardous material spills.")
         ])
    ]
    
    for cat_title, cat_desc, subs in categories:
        doc.add_heading(cat_title, level=2)
        doc.add_paragraph(cat_desc)
        for sub_name, sla, scope in subs:
            p = doc.add_paragraph(style='List Bullet')
            p.add_run(f"{sub_name} ").bold = True
            p.add_run(f"(SLA: {sla})\n").italic = True
            p.add_run(f"Scope: {scope}")
            
    # Section 3: Guardrails
    doc.add_heading('Guardrail Rules & Extensions', level=1)
    
    g1 = doc.add_paragraph(style='List Number')
    g1.add_run('Private Domain Rejection: ').bold = True
    g1.add_run('Any issue occurring strictly within a private residence or compound (e.g., indoor plumbing leaks, private generator faults) is flagged as is_public_domain: false and rejected before database routing occurs.')
    
    g2 = doc.add_paragraph(style='List Number')
    g2.add_run('Dynamic Fallback Catch-All: ').bold = True
    g2.add_run('If an incident falls under a valid Parent Category but does not match any existing subcategory, the AI extracts it under the closest semantic fit, or the backend Matrix Router defaults to subcategory: null to route to the general departmental desk.')
    
    doc.save('Civic_Intake_Taxonomy.docx')
    print("Successfully generated 'Civic_Intake_Taxonomy.docx' in the current directory.")

if __name__ == '__main__':
    create_taxonomy_docx()