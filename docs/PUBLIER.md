# Publier sur GitHub

1. Créez un dépôt **public** `ha-iwona-pellets` sur GitHub (sans README ni licence).
2. Dans le dossier du projet :
   ```
   git init -b main
   git add .
   git commit -m "Iwona Pellets 0.12.0"
   git remote add origin https://github.com/JVmaisGpeur/ha-iwona-pellets.git
   git push -u origin main
   ```
3. Onglet *Actions* : vérifiez que *hassfest*, *HACS* et *tests* sont verts.
4. Dépôt → *About* → ajoutez une description et les sujets (topics) `home-assistant`, `hacs`, `custom-component`, `modbus`. HACS l'exige.
5. *Releases* → *Create a new release* → tag `v0.12.0` (même numéro que `manifest.json`).
6. Dans Home Assistant : HACS → ⋮ → Dépôts personnalisés → l'URL du dépôt → catégorie *Intégration*.
