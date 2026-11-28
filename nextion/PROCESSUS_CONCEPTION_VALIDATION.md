# Processus obligatoire de conception des écrans Nextion

**Portée : toute modification Nextion**, même cosmétique : page, icône, composant, texte, police, couleur, animation, bouton, commande série, HMI ou TFT. Pour le petit écran : `NX4832K035_011`, 480 × 320, HMI 7.0.0.

**Règle bloquante : ne rien committer ni pousser sur `dev`, et ne pas annoncer « terminé », tant que le build, le contrat visuel du scénario demandé, le comportement tactile et les régressions n'ont pas été vérifiés indépendamment.** Les tests pré-commit se font sur une copie de travail ou une branche expérimentale. Une compilation verte ou un PNG identique n'est pas une validation complète.

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

## 4. Contrat de prévisualisation : le PNG doit montrer le scénario demandé

**Trois sources distinctes :**
- **Capture de l'utilisateur** : seule référence approuvée pour l'apparence (provenance `écran réel`).
- **PNG `render_nx_*.py`** : reconstitution Pillow à partir des bitmaps HMI et d'un état de menu explicitement identifié, **pas** une capture native du Nextion. Il ne prouve ni le rendu de la police embarquée ni le tactile.
- **HMI/TFT réellement compilés** : autorité pour les objets, coordonnées, ressources, IDs, événements et scripts ; à vérifier par extraction/nxwright et, si possible, simulateur Nextion.

**Pour `pageCfgMenu` 7.0.0, l'aperçu principal doit représenter le menu demandé, et non des données imaginées :**
1. Charger les enfants réels de `network` à partir de `src/Modules/Network/WifiModule/text/cfgmods.fr.json`, source de la hiérarchie partagée. Contrôler leur ordre contre `ConfigMenuModel::collectBranchPaths_`.
2. Afficher `config > network` avec, dans l'ordre, `ethernet`, `modbus-tcp/`, `mqtt`, `time/`, `wifi`, puis **une ligne vide**. Le modèle `buildHomeView_` force `valueVisible=false` : **aucune valeur fictive, aucun bouton de valeur `tV0..tV5` visible**. Pagination `1 / 1`.
3. Le rendu doit employer le véritable fond et les vrais sprites du HMI. Les éléments dynamiques restent des approximations des polices intégrées, mais leurs textes et leur état doivent venir du scénario ci-dessus.
4. Exécuter `nextion/scripts/test_nextion_cfg_preview.py` : il reconstruit indépendamment la scène autorisée et compare **tous les pixels**, vérifie l'absence des anciens champs et le sixième emplacement vide. Un PNG « Paramètre 1 / Valeur / 7,20 » doit désormais **faire échouer** le test.
5. Ouvrir le PNG à **480 × 320** et le comparer côte à côte à **la capture utilisateur**, pas seulement à l'ancien PNG généré. Signaler toute différence restante de police, texte, couleur, position, marge ou icône. Ne jamais présenter le PNG Pillow comme « capture de l'écran réel » ou « simulateur Nextion ».
6. Si un contrôle visuel échoue, corriger la source et recommencer **génération → tests → build HMI/TFT → comparaison visuelle** avant publication.

Un PNG identique à sa version précédente est un **résultat normal pour une modification purement tactile**, mais il ne valide pas cette modification. De même, un `PASS` sur des rectangles JSON ne prouve pas qu'un vrai appui déclenchera le bon événement. Les deux vérifications doivent être indépendantes.

### Contrat tactile indépendant du PNG

