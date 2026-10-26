# Gap Analysis: Current automation vs a1f-simple requirements

## Current state (what exists)
- Current automation in repo does a lot more than placeholder replacement:
  - Uses coordinate overlays/layouts (a1_layout.json), background templates (a1_background*.pdf), fonts/styling, draws notices/watermarks
  - Does complex data modeling, validation policies, provisional numbering, issue dates, checkboxes via layout coordinates
  - Has multiple entry points and generators doing extra work
  - Tests/QA do structural/complex validations beyond "replaced placeholders correctly"

## What a1f-simple requires (strict)
- ONLY use `templates/a1_template_v1.pdf` (single template)
- ONLY replace placeholders with worker values (no styling/positioning/repositioning/fonts beyond what's needed for checkbox toggle)
- Checkbox handling is the ONLY exception - toggle empty/checked based on worker data without modifying template structure
- No notices/watermarks/styling/improvements
- Self-contained, own AGENTS.md, standalone workspace

## Gaps to address
| Area | Current | a1f-simple needed | Action |
|------|---------|-------------------|--------|
| Template selection | Multiple templates/backgrounds with switching logic | Single fixed template `a1_template_v1.pdf` | Strip all template switching, hardcode single template |
| Rendering | Coordinate overlays, canvas drawing, font registration, styling | Pure placeholder replacement via text span replacement (like current core does for tokens) | Keep only placeholder replacement logic; remove drawing/styling/notice code |
| Checkboxes | Handled via layout coordinates with stamps | Toggle checkbox states as they exist in PDF based on worker data | Isolate checkbox logic - only state changes, no repositioning |
| Notices/watermarks | Adds provisional/draft notices | None | Remove all notice drawing |
| Validation | Complex policy validation, gates | Minimal validation - ensure all required placeholders replaced? Or just do replacement | Keep minimal, don't add extra checks |
| Entry points | Many scripts with different behaviors | Minimal scripts focused on placeholder replacement | Simplify to core generation path |

## Antipatterns to avoid
- Drawing text/stamps outside of placeholder replacement
- Using coordinates/layout files to position things
- Adding "improvements" or notices
- Template switching logic
- Font/style customization
- Modifying template structure
