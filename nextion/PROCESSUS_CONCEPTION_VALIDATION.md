# Processus obligatoire de conception des écrans Nextion

**Portée : toute modification Nextion**, même cosmétique : page, icône, composant, texte, police, couleur, animation, bouton, commande série, HMI ou TFT. Pour le petit écran : `NX4832K035_011`, 480 × 320, HMI 7.0.0.

**Règle bloquante : ne rien committer ni pousser sur `dev`, et ne pas annoncer « terminé », tant que le build des modifications et la comparaison des vrais PNG à la référence approuvée ne sont pas effectués avec succès.** Les tests pré-commit se font sur la copie de travail ou une branche de test, avant le commit, et non au moyen de commits successifs sur `dev`.

## 1. Figer les exigences
- Identifier le modèle, la version, la résolution, les pages, les fonctions à préserver et les changements demandés.
- Conserver le **dernier PNG / capture approuvé par l'utilisateur** comme référence. Une illustration conceptuelle n'est pas une référence de rendu compilé.
- Lister les critères précis : fond, couleurs, taille des textes, retours à la ligne, centrage, marges, icônes, états ON/OFF, positions et fonctions tactiles.

## 2. Modifier uniquement les sources réellement utilisées
- Éditer les sources `nextion/tests/NX4832K035_011/7.0.0/source/` et les générateurs `nextion/scripts/` pour le petit écran. Ne pas corriger le HMI/TFT par patch binaire.
- Préserver les IDs/ordres des composants, les événements `.down/.up`, variables, timers et échanges ESP32, sauf changement intentionnel et testé.
- **Un hotspot n'affiche pas d'icône.** Contrôler qu'une image visible est bien affectée à un vrai composant Nextion, et non uniquement insérée dans le PNG de simulation. Une étiquette ou image superposée peut intercepter le tactile : vérifier aussi ses événements.
- Vérifier les deux images réellement associées au HMI pour ON/OFF, avec une différence perceptible en 480 × 320.
- Dimensionner les rectangles de texte selon la police **réellement intégrée au HMI**. Vérifier les accents, lignes longues, centrage de chaque ligne et absence de rognage.

## 3. Simuler et compiler complètement AVANT commit

Depuis la racine du dépôt, sur les changements **non committés** :

```bash
set -o pipefail
pio run -e nextion 2>&1 | tee /tmp/flowio-nextion.log
```

Le test doit aller jusqu'à : tests Python → génération des sprites et aperçus → `nxwright check` → `nxwright build` → extraction/validation du HMI → `nxwright compile` → lecture du TFT → contrôle du manifeste, **sans aucune erreur**.

Vérifier concrètement les sorties du petit Nextion :

```text
.pio/nextion-output/FlowIO_Nextion_NX4832K035_011-7.0.0.HMI
.pio/nextion-output/FlowIO_Nextion_NX4832K035_011-7.0.0.tft
.pio/nextion-output/NX4832K035_011/7.0.0/FlowIO_Nextion_NX4832K035_011-7.0.0-pageHome.png
.pio/nextion-output/NX4832K035_011/7.0.0/FlowIO_Nextion_NX4832K035_011-7.0.0-pageHomeSwtch.png
```

**Attention :** `pio run -e nextion -t manifest` ne compile pas. `pio run` standard compile aussi le firmware ESP32 : une réussite Nextion ne prouve pas une réussite ESP32, et inversement. Compiler aussi l'ESP32 quand la modification l'exige.

## 4. Comparer les vrais PNG compilés à la référence approuvée — étape bloquante

1. **Ouvrir chaque PNG généré par cette compilation à la taille native** et le placer **côte à côte** avec le dernier visuel approuvé par l'utilisateur.
2. Contrôler les positions, le centrage, les marges, les tailles d'icônes, la couleur du fond, les contrastes, la disposition des huit commandes, les libellés complets, les retours à la ligne et toute superposition.
3. Vérifier séparément les rendus **ON et OFF**, lisibles à la résolution finale. Tester l'absence de disparition de l'icône après changement d'état et retour de veille.
4. Vérifier que les composants compilés dans le HMI **affichent vraiment** les icônes et polices correspondantes. Un PNG PIL correct ne garantit pas la visibilité d'un composant sur Nextion.
5. Contrôler dans Nextion Editor / un simulateur adapté les aspects que le PNG PIL ne reproduit pas fidèlement, notamment la police exacte et les événements. Si un tel contrôle n'est pas disponible, le déclarer **non vérifié**.
6. **Si un écart existe : corriger → recompiler → regénérer le PNG → recommencer la comparaison**, avant tout commit.

Les tests automatiques de pixels et de structure sont nécessaires, mais **ne remplacent jamais** cette inspection côte à côte avec le design validé.