- Vérifier les **six** barres et leurs coordonnées `x=5..475`, `y=37+38*i`, `h=34`, les superpositions et l'ordre des composants.
- Vérifier les handlers `bR0..bR5` : appui depuis la gauche, le centre **et la droite** ; mode navigation `RowActivate` vers branche ou feuille ; mode édition vers le gestionnaire `tV` (texte, nombre, booléen et sélection), **sans double événement**.
- Vérifier visibilité et `tsw` au rendu initial **et** au rafraîchissement, page vide, retour clavier, pagination, veille/réveil et alarmes.
- Vérifier `Reboot` : `tmReboot.tim=50`, seuil 40 ticks = **2 s**, relâchement à 1,9 s = aucun reboot, maintien à 2 s = reboot. Tester séparément Home, Back, Prev, Next et Valid.
- Vérifier UART local et UDP distant avec la même vue `ConfigMenuModel` ; conserver la compatibilité des TFT 6.0.0 (5″/7″).
- Les assertions statiques et la compilation démontrent seulement le contrat source et l'assemblage. **Un test de toucher natif dans Nextion Editor/simulateur, ou sur le vrai matériel, doit être déclaré non effectué tant qu'il n'a pas réellement eu lieu.**

## 5. Vérifier les comportements et les régressions
- Tester le fonctionnement des boutons, les couches d'objets, les handlers tactiles, Home, les commandes série, les états, les timers, les animations, les changements de page et la veille/réveil.
- Exécuter les tests `nextion/scripts/test_nextion_*.py` concernés et inspecter les échecs. Ne jamais affaiblir une assertion seulement pour obtenir un `PASS` ; vérifier le comportement attendu.
- **Compatibilité Python/Pillow (2027 et versions ultérieures) — contrôle obligatoire à chaque modification :** exécuter `python nextion/scripts/test_nextion_pillow_compat.py` (également appelé automatiquement par `pio run -e nextion` et dans la CI). Vérifier que les scripts n'emploient pas d'API Pillow obsolète ou dépréciée : notamment `Image.getdata()` (remplacer par `getpixel()` pour des coordonnées connues ou `get_flattened_data()` si disponible et adapté), `Image.ANTIALIAS` (remplacer par `Image.Resampling.LANCZOS`), `ImageFont.getsize()` et `ImageDraw.textsize()` (utiliser les méthodes `*bbox` / `*length` adaptées).
- **Hiérarchie ConfigStore partagée :** pour toute modification de navigation ou de module, modifier exclusivement les métadonnées `cfg_tree_aliases` et `cfg_tree_virtual_branches` dans les fichiers `src/Modules/**/text/cfgmods.fr.json`. Le firmware Nextion et l'interface Web sont générés depuis la même liste résolue. Exécuter `python scripts/tests/test_hmi_config_hierarchy.py`, contrôler les dossiers virtuels et le rendu sur l'écran réel ; ne jamais maintenir une seconde table de chemins C++ (voir `docs/core/nextion-configstore-hierarchy.md`).
- **Double transport Nextion UART / UDP :** dès qu'une page, un bouton, un événement ou le menu ConfigStore change, vérifier **les deux chemins**. Flow.io reste l'unique propriétaire de `ConfigMenuModel` : le dépôt `Flow.io-RemoteDisplay` ne doit contenir aucune copie de la liste des modules/alias. Vérifier `HmiUdpProtocol.h/.cpp` entre les deux dépôts, les six lignes du `ConfigViewSnapshot`, les `HmiEvent` de navigation et de saisie avec `contextRef`, le retour du clavier sur la même page, ainsi que l'affichage des boutons actifs/inactifs sur les TFT 6.0.0 et 7.0.0. Exécuter `python scripts/tests/test_hmi_udp_remote_compat.py --remote-root /chemin/Flow.io-RemoteDisplay --patched` après application du patch FCD, puis compiler **les deux firmwares**. Le test et la compilation CI ne remplacent pas un essai sur matériel réel. Voir `docs/core/nextion-configstore-hierarchy.md`.
- **Suivi obligatoire du projet Nextion Remote UDP (`stephdust/Flow.io-RemoteDisplay`) :** à **chaque modification Nextion ou HMI côté Flow.io** (pages, composants, commandes UART, événements tactiles, menu ConfigStore, protocole UDP, versions TFT), examiner systématiquement les conséquences sur ce dépôt distant, comparer ses implémentations et sa documentation à celles de Flow.io et décider explicitement **« mise à jour nécessaire » ou « aucun changement nécessaire »**. Si nécessaire, **adapter, tester, compiler, committer et mettre à jour la documentation du dépôt RemoteDisplay** en parallèle du correctif Flow.io, puis vérifier l'interopérabilité UART local / UDP distant et les versions 3,5″/5″/7″. Si le dépôt distant n'est pas accessible en écriture, signaler le blocage, préparer le patch/PR et **ne jamais annoncer les deux projets synchronisés** tant que le correctif distant n'a pas été intégré. Éviter toute seconde liste d'alias ConfigStore dans RemoteDisplay.
- **Lire les avertissements** `DeprecationWarning`/`FutureWarning` des scripts de rendu, tests et compilation : les traiter comme un point à résoudre avant publication, **ne jamais masquer** un avertissement avec un filtre, une suppression de logs ou un test affaibli. Le contrôle statique couvre les appels connus dans nos scripts ; il ne remplace pas l'inspection des avertissements provenant de nouvelles API ou dépendances. Vérifier les versions Python/Pillow effectivement utilisées sur le PC et en CI.
- Contrôler `git diff` et les artefacts : aucune modification non demandée d'autres modèles, aucun PNG dans `binary/`, pas de source HMI dirty par la compilation.

