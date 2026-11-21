# Registres Modbus de l'Iwona Pellets (RK-2014KH, firmware C407)

Relevé du 20/11/2026 sur le poêle réel. Le registre `1xxyy` correspond au réglage **xx.yy** du menu ; le minimum est à `+5000` (`15xxx`…) et le maximum à `+10000` (`20xxx`…).
Les libellés viennent de la lecture des écrans de l'afficheur (menus utilisateur et installateur). Un libellé sans nom = réglage présent en Modbus mais jamais affiché dans le menu.

| Registre | Réglage | Libellé | Valeur relevée | Min | Max | Unité | Remarque |
|---|---|---|---|---|---|---|---|
| 10101 | 1.01 | Taille des granulés (1.1) | 0 | 0 | 1 | mm | 0 = 6 mm, 1 = 8 mm (supposé) |
| 10102 | 1.02 | Type de combustible (1.2) | 1 | 0 | 2 |  | 0 pellet, 1 bois, 2 bois+pellet |
| 10103 | 1.03 | Température souhaitée pellet (1.3) | 110 | 35 | 120 | °C |  |
| 10104 | 1.04 | Température souhaitée bois (1.4) | 120 | 60 | 120 | °C |  |
| 10110 | 1.10 | Température des fumées (1.10) — lecture seule | 42 | 0 | — | °C | capteur |
| 10111 | 1.11 | Durée de fonctionnement du brûleur (1.11) — lecture seule | 1864 | 0 | — | h |  |
| 10112 | 1.12 | Nombre d'allumages (1.12) — lecture seule | 1922 | 0 | — |  |  |
| 10113 | 1.13 | Souffle / Ajouter du bois (1.13) | 0 | 0 | 1 |  | 0 NON, 1 OUI ; non modifiable en Modbus (ignoré) |
| 10114 | 1.14 | (libellé non lu) | 0 | 0 | 1 |  |  |
| 10115 | 1.15 | (libellé non lu) | 1 | 0 | 1 |  |  |
| 10116 | 1.16 | (libellé non lu) | 0 | 0 | 1 |  |  |
| 10120 | 1.20 | (libellé non lu) | 1 | 0 | 2 |  |  |
| 10129 | 1.29 | (libellé non lu) | 45 | 0 | — |  |  |
| 10130 | 1.30 | (libellé non lu) | 554 | 0 | — |  |  |
| 10201 | 2.01 | Langue (2.1) | 3 | 0 | 4 |  | 3 = français (max 4) |
| 10202 | 2.02 | Paramètres par défaut (2.2) | 0 | 0 | 1 |  | 0 NON, 1 OUI — remise à zéro d'usine, ne pas écrire |
| 10207 | 2.07 | (libellé non lu) | 41 | 0 | 3 |  |  |
| 10301 | 3.01 | Tours ventilateur à l'allumage (3.01) | 70 | 25 | 100 | % |  |
| 10302 | 3.02 | Vitesse ventilateur puissance maxi (3.02) | 65 | 30 | 100 | % |  |
| 10303 | 3.03 | Vitesse ventilateur puissance mini (3.03) | 30 | 25 | 65 | % |  |
| 10304 | 3.04 | Vitesse ventilateur extinction (3.04) | 60 | 25 | 100 | % |  |
| 10305 | 3.05 | Vitesse ventilateur nettoyage (3.05) | 100 | 25 | 100 | % |  |
| 10306 | 3.06 | Souffle automatique (3.06) | 0 | 0 | 1 |  | 0 NON, 1 OUI |
| 10307 | 3.07 | (libellé non lu) | 5 | 1 | 60 |  |  |
| 10308 | 3.08 | (libellé non lu) | 15 | 1 | 99 |  |  |
| 10309 | 3.09 | Temps souffle manuel (3.09) | 3 | 1 | 60 | min |  |
| 10310 | 3.10 | Vitesse ventilateur souffle (3.10) | 100 | 25 | 100 | % |  |
| 10311 | 3.11 | Temps d'allumage (3.11) | 60 | 0 | 400 | s |  |
| 10312 | 3.12 | Vitesse ventilateur allumage (3.12) | 30 | 25 | 100 | % |  |
| 10313 | 3.13 | Mesure vitesse ventilateur (3.13) | 1 | 0 | 1 |  | 0 NON, 1 OUI |
| 10315 | 3.15 | Détection blocage ventilateur (3.15) | 1 | 0 | 1 |  | 0 NON, 1 OUI |
| 10316 | 3.16 | Seuil de blocage (3.16) | 80 | 0 | 100 | % |  |
| 10317 | 3.17 | Retard détection blocage (3.17) | 10 | 0 | 180 | s |  |
| 10318 | 3.18 | Vitesse puissance mini (3.18) | 550 | 0 | 2400 | tr/min | à 30 % |
| 10319 | 3.19 | Vitesse puissance maxi (3.19) | 1100 | 0 | 2400 | tr/min | à 65 % |
| 10320 | 3.20 | Calibrage mini (3.20) | 550 | 0 | 2400 | tr/min |  |
| 10321 | 3.21 | Calibrage maxi (3.21) | 1100 | 0 | 2400 | tr/min |  |
| 10401 | 4.01 | Temps de chargement vis sans fin (4.01) | 5 | 1 | 99 | min |  |
| 10402 | 4.02 | Dose de combustible au démarrage (4.02) | 57 | 0 | 80 | s |  |
| 10403 | 4.03 | Cycle de démarrage combustible (4.03) | 22 | 1 | 250 | s |  |
| 10404 | 4.04 | Quantité combustible au démarrage (4.04) | 3 | 0 | 15 |  |  |
| 10405 | 4.05 | Allumage (4.05) | 100 | 1 | 999 | s |  |
| 10406 | 4.06 | Quantité combustible puissance maxi (4.06) | 21 | 1 | 50 | % |  |
| 10407 | 4.07 | Quantité combustible puissance mini (4.07) | 10 | 1 | 30 | % |  |
| 10408 | 4.08 | Sonde retour de feu vis sans fin (4.08) | 1 | 0 | 1 |  | 0 NON, 1 OUI |
| 10409 | 4.09 | Température retour de feu vis sans fin (4.09) | 80 | 20 | 99 | °C |  |
| 10410 | 4.10 | Limite ouverture trappe réservoir (4.10) | 4 | 1 | 30 | min |  |
| 10411 | 4.11 | Détection (4.11) | 0 | 0 | 1 |  | 0 NON, 1 OUI |
| 10412 | 4.12 | Temps augmentation dose granulés (4.12) | 3 | 0 | 20 | min |  |
| 10413 | 4.13 | Capteur trappe réservoir (4.13) | 1 | 0 | 1 |  | 0 NON, 1 OUI |
| 10414 | 4.14 | Retard dose allumage granulés (4.14) | 30 | 0 | 120 | s |  |
| 10415 | 4.15 | Fuel time during ignition (4.15) | 3 | 1 | 30 | min |  |
| 10416 | 4.16 | Température fumées max pour pellet (4.16) | 280 | 200 | 350 | °C |  |
| 10417 | 4.17 | Modulation température fumées pellet (4.17) | 10 | 0 | 100 | °C |  |
| 10418 | 4.18 | Allumage après démarrage courant (4.18) | 1 | 0 | 1 |  | 0 NON, 1 OUI |
| 10419 | 4.19 | Contrôle pompe à vacuum (4.19) | 0 | 0 | 1 |  | 0 NON, 1 OUI |
| 10420 | 4.20 | (libellé non lu) | 0 | 0 | 1 |  |  |
| 10501 | 5.01 | Augmentation température flamme (5.01) | 8 | 1 | 99 | °C |  |
| 10502 | 5.02 | Détection flamme, temps d'augmentation (5.02) | 20 | 1 | 500 | s |  |
| 10503 | 5.03 | Chute de température pendant perte de flamme (5.03) | 25 | 1 | 99 | °C |  |
| 10504 | 5.04 | Temps détection perte de flamme (5.04) | 40 | 1 | 500 | s |  |
| 10505 | 5.05 | Température d'urgence flamme pellet (5.05) | 70 | 30 | 500 | °C |  |
| 10506 | 5.06 | Avertissement temps flamme pellet (5.06) | 12 | 1 | 90 | min |  |
| 10507 | 5.07 | Température d'urgence flamme bois (5.07) | 80 | 30 | 500 | °C |  |
| 10508 | 5.08 | Temps d'urgence flamme bois (5.08) | 12 | 1 | 90 | min |  |
| 10601 | 6.01 | Temps d'allumage combustible (6.01) | 15 | 7 | 30 | min |  |
| 10602 | 6.02 | Nombre d'essais d'allumage (6.02) | 2 | 1 | 10 |  |  |
| 10603 | 6.03 | Allumage pellet, temps de stabilisation (6.03) | 7 | 1 | 99 | min |  |
| 10604 | 6.04 | Allumage bois, temps de stabilisation (6.04) | 10 | 1 | 99 | min |  |
| 10605 | 6.05 | Temps d'extinction du foyer (6.05) | 5 | 1 | 30 | min |  |
| 10606 | 6.06 | Temps fermeture mécanisme (6.06) | 200 | 50 | 400 |  | affiché « 200 °C » par le menu |
| 10607 | 6.07 | Postcombustion, temps maxi (6.07) | 15 | 1 | 30 | min |  |
| 10608 | 6.08 | Temps de travail de la bougie (6.08) | 7 | 1 | 15 | min |  |
| 10609 | 6.09 | Température de transition au bois (6.09) | 300 | 250 | 400 | °C |  |
| 10610 | 6.10 | Température d'alarme des fumées (6.10) | 350 | 350 | 400 | °C |  |
| 10611 | 6.11 | Passage au mode bois/pellet (6.11) | 1 | 0 | 1 |  | 0 NON, 1 OUI |
| 10701 | 7.01 | Temps d'ouverture mécanisme (7.01) | 145 | 1 | 900 | s |  |
| 10702 | 7.02 | Temps de fermeture mécanisme (7.02) | 115 | 1 | 900 | s |  |
| 10703 | 7.03 | Temps sans nettoyage (7.03) | 7 | 1 | 99 | h |  |
| 10704 | 7.04 | Renversement mécanisme (7.04) | 0 | 0 | 1 |  |  |
| 10705 | 7.05 | Demande de nettoyage chaque (7.05) | 60 | 0 | 1000 |  |  |
| 10706 | 7.06 | Nettoyer le brûleur chaque (7.06) | 1000 | 0 | 3000 | h |  |
| 11001 | 10.01 | Pilote turbine, mode (10.01) | 0 | 0 | 2 |  | 0 = auto |
| 11002 | 10.02 | Rotation mini turbine (10.02) | 40 | 40 | 100 | % |  |
| 11003 | 10.03 | Rotation maxi turbine (10.03) | 100 | 40 | 100 | % |  |
| 11004 | 10.04 | (libellé non lu) | 20 | 1 | 100 |  |  |
| 11005 | 10.05 | (libellé non lu) | 5 | 1 | 10 |  |  |
| 11006 | 10.06 | (libellé non lu) | 10 | 0 | 20 |  |  |
| 11007 | 10.07 | (libellé non lu) | 35 | 35 | 60 |  |  |
| 11008 | 10.08 | (libellé non lu) | 5 | 1 | 10 |  |  |
| 11101 | 11.01 | Température minimum granulés (11.01) | 35 | 35 | 90 | °C |  |
| 11102 | 11.02 | Température maximum granulés (11.02) | 120 | 90 | 150 | °C |  |
| 11103 | 11.03 | Température minimum bois (11.03) | 60 | 60 | 80 | °C |  |
| 11104 | 11.04 | Température maximum bois (11.04) | 120 | 90 | 150 | °C |  |
| 11105 | 11.05 | Hystérésis haut cheminée (11.05) | 20 | 1 | 99 | °C |  |
| 11106 | 11.06 | Hystérésis changement de puissance (11.06) | 1 | 1 | 9 | °C |  |
| 11107 | 11.07 | Hystérésis protection (11.07) | 2 | 1 | 5 | °C |  |
| 11108 | 11.08 | Température de surchauffe cheminée (11.08) | 150 | 90 | 170 | °C |  |
| 11109 | 11.09 | Modulation de puissance (11.09) | 1 | 0 | 1 |  | 0 NON, 1 OUI |
| 11110 | 11.10 | Facteur de modulation (11.10) | 15 | 1 | 20 |  |  |
| 11111 | 11.11 | (libellé non lu) | 0 | 0 | 1 |  |  |
| 11112 | 11.12 | (libellé non lu) | 5 | 1 | 99 |  |  |
| 11113 | 11.13 | Retard arrêt brûleur (11.13) | 5 | 0 | 200 | 0,1 h |  |
| 11114 | 11.14 | Capteur de température pièce (11.14) | 0 | 0 | 4 |  | 0 = terminal ; 0..4 selon max |
| 11115 | 11.15 | Chaudière supplémentaire / démarrage manuel (11.15) | 0 | 0 | 2 |  |  |
| 11116 | 11.16 | Protection surchauffe pièce (11.16) | 3 | 0 | 10 | °C |  |
| 11117 | 11.17 | Correction thermomètre (11.17) | 17 | 65436 | 100 | 0,1 °C | 17 = 1,7 °C |
| 11118 | 11.18 | Hystérésis haut cheminée avec retard (11.18) | 30 | 1 | 99 | °C |  |
| 11201 | 12.01 | Entrée d'air pour granulés (12.1) | 100 | 0 | 100 | % |  |
| 11202 | 12.02 | Entrée d'air pour bois (12.2) | 5 | 0 | 50 | % |  |
| 11203 | 12.03 | Accélération 1 (12.3) | 150 | 1 | 999 |  |  |
| 11204 | 12.04 | Accélération 2 (12.4) | 10 | 1 | 999 |  |  |
| 11205 | 12.05 | Accélération 3 (12.5) | 60 | 0 | 999 |  |  |
| 11206 | 12.06 | (libellé non lu) | 20 | 0 | 6500 |  |  |
| 11207 | 12.07 | (libellé non lu) | 270 | 200 | 300 |  |  |
| 11208 | 12.08 | (libellé non lu) | 300 | 270 | 450 |  |  |
| 11209 | 12.09 | Fermeture départ volet d'air (12.9) | 30 | 0 | 100 | s |  |
| 11210 | 12.10 | Type du volet d'air (12.10) | 0 | 0 | 1 |  | 0 = KEY |
| 11301 | 13.01 | Connexion WiFi/série : mode (13.1) | 1 | 0 | 1 |  | 1 = Modbus RTU |
| 11302 | 13.02 | Numéro d'appareil Modbus (13.2) | 1 | 1 | 247 |  | 1 |
| 11303 | 13.03 | Vitesse de la ligne Modbus (13.3) | 12 | 0 | 12 |  | 12 = 115200 bauds |
| 11304 | 13.04 | Format de trame Modbus (13.4) | 3 | 0 | 3 |  | 3 = 8N2 |
| 11305 | 13.05 | Niveau d'accès Modbus (13.5) | 3 | 0 | 3 |  | 3 = service |
| 11306 | 13.06 | Niveau d'accès du terminal (13.6) | 3 | 0 | 3 |  | 3 = service |
| 11307 | 13.07 | Retard additionnel Modbus (13.7) | 0 | 0 | 99 | ms |  |

