# Hiérarchie ConfigStore Nextion (3,5 / 5 / 7 pouces)

La navigation de configuration est fournie par `ConfigMenuModel` dans le firmware ESP32-S3. **Les trois tailles de Nextion utilisent le même modèle**, donc aucune modification graphique par modèle n'est requise pour la navigation.

## Structure physique et effet sur l'existant

Les vrais modules des serveurs Modbus TCP sont désormais :

- `network/modbus-tcp/502`
- `network/modbus-tcp/503`
- `network/modbus-tcp/504`

Les anciens modules `modbustcp502/503/504` ne sont **plus enregistrés** dans le ConfigStore. À la première mise à jour, les **21 anciennes clés NVS** `mt0*`, `mt1*`, `mt2*` et les trois blobs `mbtcp0..2` sont effacés exclusivement, avec un marqueur NVS `mbpathv2`. Les nouveaux réglages ont des clés `n502*`, `n503*`, `n504*`, distinctes. **La reconfiguration des trois ports est nécessaire.** Les autres modules, les données SPIFFS, l'OTA et les réglages non-Modbus ne sont pas effacés.

Les topics MQTT deviennent `cfg/network/modbus-tcp/{502,503,504}` ; les commandes HA `cfg/set` écrivent maintenant sur ces chemins. Les `unique_id` existants des entités HA sont conservés, mais il faut **rafraîchir la découverte Home Assistant** après la mise à jour. Les anciens topics retenus sur le broker MQTT, le cas échéant, peuvent demander un nettoyage manuel.

## Une seule source de vérité pour le Web et les trois Nextion

**Ne plus ajouter manuellement d'alias ou de dossier virtuel dans le C++.**
Chaque module déclare ses métadonnées dans son fichier `src/Modules/**/text/cfgmods.fr.json`, via les tableaux `meta.cfg_tree_aliases` et `meta.cfg_tree_virtual_branches`. Ces déclarations sont fusionnées et **filtrées selon le profil matériel** par `scripts/generate_config_docs.py` dans le fichier Web transitoire `data/webinterface/cfgmods.json`.

Le Web lit directement ce résultat. Lors de la même préparation SPIFFS, `scripts/generate_hmi_config_paths.py` transforme **ce même JSON déjà résolu** en `src/Modules/HMIModule/ConfigMenuPaths_Generated.h` pour l'ESP32. Ce fichier C++ est une **sortie générée** et non une deuxième liste à maintenir. `ConfigMenuPaths.h` contient uniquement la mécanique générique de recherche de préfixes, sans alias écrits en dur.

Les chemins d'affichage tels que `network/wifi`, `io/input/analog/aXX`, `io/input/digital/iXX` et `hmi/tft` restent traduits vers leurs vrais noms ConfigStore au moment des lectures et des écritures. **Les sous-chemins d'un alias** sont automatiquement conservés. Une correspondance nouvelle ne demande donc que de modifier ses métadonnées, pas le Web et le firmware séparément.

Les dossiers `cfg_tree_virtual_branches` utilisent désormais **exactement leurs enfants déclarés**, même lorsqu'un enfant n'a pas encore de module ConfigStore. Un dossier virtuel permet la navigation mais ne peut pas recevoir d'écriture. Un enfant sans module ni sous-dossier s'affiche sans action d'édition ; cela évite de diriger une commande vers un module inexistant. Les autres dossiers sont reconstruits à partir des modules enregistrés, avec tri et dédoublonnage.

La limite reste 64 entrées par niveau, paginées par six. Le même `ConfigMenuModel` pilote les Nextion 3,5″, 5″ et 7″ ; la hiérarchie partagée ne nécessite pas de modifier les images des 5″/7″. L'ergonomie tactile sans flèches est une modification visuelle spécifique au TFT 7.0.0 du 3,5″.

### Navigation tactile sans flèches — Nextion 3,5″ TFT 7.0.0

Sur `pageCfgMenu`, le fil d'Ariane `tPath` utilise une police intermédiaire plus lisible. Les six zones de libellés `tL0..tL5` s'étendent jusqu'à l'extrémité droite (x=15, largeur=452) et sont tactiles. Les flèches `bR0..bR5` ne sont plus dessinées : sur la version 7.0.0, les éventuelles zones `bR` sont des `hotspot` transparents, sans image. Le bouton de valeur `tV` conserve sa propre interaction lorsqu'il existe.

Un appui sur le libellé génère toujours `RowActivate` : Flow.io appelle d'abord `ConfigMenuModel::enterRow` pour ouvrir un dossier, puis, seulement si aucun dossier n'a été ouvert, `editRow` pour afficher les valeurs d'une feuille. Le modèle ConfigStore reste centralisé dans Flow.io, sans nouvel alias ni changement du protocole UDP v7. Le TFT 6.0.0 (5″/7″) garde son apparence et ses commandes existantes.

