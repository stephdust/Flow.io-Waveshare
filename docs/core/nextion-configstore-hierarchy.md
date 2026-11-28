# Hiérarchie ConfigStore Nextion (3,5 / 5 / 7 pouces)

La navigation de configuration est fournie par `ConfigMenuModel` dans le firmware ESP32-S3. **Les trois tailles de Nextion utilisent le même modèle**, donc aucune modification graphique par modèle n'est requise pour la navigation.

## Structure physique et effet sur l'existant

Les vrais modules des serveurs Modbus TCP sont désormais :

- `network/modbus-tcp/502`
- `network/modbus-tcp/503`
- `network/modbus-tcp/504`

Les anciens modules `modbustcp502/503/504` ne sont **plus enregistrés** dans le ConfigStore. À la première mise à jour, les **21 anciennes clés NVS** `mt0*`, `mt1*`, `mt2*` et les trois blobs `mbtcp0..2` sont effacés exclusivement, avec un marqueur NVS `mbpathv2`. Les nouveaux réglages ont des clés `n502*`, `n503*`, `n504*`, distinctes. **La reconfiguration des trois ports est nécessaire.** Les autres modules, les données SPIFFS, l'OTA et les réglages non-Modbus ne sont pas effacés.

Les topics MQTT deviennent `cfg/network/modbus-tcp/{502,503,504}` ; les commandes HA `cfg/set` écrivent maintenant sur ces chemins. Les `unique_id` existants des entités HA sont conservés, mais il faut **rafraîchir la découverte Home Assistant** après la mise à jour. Les anciens topics retenus sur le broker MQTT, le cas échéant, peuvent demander un nettoyage manuel.

## Navigation commune

Le modèle de navigation applique aussi les correspondances déjà utilisées dans le Web, sans renommer leurs vraies données :

- `network/wifi` ↔ `wifi`, idem ethernet, time et mqtt ;
- `io/input/analog/aXX` ↔ `io/input/aXX` et `io/input/digital/iXX` ↔ `io/input/iXX` ;
- `hmi/tft` ↔ `tft/s3`, y compris les sous-modules.

Tous les chemins `config > ...` affichés sont convertis en vrais noms **avant lecture et écriture**, et les chemins restent triés et dédoublonnés. Le menu passe de 24 à 64 entrées par niveau, toujours par pages de six. Aucun changement de dessin HMI/TFT n'est nécessaire.

## Validation obligatoire

Le contrôle `python scripts/tests/test_hmi_config_hierarchy.py` compile le convertisseur C++ natif puis compare ses résultats aux alias présents dans **tous** les fichiers `cfgmods.fr.json`. Il vérifie également les chemins Modbus, les nouveaux topics MQTT, les modèles de commandes HA et l'absence des anciens modules. GitHub Actions compile ensuite le firmware ESP32-S3 réel. Tester sur matériel : root network, network/modbus-tcp, ports 502/503/504, édition, Back/Home, navigation à 32 entrées analogiques, HA et MQTT.