Réglages vus dans le menu dont la valeur est 0 (absents du tableau ci-dessus) :

- `10203` — Sortie test (2.3) 
- `10314` — Vitesse actuelle ventilateur (3.14) — lecture 

## Autres zones lues

- `40000..40031` fabricant : « P.W. KEY (www.pwkey.eu) » ; `40032..40055` appareil : « RK-2014KH » ; `40056..40063` firmware : « C407 » ; `40064` heures brûleur (1864) ; `40065` allumages (1922).
- `41000..41511` image de l'écran, `41512` clavier virtuel, `41513` état du menu (0 = écran principal), `41999` drapeau terminal.
- `42000..42003` thermostats virtuels, `43000..43167` programmes journaliers, `44000..44199` journal d'erreurs.

## Remarques

- Les réglages installateur ne peuvent être changés qu'après le code d'accès ; en Modbus l'accès dépend du niveau (13.5 / 13.6 = service).
- Pendant le relevé, le réglage 5.08 a été modifié par erreur (12 → 19 min) puis remis à 12 ; tout le reste est resté identique (vérifié registre par registre).

## Carte officielle du constructeur (P.W. KEY, RK-2014K/KW)

Adresses logiques (1-based) ; sur le fil, l'adresse envoyée est celle-ci moins 1.

