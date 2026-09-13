# Blender game assets

## Make

Design assets for their gameplay role and visible size. Establish silhouette, proportion and primary/secondary/tertiary forms before surface detail. Give interactive, hazardous and decorative objects distinguishable shapes and value groups. Test hero assets as small silhouettes and from the actual gameplay camera; a close-up beauty render can conceal weak readability.

Use consistent units, pivots, sockets, modular dimensions, palette and material response. Preserve intentional asymmetry and authored landmarks so a scene does not look assembled from identical primitive stacks. Spend geometry and texture detail where it affects contour, motion or player attention. A stylized asset can use simple materials and still need deliberate form design.

Model for deformation, silhouette and repeated use. Choose topology, bevels, smooth/flat shading, UV seams, texel density, atlases and baking according to the asset, not a universal checklist. Keep an editable source before destructive export preparation. Bake procedural appearance when the runtime cannot reproduce it; do not assume Blender nodes survive GLB export.

Animation must communicate anticipation, action and recovery at gameplay speed. Test contact, foot sliding, loop seams, poses and clipping where relevant. Agree with the game maker whether movement comes from simulation or root motion, and who owns action/hit timing. Decorative animation cannot silently move gameplay colliders or delay an action.

Inspect the source, exported model and model in the game. Deliver `.blend`, dependencies, export settings/scripts and GLB together. Explain third-party asset provenance and permission when using external material; preserve attribution supplied with it. Do not call generated geometry an original Blender deliverable without actually opening/saving it through Blender and inspecting its export.

## Review

Inspect gameplay-camera views and runtime motion, not only studio renders. Check visual hierarchy, silhouette, scale, readable affordances, visible mesh quality, materials, animation, missing resources and collider fit. Check source editability and reproducible export. Budget decisions should be supported by exported/runtime measurements, because Blender mesh counts can differ from exported counts.
