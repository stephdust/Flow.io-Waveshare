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

La limite reste 64 entrées par niveau, paginées par six. Le même `ConfigMenuModel` pilote les Nextion 3,5″, 5″ et 7″ ; aucune modification d'images HMI/TFT n'est nécessaire.

### Procédure pour ajouter une branche

1. Ajouter ou modifier **uniquement** `cfg_tree_aliases` et/ou `cfg_tree_virtual_branches` dans les métadonnées du module concerné.
2. Exécuter `python scripts/tests/test_hmi_config_hierarchy.py` : le test recrée le JSON Web du profil Waveshare, génère le C++, compare les chemins, les sous-arbres et teste une nouvelle entrée synthétique.
3. Exécuter `pio run -e Flowio-waveshare-esp32-s3`. La préparation SPIFFS régénère systématiquement le C++ avant la compilation du firmware.
4. Vérifier Web et Nextion sur l'écran réel, notamment l'accès aux nœuds virtuels sans module physique, Retour et Home. **Ne pas créer de table de chemins dans `ConfigMenuPaths.h`.**

## Validation obligatoire

Le contrôle `python scripts/tests/test_hmi_config_hierarchy.py` génère d'abord le JSON Web pour le profil Waveshare, puis le même tableau C++ que la compilation. Il compile le convertisseur C++ natif et compare **tous les alias et tous les enfants virtuels** au JSON Web effectivement utilisé. Il vérifie aussi qu'un ajout synthétique dans les métadonnées apparaît sans retouche C++, les chemins Modbus, les nouveaux topics MQTT, les commandes HA et l'absence des anciens modules. GitHub Actions compile ensuite le firmware ESP32-S3 réel. Tester sur matériel : root network, network/modbus-tcp, ports 502/503/504, édition, Back/Home, navigation à 32 entrées analogiques, HA et MQTT.