### 1..99 — états (lecture seule)
1 température chaudière · 2 eau chaude · 3 température alimentateur · 5 fumées · 12 flamme (1 invisible, 2 visible) · 14 entrée sécurité · 16 puissance ventilateur d'extraction (0..100) · 17 puissance ventilateur de soufflage · 18 alimentateur · 20 allumeur · 21 pompe chauffage · 22 pompe eau chaude · 23 mécanisme de nettoyage · 24 alarme · 31 position du volet · 32 sortie chaudière externe · 33 température pièce (capteur interne, 0,1 °C) · 34 température pièce (capteur supplémentaire) · 35 capteur capacitif · 36 température pièce finale · 37 tampon · 38 vitesse ventilateur (tr/min).

**6 – état du process** : 0 arrêt, 1 alimentation, 5 veille, 6 allumage (nettoyage), 7 allumage (principal), 8 stabilisation puissance (pellet), 9 puissance maxi, 10 puissance modulée, 11 puissance mini, 12 soufflage (pellet), 13 extinction, 14 postcombustion, 15 nettoyage (ouverture), 16 nettoyage (fermeture), 17 alarme (ouverture), 18 ouverture manuelle, 19 dose de démarrage, 20 stabilisation (bois), 21 fonctionnement (bois), 22 soufflage (bois).