## 5. Vérifier les comportements et les régressions
- Tester le fonctionnement des boutons, les couches d'objets, les handlers tactiles, Home, les commandes série, les états, les timers, les animations, les changements de page et la veille/réveil.
- Exécuter les tests `nextion/scripts/test_nextion_*.py` concernés et inspecter les échecs. Ne jamais affaiblir une assertion seulement pour obtenir un `PASS` ; vérifier le comportement attendu.
- **Compatibilité Python/Pillow (2027 et versions ultérieures) — contrôle obligatoire à chaque modification :** exécuter `python nextion/scripts/test_nextion_pillow_compat.py` (également appelé automatiquement par `pio run -e nextion` et dans la CI). Vérifier que les scripts n'emploient pas d'API Pillow obsolète ou dépréciée : notamment `Image.getdata()` (remplacer par `getpixel()` pour des coordonnées connues ou `get_flattened_data()` si disponible et adapté), `Image.ANTIALIAS` (remplacer par `Image.Resampling.LANCZOS`), `ImageFont.getsize()` et `ImageDraw.textsize()` (utiliser les méthodes `*bbox` / `*length` adaptées).
- **Hiérarchie ConfigStore partagée :** pour toute modification de navigation ou de module, modifier exclusivement les métadonnées `cfg_tree_aliases` et `cfg_tree_virtual_branches` dans les fichiers `src/Modules/**/text/cfgmods.fr.json`. Le firmware Nextion et l'interface Web sont générés depuis la même liste résolue. Exécuter `python scripts/tests/test_hmi_config_hierarchy.py`, contrôler les dossiers virtuels et le rendu sur l'écran réel ; ne jamais maintenir une seconde table de chemins C++ (voir `docs/core/nextion-configstore-hierarchy.md`).
- **Double transport Nextion UART / UDP :** dès qu'une page, un bouton, un événement ou le menu ConfigStore change, vérifier **les deux chemins**. Flow.io reste l'unique propriétaire de `ConfigMenuModel` : le dépôt `Flow.io-RemoteDisplay` ne doit contenir aucune copie de la liste des modules/alias. Vérifier `HmiUdpProtocol.h/.cpp` entre les deux dépôts, les six lignes du `ConfigViewSnapshot`, les `HmiEvent` de navigation et de saisie avec `contextRef`, le retour du clavier sur la même page, ainsi que l'affichage des boutons actifs/inactifs sur les TFT 6.0.0 et 7.0.0. Exécuter `python scripts/tests/test_hmi_udp_remote_compat.py --remote-root /chemin/Flow.io-RemoteDisplay --patched` après application du patch FCD, puis compiler **les deux firmwares**. Le test et la compilation CI ne remplacent pas un essai sur matériel réel. Voir `docs/core/nextion-configstore-hierarchy.md`.
- **Lire les avertissements** `DeprecationWarning`/`FutureWarning` des scripts de rendu, tests et compilation : les traiter comme un point à résoudre avant publication, **ne jamais masquer** un avertissement avec un filtre, une suppression de logs ou un test affaibli. Le contrôle statique couvre les appels connus dans nos scripts ; il ne remplace pas l'inspection des avertissements provenant de nouvelles API ou dépendances. Vérifier les versions Python/Pillow effectivement utilisées sur le PC et en CI.
- Contrôler `git diff` et les artefacts : aucune modification non demandée d'autres modèles, aucun PNG dans `binary/`, pas de source HMI dirty par la compilation.

## 6. Autorisation de commit (les six conditions sont requises)
- [ ] Sources/identifiants/commandes préservés ou changements explicitement documentés.
- [ ] **Compilation réellement exécutée sur les modifications non committées, et réussie.**
- [ ] **PNG compilé de chaque page modifiée ouvert et comparé côte à côte au PNG approuvé.**
- [ ] Rendu jugé conforme : vrais objets graphiques, bonnes polices, textes centrés et lisibles, deux états contrastés, aucun chevauchement.
- [ ] Tests de comportement et de non-régression effectués dans la mesure possible ; limitations signalées.
- [ ] **Compatibilité Python/Pillow vérifiée :** test `test_nextion_pillow_compat.py` réussi, aucun avertissement de dépréciation non traité dans les logs, et aucune API vouée à disparaître dans les versions futures (notamment Pillow 14).

**Si une condition n'est pas remplie ou vérifiable : aucun commit.** Corriger avant publication ou expliquer le blocage ; ne pas prétendre avoir simulé un environnement inaccessible. Après les six feux verts : commit → CI GitHub → contrôle des logs → promotion des sorties prévues. La validation sur le **Nextion physique** reste distincte et ne doit pas être revendiquée sans test matériel.

## 7. Si la compilation de l'utilisateur échoue malgré un CI vert

Demander/relever immédiatement : commande exacte (`pio run` ou `pio run -e nextion`), **première erreur** complète, branche et SHA local (`git rev-parse --short HEAD`), version Python et PlatformIO. Reproduire le chemin local si possible ou signaler ce qui n'a pas pu être reproduit. **Ne pas confondre succès CI Linux et succès sur le PC de l'utilisateur.** Ne pas changer le code par hypothèse ni annoncer « tout compile » sans son erreur locale.