## 6. Autorisation de commit (toutes les conditions sont requises)
- [ ] Référence **réelle** identifiée : photo utilisateur et état demandé, page/mode connus.
- [ ] Le PNG montre exactement **la scène demandée**, tirée des métadonnées ConfigStore et non de paramètres fictifs ; contrôle visuel manuel à 480 × 320.
- [ ] Test d'image compare le rendu généré au scénario attendu, pas seulement au dernier rendu généré ; aucun ancien bouton/champ de valeur ne persiste en mode navigation.
- [ ] Sources/identifiants/commandes préservés ou changements explicitement documentés.
- [ ] Compilation **HMI et TFT réellement exécutée** sur les nouvelles sources et réussie ; extraction/contrôle des ressources HMI, manifeste et fichiers finaux.
- [ ] **Tactile et timers vérifiés indépendamment du PNG** (les six lignes, trois positions par ligne, Browse/Edit, retour clavier, annulation Reboot avant 2 s).
- [ ] Firmware ESP32-S3 compilé et tests de hiérarchie Web/Nextion/MQTT/HA réussis s'il y a un impact.
- [ ] **Impact Nextion Remote UDP vérifié :** correctif synchronisé, test croisé et compilation RemoteDisplay si nécessaire ; comportement 6.0.0/7.0.0 préservé.
- [ ] Compatibilité Python/Pillow vérifiée ; aucun avertissement de dépréciation non traité dans nos scripts, aucun assouplissement d'assertions pour cacher un échec.
- [ ] Les limites restantes sont énoncées explicitement : notamment test physique ou simulateur Nextion non effectué, ou différences de police encore possibles.

**Si une condition n'est pas remplie ou vérifiable : aucun commit `dev`, aucune release annoncée comme validée.** Corriger avant publication ou expliquer le blocage. Une branche de test n'est qu'un espace d'expérimentation ; la publication en production exige ces preuves, même si les étapes CI sont vertes. La validation sur le **Nextion physique** reste distincte et ne doit pas être revendiquée sans test matériel.

## 7. Si la compilation de l'utilisateur échoue malgré un CI vert

Demander/relever immédiatement : commande exacte (`pio run` ou `pio run -e nextion`), **première erreur** complète, branche et SHA local (`git rev-parse --short HEAD`), version Python et PlatformIO. Reproduire le chemin local si possible ou signaler ce qui n'a pas pu être reproduit. **Ne pas confondre succès CI Linux et succès sur le PC de l'utilisateur.** Ne pas changer le code par hypothèse ni annoncer « tout compile » sans son erreur locale.