**7 – erreurs (bits)** : 0 sonde chaudière, 1 sonde alimentateur, 2 sonde fumées, 3 STB, 4 entrée sécurité, 5 capteur capacitif (débourrage), 6 capteur capacitif (critique), 7 surchauffe chaudière, 8 allumage alimentateur, 9 allumage alimentateur détecté, 10 manque combustible (pellet), 11 manque combustible (bois), 12 flamme éteinte, 13 sonde eau chaude/tampon, 14 surchauffe tampon, 15 coupure courant / arrêt manuel.
**8 – erreurs n°2** : 0 ventilateur bloqué, 1 trop de bois.

### 100..123 — réglages de base
100 consigne chaudière · 101 eau chaude · 102 marche (0 stop, 1 start, **2 start avec appui long** — retiré de l'intégration) · 103 mode (0 hiver, 1 été) · 105 défaut (écrire 0 pour effacer) · 107 consigne jour (0,1 °C) · 108 consigne nuit · 109..115 date/heure · 116 programme (0 jour, 1 nuit, 2 arrêt, 3..5 PRG1..3) · 117 hystérésis thermostat · 118 luminosité · 119 luminosité en veille · 120 contraste · 121 vitesse turbine manuelle · 122/123 consigne tampon. Minimums `200..299`, maximums `300..399`.

### Autres zones
- `42000..42003` thermostats virtuels (1..600 s) · `43000..43167` programmes PRG1/2/3/vacances (bits de 15 min depuis lundi 0 h) · `43998` = 4 programmes · `44000..44199` journal d'erreurs (id 1..15 = erreur, 50..249 = date) · `44998` taille = 200.
- Clavier `41512` : 1 OK, 2 Esc, 3 Plus, 4 Moins, 5 Menu (+128 = répétition).
