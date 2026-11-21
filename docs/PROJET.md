# Comment cette intégration a été construite

Ce document raconte la démarche : d'où part le projet, ce qui a été découvert, ce qui marche, ce qui ne marche pas. Il sert d'explication à la publication du dépôt.

## Point de départ

Un poêle **Iwona Pellets** (pellets, bois, ou les deux) équipé du contrôleur **P.W. KEY RK-2014KH**, famille RK-2014K/KW. L'objectif : le piloter depuis Home Assistant, en local, sans cloud : lire les températures et l'état, démarrer et arrêter.

Le contrôleur possède un port **RS485 Modbus**. Un convertisseur RS485 ⇄ WiFi/Ethernet (ici un **Elfin EW41**, équivalent de l'EW11) expose ce port sur le réseau.

## Sources utilisées

- La documentation Modbus du constructeur (tables de registres, fournies par Iwona Pellets). Elle n'est **pas redistribuée** dans ce dépôt.
- Une discussion de la communauté polonaise ArturHome sur ce contrôleur.
- Surtout, des **essais sur le vrai poêle**, via l'intégration elle-même (un service de lecture de registres sert à explorer le contrôleur).

## Ce qui a été fait

1. **Un fichier YAML Home Assistant** (capteurs Modbus), premier prototype basé sur la table de registres.
2. **Une vraie intégration personnalisée**, installable à la main ou via HACS : configuration par l'interface, lecture cyclique, entités traduites (français et anglais), tests automatisés.
3. **Des corrections issues des essais réels** : démarrage appui court / appui long, choix du combustible, etc.
4. **Des fonctions au-delà de la documentation**, découvertes par comparaison de lectures du contrôleur (voir ci-dessous).
5. **Une carte Lovelace animée** avec la photo de la cheminée, et un tableau de bord dédié.

## Architecture

- `protocol.py` : client Modbus minimal (RTU sur TCP « transparent », ou Modbus TCP), sans dépendance à Home Assistant. Le contrôleur ignore silencieusement les requêtes invalides : l'absence de réponse est donc traitée comme un refus.
- `registers.py` : table des registres et descriptions des entités, également sans dépendance à Home Assistant.
- `coordinator.py` : une lecture groupée par cycle, écritures protégées par une liste blanche.
- Plateformes : capteurs, capteurs binaires, interrupteur Start/Stop, nombres (consignes), sélecteurs, boutons, image.
- `www/` : la carte `iwona-stove-card.js` et la photo de fond, servies par l'intégration elle-même (rien à copier dans `www` de Home Assistant).
- `tests/` : un faux poêle Modbus (les deux modes de trame) et de faux modules Home Assistant. Ces tests vérifient notre logique, pas la compatibilité avec une version donnée de Home Assistant.

## Découvertes sur le contrôleur

| Sujet | Ce qui a été établi |
|---|---|
| Mode de combustible | Absent de la table documentée. Trouvé en comparant des lectures dans chaque mode : registre **10102** (0 pellet, 1 bois, 2 bois et pellet). Modifiable, avec garde-fous. |
| Démarrage | Écrire 1 = marche, 0 = arrêt dans le registre 102 (l'interrupteur Start/Stop en découle). La valeur 2 n'a pas d'effet différent. |
| Écran du contrôleur | Les registres 41000 à 41511 contiennent l'image de l'afficheur (128×64 pixels). Le décodage (octet bas = colonne de gauche, bit 0 = pixel du haut) a été validé en comparant quatre variantes sur une vraie capture. |
| Touches virtuelles | Le registre 41512 simule les touches du pupitre. Le code que la documentation appelle « Echap » est en pratique la touche **Start/Stop** : il n'est donc volontairement pas exposé. |
| Horloge | Après une coupure de courant, l'horloge repart de 2014. Les registres 109 à 115 permettent de la remettre à l'heure depuis Home Assistant. |
| État « ajout de bois » | Observé (code 22, non documenté) quand la fonction « Souffle / Ajouter du bois » est active sur le pupitre. |

## Ce qui ne fonctionne pas

- **Démarrage du bois avec allumage** : un appui long sur Start/Stop au pupitre lance l'allumage, mais aucune commande Modbus testée ne le reproduit (écriture 1 ou 2 dans le registre 102, touche virtuelle 41512 maintenue avec/sans répétition, divers timings) : on obtient seulement `work_wood`. Fonction abandonnée.

- **« Souffle / Ajouter du bois »** (réglage 1.13 de l'afficheur, registre 10113) : le registre a été identifié et se lit, mais le contrôleur **ignore toute écriture Modbus**, même en niveau d'accès SERVICE et menu ouvert. Il n'y a donc pas de bouton ; la fonction reste utilisable sur le pupitre. Une piste non retenue : rejouer le chemin du menu avec les touches virtuelles.
- Les entités « Écran » et « Touches » sont désactivées par défaut (lecture de 512 registres, et actions sur les menus du poêle).

## Sécurité

- L'intégration n'écrit que dans les réglages de base (registres 100 à 123), plus le mode de combustible (10102) et le clavier virtuel (41512, quatre touches seulement). Tout autre registre est refusé par le code.
- Les écritures sensibles sont relues après coup : si le contrôleur les ignore, une erreur claire s'affiche au lieu d'un faux succès.
- Un poêle est un appareil de chauffage. N'utilisez jamais cette intégration comme fonction de sécurité.

## État de validation

- Validé sur un poêle réel : communication, lectures, marche/arrêt, changement du mode de combustible dans les trois sens, lecture de l'image de l'écran.
- **Écrit et testé uniquement contre un poêle simulé** : mise à l'heure automatique, touches virtuelles, carte animée dans Home Assistant. Le codage du jour de la semaine (lundi = 0) est à vérifier sur l'afficheur.
- Retours de test bienvenus, avec les journaux (`logger: custom_components.iwona_pellets: debug`) et la référence exacte du contrôleur.

## Une note sur la méthode

L'intégration a été développée avec l'aide de l'assistant d'IA Claude (Anthropic), en dialogue avec le propriétaire du poêle, qui a effectué les essais sur l'appareil et validé chaque étape. Le code a été relu par les tests, pas par un audit externe : utilisez-le en connaissance de cause.

## Projet non officiel

Ce projet n'a aucun lien avec Iwona Pellets ni P.W. KEY.

## v0.11.0 — journal d'erreurs, export des réglages, thermostat virtuel

- Capteur « Dernière erreur » (diagnostic) : lit le journal 44000..44199 au démarrage et à chaque changement des registres d'erreur ; l'historique (30 derniers) est en attribut.
- Service `export_settings` : tous les réglages (valeur, min, max) par registre, lecture seule.
- Service `set_virtual_thermostat` (index 0..3, secondes 0..600) : écrit 42000+index. Le poêle décompte seul.
  **Le comportement réel n'est pas encore vérifié** : à tester poêle allumé (lire le registre 9 et la puissance pendant que le thermostat est actif puis expiré) avant d'écrire une régulation sur une sonde externe.

## v0.12.0 — régulation par sonde externe (thermostat virtuel 0)

- Option « Sonde de température de la pièce » (ex. `sensor.station_meteo_salle_a_manger_temperature`) ; elle crée l'interrupteur « Régulation par sonde externe » et les nombres consigne / hystérésis (21 °C / 0,5 °C par défaut, restaurés au redémarrage). Désactivée par défaut.
- À chaque lecture (15 s) : demande ON si T ≤ consigne − hystérésis, OFF si T ≥ consigne ; la demande est réécrite (≥ 120 s) à chaque lecture, donc elle expire seule si HA, la sonde (> 15 min) ou la liaison s'arrête. Poêle arrêté : jamais de demande.
- Test réel du 20/11/2026 : écrire 120 dans 42000 passe le registre 9 de 0 à 1 et le décompte tourne seul.
- Non vérifié : effet sur la puissance, et combinaison avec le thermostat interne (le poêle peut garder sa propre demande ; baisser les consignes 107/108 si besoin).