Tests : `pio run -e nextion`, `python scripts/tests/test_hmi_config_hierarchy.py`, `pio run -e Flowio-waveshare-esp32-s3`, test du firmware distant et examen réel du PNG `pageCfgMenu`. La vérification matérielle tactile UART/UDP reste à faire lors de l'installation.

### Procédure pour ajouter une branche

1. Ajouter ou modifier **uniquement** `cfg_tree_aliases` et/ou `cfg_tree_virtual_branches` dans les métadonnées du module concerné.
2. Exécuter `python scripts/tests/test_hmi_config_hierarchy.py` : le test recrée le JSON Web du profil Waveshare, génère le C++, compare les chemins, les sous-arbres et teste une nouvelle entrée synthétique.
3. Exécuter `pio run -e Flowio-waveshare-esp32-s3`. La préparation SPIFFS régénère systématiquement le C++ avant la compilation du firmware.
4. Vérifier Web et Nextion sur l'écran réel, notamment l'accès aux nœuds virtuels sans module physique, Retour et Home. **Ne pas créer de table de chemins dans `ConfigMenuPaths.h`.**

## Validation obligatoire

Le contrôle `python scripts/tests/test_hmi_config_hierarchy.py` génère d'abord le JSON Web pour le profil Waveshare, puis le même tableau C++ que la compilation. Il compile le convertisseur C++ natif et compare **tous les alias et tous les enfants virtuels** au JSON Web effectivement utilisé. Il vérifie aussi qu'un ajout synthétique dans les métadonnées apparaît sans retouche C++, les chemins Modbus, les nouveaux topics MQTT, les commandes HA et l'absence des anciens modules. GitHub Actions compile ensuite le firmware ESP32-S3 réel. Tester sur matériel : root network, network/modbus-tcp, ports 502/503/504, édition, Back/Home, navigation à 32 entrées analogiques, HA et MQTT.


## Transport du Nextion : UART local et UDP distant

Les deux transports utilisent **exactement le même `ConfigMenuView`**, produit par `ConfigMenuModel` **dans Flow.io**. La liste unique `cfg_tree_aliases` / `cfg_tree_virtual_branches` n'est jamais recopiée dans `Flow.io-RemoteDisplay`.

- **UART local :** Flow.io construit le menu puis le rend directement par `NextionDriver`.
- **UDP :** Flow.io construit le même menu puis `RemoteHmiUdpDriver` envoie un `ConfigViewSnapshot` fiable au `FlowConnectDisplayUdpClientModule`, qui rend les six lignes en UART local. Le remote n'effectue **aucune recherche ConfigStore**. Ses événements `RowActivate`, `RowEdit`, `Back`, `NextPage`, `Validate` et `RowSetText` reviennent à Flow.io avec `contextRef`.
- **Protocole UDP :** version **7** conservée. Le titre reste limité à 24 octets, mais Flow.io le compacte en chemin avec `/` en privilégiant la partie utile à droite (ex. `network/modbus-tcp/502`). Il s'agit uniquement d'un libellé, **pas d'un chemin utilisé pour les commandes**. Les lignes, flags, séquences, ACK et contextes ne changent pas.
- **Compatibilité TFT :** le Nextion 7.0.0 (design 3D 3,5″) et les TFT 6.0.0 (5″/7″ existants) sont acceptés par Flow.io ; 2.0.0 reste historiquement accepté. Sur la version 7.0.0 du RemoteDisplay, les boutons Home, Back, Prev, Next et Valid restent visibles, même désactivés (touch `tsw=0`). Le TFT 6.0.0 conserve son rendu d'origine.

### Vérification croisée des deux dépôts

Le test `python scripts/tests/test_hmi_udp_remote_compat.py --remote-root /chemin/Flow.io-RemoteDisplay` vérifie le contrat entre les deux dépôts et compile l'algorithme de titre en C++ natif. La CI extrait le vrai dépôt RemoteDisplay en lecture seule, vérifie les sources du protocole, applique en **copie temporaire** `python scripts/tests/apply_remote_display_menu_patch.py --remote-root remote-display --apply`, puis compile **les deux firmwares ESP32**. Ne jamais supposer que le code modifié dans la copie CI a été publié dans RemoteDisplay.

Pour intégrer le correctif dans le vrai dépôt distant (après autorisation GitHub en écriture), créer une branche RemoteDisplay, appliquer le script avec `--apply`, vérifier `pio run -e FlowConnectDisplay` et ouvrir une PR vers `main`. Les fichiers TFT ne changent pas automatiquement ; installer la version adaptée physiquement sur le Nextion.

### Matrice d'essais matériels

Vérifier sur UART direct **et** UDP :
- navigation `config > network > modbus-tcp > Port 502`, puis édition, validation et retour ;
- `io/input/analog` avec pagination, `hmi/tft` et dossiers virtuels déclarés ;
- retour du clavier sur la **même page** avec `contextRef`, sans perte du formulaire ;
- visibilité des boutons 3D désactivés sur 7.0.0 et fonctionnement normal des TFT 6.0.0 ;
- déconnexion UDP, reconnexion et réémission du snapshot sans événement exécuté deux fois.
